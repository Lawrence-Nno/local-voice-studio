from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

import numpy as np
import soundfile as sf

from .storage import DATA, atomic_json, read_json


class Cancelled(Exception):
    pass


def chunk_text(text: str, limit: int = 240) -> list[str]:
    text = " ".join(text.split())
    if not text:
        raise ValueError("Enter some text first.")
    if len(text) > 20000:
        raise ValueError("Use no more than 20,000 characters per generation.")
    chunks = []
    while len(text) > limit:
        prefix = text[:limit + 1]
        boundaries = list(re.finditer(r"[.!?](?:[\"')])?\s+", prefix))
        split = boundaries[-1].end() if boundaries else prefix.rfind(" ")
        if split <= 0:
            split = limit
        chunks.append(text[:split].strip())
        text = text[split:].lstrip()
    if text:
        chunks.append(text)
    return chunks


def run_job(engine, text: str, profile: dict | None, reference: Path | None,
            device: str, cancel: Event, progress, data: Path = DATA) -> Path:
    chunks = chunk_text(text)
    job_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    directory = data / "jobs" / job_id
    directory.mkdir(parents=True)
    outputs = data / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    metadata = {"id": job_id, "state": "loading", "created": datetime.now(timezone.utc).isoformat(),
                "profile_id": profile["id"] if profile else None,
                "profile_version": profile["version"] if profile else None,
                "generic_test": profile is None, "sections": len(chunks), "completed": 0}
    atomic_json(directory / "job.json", metadata)
    temporary = outputs / (job_id + ".partial.wav")
    started = time.perf_counter()
    try:
        if cancel.is_set():
            raise Cancelled()
        engine.load(device, progress)
        progress(f"Preparing {'saved voice' if profile else 'generic test voice'} on {engine.device}")
        engine.prepare(reference)
        paths, rate = [], None
        for index, chunk in enumerate(chunks, 1):
            if cancel.is_set():
                raise Cancelled()
            progress(f"Generating section {index} of {len(chunks)} on {engine.device}", index - 1, len(chunks))
            audio, section_rate = engine.generate(chunk)
            if not len(audio) or not np.isfinite(audio).all():
                raise ValueError("The model returned invalid audio. Try a shorter section or a different recording.")
            if rate is not None and rate != section_rate:
                raise ValueError("The model returned inconsistent sample rates.")
            rate = section_rate
            path = directory / f"section-{index:04d}.wav"
            sf.write(path, audio, rate, subtype="PCM_16")
            paths.append(path)
            metadata.update(state="generating", completed=index)
            atomic_json(directory / "job.json", metadata)
        if cancel.is_set():
            raise Cancelled()
        progress("Assembling WAV", len(chunks), len(chunks))
        frames = 0
        with sf.SoundFile(temporary, "w", samplerate=rate, channels=1, subtype="PCM_16") as target:
            for index, path in enumerate(paths):
                if cancel.is_set():
                    raise Cancelled()
                with sf.SoundFile(path) as source:
                    for block in source.blocks(blocksize=65536):
                        target.write(block)
                        frames += len(block)
                if index < len(paths) - 1:
                    pause = np.zeros(int(rate * 0.18), dtype=np.float32)
                    target.write(pause)
                    frames += len(pause)
        if cancel.is_set():
            raise Cancelled()
        result = outputs / (job_id + ".wav")
        temporary.replace(result)
        manifest = read_json(engine.directory / "manifest.json") if hasattr(engine, "directory") else {}
        metadata.update(state="complete", output=result.name, sample_rate=rate,
                        duration_seconds=frames / rate, elapsed_seconds=time.perf_counter() - started,
                        device=engine.device, model_revision=manifest.get("revision"))
        atomic_json(directory / "job.json", metadata)
        return result
    except Cancelled:
        metadata.update(state="cancelled")
        atomic_json(directory / "job.json", metadata)
        raise
    except Exception:
        metadata.update(state="failed")
        atomic_json(directory / "job.json", metadata)
        raise
    finally:
        temporary.unlink(missing_ok=True)
