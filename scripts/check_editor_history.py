"""Native undo/redo grouping, branching and file preservation check."""
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
    source=folder/'history-source.wav'
    sf.write(source,np.zeros(32000),8000)
    original=source.read_bytes()
    def pump(seconds=.6):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            root.update()
            time.sleep(.01)
    try:
        panel.load(source)
        pump()
        baseline=panel.history_state()
        assert not panel.history.past
        width=panel.canvas.winfo_width()
        panel.drag_start(SimpleNamespace(x=width/4))
        for x in (width/3,width/2,3*width/4): panel.drag(SimpleNamespace(x=x))
        panel.drag_end(SimpleNamespace(x=3*width/4))
        selected=panel.history_state()
        assert len(panel.history.past)==1
        panel.restore_history(True)
        assert panel.history_state()==baseline
        panel.restore_history(False)
        assert panel.history_state()==selected
        entry=next(control for control in panel.controls if control.winfo_class()=='TEntry')
        entry.focus_force()
        root.update()
        entry.event_generate('<Control-z>')
        root.update()
        assert panel.history_state()==baseline
        entry.event_generate('<Control-y>')
        root.update()
        assert panel.history_state()==selected
        panel.begin_history_gesture()
        for value in (1.1,1.2,1.3): panel.gain.set(value)
        panel.end_history_gesture()
        assert len(panel.history.past)==2
        panel.restore_history(True)
        assert panel.gain.get()==1
        panel.fade_in.set('bad')
        panel.restore_history(True)
        assert panel.fade_in.get()=='0'
        assert panel.history.future
        panel.fade_out.set('.2')
        pump()
        assert not panel.history.future
        before_reset=panel.history_state()
        panel.reset()
        panel.restore_history(True)
        assert panel.history_state()==before_reset
        panel.playhead_time=1.5
        panel.set_boundary(True)
        assert float(panel.start_time.get())==1.5
        panel.restore_history(True)
        assert panel.history_state()==before_reset
        panel.render(False)
        pump(.9)
        assert panel.output
        saved=panel.output.read_bytes()
        panel.gain.set(.5)
        panel.restore_history(True)
        assert panel.output.read_bytes()==saved
        state=panel.history_state()
        app.batch_running=True
        panel.restore_history(True)
        assert panel.history_state()==state
        app.batch_running=False
        app.notebook.select(5)
        assert panel.history_shortcut(SimpleNamespace(widget=root),True) is None
        assert panel.history_state()==state
        app.notebook.select(4)
        panel.load(source)
        pump()
        assert not panel.history.past and not panel.history.future
        assert source.read_bytes()==original
        for control in (panel.undo_button,panel.redo_button):
            assert control.winfo_ismapped()
            assert control.winfo_rootx()+control.winfo_width() <= root.winfo_rootx()+root.winfo_width()
        from PIL import ImageGrab
        root.attributes('-topmost',True)
        pump(.2)
        ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(folder/'history-ui.png')
        print('Undo/redo grouping, invalid text recovery, branching, reset, boundaries, busy guard, source reset and saved-file preservation passed.')
    finally:
        panel.stop_playback()
        root.destroy()


if __name__=='__main__': main()
