"""Shared studio palette for ttk controls and classic Tk widgets."""
import tkinter as tk
from tkinter import ttk

BG = '#111820'
PANEL = '#1b2531'
FIELD = '#0e151e'
INK = '#e6edf5'
MUTED = '#9caec2'
ACCENT = '#448cff'
BORDER = '#314154'


def configure_theme(root):
    root.configure(background=BG)
    for widget in ('Text','Listbox','Menu'):
        root.option_add('*' + widget + '.font', ('Segoe UI', 10))
    for key, value in {'*Text.background':FIELD, '*Text.foreground':INK,
                       '*Text.insertBackground':INK, '*Text.selectBackground':'#285787',
                       '*Text.selectForeground':INK, '*Text.highlightBackground':BORDER,
                       '*Text.highlightColor':ACCENT, '*Text.relief':'flat',
                       '*Listbox.background':FIELD, '*Listbox.foreground':INK,
                       '*Listbox.selectBackground':'#285787', '*Listbox.selectForeground':INK,
                       '*Menu.background':PANEL, '*Menu.foreground':INK,
                       '*Menu.activeBackground':'#285787', '*Menu.activeForeground':INK,
                       '*Menu.disabledForeground':'#718095', '*TCombobox*Listbox.background':FIELD,
                       '*TCombobox*Listbox.foreground':INK,
                       '*TCombobox*Listbox.selectBackground':'#285787'}.items():
        root.option_add(key, value)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=BG, foreground=INK, font=('Segoe UI',10), bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER, focuscolor=ACCENT)
    style.configure('TFrame', background=BG)
    style.configure('TLabel', background=BG, foreground=INK)
    style.configure('Title.TLabel', font=('Segoe UI',20,'bold'))
    style.configure('Card.TFrame', background=PANEL)
    style.configure('Card.TLabel', background=PANEL)
    style.configure('Help.TLabel', background=PANEL, foreground=MUTED, font=('Segoe UI',9))
    style.configure('Heading.TLabel', background=PANEL, font=('Segoe UI',11,'bold'))
    style.configure('TButton', background='#263548', foreground=INK, padding=(10,7), borderwidth=0,
                    focusthickness=1, focuscolor=ACCENT)
    style.map('TButton', background=[('disabled','#1d2936'),('pressed','#354d68'),('active','#32475f')],
              foreground=[('disabled','#748498')])
    style.configure('TMenubutton', background='#263548', foreground=INK, padding=(10,7), borderwidth=0, arrowcolor=MUTED)
    style.map('TMenubutton', background=[('disabled','#1d2936'),('active','#32475f')],
              foreground=[('disabled','#748498')])
    style.configure('Primary.TButton', background=ACCENT, foreground='#ffffff')
    style.map('Primary.TButton', background=[('disabled','#243c5b'),('pressed','#2563cf'),('active','#5b9bff')],
              foreground=[('disabled','#8199b9')])
    for name in ('TEntry','TCombobox','TSpinbox'):
        style.configure(name, fieldbackground=FIELD, background=PANEL, foreground=INK,
                        insertcolor=INK, padding=5, arrowcolor=MUTED, bordercolor=BORDER)
        style.map(name, fieldbackground=[('disabled','#1b2531'),('readonly',FIELD)],
                  foreground=[('disabled','#748498'),('readonly',INK)],
                  selectbackground=[('!disabled','#285787')], selectforeground=[('!disabled',INK)])
    for name in ('TCheckbutton','TRadiobutton'):
        style.configure(name, background=BG, foreground=INK, indicatorbackground=FIELD,
                        indicatorforeground=ACCENT, padding=3)
        style.map(name, background=[('active',BG)], foreground=[('disabled','#748498')],
                  indicatorbackground=[('selected',ACCENT),('active','#32475f')])
    style.configure('TLabelframe', background=BG, bordercolor=BORDER, relief='solid')
    style.configure('TLabelframe.Label', background=BG, foreground=MUTED, font=('Segoe UI',9,'bold'))
    style.configure('Horizontal.TScale', background=BG, troughcolor=FIELD, bordercolor=BORDER)
    style.configure('Horizontal.TProgressbar', background=ACCENT, troughcolor=FIELD, borderwidth=0)
    style.configure('Vertical.TScrollbar', background='#34465c', troughcolor=BG, arrowcolor=MUTED, borderwidth=0)
    style.configure('Horizontal.TScrollbar', background='#34465c', troughcolor=BG, arrowcolor=MUTED, borderwidth=0)
    style.configure('Treeview', background=FIELD, fieldbackground=FIELD, foreground=INK,
                    rowheight=round(28*max(1,root.winfo_fpixels('1i')/96)), borderwidth=0)
    style.map('Treeview', background=[('selected','#285787')], foreground=[('selected',INK)])
    style.configure('Treeview.Heading', background=PANEL, foreground=MUTED, padding=8, relief='flat')
    style.map('Treeview.Heading', background=[('active','#263548')])
    style.configure('Studio.TNotebook', background=BG, borderwidth=0, tabmargins=0)
    style.layout('Studio.TNotebook.Tab', [])
    style.configure('Sidebar.TFrame', background='#0b1119')
    style.configure('Sidebar.TLabel', background='#0b1119', foreground=MUTED, font=('Segoe UI',9))
    style.configure('Brand.TLabel', background='#0b1119', foreground=INK, font=('Segoe UI',13,'bold'))
    style.configure('Nav.TButton', background='#0b1119', foreground=MUTED, anchor='w', padding=(12,10))
    style.map('Nav.TButton', background=[('active','#1b2c40')], foreground=[('active',INK)])
    style.configure('Selected.Nav.TButton', background='#183454', foreground='#dcebff')
    style.map('Selected.Nav.TButton', background=[('active','#21446b')], foreground=[('active','#ffffff')])


def finish_theme(root):
    """Style classic entries/labels in dialogs created by Tk itself."""
    def visit(widget):
        if isinstance(widget, ttk.Widget):
            pass
        elif isinstance(widget, tk.Toplevel):
            widget.configure(background=BG)
        elif isinstance(widget, (tk.Frame, tk.LabelFrame)):
            widget.configure(background=BG)
        elif isinstance(widget, tk.Label):
            widget.configure(background=BG, foreground=INK)
        elif isinstance(widget, tk.Entry):
            widget.configure(background=FIELD, foreground=INK, insertbackground=INK,
                             selectbackground='#285787', relief='flat')
        elif isinstance(widget, tk.Button):
            widget.configure(background=PANEL, foreground=INK, activebackground='#32475f',
                             activeforeground=INK, relief='flat')
        for child in widget.winfo_children():
            visit(child)
    visit(root)
