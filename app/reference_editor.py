from __future__ import annotations

import uuid
import tkinter as tk
import winsound
from tkinter import messagebox, ttk

import soundfile as sf

from .audio_processing import clean_reference
from .storage import DATA


class ReferenceEditor(tk.Toplevel):
    def __init__(self, parent, source):
        super().__init__(parent)
        self.title("Clean voice reference ? Before generation")
        self.result = None
        self.source = source
        if source.stat().st_size > 100 * 1024 * 1024:
            self.destroy()
            raise ValueError("Use a WAV smaller than 100 MB.")
        info = sf.info(source)
        if not 5 < info.duration <= 60 or info.channels not in (1, 2) or not 8000 <= info.samplerate <= 192000:
            self.destroy()
            raise ValueError("Use a mono/stereo WAV longer than 5 and up to 60 seconds, at 8–192 kHz.")
        audio, self.rate = sf.read(source, dtype="float32", always_2d=True)
        self.audio = audio.mean(axis=1)
        self.start = tk.StringVar(value="0")
        self.end = tk.StringVar(value=f"{info.duration:.4f}")
        self.trim = tk.BooleanVar(value=True)
        self.normal = tk.BooleanVar(value=True)
        self.denoise = tk.BooleanVar(value=False)
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"{source.name} · {info.duration:.2f} seconds").pack(anchor="w")
        ttk.Label(frame, text="These settings prepare your recording for future voice cloning.
Your original is preserved. Generated speech is polished separately.").pack(anchor="w", pady=8)
        times = ttk.Frame(frame)
        times.pack(fill="x", pady=8)
        for label, variable in (("Start (seconds)", self.start), ("End (seconds)", self.end)):
            ttk.Label(times, text=label).pack(side="left", padx=4)
            ttk.Entry(times, textvariable=variable, width=10).pack(side="left", padx=4)
        ttk.Checkbutton(frame, text="Trim quiet beginning and ending", variable=self.trim).pack(anchor="w")
        ttk.Checkbutton(frame, text="Balance recording volume (safe normalization)", variable=self.normal).pack(anchor="w")
        ttk.Checkbutton(frame, text="Reduce steady background noise (may soften voice detail)", variable=self.denoise).pack(anchor="w")
        self.description = tk.StringVar(value="Preview the cleaned version before saving; keep more than 5 seconds.")
        ttk.Label(frame, textvariable=self.description, wraplength=580).pack(anchor="w", pady=12)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Play original", command=self.play_original).pack(side="left", padx=3)
        ttk.Button(buttons, text="Preview cleanup", command=self.preview).pack(side="left", padx=3)
        ttk.Button(buttons, text="Stop", command=lambda: winsound.PlaySound(None, 0)).pack(side="left", padx=3)
        save = ttk.Frame(frame)
        save.pack(fill="x", pady=(12, 0))
        ttk.Button(save, text="Save voice reference", style="Primary.TButton", command=self.accept).pack(side="right")
        ttk.Button(save, text="Cancel", command=self.close).pack(side="right", padx=8)
        self.preview_path = DATA / "previews" / (uuid.uuid4().hex + ".wav")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.transient(parent)
        self.grab_set()

    def process(self):
        options = dict(start=float(self.start.get()), end=float(self.end.get()), trim=self.trim.get(),
                       normalize_volume=self.normal.get(), denoise=self.denoise.get())
        audio = clean_reference(self.audio, self.rate, **options)
        return audio, options

    def play_original(self):
        try:
            winsound.PlaySound(str(self.source), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except RuntimeError:
            messagebox.showerror("Playback failed", "Windows cannot play this source WAV. Try Preview cleanup.", parent=self)

    def preview(self):
        try:
            audio, _ = self.process()
            winsound.PlaySound(None, 0)
            self.preview_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(self.preview_path, audio, self.rate, subtype="PCM_16")
            winsound.PlaySound(str(self.preview_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.description.set(f"Cleaned reference: {len(audio) / self.rate:.2f} seconds. Your source file is unchanged.")
        except Exception as exc:
            messagebox.showerror("Cannot preview", str(exc), parent=self)

    def accept(self):
        try:
            _, options = self.process()
            self.result = options
            self.close()
        except Exception as exc:
            messagebox.showerror("Cannot use reference", str(exc), parent=self)

    def close(self):
        winsound.PlaySound(None, 0)
        self.preview_path.unlink(missing_ok=True)
        self.destroy()
