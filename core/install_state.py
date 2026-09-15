"""Managed install state and fail-closed apply verification.

This module intentionally never creates, edits, or deletes target files.
"""
import hashlib
import json
from typing import Any, Dict, Iterable, List

STATE_SCHEMA = 1


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_state(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Build a stable managed-state record from an ECC plan."""
    operations = plan.get("operations", [])
    entries: List[Dict[str, Any]] = []
    for operation in operations:
        entries.append({
            "module": operation.get("module"),
            "source": operation.get("source"),
            "target": operation.get("target"),
            "strategy": operation.get("strategy"),
            "ownership": operation.get("ownership", "managed"),
        })
    entries.sort(key=lambda item: (str(item.get("target")), str(item.get("source")), str(item.get("module"))))
    identity = {
        "profile": plan.get("profile"),
        "target": plan.get("target"),
        "target_info": plan.get("target_info"),
        "modules": plan.get("modules", []),
        "entries": entries,
    }
    digest = hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()
    return {
        "valid": True,
        "schema": STATE_SCHEMA,
        "managed": True,
        "read_only": True,
        "profile": plan.get("profile"),
        "target": plan.get("target"),
        "plan_sha256": digest,
        "entries": entries,
    }


def verify_dry_run(plan: Dict[str, Any], *, dry_run: bool) -> Dict[str, Any]:
    """Validate that a plan can be reviewed without permitting filesystem writes."""
    operations = plan.get("operations", [])
    unsafe = [index for index, item in enumerate(operations) if item.get("read_only") is not True]
    if not dry_run:
        return {"valid": False, "dry_run": False, "write_enabled": False, "error": "apply is disabled; pass --dry-run for review"}
    if unsafe:
        return {"valid": False, "dry_run": True, "write_enabled": False, "error": "plan contains non-read-only operations", "unsafe_operations": unsafe}
    return {
        "valid": True,
        "dry_run": True,
        "write_enabled": False,
        "operation_count": len(operations),
        "state": build_state(plan),
        "would_apply": [item.get("target") for item in operations],
    }
