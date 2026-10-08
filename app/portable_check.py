"""Short native-window self-check used by the executable packaging check."""
import sys
import tkinter as tk
from .storage import ROOT, DATA, configure_runtime, atomic_json


def main():
    configure_runtime()
    from .main import configure_dpi
    configure_dpi()
    from .ui import VoiceApp
    root = tk.Tk()
    app = VoiceApp(root)
    root.update()
    assert app.models.winfo_ismapped()
    assert app.generate_button.winfo_ismapped()
    atomic_json(DATA / "portable-check.json", {"root": str(ROOT), "python": sys.executable,
        "window": root.title(), "profiles": len(app.profile_rows), "models": list(app.models["values"])})
    root.after(1200, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
