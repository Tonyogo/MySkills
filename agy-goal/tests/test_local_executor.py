import unittest
import tempfile
import shutil
import os
import stat
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.executors.local import LocalExecutor

class TestLocalExecutor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir)
        self.bin_dir = self.workspace / "bin"
        self.bin_dir.mkdir()
        self.old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.bin_dir}:{self.old_path}"

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        shutil.rmtree(self.test_dir)

    def _create_mock_agy(self, output: str, exit_code: int = 0):
        agy_bin = self.bin_dir / "agy"
        with open(agy_bin, "w") as f:
            f.write(f"#!/usr/bin/env bash\ncat << 'EOF'\n{output}\nEOF\nexit {exit_code}\n")
        agy_bin.chmod(agy_bin.stat().st_mode | stat.S_IEXEC)

    def test_preflight_missing_agy(self):
        executor = LocalExecutor(self.workspace)
        # Temporarily clear PATH
        os.environ["PATH"] = ""
        with self.assertRaises(RuntimeError) as ctx:
            executor.preflight_check()
        self.assertIn("not found in PATH", str(ctx.exception))

    def test_execute_success(self):
        mock_resp = '{"conversation_id":"c1","status":"SUCCESS","duration_seconds":1.2,"response":"Done\\n<!-- GOAL_COMPLETE -->"}'
        self._create_mock_agy(mock_resp, exit_code=0)
        executor = LocalExecutor(self.workspace)
        executor.preflight_check()
        res = executor.execute("Implement plan", is_continue=False)
        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(res.goal_complete)
        self.assertEqual(res.conversation_id, "c1")
