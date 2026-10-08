"""Real codec round trips plus native conversion/export/cancellation checks."""
import sys
from pathlib import Path

from app.storage import ROOT, DATA, configure_runtime


def codecs():
    import av
    import numpy as np
    import soundfile as sf
    from app.conversion_worker import convert
    from app.converter_ui import EXTENSIONS
    directory = DATA/'verification/converter'
    directory.mkdir(parents=True,exist_ok=True)
    source = directory/'source.wav'
    audio = np.column_stack((.3*np.sin(2*np.pi*220*np.arange(48000)/24000),.2*np.sin(2*np.pi*440*np.arange(48000)/24000)))
    sf.write(source,audio,24000,subtype='PCM_16')
    original = source.read_bytes()
    for format_name, extension in EXTENSIONS.items():
        path = directory/('encoded'+extension)
        result = convert(source,path,format_name,48000,'Stereo',192000)
        with av.open(str(path)) as container:
            frames = list(container.decode(audio=0))
        assert frames and all(len(f.layout.channels)==2 for f in frames)
        duration = sum(f.samples/f.sample_rate for f in frames)
        assert abs(duration-2)<.1, (format_name,duration)
        decoded = directory/(format_name.split()[0]+'-roundtrip.wav')
        convert(path,decoded,'WAV',24000,'Mono',192000)
        assert sf.info(decoded).channels==1
        assert abs(sf.info(decoded).duration-2)<.1
        assert source.read_bytes()==original
    with av.open(str(directory/'encoded.flac')) as container:
        assert container.streams.audio[0].codec_context.name=='flac'
    try:
        convert(source,source,'WAV')
    except ValueError:
        pass
    else:
        raise AssertionError('Source overwrite allowed')
    print('Five formats encoded/decoded; duration, channels, resampling, round trips and source protection passed.')


def ui():
    import subprocess
    import time
    import tkinter as tk
    from unittest.mock import patch
    import numpy as np
    import soundfile as sf
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from PIL import ImageGrab
    interpreter=ROOT/'runtime/qwen/python.exe'
    if not interpreter.is_file():
        interpreter=ROOT/'.venv-qwen/Scripts/python.exe'
    subprocess.run([str(interpreter),'-E','-s','-m','scripts.check_converter','--codecs'],cwd=ROOT,check=True)
    directory=DATA/'verification/converter'
    source=directory/'source.wav'
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    panel=app.converter_panel
    app.notebook.select(5)
    panel.use(source)
    panel.format.set('MP3')
    def wait():
        deadline=time.monotonic()+20
        while app.conversion_running and time.monotonic()<deadline:
            root.update()
            time.sleep(.02)
        root.update()
        assert not app.conversion_running
    panel.start()
    wait()
    assert panel.output and panel.output.suffix=='.mp3'
    saved=panel.output
    export=directory/'exported.mp3'
    with patch('app.converter_ui.filedialog.asksaveasfilename',return_value=str(export)):
        panel.export()
    assert export.read_bytes()==saved.read_bytes()
    with patch('app.converter_ui.filedialog.asksaveasfilename',return_value=str(source)),patch('app.converter_ui.messagebox.showerror') as error:
        panel.export()
        assert error.called
    panel.start()
    panel.cancel.set()
    wait()
    assert panel.output==saved
    invalid=directory/'invalid.wav'
    invalid.write_text('invalid audio')
    panel.use(invalid)
    with patch('app.converter_ui.messagebox.showerror') as error:
        panel.start()
        wait()
        assert error.called
    assert panel.output==saved
    panel.format.set('OGG (Opus)')
    assert str(panel.choices[1]['state'])=='disabled'
    panel.format.set('FLAC')
    assert str(panel.choices[3]['state'])=='disabled'
    root.update()
    for control in [*panel.controls,*panel.choices,panel.export_button]:
        assert control.winfo_rootx()+control.winfo_width()<=root.winfo_rootx()+root.winfo_width()
        assert control.winfo_rooty()+control.winfo_height()<=root.winfo_rooty()+root.winfo_height()
    ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(DATA/'converter-ui-preview.png')
    app.close()
    print('Native conversion, export, overwrite protection, cancellation, invalid-file recovery and layout passed.')


if __name__=='__main__':
    configure_runtime()
    codecs() if '--codecs' in sys.argv else ui()
