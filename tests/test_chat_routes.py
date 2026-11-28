import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
from core import memory


class TestChatShortcuts(unittest.TestCase):
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

    def chat(self, message, memory_on=True):
        response = self.client.post("/chat", json={"message": message, "memory": memory_on})
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_shortcuts_reply_without_llm(self):
        cases = [
            ("Hi!", "Hello! How can I help you?"),
            ("HELLO", "Hello! How can I help you?"),
            ("good morning", "Hello! How can I help you?"),
            ("thanks", "You're welcome!"),
            ("bye", "Bye! Talk to you soon."),
            ("good night", "Bye! Talk to you soon."),
            ("who are you", "I'm NeuraXAi, a local AI assistant running on your computer."),
        ]
        for message, expected in cases:
            with self.subTest(message=message):
                self.llm.reset_mock()
                self.assertEqual(self.chat(message), expected)
                self.llm.assert_not_called()

    def test_longer_messages_go_to_llm(self):
        for message in ("high school", "hello world program in python"):
            with self.subTest(message=message):
                self.llm.reset_mock()
                self.llm.return_value = iter(["A reply."])
                self.assertEqual(self.chat(message), "A reply.")
                self.llm.assert_called_once()

    def test_memory_on_saves_shortcut_turn(self):
        self.assertEqual(self.chat("thanks"), "You're welcome!")
        self.assertEqual(memory.get_history(), "User: thanks\nAssistant: You're welcome!")

    def test_memory_off_does_not_create_memory_file(self):
        self.assertEqual(self.chat("thanks", memory_on=False), "You're welcome!")
        self.assertFalse(self.memory_file.exists())

    def test_telugu_identity_reply(self):
        self.assertEqual(
            self.chat("నువ్వు ఎవరు"),
            "నేను NeuraXAi, మీ కంప్యూటర్ లో నడిచే లోకల్ AI అసిస్టెంట్.",
        )
        self.llm.assert_not_called()

    def test_roman_telugu_name_lookup_does_not_overwrite_saved_name(self):
        memory.save_user_name("Alex")
        self.assertEqual(self.chat("naa peru enti"), "Alex")
        self.assertEqual(memory.get_user_name(), "Alex")
        self.llm.assert_not_called()

    def test_identity_does_not_read_saved_name(self):
        memory.save_user_name("Alex")
        with mock.patch.object(app_module, "get_user_name") as get_name:
            for memory_on in (True, False):
                with self.subTest(memory_on=memory_on):
                    self.assertEqual(
                        self.chat("who are you", memory_on=memory_on),
                        "I'm NeuraXAi, a local AI assistant running on your computer.",
                    )
            get_name.assert_not_called()
