"""Ordered clip list for the audio editor."""
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog,messagebox,ttk

import soundfile as sf


class JoinDialog(tk.Toplevel):
    def __init__(self,editor):
        super().__init__(editor.app.root)
        self.editor=editor
        self.clips=[]
        self.title('Join audio clips')
        scale=max(1,self.winfo_fpixels('1i')/96)
        width=min(round(780*scale),self.winfo_screenwidth()-80)
        height=min(round(620*scale),self.winfo_screenheight()-120)
        self.geometry(f'{width}x{height}')
        self.minsize(width,height)
        self.rate=tk.StringVar(value='44100')
        self.channels=tk.StringVar(value='Stereo')
        self.gap=tk.StringVar(value='0')
        frame=ttk.Frame(self,padding=16)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Join clips in order',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text='Add files or the current waveform selection. Move clips into playback order, then preview or save.',wraplength=710).pack(anchor='w',pady=8)
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=8)
        self.buttons=[]
        for title,command in (('Add audio files...',self.add_files),('Add current edited selection',self.add_selection)):
            button=ttk.Button(row,text=title,command=command)
            button.pack(side='left',padx=(0,8))
            self.buttons.append(button)
        self.list=tk.Listbox(frame,height=6,exportselection=False,font=('Segoe UI',10))
        self.list.pack(fill='both',expand=True,pady=6)
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=6)
        for title,command in (('Move up',lambda:self.move(-1)),('Move down',lambda:self.move(1)),('Remove selected',self.remove),('Clear list',self.clear)):
            button=ttk.Button(row,text=title,command=command)
            button.pack(side='left',padx=(0,8))
            self.buttons.append(button)
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=10)
        self.options=[]
        for title,variable,values in (('Output Hz',self.rate,('24000','44100','48000')),('Channels',self.channels,('Mono','Stereo'))):
            ttk.Label(row,text=title).pack(side='left',padx=(0,6))
            combo=ttk.Combobox(row,textvariable=variable,values=values,state='readonly',width=9)
            combo.pack(side='left',padx=(0,12))
            self.options.append(combo)
        ttk.Label(row,text='Gap (seconds)').pack(side='left',padx=(0,6))
        self.gap_entry=ttk.Entry(row,textvariable=self.gap,width=7)
        self.gap_entry.pack(side='left')
        row=ttk.Frame(frame)
        row.pack(fill='x',pady=8)
        for title,command in (('Preview joined clips',lambda:self.join(True)),('Save joined WAV',lambda:self.join(False))):
            button=ttk.Button(row,text=title,command=command)
            button.pack(side='left',padx=(0,8))
            self.buttons.append(button)
        ttk.Label(frame,text='Selection clips capture current volume/fades when added. File clips use the full audio.\nOutput is a new PCM16 WAV. Export the saved join from the Audio editor. Joining changes subtitle timings.',wraplength=710).pack(anchor='w',pady=8)
        self.status=ttk.Label(frame,text='Add at least two clips. The list plays from top to bottom.')
        self.status.pack(anchor='w')
        self.after(100,self.poll)
        self.protocol('WM_DELETE_WINDOW',self.close)

    def refresh(self,index=None):
        self.list.delete(0,'end')
        for number,clip in enumerate(self.clips,1):
            self.list.insert('end',f"{number}. {Path(clip['source']).name} | {clip['start']:.2f}s to {clip['end']:.2f}s | volume {clip['gain']:.0%}")
        if index is not None and self.clips:
            self.list.selection_set(min(index,len(self.clips)-1))

    def add_files(self):
        paths=filedialog.askopenfilenames(parent=self,title='Add audio clips',filetypes=[('Audio','*.wav *.flac *.ogg *.mp3'),('All files','*.*')])
        try:
            added=[]
            for path in paths:
                info=sf.info(path)
                if not 0<info.duration<=3600 or info.channels not in (1,2):
                    raise ValueError('Use non-empty mono/stereo files up to one hour long.')
                added.append({'source':path,'start':0,'end':info.duration,'gain':1,'fade_in':0,'fade_out':0})
            if len(self.clips)+len(added)>50:
                raise ValueError('The list supports up to 50 clips.')
            self.clips.extend(added)
            self.refresh(len(self.clips)-1)
        except Exception as exc:
            messagebox.showerror('Cannot add clips',str(exc),parent=self)

    def add_selection(self):
        editor=self.editor
        try:
            if not editor.source or not editor.info:
                raise ValueError('Open audio and select a section in the Audio editor first.')
            start,end,gain,fade_in,fade_out=[float(v.get()) for v in (editor.start_time,editor.end_time,editor.gain,editor.fade_in,editor.fade_out)]
            if not all(math.isfinite(v) for v in (start,end,gain,fade_in,fade_out)) or not 0<=start<end<=editor.info['duration']+.000001 or min(fade_in,fade_out)<0 or max(fade_in,fade_out)>end-start:
                raise ValueError('Choose valid selection times and fades first.')
            if len(self.clips)>=50:
                raise ValueError('The list supports up to 50 clips.')
            self.clips.append({'source':str(editor.source),'start':start,'end':end,'gain':gain,'fade_in':fade_in,'fade_out':fade_out})
            self.refresh(len(self.clips)-1)
        except (ValueError,tk.TclError) as exc:
            messagebox.showerror('Cannot add selection',str(exc),parent=self)

    def move(self,direction):
        selected=self.list.curselection()
        if selected:
            index=selected[0]
            target=index+direction
            if 0<=target<len(self.clips):
                self.clips[index],self.clips[target]=self.clips[target],self.clips[index]
                self.refresh(target)

    def remove(self):
        selected=self.list.curselection()
        if selected:
            index=selected[0]
            self.clips.pop(index)
            self.refresh(index)

    def clear(self):
        self.clips.clear()
        self.refresh()

    def join(self,preview):
        try:
            if len(self.clips)<2:
                raise ValueError('Add at least two clips to join.')
            gap=float(self.gap.get())
            if not math.isfinite(gap) or not 0<=gap<=10:
                raise ValueError('Choose a gap from 0 to 10 seconds.')
            self.editor.join_clips([dict(clip) for clip in self.clips],int(self.rate.get()),self.channels.get(),gap,preview)
        except ValueError as exc:
            messagebox.showerror('Cannot join clips',str(exc),parent=self)

    def poll(self):
        active=self.editor.occupied()
        for button in self.buttons:
            button.configure(state='disabled' if active else 'normal')
        for option in self.options:
            option.configure(state='disabled' if active else 'readonly')
        self.gap_entry.configure(state='disabled' if active else 'normal')
        self.status.configure(text='Processing audio; completion appears in the Audio editor.' if active else f'{len(self.clips)} clips. Preview or save, then export from the Audio editor.')
        self.after(100,self.poll)

    def close(self):
        if self.editor.app.editor_running:
            messagebox.showinfo('Audio task running','Wait for processing to finish before closing this window.',parent=self)
        else:
            self.destroy()
