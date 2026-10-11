import threading
import unittest
from unittest.mock import patch

from app.engine import SpeechEngine
from app.shutdown import start_cleanup


class ShutdownTests(unittest.TestCase):
    def test_cleanup_returns_while_work_is_blocked(self):
        entered, release = threading.Event(), threading.Event()
        completed = []

        def blocked():
            entered.set()
            release.wait(5)

        worker = start_cleanup(blocked, lambda: completed.append(True))
        try:
            self.assertTrue(entered.wait(2))
            self.assertTrue(worker.is_alive())
            self.assertFalse(worker.daemon)
            self.assertEqual(completed, [])
        finally:
            release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(completed, [True])

    def test_failure_does_not_skip_remaining_resources(self):
        completed = []

        def failed():
            raise RuntimeError('Test cleanup failure')

        with patch('app.shutdown.logging.exception') as report:
            worker = start_cleanup(failed, lambda: completed.append(True))
            worker.join(5)
            report.assert_called_once()
        self.assertEqual(completed, [True])

    def test_unused_engine_does_not_import_torch(self):
        with patch('builtins.__import__', side_effect=AssertionError('Unexpected import')):
            SpeechEngine().unload()
