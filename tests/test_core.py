import tempfile
import unittest
from pathlib import Path
from threading import Event

import numpy as np
import soundfile as sf

from app.generation import Cancelled, chunk_text, run_job
from app.profiles import Profiles
from app.storage import Settings, read_json


class CoreTests(unittest.TestCase):
    def test_chunking_preserves_normalized_text(self):
        text = ("First sentence.\nSecond sentence has several words! " * 50).strip()
        chunks = chunk_text(text)
        self.assertEqual(" ".join(chunks), " ".join(text.split()))
        self.assertTrue(all(len(chunk) <= 240 for chunk in chunks))

    def test_unbroken_text_is_preserved(self):
        text = "a" * 1900
        self.assertEqual("".join(chunk_text(text)), text)

    def test_profile_restart_and_invalid_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            rate = 24000
            audio = 0.1 * np.sin(np.arange(rate * 7) * 2 * np.pi * 220 / rate)
            source = directory / "source.wav"
            sf.write(source, audio, rate)
            store = Profiles(directory)
            profile, _ = store.import_wav(source, "My voice")
            settings = Settings(directory)
            settings.update(selected_profile=profile["id"])
            self.assertEqual(Settings(directory).values["selected_profile"], profile["id"])
            restored, errors = Profiles(directory).list()
            self.assertFalse(errors)
            self.assertEqual(restored[0]["version"], profile["version"])
            sf.write(source, np.zeros(rate * 7), rate)
            with self.assertRaises(ValueError):
                store.import_wav(source, "Replacement", profile)
            self.assertEqual(store.list()[0][0]["version"], profile["version"])
            self.assertTrue(store.reference(profile).exists())

    def test_valid_replacement_changes_version_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "source.wav"
            sf.write(source, np.full(24000 * 6, 0.1), 24000)
            store = Profiles(directory)
            first, _ = store.import_wav(source, "Voice")
            second, _ = store.import_wav(source, "New style", first)
            self.assertEqual(first["id"], second["id"])
            self.assertNotEqual(first["version"], second["version"])
            self.assertTrue(store.reference(first).exists())
            self.assertEqual(store.list()[0][0]["version"], second["version"])

    def test_completed_job_and_cancellation_do_not_publish_partial_result(self):
        class FakeEngine:
            device = "cpu"
            def load(self, *_):
                pass
            def prepare(self, *_):
                pass
            def generate(self, _):
                return np.ones(2400, dtype=np.float32) * 0.1, 24000

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = run_job(FakeEngine(), "Hello.", None, None, "CPU", Event(), lambda *_: None, directory)
            self.assertEqual(sf.info(output).frames, 2400)
            self.assertEqual(read_json(next((directory / "jobs").glob("*/job.json")))["state"], "complete")
            cancel = Event()
            def progress(message, *_):
                if "Generating section" in message:
                    cancel.set()
            with self.assertRaises(Cancelled):
                run_job(FakeEngine(), "A short sentence. " * 40, None, None, "CPU", cancel, progress, directory)
            self.assertEqual(len(list((directory / "outputs").glob("*.wav"))), 1)
            states = [read_json(path)["state"] for path in (directory / "jobs").glob("*/job.json")]
            self.assertIn("cancelled", states)


if __name__ == "__main__":
    unittest.main()
