"""Sidebar navigation around the existing notebook pages and callbacks."""
import tkinter as tk
from tkinter import ttk
from .studio_theme import BG, MUTED, finish_theme


class StudioShell:
    def __init__(self, app):
        self.app = app
        self.frame = ttk.Frame(app.root)
        self.frame.pack(fill='both', expand=True)
        self.sidebar = ttk.Frame(self.frame, style='Sidebar.TFrame', padding=(12,20))
        self.sidebar.pack(side='left', fill='y')
        ttk.Label(self.sidebar, text='LOCAL VOICE\nSTUDIO', style='Brand.TLabel').pack(anchor='w', padx=10)
        ttk.Label(self.sidebar, text='Your private audio workspace', style='Sidebar.TLabel').pack(anchor='w', padx=10, pady=(8,20))
        self.notebook = ttk.Notebook(self.frame, style='Studio.TNotebook', takefocus=False)
        self.notebook.pack(side='left', fill='both', expand=True)
        self.buttons = {}
        self.scroll_pages = {}
        self.notebook.bind('<<NotebookTabChanged>>', self.changed, add='+')
        app.root.bind('<MouseWheel>', self.wheel, add='+')
        app.root.bind('<Map>', self.mapped, add='+')

    def mapped(self, event):
        if event.widget == self.app.root or isinstance(event.widget, tk.Toplevel):
            widget = event.widget
            self.app.root.after_idle(lambda: finish_theme(widget) if widget.winfo_exists() else None)

    def finish(self):
        for title, pages in (('CREATE', ((0,'Text to speech'),(3,'Voice recorder'),(1,'Audio to subtitles'))),
                             ('EDIT & ENHANCE', ((4,'Audio editor'),(6,'Audio cleanup'),(8,'Voice effects'),(2,'Background music'))),
                             ('EXPORT & AUTOMATE', ((5,'Format converter'),(7,'Batch processing')))):
            ttk.Label(self.sidebar, text=title, style='Sidebar.TLabel').pack(anchor='w', padx=10, pady=(14,6))
            for index, name in pages:
                button = ttk.Button(self.sidebar, text=name, style='Nav.TButton',
                                    command=lambda index=index: self.notebook.select(index))
                button.pack(fill='x', pady=2)
                self.buttons[index] = button
        ttk.Label(self.sidebar, text='LOCAL PROCESSING\nAudio stays on this computer.', style='Sidebar.TLabel').pack(side='bottom', anchor='w', padx=10, pady=(18,0))
        for page_id in self.notebook.tabs():
            page = self.app.root.nametowidget(page_id)
            children = page.winfo_children()
            if len(children) != 1:
                continue
            body = children[0]
            body.pack_forget()
            canvas = tk.Canvas(page, background=BG, highlightthickness=0, borderwidth=0)
            scroll = ttk.Scrollbar(page, command=canvas.yview)
            canvas.configure(yscrollcommand=scroll.set)
            scroll.pack(side='right', fill='y')
            canvas.pack(side='left', fill='both', expand=True)
            window = canvas.create_window((0,0), window=body, anchor='nw')
            body.lift(canvas)
            def resize(_event=None, canvas=canvas, body=body, window=window):
                at_bottom = canvas.yview()[0] > 0 and canvas.yview()[1] >= .999
                canvas.itemconfigure(window, width=max(1,canvas.winfo_width()),
                                     height=max(canvas.winfo_height(),body.winfo_reqheight()))
                canvas.configure(scrollregion=canvas.bbox('all'))
                if at_bottom:
                    canvas.yview_moveto(1)
            canvas.bind('<Configure>', resize)
            body.bind('<Configure>', resize, add='+')
            self.scroll_pages[page_id] = canvas
        self.changed()

    def changed(self, _event=None):
        if not self.notebook.tabs():
            return
        current = self.notebook.index('current')
        for index, button in self.buttons.items():
            button.configure(style='Selected.Nav.TButton' if index==current else 'Nav.TButton')

    def wheel(self, event):
        # Text editors and list controls keep their own wheel behavior.
        if event.widget.winfo_class() in ('Text','Treeview','Listbox','TCombobox','TScale'):
            return
        page = self.notebook.select()
        widget = event.widget
        while widget is not None:
            if str(widget) == page:
                canvas = self.scroll_pages.get(page)
                if canvas:
                    canvas.yview_scroll(-int(event.delta/120), 'units')
                    return 'break'
                return
            widget = getattr(widget, 'master', None)
