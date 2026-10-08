"""All-page sidebar, dark theme, scrolling and native dialog checks."""
import time
import tkinter as tk
from app.storage import DATA, configure_runtime


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from app.studio_theme import FIELD
    from PIL import ImageGrab
    configure_dpi()
    root=tk.Tk()
    callback_errors=[]
    root.report_callback_exception=lambda *args: callback_errors.append(args)
    app=VoiceApp(root)
    folder=DATA/'verification/studio-ui'
    folder.mkdir(parents=True,exist_ok=True)
    def pump(seconds=.15):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            root.update()
            time.sleep(.01)
    try:
        root.attributes('-topmost',True)
        for index,button in app.shell.buttons.items():
            button.invoke()
            pump()
            assert app.notebook.index('current')==index
            assert button['style']=='Selected.Nav.TButton'
            canvas=app.shell.scroll_pages[app.notebook.select()]
            assert canvas.winfo_ismapped()
            body=root.nametowidget(app.notebook.select()).winfo_children()[0]
            assert body.winfo_ismapped()
            assert canvas.yview()[0]==0
            assert button.winfo_rooty()+button.winfo_height() <= root.winfo_rooty()+root.winfo_height()
            ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(folder/f'page-{index}.png')
        assert app.text['background']==FIELD
        app.notebook.select(app.subtitles.parent)
        pump()
        assert app.shell.buttons[1]['style']=='Selected.Nav.TButton'
        app.open_pronunciation()
        pump()
        assert app.pronunciation_dialog.preview_text['background']==FIELD
        app.pronunciation_dialog.destroy()
        scale=max(1,root.winfo_fpixels('1i')/96)
        root.geometry(f'{round(1050*scale)}x{round(650*scale)}')
        app.notebook.select(0)
        pump()
        canvas=app.shell.scroll_pages[app.notebook.select()]
        canvas.yview_moveto(1)
        pump()
        assert canvas.yview()[1]>.99, (canvas.yview(),canvas['scrollregion'],canvas.winfo_height())
        assert app.export_button.winfo_rooty()+app.export_button.winfo_height() <= canvas.winfo_rooty()+canvas.winfo_height()
        assert not callback_errors, callback_errors
        print('Nine-page sidebar, active navigation, dark text/dialogs, programmatic handoff and small-window scrolling passed.')
    finally:
        app.editor_panel.stop_playback()
        root.destroy()


if __name__=='__main__': main()
