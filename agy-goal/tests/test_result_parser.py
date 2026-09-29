import unittest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from agy_goal.core.result_parser import parse_agy_output, ExecutionResult

class TestResultParser(unittest.TestCase):
    def test_parse_valid_json_with_goal_complete(self):
        sample = '{"conversation_id": "c1", "status": "SUCCESS", "duration_seconds": 12.5, "response": "Done!\\n<!-- GOAL_COMPLETE -->"}'
        res = parse_agy_output(sample, exit_code=0)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.conversation_id, "c1")
        self.assertEqual(res.duration_seconds, 12.5)
        self.assertTrue(res.goal_complete)
        self.assertIn("Done!", res.raw_response)

    def test_parse_valid_json_without_goal_complete(self):
        sample = '{"conversation_id": "c2", "status": "ERROR", "duration_seconds": 5.0, "response": "Failed at test_foo"}'
        res = parse_agy_output(sample, exit_code=1)
        self.assertEqual(res.status, "ERROR")
        self.assertEqual(res.conversation_id, "c2")
        self.assertFalse(res.goal_complete)
        self.assertIn("Failed at test_foo", res.raw_response)

    def test_parse_malformed_json_fallback(self):
        sample = "Internal fatal error: connection refused"
        res = parse_agy_output(sample, exit_code=1)
        self.assertEqual(res.status, "ERROR")
        self.assertFalse(res.goal_complete)
        self.assertIn("Internal fatal error", res.raw_response)

    def test_parse_empty_output(self):
        res = parse_agy_output("", exit_code=1)
        self.assertEqual(res.status, "ERROR")
        self.assertFalse(res.goal_complete)
        self.assertEqual(res.raw_response, "")
