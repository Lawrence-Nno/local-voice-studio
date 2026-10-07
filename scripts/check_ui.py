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
