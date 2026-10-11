"""Real Rubber Band target-duration and speed-map processing checks."""
import hashlib
import json
import subprocess
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
import numpy as np
import soundfile as sf
from app.storage import ROOT,DATA,configure_runtime


def dsp():
    from app.voice_effects import apply_effects
    from app.effect_timing import timing_plan
    rate=24000
    audio=(.15*np.sin(2*np.pi*440*np.arange(rate*2)/rate)).astype('float32')[:,None]
    for reverb in (0,.2):
        result,_=apply_effects(audio,rate,time_mode='Fit duration',target_duration=3,reverb=reverb)
        assert len(result)==rate*3
        assert np.isfinite(result).all()
    for start,end in ((.5,2),(2,.5),(.8,.8)):
        result,_=apply_effects(audio,rate,speed=start,time_mode='Gradual speed',end_speed=end)
        expected=timing_plan(len(audio),rate,start,'Gradual speed',end_speed=end)[1]
        assert len(result)==expected
        samples=result[rate//4:-rate//4,0]
        hz=np.fft.rfftfreq(len(samples),1/rate)[np.argmax(np.abs(np.fft.rfft(samples)))]
        assert abs(hz-440)<5
    # Verify internal event timing follows the map, not just its total duration.
    bursts=np.zeros((rate*4,1),dtype='float32')
    for second in (1,2,3):
        width=round(.06*rate)
        bursts[second*rate:second*rate+width,0]=.2*np.sin(2*np.pi*440*np.arange(width)/rate)*np.hanning(width)
    ramp,_=apply_effects(bursts,rate,speed=.5,time_mode='Gradual speed',end_speed=2)
    from scipy.signal import find_peaks
    envelope=np.array([np.mean(ramp[i:i+240,0]**2) for i in range(0,len(ramp),240)])
    peaks,_=find_peaks(envelope,distance=30)
    strongest=sorted(peaks[np.argsort(envelope[peaks])[-3:]])
    import math
    expected=[4*math.log1p(1.5*(second+.03)/(4*.5))/1.5 for second in (1,2,3)]
    assert len(strongest)==3
    assert all(abs(index*.01-time)<.12 for index,time in zip(strongest,expected)), (strongest,expected)
    print('Sample-exact final duration with/without reverb; rising/falling/constant ramps and pitch preservation passed.')


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    interpreter=ROOT/'runtime/qwen/python.exe'
    if not interpreter.exists(): interpreter=ROOT/'.venv-qwen/Scripts/python.exe'
    subprocess.run([str(interpreter),'-E','-s','-m','scripts.check_effect_timing','--dsp'],cwd=ROOT,check=True)
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    panel=app.effects_panel
    folder=DATA/'verification/effect-timing'
    folder.mkdir(parents=True,exist_ok=True)
    source=folder/'source.wav'
    sf.write(source,.1*np.sin(2*np.pi*220*np.arange(48000)/24000),24000)
    original=hashlib.sha256(source.read_bytes()).hexdigest()
    def wait():
        until=time.monotonic()+30
        while app.conversion_running and time.monotonic()<until:
            root.update()
            time.sleep(.02)
        root.update()
        assert not app.conversion_running
    try:
        app.notebook.select(8)
        panel.use(source)
        panel.time_mode.set('Fit duration')
        panel.target_duration.set('3')
        panel.reverb.set(.2)
        assert str(panel.speed_slider['state'])=='disabled'
        panel.start()
        wait()
        assert panel.output and sf.info(panel.output).frames==72000
        previous=panel.output
        panel.target_duration.set('.1')
        with patch('app.converter_ui.messagebox.showerror') as error:
            panel.start()
            wait()
            assert error.called
        assert panel.output==previous
        panel.reverb.set(0)
        panel.time_mode.set('Gradual speed')
        panel.speed.set(.5)
        panel.end_speed.set('2')
        panel.start()
        wait()
        assert panel.output!=previous
        assert panel.result_info['time_mode']=='Gradual speed'
        assert str(panel.target_entry['state'])=='disabled'
        assert panel.result_info['end_speed']==2
        panel.reset()
        assert panel.time_mode.get()=='Constant speed'
        assert hashlib.sha256(source.read_bytes()).hexdigest()==original
        canvas=app.shell.scroll_pages[app.notebook.select()]
        canvas.yview_moveto(1)
        root.update()
        assert panel.export_button.winfo_rooty()+panel.export_button.winfo_height()<=root.winfo_rooty()+root.winfo_height()
        panel.time_mode.set('Gradual speed')
        canvas.yview_moveto(0)
        root.attributes('-topmost',True)
        root.update()
        time.sleep(.2)
        root.update()
        from PIL import ImageGrab
        ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(folder/'timing-controls.png')
        print('Native mode controls, target final duration, invalid-range recovery, gradual speed, reset, source preservation and scrolling passed.')
    finally:
        root.destroy()


if __name__=='__main__':
    import sys
    dsp() if '--dsp' in sys.argv else main()
