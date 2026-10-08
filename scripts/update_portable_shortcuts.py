"""Update direct audio handoffs while preserving portable user files."""
import json
import shutil
from scripts.build_portable import ROOT,ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_audio_shortcuts.py',target/'scripts/check_audio_shortcuts.py')
    shutil.copy2(ROOT/'README.md',target/'README.md')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['audio_shortcuts']={'sources':['saved edit','cleaned result'],'destinations':['conversion','subtitles','effects'],'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    if 'Direct audio shortcuts:' not in text:
        note.write_text(text+'\nDirect audio shortcuts: Send saved edit to / Send cleaned audio to selects the completed result in conversion, subtitles or effects and opens that tab. Start processing there when ready.\n',encoding='utf-8')
    print('Portable audio shortcuts updated; user data preserved.')


if __name__=='__main__':
    main()
