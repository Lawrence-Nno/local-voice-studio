"""Decode and mix in blocks using PyAV; no model, network, or GPU required."""
import contextlib
import json
import sys
from pathlib import Path

from .storage import configure_runtime


def main():
    configure_runtime()
    channel = sys.stdout
    def send(**value):
        channel.write(json.dumps(value) + "\n")
        channel.flush()
    request = json.loads(sys.stdin.readline())
    with contextlib.redirect_stdout(sys.stderr):
        try:
            import av
            import numpy as np
            import soundfile as sf
            from .music_mixing import RATE, mix_block
            work = Path(request["work"])
            work.mkdir(parents=True, exist_ok=True)
            def decode(source, destination):
                energy, frames = 0.0, 0
                with av.open(source) as container, sf.SoundFile(destination, "w", samplerate=RATE,
                        channels=2, subtype="FLOAT") as output:
                    resampler = av.AudioResampler(format="fltp", layout="stereo", rate=RATE)
                    for frame in container.decode(audio=0):
                        for converted in resampler.resample(frame):
                            block = converted.to_ndarray().T
                            if not np.isfinite(block).all():
                                raise ValueError("Audio contains invalid samples.")
                            output.write(block)
                            energy += float(np.sum(block.astype(np.float64) ** 2))
                            frames += len(block)
                    for converted in resampler.resample(None):
                        block = converted.to_ndarray().T
                        output.write(block)
                        energy += float(np.sum(block.astype(np.float64) ** 2))
                        frames += len(block)
                if not frames:
                    raise ValueError("The file contains no decodable audio.")
                return np.sqrt(energy / (frames * 2))
            send(progress="Decoding voice/audio locally")
            rms = decode(request["voice"], work / "voice.wav")
            send(progress="Decoding background music locally")
            decode(request["music"], work / "music.wav")
            options = request["options"]
            threshold = max(.0001, min(.018, rms * .5))
            peak, previous = 0.0, 1.0
            with sf.SoundFile(work / "voice.wav") as voice, sf.SoundFile(work / "music.wav") as music, \
                 sf.SoundFile(work / "raw.wav", "w", samplerate=RATE, channels=2, subtype="FLOAT") as output:
                start = round(options["music_start"] * RATE)
                if start < 0 or start >= len(music):
                    raise ValueError("Music start must be within the music track.")
                total, available = len(voice), len(music) - start
                music_end = total if options["loop"] else min(total, available)
                music.seek(start)
                def read_music(frames):
                    pieces, remaining = [], frames
                    while remaining:
                        position = music.tell()
                        block = music.read(remaining, dtype="float32", always_2d=True)
                        if len(block):
                            if options["loop"]:
                                # Brief loop-edge fades avoid discontinuity clicks.
                                indices = np.arange(position - start, position - start + len(block))
                                edge = np.minimum(np.clip(indices / (RATE * .01), 0, 1),
                                                  np.clip((available - 1 - indices) / (RATE * .01), 0, 1))
                                block *= edge[:, None]
                            pieces.append(block)
                            remaining -= len(block)
                        if remaining and music.tell() == len(music):
                            if options["loop"]:
                                music.seek(start)
                            else:
                                pieces.append(np.zeros((remaining, 2), dtype=np.float32))
                                break
                    return np.concatenate(pieces)
                offset = 0
                for block in voice.blocks(blocksize=4410, dtype="float32", always_2d=True):
                    mixed, previous = mix_block(block, read_music(len(block)), options, offset, total,
                                                music_end, threshold, previous)
                    output.write(mixed)
                    peak = max(peak, float(np.max(np.abs(mixed))))
                    offset += len(block)
                    if offset % RATE < 4410:
                        send(progress=f"Mixing: {offset / RATE:.1f} / {total / RATE:.1f} seconds")
            gain = min(1.0, .98 / peak) if peak else 1.0
            result = work / "finished.wav"
            send(progress="Protecting peaks and writing stereo WAV")
            with sf.SoundFile(work / "raw.wav") as source, sf.SoundFile(result, "w", samplerate=RATE,
                    channels=2, subtype="PCM_16") as output:
                for block in source.blocks(blocksize=65536, dtype="float32", always_2d=True):
                    output.write(block * gain)
            send(result={"temporary_output": str(result), "sample_rate": RATE, "frames": total,
                         "duration": total / RATE, "master_gain": gain, "options": options})
        except Exception as exc:
            import traceback
            traceback.print_exc()
            send(error=str(exc))


if __name__ == "__main__":
    main()
