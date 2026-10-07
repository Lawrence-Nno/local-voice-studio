from __future__ import annotations

import os
import queue
import shutil
import threading
import tkinter as tk
import winsound
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .engine import SpeechEngine
from .generation import Cancelled, run_job
from .profiles import Profiles
from .storage import DATA, Settings
from .audio_processing import POLISH_MODES, polish_file
from .generation import GENERATION_PRESETS


class VoiceApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Local Voice Studio")
        scale = max(1.0, root.winfo_fpixels("1i") / 96)
        width = min(round(940 * scale), root.winfo_screenwidth() - 80)
        height = min(round(740 * scale), root.winfo_screenheight() - 120)
        root.geometry(f"{width}x{height}")
        root.minsize(min(round(760 * scale), width), min(round(620 * scale), height))
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.output = None
        self.polished_output = None
        self.engine = SpeechEngine()
        self.profiles = Profiles()
        self.settings = Settings()
        self.profile_rows = []
        self.status = tk.StringVar(value="Ready. Import your voice, or run a generic speech test.")
        self.device = tk.StringVar(value=self.settings.values.get("device", "Automatic"))
        self.preset = tk.StringVar(value=self.settings.values.get("preset", "Default"))
        if self.preset.get() not in GENERATION_PRESETS:
            self.preset.set("Default")
        self.seed = tk.StringVar(value=str(self.settings.values.get("seed", "")))
        self.polish_mode = tk.StringVar(value=self.settings.values.get("polish_mode", "Natural polish"))
        if self.polish_mode.get() not in POLISH_MODES:
            self.polish_mode.set("Natural polish")
        self.polish_strength = tk.DoubleVar(value=.5)
        self.output_version = tk.StringVar(value="Original")
        if self.device.get() not in ("Automatic", "NVIDIA GPU", "CPU"):
            self.device.set("Automatic")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=8)
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"))
        style.configure("TLabel", font=("Segoe UI", 10))
        panel = ttk.Frame(root, padding=24)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Local Voice Studio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(panel, text="Your recordings and speech stay on this computer.").pack(anchor="w", pady=(4, 20))
        voices = ttk.LabelFrame(panel, text="Saved voice", padding=12)
        voices.pack(fill="x")
        self.voice = ttk.Combobox(voices, state="readonly", width=36)
        self.voice.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.voice.bind("<<ComboboxSelected>>", self.select_voice)
        self.add_button = ttk.Button(voices, text="Add recording", command=self.import_voice)
        self.add_button.grid(row=0, column=1, padx=4)
        self.replace_button = ttk.Button(voices, text="Replace recording", command=lambda: self.import_voice(True))
        self.replace_button.grid(row=0, column=2, padx=4)
        self.cleanup_button = ttk.Button(voices, text="Clean saved reference", command=self.clean_saved_reference)
        self.cleanup_button.grid(row=2, column=0, sticky="w", pady=(8, 0))
        voices.columnconfigure(0, weight=1)
        ttk.Label(voices, text="Use a clear 10–15 second WAV. One speaker, quiet room, natural speaking style.",
                  wraplength=800).grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))
        row = ttk.Frame(panel)
        row.pack(fill="x", pady=(16, 8))
        ttk.Label(row, text="Text to speak · English · up to 20,000 characters").pack(side="left")
        ttk.Label(row, text="Device:").pack(side="left", padx=(20, 6))
        self.devices = ttk.Combobox(row, state="readonly", textvariable=self.device,
                                   values=("Automatic", "NVIDIA GPU", "CPU"), width=14)
        self.devices.pack(side="left")
        options = ttk.Frame(panel)
        options.pack(fill="x", pady=(0, 8))
        ttk.Label(options, text="Delivery:").grid(row=0, column=0, padx=3)
        self.presets = ttk.Combobox(options, state="readonly", textvariable=self.preset,
                                   values=tuple(GENERATION_PRESETS), width=12)
        self.presets.grid(row=0, column=1, padx=3)
        ttk.Label(options, text="Seed (optional):").grid(row=0, column=2, padx=3)
        self.seed_entry = ttk.Entry(options, textvariable=self.seed, width=12)
        self.seed_entry.grid(row=0, column=3, padx=3)
        ttk.Label(options, text="Output polish:").grid(row=1, column=0, padx=3, pady=5)
        self.polishes = ttk.Combobox(options, state="readonly", textvariable=self.polish_mode,
                                    values=POLISH_MODES, width=16)
        self.polishes.grid(row=1, column=1, padx=3)
        ttk.Label(options, text="Strength:").grid(row=1, column=2, padx=3)
        self.strength_slider = ttk.Scale(options, from_=0, to=1, variable=self.polish_strength, length=120)
        self.strength_slider.grid(row=1, column=3, padx=3)
        text_frame = ttk.Frame(panel)
        text_frame.pack(fill="both", expand=True)
        self.text = tk.Text(text_frame, wrap="word", height=4, font=("Segoe UI", 12), padx=12, pady=12, undo=True)
        scroll = ttk.Scrollbar(text_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        controls = ttk.Frame(panel)
        controls.pack(fill="x", pady=12)
        self.generate_button = ttk.Button(controls, text="Generate with saved voice", command=self.generate)
        self.generate_button.pack(side="left")
        self.test_button = ttk.Button(controls, text="Generic speech test", command=lambda: self.generate(True))
        self.test_button.pack(side="left", padx=8)
        self.cancel_button = ttk.Button(controls, text="Cancel", state="disabled", command=self.request_cancel)
        self.cancel_button.pack(side="left")
        self.progress = ttk.Progressbar(panel, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))
        ttk.Label(panel, textvariable=self.status, wraplength=820).pack(anchor="w")
        playback = ttk.Frame(panel)
        playback.pack(fill="x", pady=(16, 0))
        self.play_button = ttk.Button(playback, text="Play", state="disabled", command=self.play)
        self.play_button.pack(side="left")
        ttk.Button(playback, text="Stop", command=lambda: winsound.PlaySound(None, 0)).pack(side="left", padx=8)
        self.export_button = ttk.Button(playback, text="Export WAV", state="disabled", command=self.export)
        self.export_button.pack(side="left")
        self.versions = ttk.Combobox(playback, state="disabled", textvariable=self.output_version,
                                    values=("Original", "Polished"), width=10)
        self.versions.pack(side="left", padx=8)
        self.polish_button = ttk.Button(playback, text="Apply polish", state="disabled", command=self.apply_polish)
        self.polish_button.pack(side="left")
        ttk.Button(playback, text="Open output folder", command=self.open_outputs).pack(side="right")
        self.refresh_profiles()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll)

    def current_profile(self):
        index = self.voice.current()
        return self.profile_rows[index] if 0 <= index < len(self.profile_rows) else None

    def refresh_profiles(self):
        self.profile_rows, errors = self.profiles.list()
        self.voice["values"] = [f"{p['name']} ({p['duration']:.1f}s)" for p in self.profile_rows]
        selected = self.settings.values.get("selected_profile")
        for index, profile in enumerate(self.profile_rows):
            if profile["id"] == selected:
                self.voice.current(index)
                break
        else:
            if self.profile_rows:
                self.voice.current(0)
                self.select_voice()
        if errors:
            messagebox.showwarning("Voice profiles need attention", "\n".join(errors))

    def select_voice(self, _event=None):
        profile = self.current_profile()
        if profile:
            try:
                self.settings.update(selected_profile=profile["id"])
            except (OSError, ValueError) as exc:
                messagebox.showerror("Cannot save selection", str(exc))

    def import_voice(self, replace=False):
        previous = self.current_profile() if replace else None
        if replace and previous is None:
            messagebox.showinfo("Select a voice", "Add a recording first.")
            return
        filename = filedialog.askopenfilename(title="Choose your reference WAV", filetypes=[("WAV audio", "*.wav")])
        if not filename:
            return
        name = simpledialog.askstring("Voice name", "Name this voice or speaking style:",
                                      initialvalue=previous["name"] if previous else Path(filename).stem)
        if name is None:
            return
        try:
            from .reference_editor import ReferenceEditor
            editor = ReferenceEditor(self.root, Path(filename))
            self.root.wait_window(editor)
            if editor.result is None:
                return
            profile, warnings = self.profiles.import_wav(Path(filename), name, previous, cleanup=editor.result)
            self.settings.update(selected_profile=profile["id"])
            self.refresh_profiles()
            self.status.set(f"Saved {profile['name']}. This voice will be restored on restart.")
            if warnings:
                messagebox.showwarning("Recording saved", "\n".join(warnings))
        except Exception as exc:
            messagebox.showerror("Cannot import recording", str(exc))

    def clean_saved_reference(self):
        profile = self.current_profile()
        if profile is None:
            messagebox.showinfo("Select a voice", "Add a recording first.")
            return
        try:
            from .reference_editor import ReferenceEditor
            source = self.profiles.reference(profile).parent / profile["original"]
            editor = ReferenceEditor(self.root, source)
            self.root.wait_window(editor)
            if editor.result is None:
                return
            updated, warnings = self.profiles.import_wav(source, profile["name"], profile, cleanup=editor.result)
            self.settings.update(selected_profile=updated["id"])
            self.refresh_profiles()
            self.status.set("Saved cleaned reference. The original and previous versions are preserved.")
            if warnings:
                messagebox.showwarning("Reference saved", "\n".join(warnings))
        except Exception as exc:
            messagebox.showerror("Cannot clean reference", str(exc))

    def busy(self, active):
        for control in (self.generate_button, self.test_button, self.add_button, self.replace_button,
                        self.cleanup_button, self.seed_entry, self.strength_slider):
            control.configure(state="disabled" if active else "normal")
        for control in (self.voice, self.devices, self.presets, self.polishes):
            control.configure(state="disabled" if active else "readonly")
        self.polish_button.configure(state="normal" if not active and self.output else "disabled")
        self.cancel_button.configure(state="normal" if active else "disabled")

    def generate(self, generic=False):
        if self.worker and self.worker.is_alive():
            return
        profile = None if generic else self.current_profile()
        if not generic and profile is None:
            messagebox.showinfo("Import your voice", "Add a WAV recording before generating with your voice.")
            return
        text = self.text.get("1.0", "end").strip()
        if not text and generic:
            text = "Hello. This is a generic test of local speech generation, not a clone of your voice."
        if not text:
            messagebox.showinfo("Enter text", "Enter the text you want to hear.")
            return
        try:
            reference = self.profiles.reference(profile) if profile else None
            seed_text = self.seed.get().strip()
            seed = int(seed_text) if seed_text else None
            if seed is not None and not 0 <= seed <= 2**32 - 1:
                raise ValueError("Seed must be between 0 and 4294967295, or blank.")
            generation_options = {"preset": self.preset.get(), "seed": seed}
            mode, strength = self.polish_mode.get(), self.polish_strength.get()
            self.settings.update(device=self.device.get(), preset=self.preset.get(), seed=seed_text,
                                 polish_mode=mode)
        except Exception as exc:
            messagebox.showerror("Cannot start generation", str(exc))
            return
        device = self.device.get()
        self.cancel.clear()
        self.busy(True)
        self.progress["value"] = 0
        self.status.set("Starting generic test (not your voice)." if generic else "Starting generation.")

        def progress(message, completed=0, total=1):
            self.events.put(("progress", (message, completed, total)))

        def work():
            try:
                # Reset conditioning before a generic test, since a prior job may have used a personal voice.
                if generic and self.engine.model is not None:
                    self.engine.unload()
                result = run_job(self.engine, text, profile, reference, device, self.cancel, progress,
                                 options=generation_options)
                polishing = mode != "Original" and not self.cancel.is_set()
                self.events.put(("complete", (result, generic, polishing)))
                if polishing:
                    try:
                        progress("Polishing completed audio")
                        destination = result.with_name(result.stem + "-polished.wav")
                        polish_file(result, destination, mode, strength)
                        self.events.put(("polished", destination))
                    except Exception as exc:
                        self.events.put(("polish_error", str(exc)))
            except Cancelled:
                self.events.put(("cancelled", None))
            except Exception as exc:
                message = str(exc)
                if "out of memory" in message.lower():
                    message = "GPU memory was exhausted. Close GPU-heavy apps, shorten your text, or select CPU and retry."
                try:
                    self.engine.unload()
                except Exception:
                    pass
                self.events.put(("error", message))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def request_cancel(self):
        self.cancel.set()
        self.cancel_button.configure(state="disabled")
        self.status.set("Cancellation requested. The current section may need to finish first.")

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    message, completed, total = value
                    if not self.cancel.is_set():
                        self.status.set(message)
                    self.progress.configure(maximum=total, value=completed)
                elif kind == "complete":
                    self.output, generic, polishing = value
                    self.polished_output = None
                    self.output_version.set("Original")
                    self.versions.configure(state="readonly", values=("Original",))
                    self.busy(polishing)
                    if polishing:
                        self.cancel_button.configure(state="disabled")
                    self.progress["value"] = self.progress["maximum"]
                    self.play_button.configure(state="normal")
                    self.export_button.configure(state="normal")
                    self.status.set(("Generic test complete (not your voice). " if generic else "Generation complete. ") + self.output.name)
                elif kind == "polished":
                    self.polished_output = value
                    self.versions.configure(state="readonly", values=("Original", "Polished"))
                    self.output_version.set("Polished")
                    self.busy(False)
                    self.status.set("Polish complete. Choose Original or Polished to compare and export.")
                elif kind == "polish_error":
                    self.busy(False)
                    self.status.set("Polish failed; the original completed WAV is available.")
                    messagebox.showerror("Polish failed", value)
                elif kind == "cancelled":
                    self.busy(False)
                    self.status.set("Cancelled. Completed sections remain in data/jobs; no full result was published.")
                elif kind == "error":
                    self.busy(False)
                    self.status.set("Generation failed. Completed sections remain in data/jobs.")
                    messagebox.showerror("Generation failed", value)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def play(self):
        try:
            winsound.PlaySound(str(self.selected_output()), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except RuntimeError:
            messagebox.showerror("Playback failed", "Check your Windows audio output device. You can still export the WAV.")

    def export(self):
        source = self.selected_output()
        filename = filedialog.asksaveasfilename(title="Export generated WAV", defaultextension=".wav",
                                               initialfile=source.name, filetypes=[("WAV audio", "*.wav")])
        if filename:
            try:
                if source != self.output and Path(filename).resolve() == self.output.resolve():
                    raise ValueError("Choose another filename to preserve the original generated WAV.")
                if Path(filename).resolve() != source.resolve():
                    shutil.copyfile(source, filename)
                self.status.set("Exported WAV to " + filename)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Export failed", str(exc))

    def selected_output(self):
        return self.polished_output if self.output_version.get() == "Polished" and self.polished_output else self.output

    def apply_polish(self):
        if not self.output or (self.worker and self.worker.is_alive()):
            return
        if self.polish_mode.get() == "Original":
            self.output_version.set("Original")
            return
        source, mode, strength = self.output, self.polish_mode.get(), self.polish_strength.get()
        self.busy(True)
        self.cancel_button.configure(state="disabled")
        self.status.set("Polishing completed audio...")
        def work():
            try:
                destination = source.with_name(source.stem + "-polished.wav")
                polish_file(source, destination, mode, strength)
                self.events.put(("polished", destination))
            except Exception as exc:
                self.events.put(("polish_error", str(exc)))
        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def open_outputs(self):
        directory = DATA / "outputs"
        directory.mkdir(parents=True, exist_ok=True)
        os.startfile(directory)

    def close(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Generation is running", "Cancel and wait for the current section to finish before closing.")
            return
        winsound.PlaySound(None, 0)
        self.root.destroy()
