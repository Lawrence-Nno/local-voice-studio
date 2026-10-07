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
        VoiceApp(root)
    except Exception as exc:
        messagebox.showerror("Local Voice Studio cannot start", str(exc), parent=root)
        root.destroy()
        return
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
