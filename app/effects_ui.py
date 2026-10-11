"""Voice effects controls sharing the existing offline worker/export lifecycle."""
import tkinter as tk
import winsound
from pathlib import Path
from tkinter import messagebox,ttk

from .converter_ui import ConverterPanel
from .cleanup_ui import CleanupPanel
from .effects_presets import EffectsPresets


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
        self.formant=tk.BooleanVar(value=True)
        self.time_mode=tk.StringVar(value='Constant speed')
        self.target_duration=tk.StringVar(value='10')
        self.end_speed=tk.StringVar(value='1')
        self.timing_widgets=[]
        self.preset_dialog=None
        self.preset_error=None
        try:
            self.preset_store=EffectsPresets()
        except (ValueError,OSError) as exc:
            self.preset_store=None
            self.preset_error=str(exc)
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
        timing=ttk.Frame(settings)
        timing.pack(fill='x',pady=(0,8))
        ttk.Label(timing,text='Speed mode').grid(row=0,column=0,sticky='w',padx=(0,8))
        from .effect_timing import MODES
        self.mode_choice=ttk.Combobox(timing,textvariable=self.time_mode,values=MODES,state='readonly',width=18)
        self.mode_choice.grid(row=0,column=1,sticky='w')
        self.choices.append(self.mode_choice)
        self.target_entry=ttk.Entry(timing,textvariable=self.target_duration,width=10)
        self.end_speed_entry=ttk.Entry(timing,textvariable=self.end_speed,width=10)
        ttk.Label(timing,text='Final duration (seconds)').grid(row=0,column=2,padx=8)
        self.target_entry.grid(row=0,column=3)
        ttk.Label(timing,text='Ending speed (0.5–2x)').grid(row=1,column=0,columnspan=2,sticky='w',pady=5)
        self.end_speed_entry.grid(row=1,column=2,sticky='w')
        self.timing_widgets=[self.target_entry,self.end_speed_entry]
        self.controls.extend(self.timing_widgets)
        self.timing_help=tk.StringVar()
        ttk.Label(settings,textvariable=self.timing_help,wraplength=850).pack(anchor='w',pady=(0,8))
        self.time_mode.trace_add('write',lambda *_:self.update_timing())
        for title,variable,low,high in (('Speed',self.speed,.5,2),('Pitch',self.pitch,-12,12),('Reverb',self.reverb,0,1)):
            caption=tk.StringVar()
            def update(*_,title=title,variable=variable,caption=caption):
                value=variable.get()
                caption.set(f'{"Starting speed" if self.time_mode.get()=="Gradual speed" else "Speed"}: {value:.2f}x (1.00 = original)' if title=='Speed' else f'Pitch: {value:+.1f} semitones (0 = original)' if title=='Pitch' else f'Reverb: {value:.0%}')
            variable.trace_add('write',update)
            if title=='Speed':
                self.time_mode.trace_add('write',update)
            update()
            ttk.Label(settings,textvariable=caption).pack(anchor='w')
            slider=ttk.Scale(settings,variable=variable,from_=low,to=high)
            slider.pack(fill='x',pady=(2,8))
            self.controls.append(slider)
            if title=='Speed':
                self.speed_slider=slider
        check=ttk.Checkbutton(settings,text='Radio-style voice (narrow frequency range and mild saturation)',variable=self.radio)
        check.pack(anchor='w',pady=4)
        self.controls.append(check)
        check=ttk.Checkbutton(settings,text='Preserve vocal character when changing pitch (reduces the chipmunk effect)',variable=self.formant)
        check.pack(anchor='w',pady=4)
        self.controls.append(check)
        preset_row=ttk.Frame(settings)
        preset_row.pack(fill='x',pady=4)
        button=ttk.Button(preset_row,text='Reset effects',command=self.reset)
        button.pack(side='left')
        self.controls.append(button)
        self.presets_button=ttk.Button(preset_row,text='Effects presets...',command=self.open_presets)
        self.presets_button.pack(side='left',padx=8)
        self.controls.append(self.presets_button)
        ttk.Label(frame,text='Rubber Band R3 Finer processes speed and pitch together. Vocal character preservation affects pitch changes only.\nReverb adds a 0.6-second tail. Speed changes or reverb require new subtitle timings.\nUse clips up to ten minutes. Mono/stereo is retained; rates above 48 kHz become 48 kHz.',wraplength=820).pack(anchor='w',pady=8)
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
        self.update_timing()
        app.root.after(100,self.poll_timing)

    def update_timing(self):
        mode=self.time_mode.get()
        busy=self.app.editor_panel.occupied()
        self.mode_choice.configure(state='disabled' if busy else 'readonly')
        self.target_entry.configure(state='normal' if mode=='Fit duration' and not busy else 'disabled')
        self.end_speed_entry.configure(state='normal' if mode=='Gradual speed' and not busy else 'disabled')
        self.speed_slider.configure(state='disabled' if mode=='Fit duration' or busy else 'normal')
        self.timing_help.set({'Constant speed':'One speed for the whole clip; 1x is unchanged.',
                             'Fit duration':'Final WAV length includes any reverb tail. The speed slider is ignored.',
                             'Gradual speed':'The speed slider sets the starting speed. Transition smoothly to Ending speed across the whole clip.'}.get(mode,''))

    def poll_timing(self):
        self.update_timing()
        self.app.root.after(100,self.poll_timing)

    def update_options(self):
        pass

    def open_presets(self):
        if self.preset_dialog and self.preset_dialog.winfo_exists():
            self.preset_dialog.lift()
            return
        from .effects_presets_ui import PresetsDialog
        self.preset_dialog=PresetsDialog(self)

    def reset(self):
        self.speed.set(1)
        self.pitch.set(0)
        self.reverb.set(0)
        self.radio.set(False)
        self.formant.set(True)
        self.time_mode.set('Constant speed')
        self.target_duration.set('10')
        self.end_speed.set('1')

    def make_request(self,source,temporary,format_name):
        return {'source':str(source),'destination':str(temporary),'original':str(temporary.with_name(temporary.stem+'-original.wav')),
                'speed':self.speed.get(),'pitch':self.pitch.get(),'reverb':self.reverb.get(),'radio':self.radio.get(),'formant':self.formant.get(),
                'time_mode':self.time_mode.get(),'target_duration':float(self.target_duration.get()) if self.time_mode.get()=='Fit duration' else 10,
                'end_speed':float(self.end_speed.get()) if self.time_mode.get()=='Gradual speed' else 1}

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
