import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
from core import memory
from core.intent import extract_name
from core.intent import Intent, classify, shortcut_reply


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


class TestClassify(unittest.TestCase):
    def test_exact_phrase_matching(self):
        cases = [
            ("Hi!", Intent.GREETING),
            ("HELLO", Intent.GREETING),
            ("  hey  ", Intent.GREETING),
            ("good morning", Intent.GREETING),
            ("... good   afternoon ?!", Intent.GREETING),
            ("నమస్కారం", Intent.GREETING),
            ("Thanks!", Intent.THANKS),
            ("thank you", Intent.THANKS),
            ("ధన్యవాదాలు", Intent.THANKS),
            ("bye", Intent.FAREWELL),
            ("good night", Intent.FAREWELL),
            ("శుభ రాత్రి", Intent.FAREWELL),
            ("Who are you?", Intent.IDENTITY),
            ("What’s your name?", Intent.IDENTITY),
            ("నువ్వు ఎవరు?", Intent.IDENTITY),
            ("what is my name", Intent.ASK_NAME),
            ("what's my name", Intent.ASK_NAME),
            ("naa peru enti", Intent.ASK_NAME),
            ("నా పేరు ఏమిటి", Intent.ASK_NAME),
            ("high school", None),
            ("hello world program in python", None),
            ("hi, can you explain recursion", None),
            ("thanks for nothing, explain python", None),
            ("what is your name based on", None),
            ("my name is Alex", None),
            ("hi neuraxai", None),
            ("thanks, that helped", None),
            ("", None),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertIs(classify(text), expected)

    def test_shortcut_replies(self):
        cases = [
            (Intent.GREETING, "telugu", None, "హలో! నేను మీకు ఎలా సహాయం చేయగలను?"),
            (Intent.IDENTITY, "english", "Alex", "I'm NeuraXAi, a local AI assistant running on your computer."),
            (Intent.ASK_NAME, "english", "Alex", "Alex"),
            (Intent.ASK_NAME, "english", None, "I don't know."),
            (Intent.ASK_NAME, "telugu", "Alex", "Alex"),
            (Intent.ASK_NAME, "telugu", None, "నాకు తెలియదు."),
            (Intent.THANKS, "other", None, "You're welcome!"),
        ]
        for intent, language, name, expected in cases:
            with self.subTest(intent=intent, language=language, name=name):
                self.assertEqual(shortcut_reply(intent, language, name), expected)
