import tempfile
import unittest
from pathlib import Path
from threading import Event
import numpy as np
from app import pronunciation as p
from app.generation import run_job
from app.storage import read_json


class PronunciationTests(unittest.TestCase):
    def test_literal_longest_whole_word_single_pass(self):
        value = {'enabled': True, 'entries': {'SQL': 'sequel', 'SQL server': 'sequel server', 'sequel': 'other', 'C++': 'see plus plus'}}
        self.assertEqual(p.apply('SQL server, sql! SQLish C++ sequel.', value), 'sequel server, sequel! SQLish see plus plus other.')
        value['enabled'] = False
        self.assertEqual(p.apply('SQL', value), 'SQL')

    def test_persistence_and_invalid_preserve(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'dictionary.json'
            value = {'enabled': True, 'entries': {'Chima': 'Chee mah'}}
            p.save(value, path)
            self.assertEqual(p.load(path), value)
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                p.save({'enabled': True, 'entries': {'SQL': 'one', 'sql': 'two'}}, path)
            self.assertEqual(path.read_bytes(), original)

    def test_generation_keeps_original_sections_and_snapshot(self):
        class Engine:
            device = 'CPU'
            model_id = 'Qwen test'
            def load(self, *args): pass
            def prepare(self, *args): pass
            def generate(self, text, **kwargs):
                self.spoken.append(text)
                return np.zeros(800), 8000
        engine = Engine()
        engine.spoken = []
        script = 'a ' * 116 + 'SQL server is ready.'
        dictionary = {'enabled': True, 'entries': {'SQL server': 'sequel server'}}
        with tempfile.TemporaryDirectory() as folder:
            result = run_job(engine, script, None, None, 'CPU', Event(), lambda *args: None, data=Path(folder), options={'pronunciation': dictionary})
            metadata = read_json(next((Path(folder)/'jobs').glob('*/job.json')))
            self.assertEqual(metadata['text'], script)
            self.assertIn('SQL server', ' '.join(metadata['section_texts']))
            self.assertIn('sequel server', ' '.join(engine.spoken))
            self.assertEqual(metadata['spoken_section_texts'], engine.spoken)
            self.assertEqual(metadata['pronunciation_dictionary'], dictionary)
            self.assertTrue(result.is_file())
