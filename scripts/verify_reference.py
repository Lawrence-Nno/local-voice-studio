"""Exercise saved-reference generation with a synthetic voice, never the user's voice."""
import socket
from pathlib import Path
from threading import Event

from app.storage import DATA, atomic_json, configure_runtime, read_json


def main():
    configure_runtime()
    def blocked(*_args, **_kwargs):
        raise RuntimeError("Network access is forbidden during reference validation")
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    from app.engine import SpeechEngine
    from app.generation import run_job
    from app.profiles import Profiles
    from app.storage import ROOT, Settings
    import torch
    smoke = read_json(DATA / "smoke-test.json")
    if not smoke:
        raise ValueError("Run scripts.smoke_test first to create a synthetic reference.")
    directory = DATA / "verification"
    profiles = Profiles(directory)
    profile, warnings = profiles.import_wav(ROOT / smoke["output"], "Synthetic verification voice")
    Settings(directory).update(selected_profile=profile["id"])
    restored = Profiles(directory)
    rows, errors = restored.list()
    assert not errors
    selected = Settings(directory).values["selected_profile"]
    profile = next(row for row in rows if row["id"] == selected)
    engine = SpeechEngine()
    device = "NVIDIA GPU" if torch.cuda.is_available() else "CPU"
    text = ("This uses a saved synthetic reference recording to verify the local voice profile workflow. "
            "It does not test resemblance to your voice. The application processes longer text in short sections. "
            "Each section is generated separately and then joined into a completed audio file.")
    output = run_job(engine, text, profile, restored.reference(profile), device, Event(),
                     lambda message, *_: print(message, flush=True), directory)
    metadata = read_json(directory / "jobs" / output.stem / "job.json")
    report = {"synthetic_reference": True, "user_voice_similarity_tested": False,
              "profile_restart_verified": True, "device": engine.device,
              "output": str(output.relative_to(ROOT)), "warnings": warnings,
              "sections": metadata["sections"], "duration_seconds": metadata["duration_seconds"],
              "elapsed_seconds": metadata["elapsed_seconds"], "python_socket_connections_blocked": True}
    atomic_json(DATA / "reference-test.json", report)
    print(report, flush=True)


if __name__ == "__main__":
    main()
