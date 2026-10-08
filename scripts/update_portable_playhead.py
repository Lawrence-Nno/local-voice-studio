"""Update waveform playback without touching portable user data."""
import json
import shutil
from scripts.build_portable import ROOT, ignore


def main():
    target=ROOT/'dist/Local Voice Studio'
    if not (target/'Local Voice Studio.exe').is_file():
        raise ValueError('Build the portable app first.')
    shutil.copytree(ROOT/'app',target/'app',dirs_exist_ok=True,ignore=ignore)
    shutil.copy2(ROOT/'scripts/check_playhead.py',target/'scripts/check_playhead.py')
    shutil.copy2(ROOT/'README.md',target/'README.md')
    manifest=target/'portable-build.json'
    value=json.loads(manifest.read_text())
    value['waveform_playback']={'device_clock':True,'seek_pause_cut_markers':True,'verified':'2026-10-08'}
    manifest.write_text(json.dumps(value,indent=2),encoding='utf-8')
    note=target/'READ ME.txt'
    text=note.read_text(encoding='utf-8')
    if 'Waveform playback:' not in text:
        note.write_text(text+'\nWaveform playback: Audio editor has Play source, Pause/Resume and Stop. Shift-click seeks; Set start/end here copies the playhead time. Selection preview includes finishing settings.\n',encoding='utf-8')
    print('Portable waveform playback updated; user data preserved.')


if __name__=='__main__': main()
