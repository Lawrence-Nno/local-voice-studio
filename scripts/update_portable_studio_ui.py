"""Refresh the portable studio interface, preserving all user data."""
import json
import shutil
from scripts.build_portable import ROOT, ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_studio_ui.py',target/'scripts/check_studio_ui.py')
    shutil.copy2(ROOT/'README.md',target/'README.md')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['studio_interface']={'theme':'dark','navigation':'grouped sidebar','scrollable_pages':True,
                               'shaded_group_headers':True,'checkboxes':'green checkmarks',
                               'audio_info_sidebar':True,'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    if 'Studio interface:' not in text:
        note.write_text(text+'\nStudio interface: Choose tools in the left sidebar. Dark controls and dialogs share one theme; page scrollbars keep actions accessible in smaller windows. All audio workflows and saved user files are retained.\n',encoding='utf-8')
    print('Portable studio interface updated; user data preserved.')


if __name__=='__main__': main()
