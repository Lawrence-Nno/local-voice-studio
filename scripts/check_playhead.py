"""Real output-device playback and native editor timeline checks."""
import time
import tkinter as tk
from types import SimpleNamespace
import numpy as np
import soundfile as sf
from app.storage import DATA, configure_runtime


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    panel=app.editor_panel
    app.notebook.select(4)
    folder=DATA/'verification'
    folder.mkdir(parents=True,exist_ok=True)
    source=folder/'playhead-test.wav'
    sf.write(source,.015*np.sin(2*np.pi*220*np.arange(32000)/8000),8000)
    original=source.read_bytes()
    def pump(seconds):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            root.update()
            time.sleep(.01)
    try:
        panel.load(source)
        pump(.8)
        assert panel.info
        panel.play_source()
        pump(.6)
        assert .1<panel.playhead_time<1.2
        assert panel.canvas.find_withtag('playhead')
        panel.pause_playback()
        pump(.1)
        held=panel.playhead_time
        pump(.3)
        assert abs(panel.playhead_time-held)<.01
        panel.set_boundary(True)
        assert abs(float(panel.start_time.get())-held)<.001
        panel.seek_waveform(SimpleNamespace(x=panel.canvas.winfo_width()/2))
        panel.set_boundary(False)
        assert abs(float(panel.end_time.get())-2)<.001
        panel.pause_playback()
        pump(.9)
        assert panel.playhead_time>2.1
        panel.stop_playback()
        pump(.1)
        assert panel.playhead_time==0
        panel.start_time.set('1')
        panel.end_time.set('2')
        panel.render(True)
        pump(.9)
        assert 1.05<panel.playhead_time<2.01
        pump(1.2)
        assert not panel.playback.playing
        assert abs(panel.playhead_time-2)<.01
        panel.play_source()
        pump(.1)
        app.notebook.select(5)
        pump(.1)
        assert not panel.playback.playing
        app.notebook.select(4)
        root.update()
        for control in (panel.play_button,panel.pause_button,panel.export_button,*panel.controls):
            assert control.winfo_ismapped()
            assert control.winfo_rooty()+control.winfo_height() <= root.winfo_rooty()+root.winfo_height()
            assert control.winfo_rootx()+control.winfo_width() <= root.winfo_rootx()+root.winfo_width()
        assert source.read_bytes()==original
        from PIL import ImageGrab
        root.attributes('-topmost',True)
        pump(.2)
        ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(folder/'playhead-ui.png')
        print('Real playback, playhead, pause/resume, seek, boundaries, preview offsets, finish, tab stop and layout passed.')
    finally:
        panel.stop_playback()
        root.destroy()


if __name__=='__main__': main()
