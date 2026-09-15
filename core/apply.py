"""Explicitly authorized, atomic application of a read-only ECC plan."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

from core.install_state import build_state


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply_plan(plan: Dict[str, Any], *, allow_writes: bool, confirm_plan: str = "", overwrite: bool = False) -> Dict[str, Any]:
    """Apply copy/merge operations only after two explicit safety gates."""
    if not allow_writes:
        return {"valid": False, "write_enabled": False, "error": "writes are disabled; pass --allow-writes"}
    expected = build_state(plan)["plan_sha256"]
    if confirm_plan != expected:
        return {"valid": False, "write_enabled": False, "error": "plan hash confirmation does not match", "expected_plan_sha256": expected}
    if any(item.get("read_only") is not True for item in plan.get("operations", [])):
        return {"valid": False, "write_enabled": False, "error": "plan contains non-read-only operations"}
    source_root = Path(plan["source_root"])
    applied = []
    for operation in plan.get("operations", []):
        destination = Path(operation["target"])
        if destination.exists() and not overwrite and operation["strategy"] != "merge-json":
            return {"valid": False, "write_enabled": True, "error": f"refusing to overwrite existing path: {destination}", "applied": applied}
        source = source_root / operation["source"]
        if operation["strategy"] == "merge-json":
            existing: Dict[str, Any] = {}
            if destination.is_file():
                existing = json.loads(destination.read_text(encoding="utf-8"))
            incoming = operation.get("merge_payload", {})
            merged = dict(existing)
            for key, value in incoming.items():
                if isinstance(value, dict) and isinstance(merged.get(key), dict):
                    merged[key] = {**merged[key], **value}
                else:
                    merged[key] = value
            _atomic_write(destination, (json.dumps(merged, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        elif source.is_file():
            _atomic_write(destination, source.read_bytes())
        elif source.is_dir():
            for child in sorted(item for item in source.rglob("*") if item.is_file()):
                relative = child.relative_to(source)
                _atomic_write(destination / relative, child.read_bytes())
        else:
            return {"valid": False, "write_enabled": True, "error": f"source disappeared: {source}", "applied": applied}
        applied.append(str(destination))
    state_path = Path(plan["target_info"]["root"]) / ".brecc-state.json"
    _atomic_write(state_path, (json.dumps(build_state(plan), indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return {"valid": True, "write_enabled": True, "applied": applied, "state_file": str(state_path), "plan_sha256": expected}
