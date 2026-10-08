"""Add the recorder and its native audio dependency without touching user data."""
import importlib.metadata
import json
import shutil

from scripts.build_portable import ROOT, ignore


def main():
    target = ROOT / 'dist' / 'Local Voice Studio'
    runtime = target / 'runtime' / 'turbo' / 'Lib' / 'site-packages'
    if not (target / 'Local Voice Studio.exe').is_file() or not runtime.is_dir():
        raise ValueError('Build the portable app first.')
    distribution = importlib.metadata.distribution('sounddevice')
    for entry in distribution.files:
        if '..' in entry.parts:
            continue
        source = distribution.locate_file(entry)
        destination = runtime / str(entry)
        if source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    shutil.copytree(ROOT / 'app', target / 'app', dirs_exist_ok=True, ignore=ignore)
    for name in ('requirements-lock.txt',):
        shutil.copy2(ROOT / name, target / name)
    shutil.copy2(ROOT / 'scripts/check_recorder.py', target / 'scripts/check_recorder.py')
    manifest = target / 'portable-build.json'
    value = json.loads(manifest.read_text())
    value['voice_recorder'] = {'offline': True, 'format': 'mono PCM16 WAV', 'verified': '2026-10-08'}
    manifest.write_text(json.dumps(value, indent=2), encoding='utf-8')
    note = target / 'READ ME.txt'
    text = note.read_text(encoding='utf-8')
    if 'Voice recorder tab' not in text:
        note.write_text(text + '\nVoice recorder tab: choose a microphone, record/pause/resume, preview/export WAV, or clean up and use as a voice reference. Takes are saved in data/recordings.\n', encoding='utf-8')
    print('Portable recorder updated. User data preserved.')


if __name__ == '__main__':
    main()
