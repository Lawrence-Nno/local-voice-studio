"""Check native window construction and save an app-only screenshot for layout review."""
import tkinter as tk

from app.storage import DATA, configure_runtime


def main():
    configure_runtime()
    from app.main import configure_dpi
    configure_dpi()
    from app.ui import VoiceApp
    from PIL import ImageGrab
    root = tk.Tk()
    root.geometry("940x740+80+80")
    app = VoiceApp(root)
    root.update()
    root.after(800, root.quit)
    root.mainloop()
    assert app.generate_button.winfo_ismapped()
    assert app.export_button.winfo_ismapped()
    assert app.export_button.winfo_rooty() + app.export_button.winfo_height() <= root.winfo_rooty() + root.winfo_height()
    root.minsize(*root.minsize())
    smallest = root.minsize()
    root.geometry(f"{smallest[0]}x{smallest[1]}")
    root.update()
    for widget in (app.cleanup_button, app.polish_button, app.generate_button, app.export_button):
        assert widget.winfo_rootx() + widget.winfo_width() <= root.winfo_rootx() + root.winfo_width()
        assert widget.winfo_rooty() + widget.winfo_height() <= root.winfo_rooty() + root.winfo_height()
    original_model = app.model_choice.get()
    for model in ("Qwen3-TTS 1.7B Base", "Chatterbox Turbo"):
        app.model_choice.set(model)
        app.update_model_controls()
        root.update()
        qwen = model.startswith("Qwen")
        assert (str(app.test_button["state"]) == "disabled") == qwen
        assert (str(app.transcript_button["state"]) == "normal") == qwen
        app.busy(True)
        assert str(app.models["state"]) == "disabled"
        app.busy(False)
        assert (str(app.test_button["state"]) == "disabled") == qwen
    app.model_choice.set(original_model)
    app.update_model_controls()
    status_label = app.progress.master.winfo_children()[-1]
    assert status_label.winfo_ismapped()
    assert status_label.winfo_rooty() + status_label.winfo_height() <= root.winfo_rooty() + root.winfo_height()
    app.text.insert("1.0", "A short test.")
    root.update()
    assert not app.text.edit_modified()
    assert app.devices.get() in ("Automatic", "NVIDIA GPU", "CPU")
    DATA.mkdir(parents=True, exist_ok=True)
    image = ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(),
                                root.winfo_rootx() + root.winfo_width(),
                                root.winfo_rooty() + root.winfo_height()))
    image.save(DATA / "ui-preview.png")
    root.destroy()
    print("Native UI constructed; controls fit the window. Saved data/ui-preview.png.")


if __name__ == "__main__":
    main()
