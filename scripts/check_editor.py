"""Native editor workflow with synthetic audio; no microphone capture needed."""
import time
import tkinter as tk
from unittest.mock import patch

import numpy as np
import soundfile as sf

from app.storage import DATA, configure_runtime


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from PIL import ImageGrab
    configure_dpi()
    directory = DATA / 'verification'
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'editor-test-source.wav'
    sf.write(source, .3*np.sin(2*np.pi*220*np.arange(32000)/8000), 8000)
    original = source.read_bytes()
    root = tk.Tk()
    app = VoiceApp(root)
    panel = app.editor_panel
    app.notebook.select(4)
    def wait():
        end = time.monotonic() + 10
        while app.editor_running and time.monotonic() < end:
            root.update()
            time.sleep(.02)
        root.update()
        assert not app.editor_running
    panel.load(source)
    wait()
    assert panel.info['duration'] == 4
    panel.start_time.set('1')
    panel.end_time.set('3')
    panel.fade_in.set('.1')
    panel.fade_out.set('.1')
    panel.render(False)
    wait()
    assert panel.output and sf.info(panel.output).duration == 2
    exported = directory / 'editor-export.wav'
    with patch('app.editor_ui.filedialog.asksaveasfilename', return_value=str(exported)):
        panel.export()
    assert exported.read_bytes() == panel.output.read_bytes()
    with patch('app.editor_ui.filedialog.asksaveasfilename', return_value=str(source)), patch('app.editor_ui.messagebox.showerror') as error:
        panel.export()
        assert error.called
    assert source.read_bytes() == original
    panel.render(True)
    wait()
    saved = panel.output
    panel.end_time.set('99')
    with patch('app.editor_ui.messagebox.showerror') as error:
        panel.render(False)
        wait()
        assert error.called
    assert panel.output == saved
    panel.reset()
    root.update()
    for control in [*panel.controls, panel.export_button, panel.reference_button]:
        assert control.winfo_rootx()+control.winfo_width() <= root.winfo_rootx()+root.winfo_width()
        assert control.winfo_rooty()+control.winfo_height() <= root.winfo_rooty()+root.winfo_height()
    ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(DATA/'editor-ui-preview.png')
    app.close()
    print('Waveform, trim/fades, preview, export, source preservation, invalid-edit recovery and native layout passed.')


if __name__ == '__main__':
    main()
