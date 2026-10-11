import tkinter as tk
from tkinter import messagebox

from .storage import configure_runtime


def configure_dpi():
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def main():
    configure_runtime()
    configure_dpi()
    root = tk.Tk()
    root.withdraw()
    try:
        from .ui import VoiceApp
        app = VoiceApp(root)
    except Exception as exc:
        messagebox.showerror("Local Voice Studio cannot start", str(exc), parent=root)
        root.destroy()
        return
    root.deiconify()
    root.mainloop()
    worker = getattr(app, "shutdown_worker", None)
    if worker is not None:
        # Keep packaged-launch logging open while background cleanup finishes.
        worker.join()


if __name__ == "__main__":
    main()
