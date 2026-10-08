"""General audio cleanup with original/cleaned comparison."""
import tkinter as tk
import winsound
from pathlib import Path
from tkinter import messagebox,ttk

from .converter_ui import ConverterPanel
from .storage import DATA


class CleanupPanel(ConverterPanel):
    worker_module='app.cleanup_worker'
    output_directory='cleaned'
    task_label='Cleanup'

    def completion_status(self,info):
        text=f"Cleanup complete: {info['duration']:.2f}s | {info['rate']} Hz | {info['channels']} channel(s). Compare original and cleaned, then export."
        if info['peak_protection']:
            text+=' Peak protection limited volume to avoid clipping.'
        return text

    def use(self,source):
        super().use(source)
        if source and Path(source).is_file():
            self.status.set('Ready to clean. Playback and export use the last completed cleanup.')

    def __init__(self,app,parent):
        # Reuse the converter's isolated worker, cancellation and protected export.
        super().__init__(app,parent)
        for widget in parent.winfo_children():
            widget.destroy()
        self.format.set('WAV')
        self.strength=tk.DoubleVar(value=.35)
        self.volume=tk.DoubleVar(value=1)
        self.normalize=tk.BooleanVar(value=True)
        self.rumble=tk.BooleanVar(value=False)
        self.choices=[]
        self.controls=[]
        frame=ttk.Frame(parent,padding=20)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Audio cleanup',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text='Reduce steady background noise and adjust volume. Save a separate WAV and compare it with the original.',wraplength=820).pack(anchor='w',pady=(6,16))
        row=ttk.Frame(frame)
        row.pack(fill='x')
        for title,command in (('Open audio...',self.choose),('Use latest recording',lambda:self.use(app.recorder_panel.output)),('Use selected generated speech',lambda:self.use(app.selected_output()))):
            button=ttk.Button(row,text=title,command=command)
            button.pack(side='left',padx=(0,8))
            self.controls.append(button)
        label=ttk.Label(frame,textvariable=self.filename,wraplength=820)
        label.pack(fill='x',pady=12)
        label.bind('<Configure>',lambda e:label.configure(wraplength=max(100,e.width)))
        settings=ttk.LabelFrame(frame,text='Cleanup settings',padding=16)
        settings.pack(fill='x',pady=8)
        for title,variable,maximum in (('Noise reduction',self.strength,1),('Volume',self.volume,2)):
            caption=tk.StringVar()
            def update(*_,title=title,variable=variable,caption=caption):
                caption.set(f'{title}: {variable.get():.0%}')
            variable.trace_add('write',update)
            update()
            ttk.Label(settings,textvariable=caption).pack(anchor='w',pady=4)
            slider=ttk.Scale(settings,variable=variable,from_=0,to=maximum)
            slider.pack(fill='x',pady=(0,12))
            self.controls.append(slider)
        for title,variable in (('Automatically level volume (with peak protection)',self.normalize),('Reduce low-frequency rumble (70 Hz high-pass)',self.rumble)):
            button=ttk.Checkbutton(settings,text=title,variable=variable)
            button.pack(anchor='w',pady=4)
            self.controls.append(button)
        ttk.Label(frame,text='Start with mild noise reduction. Steady hiss or fan noise is easier to reduce than music or other voices.\nStronger settings can affect speech; compare both versions. Set noise reduction to 0% for volume-only adjustment.\nDuration, sample rate and mono/stereo channels stay unchanged. Output is PCM16 WAV.',wraplength=820).pack(anchor='w',pady=12)
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=10)
        self.convert_button=ttk.Button(row,text='Clean audio',style='Primary.TButton',command=self.start)
        self.convert_button.pack(side='left')
        self.controls.append(self.convert_button)
        self.cancel_button=ttk.Button(row,text='Cancel',command=self.cancel.set,state='disabled')
        self.cancel_button.pack(side='left',padx=8)
        self.export_button=ttk.Button(row,text='Export cleaned WAV...',command=self.export,state='disabled')
        self.export_button.pack(side='left')
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=8)
        for title,command in (('Play original',lambda:self.play(True)),('Play cleaned',lambda:self.play(False)),('Stop playback',lambda:winsound.PlaySound(None,0))):
            button=ttk.Button(row,text=title,command=command)
            button.pack(side='left',padx=(0,8))
            self.controls.append(button)
        from .audio_shortcuts import AudioShortcuts
        self.shortcuts=AudioShortcuts(app,self,row,'Send cleaned audio to...')
        ttk.Label(frame,text='Playback compares the last completed cleanup. Click Clean audio again after changing settings.',wraplength=820).pack(anchor='w',pady=8)
        ttk.Button(frame,text='Open cleaned files folder',command=self.open_folder).pack(anchor='w',pady=8)
        self.progress=ttk.Progressbar(frame,mode='indeterminate')
        self.progress.pack(fill='x',pady=8)
        label=ttk.Label(frame,textvariable=self.status,wraplength=820)
        label.pack(fill='x')
        label.bind('<Configure>',lambda e:label.configure(wraplength=max(100,e.width)))
        self.status.set('Choose audio or a saved recording, adjust cleanup settings, then click Clean audio.')

    def update_options(self):
        pass

    def make_request(self,source,temporary,format_name):
        return {'source':str(source),'destination':str(temporary),'original':str(temporary.with_name(temporary.stem+'-original.wav')),
                'strength':self.strength.get(),'volume':self.volume.get(),'normalize':self.normalize.get(),'rumble':self.rumble.get()}

    def play(self,original):
        if not self.output:
            messagebox.showinfo('Clean audio first','Complete a cleanup to compare its original and cleaned audio.')
            return
        path=Path(self.result_info['original']) if original else self.output
        try:
            winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC)
        except RuntimeError as exc:
            messagebox.showerror('Playback failed',str(exc))

    def open_folder(self):
        import os
        directory=DATA/self.output_directory
        directory.mkdir(parents=True,exist_ok=True)
        os.startfile(directory)
