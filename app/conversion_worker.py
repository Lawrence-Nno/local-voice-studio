"""Streaming offline audio conversion in the existing PyAV runtime."""
import json
import sys
from fractions import Fraction
from pathlib import Path

FORMATS = {
    'WAV': ('wav', 'pcm_s16le', 's16'),
    'MP3': ('mp3', 'libmp3lame', 'fltp'),
    'FLAC': ('flac', 'flac', 's16'),
    'M4A (AAC)': ('mp4', 'aac', 'fltp'),
    'OGG (Opus)': ('ogg', 'libopus', 'flt'),
}


def convert(source, destination, format_name, rate=44100, channels='Keep source', bitrate=192000):
    import av
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Choose a new filename to preserve your source audio.')
    container_name, codec, sample_format = FORMATS[format_name]
    if rate not in (24000, 44100, 48000) or bitrate not in (96000, 128000, 192000, 256000, 320000):
        raise ValueError('Unsupported sample rate or bitrate.')
    if channels not in ('Keep source', 'Mono', 'Stereo'):
        raise ValueError('Unsupported channel setting.')
    if format_name == 'OGG (Opus)':
        rate = 48000
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with av.open(str(source)) as incoming:
            if not incoming.streams.audio:
                raise ValueError('No audio stream found in this file.')
            input_stream = incoming.streams.audio[0]
            count = len(input_stream.codec_context.layout.channels)
            if channels == 'Keep source' and count not in (1, 2):
                raise ValueError('For multichannel audio, choose Mono or Stereo.')
            layout = 'mono' if channels == 'Mono' or (channels == 'Keep source' and count == 1) else 'stereo'
            samples = 0
            with av.open(str(destination), 'w', format=container_name) as outgoing:
                stream = outgoing.add_stream(codec, rate=rate)
                stream.layout = layout
                stream.codec_context.format = sample_format
                if format_name not in ('WAV', 'FLAC'):
                    stream.bit_rate = bitrate
                resampler = av.AudioResampler(format=sample_format, layout=layout, rate=rate)
                def encode(frame):
                    nonlocal samples
                    frame.pts = samples
                    frame.time_base = Fraction(1, rate)
                    samples += frame.samples
                    for packet in stream.encode(frame):
                        outgoing.mux(packet)
                for frame in incoming.decode(input_stream):
                    # Continuous output timestamps, independent of source/container offsets.
                    frame.pts = None
                    for converted in resampler.resample(frame):
                        encode(converted)
                for converted in resampler.resample(None):
                    encode(converted)
                for packet in stream.encode(None):
                    outgoing.mux(packet)
            if not samples:
                raise ValueError('No decodable audio was found.')
        return {'rate': rate, 'channels': 1 if layout == 'mono' else 2,
                'duration': samples / rate, 'format': format_name, 'bytes': destination.stat().st_size}
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main():
    try:
        request = json.loads(sys.stdin.readline())
        result = convert(**request)
        print(json.dumps({'ok': True, 'result': result}))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))


if __name__ == '__main__':
    main()
