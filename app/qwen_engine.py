"""Engine adapter; dependency isolation keeps Chatterbox's runtime intact."""
import json
import subprocess
import uuid

from .storage import DATA, ROOT


class QwenEngine:
    model_id = "Qwen3-TTS 1.7B Base"

    def __init__(self):
        self.directory = ROOT / "models" / "qwen3-tts-1.7b"
        self.model = None
        self.device = None
        self.transcript = ""
        self.log = None
        self.metrics = {}

    def request(self, operation, **values):
        self.model.stdin.write(json.dumps({"operation": operation, **values}) + "\n")
        self.model.stdin.flush()
        line = self.model.stdout.readline()
        if not line:
            raise RuntimeError("Qwen worker stopped. See data/qwen-worker.log for details.")
        result = json.loads(line)
        if not result["ok"]:
            raise RuntimeError(result["error"])
        return result

    def load(self, requested, progress):
        interpreter = ROOT / ".venv-qwen" / "Scripts" / "python.exe"
        if not interpreter.is_file() or not (self.directory / "manifest.json").is_file():
            raise ValueError("Qwen is not installed. Run setup-qwen.ps1 while online.")
        import torch
        device = "cuda" if requested != "CPU" and torch.cuda.is_available() else "cpu"
        if requested == "NVIDIA GPU" and device != "cuda":
            raise ValueError("CUDA is unavailable. Select CPU explicitly.")
        if self.model is not None and self.device == device and self.model.poll() is None:
            return
        self.unload()
        DATA.mkdir(parents=True, exist_ok=True)
        self.log = (DATA / "qwen-worker.log").open("a", encoding="utf-8")
        self.model = subprocess.Popen([str(interpreter), "-m", "app.qwen_worker"], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True,
            encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
        progress("Loading Qwen3-TTS 1.7B on " + device + "; first load may take a while")
        self.request("load", directory=str(self.directory), device=device)
        self.device = device

    def prepare(self, reference):
        if reference is None:
            raise ValueError("Qwen Base needs your reference recording; it has no built-in test voice.")
        self.request("prepare", reference=str(reference), transcript=self.transcript)

    def set_seed(self, seed):
        self.request("seed", seed=seed)

    def generate(self, text, temperature=.8, repetition_penalty=1.2):
        import numpy as np
        directory = DATA / "worker-audio"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (uuid.uuid4().hex + ".npz")
        try:
            self.metrics = self.request("generate", text=text, temperature=temperature,
                repetition_penalty=repetition_penalty, output=str(path))
            with np.load(path) as result:
                return result["audio"].copy().reshape(-1), int(result["rate"])
        finally:
            path.unlink(missing_ok=True)

    def unload(self):
        if self.model is not None:
            self.model.terminate()
            try:
                self.model.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.model.kill()
                self.model.wait()
            self.model.stdin.close()
            self.model.stdout.close()
        self.model = None
        self.device = None
        if self.log is not None:
            self.log.close()
            self.log = None
