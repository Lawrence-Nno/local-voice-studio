import json
import platform

from app.storage import DATA, atomic_json, configure_runtime


def main():
    configure_runtime()
    import tkinter
    import torch
    result = {"python": platform.python_version(), "windows": platform.platform(),
              "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
              "tk": tkinter.TkVersion, "cuda_available": torch.cuda.is_available()}
    if torch.cuda.is_available():
        sample = torch.arange(16, device="cuda").sum().item()
        props = torch.cuda.get_device_properties(0)
        result.update(gpu=props.name, gpu_vram_gib=props.total_memory / 1024**3,
                      gpu_tensor_test=sample == 120)
    atomic_json(DATA / "diagnostics.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
