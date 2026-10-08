"""Verify mixed-format joins, order, gaps, source protection and native controls."""
import sys
from app.storage import ROOT,DATA,configure_runtime


def dsp():
    import numpy as np
    import soundfile as sf
    from app.clip_joining import join_clips
    directory=DATA/'verification/join'
    directory.mkdir(parents=True,exist_ok=True)
    first,second=directory/'first.wav',directory/'second.flac'
    sf.write(first,np.full(8000,.2),8000)
    sf.write(second,np.full((16000,2),-.3),16000)
    before=[p.read_bytes() for p in (first,second)]
    clips=[{'source':str(first),'start':.25,'end':.75},{'source':str(second),'start':0,'end':1}]
    destination=directory/'joined.wav'
    info=join_clips(clips,destination,24000,'Stereo',.1)
    audio,rate=sf.read(destination,always_2d=True)
    assert audio.shape==(38400,2) and rate==24000
    assert abs(info['duration']-1.6)<.0001
    assert audio[4000,0]>.13 and audio[27000,0]<-.29
    assert np.max(np.abs(audio[12000:14400]))==0
    join_clips(list(reversed(clips)),destination,24000,'Mono',0)
    audio,_=sf.read(destination)
    assert audio[4000]<-.29 and audio[-4000]>.19
    assert [p.read_bytes() for p in (first,second)]==before
    try:
        join_clips(clips,first,24000,'Mono')
    except ValueError:
        pass
    else:
        raise AssertionError('Source overwrite allowed')
    previous=destination.read_bytes()
    try:
        join_clips([clips[0],{'source':str(directory/'missing.wav')}],destination)
    except Exception:
        pass
    assert destination.read_bytes()==previous
    print('Mixed rates/channels/formats, exact duration/gap, clip order and source/previous-result protection passed.')


def ui():
    import subprocess,time,tkinter as tk
    from unittest.mock import patch
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from PIL import ImageGrab
    interpreter=ROOT/'runtime/qwen/python.exe'
    if not interpreter.is_file():
        interpreter=ROOT/'.venv-qwen/Scripts/python.exe'
    subprocess.run([str(interpreter),'-E','-s','-m','scripts.check_join','--dsp'],cwd=ROOT,check=True)
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    editor=app.editor_panel
    app.notebook.select(4)
    directory=DATA/'verification/join'
    def wait():
        end=time.monotonic()+20
        while app.editor_running and time.monotonic()<end:
            root.update()
            time.sleep(.02)
        root.update()
        assert not app.editor_running
    editor.load(directory/'first.wav')
    wait()
    editor.start_time.set('.25')
    editor.end_time.set('.75')
    editor.open_join()
    dialog=editor.join_dialog
    dialog.add_selection()
    with patch('app.join_ui.filedialog.askopenfilenames',return_value=(str(directory/'second.flac'),)):
        dialog.add_files()
    assert len(dialog.clips)==2 and dialog.clips[0]['end']==.75
    dialog.list.selection_clear(0,'end')
    dialog.list.selection_set(1)
    dialog.move(-1)
    assert dialog.clips[0]['source'].endswith('second.flac')
    dialog.join(False)
    wait()
    assert editor.output and len(editor.output_sources)==2
    saved=editor.output
    with patch('app.editor_ui.filedialog.asksaveasfilename',return_value=str(directory/'first.wav')),patch('app.editor_ui.messagebox.showerror') as error:
        editor.export()
        assert error.called
    with patch('app.editor_ui.winsound.PlaySound') as playback:
        dialog.join(True)
        wait()
        assert playback.called
    assert editor.output==saved
    root.update()
    for widget in dialog.buttons:
        assert widget.winfo_rootx()+widget.winfo_width()<=dialog.winfo_rootx()+dialog.winfo_width()
        assert widget.winfo_rooty()+widget.winfo_height()<=dialog.winfo_rooty()+dialog.winfo_height()
    ImageGrab.grab(bbox=(dialog.winfo_rootx(),dialog.winfo_rooty(),dialog.winfo_rootx()+dialog.winfo_width(),dialog.winfo_rooty()+dialog.winfo_height())).save(DATA/'join-ui-preview.png')
    dialog.close()
    app.close()
    print('Native selection/file list, reorder, save/preview, export protection and layout passed.')


if __name__=='__main__':
    configure_runtime()
    dsp() if '--dsp' in sys.argv else ui()
