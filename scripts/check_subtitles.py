"""Real offline transcription and saved-script alignment acceptance checks."""
import argparse
import json
import re
import subprocess
from pathlib import Path

from app.storage import ROOT, DATA, read_json, atomic_json
from app.subtitles import parse_srt


def run(request):
    interpreter = ROOT / "runtime/qwen/python.exe"
    if not interpreter.exists():
        interpreter = ROOT / ".venv-qwen/Scripts/python.exe"
    with (DATA / "subtitle-verification.log").open("a", encoding="utf-8") as log:
        process = subprocess.Popen([str(interpreter), "-E", "-s", "-m", "app.subtitle_worker"], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True, encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.close()
            result = None
            for line in process.stdout:
                message = json.loads(line)
                print(message.get("progress", message.get("error", "Complete")), flush=True)
                if "error" in message:
                    raise ValueError(message["error"])
                result = message.get("result", result)
            assert process.wait() == 0 and result is not None
            parse_srt(result["srt"])
            return result
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=("NVIDIA GPU", "CPU"), default="NVIDIA GPU")
    args = parser.parse_args()
    report = read_json(DATA / "turbo-comparison.json")
    audio = ROOT / report["warm_output"]
    directory = DATA / "verification"
    directory.mkdir(parents=True, exist_ok=True)
    import soundfile as sf
    results = {}
    for mode in ("transcribe", "align"):
        request = {"mode": mode, "audio": str(audio), "language": "en", "device": args.device}
        if mode == "align":
            request["sections"] = [{"path": str(audio), "text": report["text"], "duration": sf.info(audio).duration}]
        result = run(request)
        (directory / (mode + ".srt")).write_text(result["srt"], encoding="utf-8")
        print(result["srt"], flush=True)
        if mode == "align":
            expected = report["text"]
            actual = re.sub(r"\s+", " ", " ".join(c["text"] for c in result["cues"])).strip()
            assert expected == actual, (expected, actual)
        results[mode] = result
    atomic_json(DATA / "subtitle-verification.json", results)
    print("Both real subtitle workflows passed.", flush=True)


if __name__ == "__main__":
    main()
