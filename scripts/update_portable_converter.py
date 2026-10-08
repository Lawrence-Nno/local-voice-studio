"""Update converter code without changing portable user data or runtime DLLs."""
import json
import shutil

from scripts.build_portable import ROOT, ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file() or not (target/'runtime/qwen/Lib/site-packages/av').is_dir():
        raise ValueError('Build the portable app with its audio runtime first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_converter.py',target/'scripts/check_converter.py')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['format_converter']={'offline':True,'formats':['WAV','MP3','FLAC','M4A/AAC','OGG/Opus'],'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    if 'Format converter tab' not in text:
        note.write_text(text+'\nFormat converter tab: open audio or select a recording/generated/saved edit, choose WAV/MP3/FLAC/M4A/OGG output, convert locally, and export a separate file. Results are saved in data/converted.\n',encoding='utf-8')
    print('Portable format converter updated. Data and runtime dependencies preserved.')


if __name__=='__main__':
    main()
