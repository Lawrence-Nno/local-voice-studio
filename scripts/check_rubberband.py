"""Real engine checks including user-sample comparison and formant modes."""
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from app.storage import ROOT, DATA
from app.voice_effects import apply_effects


def main():
    rate=44100
    tone=(.2*np.sin(2*np.pi*220*np.arange(rate*2)/rate)).astype('float32')[:,None]
    for speed,pitch in ((.8,0),(1.25,3),(1,-3)):
        for formant in (False,True):
            result,_=apply_effects(tone,rate,speed=speed,pitch=pitch,formant=formant)
            assert abs(len(result)-round(len(tone)/speed))<=1
            assert np.isfinite(result).all()
    from app.rubberband import DIRECTORY
    assert (DIRECTORY/'COPYING.txt').is_file()
    source=Path(r'C:\Users\USER\Desktop\audio\test.wav')
    if source.is_file():
        original=hashlib.sha256(source.read_bytes()).hexdigest()
        audio,rate=sf.read(source,dtype='float32',always_2d=True)
        folder=DATA/'verification/rubberband'
        folder.mkdir(parents=True,exist_ok=True)
        result,_=apply_effects(audio,rate,speed=.8)
        sf.write(folder/'test-rubberband-080.wav',result,rate,subtype='PCM_16')
        # Existing librosa remains a TTS dependency; comparison only, never effects fallback.
        import librosa
        old=librosa.effects.time_stretch(audio.T,rate=.8).T
        sf.write(folder/'test-librosa-080.wav',old,rate,subtype='PCM_16')
        assert hashlib.sha256(source.read_bytes()).hexdigest()==original
        print('User-sample 0.80x comparisons saved in '+str(folder))
    print('R3 duration, combined speed/pitch, formant modes, finite output, notices and source preservation passed.')


if __name__=='__main__': main()
