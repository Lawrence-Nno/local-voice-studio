"""Build a self-contained Windows x64 folder from the verified local installs."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ignore(_directory, names):
    return [name for name in names if name in ("__pycache__", ".cache", ".git") or name.endswith(".pyc")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-profiles", action="store_true")
    args = parser.parse_args()
    target = ROOT / "dist" / "Local Voice Studio.build"
    if target.exists():
        raise ValueError("Build folder already exists; choose a new build after preserving your existing copy.")
    base = ROOT / ".python" / "cpython-3.11-windows-x86_64-none"
    if shutil.disk_usage(ROOT).free < 20 * 1024**3:
        raise ValueError("Allow 20 GiB free for the two-model portable folder.")
    target.mkdir(parents=True)
    for name, environment in (("turbo", ".venv"), ("qwen", ".venv-qwen")):
        print("Bundling " + name + " runtime and libraries", flush=True)
        runtime = target / "runtime" / name
        shutil.copytree(base, runtime, ignore=ignore)
        shutil.copytree(ROOT / environment / "Lib" / "site-packages", runtime / "Lib" / "site-packages",
                        dirs_exist_ok=True, ignore=ignore)
    print("Bundling app and model weights", flush=True)
    shutil.copytree(ROOT / "app", target / "app", ignore=ignore)
    (target / "scripts").mkdir()
    for name in ("__init__.py", "check_qwen.py", "check_subtitles.py", "check_music.py", "check_recorder.py", "check_editor.py", "check_recording_subtitles.py", "check_converter.py", "check_cleanup.py", "check_join.py", "check_batch.py", "check_effects.py", "check_audio_info.py"):
        source = ROOT / "scripts" / name
        if source.exists():
            shutil.copy2(source, target / "scripts" / name)
    for name in ("chatterbox-turbo", "qwen3-tts-1.7b", "whisper-small"):
        shutil.copytree(ROOT / "models" / name, target / "models" / name, ignore=ignore)
    if args.include_profiles:
        print("Copying your saved voice profiles and preferences", flush=True)
        shutil.copytree(ROOT / "data" / "profiles", target / "data" / "profiles", ignore=ignore)
        shutil.copy2(ROOT / "data" / "settings.json", target / "data" / "settings.json")
    for name in ("model-spec.json", "qwen-model-spec.json", "requirements-lock.txt", "requirements-qwen-lock.txt", "subtitle-model-spec.json"):
        shutil.copy2(ROOT / name, target / name)
    shutil.copy2(ROOT / "packaging" / "Create desktop shortcut.ps1", target)
    shutil.copy2(ROOT / "README.md", target / "README.md")
    (target / "Create desktop shortcut.cmd").write_text(
        '@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Create desktop shortcut.ps1"\r\nif errorlevel 1 pause\r\n')
    compiler = Path("C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe")
    subprocess.run([str(compiler), "/nologo", "/target:winexe", "/platform:x64",
        "/reference:System.Windows.Forms.dll", "/out:" + str(target / "Local Voice Studio.exe"),
        "/win32icon:" + str(ROOT / "app" / "assets" / "local-voice-studio.ico"),
        str(ROOT / "packaging" / "Launcher.cs")], check=True)
    (target / "READ ME.txt").write_text(
        "Local Voice Studio - portable Windows x64 edition\n\n"
        "Double-click Local Voice Studio.exe. No Python installation or online setup is needed.\n"
        "Copy or move this ENTIRE folder to a writable location on Windows 10/11 x64.\n"
        "The EXE alone is not the app: keep runtime, app, and models beside it.\n"
        "Double-click Create desktop shortcut.cmd for convenient access; rerun after moving.\n"
        "Voices, settings, outputs and logs are saved in data inside this folder.\n"
        "Close the app before moving it. Avoid Program Files or other read-only folders.\n"
        "NVIDIA GPU use needs a compatible installed NVIDIA driver; CPU is selectable.\n"
        "Qwen 1.7B was GPU-tested on an RTX 3060 6GB. Other PCs are not yet verified.\n"
        "Model licenses: Chatterbox Turbo MIT; Qwen3-TTS Apache-2.0.\n"
        "Bundled dependency license files are retained in runtime/Lib/site-packages.\n"
        + ("This personal build includes your saved voice recordings and profiles.\n" if args.include_profiles else "This build contains no personal profiles.\n"), encoding="utf-8")
    (target / "portable-build.json").write_text(json.dumps({"platform": "Windows x64",
        "personal_profiles_included": args.include_profiles, "python": "3.11.15",
        "models": ["Chatterbox Turbo", "Qwen3-TTS 1.7B Base"], "subtitle_model": "Whisper Small", "background_music": {"offline": True, "model_required": False, "imported_tracks_bundled": False}}, indent=2))
    print("Portable folder built: " + str(target), flush=True)


if __name__ == "__main__":
    main()
