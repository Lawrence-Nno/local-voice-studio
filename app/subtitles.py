"""Readable subtitle cues and strict UTF-8 SubRip serialization."""
import math
import re
import textwrap


def timestamp(seconds):
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Subtitle times must be finite and nonnegative.")
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{sec:02d},{ms:03d}"


def make_cues(words):
    cues, group = [], []
    def flush():
        if not group:
            return
        text = " ".join(w["word"].strip() for w in group).strip()
        if text:
            start = max(cues[-1]["end"] if cues else 0, group[0]["start"])
            end = max(start + .001, group[-1]["end"])
            cues.append({"start": start, "end": end,
                         "text": "\n".join(textwrap.wrap(text, 42, break_long_words=False, break_on_hyphens=False))})
        group.clear()
    for word in words:
        if not word["word"].strip():
            continue
        if group and (len(" ".join(w["word"].strip() for w in group)) + len(word["word"]) + 1 > 84
                      or len(textwrap.wrap(" ".join(w["word"].strip() for w in group) + " " + word["word"].strip(), 42, break_long_words=False, break_on_hyphens=False)) > 2
                      or word["end"] - group[0]["start"] > 7
                      or word["start"] - group[-1]["end"] > .8):
            flush()
        group.append(word)
        if word["word"].strip().endswith((".", "!", "?")):
            flush()
    flush()
    return cues


def serialize(cues):
    previous = 0
    blocks = []
    for index, cue in enumerate(cues, 1):
        start, end = cue["start"], cue["end"]
        if start < previous or round(end * 1000) <= round(start * 1000):
            raise ValueError("Cues must be ordered, non-overlapping, and have positive durations.")
        text = cue["text"].strip()
        if not text or "\n\n" in text:
            raise ValueError("Each cue needs text without blank lines.")
        blocks.append(f"{index}\n{timestamp(start)} --> {timestamp(end)}\n{text}")
        previous = end
    if not blocks:
        raise ValueError("No speech cues were found. Try a clearer recording or a language selection.")
    return "\n\n".join(blocks) + "\n"


def parse_srt(value):
    cues = []
    pattern = r"(\d{2,}):(\d{2}):(\d{2}),(\d{3})"
    def seconds(parts):
        h, m, s, ms = map(int, parts)
        if m >= 60 or s >= 60:
            raise ValueError("Minutes and seconds must be below 60.")
        return h * 3600 + m * 60 + s + ms / 1000
    for index, block in enumerate(re.split(r"\n\s*\n", value.replace("\r\n", "\n").strip()), 1):
        lines = block.splitlines()
        if len(lines) < 3 or lines[0].strip() != str(index):
            raise ValueError(f"Cue {index}: keep sequential numbers, a timing line, and caption text.")
        match = re.fullmatch(pattern + r" --> " + pattern, lines[1].strip())
        if not match:
            raise ValueError(f"Cue {index}: use HH:MM:SS,mmm --> HH:MM:SS,mmm.")
        cues.append({"start": seconds(match.groups()[:4]), "end": seconds(match.groups()[4:]),
                     "text": "\n".join(lines[2:])})
    serialize(cues)
    return cues
