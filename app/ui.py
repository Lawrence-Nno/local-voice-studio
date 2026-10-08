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
from .storage import DATA, Settings, atomic_json, read_json
from .audio_processing import POLISH_MODES, polish_file
from .generation import GENERATION_PRESETS


class VoiceApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Local Voice Studio")
        icon = Path(__file__).resolve().parent / "assets" / "local-voice-studio.ico"
        if icon.exists():
            root.iconbitmap(default=str(icon))
        scale = max(1.0, root.winfo_fpixels("1i") / 96)
        width = min(round(1220 * scale), root.winfo_screenwidth() - 80)
        height = min(round(820 * scale), root.winfo_screenheight() - 120)
        root.geometry(f"{width}x{height}")
        root.minsize(min(round(1050 * scale), width), min(round(650 * scale), height))
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.subtitle_running = False
        self.mix_running = False
        self.recording_running = False
        self.editor_running = False
        self.conversion_running = False
        self.batch_running = False
        self.output = None
        self.polished_output = None
        self.engine = SpeechEngine()
        self.profiles = Profiles()
        self.settings = Settings()
        self.model_choice = tk.StringVar(value=self.settings.values.get("model", "Chatterbox Turbo"))
        if self.model_choice.get() not in ("Chatterbox Turbo", "Qwen3-TTS 1.7B Base"):
            self.model_choice.set("Chatterbox Turbo")
        self.profile_rows = []
        self.status = tk.StringVar(value="Ready. Choose a tool in the sidebar to begin.")
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
        from .ui_layout import build_interface
        from .studio_theme import configure_theme
        from .studio_shell import StudioShell
        configure_theme(root)
        self.shell = StudioShell(self)
        notebook = self.shell.notebook
        speech_tab = ttk.Frame(notebook)
        subtitle_tab = ttk.Frame(notebook)
        music_tab = ttk.Frame(notebook)
        recording_tab = ttk.Frame(notebook)
        notebook.add(speech_tab, text="Text to speech")
        notebook.add(subtitle_tab, text="Audio to subtitles")
        notebook.add(music_tab, text="Background music")
        notebook.add(recording_tab, text="Voice recorder")
        editor_tab = ttk.Frame(notebook)
        notebook.add(editor_tab, text="Audio editor")
        converter_tab = ttk.Frame(notebook)
        notebook.add(converter_tab, text="Format converter")
        cleanup_tab = ttk.Frame(notebook)
        notebook.add(cleanup_tab, text="Audio cleanup")
        batch_tab = ttk.Frame(notebook)
        notebook.add(batch_tab, text="Batch processing")
        effects_tab = ttk.Frame(notebook)
        notebook.add(effects_tab, text="Voice effects")
        build_interface(self, speech_tab)
        from .subtitle_ui import SubtitlePanel
        self.subtitles = SubtitlePanel(self, subtitle_tab)
        from .music_ui import MusicPanel
        self.music_panel = MusicPanel(self, music_tab)
        from .recorder_ui import RecorderPanel
        self.recorder_panel = RecorderPanel(self, recording_tab)
        from .editor_ui import EditorPanel
        self.editor_panel = EditorPanel(self, editor_tab)
        from .converter_ui import ConverterPanel
        self.converter_panel = ConverterPanel(self, converter_tab)
        from .cleanup_ui import CleanupPanel
        self.cleanup_panel = CleanupPanel(self, cleanup_tab)
        from .batch_ui import BatchPanel
        self.batch_panel = BatchPanel(self, batch_tab)
        from .effects_ui import EffectsPanel
        self.effects_panel = EffectsPanel(self, effects_tab)
        self.notebook = notebook
        self.shell.finish()
        notebook.bind('<<NotebookTabChanged>>', lambda _: self.editor_panel.stop_playback() if notebook.index('current') != 4 else None, add='+')
        menu = tk.Menu(root)
        menu.add_command(label="Audio file information...", command=self.open_audio_info)
        menu.add_command(label="Pronunciation dictionary...", command=self.open_pronunciation)
        root.configure(menu=menu)
        self.audio_info_dialog = None
        self.pronunciation_dialog = None
        self.refresh_profiles()
        self.select_model()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll)

    def open_pronunciation(self):
        if self.pronunciation_dialog and self.pronunciation_dialog.winfo_exists():
            self.pronunciation_dialog.lift()
            return
        try:
            from .pronunciation_ui import PronunciationDialog
            self.pronunciation_dialog = PronunciationDialog(self)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Cannot open pronunciation dictionary', str(exc))

    def open_audio_info(self):
        if self.audio_info_dialog and self.audio_info_dialog.winfo_exists():
            self.audio_info_dialog.lift()
            return
        from .audio_info_ui import AudioInfoDialog
        self.audio_info_dialog = AudioInfoDialog(self)

    def update_model_controls(self):
        qwen = self.model_choice.get() == "Qwen3-TTS 1.7B Base"
        self.test_button.configure(state="disabled" if qwen else "normal")
        self.transcript_button.configure(state="normal" if qwen else "disabled")
        self.model_description.set(
            "Qwen 1.7B: audio-only cloning by default. Add an exact reference transcript for fuller cloning."
            if qwen else "Turbo: fast English voice cloning. No reference transcript needed; built-in test voice available.")

    def select_model(self, _event=None):
        self.update_model_controls()
        try:
            self.settings.update(model=self.model_choice.get())
        except (OSError, ValueError) as exc:
            messagebox.showerror("Cannot save model selection", str(exc))

    def reference_transcript(self, profile):
        path = self.profiles.reference(profile).parent / ("transcript-" + profile["version"] + ".json")
        return read_json(path).get("text", "")

    def edit_transcript(self):
        profile = self.current_profile()
        if profile is None:
            messagebox.showinfo("Select a voice", "Add a recording first.")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Qwen reference transcript")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Write the exact words spoken in the selected prepared recording.\nLeave blank to use audio-only cloning. Editing or replacing a reference needs a new transcript.",
                  wraplength=600).pack(anchor="w", pady=(0, 10))
        text = tk.Text(frame, width=60, height=10, wrap="word", font=("Segoe UI", 11))
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.reference_transcript(profile))
        def save():
            try:
                value = text.get("1.0", "end-1c").strip()
                if len(value) > 10000:
                    raise ValueError("Keep the reference transcript under 10,000 characters.")
                path = self.profiles.reference(profile).parent / ("transcript-" + profile["version"] + ".json")
                atomic_json(path, {"text": value, "reference_version": profile["version"]})
                dialog.destroy()
                self.status.set("Reference transcript saved." if value else "Audio-only Qwen cloning selected.")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Cannot save transcript", str(exc), parent=dialog)
        ttk.Button(frame, text="Save reference transcript", style="Primary.TButton", command=save).pack(side="right", pady=10)
        ttk.Button(frame, text="Cancel", command=dialog.destroy).pack(side="right", padx=8, pady=10)

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

    def import_voice(self, replace=False, source=None):
        previous = self.current_profile() if replace else None
        if replace and previous is None:
            messagebox.showinfo("Select a voice", "Add a recording first.")
            return
        filename = str(source) if source else filedialog.askopenfilename(title="Choose your reference WAV", filetypes=[("WAV audio", "*.wav")])
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
        active = active or self.subtitle_running or self.mix_running or self.recording_running or self.editor_running or self.conversion_running or self.batch_running
        for control in (self.generate_button, self.test_button, self.add_button, self.replace_button,
                        self.cleanup_button, self.seed_entry, self.strength_slider, self.transcript_button):
            control.configure(state="disabled" if active else "normal")
        for control in (self.voice, self.devices, self.presets, self.polishes, self.models):
            control.configure(state="disabled" if active else "readonly")
        self.polish_button.configure(state="normal" if not active and self.output else "disabled")
        self.cancel_button.configure(state="normal" if active else "disabled")
        if not active:
            self.update_model_controls()

    def generate(self, generic=False):
        if (self.worker and self.worker.is_alive()) or self.subtitles.active() or self.mix_running or self.recording_running or self.editor_running or self.conversion_running or self.batch_running:
            return
        if generic and self.model_choice.get() != "Chatterbox Turbo":
            messagebox.showinfo("Reference required", "Qwen Base needs a saved voice recording. Use Generate my voice.")
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
            from .pronunciation import load
            generation_options['pronunciation'] = load()
            chosen_model = self.model_choice.get()
            transcript = self.reference_transcript(profile) if profile else ""
            mode, strength = self.polish_mode.get(), self.polish_strength.get()
            self.settings.update(device=self.device.get(), preset=self.preset.get(), seed=seed_text,
                                 polish_mode=mode, model=chosen_model)
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
                current = getattr(self.engine, "model_id", "Chatterbox Turbo")
                if current != chosen_model:
                    self.engine.unload()
                    if chosen_model == "Chatterbox Turbo":
                        self.engine = SpeechEngine()
                    else:
                        from .qwen_engine import QwenEngine
                        self.engine = QwenEngine()
                if chosen_model != "Chatterbox Turbo":
                    self.engine.transcript = transcript
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
        if not self.output or (self.worker and self.worker.is_alive()) or self.subtitles.active() or self.mix_running or self.recording_running or self.editor_running or self.conversion_running or self.batch_running:
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
        if (self.worker and self.worker.is_alive()) or self.subtitles.active() or self.mix_running or self.recording_running or self.editor_running or self.conversion_running or self.batch_running:
            messagebox.showinfo("Generation is running", "Cancel the active job in its tab and wait for it to finish before closing.")
            return
        winsound.PlaySound(None, 0)
        self.engine.unload()
        self.editor_panel.stop_playback()
        self.root.destroy()
