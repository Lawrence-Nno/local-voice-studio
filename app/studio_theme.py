"""Shared studio palette for ttk controls and classic Tk widgets."""
import tkinter as tk
from tkinter import ttk

BG = '#071b2e'
PANEL = '#102b43'
FIELD = '#061727'
INK = '#e6edf5'
MUTED = '#9caec2'
ACCENT = '#0785ff'
BORDER = '#244b68'


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
    # Use explicit images: clam's filled square was ambiguous on the dark palette.
    from PIL import Image, ImageDraw, ImageTk
    # Nine-slice image borders give ttk real rounded surfaces without changing
    # button commands, keyboard focus, or accessibility semantics.
    button_images = []
    for name, colors in (
        ('Studio.Button', ('#16334c', '#204762', '#102b43', '#0d2438')),
        ('Studio.Primary', (ACCENT, '#2698ff', '#006bd1', '#183752')),
    ):
        variants = []
        for color in colors:
            surface = Image.new('RGBA', (32,32), (0,0,0,0))
            ImageDraw.Draw(surface).rounded_rectangle((1,1,30,30), radius=7,
                                                      fill=color, outline=BORDER)
            variants.append(ImageTk.PhotoImage(surface, master=root))
        button_images.extend(variants)
        normal, hover, pressed, disabled = variants
        style.element_create(name, 'image', normal, ('disabled',disabled),
                             ('pressed',pressed), ('active',hover), border=9, sticky='nswe')
        target = 'TButton' if name=='Studio.Button' else 'Primary.TButton'
        style.layout(target, [(name, {'sticky':'nswe','children':[
            ('Button.padding', {'sticky':'nswe','children':[
                ('Button.focus', {'sticky':'nswe','children':[
                    ('Button.label', {'sticky':'nswe'})]})]})]})])
    root.studio_button_images = button_images
    size = round(18 * max(1,root.winfo_fpixels('1i')/96))
    images = []
    for checked, disabled in ((False,False),(True,False),(False,True),(True,True)):
        image = Image.new('RGBA',(size,size),(0,0,0,0))
        draw = ImageDraw.Draw(image)
        green = '#2b8d62' if disabled else '#35cf89'
        draw.rounded_rectangle((1,1,size-2,size-2),radius=max(2,size//6),
                               fill=green if checked else FIELD,
                               outline=green if checked else '#73869c',width=max(1,size//12))
        if checked:
            draw.line([(size*.23,size*.50),(size*.43,size*.70),(size*.77,size*.30)],
                      fill='#062c1c',width=max(2,size//8))
        images.append(ImageTk.PhotoImage(image,master=root))
    root.studio_checkbox_images = images
    off,on,disabled_off,disabled_on = images
    style.element_create('Studio.Check.indicator','image',off,
                         ('disabled','selected',disabled_on),('disabled',disabled_off),
                         ('selected',on),('alternate',off),width=size+8,sticky='w')
    style.layout('TCheckbutton', [('Checkbutton.padding', {'sticky':'nswe','children':[
        ('Studio.Check.indicator', {'side':'left','sticky':''}),
        ('Checkbutton.focus', {'side':'left','sticky':'w','children':[
            ('Checkbutton.label', {'sticky':'nswe'})]})]})])
    style.configure('TCheckbutton', padding=(3,5), indicatormargin=(0,0,8,0))
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
    style.configure('Sidebar.TFrame', background='#061727')
    style.configure('Sidebar.TLabel', background='#061727', foreground=MUTED, font=('Segoe UI',9))
    style.configure('SidebarGroup.TLabel', background='#102b43', foreground='#8dccf5',
                    font=('Segoe UI',8,'bold'), padding=(10,5))
    style.configure('Brand.TLabel', background='#061727', foreground=INK, font=('Segoe UI',13,'bold'))
    style.configure('Nav.TButton', background='#061727', foreground=MUTED, anchor='w', padding=(10,6))
    style.layout('Nav.TButton', [('Button.border', {'sticky':'nswe','border':'1','children':[
        ('Button.padding', {'sticky':'nswe','children':[
            ('Button.label', {'sticky':'nswe'})]})]})])
    style.map('Nav.TButton', background=[('active','#1b2c40')], foreground=[('active',INK)])
    style.configure('Selected.Nav.TButton', background='#0c4972', foreground='#ffffff')
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
