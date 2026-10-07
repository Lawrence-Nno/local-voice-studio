from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf

from .storage import DATA, atomic_json, read_json


class Profiles:
    def __init__(self, data: Path = DATA):
        self.directory = data / "profiles"
        self.directory.mkdir(parents=True, exist_ok=True)

    def list(self) -> tuple[list[dict], list[str]]:
        profiles, errors = [], []
        for path in sorted(self.directory.glob("*/profile.json")):
            try:
                profile = read_json(path)
                if profile.get("id") != path.parent.name or not profile.get("name"):
                    raise ValueError("Invalid profile metadata")
                if (not isinstance(profile["name"], str)
                        or not isinstance(profile.get("duration"), (int, float))
                        or not 5 < profile["duration"] <= 60
                        or not isinstance(profile.get("version"), str)
                        or not isinstance(profile.get("created"), str)):
                    raise ValueError("Invalid profile metadata. Restore a backup or add a new recording.")
                self.reference(profile)
                profiles.append(profile)
            except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
                errors.append(f"Profile {path.parent.name}: {exc}")
        return profiles, errors

    def reference(self, profile: dict) -> Path:
        identifier = str(profile["id"])
        if str(uuid.UUID(identifier)) != identifier:
            raise ValueError("Invalid profile identifier")
        filename = profile["reference"]
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError("Invalid reference filename")
        path = self.directory / identifier / filename
        if not path.is_file():
            raise ValueError("Reference recording is missing. Replace this recording or restore a backup.")
        return path

    def import_wav(self, source: Path, name: str, replace: dict | None = None, cleanup: dict | None = None) -> tuple[dict, list[str]]:
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("Enter a voice name between 1 and 80 characters.")
        if source.suffix.lower() != ".wav":
            raise ValueError("Choose a WAV recording. Other audio formats are not supported yet.")
        if source.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("Recording is too large. Use a WAV smaller than 100 MB.")
        try:
            info = sf.info(source)
            if not 5 < info.duration <= 60 or not 8000 <= info.samplerate <= 192000:
                raise ValueError("Use a recording longer than 5 seconds and no longer than 60 seconds, at 8–192 kHz.")
            if not 1 <= info.channels <= 2:
                raise ValueError("Use a mono or stereo WAV recording.")
            audio, rate = sf.read(source, dtype="float32", always_2d=True)
        except (RuntimeError, sf.LibsndfileError) as exc:
            raise ValueError("Cannot decode this WAV recording. Try exporting it as a standard PCM WAV.") from exc
        if not np.isfinite(audio).all():
            raise ValueError("Recording contains invalid audio samples.")
        warnings = []
        if np.mean(np.abs(audio) >= 0.999) > 0.001:
            warnings.append("The recording may be clipped. A quieter recording may work better.")
        mono = audio.mean(axis=1)
        peak = float(np.max(np.abs(mono)))
        rms = float(np.sqrt(np.mean(mono * mono)))
        if peak < 0.005 or rms < 0.001:
            raise ValueError("Recording is silent or too quiet. Record clear speech at a higher level.")
        if info.duration > 15:
            warnings.append("The model uses the opening portions of your recording. Put clear speech at the start.")
        if cleanup is None:
            mono *= min(0.95 / peak, 4.0)
        else:
            from .audio_processing import clean_reference
            mono = clean_reference(mono, rate, **cleanup)
        identifier = replace["id"] if replace else str(uuid.uuid4())
        if replace:
            self.reference(replace)
        directory = self.directory / identifier
        directory.mkdir(parents=True, exist_ok=True)
        version = uuid.uuid4().hex
        original = directory / f"original-{version}.wav"
        reference = directory / f"reference-{version}.wav"
        # Versioned files ensure an invalid replacement never overwrites a working reference.
        try:
            shutil.copyfile(source, original)
            sf.write(reference, mono, rate, subtype="PCM_16")
            profile = {
                "id": identifier, "name": name,
                "created": replace["created"] if replace else datetime.now(timezone.utc).isoformat(),
                "updated": datetime.now(timezone.utc).isoformat(),
                "reference": reference.name, "original": original.name,
                "duration": len(mono) / rate, "sample_rate": rate, "version": version,
                "source_duration": info.duration, "cleanup": cleanup,
            }
            atomic_json(directory / "profile.json", profile)
        except Exception:
            original.unlink(missing_ok=True)
            reference.unlink(missing_ok=True)
            raise
        return profile, warnings
