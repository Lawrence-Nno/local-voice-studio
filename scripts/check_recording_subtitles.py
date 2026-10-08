"""Verify recorded-take handoff without starting microphone capture or ASR."""
import tkinter as tk
from unittest.mock import patch

import numpy as np
import soundfile as sf

from app.storage import DATA, configure_runtime


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    configure_dpi()
    directory = DATA / 'verification'
    directory.mkdir(parents=True, exist_ok=True)
    take = directory / 'recording-shortcut-test.wav'
    sf.write(take, np.zeros(8000), 8000)
    root = tk.Tk()
    app = VoiceApp(root)
    recorder, subtitles = app.recorder_panel, app.subtitles
    assert str(recorder.subtitle_button['state']) == 'disabled'
    recorder.output = take
    recorder.controls(False)
    assert str(recorder.subtitle_button['state']) == 'normal'
    subtitles.source = {'mode': 'align', 'sections': ['old script']}
    subtitles.result_source = str(directory / 'previous.wav')
    reviewed = '1\n00:00:00,000 --> 00:00:01,000\nReviewed words\n'
    subtitles.text.insert('1.0', reviewed)
    recorder.use_subtitles()
    assert app.notebook.select() == str(subtitles.parent)
    assert subtitles.source == {'mode': 'transcribe', 'audio': str(take)}
    assert subtitles.text.get('1.0', 'end').strip() == reviewed.strip()
    assert 'previous.wav' in subtitles.filename.get()
    recorder.controls(True)
    assert str(recorder.subtitle_button['state']) == 'disabled'
    app.recording_running = True
    with patch('app.recorder_ui.messagebox.showinfo') as notice:
        recorder.use_subtitles()
        assert notice.called
    app.recording_running = False
    recorder.controls(False)
    recorder.output = directory / 'missing-recording.wav'
    with patch('app.recorder_ui.messagebox.showerror') as error:
        recorder.use_subtitles()
        assert error.called
    assert subtitles.source['audio'] == str(take)
    app.notebook.select(3)
    root.update()
    button = recorder.subtitle_button
    assert button.winfo_rootx()+button.winfo_width() <= root.winfo_rootx()+root.winfo_width()
    assert button.winfo_rooty()+button.winfo_height() <= root.winfo_rooty()+root.winfo_height()
    app.close()
    print('Recorded audio handoff, transcription mode, tab switching, prior subtitle preservation, busy/missing-file guards and layout passed.')


if __name__ == '__main__':
    main()
