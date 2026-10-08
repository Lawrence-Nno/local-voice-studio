"""Microphone recording workflow in the native desktop app."""
import os
import queue
import shutil
import tkinter as tk
import winsound
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .recorder import Recorder
from .storage import DATA


class RecorderPanel:
    def __init__(self, app, parent):
        self.app = app
        self.recorder = Recorder()
        self.output = None
        self.countdown_remaining = None
        self.countdown_after = None
        self.countdown_device = None
        self.devices = {}
        self.device = tk.StringVar()
        self.status = tk.StringVar(value="Choose your microphone and start a recording. Audio stays on this computer.")
        self.timer = tk.StringVar(value="00:00.0")
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Record your voice", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Capture a voice reference or any microphone audio. Each completed take is saved as a separate WAV.", wraplength=820).pack(anchor="w", pady=(6, 20))
        ttk.Label(frame, text="Microphone / audio input").pack(anchor="w")
        self.selector = ttk.Combobox(frame, textvariable=self.device, state="readonly")
        self.selector.pack(fill="x", pady=6)
        self.refresh = ttk.Button(frame, text="Refresh microphones", command=self.refresh_devices)
        self.refresh.pack(anchor="w")
        ttk.Label(frame, textvariable=self.timer, font=("Segoe UI", 32)).pack(anchor="w", pady=(24, 8))
        ttk.Label(frame, text="Microphone level — if it reaches 100%, move farther away or lower Windows input volume.", wraplength=820).pack(anchor="w")
        self.meter = ttk.Progressbar(frame, maximum=1)
        self.meter.pack(fill="x", pady=8)
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=12)
        self.start_button = ttk.Button(row, text="Start recording (3-second countdown)", style="Primary.TButton", command=self.start)
        self.start_button.pack(side="left")
        self.pause_button = ttk.Button(row, text="Pause", state="disabled", command=self.pause)
        self.pause_button.pack(side="left", padx=8)
        self.stop_button = ttk.Button(row, text="Stop and save", state="disabled", command=self.stop)
        self.stop_button.pack(side="left")
        ttk.Label(frame, text="For cloning: record 10–30 seconds in a quiet room, speak naturally, and avoid background music.\nFor a voice reference, stop after 6 to 60 seconds. Longer recordings can be exported for other uses.\nPause removes the pause from the saved audio. Recordings stop automatically at one hour.", wraplength=820).pack(anchor="w", pady=12)
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=12)
        self.result_buttons = []
        for title, command in (("Preview recording", self.play), ("Export WAV...", self.export), ("Clean up and use as voice reference", self.use_reference)):
            button = ttk.Button(row, text=title, command=command, state="disabled")
            button.pack(side="left", padx=(0, 8))
            self.result_buttons.append(button)
        self.subtitle_button = ttk.Button(frame, text="Create subtitles from recording", command=self.use_subtitles, state="disabled")
        self.subtitle_button.pack(anchor="w", pady=(0, 8))
        self.result_buttons.append(self.subtitle_button)
        ttk.Button(frame, text="Stop playback", command=lambda: winsound.PlaySound(None, 0)).pack(anchor="w")
        ttk.Button(frame, text="Open recordings folder", command=self.open_folder).pack(anchor="w", pady=8)
        label = ttk.Label(frame, textvariable=self.status, wraplength=820)
        label.pack(fill="x", pady=12)
        label.bind("<Configure>", lambda e: label.configure(wraplength=max(100, e.width)))
        self.refresh_devices()
        app.root.after(100, self.poll)

    def refresh_devices(self):
        try:
            import sounddevice as sd
            hosts = sd.query_hostapis()
            self.devices = {f"{index}: {device['name']} ({hosts[device['hostapi']]['name']})": (index, int(device['default_samplerate']))
                            for index, device in enumerate(sd.query_devices()) if device['max_input_channels'] > 0}
            self.selector.configure(values=list(self.devices))
            if self.device.get() not in self.devices:
                default = sd.default.device[0]
                self.device.set(next((key for key, value in self.devices.items() if value[0] == default), next(iter(self.devices), "")))
            if not self.devices:
                self.status.set("No audio input found. Connect a microphone and check Windows microphone permissions, then refresh.")
        except Exception as exc:
            self.status.set("Microphone setup unavailable: " + str(exc))

    def controls(self, active):
        self.start_button.configure(state="disabled" if active else "normal")
        self.selector.configure(state="disabled" if active else "readonly")
        self.refresh.configure(state="disabled" if active else "normal")
        for button in (self.pause_button, self.stop_button):
            button.configure(state="normal" if active else "disabled")
        for button in self.result_buttons:
            button.configure(state="normal" if self.output and not active else "disabled")

    def start(self):
        if self.app.batch_running or self.app.conversion_running or self.app.editor_running or self.app.recording_running or self.app.subtitle_running or self.app.mix_running or (self.app.worker and self.app.worker.is_alive()):
            messagebox.showinfo("Audio task running", "Finish the active audio task before recording.")
            return
        if self.device.get() not in self.devices:
            messagebox.showinfo("Choose a microphone", "Connect a microphone, refresh, and select an audio input.")
            return
        winsound.PlaySound(None, 0)
        self.app.recording_running = True
        self.app.busy(False)
        self.controls(True)
        self.pause_button.configure(text="Pause")
        self.pause_button.configure(state="disabled")
        self.stop_button.configure(text="Cancel countdown")
        self.countdown_device = self.devices[self.device.get()]
        self.countdown_remaining = 3
        self.countdown_tick()

    def countdown_tick(self):
        self.countdown_after = None
        if self.countdown_remaining is None:
            return
        if self.countdown_remaining > 0:
            self.timer.set(f"Starting in {self.countdown_remaining}")
            self.status.set("Get ready. Microphone capture starts after the countdown; no audio is being saved yet.")
            self.countdown_remaining -= 1
            self.countdown_after = self.app.root.after(1000, self.countdown_tick)
            return
        self.countdown_remaining = None
        self.stop_button.configure(text="Stop and save")
        self.pause_button.configure(state="normal")
        self.status.set("Recording… Speak into your microphone. Click Stop and save when finished.")
        try:
            self.recorder.start(*self.countdown_device)
        except Exception as exc:
            self.app.recording_running = False
            self.app.busy(False)
            self.controls(False)
            self.status.set("Recording could not start; your previous take is still available.")
            messagebox.showerror("Recording failed", str(exc))

    def pause(self):
        if self.countdown_remaining is not None:
            return
        if self.recorder.paused.is_set():
            self.recorder.paused.clear()
            self.pause_button.configure(text="Pause")
            self.status.set("Recording resumed.")
        else:
            self.recorder.paused.set()
            self.pause_button.configure(text="Resume")
            self.status.set("Paused. This pause will not be included in the saved audio.")

    def stop(self):
        if self.countdown_remaining is not None:
            if self.countdown_after is not None:
                self.app.root.after_cancel(self.countdown_after)
            self.countdown_after = None
            self.countdown_remaining = None
            self.countdown_device = None
            self.app.recording_running = False
            self.app.busy(False)
            self.controls(False)
            self.stop_button.configure(text="Stop and save")
            self.status.set("Countdown cancelled. No new audio was recorded; your previous take is still available.")
            return
        self.recorder.stop.set()
        self.stop_button.configure(state="disabled")
        self.pause_button.configure(state="disabled")
        self.status.set("Saving recording…")

    def poll(self):
        seconds = self.recorder.seconds
        if self.countdown_remaining is None:
            self.timer.set(f"{int(seconds // 60):02d}:{seconds % 60:04.1f}")
        self.meter.configure(value=self.recorder.level)
        try:
            kind, value = self.recorder.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.app.recording_running = False
            self.app.busy(False)
            if kind == "complete":
                self.output, warning = value
                self.status.set("Saved: " + self.output.name + (" — input overflow occurred; review for gaps before using." if warning else " — ready to preview, export, or use as a reference."))
            else:
                self.status.set("Recording failed; your previous take is still available.")
                messagebox.showerror("Recording failed", str(value) + "\nCheck your selected microphone and Windows privacy permissions.")
            self.controls(False)
        self.app.root.after(100, self.poll)

    def play(self):
        try:
            winsound.PlaySound(str(self.output), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except RuntimeError as exc:
            messagebox.showerror("Playback failed", str(exc))

    def export(self):
        filename = filedialog.asksaveasfilename(title="Export recording", initialfile=self.output.name, defaultextension=".wav", filetypes=[("WAV audio", "*.wav")])
        if filename:
            try:
                if Path(filename).resolve() != self.output.resolve():
                    shutil.copyfile(self.output, filename)
                self.status.set("Exported recording to " + filename)
            except OSError as exc:
                messagebox.showerror("Export failed", str(exc))

    def use_reference(self):
        self.app.import_voice(source=self.output)

    def use_subtitles(self):
        if self.app.batch_running or self.app.conversion_running or self.app.editor_running or self.app.recording_running or self.app.subtitle_running or self.app.mix_running or (self.app.worker and self.app.worker.is_alive()):
            messagebox.showinfo("Audio task running", "Finish the active audio task before sending a recording to subtitles.")
            return
        if not self.output:
            messagebox.showinfo("Save a recording first", "Record a take and click Stop and save first.")
            return
        try:
            self.app.subtitles.select_audio(self.output)
            winsound.PlaySound(None, 0)
            self.app.notebook.select(self.app.subtitles.parent)
        except ValueError as exc:
            messagebox.showerror("Cannot use recording", str(exc))

    def open_folder(self):
        directory = DATA / "recordings"
        directory.mkdir(parents=True, exist_ok=True)
        os.startfile(directory)
