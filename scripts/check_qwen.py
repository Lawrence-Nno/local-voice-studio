"""Real offline GPU smoke test with an existing local profile; no cloud audio."""
import argparse
import time
from threading import Event

from app.storage import DATA, ROOT, atomic_json, configure_runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("qwen", "turbo"), default="qwen")
    args = parser.parse_args()
    configure_runtime()
    from app.profiles import Profiles
    from app.generation import run_job
    from app.qwen_engine import QwenEngine
    from app.engine import SpeechEngine
    profiles = Profiles()
    rows, errors = profiles.list()
    if errors or not rows:
        raise ValueError("A valid saved voice is needed for this test.")
    profile = min(rows, key=lambda p: p["duration"])
    engine = QwenEngine() if args.model == "qwen" else SpeechEngine()
    import soundfile as sf
    start = time.perf_counter()
    try:
        text = "Hello. This is my voice, generated locally on my computer."
        path = run_job(engine, text, profile, profiles.reference(profile), "NVIDIA GPU", Event(),
                       lambda message, *_: print(message, flush=True), options={"preset": "Default", "seed": 42})
        info = sf.info(path)
        report = {"model": args.model, "output": str(path.relative_to(ROOT)), "profile_id": profile["id"],
                  "reference_version": profile["version"], "text": text, "elapsed_seconds": time.perf_counter() - start,
                  "duration_seconds": info.duration, "sample_rate": info.samplerate,
                  "device": engine.device, "metrics": getattr(engine, "metrics", {})}
        warm_start = time.perf_counter()
        warm_path = run_job(engine, text, profile, profiles.reference(profile), "NVIDIA GPU", Event(),
                            lambda message, *_: print(message, flush=True), options={"preset": "Default", "seed": 42})
        report["warm_elapsed_seconds"] = time.perf_counter() - warm_start
        report["warm_output"] = str(warm_path.relative_to(ROOT))
        report["warm_duration_seconds"] = sf.info(warm_path).duration
        report["metrics"] = getattr(engine, "metrics", {})
        atomic_json(DATA / (args.model + "-comparison.json"), report)
        print(report, flush=True)
    finally:
        engine.unload()


if __name__ == "__main__":
    main()
