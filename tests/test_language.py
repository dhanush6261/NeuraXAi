"""Tests for core.language.detect_language and its /chat integration."""
import os
import tempfile
import unittest
from unittest import mock

import app as app_module
from core import memory
from core.language import detect_language


class TestDetectLanguage(unittest.TestCase):
    def test_detect_language_cases(self):
        cases = [
            ("Telugu script sentence", "తెలుగులో AI గురించి చెప్పు", "telugu"),
            ("Telugu script short", "తెలుగులో చెప్పు", "telugu"),
            ("Mixed English and Telugu script", "Explain AI తెలుగులో", "telugu"),
            ("Roman Telugu question", "Python ante enti?", "telugu"),
            ("Roman Telugu name question", "Naa peru enti?", "telugu"),
            ("Roman Telugu uppercase", "PYTHON ANTE ENTI?", "telugu"),
            ("Roman Telugu greeting", "Meeru baagunnara?", "telugu"),
            ("Roman Telugu two ambiguous words", "Naa peru Alex", "telugu"),
            ("Roman Telugu ante emi", "AI ante emi?", "telugu"),
            ("Roman Telugu install cheyali", "Flask ela install cheyali?", "telugu"),
            ("Roman Telugu em chestunnav", "em chestunnav", "telugu"),
            ("Roman Telugu lo ela raayali", "Python lo loops ela raayali?", "telugu"),
            ("English question", "What is Python?", "english"),
            ("Empty string", "", "english"),
            ("Whitespace only", "   \t\n  ", "english"),
            ("Numbers only", "12345", "english"),
            ("Ambiguous single word Peru", "Peru", "english"),
            ("English sentence with Peru", "Tell me about Peru", "english"),
            ("Ambiguous single word ante", "Up the ante", "english"),
            ("Ambiguous single word ELA", "What is ELA?", "english"),
            ("Ambiguous single word EMI", "What is my EMI?", "english"),
            ("Ambiguous single word chala", "chala thanks", "english"),
            ("Repeated single ambiguous word", "Peru Peru", "english"),
            ("Substring must not match whole word", "antenna", "english"),
            ("Substring peruvian must not match peru", "Peruvian food", "english"),
        ]
        for label, text, expected in cases:
            with self.subTest(label=label, text=text):
                self.assertEqual(detect_language(text), expected)


class TestLanguageRouteIntegration(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.memory_file = os.path.join(self._tmp.name, "memory.json")
        patcher = mock.patch.object(memory, "MEMORY_FILE", self.memory_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

        self.llm = mock.patch.object(
            app_module, "ask_llm_stream", return_value=iter(["OK."])
        ).start()
        self.addCleanup(mock.patch.stopall)

        self.client = app_module.app.test_client()

    def test_roman_telugu_prompt_sets_telugu_language_rule(self):
        resp = self.client.post(
            "/chat",
            json={"message": "Python ante enti?", "memory": True},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_data(as_text=True), "OK.")
        self.llm.assert_called_once()
        prompt_sent = self.llm.call_args[0][0]
        self.assertIn("Answer ONLY in Telugu.", prompt_sent)


if __name__ == "__main__":
    unittest.main()
