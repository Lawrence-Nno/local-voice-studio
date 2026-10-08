"""Streaming microphone capture; no models or network required."""
import queue
import threading
import uuid

import numpy as np
import soundfile as sf

from .storage import DATA


class Recorder:
    def __init__(self):
        self.stop = threading.Event()
        self.paused = threading.Event()
        self.events = queue.Queue()
        self.worker = None
        self.seconds = self.level = 0

    def active(self):
        return self.worker is not None and self.worker.is_alive()

    def start(self, device, rate):
        if self.active():
            raise RuntimeError("A recording is already running.")
        self.stop.clear()
        self.paused.clear()
        self.seconds = self.level = 0
        self.worker = threading.Thread(target=self.capture, args=(device, rate), daemon=True)
        self.worker.start()

    def capture(self, device, rate):
        import sounddevice as sd
        directory = DATA / "recordings"
        path = directory / (uuid.uuid4().hex + ".wav")
        temporary = path.with_suffix(".partial.wav")
        frames = 0
        warning = False
        try:
            directory.mkdir(parents=True, exist_ok=True)
            with sd.InputStream(device=device, samplerate=rate, channels=1, dtype="float32") as stream:
                with sf.SoundFile(temporary, mode="w", samplerate=rate, channels=1, subtype="PCM_16") as output:
                    while not self.stop.is_set():
                        audio, overflow = stream.read(max(1, int(rate / 10)))
                        warning |= overflow
                        if self.paused.is_set():
                            self.level = 0
                            continue
                        output.write(audio)
                        frames += len(audio)
                        self.seconds = frames / rate
                        self.level = float(np.max(np.abs(audio))) if len(audio) else 0
                        if self.seconds >= 3600:
                            self.stop.set()
            if not frames:
                raise ValueError("No audio was recorded. Start a new take and wait before stopping.")
            temporary.replace(path)
            self.events.put(("complete", (path, warning)))
        except Exception as exc:
            self.events.put(("error", str(exc)))
        finally:
            temporary.unlink(missing_ok=True)
            self.level = 0
