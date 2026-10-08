"""Bounded-memory playback with position based on the audio device clock."""
import sounddevice as sd
import soundfile as sf


class WaveformPlayback:
    def __init__(self):
        self.stream = self.file = None
        self.path = None
        self.offset = self.cursor = 0.0
        self.rate = self.frames = 0
        self.anchor_time = None
        self.anchor_frame = 0
        self.playing = False
        self.error = None

    @property
    def duration(self):
        return self.frames / self.rate if self.rate else 0

    @property
    def position(self):
        if self.playing and self.stream and self.anchor_time is not None:
            elapsed = max(0, self.stream.time - self.anchor_time)
            return min(self.duration, self.anchor_frame / self.rate + elapsed)
        return self.cursor

    def start(self, path, offset=0.0, position=0.0):
        self.stop()
        self.path, self.offset = path, offset
        self.error = None
        try:
            self.file = sf.SoundFile(path)
            self.rate, self.frames = self.file.samplerate, len(self.file)
            self.cursor = max(0, min(position, self.duration))
            self.file.seek(round(self.cursor * self.rate))
            self.anchor_time = None
            self.stream = sd.OutputStream(samplerate=self.rate, channels=self.file.channels,
                                          dtype='float32', blocksize=1024, callback=self.callback)
            self.playing = True
            self.stream.start()
        except Exception:
            self.stop()
            raise

    def callback(self, output, frames, timing, status):
        try:
            start = self.file.tell()
            audio = self.file.read(frames, dtype='float32', always_2d=True)
            output.fill(0)
            output[:len(audio)] = audio
            # Publish a coherent frame/time pair before signalling it is available.
            if self.anchor_time is None:
                self.anchor_frame = start
                self.anchor_time = timing.outputBufferDacTime
            if len(audio) < frames:
                raise sd.CallbackStop()
        except sd.CallbackStop:
            raise
        except Exception as exc:
            self.error = str(exc)
            output.fill(0)
            raise sd.CallbackAbort()

    def pause(self):
        position = self.position
        path, offset = self.path, self.offset
        self.stop()
        self.path, self.offset = path, offset
        self.cursor = position

    def resume(self):
        if self.path:
            self.start(self.path, self.offset, self.cursor)

    def seek(self, position):
        position = max(0, min(position, self.duration))
        if self.playing:
            self.start(self.path, self.offset, position)
        else:
            self.cursor = position

    def refresh(self):
        if self.playing and self.stream and not self.stream.active:
            path, offset = self.path, self.offset
            self.stop()
            self.path, self.offset = path, offset
            self.cursor = self.duration

    def stop(self):
        self.playing = False
        if self.stream:
            try:
                self.stream.abort()
            finally:
                self.stream.close()
                self.stream = None
        if self.file:
            self.file.close()
            self.file = None
        self.anchor_time = None
        self.cursor = 0.0
        self.path = None
        self.offset = 0.0
