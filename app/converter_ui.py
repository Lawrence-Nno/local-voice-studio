"""Native offline format conversion and separate-file export."""
import json
import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .storage import ROOT, DATA

EXTENSIONS = {'WAV': '.wav', 'MP3': '.mp3', 'FLAC': '.flac', 'M4A (AAC)': '.m4a', 'OGG (Opus)': '.ogg'}


class ConverterPanel:
    def __init__(self, app, parent):
        self.app = app
        self.source = self.output = self.output_source = None
        self.process = None
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.format = tk.StringVar(value='MP3')
        self.rate = tk.StringVar(value='44100')
        self.channels = tk.StringVar(value='Keep source')
        self.bitrate = tk.StringVar(value='192')
        self.filename = tk.StringVar(value='No audio selected')
        self.status = tk.StringVar(value='Open audio and choose an output format. Conversion runs entirely on this computer.')
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Format converter', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Create a separate file in a different audio format. Your original file stays unchanged.', wraplength=820).pack(anchor='w', pady=(6, 16))
        row = ttk.Frame(frame)
        row.pack(fill='x')
        self.controls = []
        for title, command in (('Open audio...', self.choose), ('Use latest recording', lambda: self.use(self.app.recorder_panel.output)), ('Use selected generated speech', lambda: self.use(self.app.selected_output()))):
            button = ttk.Button(row, text=title, command=command)
            button.pack(side='left', padx=(0, 8))
            self.controls.append(button)
        button = ttk.Button(frame, text='Use last saved audio edit', command=lambda: self.use(self.app.editor_panel.output))
        button.pack(anchor='w', pady=8)
        self.controls.append(button)
        label = ttk.Label(frame, textvariable=self.filename, wraplength=820)
        label.pack(fill='x', pady=8)
        label.bind('<Configure>', lambda e: label.configure(wraplength=max(100, e.width)))
        options = ttk.LabelFrame(frame, text='Output settings', padding=16)
        options.pack(fill='x', pady=12)
        self.choices = []
        for index, (title, variable, values) in enumerate((('Format', self.format, tuple(EXTENSIONS)), ('Sample rate (Hz)', self.rate, ('24000','44100','48000')), ('Channels', self.channels, ('Keep source','Mono','Stereo')), ('Compressed audio bitrate (kbps)', self.bitrate, ('96','128','192','256','320')))):
            ttk.Label(options, text=title).grid(row=index, column=0, sticky='w', padx=(0,20), pady=8)
            combo = ttk.Combobox(options, textvariable=variable, values=values, state='readonly', width=20)
            combo.grid(row=index, column=1, sticky='w')
            self.choices.append(combo)
        self.format.trace_add('write', lambda *_: self.update_options())
        self.update_options()
        ttk.Label(frame, text='WAV: uncompressed PCM16. FLAC: lossless compression of PCM16 audio.\nMP3 and M4A/AAC: smaller, lossy files; higher bitrates usually retain more detail.\nOGG/Opus uses 48,000 Hz. Changing format cannot restore detail lost in a compressed source.\nKeep source retains mono/stereo; select Mono or Stereo to downmix multichannel inputs.', wraplength=820).pack(anchor='w', pady=10)
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=12)
        self.convert_button = ttk.Button(row, text='Convert audio', style='Primary.TButton', command=self.start)
        self.convert_button.pack(side='left')
        self.controls.append(self.convert_button)
        self.cancel_button = ttk.Button(row, text='Cancel', command=self.cancel.set, state='disabled')
        self.cancel_button.pack(side='left', padx=8)
        self.export_button = ttk.Button(row, text='Export converted file...', command=self.export, state='disabled')
        self.export_button.pack(side='left')
        ttk.Button(frame, text='Open converted files folder', command=self.open_folder).pack(anchor='w', pady=8)
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(fill='x', pady=8)
        label = ttk.Label(frame, textvariable=self.status, wraplength=820)
        label.pack(fill='x')
        label.bind('<Configure>', lambda e: label.configure(wraplength=max(100,e.width)))
        app.root.after(100,self.poll)

    def update_options(self):
        active = self.app.conversion_running
        for choice in self.choices:
            choice.configure(state='disabled' if active else 'readonly')
        if not active:
            if self.format.get() in ('WAV','FLAC'):
                self.choices[3].configure(state='disabled')
            if self.format.get() == 'OGG (Opus)':
                self.choices[1].configure(state='disabled')

    def choose(self):
        filename = filedialog.askopenfilename(title='Choose audio to convert', filetypes=[('Audio','*.wav *.mp3 *.m4a *.flac *.ogg *.opus *.aac *.wma *.aiff'),('All files','*.*')])
        if filename:
            self.use(Path(filename))

    def use(self, source):
        if source and Path(source).is_file():
            self.source = Path(source)
            self.filename.set(str(self.source))
            self.status.set('Ready to convert. Export uses the last completed conversion.')
        else:
            messagebox.showinfo('Choose audio first','Open an audio file, or finish recording, generation, or editing first.')

    def start(self):
        if self.app.conversion_running or self.app.editor_running or self.app.recording_running or self.app.subtitle_running or self.app.mix_running or (self.app.worker and self.app.worker.is_alive()):
            messagebox.showinfo('Audio task running','Finish the active audio task first.')
            return
        if not self.source or not self.source.is_file():
            messagebox.showinfo('Choose audio first','Open an existing audio file to convert.')
            return
        interpreter = ROOT/'runtime/qwen/python.exe'
        if not interpreter.is_file():
            interpreter = ROOT/'.venv-qwen/Scripts/python.exe'
        if not interpreter.is_file():
            messagebox.showerror('Audio runtime missing','Install the Qwen/subtitle audio runtime first.')
            return
        source = self.source
        format_name = self.format.get()
        output = DATA/'converted'/(uuid.uuid4().hex+EXTENSIONS[format_name])
        temporary = output.with_name(output.stem+'.partial'+output.suffix)
        request = {'source':str(source),'destination':str(temporary),'format_name':format_name,'rate':int(self.rate.get()),'channels':self.channels.get(),'bitrate':int(self.bitrate.get())*1000}
        self.cancel.clear()
        self.app.conversion_running = True
        self.app.busy(False)
        for button in self.controls:
            button.configure(state='disabled')
        self.update_options()
        self.export_button.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        self.progress.start()
        self.status.set('Converting locally...')
        def work():
            process = None
            try:
                process = subprocess.Popen([str(interpreter),'-E','-s','-m','app.conversion_worker'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
                self.process = process
                payload = json.dumps(request)+'\n'
                while True:
                    if self.cancel.is_set():
                        process.terminate()
                        process.communicate()
                        self.events.put(('cancelled',None))
                        return
                    try:
                        stdout, stderr = process.communicate(input=payload,timeout=.2)
                        break
                    except subprocess.TimeoutExpired:
                        payload = None
                if self.cancel.is_set():
                    self.events.put(('cancelled',None))
                    return
                result = json.loads(stdout)
                if not result['ok']:
                    raise ValueError(result['error'])
                temporary.replace(output)
                self.events.put(('complete',(output,source,result['result'])))
            except Exception as exc:
                self.events.put(('error',str(exc)))
            finally:
                if process and process.poll() is None:
                    process.terminate()
                    process.communicate()
                self.process = None
                temporary.unlink(missing_ok=True)
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            kind, value = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.app.conversion_running = False
            self.app.busy(False)
            self.progress.stop()
            for button in self.controls:
                button.configure(state='normal')
            self.update_options()
            self.cancel_button.configure(state='disabled')
            if kind == 'complete':
                self.output,self.output_source,info = value
                self.status.set(f"Converted: {info['format']} | {info['duration']:.2f}s | {info['rate']} Hz | {info['channels']} channel(s) | {info['bytes']/1024:.1f} KB. Ready to export.")
            elif kind == 'cancelled':
                self.status.set('Conversion cancelled. Previous converted file is still available.')
            else:
                self.status.set('Conversion failed. Source and previous result are unchanged.')
                messagebox.showerror('Conversion failed',value)
            self.export_button.configure(state='normal' if self.output else 'disabled')
        self.app.root.after(100,self.poll)

    def export(self):
        filename = filedialog.asksaveasfilename(title='Export converted audio',defaultextension=self.output.suffix,initialfile=self.output_source.stem+'-converted'+self.output.suffix,filetypes=[('Converted audio','*'+self.output.suffix)])
        if filename:
            try:
                path = Path(filename).resolve()
                if path in {p.resolve() for p in (self.source,self.output_source) if p}:
                    raise ValueError('Choose a different filename to preserve the source audio.')
                if path.suffix.lower() != self.output.suffix:
                    raise ValueError('Use the converted file extension: '+self.output.suffix)
                if path != self.output.resolve():
                    shutil.copyfile(self.output,path)
                self.status.set('Exported converted file to '+filename)
            except (OSError,ValueError) as exc:
                messagebox.showerror('Export failed',str(exc))

    def open_folder(self):
        directory = DATA/'converted'
        directory.mkdir(parents=True,exist_ok=True)
        os.startfile(directory)
