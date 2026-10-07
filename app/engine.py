from __future__ import annotations

from pathlib import Path

from .storage import MODEL, configure_runtime

REQUIRED = ("ve.safetensors", "t3_turbo_v1.safetensors", "s3gen_meanflow.safetensors",
            "conds.pt", "vocab.json", "merges.txt", "tokenizer_config.json",
            "special_tokens_map.json", "added_tokens.json")


class SpeechEngine:
    def __init__(self, model_directory: Path = MODEL):
        self.directory = model_directory
        self.model = None
        self.device = None

    def load(self, requested: str, progress) -> None:
        configure_runtime()
        missing = [name for name in REQUIRED if not (self.directory / name).is_file()]
        if missing:
            raise ValueError("Model files are missing. Run setup.ps1 while online, then launch again.")
        import torch
        device = "cpu"
        if requested != "CPU":
            if torch.cuda.is_available():
                try:
                    torch.ones(1, device="cuda").cpu()
                    device = "cuda"
                except RuntimeError as exc:
                    raise RuntimeError("GPU initialization failed. Select CPU explicitly or repair the CUDA runtime.") from exc
            elif requested == "NVIDIA GPU":
                raise ValueError("CUDA is unavailable. Select CPU or rerun setup to check your GPU.")
        if self.model is not None and self.device == device:
            return
        self.unload()
        progress("Loading model on " + (torch.cuda.get_device_name(0) if device == "cuda" else "CPU"))
        from chatterbox.tts_turbo import ChatterboxTurboTTS
        self.model = ChatterboxTurboTTS.from_local(self.directory, device=device)
        self.device = device

    def unload(self) -> None:
        self.model = None
        self.device = None
        import gc
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def prepare(self, reference: Path | None) -> None:
        import torch
        with torch.inference_mode():
            if reference is not None:
                self.model.prepare_conditionals(str(reference))
            elif self.model.conds is None:
                raise ValueError("The generic test voice is unavailable. Import a recording first.")

    def generate(self, text: str, temperature=.8, repetition_penalty=1.2):
        import torch
        tokens = self.model.tokenizer(text, return_tensors="pt").input_ids.shape[-1]
        if tokens > 200:
            raise ValueError("This section has too many tokens. Use shorter sentences.")
        with torch.inference_mode():
            audio = self.model.generate(text, temperature=temperature, repetition_penalty=repetition_penalty)
        return audio.detach().cpu().numpy().reshape(-1), self.model.sr
