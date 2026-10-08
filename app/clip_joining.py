"""Join selected clips through the existing offline audio runtime."""
import json
import sys
import tempfile
from pathlib import Path


def join_clips(clips,destination,rate=44100,channels='Stereo',gap=0):
    import math
    import numpy as np
    import soundfile as sf
    from .audio_editor import render_edit
    from .conversion_worker import convert
    destination=Path(destination)
    if not 2 <= len(clips) <= 50:
        raise ValueError('Add between 2 and 50 clips to join.')
    if rate not in (24000,44100,48000) or channels not in ('Mono','Stereo') or not math.isfinite(gap) or not 0 <= gap <= 10:
        raise ValueError('Choose supported output settings and a gap from 0 to 10 seconds.')
    if any(Path(clip['source']).resolve()==destination.resolve() for clip in clips):
        raise ValueError('Choose a new output file to preserve the source clips.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_suffix('.partial.wav')
    count=1 if channels=='Mono' else 2
    frames=0
    clipped=False
    try:
        with tempfile.TemporaryDirectory(dir=destination.parent,prefix='join-work-') as work:
            with sf.SoundFile(temporary,'w',samplerate=rate,channels=count,subtype='PCM_16') as output:
                for index,clip in enumerate(clips):
                    selected=Path(work)/'selected.wav'
                    converted=Path(work)/'converted.wav'
                    source=Path(clip['source'])
                    info=sf.info(source)
                    result=render_edit(source,selected,float(clip.get('start',0)),float(clip.get('end',info.duration)),float(clip.get('gain',1)),float(clip.get('fade_in',0)),float(clip.get('fade_out',0)))
                    clipped |= result['clipped']
                    convert(selected,converted,'WAV',rate,channels)
                    with sf.SoundFile(converted) as audio:
                        if (frames+len(audio)+round(gap*rate)*(len(clips)-index-1))/rate>3600:
                            raise ValueError('Joined audio must be at most one hour long.')
                        for block in audio.blocks(blocksize=65536,dtype='float32',always_2d=True):
                            output.write(block)
                            frames+=len(block)
                    if index<len(clips)-1:
                        remaining=round(gap*rate)
                        while remaining:
                            size=min(65536,remaining)
                            output.write(np.zeros((size,count),dtype='float32'))
                            frames+=size
                            remaining-=size
        temporary.replace(destination)
        return {'duration':frames/rate,'rate':rate,'channels':count,'clipped':clipped,'clips':len(clips)}
    finally:
        temporary.unlink(missing_ok=True)


if __name__=='__main__':
    try:
        print(json.dumps({'ok':True,'result':join_clips(**json.loads(sys.stdin.readline()))}))
    except Exception as exc:
        print(json.dumps({'ok':False,'error':str(exc)}))
