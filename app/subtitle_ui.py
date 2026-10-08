"""Audio transcription and saved-script alignment in a dedicated native tab."""
import json
import os
import queue
import subprocess
import threading
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from .storage import ROOT, DATA, atomic_json, read_json
from .subtitles import parse_srt, serialize


class SubtitlePanel:
    def __init__(self, app, parent):
        self.app = app
        self.source = None
        self.result_source = None
        self.process = None
        self.worker = None
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.status = tk.StringVar(value="Choose audio to transcribe, or align the saved script of your latest generated speech.")
        self.filename = tk.StringVar(value="No audio selected")
        self.language = tk.StringVar(value="Automatic")
        self.device = tk.StringVar(value="Automatic")
        frame = ttk.Frame(parent, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Audio to subtitles", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Local transcription and script alignment. Review words and timings before exporting.").pack(anchor="w", pady=(4, 12))
        controls = ttk.Frame(frame)
        controls.pack(fill="x")
        self.import_button = ttk.Button(controls, text="Import audio...", command=self.choose)
        self.import_button.pack(side="left")
        self.generated_button = ttk.Button(controls, text="Use generated speech + saved script", command=self.generated)
        self.generated_button.pack(side="left", padx=8)
        ttk.Label(frame, textvariable=self.filename, wraplength=800).pack(anchor="w", pady=8)
        ttk.Label(frame, text="Imported audio: recognize spoken words. Generated speech: keep the saved script and align its words to the audio.", wraplength=1000).pack(anchor="w", pady=(0, 12))
        options = ttk.Frame(frame)
        options.pack(fill="x")
        ttk.Label(options, text="Audio language").pack(side="left", padx=(0, 8))
        self.languages = ttk.Combobox(options, textvariable=self.language, state="readonly", values=("Automatic", "English"), width=12)
        self.languages.pack(side="left")
        ttk.Label(options, text="Processing device").pack(side="left", padx=(20, 8))
        self.devices = ttk.Combobox(options, textvariable=self.device, state="readonly", values=("Automatic", "NVIDIA GPU", "CPU"), width=14)
        self.devices.pack(side="left")
        self.start_button = ttk.Button(options, text="Create subtitles", style="Primary.TButton", command=self.start)
        self.start_button.pack(side="left", padx=16)
        self.cancel_button = ttk.Button(options, text="Cancel", state="disabled", command=self.stop)
        self.cancel_button.pack(side="left")
        ttk.Label(frame, text="Whisper Small • multilingual • offline   |   Edit cue text or HH:MM:SS,mmm timings below.").pack(anchor="w", pady=(12, 8))
        footer = ttk.Frame(frame)
        footer.pack(side="bottom", fill="x")
        editor = ttk.Frame(frame)
        editor.pack(fill="both", expand=True)
        self.text = tk.Text(editor, height=4, wrap="word", font=("Consolas", 11), undo=True, padx=12, pady=12)
        scrollbar = ttk.Scrollbar(editor, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        actions = ttk.Frame(footer)
        actions.pack(fill="x", pady=12)
        self.export_button = ttk.Button(actions, text="Export reviewed SRT...", state="disabled", command=self.export)
        self.export_button.pack(side="left")
        ttk.Button(actions, text="Open subtitle folder", command=self.open_folder).pack(side="left", padx=8)
        self.progress = ttk.Progressbar(footer, mode="indeterminate")
        self.progress.pack(fill="x")
        ttk.Label(footer, textvariable=self.status, wraplength=1000).pack(anchor="w", pady=8)
        app.root.after(100, self.poll)

    def active(self):
        return self.worker is not None and self.worker.is_alive()

    def choose(self):
        filename = filedialog.askopenfilename(title="Choose audio for subtitles", filetypes=[
            ("Audio", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.wma"), ("All files", "*.*")])
        if filename:
            self.source = {"mode": "transcribe", "audio": filename}
            self.filename.set("Transcription: " + filename)
            if self.result_source:
                self.filename.set(self.filename.get() + " | Editor still contains: " + Path(self.result_source).name)
            self.status.set("Ready to recognize speech. Automatic detects the language; choose English if detection is unreliable.")

    def generated(self):
        if not self.app.output:
            messagebox.showinfo("Generate speech first", "Generate speech in the Text to speech tab, then return here.")
            return
        try:
            directory = DATA / "jobs" / self.app.output.stem
            metadata = read_json(directory / "job.json")
            sections = metadata.get("section_texts")
            if not sections:
                raise ValueError("This older output has no saved script. Generate it again, or import its WAV for transcription.")
            import soundfile as sf
            paths = []
            for index, text in enumerate(sections, 1):
                path = directory / f"section-{index:04d}.wav"
                paths.append({"path": str(path), "text": text, "duration": sf.info(path).duration})
            self.source = {"mode": "align", "audio": str(self.app.selected_output()), "sections": paths}
            self.filename.set("Saved-script alignment: " + self.app.selected_output().name)
            self.status.set("Ready to align the original saved English script. Current edits in the TTS text box do not change this script.")
        except Exception as exc:
            messagebox.showerror("Cannot use generated speech", str(exc))

    def busy(self, active):
        for widget in (self.import_button, self.generated_button, self.start_button):
            widget.configure(state="disabled" if active else "normal")
        for widget in (self.languages, self.devices):
            widget.configure(state="disabled" if active else "readonly")
        self.text.configure(state="disabled" if active else "normal")
        self.export_button.configure(state="normal" if not active and self.text.get("1.0", "end").strip() else "disabled")
        self.cancel_button.configure(state="normal" if active else "disabled")
        self.app.busy(active)
        if active:
            self.app.cancel_button.configure(state="disabled")
            self.progress.start()
        else:
            self.progress.stop()

    def start(self):
        if self.app.editor_running or self.app.recording_running or self.active() or self.app.mix_running or (self.app.worker and self.app.worker.is_alive()):
            messagebox.showinfo("Job running", "Wait for the current audio job to finish first.")
            return
        if self.source is None:
            messagebox.showinfo("Choose audio", "Import audio or select your latest generated speech first.")
            return
        interpreter = ROOT / "runtime/qwen/python.exe"
        if not interpreter.is_file():
            interpreter = ROOT / ".venv-qwen/Scripts/python.exe"
        if not interpreter.is_file() or not (ROOT / "models/whisper-small/manifest.json").is_file():
            messagebox.showerror("Subtitle model missing", "Run setup-subtitles.ps1 while online first.")
            return
        request = {**self.source, "device": self.device.get(), "language": "en" if self.language.get() == "English" else None}
        self.cancel.clear()
        self.app.subtitle_running = True
        self.busy(True)
        self.status.set("Releasing speech model and starting subtitle processing...")
        def work():
            try:
                self.app.engine.unload()
                DATA.mkdir(parents=True, exist_ok=True)
                with (DATA / "subtitle-worker.log").open("a", encoding="utf-8") as log:
                    self.process = subprocess.Popen([str(interpreter), "-E", "-s", "-m", "app.subtitle_worker"],
                        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True,
                        encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
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
                            if "result" in value:
                                result = value["result"]
                        if not self.cancel.is_set():
                            if result is None:
                                raise RuntimeError("Subtitle worker stopped. See data/subtitle-worker.log.")
                            directory = DATA / "subtitles"
                            directory.mkdir(parents=True, exist_ok=True)
                            path = directory / (uuid.uuid4().hex + ".srt")
                            path.write_text(result["srt"], encoding="utf-8")
                            atomic_json(path.with_suffix(".json"), {**result, "source": request["audio"], "saved_srt": path.name})
                            self.events.put(("complete", (result, path, request["audio"])))
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
                self.events.put(("finished", self.cancel.is_set()))
        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def stop(self):
        self.cancel.set()
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
        self.status.set("Cancelling subtitle processing...")
        self.cancel_button.configure(state="disabled")

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress" and not self.cancel.is_set():
                    self.status.set(value)
                elif kind == "complete":
                    result, path, self.result_source = value
                    self.text.configure(state="normal")
                    self.text.delete("1.0", "end")
                    self.text.insert("1.0", result["srt"])
                    self.status.set(f"Created {len(result['cues'])} cues ({result['language']}, {result['device']}). Review and export. Saved {path.name}.")
                elif kind == "error":
                    self.status.set("Subtitle processing failed. Previous captions remain available.")
                    messagebox.showerror("Cannot create subtitles", value)
                elif kind == "finished":
                    self.app.subtitle_running = False
                    self.busy(False)
                    if value:
                        self.status.set("Cancelled. Previous captions remain available.")
        except queue.Empty:
            pass
        self.app.root.after(100, self.poll)

    def export(self):
        try:
            text = serialize(parse_srt(self.text.get("1.0", "end-1c")))
            filename = filedialog.asksaveasfilename(title="Export reviewed subtitles", defaultextension=".srt",
                initialfile=Path(self.result_source).stem + ".srt" if self.result_source else "subtitles.srt",
                filetypes=[("SubRip subtitles", "*.srt")])
            if filename:
                Path(filename).write_text(text, encoding="utf-8")
                self.status.set("Exported reviewed subtitles to " + filename)
        except Exception as exc:
            messagebox.showerror("Cannot export subtitles", str(exc))

    def open_folder(self):
        path = DATA / "subtitles"
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)
