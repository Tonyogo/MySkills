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

    def test_start_plan_prompt_uses_relative_path(self):
        plan_dir = self.workspace / "docs"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "my_plan.md"
        plan_file.write_text("# Test Plan")

        captured_prompts = []
        def mock_run(executor, state, prompt, is_continue):
            captured_prompts.append(prompt)
            return 0
        self.api._run_and_handle = mock_run

        # Passing absolute path should still format relative to workspace root
        self.api.start_plan(str(plan_file))
        self.assertEqual(len(captured_prompts), 1)
        self.assertEqual(captured_prompts[0], "/goal Implement Plan @docs/my_plan.md")

