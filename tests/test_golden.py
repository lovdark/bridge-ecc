import json
import unittest
from pathlib import Path

from core.policy import inspect_command


class GoldenPolicyTests(unittest.TestCase):
    def test_fixture_decisions_remain_stable(self):
        fixture = Path(__file__).parent / "fixtures/policy_cases.json"
        cases = json.loads(fixture.read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["name"]):
                result = inspect_command(case["command"])
                self.assertEqual(result["decision"], case["decision"])


if __name__ == "__main__":
    unittest.main()
