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
        self.icons = {}
        self.group_headers = []
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
            header = ttk.Label(self.sidebar, text=title, style='SidebarGroup.TLabel', takefocus=False)
            header.pack(fill='x', pady=(8,4))
            self.group_headers.append(header)
            for index, name in pages:
                button = ttk.Button(self.sidebar, text='  '+name, image=self.nav_icon(index), compound='left', style='Nav.TButton',
                                    command=lambda index=index: self.notebook.select(index))
                button.pack(fill='x', pady=2)
                self.buttons[index] = button
        self.audio_info_button = ttk.Button(self.sidebar, text='Audio file information...',
                                           style='Nav.TButton', command=self.app.open_audio_info)
        self.audio_info_button.pack(fill='x', pady=2)
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

    def nav_icon(self, index):
        """Small drawn line icons, retained for the lifetime of the sidebar."""
        from PIL import Image, ImageDraw, ImageTk
        size = round(20 * max(1,self.app.root.winfo_fpixels('1i')/96))
        image = Image.new('RGBA',(40,40))
        draw = ImageDraw.Draw(image)
        color = '#b4d9f5'
        if index in (0,4,6,8):
            heights = (10,22,32,18,26)
            for x,h in zip((6,13,20,27,34),heights):
                draw.line((x,20-h/2,x,20+h/2),fill=color,width=2)
        elif index==3:
            draw.rounded_rectangle((14,4,26,25),radius=6,outline=color,width=2)
            draw.arc((8,10,32,32),0,180,fill=color,width=2)
            draw.line((20,32,20,37),fill=color,width=2)
            draw.line((13,37,27,37),fill=color,width=2)
        elif index==2:
            draw.line((18,29,18,8,33,5,33,26),fill=color,width=2)
            draw.ellipse((7,26,18,35),outline=color,width=2)
            draw.ellipse((22,23,33,32),outline=color,width=2)
        else:
            draw.rounded_rectangle((9,5,31,35),radius=3,outline=color,width=2)
            for y in (13,20,27):
                draw.line((14,y,26,y),fill=color,width=2)
        self.icons[index] = ImageTk.PhotoImage(image.resize((size,size)),master=self.app.root)
        return self.icons[index]

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
