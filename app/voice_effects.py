"""Independent time/pitch effects plus room reverb and radio filtering."""
import math


def apply_effects(audio,rate,speed=1,pitch=0,reverb=0,radio=False):
    import numpy as np
    from scipy import signal
    audio=np.asarray(audio,dtype=np.float32)
    if audio.ndim!=2 or not len(audio) or audio.shape[1] not in (1,2) or not np.isfinite(audio).all():
        raise ValueError('Use finite mono/stereo audio.')
    if not all(math.isfinite(x) for x in (speed,pitch,reverb)) or not .5<=speed<=2 or not -12<=pitch<=12 or not 0<=reverb<=1:
        raise ValueError('Speed must be 0.5-2x, pitch -12 to +12 semitones, and reverb 0-100%.')
    result=audio.T.copy()
    if speed!=1 or pitch!=0:
        import librosa
        if speed!=1:
            result=librosa.effects.time_stretch(result,rate=speed)
        if pitch!=0:
            result=librosa.effects.pitch_shift(result,sr=rate,n_steps=pitch)
    result=result.T
    if radio:
        sos=signal.butter(3,(300,min(3400,rate*.4)),fs=rate,btype='bandpass',output='sos')
        result=signal.sosfilt(sos,result,axis=0)
        result=np.tanh(result*2)/2
    if reverb:
        impulse=np.zeros(round(.6*rate)+1)
        for delay,amplitude in ((.029,.35),(.047,.29),(.073,.23),(.113,.18),(.173,.13),(.251,.08),(.367,.04),(.55,.015)):
            impulse[round(delay*rate)]=amplitude
        impulse/=np.sum(impulse)
        wet=signal.fftconvolve(result,impulse[:,None],mode='full',axes=0)
        dry=np.pad(result,((0,len(wet)-len(result)),(0,0)))
        result=dry+reverb*wet
    peak=float(np.max(np.abs(result)))
    gain=min(1,.98/peak) if peak else 1
    return (result*gain).astype(np.float32),gain
