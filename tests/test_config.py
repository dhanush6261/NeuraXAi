import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import config, llm, memory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "MODEL": "phi3:mini",
    "OLLAMA_URL": "http://localhost:11434",
    "CONNECT_TIMEOUT": 3.0,
    "READ_TIMEOUT": 120.0,
    "TEMPERATURE": 0.7,
    "MAX_MESSAGE_CHARS": 4000,
    "DEBUG": False,
    "DATA_DIR": str(PROJECT_ROOT / "data"),
}


class TestEnvironmentConfig(unittest.TestCase):
    def setUp(self):
        self.addCleanup(importlib.reload, config)

    def load(self, **settings):
        variables = {f"NEURAXAI_{name}": value for name, value in settings.items()}
        with mock.patch.dict(os.environ, variables, clear=True):
            return importlib.reload(config)

    def test_defaults_without_environment_variables(self):
        settings = self.load()
        self.assertEqual({name: getattr(settings, name) for name in DEFAULTS}, DEFAULTS)

    def test_each_environment_variable_overrides_its_default(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.load(
                MODEL="qwen3.5:4b",
                OLLAMA_URL="https://localhost:8443/",
                CONNECT_TIMEOUT="1.25",
                READ_TIMEOUT="45",
                TEMPERATURE="0",
                MAX_MESSAGE_CHARS="2000",
                DEBUG="true",
                DATA_DIR=directory,
            )
            self.assertEqual(settings.MODEL, "qwen3.5:4b")
            self.assertEqual(settings.OLLAMA_URL, "https://localhost:8443")
            self.assertEqual(settings.CONNECT_TIMEOUT, 1.25)
            self.assertEqual(settings.READ_TIMEOUT, 45.0)
            self.assertEqual(settings.TEMPERATURE, 0.0)
            self.assertEqual(settings.MAX_MESSAGE_CHARS, 2000)
            self.assertIs(settings.DEBUG, True)
            self.assertEqual(settings.DATA_DIR, directory)

    def test_invalid_values_warn_and_fall_back(self):
        invalid = {
            "MODEL": ("", "two words"),
            "OLLAMA_URL": ("invalid", "http://localhost:99999", "http://localhost/?a=b"),
            "CONNECT_TIMEOUT": ("abc", "-1", "0", "inf"),
            "READ_TIMEOUT": ("abc", "-1", "nan"),
            "TEMPERATURE": ("abc", "-1", "5", "nan"),
            "MAX_MESSAGE_CHARS": ("abc", "-1", "2.5"),
            "DEBUG": ("maybe",),
            "DATA_DIR": ("",),
        }
        for name, values in invalid.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    with self.assertLogs("core.config", level="WARNING") as logs:
                        settings = self.load(**{name: value})
                    self.assertIn(f"NEURAXAI_{name}", logs.output[0])
                    self.assertEqual(getattr(settings, name), DEFAULTS[name])

    def test_debug_truthy_and_falsy_values(self):
        for value, expected in (
            ("1", True), ("true", True), (" YES ", True),
            ("0", False), ("false", False), ("No", False),
        ):
            with self.subTest(value=value):
                self.assertIs(self.load(DEBUG=value).DEBUG, expected)

    def test_relative_data_directory_uses_project_root(self):
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                settings = self.load(DATA_DIR="local/storage")
                self.assertEqual(settings.DATA_DIR, str(PROJECT_ROOT / "local" / "storage"))
            finally:
                os.chdir(original_cwd)

    def test_memory_file_uses_config_data_directory(self):
        self.addCleanup(importlib.reload, memory)
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(config, "DATA_DIR", directory):
                self.assertEqual(
                    importlib.reload(memory).MEMORY_FILE,
                    os.path.join(directory, "memory.json"),
                )


class TestConfigConsumers(unittest.TestCase):
    def test_llm_reads_patched_config_when_called(self):
        with (
            mock.patch.object(config, "MODEL", "test-model"),
            mock.patch.object(config, "OLLAMA_URL", "http://localhost:8443/"),
            mock.patch.object(config, "TEMPERATURE", 1.25),
            mock.patch.object(llm.requests, "post") as post,
        ):
            post.return_value.status_code = 200
            post.return_value.iter_lines.return_value = [b'{"response":"hello"}']
            self.assertEqual(list(llm.ask_llm_stream("test prompt")), ["hello"])

        post.assert_called_once_with(
            "http://localhost:8443/api/generate",
            json={
                "model": "test-model",
                "prompt": "test prompt",
                "stream": True,
                "options": {"temperature": 1.25},
            },
            stream=True,
            timeout=(config.CONNECT_TIMEOUT, config.READ_TIMEOUT),
        )

    def test_no_model_or_port_literals_outside_config(self):
        sources = [PROJECT_ROOT / "app.py", *(PROJECT_ROOT / "core").rglob("*.py")]
        for path in sources:
            if path == PROJECT_ROOT / "core" / "config.py":
                continue
            with self.subTest(path=path):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("phi3:mini", source)
                self.assertNotIn("11434", source)
