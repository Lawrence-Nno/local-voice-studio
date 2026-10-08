"""Offline stereo-preserving noise reduction and volume adjustment."""
import json
import math
import sys
from pathlib import Path


def cleanup(source, destination, original, strength=.35, volume=1, normalize=True, rumble=False):
    import av
    import numpy as np
    import soundfile as sf
    from scipy import signal, ndimage
    if not all(math.isfinite(x) for x in (strength, volume)) or not 0 <= strength <= 1 or not 0 <= volume <= 2:
        raise ValueError('Invalid cleanup strength or volume.')
    source,destination,original = map(Path,(source,destination,original))
    if source.resolve() in (destination.resolve(),original.resolve()):
        raise ValueError('Save cleanup to a new file.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    processed = destination.with_suffix('.processing.wav')
    try:
        with av.open(str(source)) as container:
            if not container.streams.audio:
                raise ValueError('No audio stream found.')
            stream=container.streams.audio[0]
            rate=stream.codec_context.sample_rate
            channels=len(stream.codec_context.layout.channels)
            if channels not in (1,2) or not 8000 <= rate <= 192000:
                raise ValueError('Use mono/stereo audio at 8 to 192 kHz.')
            layout='mono' if channels==1 else 'stereo'
            resampler=av.AudioResampler(format='fltp',layout=layout,rate=rate)
            frames=0
            with sf.SoundFile(original,'w',samplerate=rate,channels=channels,subtype='PCM_16') as output:
                for frame in container.decode(stream):
                    for converted in resampler.resample(frame):
                        block=converted.to_ndarray().T
                        if not np.isfinite(block).all():
                            raise ValueError('Invalid audio samples.')
                        output.write(block)
                        frames+=len(block)
                        if frames/rate>3600:
                            raise ValueError('Use audio up to one hour long.')
                for converted in resampler.resample(None):
                    output.write(converted.to_ndarray().T)
                    frames+=converted.samples
        if not frames:
            raise ValueError('No decodable audio found.')
        # Sample quiet spectral frames across the file; do not assume opening silence.
        noise=[]
        with sf.SoundFile(original) as audio:
            for channel in range(channels):
                candidates=[]
                for offset in np.linspace(0,max(0,frames-rate),min(40,max(1,math.ceil(frames/rate))),dtype=int):
                    audio.seek(int(offset))
                    samples=audio.read(min(rate,frames-int(offset)),dtype='float64',always_2d=True)[:,channel]
                    samples=np.pad(samples,(0,max(0,1024-len(samples))))
                    _,_,z=signal.stft(samples,nperseg=1024,noverlap=768)
                    power=np.abs(z[:,2:-2] if z.shape[1]>4 else z)**2
                    quiet=np.argsort(power.mean(axis=0))[:max(1,power.shape[1]//10)]
                    candidates.extend(power[:,quiet].T)
                candidates=np.asarray(candidates)
                quiet=np.argsort(candidates.mean(axis=1))[:max(1,len(candidates)//4)]
                noise.append(np.median(candidates[quiet],axis=0)[:,None])
        peak=energy=0.
        filter_sos=signal.butter(2,70,fs=rate,btype='highpass',output='sos')
        states=[np.zeros((len(filter_sos),2)) for _ in range(channels)]
        with sf.SoundFile(original) as audio, sf.SoundFile(processed,'w',samplerate=rate,channels=channels,subtype='FLOAT') as output:
            for offset in range(0,frames,65536):
                count=min(65536,frames-offset)
                begin=max(0,offset-1024)
                audio.seek(begin)
                block=audio.read(min(frames-begin,count+offset-begin+1024),dtype='float64',always_2d=True)
                result=np.empty((count,channels))
                for channel in range(channels):
                    samples=block[:,channel]
                    if strength:
                        padded=np.pad(samples,(0,max(0,1024-len(samples))))
                        _,_,z=signal.stft(padded,nperseg=1024,noverlap=768)
                        power=np.abs(z)**2
                        gain=np.sqrt(np.maximum(0,1-strength*noise[channel]/np.maximum(power,1e-18)))
                        gain=np.maximum(1-.85*strength,ndimage.uniform_filter(gain,size=(3,3)))
                        _,restored=signal.istft(z*gain,nperseg=1024,noverlap=768)
                        samples=restored[:len(samples)]
                    samples=samples[offset-begin:offset-begin+count]
                    if rumble:
                        samples,states[channel]=signal.sosfilt(filter_sos,samples,zi=states[channel])
                    result[:,channel]=samples
                output.write(result)
                peak=max(peak,float(np.max(np.abs(result))))
                energy+=float(np.sum(result**2))
        rms=math.sqrt(energy/(frames*channels))
        auto=min(10,10**(-20/20)/rms) if normalize and rms>1e-8 else 1
        requested=auto*volume
        gain=min(requested,.98/peak) if peak else requested
        with sf.SoundFile(processed) as audio,sf.SoundFile(destination,'w',samplerate=rate,channels=channels,subtype='PCM_16') as output:
            for block in audio.blocks(blocksize=65536,dtype='float64',always_2d=True):
                output.write(block*gain)
        return {'format':'Cleaned WAV','rate':rate,'channels':channels,'duration':frames/rate,'bytes':destination.stat().st_size,
                'original':str(original),'gain':gain,'peak_protection':gain<requested,'strength':strength}
    except Exception:
        destination.unlink(missing_ok=True)
        original.unlink(missing_ok=True)
        raise
    finally:
        processed.unlink(missing_ok=True)


if __name__=='__main__':
    try:
        print(json.dumps({'ok':True,'result':cleanup(**json.loads(sys.stdin.readline()))}))
    except Exception as exc:
        print(json.dumps({'ok':False,'error':str(exc)}))
