import json
import tempfile
import unittest
from pathlib import Path

from adapters.hermes import to_hermes_decision
from adapters.hooks import build_hook_request
from adapters.node import NodeAdapter
from adapters.posix import argv as posix_argv
from adapters.powershell import argv as powershell_argv
from core.catalog import catalog
from core.doctor import repository_status
from core.install_plan import build_install_plan
from core.install_compat import list_profiles, resolve_profile
from core.operations import plan_operations
from core.install_state import build_state, verify_dry_run
from core.apply import apply_plan
from core.targets import resolve_target
from core.validate import validate_tree


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

    def test_validate_tree_checks_skill_frontmatter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skills/demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: demo\ndescription: test\n---\n# Demo", encoding="utf-8")
            self.assertTrue(validate_tree(root)["valid"])
            (skill / "SKILL.md").write_text("# Demo", encoding="utf-8")
            self.assertFalse(validate_tree(root)["valid"])

    def test_validate_tree_checks_ecc_agent_command_and_hook_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "agents").mkdir()
            (root / "commands").mkdir()
            (root / "hooks").mkdir()
            (root / "agents/reviewer.md").write_text("---\nname: reviewer\ndescription: review\n---\nPrompt", encoding="utf-8")
            (root / "commands/check.md").write_text("---\ndescription: check\n---\nRun check", encoding="utf-8")
            (root / "hooks/hooks.json").write_text('{"hooks": {"PreToolUse": []}}', encoding="utf-8")
            (root / "hooks/hooks.metadata.json").write_text('{"entries": {"PreToolUse": []}}', encoding="utf-8")
            (root / "hooks/events.json").write_text('{"events": []}', encoding="utf-8")
            (root / "agents/__init__.py").write_text("", encoding="utf-8")
            self.assertTrue(validate_tree(root)["valid"])
            (root / "hooks/hooks.json").write_text('{"bad": true}', encoding="utf-8")
            self.assertFalse(validate_tree(root)["valid"])

    def test_hook_request_never_enables_execution(self):
        request = build_hook_request("pre-tool", "rm -rf ./cache")
        self.assertFalse(request["execute"])
        self.assertTrue(request["approval"]["blocked"])

    def test_install_plan_is_read_only_and_filterable(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            target = Path(directory) / "target"
            (source / "skills/demo").mkdir(parents=True)
            (source / "skills/demo/SKILL.md").write_text("---\nname: demo\ndescription: test\n---\n# Demo", encoding="utf-8")
            (source / "rules.md").write_text("ignored", encoding="utf-8")
            result = build_install_plan(source, target, ["skill"])
            self.assertTrue(result["valid"])
            self.assertTrue(result["write_required"])
            self.assertFalse(target.exists())
            self.assertEqual(result["actions"][0]["kind"], "skill")

    def test_ecc_profile_resolution_preserves_target_skips(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifests").mkdir()
            (root / "rules").mkdir()
            (root / "rules/common.md").write_text("rules", encoding="utf-8")
            (root / "manifests/install-profiles.json").write_text(
                '{"version": 1, "profiles": {"core": {"description": "Core", "modules": ["rules-core", "hooks-runtime"]}}}', encoding="utf-8"
            )
            (root / "manifests/install-modules.json").write_text(
                '{"version": 1, "modules": ['
                '{"id": "rules-core", "kind": "rules", "paths": ["rules"], "targets": ["hermes"]},'
                '{"id": "hooks-runtime", "kind": "hooks", "paths": ["hooks"], "targets": ["claude"]}'
                ']}', encoding="utf-8"
            )
            self.assertEqual(list_profiles(root)[0]["id"], "core")
            result = resolve_profile(root, "core", "hermes", home_dir=root / "home")
            self.assertTrue(result["valid"])
            self.assertEqual(result["modules"], ["rules-core"])
            self.assertEqual(result["skipped_modules"], ["hooks-runtime"])
            self.assertEqual(result["target_info"]["root"], str((root / "home/.hermes").resolve()))

    def test_target_registry_distinguishes_home_and_project_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            self.assertEqual(resolve_target("hermes", base)["root"], str((base / ".hermes").resolve()))
            self.assertEqual(resolve_target("cursor", project_root=base)["root"], str((base / ".cursor").resolve()))

    def test_target_operation_strategies(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            (source / "rules/common").mkdir(parents=True)
            (source / "rules/common/security.md").write_text("rule", encoding="utf-8")
            (source / ".mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            zed = resolve_target("zed", project_root=Path(directory))
            flattened = plan_operations(source, zed, "rules-core", ["rules"])
            self.assertEqual(flattened[0]["strategy"], "flatten-copy")
            self.assertTrue(flattened[0]["target"].endswith("rules/common-security.md"))
            (source / ".cursor/rules").mkdir(parents=True)
            (source / ".cursor/rules/common.md").write_text("rule", encoding="utf-8")
            cursor_rules = plan_operations(source, resolve_target("cursor", project_root=Path(directory)), "platform-configs", [".cursor/rules"])
            self.assertEqual(cursor_rules[0]["strategy"], "flatten-copy")
            self.assertTrue(cursor_rules[0]["target"].endswith("rules/common.mdc"))
            cursor = resolve_target("cursor", project_root=Path(directory))
            merged = plan_operations(source, cursor, "platform-configs", [".mcp.json"])
            self.assertEqual(merged[0]["strategy"], "merge-json")
            self.assertTrue(merged[0]["read_only"])
            self.assertEqual(plan_operations(source, zed, "platform-configs", [".missing-platform-dir"]), [])

    def test_managed_state_is_deterministic_and_dry_run_never_writes(self):
        plan = {"profile": "core", "target": "hermes", "target_info": {"root": "/tmp/.hermes"}, "modules": ["rules"], "operations": [{"module": "rules", "source": "rules/a.md", "target": "/tmp/.hermes/rules/a.md", "strategy": "preserve-relative-path", "read_only": True}]}
        first = build_state(plan)
        second = build_state(plan)
        self.assertEqual(first, second)
        result = verify_dry_run(plan, dry_run=True)
        self.assertTrue(result["valid"])
        self.assertFalse(result["write_enabled"])
        self.assertEqual(result["operation_count"], 1)
        self.assertFalse(verify_dry_run(plan, dry_run=False)["valid"])

    def test_apply_requires_gates_and_writes_fixture_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            (source / "rules").mkdir(parents=True)
            (source / "rules/a.md").write_text("rule", encoding="utf-8")
            plan = {"profile": "core", "target": "hermes", "source_root": str(source), "target_info": {"root": str(target)}, "modules": ["rules"], "operations": [{"module": "rules", "source": "rules/a.md", "target": str(target / "rules/a.md"), "strategy": "preserve-relative-path", "read_only": True}]}
            self.assertFalse(apply_plan(plan, allow_writes=False)["valid"])
            digest = build_state(plan)["plan_sha256"]
            result = apply_plan(plan, allow_writes=True, confirm_plan=digest)
            self.assertTrue(result["valid"])
            self.assertEqual((target / "rules/a.md").read_text(encoding="utf-8"), "rule")
            self.assertTrue(Path(result["state_file"]).is_file())
            self.assertFalse(apply_plan(plan, allow_writes=True, confirm_plan="wrong")["valid"])

    def test_apply_rejects_target_escape_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            (source / "rules").mkdir(parents=True)
            (source / "rules/a.md").write_text("rule", encoding="utf-8")
            plan = {"profile": "core", "target": "hermes", "source_root": str(source), "target_info": {"root": str(target)}, "modules": ["rules"], "operations": [{"module": "rules", "source": "rules/a.md", "target": str(root / "outside.md"), "strategy": "preserve-relative-path", "read_only": True}]}
            result = apply_plan(plan, allow_writes=True, confirm_plan=build_state(plan)["plan_sha256"])
            self.assertFalse(result["valid"])
            self.assertFalse((root / "outside.md").exists())

    def test_apply_merges_claude_hook_ids_without_replacing_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source"; target = root / "target"
            source.mkdir(); target.mkdir()
            hook = {"matcher": "Bash", "hooks": [{"type": "command", "command": "check"}]}
            (source / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": [hook]}}), encoding="utf-8")
            settings = target / "settings.json"
            settings.write_text(json.dumps({"theme": "dark", "hooks": {"PreToolUse": [hook]}}), encoding="utf-8")
            plan = {"profile": "core", "target": "claude", "source_root": str(source), "target_info": {"root": str(target)}, "modules": ["hooks"], "operations": [{"kind": "update-claude-settings", "module": "hooks", "source": "hooks.json", "target": str(settings), "strategy": "merge-hook-ids", "read_only": True}]}
            result = apply_plan(plan, allow_writes=True, confirm_plan=build_state(plan)["plan_sha256"])
            self.assertTrue(result["valid"])
            merged = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(merged["theme"], "dark")
            self.assertEqual(len(merged["hooks"]["PreToolUse"]), 1)


if __name__ == "__main__":
    unittest.main()
