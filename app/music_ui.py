"""Native background music workflow; user tracks remain external imports."""
import json
import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
import uuid
import winsound
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .storage import ROOT, DATA, atomic_json


class MusicPanel:
    def __init__(self, app, parent):
        self.app = app
        self.voice = self.music = self.output = None
        self.result_sources = ()
        self.process = self.worker = None
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.voice_label = tk.StringVar(value="Voice/audio: none selected")
        self.music_label = tk.StringVar(value="Music: none selected")
        self.status = tk.StringVar(value="Import voice/audio and a music track, then create a mix. Your original files stay unchanged.")
        self.voice_gain = tk.DoubleVar(value=1)
        self.music_gain = tk.DoubleVar(value=.15)
        self.duck_strength = tk.DoubleVar(value=.75)
        self.duck = tk.BooleanVar(value=True)
        self.loop = tk.BooleanVar(value=True)
        self.music_start = tk.StringVar(value="0")
        self.fade_in = tk.StringVar(value="1")
        self.fade_out = tk.StringVar(value="1")
        frame = ttk.Frame(parent, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Background music", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Mix a soundtrack under speech. Voice timing stays unchanged, so existing subtitles stay synchronized.", wraplength=1000).pack(anchor="w", pady=(4, 12))
        row = ttk.Frame(frame)
        row.pack(fill="x")
        self.import_voice = ttk.Button(row, text="Import voice/audio...", command=lambda: self.choose(False))
        self.import_voice.pack(side="left")
        self.generated = ttk.Button(row, text="Use selected generated speech", command=self.use_generated)
        self.generated.pack(side="left", padx=8)
        self.import_music = ttk.Button(row, text="Import background music...", command=lambda: self.choose(True))
        self.import_music.pack(side="left")
        for variable in (self.voice_label, self.music_label):
            label = ttk.Label(frame, textvariable=variable, wraplength=1000)
            label.pack(fill="x", pady=5)
            label.bind("<Configure>", lambda e, label=label: label.configure(wraplength=max(100, e.width)))
        options = ttk.LabelFrame(frame, text="Mix settings", padding=12)
        options.pack(fill="x", pady=12)
        options.columnconfigure(1, weight=1)
        options.columnconfigure(3, weight=1)
        self.controls = []
        for index, (title, variable, maximum) in enumerate((
                ("Voice volume", self.voice_gain, 2), ("Music volume", self.music_gain, 1),
                ("Lower music during speech", self.duck_strength, 1))):
            text = tk.StringVar()
            def update(*_, title=title, variable=variable, text=text):
                text.set(f"{title}: {variable.get():.0%}")
            variable.trace_add("write", update)
            update()
            ttk.Label(options, textvariable=text).grid(row=index * 2, column=0, columnspan=2, sticky="w")
            scale = ttk.Scale(options, from_=0, to=maximum, variable=variable)
            scale.grid(row=index * 2 + 1, column=0, columnspan=2, sticky="ew", padx=(0, 20), pady=(0, 8))
            self.controls.append(scale)
        for index, (title, variable) in enumerate((("Music start (seconds)", self.music_start),
                ("Music fade-in (seconds)", self.fade_in), ("Music fade-out (seconds)", self.fade_out))):
            ttk.Label(options, text=title).grid(row=index * 2, column=2, sticky="w", padx=(16, 8))
            entry = ttk.Entry(options, textvariable=variable, width=10)
            entry.grid(row=index * 2, column=3, sticky="w")
            self.controls.append(entry)
        for index, (title, variable) in enumerate((("Automatic ducking (music lowers while speech is active)", self.duck),
                ("Loop the selected music portion if it is shorter than the voice", self.loop))):
            check = ttk.Checkbutton(frame, text=title, variable=variable)
            check.pack(anchor="w", pady=3)
            self.controls.append(check)
        ttk.Label(frame, text="Music source / license / required credit (optional; saved with this mix)").pack(anchor="w", pady=(12, 4))
        self.notes = tk.Text(frame, height=3, wrap="word", font=("Segoe UI", 10), padx=8, pady=8)
        self.notes.pack(fill="x")
        ttk.Label(frame, text="Use music whose license permits your intended use. Imported music is not bundled with the app.\nPeak protection may lower the whole mix to prevent clipping. Ducking detects audio energy, so noise can also trigger it.", wraplength=1000).pack(anchor="w", pady=8)
        footer = ttk.Frame(frame)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        actions = ttk.Frame(footer)
        actions.pack(fill="x", pady=8)
        self.create_button = ttk.Button(actions, text="Create music mix", style="Primary.TButton", command=self.start)
        self.create_button.pack(side="left")
        self.cancel_button = ttk.Button(actions, text="Cancel", state="disabled", command=self.stop)
        self.cancel_button.pack(side="left", padx=8)
        self.play_button = ttk.Button(actions, text="Preview mix", state="disabled", command=self.play)
        self.play_button.pack(side="left")
        ttk.Button(actions, text="Stop playback", command=lambda: winsound.PlaySound(None, 0)).pack(side="left", padx=8)
        self.export_button = ttk.Button(actions, text="Export mixed WAV...", state="disabled", command=self.export)
        self.export_button.pack(side="left")
        ttk.Button(footer, text="Open mixes folder", command=self.open_folder).pack(anchor="w", pady=(0, 8))
        self.progress = ttk.Progressbar(footer, mode="indeterminate")
        self.progress.pack(fill="x")
        label = ttk.Label(footer, textvariable=self.status, wraplength=1000)
        label.pack(fill="x", pady=8)
        label.bind("<Configure>", lambda e: label.configure(wraplength=max(100, e.width)))
        app.root.after(100, self.poll)

    def active(self):
        return self.worker is not None and self.worker.is_alive()

    def choose(self, music):
        filename = filedialog.askopenfilename(title="Choose background music" if music else "Choose voice/audio",
            filetypes=[("Audio", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.wma"), ("All files", "*.*")])
        if filename:
            if music:
                self.music = Path(filename)
                self.music_label.set("Music: " + filename)
            else:
                self.voice = Path(filename)
                self.voice_label.set("Voice/audio: " + filename)

    def use_generated(self):
        if not self.app.output:
            messagebox.showinfo("Generate speech first", "Generate speech in Text to speech, then choose Original or Polished and return here.")
            return
        self.voice = self.app.selected_output()
        self.voice_label.set("Generated " + self.app.output_version.get() + ": " + self.voice.name)

    def busy(self, active):
        for control in (*self.controls, self.import_voice, self.import_music, self.generated, self.create_button):
            control.configure(state="disabled" if active else "normal")
        self.notes.configure(state="disabled" if active else "normal")
        for control in (self.play_button, self.export_button):
            control.configure(state="normal" if not active and self.output else "disabled")
        self.cancel_button.configure(state="normal" if active else "disabled")
        self.app.busy(active)
        if active:
            self.app.cancel_button.configure(state="disabled")
            self.progress.start()
        else:
            self.progress.stop()

    def start(self):
        if self.app.editor_running or self.app.recording_running or self.active() or self.app.subtitle_running or (self.app.worker and self.app.worker.is_alive()):
            messagebox.showinfo("Job running", "Wait for the current audio job to finish first.")
            return
        try:
            if not self.voice or not self.music or not self.voice.is_file() or not self.music.is_file():
                raise ValueError("Choose a voice/audio file and a background music file first.")
            options = {"voice_gain": self.voice_gain.get(), "music_gain": self.music_gain.get(),
                "duck_strength": self.duck_strength.get(), "duck": self.duck.get(), "loop": self.loop.get(),
                "music_start": float(self.music_start.get()), "fade_in": float(self.fade_in.get()), "fade_out": float(self.fade_out.get())}
            import math
            for key in ("music_start", "fade_in", "fade_out"):
                if not math.isfinite(options[key]) or options[key] < 0:
                    raise ValueError("Music start and fade times must be finite, nonnegative seconds.")
            interpreter = ROOT / "runtime/qwen/python.exe"
            if not interpreter.is_file():
                interpreter = ROOT / ".venv-qwen/Scripts/python.exe"
            if not interpreter.is_file():
                raise ValueError("The audio worker environment is missing. Run setup-qwen.ps1 first.")
            identifier = uuid.uuid4().hex
            work = DATA / "mixwork" / identifier
            sources = (self.voice.resolve(), self.music.resolve())
            request = {"voice": str(sources[0]), "music": str(sources[1]), "options": options,
                       "work": str(work), "notes": self.notes.get("1.0", "end-1c").strip()}
        except Exception as exc:
            messagebox.showerror("Cannot create mix", str(exc))
            return
        self.cancel.clear()
        self.app.mix_running = True
        self.busy(True)
        self.status.set("Starting local background music mix...")
        def run():
            try:
                DATA.mkdir(parents=True, exist_ok=True)
                with (DATA / "music-worker.log").open("a", encoding="utf-8") as log:
                    self.process = subprocess.Popen([str(interpreter), "-E", "-s", "-m", "app.music_worker"], cwd=ROOT,
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True, encoding="utf-8",
                        creationflags=subprocess.CREATE_NO_WINDOW)
                    if self.cancel.is_set():
                        self.process.terminate()
                    else:
                        self.process.stdin.write(json.dumps(request) + "\n")
                        self.process.stdin.flush()
                        self.process.stdin.close()
                        result = None
                        for line in self.process.stdout:
                            value = json.loads(line)
                            if "progress" in value:
                                self.events.put(("progress", value["progress"]))
                            if "error" in value:
                                raise ValueError(value["error"])
                            result = value.get("result", result)
                        if not self.cancel.is_set():
                            if result is None:
                                raise RuntimeError("Audio worker stopped. See data/music-worker.log.")
                            directory = DATA / "mixes"
                            directory.mkdir(parents=True, exist_ok=True)
                            path = directory / (identifier + ".wav")
                            Path(result.pop("temporary_output")).replace(path)
                            atomic_json(path.with_suffix(".json"), {**result, "voice": str(sources[0]),
                                "music": str(sources[1]), "license_notes": request["notes"], "output": path.name})
                            self.events.put(("complete", (path, sources, result)))
            except Exception as exc:
                if not self.cancel.is_set():
                    self.events.put(("error", str(exc)))
            finally:
                if self.process is not None:
                    if self.process.poll() is None:
                        self.process.terminate()
                    self.process.wait()
                    self.process.stdout.close()
                    if not self.process.stdin.closed:
                        self.process.stdin.close()
                    self.process = None
                # Only this job's private temporary directory can be removed.
                if work.exists() and work.resolve().parent == (DATA / "mixwork").resolve():
                    shutil.rmtree(work)
                self.events.put(("finished", self.cancel.is_set()))
        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def stop(self):
        self.cancel.set()
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
        self.cancel_button.configure(state="disabled")
        self.status.set("Cancelling mix...")

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress" and not self.cancel.is_set():
                    self.status.set(value)
                elif kind == "complete":
                    self.output, self.result_sources, result = value
                    self.status.set(f"Mix ready: {result['duration']:.1f}s, stereo WAV. Preview or export; voice timing is unchanged.")
                elif kind == "error":
                    self.status.set("Mix failed. Previous mix and original files remain available.")
                    messagebox.showerror("Cannot create mix", value)
                elif kind == "finished":
                    self.app.mix_running = False
                    self.busy(False)
                    if value:
                        self.status.set("Cancelled. Previous mix and original files remain available.")
        except queue.Empty:
            pass
        self.app.root.after(100, self.poll)

    def play(self):
        if self.output:
            try:
                winsound.PlaySound(str(self.output), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except RuntimeError as exc:
                messagebox.showerror("Cannot play mix", str(exc))

    def export(self):
        if not self.output:
            return
        filename = filedialog.asksaveasfilename(title="Export mixed stereo WAV", defaultextension=".wav",
            initialfile=self.result_sources[0].stem + "-with-music.wav", filetypes=[("WAV audio", "*.wav")])
        if filename:
            try:
                target = Path(filename).resolve()
                protected = (*self.result_sources, self.voice, self.music)
                if any(source and target == Path(source).resolve() for source in protected):
                    raise ValueError("Choose a new filename to preserve the original voice and music files.")
                if target != self.output.resolve():
                    shutil.copyfile(self.output, target)
                shutil.copyfile(self.output.with_suffix(".json"), target.with_suffix(".mix.json"))
                self.status.set("Exported WAV and mix/license notes to " + str(target))
            except Exception as exc:
                messagebox.showerror("Cannot export mix", str(exc))

    def open_folder(self):
        path = DATA / "mixes"
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)
