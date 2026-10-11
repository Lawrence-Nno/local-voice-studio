import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.effects_presets import EffectsPresets,BUILTINS


class PresetsTests(unittest.TestCase):
    def test_formant_option_and_legacy_presets(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'presets.json'
            store=EffectsPresets(path)
            store.save('Legacy',BUILTINS['Normal voice'])
            settings=dict(BUILTINS['Normal voice'],formant=False)
            store.save('Altered character',settings)
            loaded=EffectsPresets(path)
            self.assertEqual(loaded.custom['Altered character'],settings)
            self.assertNotIn('formant',loaded.custom['Legacy'])
    def test_save_reload_update_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'presets.json'
            store=EffectsPresets(path)
            settings=dict(speed=1.1,pitch=-2,reverb=.15,radio=True)
            store.save('My narration',settings)
            reloaded=EffectsPresets(path)
            self.assertEqual(reloaded.all()['My narration'],settings)
            reloaded.save('My narration',BUILTINS['Normal voice'],replace=True)
            self.assertEqual(EffectsPresets(path).custom['My narration'],BUILTINS['Normal voice'])
            reloaded.delete('My narration')
            self.assertEqual(EffectsPresets(path).custom,{})

    def test_invalid_or_duplicate_presets_preserve_saved_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'presets.json'
            store=EffectsPresets(path)
            store.save('Custom',BUILTINS['Normal voice'])
            original=path.read_bytes()
            for name,settings in (('custom',BUILTINS['Normal voice']),('Normal voice',BUILTINS['Normal voice']),('',BUILTINS['Normal voice']),('Invalid',dict(speed=float('nan'),pitch=0,reverb=0,radio=False))):
                with self.assertRaises(ValueError):
                    store.save(name,settings)
                self.assertEqual(path.read_bytes(),original)
            with patch('app.effects_presets.atomic_json',side_effect=OSError('Disk error')):
                with self.assertRaises(OSError):
                    store.delete('Custom')
            self.assertIn('Custom',store.custom)

    def test_corrupt_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'presets.json'
            path.write_text('{corrupt')
            with self.assertRaises(ValueError):
                EffectsPresets(path)
            self.assertEqual(path.read_text(),'{corrupt')
