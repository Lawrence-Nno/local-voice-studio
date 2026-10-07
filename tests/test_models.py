import unittest
import tempfile
from threading import Event
import numpy as np

from app.generation import run_job
from app.storage import read_json
from pathlib import Path
from unittest.mock import Mock

from app.qwen_engine import QwenEngine


class ModelTests(unittest.TestCase):
    def test_qwen_rejects_generic_voice(self):
        with self.assertRaisesRegex(ValueError, "reference recording"):
            QwenEngine().prepare(None)

    def test_reference_and_seed_are_sent_to_isolated_worker(self):
        engine = QwenEngine()
        engine.request = Mock(return_value={"ok": True})
        engine.transcript = "The exact words in my recording."
        engine.prepare(Path("reference.wav"))
        engine.request.assert_called_once_with("prepare", reference="reference.wav", transcript=engine.transcript)
        engine.set_seed(42)
        engine.request.assert_called_with("seed", seed=42)

    def test_qwen_default_sampling_and_metadata(self):
        class FakeQwen:
            model_id = "Qwen3-TTS 1.7B Base"
            device = "cpu"
            transcript = "My reference words."
            def load(self, *_): pass
            def prepare(self, *_): pass
            def set_seed(self, value): self.seed = value
            def generate(self, _, **kwargs):
                self.parameters = kwargs
                return np.zeros(2400, dtype=np.float32), 24000
        engine = FakeQwen()
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            result = run_job(engine, "Hello.", None, Path("reference.wav"), "CPU", Event(),
                             lambda *_: None, data, {"preset": "Default", "seed": 42})
            metadata = read_json(data / "jobs" / result.stem / "job.json")
            self.assertEqual(engine.parameters, {"temperature": .9, "repetition_penalty": 1.05})
            self.assertEqual(engine.seed, 42)
            self.assertEqual(metadata["model"], engine.model_id)
            self.assertEqual(metadata["reference_mode"], "audio + transcript")

    def test_unload_releases_worker_and_pipes(self):
        engine = QwenEngine()
        process = engine.model = Mock()
        engine.log = Mock()
        engine.unload()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=10)
        process.stdin.close.assert_called_once()
        process.stdout.close.assert_called_once()
        self.assertIsNone(engine.model)
        self.assertIsNone(engine.log)


if __name__ == "__main__":
    unittest.main()
