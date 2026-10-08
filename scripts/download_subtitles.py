"""Online subtitle-model setup; runtime does not download weights."""
import json
from scripts.download_model import ROOT


def main():
    from huggingface_hub import snapshot_download
    from app.storage import atomic_json
    config = json.loads((ROOT / "subtitle-model-spec.json").read_text())
    directory = ROOT / "models" / "whisper-small"
    snapshot_download(config["repo_id"], revision=config["revision"], local_dir=directory,
                      allow_patterns=["model.bin", "*.json", "*.txt", "README.md"], max_workers=2)
    if not (directory / "model.bin").is_file():
        raise ValueError("Subtitle model download is incomplete.")
    atomic_json(directory / "manifest.json", config)
    print("Subtitle model downloaded for offline use.", flush=True)


if __name__ == "__main__":
    main()
