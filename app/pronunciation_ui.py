import tkinter as tk
from tkinter import ttk, messagebox
from . import pronunciation


class PronunciationDialog(tk.Toplevel):
    def __init__(self, app):
        value = pronunciation.load()
        super().__init__(app.root)
        self.app = app
        self.title('Pronunciation dictionary')
        self.transient(app.root)
        scale = max(1, self.winfo_fpixels('1i') / 96)
        self.geometry(f'{min(int(700*scale), self.winfo_screenwidth()-80)}x{min(int(600*scale), self.winfo_screenheight()-120)}')
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Write a word and a spelling that sounds right when read aloud, for example SQL → sequel.\nMatches ignore capitalization and use whole words or phrases. Original scripts and subtitles stay unchanged.', wraplength=620).pack(anchor='w')
        self.enabled = tk.BooleanVar(value=value['enabled'])
        ttk.Checkbutton(frame, text='Use dictionary for future speech generation', variable=self.enabled).pack(anchor='w', pady=8)
        self.rows = ttk.Treeview(frame, columns=('word', 'spoken'), show='headings', height=7)
        self.rows.heading('word', text='Written word or phrase')
        self.rows.heading('spoken', text='Read it as')
        self.rows.pack(fill='both', expand=True)
        for word, spoken in value['entries'].items():
            self.rows.insert('', 'end', values=(word, spoken))
        self.rows.bind('<<TreeviewSelect>>', self.select)
        self.word, self.spoken = tk.StringVar(), tk.StringVar()
        for label, variable in [('Written word / phrase', self.word), ('Pronunciation spelling', self.spoken)]:
            ttk.Label(frame, text=label).pack(anchor='w', pady=(5,0))
            ttk.Entry(frame, textvariable=variable).pack(fill='x')
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=8)
        ttk.Button(buttons, text='Add / update entry', command=self.add).pack(side='left')
        ttk.Button(buttons, text='Remove selected', command=self.remove).pack(side='left', padx=8)
        ttk.Button(buttons, text='Save dictionary', command=self.persist).pack(side='right')
        ttk.Button(frame, text='Preview pronunciation of current script', command=self.preview).pack(anchor='w')
        self.preview_text = tk.Text(frame, height=4, wrap='word', state='disabled')
        self.preview_text.pack(fill='x', pady=6)
        ttk.Label(frame, text='Save before generating. Preview shows these unsaved entries; listen to a short generation to check the result.', wraplength=620).pack(anchor='w')

    def value(self):
        return pronunciation.validate({'enabled': self.enabled.get(), 'entries': {self.rows.item(row, 'values')[0]: self.rows.item(row, 'values')[1] for row in self.rows.get_children()}})

    def select(self, _event=None):
        if self.rows.selection():
            word, spoken = self.rows.item(self.rows.selection()[0], 'values')
            self.word.set(word)
            self.spoken.set(spoken)

    def add(self):
        try:
            word, spoken = self.word.get().strip(), self.spoken.get().strip()
            pronunciation.validate({'enabled': True, 'entries': {word: spoken}})
            for row in self.rows.get_children():
                if self.rows.item(row, 'values')[0].casefold() == word.casefold():
                    self.rows.item(row, values=(word, spoken))
                    return
            if len(self.rows.get_children()) >= 500:
                raise ValueError('Use no more than 500 entries.')
            self.rows.insert('', 'end', values=(word, spoken))
        except ValueError as exc:
            messagebox.showerror('Cannot add pronunciation', str(exc), parent=self)

    def remove(self):
        for row in self.rows.selection():
            self.rows.delete(row)

    def persist(self):
        try:
            pronunciation.save(self.value())
            self.app.status.set('Pronunciation dictionary saved for future generations.')
            self.destroy()
        except (ValueError, OSError) as exc:
            messagebox.showerror('Cannot save dictionary', str(exc), parent=self)

    def preview(self):
        result = pronunciation.apply(self.app.text.get('1.0', 'end-1c'), self.value())
        self.preview_text.configure(state='normal')
        self.preview_text.delete('1.0', 'end')
        self.preview_text.insert('1.0', result)
        self.preview_text.configure(state='disabled')
