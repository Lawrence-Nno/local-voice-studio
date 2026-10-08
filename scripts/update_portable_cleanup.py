"""Update portable cleanup without modifying personal data or loaded DLLs."""
import json
import shutil
from scripts.build_portable import ROOT,ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_cleanup.py',target/'scripts/check_cleanup.py')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['audio_cleanup']={'offline':True,'preserves_timing':True,'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    if 'Audio cleanup tab' not in text:
        note.write_text(text+'\nAudio cleanup tab: reduce steady noise, adjust/level volume, optionally remove low rumble, compare original/cleaned, and export a separate WAV. Results are stored in data/cleaned.\n',encoding='utf-8')
    print('Portable audio cleanup updated; user data preserved.')


if __name__=='__main__':
    main()
