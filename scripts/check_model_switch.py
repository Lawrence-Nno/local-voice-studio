"""Verify UI dispatch and model release without repeating GPU inference."""
import time
import tkinter as tk
from unittest.mock import patch

from app.main import configure_dpi
from app.storage import DATA, ROOT, configure_runtime, read_json


def main():
    configure_runtime()
    configure_dpi()
    from app.ui import VoiceApp
    root = tk.Tk()
    root.withdraw()
    app = VoiceApp(root)
    source = ROOT / read_json(DATA / "smoke-test.json")["output"]
    calls, errors = [], []
    class Engine:
        model = None
        def __init__(self, name): self.model_id = name
        def unload(self): calls.append(("unload", self.model_id))
    app.engine = Engine("Chatterbox Turbo")
    def completed(engine, *_args, **_kwargs):
        calls.append(("generate", engine.model_id))
        return source
    with patch("app.qwen_engine.QwenEngine", side_effect=lambda: Engine("Qwen3-TTS 1.7B Base")), \
         patch("app.ui.SpeechEngine", side_effect=lambda: Engine("Chatterbox Turbo")), \
         patch("app.ui.run_job", side_effect=completed), \
         patch.object(app.settings, "update"), \
         patch("app.ui.messagebox.showerror", side_effect=lambda *args: errors.append(args)):
        app.polish_mode.set("Original")
        app.text.insert("1.0", "Hello.")
        for model in ("Qwen3-TTS 1.7B Base", "Chatterbox Turbo"):
            app.model_choice.set(model)
            app.select_model()
            app.generate()
            assert str(app.models["state"]) == "disabled"
            deadline = time.monotonic() + 10
            while (app.worker.is_alive() or str(app.models["state"]) == "disabled") and time.monotonic() < deadline:
                root.update()
            assert not errors, errors
            assert app.engine.model_id == model
            assert app.output == source
            assert str(app.models["state"]) == "readonly"
    assert calls == [("unload", "Chatterbox Turbo"), ("generate", "Qwen3-TTS 1.7B Base"),
                     ("unload", "Qwen3-TTS 1.7B Base"), ("generate", "Chatterbox Turbo")], calls
    root.destroy()
    print("UI dispatch to both engines and release before each model switch passed.")


if __name__ == "__main__":
    main()
