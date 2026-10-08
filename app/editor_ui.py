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
        from .waveform_playback import WaveformPlayback
        self.playback = WaveformPlayback()
        self.playhead_time = 0.0
        self.preview_start = 0.0
        self.playback_label = tk.StringVar(value='Playhead: 0.000s')
        self.events = queue.Queue()
        self.start_time = tk.StringVar(value='0')
        self.end_time = tk.StringVar(value='0')
        self.fade_in = tk.StringVar(value='0')
        self.fade_out = tk.StringVar(value='0')
        self.gain = tk.DoubleVar(value=1)
        from .edit_history import EditHistory
        self.history = EditHistory()
        self.history_timer = None
        self.history_muted = False
        self.history_gesture = False
        self.history_variables = (self.start_time, self.end_time, self.fade_in, self.fade_out, self.gain)
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
        self.redo_button = ttk.Button(row, text='Redo', command=lambda: self.restore_history(False), state='disabled')
        self.redo_button.pack(side='right')
        self.undo_button = ttk.Button(row, text='Undo', command=lambda: self.restore_history(True), state='disabled')
        self.undo_button.pack(side='right', padx=5)
        ttk.Label(frame, textvariable=self.source_label, wraplength=820).pack(anchor='w', pady=10)
        self.canvas = tk.Canvas(frame, height=140, background='#10233f', highlightthickness=0)
        self.canvas.pack(fill='x')
        self.canvas.bind('<Configure>', lambda _: self.draw())
        self.canvas.bind('<Button-1>', self.drag_start)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.drag_end)
        self.canvas.bind('<Shift-Button-1>', self.seek_waveform)
        playback_row = ttk.Frame(frame)
        playback_row.pack(fill='x', pady=4)
        self.play_button = ttk.Button(playback_row, text='Play source', command=self.play_source)
        self.play_button.pack(side='left')
        self.pause_button = ttk.Button(playback_row, text='Pause', command=self.pause_playback)
        self.pause_button.pack(side='left', padx=5)
        ttk.Button(playback_row, text='Stop', command=self.stop_playback).pack(side='left')
        ttk.Button(playback_row, text='Set start here', command=lambda: self.set_boundary(True)).pack(side='left', padx=5)
        ttk.Button(playback_row, text='Set end here', command=lambda: self.set_boundary(False)).pack(side='left')
        ttk.Label(playback_row, textvariable=self.playback_label).pack(side='right')
        ttk.Label(frame, textvariable=self.selection_label).pack(anchor='w', pady=3)
        settings = ttk.LabelFrame(frame, text='Selection and finishing', padding=10)
        settings.pack(fill='x', pady=8)
        for index, (title, variable) in enumerate((('Start (seconds)', self.start_time), ('End (seconds)', self.end_time), ('Fade in (seconds)', self.fade_in), ('Fade out (seconds)', self.fade_out))):
            column = (index % 2) * 2
            ttk.Label(settings, text=title).grid(row=index // 2, column=column, sticky='w', padx=(0, 8), pady=4)
            entry = ttk.Entry(settings, textvariable=variable, width=12)
            entry.grid(row=index // 2, column=column + 1, sticky='w', padx=(0, 20))
            self.controls.append(entry)
            entry.bind('<FocusOut>', lambda _: self.flush_history())
        self.volume_label = tk.StringVar()
        ttk.Label(settings, textvariable=self.volume_label).grid(row=2, column=0, sticky='w', pady=6)
        volume = ttk.Scale(settings, from_=0, to=2, variable=self.gain)
        volume.grid(row=2, column=1, columnspan=3, sticky='ew')
        self.controls.append(volume)
        volume.bind('<ButtonPress-1>', lambda _: self.begin_history_gesture())
        volume.bind('<ButtonRelease-1>', lambda _: self.end_history_gesture())
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
        ttk.Label(frame, text='Drag to select; Shift-click to seek. Play source ignores finishing settings; Preview selection includes volume/fades.\nThe highlight is kept. Saving preserves the source; export uses the last saved edit.', wraplength=820).pack(anchor='w', pady=6)
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(fill='x', pady=6)
        label = ttk.Label(frame, textvariable=self.status, wraplength=820)
        label.pack(fill='x')
        label.bind('<Configure>', lambda e: label.configure(wraplength=max(100, e.width)))
        for variable in self.history_variables:
            variable.trace_add('write', self.settings_changed)
        for sequence, undo in (('<Control-z>', True), ('<Control-y>', False), ('<Control-Shift-Z>', False)):
            app.root.bind(sequence, lambda event, undo=undo: self.history_shortcut(event, undo), add='+')
        app.root.after(100, self.poll)

    def history_state(self):
        # Keep text exactly, including intermediate invalid input, so Undo can recover it.
        return tuple(str(variable.get()) for variable in self.history_variables)

    def settings_changed(self, *_):
        if self.history_muted or self.history_gesture or not self.info:
            return
        if self.history_timer:
            self.app.root.after_cancel(self.history_timer)
        self.history_timer = self.app.root.after(450, self.flush_history)
        self.refresh_history_buttons()

    def flush_history(self):
        if self.history_timer:
            self.app.root.after_cancel(self.history_timer)
            self.history_timer = None
        if self.info and not self.history_muted and not self.history_gesture:
            self.history.record(self.history_state())
        self.refresh_history_buttons()

    def begin_history_gesture(self):
        self.flush_history()
        self.history_gesture = True

    def end_history_gesture(self):
        self.history_gesture = False
        self.flush_history()

    def refresh_history_buttons(self):
        available = self.info is not None and not self.occupied() and not self.history_gesture
        pending = self.info is not None and self.history.current != self.history_state()
        self.undo_button.configure(state='normal' if available and (self.history.past or pending) else 'disabled')
        self.redo_button.configure(state='normal' if available and self.history.future and not pending else 'disabled')

    def restore_history(self, undo):
        if not self.info or self.occupied() or self.history_gesture:
            return
        self.flush_history()
        if not (self.history.past if undo else self.history.future):
            return
        self.stop_playback()
        state = self.history.undo() if undo else self.history.redo()
        self.history_muted = True
        try:
            for variable, value in zip(self.history_variables, state):
                variable.set(value)
        finally:
            self.history_muted = False
        self.draw()
        self.refresh_history_buttons()
        self.status.set(('Undid' if undo else 'Redid') + ' editor settings. Preview or save again to apply them; saved audio is unchanged.')

    def history_shortcut(self, event, undo):
        widget = event.widget
        if widget.winfo_toplevel() != self.app.root:
            return
        if self.app.notebook.index('current') == 4:
            self.restore_history(undo)
            return 'break'

    def play_source(self):
        if not self.source or self.occupied():
            return
        winsound.PlaySound(None, 0)
        try:
            position = self.playhead_time if self.info and self.playhead_time < self.info['duration'] else 0
            self.playback.start(self.source, position=position)
        except Exception as exc:
            messagebox.showerror('Playback failed', str(exc))

    def pause_playback(self):
        try:
            if self.playback.playing:
                self.playback.pause()
            elif self.playback.path and not self.occupied():
                self.playback.resume()
        except Exception as exc:
            messagebox.showerror('Playback failed', str(exc))

    def stop_playback(self):
        self.playback.stop()
        winsound.PlaySound(None, 0)
        self.playhead_time = 0.0
        self.draw_playhead()
        if self.info:
            self.status.set('Playback stopped. Shift-click to seek or drag to select.')

    def seek_waveform(self, event):
        if self.info and not self.occupied():
            position = self.position(event)
            try:
                # Seeking the waveform always switches back to the original source timeline.
                if self.playback.playing:
                    self.playback.start(self.source, position=position)
                else:
                    self.playback.stop()
                    self.playback.path = self.source
                    self.playback.offset = 0
                    self.playback.rate = self.info['rate']
                    self.playback.frames = round(self.info['duration'] * self.info['rate'])
                    self.playback.cursor = position
                self.playhead_time = position
                self.draw_playhead()
            except Exception as exc:
                messagebox.showerror('Playback failed', str(exc))
        return 'break'

    def set_boundary(self, start):
        if not self.info or self.occupied():
            return
        current = self.playback.offset + self.playback.position if self.playback.path else self.playhead_time
        position = min(self.info['duration'], max(0, current))
        try:
            other = float(self.end_time.get() if start else self.start_time.get())
            if (start and position >= other) or (not start and position <= other):
                raise ValueError('Start must be before end. Seek to a point inside the desired range.')
            self.flush_history()
            (self.start_time if start else self.end_time).set(f'{position:.6f}')
            self.flush_history()
        except ValueError as exc:
            messagebox.showerror('Invalid selection boundary', str(exc))

    def draw_playhead(self):
        self.canvas.delete('playhead')
        if self.info:
            x = self.canvas.winfo_width() * self.playhead_time / self.info['duration']
            self.canvas.create_line(x, 0, x, self.canvas.winfo_height(), fill='#ffcc66', width=2, tags='playhead')
        self.playback_label.set(f'Playhead: {self.playhead_time:.3f}s')
        self.pause_button.configure(text='Pause' if self.playback.playing else 'Resume')
        self.pause_button.configure(state='normal' if self.playback.path and not self.occupied() else 'disabled')
        self.play_button.configure(state='normal' if self.source and not self.occupied() else 'disabled')

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
        self.end_history_gesture()
        self.stop_playback()
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
            self.begin_history_gesture()
            self.start_time.set('0')
            self.end_time.set(f"{self.info['duration']:.6f}")
            self.fade_in.set('0')
            self.fade_out.set('0')
            self.gain.set(1)
            self.end_history_gesture()

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
        self.draw_playhead()

    def position(self, event):
        return max(0, min(1, event.x / max(1, self.canvas.winfo_width()))) * self.info['duration']

    def drag_start(self, event):
        if self.info and not self.occupied():
            self.begin_history_gesture()
            self.anchor = self.position(event)

    def drag(self, event):
        if self.info and hasattr(self, 'anchor') and not self.occupied():
            position = self.position(event)
            self.start_time.set(f'{min(position, self.anchor):.6f}')
            self.end_time.set(f'{max(position, self.anchor):.6f}')

    def drag_end(self, event):
        if hasattr(self, 'anchor'):
            self.drag(event)
            del self.anchor
            self.end_history_gesture()

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
        self.preview_start = values[0]
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
                self.flush_history()
                self.history_muted = True
                _, self.source, self.info = result
                self.source_label.set(f"{self.source.name} | {self.info['duration']:.2f}s | {self.info['rate']} Hz | {self.info['channels']} channel(s)")
                self.reset()
                self.history_muted = False
                self.history.reset(self.history_state())
                self.status.set('Audio loaded. Drag across the waveform or enter start and end times.')
            else:
                action, path, source, info = result
                self.status.set(('Playing joined clips.' if action == 'join_preview' else 'Playing selection.' if action == 'preview' else 'Saved joined WAV: ' + path.name if action == 'joined' else 'Saved edit: ' + path.name) + (' Volume reached clipping; lower it and save again.' if info['clipped'] else ''))
                if action in ('preview', 'join_preview'):
                    try:
                        if action == 'preview':
                            self.playback.start(path, offset=self.preview_start)
                        else:
                            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                    except Exception as exc:
                        messagebox.showerror('Playback failed', str(exc))
                else:
                    self.output = path
                    self.output_sources = source if isinstance(source, tuple) else (source,)
                    self.output_source = self.output_sources[0]
            for button in (self.export_button, self.reference_button):
                button.configure(state='normal' if self.output else 'disabled')
        try:
            was_playing = self.playback.playing
            self.playback.refresh()
            if was_playing and not self.playback.playing and not self.playback.error:
                self.status.set('Playback finished. Shift-click to seek or Play source to listen again.')
            if self.playback.path:
                self.playhead_time = self.playback.offset + self.playback.position
            self.draw_playhead()
            if self.playback.error:
                self.status.set('Playback failed: ' + self.playback.error)
                self.playback.error = None
        except Exception as exc:
            self.stop_playback()
            self.status.set('Playback failed: ' + str(exc))
        self.app.root.after(50, self.poll)
        self.refresh_history_buttons()

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
