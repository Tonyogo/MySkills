import unittest
import tempfile
import shutil
import os
import stat
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.executors.remote import RemoteExecutor

class TestRemoteExecutor(unittest.TestCase):
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

    def _create_mock_gt(self, output: str, exit_code: int = 0):
        gt_bin = self.bin_dir / "gt"
        with open(gt_bin, "w") as f:
            f.write(f"#!/usr/bin/env bash\ncat << 'EOF'\n{output}\nEOF\nexit {exit_code}\n")
        gt_bin.chmod(gt_bin.stat().st_mode | stat.S_IEXEC)

    def test_preflight_blocks_main_branch(self):
        executor = RemoteExecutor(self.workspace, target="server-1", branch="main")
        with self.assertRaises(RuntimeError) as ctx:
            executor.preflight_check()
        self.assertIn("Refusing to run on 'main' or 'master'", str(ctx.exception))

    def test_preflight_missing_gt(self):
        executor = RemoteExecutor(self.workspace, target="server-1", branch="feat/foo")
        os.environ["PATH"] = ""
        with self.assertRaises(RuntimeError) as ctx:
            executor.preflight_check()
        self.assertIn("'gt' CLI tool not found", str(ctx.exception))

    def test_remote_execute_success(self):
        mock_payload = '{"conversation_id":"r1","status":"SUCCESS","duration_seconds":3.0,"response":"Remote Done\\n<!-- GOAL_COMPLETE -->"}'
        self._create_mock_gt(mock_payload, exit_code=0)
        executor = RemoteExecutor(self.workspace, target="server-1", branch="feat/foo")
        executor.preflight_check()
        res = executor.execute("Implement plan", is_continue=False)
        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(res.goal_complete)
        self.assertEqual(res.conversation_id, "r1")
