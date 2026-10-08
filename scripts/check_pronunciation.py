"""Native dictionary dialog check; uses an isolated dictionary, no model load."""
import tkinter as tk
from unittest.mock import patch
from app.storage import DATA, configure_runtime


def main():
    configure_runtime()
    from app.main import configure_dpi
    from app.ui import VoiceApp
    from app import pronunciation
    configure_dpi()
    root = tk.Tk()
    app = VoiceApp(root)
    path = DATA/'verification/pronunciation-check.json'
    path.unlink(missing_ok=True)
    real_load, real_save = pronunciation.load, pronunciation.save
    try:
        with patch.object(pronunciation, 'load', side_effect=lambda: real_load(path)), patch.object(pronunciation, 'save', side_effect=lambda value: real_save(value, path)):
            app.text.insert('1.0', 'SQL is ready.')
            app.open_pronunciation()
            dialog = app.pronunciation_dialog
            dialog.word.set('SQL')
            dialog.spoken.set('sequel')
            dialog.add()
            dialog.preview()
            root.update()
            assert dialog.preview_text.get('1.0', 'end-1c') == 'sequel is ready.'
            assert dialog.preview_text.winfo_ismapped()
            assert dialog.preview_text.winfo_rooty()+dialog.preview_text.winfo_height() < dialog.winfo_rooty()+dialog.winfo_height()
            dialog.persist()
            app.open_pronunciation()
            root.update()
            assert len(app.pronunciation_dialog.rows.get_children()) == 1
            assert app.text.get('1.0', 'end-1c') == 'SQL is ready.'
        print('Pronunciation dialog preview, save/reload and layout passed.')
    finally:
        root.destroy()
        path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
