"""Conservative local audio processing; never modifies source files."""
from __future__ import annotations

import numpy as np
import soundfile as sf
from scipy import signal

POLISH_MODES = ("Original", "Natural polish", "Brighter speech")


def validate_audio(audio):
    audio = np.asarray(audio, dtype=np.float64)
    if audio.ndim != 1 or not len(audio) or not np.isfinite(audio).all():
        raise ValueError("Audio must contain finite mono samples.")
    return audio


def normalize(audio, target_db=-23):
    audio = validate_audio(audio)
    rms = np.sqrt(np.mean(audio**2))
    peak = np.max(np.abs(audio))
    if rms < 1e-8:
        return audio.copy()
    gain = min(10**(target_db / 20) / rms, .95 / max(peak, 1e-8), 10)
    return audio * gain


def clean_reference(audio, rate, *, start=0, end=None, trim=True, normalize_volume=True, denoise=False):
    audio = validate_audio(audio)
    duration = len(audio) / rate
    end = duration if end is None else float(end)
    if not np.isfinite(start) or not np.isfinite(end) or not 0 <= start < end <= duration + .001:
        raise ValueError("Choose a valid start and end time within the recording.")
    result = audio[round(start * rate):round(end * rate)].copy()
    if len(result) / rate <= 5:
        raise ValueError("Select more than 5 seconds of reference audio.")
    if trim:
        size = max(1, round(rate * .02))
        levels = np.array([np.sqrt(np.mean(result[i:i + size]**2)) for i in range(0, len(result), size)])
        active = np.flatnonzero(levels > max(np.max(levels) * .02, 1e-6))
        if len(active):
            margin = round(rate * .15)
            result = result[max(0, active[0] * size - margin):min(len(result), (active[-1] + 1) * size + margin)]
    if len(result) / rate <= 5:
        raise ValueError("The cleaned reference must remain longer than 5 seconds. Expand the selection or disable silence trimming.")
    if denoise:
        # Minimum-energy frames estimate stationary noise; gain floor limits speech damage.
        _, _, spectrum = signal.stft(result, fs=rate, nperseg=1024, noverlap=768)
        power = np.abs(spectrum)**2
        quiet = np.argsort(np.mean(power, axis=0))[:max(1, power.shape[1] // 10)]
        noise = np.median(power[:, quiet], axis=1, keepdims=True)
        gain = np.maximum(.65, np.sqrt(np.maximum(0, 1 - .5 * noise / np.maximum(power, 1e-16))))
        _, restored = signal.istft(spectrum * gain, fs=rate, nperseg=1024, noverlap=768)
        result = restored[:len(result)]
    if normalize_volume:
        result = normalize(result)
    return np.clip(result, -.98, .98).astype(np.float32)


def polish_audio(audio, rate, mode="Natural polish", strength=.5):
    audio = validate_audio(audio)
    if mode not in POLISH_MODES or not np.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError("Invalid audio polish settings.")
    if mode == "Original" or strength == 0:
        return audio.astype(np.float32)
    filtered = signal.sosfilt(signal.butter(2, 65, fs=rate, btype="highpass", output="sos"), audio)
    if mode == "Brighter speech":
        presence = signal.sosfilt(signal.butter(2, (1500, min(4500, rate * .4)), fs=rate,
                                                btype="bandpass", output="sos"), filtered)
        filtered += .25 * presence
    # Mild compression above -12 dBFS, blended with the untreated waveform.
    magnitude = np.abs(filtered)
    threshold = 10**(-12 / 20)
    gain = np.ones_like(magnitude)
    above = magnitude > threshold
    gain[above] = (threshold / magnitude[above])**.25
    processed = normalize(filtered * gain)
    mixed = (1 - strength) * audio + strength * processed
    peak = np.max(np.abs(mixed))
    if peak > .95:
        mixed *= .95 / peak
    return mixed.astype(np.float32)


def polish_file(source, destination, mode, strength):
    audio, rate = sf.read(source, dtype="float32", always_2d=True)
    processed = polish_audio(audio.mean(axis=1), rate, mode, strength)
    temporary = destination.with_suffix(".partial.wav")
    try:
        sf.write(temporary, processed, rate, subtype="PCM_16")
        temporary.replace(destination)
        from .storage import atomic_json
        atomic_json(destination.with_suffix(".json"), {"source": source.name, "mode": mode,
                    "strength": strength, "sample_rate": rate, "duration_seconds": len(processed) / rate})
    finally:
        temporary.unlink(missing_ok=True)
