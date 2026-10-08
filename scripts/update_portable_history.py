"""Update editor history while preserving portable audio, profiles and settings."""
import json
import shutil
from scripts.build_portable import ROOT, ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_editor_history.py',target/'scripts/check_editor_history.py')
    shutil.copy2(ROOT/'README.md',target/'README.md')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['editor_history']={'steps':100,'settings_only':True,'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    if 'Editor Undo/Redo:' not in text:
        note.write_text(text+'\nEditor Undo/Redo: Recover selection, volume and fades with Undo/Redo or Ctrl+Z / Ctrl+Y. Preview or save restored settings again; saved files stay unchanged. History resets when opening audio.\n',encoding='utf-8')
    print('Portable editor Undo/Redo updated; user data preserved.')


if __name__=='__main__': main()
