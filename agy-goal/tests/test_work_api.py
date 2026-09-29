import unittest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.core.work_api import WorkAPI

class TestWorkAPI(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir)
        self.api = WorkAPI(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_status_when_no_session(self):
        status = self.api.get_status()
        self.assertFalse(status["active"])

    def test_reset_clears_session(self):
        state = self.api.state_store.load()
        state.active = True
        self.api.state_store.save(state)
        self.api.reset()
        self.assertFalse(self.api.get_status()["active"])
