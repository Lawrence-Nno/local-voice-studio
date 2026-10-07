"""Generic speech validation, explicitly not a test of the user's voice."""
import json
import socket
from threading import Event

from app.storage import DATA, configure_runtime


def main():
    configure_runtime()
    # Block Python socket connections even if this machine is online.
    def blocked(*_args, **_kwargs):
        raise RuntimeError("Network access is forbidden during offline smoke testing")
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    from app.engine import SpeechEngine
    from app.generation import run_job
    from app.storage import atomic_json
    import torch
    engine = SpeechEngine()
    device = "NVIDIA GPU" if torch.cuda.is_available() else "CPU"
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    result = run_job(engine, "Hello. This is a generic test of offline speech generation, not a clone of your voice.",
                     None, None, device, Event(), lambda message, *_: print(message, flush=True))
    import soundfile as sf
    info = sf.info(result)
    report = {"generic_test": True, "user_voice_similarity_tested": False, "device": engine.device,
              "output": str(result.relative_to(DATA.parent)), "sample_rate": info.samplerate,
              "duration_seconds": info.duration, "python_socket_connections_blocked": True}
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        report.update(peak_allocated_gib=torch.cuda.max_memory_allocated() / 1024**3,
                      peak_reserved_gib=torch.cuda.max_memory_reserved() / 1024**3,
                      device_used_gib=(total - free) / 1024**3)
    atomic_json(DATA / "smoke-test.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
