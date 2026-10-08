"""Verify read-only metadata, compressed fallback and native information window."""
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from app.storage import ROOT,DATA,configure_runtime
from app.audio_info import inspect_audio


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from PIL import ImageGrab
    directory=DATA/'verification/audio-info'
    directory.mkdir(parents=True,exist_ok=True)
    source=directory/'stereo.wav'
    sf.write(source,np.zeros((48000,2)),24000)
    original=source.read_bytes()
    info=inspect_audio(source)
    assert info['duration']==2 and info['channels']==2 and info['rate']==24000
    assert info['bytes']==source.stat().st_size and 'WAV' in info['format']
    # AAC requires PyAV fallback, unlike WAV/FLAC read by SoundFile.
    import subprocess,json
    interpreter=ROOT/'runtime/qwen/python.exe'
    if not interpreter.is_file():
        interpreter=ROOT/'.venv-qwen/Scripts/python.exe'
    m4a=directory/'test.m4a'
    result=subprocess.run([str(interpreter),'-E','-s','-m','app.conversion_worker'],cwd=ROOT,input=json.dumps({'source':str(source),'destination':str(m4a),'format_name':'M4A (AAC)'})+'\n',text=True,capture_output=True,encoding='utf-8',check=True)
    assert json.loads(result.stdout)['ok']
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    app.recorder_panel.output=source
    app.notebook.select(3)
    app.open_audio_info()
    dialog=app.audio_info_dialog
    def wait():
        end=time.monotonic()+20
        while dialog.loading and time.monotonic()<end:
            root.update()
            time.sleep(.02)
        root.update()
        assert not dialog.loading
    wait()
    assert dialog.info['duration']==2
    assert 'Voice recorder' in dialog.selected.get()
    dialog.copy()
    assert '24,000 Hz' in root.clipboard_get() and '2 (stereo)' in root.clipboard_get()
    dialog.load(m4a)
    wait()
    assert dialog.info['channels']==2 and abs(dialog.info['duration']-2)<.1
    assert 'AAC' in dialog.info['codec']
    assert source.read_bytes()==original
    with patch('app.audio_info_ui.messagebox.showerror') as error:
        dialog.load(directory/'missing.wav')
        wait()
        assert error.called
    assert dialog.info is None and str(dialog.copy_button['state'])=='disabled'
    dialog.load(source)
    wait()
    for widget in (dialog.choose_button,dialog.combo,dialog.copy_button):
        assert widget.winfo_ismapped()
        assert widget.winfo_rooty()+widget.winfo_height()<=dialog.winfo_rooty()+dialog.winfo_height()
    ImageGrab.grab(bbox=(dialog.winfo_rootx(),dialog.winfo_rooty(),dialog.winfo_rootx()+dialog.winfo_width(),dialog.winfo_rooty()+dialog.winfo_height())).save(DATA/'audio-info-ui-preview.png')
    dialog.destroy()
    app.close()
    print('WAV/AAC information, exact size/rate/channels, current-tab selection, clipboard, missing-file recovery, read-only source and layout passed.')


if __name__=='__main__':
    main()
