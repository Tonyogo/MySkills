import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.core.state import SessionState
from agy_goal.core.circuit_breaker import CircuitBreaker, CircuitBreakerError

class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.cb = CircuitBreaker()

    def test_pre_turn_passes_under_limit(self):
        state = SessionState(active=True, round=2, max_rounds=3)
        # Should not raise
        self.cb.check_pre_turn(state)

    def test_pre_turn_halts_at_max_rounds(self):
        state = SessionState(active=True, round=3, max_rounds=3)
        with self.assertRaises(CircuitBreakerError) as ctx:
            self.cb.check_pre_turn(state)
        self.assertIn("Maximum continue rounds reached (3/3)", ctx.exception.reason)

    def test_identical_error_loop_detection(self):
        state = SessionState(active=True, round=1, max_rounds=3)
        error_msg = "AssertionError: line 42 failed"

        # Turn 1
        self.cb.record_turn(state, raw_response="Some text", error_message=error_msg)
        self.assertEqual(state.consecutive_identical_errors, 1)

        # Turn 2 with identical error
        state.round = 2
        with self.assertRaises(CircuitBreakerError) as ctx:
            self.cb.record_turn(state, raw_response="Some text again", error_message=error_msg)
        self.assertIn("Identical error loop detected", ctx.exception.reason)
        self.assertEqual(state.consecutive_identical_errors, 2)

    def test_reset_consecutive_errors_on_different_output(self):
        state = SessionState(active=True, round=1, max_rounds=3)
        self.cb.record_turn(state, raw_response="Error A", error_message="Error A")
        self.assertEqual(state.consecutive_identical_errors, 1)

        state.round = 2
        self.cb.record_turn(state, raw_response="Error B", error_message="Error B")
        self.assertEqual(state.consecutive_identical_errors, 1)
