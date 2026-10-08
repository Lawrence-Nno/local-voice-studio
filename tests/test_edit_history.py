import unittest
from app.edit_history import EditHistory


class HistoryTests(unittest.TestCase):
    def test_branch_noop_and_source_reset(self):
        history=EditHistory()
        history.reset(('0','4'))
        history.record(('1','3'))
        history.record(('1','3'))
        self.assertEqual(len(history.past),1)
        self.assertEqual(history.undo(),('0','4'))
        self.assertEqual(history.redo(),('1','3'))
        history.undo()
        history.record(('2','4'))
        self.assertFalse(history.future)
        history.reset(('0','10'))
        self.assertFalse(history.past)
        self.assertFalse(history.future)

    def test_bounded_and_invalid_text_recovery(self):
        history=EditHistory(limit=2)
        history.reset(('0',))
        for state in ('1','2','invalid'): history.record((state,))
        self.assertEqual(history.undo(),('2',))
        self.assertEqual(history.undo(),('1',))
        self.assertEqual(history.undo(),('1',))
        self.assertEqual(history.redo(),('2',))
