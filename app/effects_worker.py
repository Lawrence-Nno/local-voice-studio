"""Offline voice effects with bounded input length and separate comparison WAV."""
import json
import sys
from pathlib import Path


def process(source,destination,original,speed=1,pitch=0,reverb=0,radio=False):
    import av
    import numpy as np
    import soundfile as sf
    from .voice_effects import apply_effects
    source,destination,original=map(Path,(source,destination,original))
    if source.resolve() in (destination.resolve(),original.resolve()):
        raise ValueError('Save effects to a different file.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    try:
        frames=0
        with av.open(str(source)) as container:
            if not container.streams.audio:
                raise ValueError('No audio stream found.')
            stream=container.streams.audio[0]
            channels=len(stream.codec_context.layout.channels)
            rate=min(48000,stream.codec_context.sample_rate)
            if channels not in (1,2) or rate<8000:
                raise ValueError('Use mono/stereo audio at 8 kHz or higher.')
            resampler=av.AudioResampler(format='fltp',layout='mono' if channels==1 else 'stereo',rate=rate)
            with sf.SoundFile(original,'w',samplerate=rate,channels=channels,subtype='PCM_16') as output:
                for frame in container.decode(stream):
                    for converted in resampler.resample(frame):
                        block=converted.to_ndarray().T
                        if not np.isfinite(block).all():
                            raise ValueError('Invalid audio samples.')
                        frames+=len(block)
                        if frames>600*rate:
                            raise ValueError('Voice effects supports clips up to ten minutes. Trim longer audio in Audio editor first.')
                        output.write(block)
                for converted in resampler.resample(None):
                    output.write(converted.to_ndarray().T)
                    frames+=converted.samples
        if not 0<frames<=600*rate:
            raise ValueError('Use a non-empty clip up to ten minutes long.')
        audio,_=sf.read(original,dtype='float32',always_2d=True)
        result,gain=apply_effects(audio,rate,speed,pitch,reverb,radio)
        sf.write(destination,result,rate,subtype='PCM_16')
        return {'format':'Voice effects WAV','rate':rate,'channels':channels,'duration':len(result)/rate,'bytes':destination.stat().st_size,
                'original':str(original),'peak_protection':gain<1,'speed':speed,'pitch':pitch,'reverb':reverb,'radio':radio}
    except Exception:
        destination.unlink(missing_ok=True)
        original.unlink(missing_ok=True)
        raise


if __name__=='__main__':
    try:
        print(json.dumps({'ok':True,'result':process(**json.loads(sys.stdin.readline()))}))
    except Exception as exc:
        print(json.dumps({'ok':False,'error':str(exc)}))
