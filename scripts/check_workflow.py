"""Verify UI worker transitions and export without adding a personal voice profile."""
import hashlib
import time
import tkinter as tk
import winsound
from unittest.mock import patch

from app.main import configure_dpi
from app.storage import DATA, ROOT, configure_runtime, read_json


def main():
    configure_runtime()
    configure_dpi()
    from app.ui import VoiceApp
    report = read_json(DATA / "smoke-test.json")
    source = ROOT / report["output"]
    root = tk.Tk()
    root.withdraw()
    app = VoiceApp(root)
    errors = []
    # Engine inference is validated separately. Here a completed real sample isolates UI job handling.
    def completed_job(_engine, _text, _profile, _reference, _device, _cancel, progress):
        progress("Verifying background UI job")
        return source
    with patch("app.ui.run_job", side_effect=completed_job), patch("app.ui.messagebox.showerror", side_effect=lambda *args: errors.append(args)):
        app.generate(generic=True)
        assert str(app.generate_button["state"]) == "disabled"
        deadline = time.monotonic() + 10
        heartbeats = 0
        while app.output is None and not errors and time.monotonic() < deadline:
            root.update()
            heartbeats += 1
        assert not errors, errors
        assert app.output == source
        assert heartbeats > 0
        assert str(app.generate_button["state"]) == "normal"
        assert str(app.play_button["state"]) == "normal"
        target = DATA / "verification" / "ui-export.wav"
        with patch("app.ui.filedialog.asksaveasfilename", return_value=str(target)):
            app.export()
        assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
        app.play()
        winsound.PlaySound(None, 0)
        assert not errors, errors
    root.destroy()
    print("UI background transitions passed; exported WAV is byte-identical; Windows playback API accepted the WAV.")


if __name__ == "__main__":
    main()
