"""Voice effects controls sharing the existing offline worker/export lifecycle."""
import tkinter as tk
import winsound
from pathlib import Path
from tkinter import messagebox,ttk

from .converter_ui import ConverterPanel
from .cleanup_ui import CleanupPanel


class EffectsPanel(ConverterPanel):
    worker_module='app.effects_worker'
    output_directory='effects'
    task_label='Voice effects'
    open_folder=CleanupPanel.open_folder

    def __init__(self,app,parent):
        super().__init__(app,parent)
        for widget in parent.winfo_children():
            widget.destroy()
        self.format.set('WAV')
        self.speed=tk.DoubleVar(value=1)
        self.pitch=tk.DoubleVar(value=0)
        self.reverb=tk.DoubleVar(value=0)
        self.radio=tk.BooleanVar(value=False)
        self.controls=[]
        self.choices=[]
        frame=ttk.Frame(parent,padding=16)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Voice effects',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text='Change speaking speed or pitch, add room reverb, or create a radio-style voice. Save a separate WAV.',wraplength=820).pack(anchor='w',pady=(4,12))
        row=ttk.Frame(frame)
        row.pack(fill='x')
        for title,command in (('Open audio...',self.choose),('Use latest recording',lambda:self.use(app.recorder_panel.output)),('Use selected generated speech',lambda:self.use(app.selected_output()))):
            button=ttk.Button(row,text=title,command=command)
            button.pack(side='left',padx=(0,8))
            self.controls.append(button)
        button=ttk.Button(frame,text='Use last saved audio edit',command=lambda:self.use(app.editor_panel.output))
        button.pack(anchor='w',pady=8)
        self.controls.append(button)
        label=ttk.Label(frame,textvariable=self.filename,wraplength=820)
        label.pack(fill='x',pady=6)
        label.bind('<Configure>',lambda e:label.configure(wraplength=max(100,e.width)))
        settings=ttk.LabelFrame(frame,text='Effect settings',padding=12)
        settings.pack(fill='x',pady=8)
        for title,variable,low,high in (('Speed',self.speed,.5,2),('Pitch',self.pitch,-12,12),('Reverb',self.reverb,0,1)):
            caption=tk.StringVar()
            def update(*_,title=title,variable=variable,caption=caption):
                value=variable.get()
                caption.set(f'Speed: {value:.2f}x (1.00 = original)' if title=='Speed' else f'Pitch: {value:+.1f} semitones (0 = original)' if title=='Pitch' else f'Reverb: {value:.0%}')
            variable.trace_add('write',update)
            update()
            ttk.Label(settings,textvariable=caption).pack(anchor='w')
            slider=ttk.Scale(settings,variable=variable,from_=low,to=high)
            slider.pack(fill='x',pady=(2,8))
            self.controls.append(slider)
        check=ttk.Checkbutton(settings,text='Radio-style voice (narrow frequency range and mild saturation)',variable=self.radio)
        check.pack(anchor='w',pady=4)
        self.controls.append(check)
        button=ttk.Button(settings,text='Reset effects',command=self.reset)
        button.pack(anchor='w',pady=4)
        self.controls.append(button)
        ttk.Label(frame,text='Speed and pitch work independently. Reverb adds a 0.6-second tail.\nSpeed changes or reverb require new subtitle timings. Extreme settings may sound less natural.\nUse clips up to five minutes. Mono/stereo is retained; rates above 48 kHz are converted to 48 kHz.',wraplength=820).pack(anchor='w',pady=8)
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=8)
        self.convert_button=ttk.Button(row,text='Apply voice effects',style='Primary.TButton',command=self.start)
        self.convert_button.pack(side='left')
        self.controls.append(self.convert_button)
        self.cancel_button=ttk.Button(row,text='Cancel',command=self.cancel.set,state='disabled')
        self.cancel_button.pack(side='left',padx=8)
        self.export_button=ttk.Button(row,text='Export effects WAV...',command=self.export,state='disabled')
        self.export_button.pack(side='left')
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=8)
        for title,command in (('Play original',lambda:self.play(True)),('Play with effects',lambda:self.play(False)),('Stop playback',lambda:winsound.PlaySound(None,0))):
            button=ttk.Button(row,text=title,command=command)
            button.pack(side='left',padx=(0,8))
            self.controls.append(button)
        ttk.Label(frame,text='Playback/export use the last completed result. Apply effects again after changing settings.',wraplength=820).pack(anchor='w',pady=6)
        self.progress=ttk.Progressbar(frame,mode='indeterminate')
        self.progress.pack(fill='x',pady=8)
        label=ttk.Label(frame,textvariable=self.status,wraplength=820)
        label.pack(fill='x')
        label.bind('<Configure>',lambda e:label.configure(wraplength=max(100,e.width)))
        self.status.set('Choose audio, adjust effects, and click Apply voice effects.')

    def update_options(self):
        pass

    def reset(self):
        self.speed.set(1)
        self.pitch.set(0)
        self.reverb.set(0)
        self.radio.set(False)

    def make_request(self,source,temporary,format_name):
        return {'source':str(source),'destination':str(temporary),'original':str(temporary.with_name(temporary.stem+'-original.wav')),
                'speed':self.speed.get(),'pitch':self.pitch.get(),'reverb':self.reverb.get(),'radio':self.radio.get()}

    def completion_status(self,info):
        return f"Effects complete: {info['duration']:.2f}s | {info['rate']} Hz | {info['channels']} channel(s). Compare and export." + (' Peak protection reduced the level.' if info['peak_protection'] else '')

    def use(self,source):
        super().use(source)
        if source and Path(source).is_file():
            self.status.set('Ready to apply effects. Original files stay unchanged.')

    def play(self,original):
        if not self.output:
            messagebox.showinfo('Apply effects first','Complete processing to compare original and processed audio.')
            return
        path=self.result_info['original'] if original else self.output
        try:
            winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC)
        except RuntimeError as exc:
            messagebox.showerror('Playback failed',str(exc))
