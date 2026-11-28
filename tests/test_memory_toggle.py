import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
from core import memory


class TestMemoryToggle(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.memory_file = Path(temp.name) / "memory.json"
        memory_patcher = mock.patch.object(memory, "MEMORY_FILE", str(self.memory_file))
        memory_patcher.start()
        self.addCleanup(memory_patcher.stop)
        llm_patcher = mock.patch.object(
            app_module, "ask_llm_stream", return_value=iter(["A reply."])
        )
        self.llm = llm_patcher.start()
        self.addCleanup(llm_patcher.stop)
        self.client = app_module.app.test_client()

    def test_memory_off_hides_name_and_preserves_file(self):
        memory.save_user_name("Alex")
        before = self.memory_file.read_bytes()

        for message, expected in [
            ("what is my name", "I don't know."),
            ("hello", "Hello! How can I help you?"),
            ("my name is Sam", "Nice to meet you, Sam. Memory is off, so I won't remember your name."),
            ("Explain Python", "A reply."),
        ]:
            with self.subTest(message=message):
                response = self.client.post("/chat", json={"message": message, "memory": False})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_data(as_text=True), expected)
                self.assertEqual(self.memory_file.read_bytes(), before)

    def test_memory_off_omits_history_from_prompt(self):
        memory.save_message("user", "Earlier private conversation")
        response = self.client.post(
            "/chat", json={"message": "Explain Python", "memory": False}
        )
        self.assertEqual(response.get_data(as_text=True), "A reply.")
        self.llm.assert_called_once()
        (prompt,) = self.llm.call_args.args
        self.assertIn("Explain Python", prompt)
        self.assertNotIn("Earlier private conversation", prompt)

    def test_memory_on_returns_name_and_saves_lookup(self):
        memory.save_user_name("Alex")
        response = self.client.post(
            "/chat", json={"message": "what is my name", "memory": True}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), "Alex")
        self.assertEqual(memory.get_history(), "User: what is my name\nAssistant: Alex")
        self.llm.assert_not_called()

    def test_missing_memory_defaults_to_on(self):
        response = self.client.post("/chat", json={"message": "hello"})
        self.assertEqual(response.get_data(as_text=True), "Hello! How can I help you?")
        self.assertIn("User: hello", memory.get_history())

    def test_non_boolean_memory_returns_json_error(self):
        for value in ("no", 1, None):
            with self.subTest(value=value):
                response = self.client.post("/chat", json={"message": "hello", "memory": value})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json(), {"error": "memory must be true or false"})
                self.assertFalse(self.memory_file.exists())
