"""Bounded-memory waveform scanning and non-destructive WAV edits."""
import math
from pathlib import Path

import numpy as np
import soundfile as sf


def scan_audio(path, bins=1000):
    with sf.SoundFile(path) as audio:
        if not len(audio) or audio.channels > 2:
            raise ValueError('Use non-empty mono or stereo audio.')
        if len(audio) / audio.samplerate > 3600:
            raise ValueError('Open a recording up to one hour long.')
        edges = np.linspace(0, len(audio), min(bins, len(audio)) + 1, dtype=np.int64)
        peaks = []
        for first, last in zip(edges[:-1], edges[1:]):
            block = audio.read(int(last - first), dtype='float32', always_2d=True)
            if not np.isfinite(block).all():
                raise ValueError('Audio contains invalid samples.')
            peaks.append((float(block.min()), float(block.max())))
        return {'duration': len(audio) / audio.samplerate, 'rate': audio.samplerate,
                'channels': audio.channels, 'peaks': peaks}


def render_edit(source, destination, start, end, gain=1, fade_in=0, fade_out=0):
    values = (start, end, gain, fade_in, fade_out)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Enter finite numbers for all edit settings.')
    if start < 0 or end <= start or not 0 <= gain <= 2 or min(fade_in, fade_out) < 0:
        raise ValueError('Choose an end after the start, volume from 0 to 200%, and non-negative fades.')
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Save to a new filename to preserve the original audio.')
    temporary = destination.with_suffix('.partial.wav')
    try:
        with sf.SoundFile(source) as audio:
            rate = audio.samplerate
            if end > len(audio) / rate + .000001:
                raise ValueError('Selection ends beyond the audio duration.')
            first, last = round(start * rate), min(len(audio), round(end * rate))
            total = last - first
            if total <= 0:
                raise ValueError('Select at least one audio sample.')
            if max(fade_in, fade_out) > total / rate:
                raise ValueError('Each fade must fit within the selected audio.')
            destination.parent.mkdir(parents=True, exist_ok=True)
            audio.seek(first)
            clipped = False
            with sf.SoundFile(temporary, 'w', samplerate=rate, channels=audio.channels, subtype='PCM_16') as output:
                offset = 0
                while offset < total:
                    block = audio.read(min(65536, total - offset), dtype='float32', always_2d=True)
                    if not len(block):
                        raise ValueError('Source audio changed while editing. Open it again.')
                    if not np.isfinite(block).all():
                        raise ValueError('Audio contains invalid samples.')
                    positions = np.arange(offset, offset + len(block), dtype=np.float64)
                    envelope = np.ones(len(block))
                    if fade_in:
                        envelope *= np.minimum(1, positions / (fade_in * rate))
                    if fade_out:
                        envelope *= np.minimum(1, (total - 1 - positions) / (fade_out * rate))
                    block = block * (gain * envelope[:, None])
                    clipped |= bool(np.max(np.abs(block)) >= 1)
                    output.write(np.clip(block, -1, 1))
                    offset += len(block)
        temporary.replace(destination)
        return {'duration': total / rate, 'clipped': clipped}
    finally:
        temporary.unlink(missing_ok=True)
