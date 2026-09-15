import json
import tempfile
import unittest
from pathlib import Path

from adapters.hermes import to_hermes_decision
from adapters.node import NodeAdapter
from adapters.posix import argv as posix_argv
from adapters.powershell import argv as powershell_argv
from core.catalog import catalog
from core.doctor import repository_status


class AdapterTests(unittest.TestCase):
    def test_hermes_contract_preserves_review(self):
        result = to_hermes_decision({"decision": "review", "reasons": ["network access"]})
        self.assertEqual(result["decision"], "review")
        self.assertTrue(result["requires_approval"])
        self.assertFalse(result["blocked"])

    def test_unknown_decision_fails_closed(self):
        self.assertEqual(to_hermes_decision({"decision": "surprise"})["decision"], "deny")

    def test_node_adapter_reports_missing_executable(self):
        result = NodeAdapter(executable="/not/a/node").run_script(Path("/not/a/script.js"))
        self.assertFalse(result["ok"])

    def test_argv_adapters_do_not_interpolate_arguments(self):
        self.assertEqual(powershell_argv("Write-Output 'ok'", "pwsh")[0], "pwsh")
        self.assertEqual(posix_argv("printf '%s' ok", "sh"), ["sh", "-c", "printf '%s' ok"])

    def test_catalog_and_repository_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "skills/demo").mkdir(parents=True)
            (root / "skills/demo/SKILL.md").write_text("# demo", encoding="utf-8")
            result = catalog(root)
            self.assertEqual(result["counts"]["skill"], 1)
            self.assertEqual(result["total"], 1)
            (root / "core").mkdir()
            (root / "bin").mkdir()
            (root / "tests").mkdir()
            for path in ("core/policy.py", "bin/brecc.py", "tests/test_policy.py"):
                (root / path).write_text("", encoding="utf-8")
            self.assertTrue(repository_status(root)["healthy"])


if __name__ == "__main__":
    unittest.main()
