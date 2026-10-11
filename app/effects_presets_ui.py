"""Named voice-effect presets without changing the last processed result."""
import tkinter as tk
from tkinter import messagebox,simpledialog,ttk
from .effects_presets import BUILTINS


class PresetsDialog(tk.Toplevel):
    def __init__(self,panel):
        super().__init__(panel.app.root)
        self.transient(panel.app.root)
        self.panel=panel
        self.title('Voice effects presets')
        scale=max(1,self.winfo_fpixels('1i')/96)
        width=min(round(720*scale),self.winfo_screenwidth()-80)
        height=min(round(480*scale),self.winfo_screenheight()-120)
        self.geometry(f'{width}x{height}')
        self.minsize(width,height)
        frame=ttk.Frame(self,padding=16)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Voice effects presets',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text='Load a starter or saved preset, or save the current Voice effects controls under your own name.',wraplength=700).pack(anchor='w',pady=8)
        self.list=tk.Listbox(frame,exportselection=False,font=('Segoe UI',11),height=6)
        self.list.pack(fill='both',expand=True,pady=8)
        self.list.bind('<<ListboxSelect>>',lambda _:self.update_controls())
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=8)
        self.buttons=[]
        for title,command in (('Load selected',self.load),('Save current as...',self.save),('Update selected',self.update),('Delete selected',self.delete)):
            button=ttk.Button(row,text=title,command=command)
            button.pack(side='left',padx=(0,8))
            self.buttons.append(button)
        self.status=tk.StringVar(value='Starter presets are read-only. Your presets stay in this copy of the app.')
        label=ttk.Label(frame,textvariable=self.status,wraplength=700)
        label.pack(fill='x',pady=8)
        label.bind('<Configure>',lambda e:label.configure(wraplength=max(100,e.width)))
        ttk.Label(frame,text='Loading changes speed, pitch, vocal character preservation, reverb and radio controls. Click Apply voice effects afterward.\nUpdate selected replaces that saved preset with your current controls; Delete selected removes it.',wraplength=700).pack(anchor='w',pady=8)
        self.refresh()
        if panel.preset_error:
            self.status.set('Saved presets could not be loaded: '+panel.preset_error+' Starter presets are available; restore the saved file before saving.')
        self.after(100,self.poll)

    def selected(self):
        selected=self.list.curselection()
        return self.names[selected[0]] if selected else None

    def refresh(self,selected=None):
        store=self.panel.preset_store
        self.presets=store.all() if store else {name:dict(settings) for name,settings in BUILTINS.items()}
        self.names=list(self.presets)
        self.list.delete(0,'end')
        for name in self.names:
            self.list.insert('end',name+(' [starter]' if name in BUILTINS else ' [saved]'))
        if selected in self.names:
            self.list.selection_set(self.names.index(selected))
        self.update_controls()

    def update_controls(self):
        active=self.panel.app.editor_panel.occupied()
        selected=self.selected()
        custom=self.panel.preset_store and selected in self.panel.preset_store.custom
        self.buttons[0].configure(state='normal' if selected and not active else 'disabled')
        self.buttons[1].configure(state='normal' if self.panel.preset_store and not active else 'disabled')
        for button in self.buttons[2:]:
            button.configure(state='normal' if custom and not active else 'disabled')

    def current_settings(self):
        panel=self.panel
        return dict(speed=panel.speed.get(),pitch=panel.pitch.get(),reverb=panel.reverb.get(),radio=panel.radio.get(),formant=panel.formant.get())

    def load(self):
        name=self.selected()
        if name and not self.panel.app.editor_panel.occupied():
            settings=self.presets[name]
            self.panel.formant.set(settings.get('formant',True))
            for key,value in settings.items():
                getattr(self.panel,key).set(value)
            self.status.set('Loaded '+name+'. Click Apply voice effects to process audio.')
            self.panel.status.set('Loaded preset: '+name+'. Apply voice effects to create a new result.')

    def save(self):
        name=simpledialog.askstring('Save effects preset','Name the current effect settings:',parent=self)
        if name is not None:
            try:
                name=self.panel.preset_store.save(name,self.current_settings())
                self.refresh(name)
                self.status.set('Saved preset: '+name)
            except (ValueError,OSError) as exc:
                messagebox.showerror('Cannot save preset',str(exc),parent=self)

    def update(self):
        name=self.selected()
        if name:
            try:
                self.panel.preset_store.save(name,self.current_settings(),replace=True)
                self.refresh(name)
                self.status.set('Updated preset: '+name)
            except (ValueError,OSError) as exc:
                messagebox.showerror('Cannot update preset',str(exc),parent=self)

    def delete(self):
        name=self.selected()
        if name:
            try:
                self.panel.preset_store.delete(name)
                self.refresh()
                self.status.set('Deleted preset: '+name+'. Current effect controls are unchanged.')
            except (ValueError,OSError) as exc:
                messagebox.showerror('Cannot delete preset',str(exc),parent=self)

    def poll(self):
        self.update_controls()
        self.after(100,self.poll)
