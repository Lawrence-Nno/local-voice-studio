"""Real cleanup DSP plus native comparison/export/cancellation checks."""
import sys
from app.storage import ROOT,DATA,configure_runtime


def dsp():
    import numpy as np
    import soundfile as sf
    from app.cleanup_worker import cleanup
    directory=DATA/'verification/cleanup'
    directory.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(9)
    audio=rng.normal(0,.025,(80000,2))
    audio[16000:64000]+= (.2*np.sin(2*np.pi*220*np.arange(48000)/16000))[:,None]
    source=directory/'noisy.wav'
    sf.write(source,audio,16000,subtype='PCM_16')
    originalbytes=source.read_bytes()
    output=directory/'cleaned.wav'
    reference=directory/'original.wav'
    cleanup(source,output,reference,strength=1,volume=1,normalize=False)
    original,_=sf.read(source,always_2d=True)
    cleaned,rate=sf.read(output,always_2d=True)
    assert cleaned.shape==original.shape and rate==16000
    assert np.sqrt(np.mean(cleaned[:14000]**2)) < .95*np.sqrt(np.mean(original[:14000]**2))
    cleanup(source,output,reference,strength=0,volume=1,normalize=False)
    bypass,_=sf.read(output,always_2d=True)
    np.testing.assert_array_equal(original,bypass)
    info=cleanup(source,output,reference,strength=0,volume=2,normalize=True,rumble=True)
    cleaned,_=sf.read(output,always_2d=True)
    assert np.max(np.abs(cleaned))<=.981
    assert source.read_bytes()==originalbytes
    print('Noise attenuation, exact bypass, stereo/duration/rate preservation, volume/peak protection and source bytes passed.')


def ui():
    import subprocess,time,tkinter as tk
    from unittest.mock import patch
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from PIL import ImageGrab
    interpreter=ROOT/'runtime/qwen/python.exe'
    if not interpreter.is_file():
        interpreter=ROOT/'.venv-qwen/Scripts/python.exe'
    subprocess.run([str(interpreter),'-E','-s','-m','scripts.check_cleanup','--dsp'],cwd=ROOT,check=True)
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    panel=app.cleanup_panel
    app.notebook.select(6)
    panel.use(DATA/'verification/cleanup/noisy.wav')
    def wait():
        deadline=time.monotonic()+30
        while app.conversion_running and time.monotonic()<deadline:
            root.update()
            time.sleep(.02)
        root.update()
        assert not app.conversion_running
    panel.start()
    wait()
    assert panel.output and panel.output.is_file()
    with patch('app.cleanup_ui.winsound.PlaySound') as play:
        panel.play(True)
        panel.play(False)
        assert play.call_count==2
    destination=DATA/'verification/cleanup/export.wav'
    with patch('app.converter_ui.filedialog.asksaveasfilename',return_value=str(destination)):
        panel.export()
    assert destination.read_bytes()==panel.output.read_bytes()
    previous=panel.output
    panel.start()
    panel.cancel.set()
    wait()
    assert panel.output==previous
    root.update()
    for widget in [*panel.controls,panel.export_button]:
        assert widget.winfo_rootx()+widget.winfo_width()<=root.winfo_rootx()+root.winfo_width()
        assert widget.winfo_rooty()+widget.winfo_height()<=root.winfo_rooty()+root.winfo_height()
    ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(DATA/'cleanup-ui-preview.png')
    app.close()
    print('Native cleanup, original/cleaned playback handoff, export, cancellation and layout passed.')


if __name__=='__main__':
    configure_runtime()
    dsp() if '--dsp' in sys.argv else ui()
