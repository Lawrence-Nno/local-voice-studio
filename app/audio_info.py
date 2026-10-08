"""Read local audio properties without changing or loading a speech model."""
import json
import sys
from pathlib import Path


def inspect_audio(source):
    path=Path(source)
    if not path.is_file():
        raise ValueError('The audio file is missing. Choose an existing file.')
    size=path.stat().st_size
    try:
        import soundfile as sf
        info=sf.info(path)
        if info.frames<=0:
            raise ValueError('No audio samples found.')
        return {'path':str(path.resolve()),'duration':info.duration,'format':info.format_info,
                'codec':info.subtype_info,'rate':info.samplerate,'channels':info.channels,'bytes':size,
                'duration_basis':'Audio sample count'}
    except Exception:
        import av
        with av.open(str(path)) as container:
            if not container.streams.audio:
                raise ValueError('This file has no audio stream.')
            stream=container.streams.audio[0]
            rate=stream.codec_context.sample_rate
            channels=len(stream.codec_context.layout.channels)
            duration=float(stream.duration*stream.time_base) if stream.duration is not None else container.duration/av.time_base if container.duration is not None else None
            basis='Container/stream metadata (may include codec padding)'
            if duration is None:
                duration=sum(frame.samples/frame.sample_rate for frame in container.decode(stream))
                basis='Decoded audio sample count'
            return {'path':str(path.resolve()),'duration':duration,'format':container.format.long_name,
                    'codec':stream.codec_context.codec.long_name,'rate':rate,'channels':channels,'bytes':size,
                    'duration_basis':basis}


if __name__=='__main__':
    try:
        print(json.dumps({'ok':True,'result':inspect_audio(json.loads(sys.stdin.readline())['source'])}))
    except Exception as exc:
        print(json.dumps({'ok':False,'error':str(exc)}))
