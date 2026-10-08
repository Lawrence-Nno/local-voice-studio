import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import soundfile as sf
from app.waveform_playback import WaveformPlayback


class FakeStream:
    def __init__(self, **kwargs):
        self.callback = kwargs['callback']
        self.time = 10.0
        self.active = False
    def start(self): self.active = True
    def abort(self): self.active = False
    def close(self): pass


class PlaybackTests(unittest.TestCase):
    def test_device_clock_pause_seek_finish_and_cleanup(self):
        with tempfile.TemporaryDirectory() as folder, patch('app.waveform_playback.sd.OutputStream', FakeStream):
            path = Path(folder)/'audio.wav'
            sf.write(path, np.zeros((16000, 2)), 8000)
            player = WaveformPlayback()
            player.start(path, offset=3, position=.5)
            output = np.ones((1024,2), dtype=np.float32)
            player.callback(output, 1024, SimpleNamespace(outputBufferDacTime=10.1), None)
            self.assertAlmostEqual(player.position,.5)
            player.stream.time=10.6
            self.assertAlmostEqual(player.position,1)
            player.pause()
            self.assertEqual(player.position,1)
            self.assertIsNone(player.file)
            player.resume()
            self.assertEqual(player.file.tell(),8000)
            player.seek(.25)
            self.assertEqual(player.file.tell(),2000)
            player.stream.active=False
            player.refresh()
            self.assertEqual(player.position,2)
            self.assertEqual(player.offset,3)
            player.stop()
            self.assertIsNone(player.path)
            self.assertIsNone(player.stream)

    def test_open_failure_releases_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'audio.wav'
            sf.write(path,np.zeros(8000),8000)
            player=WaveformPlayback()
            with patch('app.waveform_playback.sd.OutputStream',side_effect=RuntimeError('No device')):
                with self.assertRaises(RuntimeError): player.start(path)
            self.assertIsNone(player.file)
            self.assertFalse(player.playing)
