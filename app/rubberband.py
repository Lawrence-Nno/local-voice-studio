"""Offline Rubber Band R3 utility adapter; never falls back to librosa."""
import subprocess
import tempfile
from pathlib import Path
import soundfile as sf
from .storage import ROOT

DIRECTORY = ROOT/'tools/rubberband/rubberband-4.0.0-gpl-executable-windows'


def transform(audio, rate, speed, pitch, formant=True, work_directory=None):
    executable=DIRECTORY/'rubberband.exe'
    if not executable.is_file():
        raise ValueError('Rubber Band is missing. Run scripts/download_rubberband.py to install the official audio utility.')
    if work_directory:
        parent=Path(work_directory)
        parent.mkdir(parents=True,exist_ok=True)
    else:
        parent=ROOT/'.cache/rubberband-work'
        parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as folder:
        source=Path(folder)/'input.wav'
        output=Path(folder)/'output.wav'
        sf.write(source,audio,rate,subtype='FLOAT')
        command=[str(executable),'--fine','--quiet','--tempo',str(speed),'--pitch',str(pitch)]
        if formant and pitch!=0:
            command.append('--formant')
        if audio.shape[1]==2:
            command.append('--centre-focus')
        result=subprocess.run(command+[str(source),str(output)],capture_output=True,text=True,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:
            raise ValueError('Rubber Band processing failed: '+result.stderr[-1500:])
        processed,output_rate=sf.read(output,dtype='float32',always_2d=True)
        if output_rate!=rate or processed.shape[1]!=audio.shape[1]:
            raise ValueError('Rubber Band returned an inconsistent audio format.')
        return processed
