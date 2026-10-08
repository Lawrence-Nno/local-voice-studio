"""Direct handoff of completed audio without rerunning a workflow."""
import tkinter as tk
import winsound
from pathlib import Path
from tkinter import messagebox,ttk


class AudioShortcuts:
    def __init__(self,app,panel,parent,label):
        self.app=app
        self.panel=panel
        self.button=ttk.Menubutton(parent,text=label,state='disabled')
        self.menu=tk.Menu(self.button,tearoff=False)
        for title,destination in (('Format converter','conversion'),('Audio to subtitles','subtitles'),('Voice effects','effects')):
            self.menu.add_command(label='Send to '+title,command=lambda destination=destination:self.send(destination))
        self.button.configure(menu=self.menu)
        self.button.pack(side='left',padx=8)
        self.app.root.after(100,self.poll)

    def refresh(self):
        self.button.configure(state='normal' if self.panel.output and not self.app.editor_panel.occupied() else 'disabled')

    def poll(self):
        self.refresh()
        self.app.root.after(100,self.poll)

    def send(self,destination):
        if self.app.editor_panel.occupied():
            messagebox.showinfo('Audio task running','Finish the active audio task before sending a result to another tab.')
            return
        source=self.panel.output
        if not source or not Path(source).is_file():
            messagebox.showinfo('Save a result first','Complete and save an edit or cleanup first. The shortcut uses that saved result.')
            return
        source=Path(source)
        try:
            if destination=='subtitles':
                target=self.app.subtitles
                target.select_audio(source)
            elif destination in ('conversion','effects'):
                target=self.app.converter_panel if destination=='conversion' else self.app.effects_panel
                target.use(source)
                action='Convert audio' if destination=='conversion' else 'Apply voice effects'
                target.status.set('Selected saved audio: '+source.name+'. Click '+action+' when ready.'+(' Export/playback still uses the previous completed result until processing succeeds.' if target.output else ''))
            else:
                raise ValueError('Unknown audio destination.')
            winsound.PlaySound(None,0)
            self.app.notebook.select(target.parent)
        except (ValueError,OSError) as exc:
            messagebox.showerror('Cannot send audio',str(exc))
