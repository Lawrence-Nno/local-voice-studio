import tempfile
import unittest
from pathlib import Path
from threading import Event

import numpy as np
import soundfile as sf

from app.audio_processing import clean_reference, polish_audio, polish_file
from app.generation import run_job
from app.profiles import Profiles
from app.storage import read_json


class ProcessingTests(unittest.TestCase):
    def test_cleanup_preserves_source_and_rejects_too_short_selection(self):
        rate = 24000
        speech = .02 * np.sin(2 * np.pi * 220 * np.arange(rate * 7) / rate)
        audio = np.concatenate((np.zeros(rate), speech, np.zeros(rate)))
        snapshot = audio.copy()
        cleaned = clean_reference(audio, rate, denoise=True)
        np.testing.assert_array_equal(audio, snapshot)
        self.assertTrue(7 < len(cleaned) / rate < 8)
        self.assertTrue(np.isfinite(cleaned).all())
        self.assertLessEqual(np.max(np.abs(cleaned)), .98)
        with self.assertRaises(ValueError):
            clean_reference(audio, rate, start=1, end=5)

    def test_polish_preserves_timing_and_limits_peaks(self):
        rate = 24000
        audio = .9 * np.sin(2 * np.pi * 220 * np.arange(rate * 2) / rate)
        for mode in ("Natural polish", "Brighter speech"):
            polished = polish_audio(audio, rate, mode, 1)
            self.assertEqual(len(polished), len(audio))
            self.assertTrue(np.isfinite(polished).all())
            self.assertLessEqual(np.max(np.abs(polished)), .95001)
        np.testing.assert_allclose(polish_audio(audio, rate, "Original"), audio, atol=1e-7)
        np.testing.assert_allclose(polish_audio(audio, rate, strength=0), audio, atol=1e-7)

    def test_cleanup_replacement_keeps_original_bytes_and_records_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            source = data / "source.wav"
            rate = 24000
            sf.write(source, .05 * np.sin(np.arange(rate * 9) * 2 * np.pi * 220 / rate), rate)
            original_bytes = source.read_bytes()
            profiles = Profiles(data)
            first, _ = profiles.import_wav(source, "Voice")
            second, _ = profiles.import_wav(source, "Voice", first, cleanup=dict(start=1, end=8, trim=False))
            self.assertEqual(second["duration"], 7)
            self.assertTrue(profiles.reference(first).exists())
            self.assertEqual(source.read_bytes(), original_bytes)
            self.assertEqual((profiles.reference(second).parent / second["original"]).read_bytes(), original_bytes)
            self.assertEqual(profiles.list()[0][0]["cleanup"]["start"], 1)
            polished = data / "polished.wav"
            polish_file(source, polished, "Natural polish", .5)
            self.assertEqual(source.read_bytes(), original_bytes)
            self.assertEqual(sf.info(source).frames, sf.info(polished).frames)
            self.assertEqual(read_json(polished.with_suffix(".json"))["mode"], "Natural polish")

    def test_seed_repeats_output_and_passes_sampling_preset(self):
        class FakeEngine:
            device = "cpu"
            def load(self, *_): pass
            def prepare(self, *_): pass
            def generate(self, _, **kwargs):
                self.parameters = kwargs
                return np.random.uniform(-.1, .1, 2400), 24000
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            engine = FakeEngine()
            options = {"preset": "Steady", "seed": 42}
            first = run_job(engine, "Hello.", None, None, "CPU", Event(), lambda *_: None, data, options)
            second = run_job(engine, "Hello.", None, None, "CPU", Event(), lambda *_: None, data, options)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(engine.parameters["temperature"], .65)
            self.assertEqual(read_json(data / "jobs" / second.stem / "job.json")["generation_options"],
                             {**options, "temperature": .65, "repetition_penalty": 1.2})


if __name__ == "__main__":
    unittest.main()
