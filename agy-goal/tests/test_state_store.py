import unittest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.core.state import StateStore, SessionState

class TestStateStore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir)
        self.store = StateStore(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_load_default_when_no_file(self):
        state = self.store.load()
        self.assertFalse(state.active)
        self.assertEqual(state.round, 0)

    def test_save_and_load_roundtrip(self):
        state = SessionState(
            active=True,
            mode="remote",
            target="test-server",
            branch="feat/test",
            round=1,
            conversation_id="conv-123"
        )
        self.store.save(state)
        loaded = self.store.load()
        self.assertTrue(loaded.active)
        self.assertEqual(loaded.mode, "remote")
        self.assertEqual(loaded.target, "test-server")
        self.assertEqual(loaded.conversation_id, "conv-123")
        self.assertEqual(loaded.round, 1)

    def test_clear_state(self):
        state = SessionState(active=True, round=2)
        self.store.save(state)
        self.store.clear()
        reloaded = self.store.load()
        self.assertFalse(reloaded.active)
