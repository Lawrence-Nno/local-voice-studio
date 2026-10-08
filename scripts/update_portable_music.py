"""Update app code only; never copy imported tracks or alter portable user data."""
import json
import shutil
from scripts.build_portable import ROOT, ignore


def main():
    target = ROOT / "dist" / "Local Voice Studio"
    if not (target / "Local Voice Studio.exe").is_file():
        raise ValueError("Build the portable app first.")
    if not (target / "runtime/qwen/Lib/site-packages/av").is_dir():
        raise ValueError("Update the portable subtitle dependencies first; mixing needs PyAV.")
    shutil.copytree(ROOT / "app", target / "app", dirs_exist_ok=True, ignore=ignore)
    shutil.copy2(ROOT / "scripts/check_music.py", target / "scripts/check_music.py")
    manifest = target / "portable-build.json"
    value = json.loads(manifest.read_text())
    value["background_music"] = {"offline": True, "model_required": False, "imported_tracks_bundled": False}
    manifest.write_text(json.dumps(value, indent=2), encoding="utf-8")
    note = target / "READ ME.txt"
    text = note.read_text(encoding="utf-8")
    if "Background music tab" not in text:
        text += "\nBackground music tab: import voice/audio and licensed music, adjust levels/ducking/loops/fades, preview and export a separate stereo WAV. Voice timing is preserved. No music tracks are bundled.\n"
        note.write_text(text, encoding="utf-8")
    print("Portable app updated with background music. Data preserved; no imported tracks copied.")


if __name__ == "__main__":
    main()
