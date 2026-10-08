"""Update the existing personal portable copy without touching its data."""
import json
import shutil
import subprocess
from pathlib import Path
from scripts.build_portable import ROOT, ignore


def main():
    target = ROOT / "dist" / "Local Voice Studio"
    if not (target / "Local Voice Studio.exe").is_file():
        raise ValueError("Build the portable app first.")
    shutil.copytree(ROOT / "app", target / "app", dirs_exist_ok=True, ignore=ignore)
    # Copy installed distributions, including PyAV's bundled media DLLs and licenses.
    code = "import importlib.metadata,json; print(json.dumps([str(f) for n in ['faster-whisper','ctranslate2','av'] for f in importlib.metadata.distribution(n).files]))"
    files = json.loads(subprocess.check_output([str(ROOT / ".venv-qwen/Scripts/python.exe"), "-c", code], text=True))
    source = (ROOT / ".venv-qwen/Lib/site-packages").resolve()
    destination = target / "runtime/qwen/Lib/site-packages"
    for relative in files:
        path = (source / relative).resolve()
        if not path.is_relative_to(source) or not path.is_file() or path.suffix == ".pyc":
            continue
        copy = destination / path.relative_to(source)
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copy)
    shutil.copytree(ROOT / "models/whisper-small", target / "models/whisper-small", dirs_exist_ok=True, ignore=ignore)
    for name in ("subtitle-model-spec.json", "requirements-qwen-lock.txt"):
        shutil.copy2(ROOT / name, target / name)
    shutil.copy2(ROOT / "scripts/check_subtitles.py", target / "scripts/check_subtitles.py")
    manifest = target / "portable-build.json"
    value = json.loads(manifest.read_text())
    value["subtitle_model"] = "Whisper Small"
    value["subtitle_workflows"] = ["import audio transcription", "generated saved-script alignment"]
    manifest.write_text(json.dumps(value, indent=2), encoding="utf-8")
    note = target / "READ ME.txt"
    text = note.read_text(encoding="utf-8")
    if "Audio to subtitles tab" not in text:
        text += "\nAudio to subtitles tab: import audio for transcription, or align the saved script of newly generated speech. Review and export UTF-8 SRT. Older outputs can be transcribed.\n"
        note.write_text(text, encoding="utf-8")
    print("Portable app updated with both subtitle workflows. Personal data preserved.")


if __name__ == "__main__":
    main()
