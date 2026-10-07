from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MODEL = ROOT / "models" / "chatterbox-turbo"


def configure_runtime() -> None:
    # Set these before importing any model/download libraries.
    for key, value in {
        "HF_HOME": str(ROOT / ".cache" / "huggingface"),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "NUMBA_CACHE_DIR": str(ROOT / ".cache" / "numba"),
        "TORCH_HOME": str(ROOT / ".cache" / "torch"),
    }.items():
        os.environ[key] = value


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return {} if default is None else default.copy()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Expected an object")
        return value
    except (ValueError, OSError) as exc:
        raise ValueError(f"Cannot read {path.name}. Restore it from backup or repair the file.") from exc


class Settings:
    def __init__(self, data: Path = DATA):
        self.path = data / "settings.json"
        self.values = read_json(self.path, {"selected_profile": None, "device": "Automatic"})

    def update(self, **values) -> None:
        updated = {**self.values, **values}
        atomic_json(self.path, updated)
        self.values = updated
