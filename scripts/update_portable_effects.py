"""Update portable voice effects without changing recordings or runtime DLLs."""
import json
import shutil
from scripts.build_portable import ROOT,ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_effects.py',target/'scripts/check_effects.py')
    shutil.copy2(ROOT/'scripts/check_effects_presets.py',target/'scripts/check_effects_presets.py')
    shutil.copy2(ROOT/'README.md',target/'README.md')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['voice_effects']={'offline':True,'effects':['speed','pitch','reverb','radio'],'max_input_minutes':10,'verified':'2026-10-08'}
    value['effects_presets']={'local':True,'custom_save_load_update_delete':True,'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    text=text.replace('Five-minute input limit','Ten-minute input limit')
    note.write_text(text,encoding='utf-8')
    if 'Voice effects tab' not in text:
        note.write_text(text+'\nVoice effects tab: choose audio, adjust independent speed/pitch, reverb and radio mode, apply, compare original/processed, and export a new WAV. Ten-minute input limit; results saved in data/effects.\n',encoding='utf-8')
    text=note.read_text(encoding='utf-8')
    if 'Effects presets:' not in text:
        note.write_text(text+'\nEffects presets: open Effects presets in Voice effects to load starter settings or save/load/update/delete your own presets. Custom settings live in data/effects-presets.json and move with this folder.\n',encoding='utf-8')
    print('Portable voice effects updated; user data preserved.')


if __name__=='__main__':
    main()
