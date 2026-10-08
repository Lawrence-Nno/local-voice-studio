import unittest
import numpy as np
from app.music_mixing import RATE, mix_block, envelope


class MusicTests(unittest.TestCase):
    def options(self, **values):
        return {"voice_gain": 1, "music_gain": .2, "duck": False, "duck_strength": .75,
                "fade_in": 0, "fade_out": 0, **values}

    def test_muted_music_preserves_voice_and_frame_count(self):
        voice = np.random.default_rng(42).normal(0, .05, (4410, 2)).astype(np.float32)
        result, _ = mix_block(voice, np.ones_like(voice), self.options(music_gain=0), 0, len(voice), len(voice), .01, 1)
        np.testing.assert_array_equal(result, voice)

    def test_ducking_lowers_music_and_releases_smoothly(self):
        low, last = envelope(.25, 1, RATE)
        high, _ = envelope(1, last, RATE)
        self.assertGreater(low[0], low[-1])
        self.assertAlmostEqual(low[-1], .25, places=5)
        self.assertLess(high[0], high[-1])
        self.assertLess(high[-1], 1)
        music = np.full((4410, 2), .2, dtype=np.float32)
        voice = np.full_like(music, .1)
        plain, _ = mix_block(voice, music, self.options(), 0, 4410, 4410, .01, 1)
        ducked, _ = mix_block(voice, music, self.options(duck=True), 0, 4410, 4410, .01, .25)
        self.assertLess(float(ducked.mean()), float(plain.mean()))

    def test_music_fades_do_not_fade_voice(self):
        voice = np.full((RATE, 2), .1, dtype=np.float32)
        music = np.full_like(voice, .2)
        result, _ = mix_block(voice, music, self.options(fade_in=.2, fade_out=.2), 0, RATE, RATE, .01, 1)
        np.testing.assert_allclose(result[0], voice[0])
        np.testing.assert_allclose(result[-1], voice[-1])
        self.assertGreater(float(result[RATE // 2, 0]), .1)

    def test_invalid_audio_is_rejected(self):
        with self.assertRaises(ValueError):
            mix_block(np.full((2, 2), np.nan), np.zeros((2, 2)), self.options(), 0, 2, 2, .01, 1)


if __name__ == "__main__":
    unittest.main()
