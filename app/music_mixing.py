"""Model-free stereo mixing with smooth energy-based music ducking."""
import numpy as np
from scipy.signal import lfilter

RATE = 44100


def envelope(target, previous, frames, rate=RATE):
    seconds = .05 if target < previous else .5
    alpha = np.exp(-1 / (rate * seconds))
    values, state = lfilter([1 - alpha], [1, -alpha], np.full(frames, target), zi=[alpha * previous])
    return values, float(values[-1]) if frames else previous


def mix_block(voice, music, options, offset, total, music_end, threshold, previous):
    voice = np.asarray(voice, dtype=np.float32)
    music = np.asarray(music, dtype=np.float32)
    if voice.shape != music.shape or voice.ndim != 2 or voice.shape[1] != 2:
        raise ValueError("Use equal-length stereo blocks.")
    if not np.isfinite(voice).all() or not np.isfinite(music).all():
        raise ValueError("Audio contains invalid samples.")
    speech = float(np.sqrt(np.mean(voice ** 2))) > threshold and options["voice_gain"] > 0
    target = 1 - options["duck_strength"] if options["duck"] and speech else 1
    duck, previous = envelope(target, previous, len(voice))
    positions = np.arange(offset, offset + len(voice))
    fade_in = max(1, round(options["fade_in"] * RATE))
    fade_out = max(1, round(options["fade_out"] * RATE))
    fade = np.ones(len(voice))
    if options["fade_in"]:
        fade *= np.clip(positions / fade_in, 0, 1)
    if options["fade_out"]:
        fade *= np.clip((music_end - 1 - positions) / fade_out, 0, 1)
    result = voice * options["voice_gain"] + music * (options["music_gain"] * duck * fade)[:, None]
    return result.astype(np.float32), previous
