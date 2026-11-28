import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
from core import memory
from core.intent import extract_name


class TestExtractName(unittest.TestCase):
    def test_explicit_name_phrases_and_rejected_inputs(self):
        cases = [
            ("My name is Alex Kumar", "Alex Kumar"),
            ("call me Sam", "Sam"),
            ("naa peru Ravi", "Ravi"),
            ("my name is alex.", "alex"),
            ("Call me Sam!", "Sam"),
            ("నా పేరు అమర", None),
            ("naa peru అమర", "అమర"),
            ("naa peru రవి", "రవి"),
            ("naa peru కృష్ణ", "కృష్ణ"),
            ("My name is राम", "राम"),
            ("My name is Jose\u0301", "Jose\u0301"),
            ("call me ిరవి", None),
            ("My name is Élodie", "Élodie"),
            ("call me Anne-Marie O'Neill", "Anne-Marie O'Neill"),
            ("  CALL ME Sam…  ", "Sam"),
            ("I am a student", None),
            ("I am tired", None),
            ("I'm Alex", None),
            ("My name is", None),
            ("call me!", None),
            ("Call me A B C D E", None),
            ("Call me " + "A" * 60, "A" * 60),
            ("Call me " + "A" * 61, None),
            ("My name is R2D2", None),
            ("call me back", None),
            ("Call me Later", None),
            ("my name is not Alex", None),
            ("I said my name is Bob", None),
            ("call meSam", None),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(extract_name(text), expected)


class TestNameCapture(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        memory_file = Path(directory.name) / "memory.json"
        memory_patcher = mock.patch.object(memory, "MEMORY_FILE", str(memory_file))
        memory_patcher.start()
        self.addCleanup(memory_patcher.stop)
        llm_patcher = mock.patch.object(
            app_module, "ask_llm_stream", return_value=iter(["Good luck with your studies."])
        )
        self.llm = llm_patcher.start()
        self.addCleanup(llm_patcher.stop)
        self.client = app_module.app.test_client()

    def chat(self, text, memory_on=True):
        response = self.client.post("/chat", json={"message": text, "memory": memory_on})
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_memory_on_saves_full_name(self):
        self.assertEqual(self.chat("My name is Alex Kumar"), "Got it. Your name is Alex Kumar.")
        self.assertEqual(memory.get_user_name(), "Alex Kumar")
        self.llm.assert_not_called()

    def test_memory_off_keeps_saved_name_and_explains(self):
        memory.save_user_name("Sam")
        self.assertEqual(
            self.chat("My name is Alex Kumar", memory_on=False),
            "Nice to meet you, Alex Kumar. Memory is off, so I won't remember your name.",
        )
        self.assertEqual(memory.get_user_name(), "Sam")
        self.llm.assert_not_called()

    def test_generic_statement_keeps_name_and_goes_to_llm(self):
        memory.save_user_name("Alex Kumar")
        self.assertEqual(self.chat("I am a student"), "Good luck with your studies.")
        self.assertEqual(memory.get_user_name(), "Alex Kumar")
        self.llm.assert_called_once()
