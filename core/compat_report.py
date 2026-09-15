"""Compare BRECC plans with ECC's machine-readable install plans."""
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

DEFAULT_TARGETS = ("claude", "claude-project", "cursor", "antigravity", "codex", "gemini", "hermes", "opencode", "openclaw", "codebuddy", "joycode", "kimi", "qwen", "zed")


def _ecc_plan(root: Path, profile: str, target: str) -> Dict[str, Any]:
    try:
        output = subprocess.check_output(["node", "scripts/install-plan.js", "--profile", profile, "--target", target, "--json"], cwd=root, text=True, stderr=subprocess.STDOUT)
        return json.loads(output)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot run ECC plan for {target}: {error}")


def compare_plan(ecc: Dict[str, Any], brecc: Dict[str, Any]) -> Dict[str, Any]:
    ecc_selected = set(ecc.get("selectedModuleIds", []))
    brecc_selected = set(brecc.get("modules", []))
    ecc_skipped = set(ecc.get("skippedModuleIds", []))
    brecc_skipped = set(brecc.get("skipped_modules", []))
    ecc_strategies = Counter(item.get("strategy") for item in ecc.get("operations", []))
    brecc_strategies = Counter(item.get("strategy") for item in brecc.get("operations", []))
    return {
        "modules_match": ecc_selected == brecc_selected,
        "skipped_match": ecc_skipped == brecc_skipped,
        "operation_count_match": len(ecc.get("operations", [])) == len(brecc.get("operations", [])),
        "strategy_match": ecc_strategies == brecc_strategies,
        "exact": ecc_selected == brecc_selected and ecc_skipped == brecc_skipped and len(ecc.get("operations", [])) == len(brecc.get("operations", [])) and ecc_strategies == brecc_strategies,
        "ecc_operation_count": len(ecc.get("operations", [])),
        "brecc_operation_count": len(brecc.get("operations", [])),
        "ecc_strategies": dict(ecc_strategies),
        "brecc_strategies": dict(brecc_strategies),
    }


def compatibility_report(root: Path, profile: str, targets: Iterable[str], *, project_root: Path | None = None) -> Dict[str, Any]:
    from core.install_compat import resolve_profile
    root = Path(root).expanduser().resolve()
    project_root = project_root or root
    results: Dict[str, Any] = {}
    for target in targets:
        ecc = _ecc_plan(root, profile, target)
        brecc = resolve_profile(root, profile, target, project_root=project_root)
        results[target] = compare_plan(ecc, brecc)
    return {"profile": profile, "targets": results, "exact_target_count": sum(1 for item in results.values() if item["exact"]), "target_count": len(results)}
