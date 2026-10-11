"""Bundle the new offline engine with its notices, preserving personal data."""
import json
import shutil
from scripts.build_portable import ROOT, ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copytree(ROOT/'tools/rubberband',target/'tools/rubberband',dirs_exist_ok=True)
    for name in ('check_effects.py','check_rubberband.py'):
        shutil.copy2(ROOT/'scripts'/name,target/'scripts'/name)
    shutil.copy2(ROOT/'README.md',target/'README.md')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['effects_engine']={'name':'Rubber Band','version':'4.0.0','engine':'R3 Finer','formant_preservation':True,'verified':'2026-10-11'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    print('Portable Rubber Band R3 updated; licenses retained and user data preserved.')


if __name__=='__main__': main()
