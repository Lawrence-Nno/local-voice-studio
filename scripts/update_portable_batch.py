"""Update batch workflows without touching portable user data or native DLLs."""
import json
import shutil
from scripts.build_portable import ROOT,ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_batch.py',target/'scripts/check_batch.py')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['batch_processing']={'offline':True,'operations':['cleanup','conversion','subtitles'],'sequential':True,'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    if 'Batch processing tab' not in text:
        note.write_text(text+'\nBatch processing tab: queue files, choose Cleanup/Convert/Subtitles, adjust settings in that operation tab, return and start. Each run has a new folder and batch-report.json; cancellation keeps completed files.\n',encoding='utf-8')
    print('Portable batch processing updated; user data preserved.')


if __name__=='__main__':
    main()
