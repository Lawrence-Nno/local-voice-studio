"""Native real batches: conversion, cleanup, subtitles, failures and cancellation."""
import time
import tkinter as tk
import uuid
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from app.storage import DATA,configure_runtime,read_json


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from PIL import ImageGrab
    directory=DATA/'verification/batch'
    directory.mkdir(parents=True,exist_ok=True)
    first,second=directory/'first.wav',directory/'second.wav'
    sf.write(first,.1*np.sin(2*np.pi*220*np.arange(16000)/16000),16000)
    sf.write(second,np.zeros(8000),8000)
    original=[p.read_bytes() for p in (first,second)]
    invalid=directory/'invalid.wav'
    invalid.write_text('invalid audio')
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    panel=app.batch_panel
    app.notebook.select(7)
    def wait():
        end=time.monotonic()+120
        while app.batch_running and time.monotonic()<end:
            root.update()
            time.sleep(.02)
        root.update()
        assert not app.batch_running
        return read_json(panel.last_directory/'batch-report.json')
    panel.files=[first,invalid,second]
    panel.operation.set('Convert')
    panel.start()
    app.converter_panel.format.set('FLAC') # The active batch must retain its MP3 snapshot.
    report=wait()
    assert [row['status'] for row in report['files']]==['Completed','Failed','Completed']
    assert all(Path(row['output']).suffix=='.mp3' for row in report['files'] if row['status']=='Completed')
    panel.files=[first,second]
    panel.operation.set('Cleanup')
    panel.start()
    report=wait()
    assert all(row['status']=='Completed' for row in report['files'])
    assert all(Path(row['output']).is_file() for row in report['files'])
    panel.files=[invalid,first]
    panel.continue_errors.set(False)
    panel.start()
    report=wait()
    assert [row['status'] for row in report['files']]==['Failed','Skipped']
    panel.continue_errors.set(True)
    panel.files=[first,second]
    panel.start()
    panel.cancel.set()
    report=wait()
    assert report['status']=='Cancelled'
    assert all(row['status']=='Cancelled' for row in report['files'])
    assert not list(panel.last_directory.glob('work-*'))
    from threading import Event
    from app.batch_processing import run_batch
    from app.storage import ROOT
    interpreter=ROOT/'runtime/qwen/python.exe'
    if not interpreter.is_file():
        interpreter=ROOT/'.venv-qwen/Scripts/python.exe'
    cancel=Event()
    def completed(index,state,value):
        if state=='Completed':
            cancel.set()
    report=run_batch([first,second],'Convert',{'format_name':'MP3','rate':44100,'channels':'Keep source','bitrate':192000},directory/('cancel-after-'+uuid.uuid4().hex),interpreter,cancel,completed)
    assert [row['status'] for row in report['files']]==['Completed','Cancelled']
    assert Path(report['files'][0]['output']).is_file()
    # Real speech from the existing verified sample; run ASR on two distinct paths.
    import shutil
    speech=DATA/'verification/batch/speech.wav'
    candidate=next((path for path in (DATA/'turbo-comparison/warm.wav',DATA/'verification/voice-with-running-home.wav') if path.is_file()),None)
    if not candidate:
        candidates=list((DATA/'outputs').glob('*.wav'))
        candidate=candidates[0] if candidates else None
    assert candidate,'A previously generated speech sample is needed for the subtitle batch check.'
    shutil.copyfile(candidate,speech)
    speech2=speech.with_name('speech-copy.wav')
    shutil.copyfile(speech,speech2)
    panel.files=[speech,speech2]
    panel.operation.set('Subtitles')
    app.subtitles.device.set('CPU')
    app.subtitles.language.set('English')
    panel.start()
    report=wait()
    assert all(row['status']=='Completed' for row in report['files']),report
    assert all(Path(row['output']).read_text(encoding='utf-8').strip() for row in report['files'])
    assert [p.read_bytes() for p in (first,second)]==original
    panel.open_settings()
    assert app.notebook.select()==str(app.subtitles.parent)
    app.notebook.select(7)
    root.update()
    for widget in [*panel.controls,panel.cancel_button,panel.operations]:
        assert widget.winfo_ismapped()
        assert widget.winfo_rootx()+widget.winfo_width()<=root.winfo_rootx()+root.winfo_width()
        assert widget.winfo_rooty()+widget.winfo_height()<=root.winfo_rooty()+root.winfo_height()
    ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(DATA/'batch-ui-preview.png')
    app.close()
    print('Real multi-file conversion, cleanup and CPU subtitles, settings snapshot, continue/stop on error, cancellation, reports, source preservation and layout passed.')


if __name__=='__main__':
    main()
