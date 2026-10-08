import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from app.audio_editor import render_edit, scan_audio


class EditorTests(unittest.TestCase):
    def test_trim_preserves_channels_samples_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/'source.wav', Path(directory)/'edit.wav'
            audio = np.column_stack((np.linspace(-.5, .5, 2000), np.linspace(.3, -.3, 2000)))
            sf.write(source, audio, 1000, subtype='PCM_16')
            original = source.read_bytes()
            render_edit(source, target, .5, 1.5)
            result, rate = sf.read(target)
            decoded, _ = sf.read(source)
            np.testing.assert_array_equal(result, decoded[500:1500])
            self.assertEqual(rate, 1000)
            self.assertEqual(source.read_bytes(), original)

    def test_fades_gain_and_invalid_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/'source.wav', Path(directory)/'edit.wav'
            sf.write(source, np.full(1000, .25), 1000, subtype='PCM_16')
            render_edit(source, target, 0, 1, 2, .1, .1)
            result, _ = sf.read(target)
            self.assertEqual(result[0], 0)
            self.assertEqual(result[-1], 0)
            self.assertAlmostEqual(result[500], .5, places=4)
            previous = target.read_bytes()
            for args in ((0, 2), (.5, .1), (float('nan'), 1)):
                with self.assertRaises(ValueError):
                    render_edit(source, target, *args)
                self.assertEqual(target.read_bytes(), previous)
            with self.assertRaises(ValueError):
                render_edit(source, source, 0, 1)

    def test_scan_retains_transient_peaks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'source.wav'
            audio = np.zeros(5000)
            audio[2048] = .9
            sf.write(path, audio, 1000)
            info = scan_audio(path, 100)
            self.assertEqual(len(info['peaks']), 100)
            self.assertGreater(max(high for low, high in info['peaks']), .89)


if __name__ == '__main__':
    unittest.main()
