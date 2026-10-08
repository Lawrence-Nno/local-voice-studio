"""Check preparation time and cancellation without accessing the microphone."""
import time
import tkinter as tk
from unittest.mock import patch

from app.storage import DATA,configure_runtime


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    panel=app.recorder_panel
    panel.devices={'Test microphone':(0,48000)}
    panel.device.set('Test microphone')
    previous=DATA/'verification/previous-countdown-take.wav'
    panel.output=previous
    def pump(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            root.update()
            time.sleep(.01)
    with patch.object(panel.recorder,'start') as capture:
        panel.start()
        assert panel.timer.get()=='Starting in 3'
        assert app.recording_running and str(panel.pause_button['state'])=='disabled'
        with patch('app.converter_ui.messagebox.showinfo') as notice:
            app.converter_panel.start()
            assert notice.called
        pump(.2)
        panel.stop()
        assert not app.recording_running and panel.output==previous
        pump(3.1)
        capture.assert_not_called()
        began=time.monotonic()
        panel.start()
        pump(2.8)
        capture.assert_not_called()
        pump(.4)
        capture.assert_called_once_with(0,48000)
        assert time.monotonic()-began>=3
        assert panel.countdown_remaining is None
        assert panel.stop_button['text']=='Stop and save'
        panel.recorder.events.put(('complete',(previous,False)))
        pump(.2)
        assert not app.recording_running
    app.close()
    print('Three-second delayed capture, no early capture, cancel removes pending start, previous take retention and shared job lock passed.')


if __name__=='__main__':
    main()
