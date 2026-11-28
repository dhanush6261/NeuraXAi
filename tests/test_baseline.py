"""Characterization tests for the v0.3.0 baseline.

These lock in current behaviour before the v0.4.0 rebuild. Known bugs are
written as the *correct* behaviour and marked @unittest.expectedFailure;
the task that fixes each bug removes the decorator (see tasks/todo.md).

Memory is redirected to a temp directory and the LLM is mocked, so no
Ollama server and no real data/memory.json are touched.
"""
import os
import tempfile
import unittest
from unittest import mock

import app as app_module
from core import memory


class BaselineTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.memory_file = os.path.join(self._tmp.name, "memory.json")
        patcher = mock.patch.object(memory, "MEMORY_FILE", self.memory_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

        self.llm = mock.patch.object(
            app_module, "ask_llm_stream", return_value=iter(["Hel", "lo."])
        ).start()
        self.addCleanup(mock.patch.stopall)

        self.client = app_module.app.test_client()

    def chat(self, message, memory_on=True):
        resp = self.client.post("/chat", json={"message": message, "memory": memory_on})
        return resp.status_code, resp.get_data(as_text=True)


class TestRoutes(BaselineTestCase):
    def test_homepage_renders(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"NeuraXAi", resp.data)

    def test_greeting_shortcut_skips_llm_and_saves_turn(self):
        status, body = self.chat("hi")
        self.assertEqual(status, 200)
        self.assertEqual(body, "Hello! How can I help you?")
        self.llm.assert_not_called()
        self.assertIn("User: hi", memory.get_history())

    def test_llm_reply_is_streamed_and_saved(self):
        status, body = self.chat("What is Python?")
        self.assertEqual(status, 200)
        self.assertEqual(body, "Hello.")
        self.llm.assert_called_once()
        self.assertIn("Assistant: Hello.", memory.get_history())

    def test_memory_off_does_not_write_history(self):
        self.chat("What is Python?", memory_on=False)
        self.assertFalse(os.path.exists(self.memory_file))

    def test_full_name_is_stored(self):
        self.chat("My name is Alex")
        self.assertEqual(memory.get_user_name(), "Alex")


class TestKnownBugs(BaselineTestCase):
    def test_save_creates_missing_data_dir(self):  # D1 — fixed by Task 2
        nested = os.path.join(self._tmp.name, "data", "memory.json")
        with mock.patch.object(memory, "MEMORY_FILE", nested):
            memory.save_message("user", "hello")
            self.assertTrue(os.path.exists(nested))

    def test_i_am_a_student_does_not_overwrite_name(self):
        memory.save_user_name("Alex Kumar")
        self.chat("I am a student")
        self.assertEqual(memory.get_user_name(), "Alex Kumar")

    def test_memory_off_hides_stored_name(self):
        memory.save_user_name("Alex")
        _, body = self.chat("what is my name", memory_on=False)
        self.assertNotIn("Alex", body)


if __name__ == "__main__":
    unittest.main()
