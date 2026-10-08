"""Verify both saved-result shortcut menus and all destinations."""
import tkinter as tk
from unittest.mock import patch

import numpy as np
import soundfile as sf

from app.storage import DATA,configure_runtime


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    configure_dpi()
    directory=DATA/'verification/shortcuts'
    directory.mkdir(parents=True,exist_ok=True)
    source=directory/'input.wav'
    edit=directory/'saved-edit.wav'
    cleaned=directory/'cleaned.wav'
    for path in (source,edit,cleaned):
        sf.write(path,np.zeros(8000),8000)
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    reviewed='1\n00:00:00,000 --> 00:00:01,000\nReviewed text\n'
    app.subtitles.text.insert('1.0',reviewed)
    app.subtitles.result_source=str(source)
    for index,panel,output in ((4,app.editor_panel,edit),(6,app.cleanup_panel,cleaned)):
        shortcuts=panel.shortcuts
        shortcuts.refresh()
        assert str(shortcuts.button['state'])=='disabled'
        panel.source=source
        panel.output=output
        shortcuts.refresh()
        assert str(shortcuts.button['state'])=='normal'
        for destination,target in (('conversion',app.converter_panel),('effects',app.effects_panel),('subtitles',app.subtitles)):
            previous=getattr(target,'output',None)
            shortcuts.send(destination)
            assert app.notebook.select()==str(target.parent)
            if destination=='subtitles':
                assert target.source=={'mode':'transcribe','audio':str(output)}
                assert target.text.get('1.0','end').strip()==reviewed.strip()
                assert 'input.wav' in target.filename.get()
            else:
                assert target.source==output and target.output==previous
        # Changed unsaved trim settings must not redirect to the original.
        app.editor_panel.start_time.set('.5')
        shortcuts.send('conversion')
        assert app.converter_panel.source==output
        app.batch_running=True
        shortcuts.refresh()
        assert str(shortcuts.button['state'])=='disabled'
        with patch('app.audio_shortcuts.messagebox.showinfo') as notice:
            shortcuts.send('effects')
            assert notice.called
        app.batch_running=False
        panel.output=directory/'missing-result.wav'
        previous=app.effects_panel.source
        with patch('app.audio_shortcuts.messagebox.showinfo') as notice:
            shortcuts.send('effects')
            assert notice.called
        assert app.effects_panel.source==previous
        panel.output=output
        app.notebook.select(index)
        root.update()
        shortcuts.refresh()
        assert shortcuts.button.winfo_ismapped()
        assert shortcuts.button.winfo_rootx()+shortcuts.button.winfo_width()<=root.winfo_rootx()+root.winfo_width()
        assert shortcuts.button.winfo_rooty()+shortcuts.button.winfo_height()<=root.winfo_rooty()+root.winfo_height()
    app.close()
    print('Both menus, all six routes, saved-result identity, tab switching, prior output/subtitle preservation, busy/missing-file guards and layout passed.')


if __name__=='__main__':
    main()
