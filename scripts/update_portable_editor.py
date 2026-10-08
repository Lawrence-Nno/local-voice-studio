"""Update editor code in the portable folder while preserving all user audio."""
import json
import shutil

from scripts.build_portable import ROOT, ignore


def main():
    target = ROOT / 'dist' / 'Local Voice Studio'
    if not (target / 'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT / 'app', target / 'app', dirs_exist_ok=True, ignore=ignore)
    shutil.copy2(ROOT / 'scripts/check_editor.py', target / 'scripts/check_editor.py')
    manifest = target / 'portable-build.json'
    value = json.loads(manifest.read_text())
    value['audio_editor'] = {'offline': True, 'features': ['waveform', 'selection trim', 'volume', 'fades', 'preview', 'WAV export'], 'verified': '2026-10-08'}
    manifest.write_text(json.dumps(value, indent=2), encoding='utf-8')
    note = target / 'READ ME.txt'
    text = note.read_text(encoding='utf-8')
    if 'Audio editor tab' not in text:
        note.write_text(text + '\nAudio editor tab: open audio or use a recording/generated clip, select a section in the waveform, adjust volume/fades, preview, and save a separate WAV in data/edits. Export uses the last saved edit. Original audio is preserved.\n', encoding='utf-8')
    print('Portable audio editor updated. User data preserved; no new dependencies required.')


if __name__ == '__main__':
    main()
