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
    app.model_choice.set("Chatterbox Turbo")
    app.update_model_controls()
    errors = []
    # Engine inference is validated separately. Here a completed real sample isolates UI job handling.
    def completed_job(_engine, _text, _profile, _reference, _device, _cancel, progress, **_kwargs):
        progress("Verifying background UI job")
        return source
    with patch.object(app.settings, "update"), patch("app.ui.run_job", side_effect=completed_job), patch("app.ui.messagebox.showerror", side_effect=lambda *args: errors.append(args)):
        app.polish_mode.set("Original")
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
        original_hash = hashlib.sha256(source.read_bytes()).digest()
        app.polish_mode.set("Natural polish")
        app.apply_polish()
        deadline = time.monotonic() + 10
        while app.polished_output is None and not errors and time.monotonic() < deadline:
            root.update()
        assert not errors, errors
        assert app.polished_output and app.polished_output.is_file()
        assert app.selected_output() == app.polished_output
        assert hashlib.sha256(source.read_bytes()).digest() == original_hash
        target = DATA / "verification" / "ui-polished-export.wav"
        with patch("app.ui.filedialog.asksaveasfilename", return_value=str(target)):
            app.export()
        assert target.read_bytes() == app.polished_output.read_bytes()
        with patch("app.ui.filedialog.asksaveasfilename", return_value=str(source)):
            app.export()
        assert errors and "preserve" in errors[-1][1]
        errors.clear()
        assert hashlib.sha256(source.read_bytes()).digest() == original_hash
        with patch("app.ui.polish_file", side_effect=RuntimeError("Simulated polish failure")):
            app.apply_polish()
            deadline = time.monotonic() + 10
            while not errors and time.monotonic() < deadline:
                root.update()
            assert errors and "Simulated polish failure" in errors[-1][1]
            errors.clear()
        assert app.output == source
        assert hashlib.sha256(source.read_bytes()).digest() == original_hash
        app.output_version.set("Original")
        assert app.selected_output() == source
    root.destroy()
    print("UI transitions, original/polished selection, byte-identical exports, and Windows playback API passed.")


if __name__ == "__main__":
    main()
