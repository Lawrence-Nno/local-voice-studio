"""Local, literal pronunciation hints; never changes the user's script."""
import re
from pathlib import Path
from .storage import DATA, atomic_json, read_json


def validate(value):
    if not isinstance(value, dict) or not isinstance(value.get('enabled'), bool) or not isinstance(value.get('entries'), dict):
        raise ValueError('Invalid pronunciation dictionary. Expected enabled and entries fields.')
    entries = {}
    seen = set()
    for word, spoken in value['entries'].items():
        if not isinstance(word, str) or not isinstance(spoken, str):
            raise ValueError('Words and pronunciations must be text.')
        word, spoken = word.strip(), spoken.strip()
        if not word or not spoken or max(len(word), len(spoken)) > 200 or any(ord(c) < 32 for c in word + spoken):
            raise ValueError('Use nonempty words or phrases of up to 200 characters, without line breaks.')
        if word.casefold() in seen:
            raise ValueError('Each word or phrase can appear only once (ignoring capitalization).')
        seen.add(word.casefold())
        entries[word] = spoken
    if len(entries) > 500:
        raise ValueError('Use no more than 500 pronunciation entries.')
    return {'enabled': value['enabled'], 'entries': entries}


def load(path: Path = DATA / 'pronunciation.json'):
    return validate(read_json(path, {'enabled': True, 'entries': {}}))


def save(value, path: Path = DATA / 'pronunciation.json'):
    atomic_json(path, validate(value))


def pattern(entries):
    return r'(?<!\w)(?:' + '|'.join(re.escape(key) for key in sorted(entries, key=len, reverse=True)) + r')(?!\w)'


def apply(text, value):
    value = validate(value)
    if not value['enabled'] or not value['entries']:
        return text
    entries = value['entries']
    lookup = {key.casefold(): spoken for key, spoken in entries.items()}
    # Longest phrases win; a single pass prevents replacements replacing each other.
    return re.sub(pattern(entries), lambda match: lookup[match.group().casefold()], text, flags=re.IGNORECASE)
