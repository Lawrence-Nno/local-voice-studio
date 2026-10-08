"""Update recorder countdown without rewriting native audio libraries."""
import json
import shutil
from scripts.build_portable import ROOT,ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    for name in ('check_countdown.py','check_recorder.py'):
        shutil.copy2(ROOT/'scripts'/name,target/'scripts'/name)
    shutil.copy2(ROOT/'README.md',target/'README.md')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['recording_countdown']={'seconds':3,'cancellable':True,'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    if 'Recording countdown:' not in text:
        note.write_text(text+'\nRecording countdown: Start recording shows 3, 2, 1 before microphone capture. Cancel countdown stops preparation without saving a new take.\n',encoding='utf-8')
    print('Portable recording countdown updated; user data preserved.')


if __name__=='__main__':
    main()
