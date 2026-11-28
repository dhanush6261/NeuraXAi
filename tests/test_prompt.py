
import unittest

from core.prompt import SYSTEM_PROMPT, build_prompt


class TestPromptConstruction(unittest.TestCase):

    def test_default_format(self):
        prompt = build_prompt("What is Python?", "english")

        self.assertIn("- Answer briefly", prompt)
        self.assertIn("- Maximum 3 lines", prompt)

    def test_bullet_format(self):
        prompt = build_prompt(
            "Explain Python in bullet points",
            "english"
        )

        self.assertIn("- Answer ONLY in bullet points", prompt)
        self.assertIn("- Maximum 5 points", prompt)
        self.assertIn("- No paragraphs", prompt)

    def test_paragraph_format(self):
        prompt = build_prompt(
            "Explain Python in a paragraph",
            "english"
        )

        self.assertIn("- Answer in ONE short paragraph", prompt)
        self.assertIn("- Maximum 5 lines", prompt)
        self.assertIn("- No bullet points", prompt)

    def test_language_rules(self):
        english_prompt = build_prompt("Explain Python", "english")
        telugu_prompt = build_prompt("Python ante enti", "telugu")

        self.assertIn("Answer ONLY in English.", english_prompt)
        self.assertIn("Answer ONLY in Telugu.", telugu_prompt)

    def test_system_prompt_and_memory(self):
        history = "User: I like Python"
        prompt = build_prompt(
            "Explain functions",
            "english",
            history
        )

        self.assertTrue(prompt.startswith(SYSTEM_PROMPT.strip()))
        self.assertIn(history, prompt)
        self.assertIn("User:\nExplain functions", prompt)
        self.assertTrue(prompt.endswith("Assistant:"))


if __name__ == "__main__":
    unittest.main()
