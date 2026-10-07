"""Online setup only. Runtime must never import this module."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["HF_HOME"] = str(ROOT / ".cache" / "huggingface")
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("TRANSFORMERS_OFFLINE", None)


def main():
    from huggingface_hub import snapshot_download
    from app.engine import REQUIRED
    from app.storage import atomic_json
    config = json.loads((ROOT / "model-spec.json").read_text(encoding="utf-8"))
    directory = ROOT / "models" / "chatterbox-turbo"
    snapshot_download(repo_id=config["repo_id"], revision=config["revision"],
                      local_dir=directory, allow_patterns=[*REQUIRED, "README.md"], max_workers=2)
    missing = [name for name in REQUIRED if not (directory / name).is_file()]
    if missing:
        raise RuntimeError("Model snapshot is incomplete: " + ", ".join(missing))
    atomic_json(directory / "manifest.json", config)
    print("Model downloaded. Runtime can now load it offline.", flush=True)


if __name__ == "__main__":
    main()
