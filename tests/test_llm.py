import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
from core import config, llm, memory


class FakeResponse:
    def __init__(self, status_code=200, lines=(), body=None, stream_error=None):
        self.status_code = status_code
        self.lines = lines
        self.body = body
        self.stream_error = stream_error
        self.close_calls = 0

    def iter_lines(self):
        yield from self.lines
        if self.stream_error is not None:
            raise self.stream_error

    def json(self):
        if isinstance(self.body, ValueError):
            raise self.body
        return self.body

    def close(self):
        self.close_calls += 1


class TestOllamaClient(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("core.llm.requests.post")
        self.post = patcher.start()
        self.addCleanup(patcher.stop)

    def test_connection_error_and_initial_timeout_name_url(self):
        for error in (llm.requests.ConnectionError, llm.requests.Timeout):
            with self.subTest(error=error), mock.patch.object(
                config, "OLLAMA_URL", "http://localhost:8123"
            ):
                self.post.side_effect = error("transport failure")
                with self.assertRaises(llm.OllamaError) as raised:
                    next(llm.ask_llm_stream("hello"))
                self.assertEqual(
                    str(raised.exception),
                    "Ollama is not reachable at http://localhost:8123. Start Ollama and try again.",
                )

    def test_404_names_model_and_pull_command(self):
        response = FakeResponse(status_code=404)
        self.post.return_value = response
        with mock.patch.object(config, "MODEL", "example:mini"):
            with self.assertRaises(llm.OllamaError) as raised:
                next(llm.ask_llm_stream("hello"))
        self.assertEqual(
            str(raised.exception),
            'Model "example:mini" is not installed. Run: ollama pull example:mini',
        )
        self.assertEqual(response.close_calls, 1)

    def test_other_http_errors_include_status_and_available_detail(self):
        for status, body, expected in (
            (500, {"error": "model failed"}, "Ollama returned HTTP 500: model failed"),
            (302, ValueError("invalid JSON"), "Ollama returned HTTP 302."),
        ):
            with self.subTest(status=status):
                response = FakeResponse(status_code=status, body=body)
                self.post.return_value = response
                with self.assertRaises(llm.OllamaError) as raised:
                    next(llm.ask_llm_stream("hello"))
                self.assertEqual(str(raised.exception), expected)
                self.assertEqual(response.close_calls, 1)

    def test_stream_error_raises_after_earlier_chunk(self):
        response = FakeResponse(lines=[b'{"response":"first"}', b'{"error":"model failed"}'])
        self.post.return_value = response
        stream = llm.ask_llm_stream("hello")
        self.assertEqual(next(stream), "first")
        with self.assertRaisesRegex(llm.OllamaError, "^model failed$"):
            next(stream)
        self.assertEqual(response.close_calls, 1)

    def test_stream_read_timeout_reports_timeout_and_closes(self):
        for error in (
            llm.requests.ReadTimeout("timed out"),
            llm.requests.ConnectionError(llm.ReadTimeoutError(None, "/api/generate", "timed out")),
        ):
            with self.subTest(error=type(error)):
                response = FakeResponse(lines=[b'{"response":"first"}'], stream_error=error)
                self.post.return_value = response
                stream = llm.ask_llm_stream("hello")
                self.assertEqual(next(stream), "first")
                with self.assertRaisesRegex(llm.OllamaError, "timed out"):
                    next(stream)
                self.assertEqual(response.close_calls, 1)

    def test_normal_stream_yields_in_order_and_closes_once(self):
        response = FakeResponse(lines=[b"", b'{"response":"first"}', b'{"response":"second"}'])
        self.post.return_value = response
        self.assertEqual(list(llm.ask_llm_stream("hello")), ["first", "second"])
        self.assertEqual(response.close_calls, 1)

    def test_closing_generator_early_closes_response(self):
        response = FakeResponse(lines=[b'{"response":"first"}', b'{"response":"second"}'])
        self.post.return_value = response
        stream = llm.ask_llm_stream("hello")
        self.assertEqual(next(stream), "first")
        self.assertEqual(response.close_calls, 0)
        stream.close()
        self.assertEqual(response.close_calls, 1)

    def test_request_uses_configured_timeouts(self):
        self.post.return_value = FakeResponse()
        with (
            mock.patch.object(config, "CONNECT_TIMEOUT", 1.5),
            mock.patch.object(config, "READ_TIMEOUT", 8.5),
        ):
            list(llm.ask_llm_stream("hello"))
        self.assertEqual(self.post.call_args.kwargs["timeout"], (1.5, 8.5))


class TestChatOllamaErrors(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.memory_file = Path(directory.name) / "memory.json"
        patcher = mock.patch.object(memory, "MEMORY_FILE", str(self.memory_file))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def chat(self, stream, *, buffered=True):
        with mock.patch.object(app_module, "ask_llm_stream", return_value=stream):
            return self.client.post(
                "/chat", json={"message": "Explain Python", "memory": True}, buffered=buffered
            )

    def test_first_chunk_error_returns_503_without_saving(self):
        def failing_stream():
            yield from ()
            raise llm.OllamaError("Ollama is not reachable at the configured URL.")

        response = self.chat(failing_stream())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(), {"error": "Ollama is not reachable at the configured URL."}
        )
        self.assertFalse(self.memory_file.exists())
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_normal_reply_is_streamed_and_saved(self):
        response = self.chat(iter(["First ", "second."]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(response.get_data(as_text=True), "First second.")
        self.assertEqual(memory.get_history(), "User: Explain Python\nAssistant: First second.")

    def test_midstream_error_is_visible_without_saving(self):
        def failing_stream():
            yield "First"
            raise llm.OllamaError("model failed")

        response = self.chat(failing_stream())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), "First\n\n[Error: model failed]")
        self.assertFalse(self.memory_file.exists())

    def test_disconnecting_closes_upstream_without_saving(self):
        upstream = FakeResponse(lines=[b'{"response":"first"}', b'{"response":"second"}'])
        with mock.patch("core.llm.requests.post", return_value=upstream):
            response = self.chat(llm.ask_llm_stream("hello"), buffered=False)
            try:
                self.assertEqual(next(iter(response.response)), b"first")
                self.assertEqual(upstream.close_calls, 0)
            finally:
                response.close()

        self.assertEqual(upstream.close_calls, 1)
        self.assertFalse(self.memory_file.exists())
