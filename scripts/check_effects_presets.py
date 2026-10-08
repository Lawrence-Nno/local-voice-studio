"""Native preset save/load/update/delete using an isolated verification file."""
import tkinter as tk
import uuid
from unittest.mock import patch

from app.storage import DATA,configure_runtime
from app.effects_presets import EffectsPresets,BUILTINS


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from PIL import ImageGrab
    configure_dpi()
    root=tk.Tk()
    app=VoiceApp(root)
    panel=app.effects_panel
    app.notebook.select(8)
    path=DATA/'verification/presets'/(uuid.uuid4().hex+'.json')
    panel.preset_store=EffectsPresets(path)
    panel.preset_error=None
    panel.open_presets()
    dialog=panel.preset_dialog
    def select(name):
        dialog.list.selection_clear(0,'end')
        dialog.list.selection_set(dialog.names.index(name))
        dialog.update_controls()
    panel.speed.set(1.12)
    panel.pitch.set(-2)
    panel.reverb.set(.2)
    panel.radio.set(True)
    with patch('app.effects_presets_ui.simpledialog.askstring',return_value='My narration'):
        dialog.save()
    assert EffectsPresets(path).custom['My narration']['speed']==1.12
    panel.reset()
    select('My narration')
    dialog.load()
    assert panel.speed.get()==1.12 and panel.pitch.get()==-2 and panel.reverb.get()==.2 and panel.radio.get()
    assert panel.output is None,'Loading should not create processed audio'
    panel.pitch.set(3)
    dialog.update()
    assert EffectsPresets(path).custom['My narration']['pitch']==3
    select('Subtle reverb')
    dialog.load()
    assert panel.reverb.get()==.15 and panel.speed.get()==1 and not panel.radio.get()
    assert str(dialog.buttons[2]['state'])=='disabled' and str(dialog.buttons[3]['state'])=='disabled'
    select('My narration')
    dialog.delete()
    assert EffectsPresets(path).custom=={} and 'My narration' not in dialog.names
    app.conversion_running=True
    dialog.update_controls()
    assert all(str(button['state'])=='disabled' for button in dialog.buttons)
    app.conversion_running=False
    dialog.update_controls()
    root.update()
    dialog.attributes('-topmost',True)
    dialog.lift()
    root.update()
    import time
    time.sleep(.2)
    for button in dialog.buttons:
        assert button.winfo_ismapped()
        assert button.winfo_rootx()+button.winfo_width()<=dialog.winfo_rootx()+dialog.winfo_width()
        assert button.winfo_rooty()+button.winfo_height()<=dialog.winfo_rooty()+dialog.winfo_height()
    ImageGrab.grab(bbox=(dialog.winfo_rootx(),dialog.winfo_rooty(),dialog.winfo_rootx()+dialog.winfo_width(),dialog.winfo_rooty()+dialog.winfo_height())).save(DATA/'effects-presets-ui-preview.png')
    dialog.attributes('-topmost',False)
    dialog.destroy()
    app.close()
    print('Native preset save/reload/load/update/delete, starter protection, unchanged processed result, busy lock and layout passed.')


if __name__=='__main__':
    main()
