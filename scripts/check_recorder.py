"""Exercise the recorder with a real microphone, pause/resume, and native UI."""
import queue
import time
import tkinter as tk
from unittest.mock import patch

import soundfile as sf

from app.storage import DATA, configure_runtime


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from PIL import ImageGrab
    configure_dpi()
    root = tk.Tk()
    app = VoiceApp(root)
    panel = app.recorder_panel
    app.notebook.select(3)
    root.update()
    assert panel.devices, "No input devices available"
    panel.start()
    assert app.recording_running
    def pump(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            root.update()
            time.sleep(.02)
    pump(4.2) # Three-second preparation countdown, then microphone capture.
    panel.pause()
    pump(.2)
    before = panel.recorder.seconds
    pump(.5)
    assert panel.recorder.seconds == before, "Paused audio was saved"
    panel.pause()
    pump(.8)
    panel.stop()
    end = time.monotonic() + 10
    while app.recording_running and time.monotonic() < end:
        pump(.1)
    assert not app.recording_running and panel.output
    info = sf.info(panel.output)
    assert info.channels == 1 and info.subtype == "PCM_16" and 1 < info.duration < 3
    exported = DATA / "verification" / "recorder-export.wav"
    exported.parent.mkdir(parents=True, exist_ok=True)
    with patch('app.recorder_ui.filedialog.asksaveasfilename', return_value=str(exported)):
        panel.export()
    assert exported.read_bytes() == panel.output.read_bytes()
    with patch.object(app, 'import_voice') as use:
        panel.use_reference()
        use.assert_called_once_with(source=panel.output)
    # A failed new take must preserve the previous successful recording.
    previous = panel.output
    panel.recorder.events.put(('error', 'Simulated disconnected microphone'))
    with patch('app.recorder_ui.messagebox.showerror'):
        panel.poll()
    assert panel.output == previous
    root.update()
    for button in [panel.start_button, panel.stop_button, *panel.result_buttons]:
        assert button.winfo_rootx() + button.winfo_width() <= root.winfo_rootx() + root.winfo_width()
        assert button.winfo_rooty() + button.winfo_height() <= root.winfo_rooty() + root.winfo_height()
    ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(DATA / 'recorder-ui-preview.png')
    app.close()
    print('Microphone capture, pause/resume, mono PCM WAV, export, reference handoff, error recovery and UI passed.')


if __name__ == '__main__':
    main()
