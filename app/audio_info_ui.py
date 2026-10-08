"""Read-only audio file information available from every workflow."""
import json
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog,messagebox,ttk

from .storage import ROOT


def available_audio(app):
    choices={}
    def add(label,path):
        if path:
            choices[label]=Path(path)
    add('Text to speech - selected result',app.selected_output())
    if app.subtitles.source:
        add('Audio to subtitles - input',app.subtitles.source.get('audio'))
    add('Voice recorder - saved take',app.recorder_panel.output)
    for title,panel in (('Audio editor',app.editor_panel),('Format converter',app.converter_panel),('Audio cleanup',app.cleanup_panel),('Voice effects',app.effects_panel)):
        add(title+' - input',panel.source)
        add(title+' - saved result',panel.output)
    add('Background music - voice input',app.music_panel.voice)
    add('Background music - music input',app.music_panel.music)
    add('Background music - saved mix',app.music_panel.output)
    selected=app.batch_panel.tree.selection()
    if selected:
        add('Batch processing - selected input',app.batch_panel.files[int(selected[0])])
    return choices


def describe(info):
    seconds=info['duration']
    hours=int(seconds//3600)
    minutes=int(seconds%3600//60)
    remaining=seconds%60
    return {
        'File':Path(info['path']).name,
        'Duration':f'{hours:02d}:{minutes:02d}:{remaining:06.3f} ({seconds:.3f} seconds)',
        'Format':info['format'],
        'Codec / sample type':info['codec'],
        'Sample rate':f"{info['rate']:,} Hz",
        'Channels':f"{info['channels']}"+(' (mono)' if info['channels']==1 else ' (stereo)' if info['channels']==2 else ''),
        'File size':f"{info['bytes']/(1024*1024):.2f} MiB ({info['bytes']:,} bytes)",
        'Duration source':info['duration_basis'],
        'Full path':info['path'],
    }


class AudioInfoDialog(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app.root)
        self.transient(app.root)
        self.app=app
        self.events=queue.Queue()
        self.info=None
        self.loading=False
        self.choices=available_audio(app)
        self.selected=tk.StringVar()
        self.title('Audio file information')
        scale=max(1,self.winfo_fpixels('1i')/96)
        width=min(round(740*scale),self.winfo_screenwidth()-80)
        height=min(round(610*scale),self.winfo_screenheight()-120)
        self.geometry(f'{width}x{height}')
        self.lift()
        self.minsize(width,height)
        frame=ttk.Frame(self,padding=16)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Audio file information',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text='Inspect a local file or audio already loaded in the app. No audio is changed.',wraplength=700).pack(anchor='w',pady=8)
        self.choose_button=ttk.Button(frame,text='Choose audio file...',command=self.choose)
        self.choose_button.pack(anchor='w',pady=6)
        ttk.Label(frame,text='Audio currently loaded in the app').pack(anchor='w',pady=(8,4))
        self.combo=ttk.Combobox(frame,textvariable=self.selected,values=list(self.choices),state='readonly')
        self.combo.pack(fill='x')
        self.combo.bind('<<ComboboxSelected>>',lambda _:self.load(self.choices[self.selected.get()]))
        details=ttk.Frame(frame)
        details.pack(fill='both',expand=True,pady=12)
        self.text=tk.Text(details,height=10,wrap='word',font=('Segoe UI',11),padx=12,pady=12,state='disabled')
        scroll=ttk.Scrollbar(details,command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side='left',fill='both',expand=True)
        scroll.pack(side='right',fill='y')
        self.copy_button=ttk.Button(frame,text='Copy information',command=self.copy,state='disabled')
        self.copy_button.pack(anchor='w',pady=6)
        self.status=tk.StringVar(value='Choose a file to inspect.')
        label=ttk.Label(frame,textvariable=self.status,wraplength=700)
        label.pack(fill='x',pady=6)
        label.bind('<Configure>',lambda e:label.configure(wraplength=max(100,e.width)))
        self.after(100,self.poll)
        tab=app.notebook.tab(app.notebook.select(),'text')
        selected=next((label for label in self.choices if label.startswith(tab+' -')),next(iter(self.choices),None))
        if selected:
            self.selected.set(selected)
            self.load(self.choices[selected])

    def choose(self):
        source=filedialog.askopenfilename(parent=self,title='Inspect audio file',filetypes=[('Audio','*.wav *.mp3 *.m4a *.flac *.ogg *.opus *.aac *.wma *.aiff'),('All files','*.*')])
        if source:
            self.selected.set('Chosen file: '+Path(source).name)
            self.load(Path(source))

    def load(self,source):
        if self.loading:
            return
        self.loading=True
        self.choose_button.configure(state='disabled')
        self.combo.configure(state='disabled')
        self.copy_button.configure(state='disabled')
        self.info=None
        self.text.configure(state='normal')
        self.text.delete('1.0','end')
        self.text.configure(state='disabled')
        self.status.set('Reading file information...')
        interpreter=ROOT/'runtime/qwen/python.exe'
        if not interpreter.is_file():
            interpreter=ROOT/'.venv-qwen/Scripts/python.exe'
        if not interpreter.is_file():
            interpreter=Path(sys.executable)
        def work():
            try:
                result=subprocess.run([str(interpreter),'-E','-s','-m','app.audio_info'],cwd=ROOT,input=json.dumps({'source':str(source)})+'\n',text=True,encoding='utf-8',capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
                result=json.loads(result.stdout)
                if not result['ok']:
                    raise ValueError(result['error'])
                self.events.put(('complete',result['result']))
            except Exception as exc:
                self.events.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            kind,value=self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.loading=False
            self.choose_button.configure(state='normal')
            self.combo.configure(state='readonly')
            if kind=='complete':
                self.info=value
                self.text.configure(state='normal')
                self.text.insert('1.0','\n\n'.join(f'{key}: {value}' for key,value in describe(self.info).items()))
                self.text.configure(state='disabled')
                self.copy_button.configure(state='normal')
                self.status.set('Information read successfully. Compressed audio durations can include codec padding.')
            else:
                self.status.set('Could not inspect this file. Choose another audio file.')
                messagebox.showerror('Audio file information',value,parent=self)
        self.after(100,self.poll)

    def copy(self):
        if self.info:
            self.clipboard_clear()
            self.clipboard_append('\n'.join(f'{key}: {value}' for key,value in describe(self.info).items()))
            self.status.set('File information copied to clipboard.')
