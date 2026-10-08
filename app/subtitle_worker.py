"""One-shot offline transcription/alignment worker in the isolated environment."""
import contextlib
import json
import os
import sys
from pathlib import Path

from .storage import ROOT, configure_runtime


def main():
    configure_runtime()
    output = sys.stdout
    def send(**message):
        output.write(json.dumps(message, ensure_ascii=True) + "\n")
        output.flush()
    request = json.loads(sys.stdin.readline())
    with contextlib.redirect_stdout(sys.stderr):
        try:
            import torch
            # CTranslate2 loads these CUDA DLLs by name on Windows.
            libraries = Path(torch.__file__).parent / "lib"
            dll_handle = os.add_dll_directory(str(libraries))
            os.environ["PATH"] = str(libraries) + os.pathsep + os.environ.get("PATH", "")
            from faster_whisper import WhisperModel
            from faster_whisper.audio import decode_audio, pad_or_trim
            from faster_whisper.tokenizer import Tokenizer
            from faster_whisper.transcribe import merge_punctuations
            send(progress="Loading subtitle model")
            device = "cpu" if request["device"] == "CPU" or not torch.cuda.is_available() else "cuda"
            if request["device"] == "NVIDIA GPU" and device != "cuda":
                raise ValueError("CUDA is unavailable. Select CPU explicitly.")
            model = WhisperModel(str(ROOT / "models" / "whisper-small"), device=device,
                compute_type="int8_float16" if device == "cuda" else "int8", local_files_only=True)
            words = []
            if request["mode"] == "transcribe":
                segments, info = model.transcribe(request["audio"], language=request.get("language"),
                                                  word_timestamps=True, vad_filter=True, beam_size=5)
                for segment in segments:
                    send(progress=f"Transcribing: {segment.end:.1f} / {info.duration:.1f} seconds")
                    for word in segment.words or []:
                        words.append({"word": word.word, "start": word.start, "end": word.end})
                language = info.language
            else:
                tokenizer = Tokenizer(model.hf_tokenizer, model.model.is_multilingual, task="transcribe", language="en")
                offset = 0
                for index, section in enumerate(request["sections"], 1):
                    send(progress=f"Aligning saved script: section {index} of {len(request['sections'])}")
                    audio = decode_audio(section["path"], sampling_rate=16000)
                    duration = len(audio) / 16000
                    if duration > 30:
                        raise ValueError("A generated section exceeds the 30-second alignment window. Use audio transcription or regenerate with shorter sections.")
                    features = pad_or_trim(model.feature_extractor(audio))
                    encoded = model.encode(features)
                    alignment = model.find_alignment(tokenizer, [tokenizer.encode(section["text"])], encoded,
                                                     num_frames=len(audio) // 160)[0]
                    merge_punctuations(alignment, "\"'([", "\"'.,!?;:)]}")
                    section_words = []
                    for word in alignment:
                        raw = word["word"]
                        if not raw.strip():
                            continue
                        if section_words and not raw[:1].isspace():
                            section_words[-1]["word"] += raw
                            section_words[-1]["end"] = offset + word["end"]
                        else:
                            section_words.append({"word": raw, "start": offset + word["start"],
                                                  "end": offset + word["end"]})
                    actual = " ".join(w["word"].strip() for w in section_words)
                    expected = " ".join(section["text"].split())
                    if actual != expected:
                        raise ValueError("The aligner could not preserve this script exactly. Use transcription or simplify the script.")
                    words.extend(section_words)
                    offset += section["duration"] + .18
                language = "en"
            from .subtitles import make_cues, serialize
            cues = make_cues(words)
            send(result={"srt": serialize(cues), "cues": cues, "language": language,
                         "device": device, "mode": request["mode"]})
        except Exception as exc:
            import traceback
            traceback.print_exc()
            send(error=str(exc))


if __name__ == "__main__":
    main()
