# agy-goal/tests/test_single_file_compilation.py
import unittest
import importlib.util
from pathlib import Path

class TestSingleFileCompilation(unittest.TestCase):
    def test_script_exists_and_loads(self):
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "agy-goal.py"
        self.assertTrue(script_path.exists(), "agy-goal.py must exist")

        spec = importlib.util.spec_from_file_location("agy_goal_cli", script_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check required classes exist
        self.assertTrue(hasattr(module, "WorkAPI"))
        self.assertTrue(hasattr(module, "CircuitBreaker"))
        self.assertTrue(hasattr(module, "StateStore"))
        self.assertTrue(hasattr(module, "LocalExecutor"))
        self.assertTrue(hasattr(module, "RemoteExecutor"))
        self.assertTrue(hasattr(module, "parse_agy_output"))


if __name__ == "__main__":
    unittest.main()
