"""NotFound fixes must point at real CLI verbs."""

from __future__ import annotations

import unittest

from engine.errors import EngineError, NotFound


class NotFoundTests(unittest.TestCase):
    def test_fix_points_at_a_real_cli_verb(self) -> None:
        cases = {
            "claim": "claim list",
            "research": "research list",
            "question": "question list",
            "source": "source list",
            "hypothesis": "hypothesis list",
            "protocol": "protocol list",
            "test": "test list",
            "killtest": "test",
            "event": "events",
            "ai_artifact": "ai artifacts",
            "observation": "observation list CLAIM",
        }
        for kind, verb in cases.items():
            with self.subTest(kind=kind):
                error = NotFound(kind, "x_000001")
                self.assertIsInstance(error, EngineError)
                self.assertIn(f"python -m engine {verb}", error.fix)


if __name__ == "__main__":
    unittest.main()
