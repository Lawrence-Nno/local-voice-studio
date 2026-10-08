"""Waveform selection, trim, volume, fades, preview and export."""
import queue
import shutil
import threading
import tkinter as tk
import uuid
import winsound
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .audio_editor import scan_audio, render_edit
from .storage import DATA


class EditorPanel:
    def __init__(self, app, parent):
        self.app = app
        self.source = self.output = self.output_source = None
        self.output_sources = ()
        self.join_dialog = None
        self.info = None
        self.events = queue.Queue()
        self.start_time = tk.StringVar(value='0')
        self.end_time = tk.StringVar(value='0')
        self.fade_in = tk.StringVar(value='0')
        self.fade_out = tk.StringVar(value='0')
        self.gain = tk.DoubleVar(value=1)
        self.status = tk.StringVar(value='Open audio or use a take from Voice recorder. Edits are saved as new files.')
        self.source_label = tk.StringVar(value='No audio selected')
        self.selection_label = tk.StringVar(value='Drag across the waveform to select a section.')
        frame = ttk.Frame(parent, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Audio editor', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Select a section, preview it, and save a trimmed WAV. Adjust volume or add fades before saving.', wraplength=820).pack(anchor='w', pady=(4, 12))
        row = ttk.Frame(frame)
        row.pack(fill='x')
        self.controls = []
        for title, command in (('Open audio...', self.choose), ('Use latest recording', self.use_recording), ('Use selected generated speech', self.use_generated)):
            button = ttk.Button(row, text=title, command=command)
            button.pack(side='left', padx=(0, 8))
            self.controls.append(button)
        ttk.Label(frame, textvariable=self.source_label, wraplength=820).pack(anchor='w', pady=10)
        self.canvas = tk.Canvas(frame, height=170, background='#10233f', highlightthickness=0)
        self.canvas.pack(fill='x')
        self.canvas.bind('<Configure>', lambda _: self.draw())
        self.canvas.bind('<Button-1>', self.drag_start)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.drag)
        ttk.Label(frame, textvariable=self.selection_label).pack(anchor='w', pady=6)
        settings = ttk.LabelFrame(frame, text='Selection and finishing', padding=10)
        settings.pack(fill='x', pady=8)
        for index, (title, variable) in enumerate((('Start (seconds)', self.start_time), ('End (seconds)', self.end_time), ('Fade in (seconds)', self.fade_in), ('Fade out (seconds)', self.fade_out))):
            column = (index % 2) * 2
            ttk.Label(settings, text=title).grid(row=index // 2, column=column, sticky='w', padx=(0, 8), pady=4)
            entry = ttk.Entry(settings, textvariable=variable, width=12)
            entry.grid(row=index // 2, column=column + 1, sticky='w', padx=(0, 20))
            self.controls.append(entry)
        self.volume_label = tk.StringVar()
        ttk.Label(settings, textvariable=self.volume_label).grid(row=2, column=0, sticky='w', pady=6)
        volume = ttk.Scale(settings, from_=0, to=2, variable=self.gain)
        volume.grid(row=2, column=1, columnspan=3, sticky='ew')
        self.controls.append(volume)
        self.gain.trace_add('write', lambda *_: self.volume_label.set(f'Volume: {self.gain.get():.0%}'))
        self.volume_label.set('Volume: 100%')
        for variable in (self.start_time, self.end_time):
            variable.trace_add('write', lambda *_: self.draw())
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=8)
        for title, command in (('Select all / reset', self.reset), ('Preview selection', lambda: self.render(True)), ('Save edited WAV', lambda: self.render(False))):
            button = ttk.Button(row, text=title, command=command)
            button.pack(side='left', padx=(0, 8))
            self.controls.append(button)
        ttk.Button(row, text='Stop playback', command=lambda: winsound.PlaySound(None, 0)).pack(side='left')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=8)
        self.export_button = ttk.Button(row, text='Export saved edit...', command=self.export, state='disabled')
        self.export_button.pack(side='left', padx=(0, 8))
        self.reference_button = ttk.Button(row, text='Use saved edit as voice reference', command=self.use_reference, state='disabled')
        self.reference_button.pack(side='left')
        self.join_button = ttk.Button(row, text='Join clips...', command=self.open_join)
        self.join_button.pack(side='left', padx=8)
        self.controls.append(self.join_button)
        from .audio_shortcuts import AudioShortcuts
        self.shortcuts = AudioShortcuts(app, self, row, 'Send saved edit to...')
        ttk.Label(frame, text='The highlighted section is kept; audio outside it is removed. Preview includes your volume and fades.\nSaving preserves the source sample rate and channels. Export uses the last saved edit; changed settings require saving again.', wraplength=820).pack(anchor='w', pady=8)
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(fill='x', pady=6)
        label = ttk.Label(frame, textvariable=self.status, wraplength=820)
        label.pack(fill='x')
        label.bind('<Configure>', lambda e: label.configure(wraplength=max(100, e.width)))
        app.root.after(100, self.poll)

    def occupied(self):
        return self.app.batch_running or self.app.conversion_running or self.app.editor_running or self.app.recording_running or self.app.subtitle_running or self.app.mix_running or (self.app.worker and self.app.worker.is_alive())

    def open_join(self):
        if self.join_dialog and self.join_dialog.winfo_exists():
            self.join_dialog.lift()
            return
        from .join_ui import JoinDialog
        self.join_dialog = JoinDialog(self)

    def join_clips(self, clips, rate, channels, gap, preview):
        import json
        import subprocess
        from .storage import ROOT
        interpreter = ROOT / 'runtime/qwen/python.exe'
        if not interpreter.is_file():
            interpreter = ROOT / '.venv-qwen/Scripts/python.exe'
        if not interpreter.is_file():
            raise ValueError('Install the Qwen/subtitle audio runtime first.')
        path = DATA / ('editor-previews' if preview else 'edits') / (uuid.uuid4().hex + '.wav')
        sources = tuple(Path(clip['source']) for clip in clips)
        winsound.PlaySound(None, 0)
        def operation():
            request = {'clips': clips, 'destination': str(path), 'rate': rate, 'channels': channels, 'gap': gap}
            result = subprocess.run([str(interpreter), '-E', '-s', '-m', 'app.clip_joining'], cwd=ROOT,
                input=json.dumps(request)+'\n', text=True, encoding='utf-8', capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            response = json.loads(result.stdout)
            if not response['ok']:
                raise ValueError(response['error'])
            return ('join_preview' if preview else 'joined', path, sources, response['result'])
        self.run(operation)

    def run(self, operation):
        if self.occupied():
            messagebox.showinfo('Audio task running', 'Finish the active audio task first.')
            return
        self.app.editor_running = True
        self.app.busy(False)
        for control in self.controls:
            control.configure(state='disabled')
        self.export_button.configure(state='disabled')
        self.reference_button.configure(state='disabled')
        self.progress.start()
        self.status.set('Processing audio locally...')
        def work():
            try:
                self.events.put(('complete', operation()))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def choose(self):
        filename = filedialog.askopenfilename(title='Open audio to edit', filetypes=[('Audio files', '*.wav *.flac *.ogg *.mp3'), ('All files', '*.*')])
        if filename:
            self.load(Path(filename))

    def load(self, source):
        source = Path(source)
        self.run(lambda: ('loaded', source, scan_audio(source)))

    def use_recording(self):
        if self.app.recorder_panel.output:
            self.load(self.app.recorder_panel.output)
        else:
            messagebox.showinfo('Record a take first', 'Stop and save a take in the Voice recorder tab first.')

    def use_generated(self):
        source = self.app.selected_output()
        if source:
            self.load(source)
        else:
            messagebox.showinfo('Generate speech first', 'Complete a text-to-speech generation first.')

    def reset(self):
        if self.info:
            self.start_time.set('0')
            self.end_time.set(f"{self.info['duration']:.6f}")
            self.fade_in.set('0')
            self.fade_out.set('0')
            self.gain.set(1)

    def draw(self):
        self.canvas.delete('all')
        if not self.info:
            self.canvas.create_text(max(1, self.canvas.winfo_width()) / 2, 85, text='Open audio to display its waveform', fill='#a8c4e6')
            return
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        duration = self.info['duration']
        try:
            start, end = float(self.start_time.get()), float(self.end_time.get())
            if 0 <= start < end <= duration + .000001:
                self.canvas.create_rectangle(width * start / duration, 0, width * end / duration, height, fill='#204b79', outline='')
                self.selection_label.set(f'Selected: {start:.3f}s to {end:.3f}s | duration {end-start:.3f}s')
            else:
                self.selection_label.set('Enter a valid selection within the audio duration.')
        except ValueError:
            self.selection_label.set('Enter start and end times in seconds.')
        peaks = self.info['peaks']
        for index, (low, high) in enumerate(peaks):
            x = (index + .5) * width / len(peaks)
            self.canvas.create_line(x, height/2-low*height*.44, x, height/2-high*height*.44, fill='#51dbef')
        self.canvas.create_line(0, height/2, width, height/2, fill='#6683a3')
        self.canvas.create_text(8, height-12, anchor='w', text='0.00s', fill='#c4d8f1')
        self.canvas.create_text(width-8, height-12, anchor='e', text=f'{duration:.2f}s', fill='#c4d8f1')

    def position(self, event):
        return max(0, min(1, event.x / max(1, self.canvas.winfo_width()))) * self.info['duration']

    def drag_start(self, event):
        if self.info and not self.app.editor_running:
            self.anchor = self.position(event)

    def drag(self, event):
        if self.info and hasattr(self, 'anchor') and not self.app.editor_running:
            position = self.position(event)
            self.start_time.set(f'{min(position, self.anchor):.6f}')
            self.end_time.set(f'{max(position, self.anchor):.6f}')

    def render(self, preview):
        if not self.source:
            messagebox.showinfo('Open audio first', 'Open audio or select a recorded take first.')
            return
        try:
            values = [float(var.get()) for var in (self.start_time, self.end_time, self.gain, self.fade_in, self.fade_out)]
        except (ValueError, tk.TclError):
            messagebox.showerror('Invalid settings', 'Enter numbers for all edit settings.')
            return
        source = self.source
        directory = DATA / ('editor-previews' if preview else 'edits')
        path = directory / (uuid.uuid4().hex + '.wav')
        winsound.PlaySound(None, 0)
        self.run(lambda: ('preview' if preview else 'saved', path, source, render_edit(source, path, *values)))

    def poll(self):
        try:
            kind, result = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.app.editor_running = False
            self.app.busy(False)
            self.progress.stop()
            for control in self.controls:
                control.configure(state='normal')
            if kind == 'error':
                self.status.set('Edit failed. Your source and last saved edit are unchanged.')
                messagebox.showerror('Audio editor', result)
            elif result[0] == 'loaded':
                _, self.source, self.info = result
                self.source_label.set(f"{self.source.name} | {self.info['duration']:.2f}s | {self.info['rate']} Hz | {self.info['channels']} channel(s)")
                self.reset()
                self.status.set('Audio loaded. Drag across the waveform or enter start and end times.')
            else:
                action, path, source, info = result
                self.status.set(('Playing joined clips.' if action == 'join_preview' else 'Playing selection.' if action == 'preview' else 'Saved joined WAV: ' + path.name if action == 'joined' else 'Saved edit: ' + path.name) + (' Volume reached clipping; lower it and save again.' if info['clipped'] else ''))
                if action in ('preview', 'join_preview'):
                    try:
                        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                    except RuntimeError as exc:
                        messagebox.showerror('Playback failed', str(exc))
                else:
                    self.output = path
                    self.output_sources = source if isinstance(source, tuple) else (source,)
                    self.output_source = self.output_sources[0]
            for button in (self.export_button, self.reference_button):
                button.configure(state='normal' if self.output else 'disabled')
        self.app.root.after(100, self.poll)

    def export(self):
        filename = filedialog.asksaveasfilename(title='Export last saved edit', defaultextension='.wav', initialfile='edited-audio.wav', filetypes=[('WAV audio', '*.wav')])
        if filename:
            try:
                destination = Path(filename).resolve()
                if destination in {p.resolve() for p in (self.source, self.output_source, *self.output_sources) if p}:
                    raise ValueError('Choose another filename to preserve your original audio.')
                if destination != self.output.resolve():
                    shutil.copyfile(self.output, destination)
                self.status.set('Exported saved edit to ' + filename)
            except (OSError, ValueError) as exc:
                messagebox.showerror('Export failed', str(exc))

    def use_reference(self):
        self.app.import_voice(source=self.output)
