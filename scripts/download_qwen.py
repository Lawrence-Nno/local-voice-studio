"""Explicit online setup only; all inference uses the local snapshot."""
import json
from scripts.download_model import ROOT


def main():
    from huggingface_hub import snapshot_download
    from app.storage import atomic_json
    config = json.loads((ROOT / "qwen-model-spec.json").read_text())
    directory = ROOT / "models" / "qwen3-tts-1.7b"
    snapshot_download(config["repo_id"], revision=config["revision"], local_dir=directory,
                      allow_patterns=["*.json", "*.txt", "*.safetensors", "README.md"], max_workers=2)
    for name in ("model.safetensors", "config.json", "speech_tokenizer/model.safetensors"):
        if not (directory / name).is_file():
            raise RuntimeError("Qwen snapshot is incomplete: " + name)
    atomic_json(directory / "manifest.json", config)
    print("Qwen 1.7B downloaded for offline use.", flush=True)


if __name__ == "__main__":
    main()
