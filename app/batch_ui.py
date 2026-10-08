"""Batch queue using snapshots of the existing audio workflow settings."""
import os
import queue
import threading
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog,messagebox,ttk

from .storage import ROOT,DATA
from .batch_processing import run_batch


class BatchPanel:
    def __init__(self,app,parent):
        self.app=app
        self.files=[]
        self.output_base=DATA/'batches'
        self.last_directory=None
        self.cancel=threading.Event()
        self.events=queue.Queue()
        self.operation=tk.StringVar(value='Cleanup')
        self.continue_errors=tk.BooleanVar(value=True)
        self.status=tk.StringVar(value='Add files and choose one operation. Settings are copied from its tab when you start.')
        self.location=tk.StringVar(value=str(self.output_base))
        frame=ttk.Frame(parent,padding=16)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Batch processing',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text='Clean up, convert, or transcribe several files in one run. Originals stay unchanged; each run gets a new output folder.',wraplength=820).pack(anchor='w',pady=(4,12))
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=8)
        self.controls=[]
        for title,command in (('Add audio files...',self.add_files),('Remove selected',self.remove),('Clear queue',self.clear)):
            button=ttk.Button(row,text=title,command=command)
            button.pack(side='left',padx=(0,8))
            self.controls.append(button)
        self.tree=ttk.Treeview(frame,columns=('file','status','result'),show='headings',height=7,selectmode='extended')
        for column,title,width in (('file','Input file',300),('status','Status',100),('result','Result / error',380)):
            self.tree.heading(column,text=title)
            self.tree.column(column,width=width,minwidth=60)
        self.tree.pack(fill='both',expand=True,pady=6)
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=8)
        ttk.Label(row,text='Operation').pack(side='left',padx=(0,8))
        self.operations=ttk.Combobox(row,textvariable=self.operation,state='readonly',values=('Cleanup','Convert','Subtitles'),width=12)
        self.operations.pack(side='left')
        self.settings_button=ttk.Button(row,text='Open operation settings',command=self.open_settings)
        self.settings_button.pack(side='left',padx=8)
        ttk.Label(frame,text='Cleanup uses Audio cleanup settings. Convert uses Format converter settings.\nSubtitles uses language/device from Audio to subtitles and recognizes speech in each file.\nAdjust settings in that tab, return here, then start. The run keeps a snapshot of those settings.',wraplength=820).pack(anchor='w',pady=6)
        check=ttk.Checkbutton(frame,text='Continue with remaining files if one file fails',variable=self.continue_errors)
        check.pack(anchor='w',pady=6)
        self.controls.append(check)
        button=ttk.Button(frame,text='Choose output location...',command=self.choose_output)
        button.pack(anchor='w',pady=6)
        self.controls.append(button)
        label=ttk.Label(frame,textvariable=self.location,wraplength=820)
        label.pack(fill='x')
        label.bind('<Configure>',lambda e:label.configure(wraplength=max(100,e.width)))
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=12)
        self.start_button=ttk.Button(row,text='Start batch',style='Primary.TButton',command=self.start)
        self.start_button.pack(side='left')
        self.controls.append(self.start_button)
        self.cancel_button=ttk.Button(row,text='Cancel batch',command=self.cancel.set,state='disabled')
        self.cancel_button.pack(side='left',padx=8)
        ttk.Button(row,text='Open last batch folder',command=self.open_folder).pack(side='left')
        self.progress=ttk.Progressbar(frame,maximum=1)
        self.progress.pack(fill='x',pady=8)
        label=ttk.Label(frame,textvariable=self.status,wraplength=820)
        label.pack(fill='x')
        label.bind('<Configure>',lambda e:label.configure(wraplength=max(100,e.width)))
        app.root.after(100,self.poll)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for index,path in enumerate(self.files):
            self.tree.insert('', 'end',iid=str(index),values=(path.name,'Queued',str(path)))

    def add_files(self):
        selected=filedialog.askopenfilenames(title='Queue audio files',filetypes=[('Audio','*.wav *.mp3 *.m4a *.flac *.ogg *.opus *.aac *.wma *.aiff'),('All files','*.*')])
        unique=list(self.files)
        for filename in selected:
            path=Path(filename).resolve()
            if path not in unique:
                unique.append(path)
        if len(unique)>100:
            messagebox.showinfo('Queue limit','Queue up to 100 files per run.')
            return
        self.files=unique
        self.refresh()

    def remove(self):
        selected={int(item) for item in self.tree.selection()}
        self.files=[path for index,path in enumerate(self.files) if index not in selected]
        self.refresh()

    def clear(self):
        self.files.clear()
        self.refresh()

    def choose_output(self):
        selected=filedialog.askdirectory(title='Choose parent folder for batch results')
        if selected:
            self.output_base=Path(selected)
            self.location.set(str(self.output_base))

    def open_settings(self):
        mapping={'Cleanup':self.app.cleanup_panel,'Convert':self.app.converter_panel,'Subtitles':self.app.subtitles}
        panel=mapping[self.operation.get()]
        self.app.notebook.select(panel.parent)

    def snapshot(self,operation):
        if operation=='Cleanup':
            panel=self.app.cleanup_panel
            return {'strength':panel.strength.get(),'volume':panel.volume.get(),'normalize':panel.normalize.get(),'rumble':panel.rumble.get()}
        if operation=='Convert':
            panel=self.app.converter_panel
            return {'format_name':panel.format.get(),'rate':int(panel.rate.get()),'channels':panel.channels.get(),'bitrate':int(panel.bitrate.get())*1000}
        panel=self.app.subtitles
        return {'device':panel.device.get(),'language':'en' if panel.language.get()=='English' else None}

    def start(self):
        if self.app.batch_running or self.app.conversion_running or self.app.editor_running or self.app.recording_running or self.app.subtitle_running or self.app.mix_running or (self.app.worker and self.app.worker.is_alive()):
            messagebox.showinfo('Audio task running','Finish the active audio task first.')
            return
        if not self.files:
            messagebox.showinfo('Add files first','Queue audio files before starting a batch.')
            return
        interpreter=ROOT/'runtime/qwen/python.exe'
        if not interpreter.is_file():
            interpreter=ROOT/'.venv-qwen/Scripts/python.exe'
        operation=self.operation.get()
        if not interpreter.is_file() or (operation=='Subtitles' and not (ROOT/'models/whisper-small/manifest.json').is_file()):
            messagebox.showerror('Audio runtime missing','Install the Qwen/subtitle runtime and subtitle model first.')
            return
        files=tuple(self.files)
        settings=self.snapshot(operation)
        keep_going=self.continue_errors.get()
        directory=self.output_base/('batch-'+uuid.uuid4().hex)
        self.cancel.clear()
        self.app.batch_running=True
        self.app.busy(False)
        self.refresh()
        self.progress.configure(maximum=len(files),value=0)
        for button in self.controls:
            button.configure(state='disabled')
        self.operations.configure(state='disabled')
        self.settings_button.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        self.status.set('Starting batch: '+operation)
        def work():
            try:
                if operation=='Subtitles':
                    self.app.engine.unload()
                result=run_batch(files,operation,settings,directory,interpreter,self.cancel,lambda index,state,value:self.events.put(('file',(index,state,value))),keep_going)
                self.events.put(('complete',(directory,result)))
            except Exception as exc:
                self.events.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='file':
                    index,state,detail=value
                    self.tree.item(str(index),values=(self.files[index].name,state,detail or ''))
                    self.status.set(f'{index+1}/{len(self.files)}: {self.files[index].name} - {state}')
                    self.progress.configure(value=index if state=='Running' else index+1)
                else:
                    self.app.batch_running=False
                    self.app.busy(False)
                    for button in self.controls:
                        button.configure(state='normal')
                    self.operations.configure(state='readonly')
                    self.settings_button.configure(state='normal')
                    self.cancel_button.configure(state='disabled')
                    if kind=='complete':
                        self.last_directory,report=value
                        completed=sum(row['status']=='Completed' for row in report['files'])
                        failed=sum(row['status']=='Failed' for row in report['files'])
                        self.status.set(f"Batch {report['status'].lower()}: {completed} completed, {failed} failed. Results and batch-report.json: {self.last_directory}")
                    else:
                        self.status.set('Batch failed: '+value)
                        messagebox.showerror('Batch processing',value)
        except queue.Empty:
            pass
        self.app.root.after(100,self.poll)

    def open_folder(self):
        if self.last_directory and self.last_directory.is_dir():
            os.startfile(self.last_directory)
        else:
            messagebox.showinfo('No completed run','Start a batch first to create its output folder.')
