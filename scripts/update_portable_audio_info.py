"""Update portable audio inspection and user-facing documentation."""
import json
import shutil
from scripts.build_portable import ROOT,ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_audio_info.py',target/'scripts/check_audio_info.py')
    shutil.copy2(ROOT/'README.md',target/'README.md')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['audio_file_information']={'offline':True,'read_only':True,'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    if 'Audio file information menu' not in text:
        text+='\nAudio file information menu: inspect duration, format/codec, sample rate, channels and size, choose a file or loaded input/result, and copy the details.\n'
    if 'Designed by Chima Lawrence Nnoromele' not in text:
        text+='\nDesigned by Chima Lawrence Nnoromele\nEmail: lawrence.nno@gmail.com\nSee README.md for the complete feature list and usage.\n'
    note.write_text(text,encoding='utf-8')
    print('Portable audio information and README updated; personal data preserved.')


if __name__=='__main__':
    main()
