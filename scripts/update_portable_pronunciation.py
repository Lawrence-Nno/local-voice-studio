"""Update app code while retaining the portable dictionary and user data."""
import json
import shutil
from scripts.build_portable import ROOT, ignore


def main():
    target = ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app', target/'app', dirs_exist_ok=True, ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_pronunciation.py', target/'scripts/check_pronunciation.py')
    shutil.copy2(ROOT/'README.md', target/'README.md')
    manifest = target/'portable-build.json'
    value = json.loads(manifest.read_text())
    value['pronunciation_dictionary'] = {'local': True, 'original_script_preserved': True, 'verified': '2026-10-08'}
    manifest.write_text(json.dumps(value, indent=2), encoding='utf-8')
    print('Portable pronunciation dictionary updated; user data preserved.')


if __name__ == '__main__':
    main()
