"""Measure effect behavior and verify native processing/export/cancellation."""
import sys
from app.storage import ROOT,DATA,configure_runtime


def dsp():
    import numpy as np
    from app.voice_effects import apply_effects
    rate=24000
    tone=(.2*np.sin(2*np.pi*440*np.arange(rate*2)/rate)).astype('float32')[:,None]
    def frequency(audio):
        samples=audio[rate//4:-rate//4,0]
        return np.fft.rfftfreq(len(samples),1/rate)[np.argmax(np.abs(np.fft.rfft(samples)))]
    bypass,_=apply_effects(tone,rate)
    np.testing.assert_array_equal(bypass,tone)
    fast,_=apply_effects(tone,rate,speed=2)
    assert len(fast)==len(tone)//2 and abs(frequency(fast)-440)<5
    pitched,_=apply_effects(tone,rate,pitch=12)
    assert len(pitched)==len(tone) and abs(frequency(pitched)-880)<5
    stereo=np.column_stack((tone[:,0],tone[:,0]*.5))
    wet,gain=apply_effects(stereo,rate,reverb=.7,radio=True)
    assert wet.shape==(len(tone)+round(.6*rate),2)
    assert np.max(np.abs(wet))<=.981 and np.any(np.abs(wet[len(tone):])>1e-5)
    high=(.2*np.sin(2*np.pi*7000*np.arange(rate)/rate))[:,None]
    radio,_=apply_effects(high,rate,radio=True)
    assert np.sqrt(np.mean(radio**2))<.1*np.sqrt(np.mean(high**2))
    print('Exact bypass, independent speed/pitch, measured pitch shift, reverb tail, stereo and radio filtering passed.')


def ui():
    import subprocess,time,tkinter as tk
    from pathlib import Path
    from unittest.mock import patch
    import numpy as np
    import soundfile as sf
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from PIL import ImageGrab
    interpreter=ROOT/'runtime/qwen/python.exe'
    if not interpreter.is_file():
        interpreter=ROOT/'.venv-qwen/Scripts/python.exe'
    subprocess.run([str(interpreter),'-E','-s','-m','scripts.check_effects','--dsp'],cwd=ROOT,check=True)
    directory=DATA/'verification/effects'
    directory.mkdir(parents=True,exist_ok=True)
    source=directory/'source.wav'
    sf.write(source,.2*np.sin(2*np.pi*440*np.arange(48000)/24000),24000)
    original=source.read_bytes()
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    panel=app.effects_panel
    app.notebook.select(8)
    panel.use(source)
    panel.speed.set(1.25)
    panel.pitch.set(2)
    panel.reverb.set(.2)
    panel.radio.set(True)
    def wait():
        end=time.monotonic()+120
        while app.conversion_running and time.monotonic()<end:
            root.update()
            time.sleep(.02)
        root.update()
        assert not app.conversion_running
    panel.start()
    wait()
    assert panel.output and abs(sf.info(panel.output).duration-2.2)<.001
    assert source.read_bytes()==original
    destination=directory/'export.wav'
    with patch('app.converter_ui.filedialog.asksaveasfilename',return_value=str(destination)):
        panel.export()
    assert destination.read_bytes()==panel.output.read_bytes()
    with patch('app.effects_ui.winsound.PlaySound') as play:
        panel.play(True)
        panel.play(False)
        assert play.call_count==2
    saved=panel.output
    panel.start()
    panel.cancel.set()
    wait()
    assert panel.output==saved
    panel.reset()
    assert panel.speed.get()==1 and panel.pitch.get()==0 and panel.reverb.get()==0 and not panel.radio.get()
    root.update()
    for control in [*panel.controls,panel.export_button]:
        assert control.winfo_ismapped()
        assert control.winfo_rootx()+control.winfo_width()<=root.winfo_rootx()+root.winfo_width()
        assert control.winfo_rooty()+control.winfo_height()<=root.winfo_rooty()+root.winfo_height()
    ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(DATA/'effects-ui-preview.png')
    app.close()
    print('Native combined effects, expected duration, export, comparison handoff, cancellation, reset and layout passed.')


if __name__=='__main__':
    configure_runtime()
    dsp() if '--dsp' in sys.argv else ui()
