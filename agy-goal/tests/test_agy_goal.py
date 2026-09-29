# agy-goal/tests/test_agy_goal.py
import unittest
import importlib.util
import os
import shutil
import stat
import tempfile
from pathlib import Path

# Dynamically import agy-goal.py
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "agy-goal.py"
spec = importlib.util.spec_from_file_location("agy_goal", SCRIPT_PATH)
agy_goal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agy_goal)

parse_agy_output = agy_goal.parse_agy_output
parse_timeout_seconds = agy_goal.parse_timeout_seconds
StateStore = agy_goal.StateStore
SessionState = agy_goal.SessionState
CircuitBreaker = agy_goal.CircuitBreaker
CircuitBreakerError = agy_goal.CircuitBreakerError
LocalExecutor = agy_goal.LocalExecutor
RemoteExecutor = agy_goal.RemoteExecutor
WorkAPI = agy_goal.WorkAPI


class TestParserAndTimeout(unittest.TestCase):
    def test_parse_timeout_seconds(self):
        self.assertEqual(parse_timeout_seconds("20m"), 1200)
        self.assertEqual(parse_timeout_seconds("30s"), 30)
        self.assertEqual(parse_timeout_seconds("1h"), 3600)
        self.assertEqual(parse_timeout_seconds("500"), 500)
        self.assertIsNone(parse_timeout_seconds("invalid"))

    def test_parse_valid_json_goal_complete(self):
        sample = '{"conversation_id": "c1", "status": "SUCCESS", "duration_seconds": 10.0, "response": "OK\\n<!-- GOAL_COMPLETE -->"}'
        res = parse_agy_output(sample, exit_code=0)
        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(res.goal_complete)

    def test_parse_empty_and_fallback(self):
        res = parse_agy_output("", exit_code=1)
        self.assertEqual(res.status, "ERROR")
        self.assertFalse(res.goal_complete)


class TestStateStore(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.store = StateStore(Path(self.td))

    def tearDown(self):
        shutil.rmtree(self.td)

    def test_save_and_load(self):
        st = SessionState(active=True, mode="remote", target="test", round=1)
        self.store.save(st)
        loaded = self.store.load()
        self.assertTrue(loaded.active)
        self.assertEqual(loaded.mode, "remote")
        self.assertEqual(loaded.round, 1)


class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.cb = CircuitBreaker(max_rounds=3)

    def test_max_rounds(self):
        st = SessionState(active=True, round=3, max_rounds=3)
        with self.assertRaises(CircuitBreakerError):
            self.cb.check_pre_turn(st)

    def test_stagnation_detection(self):
        st = SessionState(active=True, round=1, max_rounds=3)
        self.cb.record_turn(st, "err1", "err1")
        st.round = 2
        with self.assertRaises(CircuitBreakerError):
            self.cb.record_turn(st, "err1", "err1")


class TestExecutors(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.ws = Path(self.td)
        self.bin_dir = self.ws / "bin"
        self.bin_dir.mkdir()
        self.old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.bin_dir}:{self.old_path}"

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        shutil.rmtree(self.td)

    def _mock_bin(self, name: str, output: str, exit_code: int = 0):
        b = self.bin_dir / name
        b.write_text(f"#!/usr/bin/env bash\ncat << 'EOF'\n{output}\nEOF\nexit {exit_code}\n")
        b.chmod(b.stat().st_mode | stat.S_IEXEC)

    def test_local_executor(self):
        self._mock_bin("agy", '{"conversation_id":"c1","status":"SUCCESS","duration_seconds":1.0,"response":"Done\\n<!-- GOAL_COMPLETE -->"}')
        ex = LocalExecutor(self.ws)
        res = ex.execute("run")
        self.assertTrue(res.goal_complete)

    def test_remote_executor_diff_parsing(self):
        payload = '{"conversation_id":"r1","status":"SUCCESS","duration_seconds":1.0,"response":"Remote\\n<!-- GOAL_COMPLETE -->"}\n---AGY_GIT_DIFF---\n a.py | 1 +\n 1 file changed, 1 insertion(+)'
        self._mock_bin("gt", payload)
        ex = RemoteExecutor(self.ws, target="node", branch="feat/x")
        res = ex.execute("run")
        self.assertTrue(res.goal_complete)
        self.assertIn("1 file changed", res.git_diff_summary)


class TestWorkAPI(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.ws = Path(self.td)
        self.api = WorkAPI(self.ws)

    def tearDown(self):
        shutil.rmtree(self.td)

    def test_relative_plan_prompt(self):
        p_dir = self.ws / "docs"
        p_dir.mkdir()
        plan = p_dir / "p.md"
        plan.write_text("# Plan")
        prompts = []
        self.api._run_and_handle = lambda ex, st, prompt, is_continue=False: prompts.append(prompt) or 0
        self.api.start_plan(str(plan))
        self.assertEqual(prompts[0], "/goal Implement Plan @docs/p.md")


if __name__ == "__main__":
    unittest.main()
