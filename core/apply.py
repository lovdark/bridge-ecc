"""Explicitly authorized, atomic application of an ECC plan."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.install_state import build_state
from core.transforms import adapt_antigravity_agent

MAX_OPERATIONS = 10_000
MAX_BYTES = 50 * 1024 * 1024


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


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _file_targets(operation: Dict[str, Any], source_root: Path) -> List[Tuple[Path, Path]]:
    source = source_root / operation["source"]
    destination = Path(operation["target"])
    if source.is_file():
        return [(source, destination)]
    if source.is_dir():
        return [(child, destination / child.relative_to(source)) for child in sorted(source.rglob("*")) if child.is_file()]
    return []


def _restore(backups: Dict[Path, bytes], absent: List[Path]) -> None:
    for path, data in backups.items():
        _atomic_write(path, data)
    for path in absent:
        if path.is_file() or path.is_symlink():
            path.unlink()


def apply_plan(plan: Dict[str, Any], *, allow_writes: bool, confirm_plan: str = "", overwrite: bool = False) -> Dict[str, Any]:
    """Apply copy/merge operations only after explicit safety gates."""
    if not allow_writes:
        return {"valid": False, "write_enabled": False, "error": "writes are disabled; pass --allow-writes"}
    expected = build_state(plan)["plan_sha256"]
    if confirm_plan != expected:
        return {"valid": False, "write_enabled": False, "error": "plan hash confirmation does not match", "expected_plan_sha256": expected}
    if any(item.get("read_only") is not True for item in plan.get("operations", [])):
        return {"valid": False, "write_enabled": False, "error": "plan contains non-read-only operations"}

    source_root = Path(plan["source_root"]).expanduser().resolve()
    target_root = Path(plan["target_info"]["root"]).expanduser().resolve()
    state_path = target_root / ".brecc-state.json"
    writes: List[Tuple[Path, bytes]] = []
    for operation in plan.get("operations", []):
        source = (source_root / operation["source"]).resolve()
        destination = Path(operation["target"]).expanduser()
        if not _inside(source, source_root):
            return {"valid": False, "write_enabled": False, "error": f"source escapes source root: {source}"}
        if not _inside(destination.resolve(strict=False), target_root):
            return {"valid": False, "write_enabled": False, "error": f"target escapes target root: {destination}"}
        if destination.exists() and destination.is_symlink():
            return {"valid": False, "write_enabled": False, "error": f"refusing symlink target: {destination}"}
        if operation["strategy"] in {"merge-json", "merge-hook-ids"}:
            if not source.is_file():
                return {"valid": False, "write_enabled": False, "error": f"source disappeared: {source}"}
            try:
                incoming = json.loads(source.read_text(encoding="utf-8"))
                existing = json.loads(destination.read_text(encoding="utf-8")) if destination.is_file() else {}
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                return {"valid": False, "write_enabled": False, "error": f"invalid JSON during preflight: {error}"}
            if operation["strategy"] == "merge-hook-ids":
                incoming = incoming.get("hooks") if isinstance(incoming, dict) else None
                if not isinstance(incoming, dict):
                    return {"valid": False, "write_enabled": False, "error": "Claude hook merge requires a hooks object"}
                existing_hooks = existing.get("hooks", {})
                if not isinstance(existing_hooks, dict):
                    return {"valid": False, "write_enabled": False, "error": "existing Claude settings hooks must be an object"}
                merged = dict(existing)
                merged["hooks"] = dict(existing_hooks)
                for event, entries in incoming.items():
                    if not isinstance(entries, list):
                        return {"valid": False, "write_enabled": False, "error": f"Claude hook event must be a list: {event}"}
                    current = list(merged["hooks"].get(event, []))
                    seen = {json.dumps(item, sort_keys=True, separators=(",", ":")) for item in current}
                    for item in entries:
                        marker = json.dumps(item, sort_keys=True, separators=(",", ":"))
                        if marker not in seen:
                            current.append(item)
                            seen.add(marker)
                    merged["hooks"][event] = current
            elif not isinstance(incoming, dict) or not isinstance(existing, dict):
                return {"valid": False, "write_enabled": False, "error": "JSON merge requires object values"}
            else:
                merged = dict(existing)
                for key, value in incoming.items():
                    if isinstance(value, dict) and isinstance(merged.get(key), dict):
                        merged[key] = {**merged[key], **value}
                    else:
                        merged[key] = value
            data = (json.dumps(merged, indent=2, sort_keys=True) + "\n").encode("utf-8")
            writes.append((destination, data))
        else:
            files = _file_targets(operation, source_root)
            if not files:
                return {"valid": False, "write_enabled": False, "error": f"source disappeared: {source}"}
            for child, destination_file in files:
                if not _inside(child.resolve(), source_root):
                    return {"valid": False, "write_enabled": False, "error": f"source file escapes source root: {child}"}
                resolved = destination_file.resolve(strict=False)
                if not _inside(resolved, target_root):
                    return {"valid": False, "write_enabled": False, "error": f"target escapes target root: {destination_file}"}
                if destination_file.exists() and destination_file.is_symlink():
                    return {"valid": False, "write_enabled": False, "error": f"refusing symlink target: {destination_file}"}
                data = child.read_bytes()
                if operation.get("content_transform") == "antigravity-agent-frontmatter" and child.suffix.lower() in {".md", ".mdx", ".markdown"}:
                    data = adapt_antigravity_agent(data, str(child))
                writes.append((destination_file, data))
    if len(writes) > MAX_OPERATIONS:
        return {"valid": False, "write_enabled": False, "error": f"operation limit exceeded: {len(writes)} > {MAX_OPERATIONS}"}
    total_bytes = sum(len(data) for _, data in writes)
    if total_bytes > MAX_BYTES:
        return {"valid": False, "write_enabled": False, "error": f"byte limit exceeded: {total_bytes} > {MAX_BYTES}"}
    merge_destinations = {Path(item["target"]).expanduser() for item in plan.get("operations", []) if item.get("strategy") in {"merge-json", "merge-hook-ids"}}
    for destination, _ in writes:
        if destination.exists() and not overwrite and destination != state_path and destination not in merge_destinations:
            return {"valid": False, "write_enabled": False, "error": f"refusing to overwrite existing path: {destination}"}
    if state_path.exists() and state_path.is_symlink():
        return {"valid": False, "write_enabled": False, "error": f"refusing symlink state file: {state_path}"}

    backups: Dict[Path, bytes] = {}
    absent: List[Path] = []
    all_writes = writes + [(state_path, (json.dumps(build_state(plan), indent=2, sort_keys=True) + "\n").encode("utf-8"))]
    for destination, _ in all_writes:
        if destination in backups or destination in absent:
            continue
        if destination.is_file():
            backups[destination] = destination.read_bytes()
        elif not destination.exists():
            absent.append(destination)
    applied: List[str] = []
    try:
        for destination, data in all_writes:
            _atomic_write(destination, data)
            applied.append(str(destination))
    except (OSError, IOError) as error:
        _restore(backups, absent)
        return {"valid": False, "write_enabled": True, "error": f"apply failed and was rolled back: {error}", "applied": applied}
    return {"valid": True, "write_enabled": True, "applied": applied, "state_file": str(state_path), "plan_sha256": expected}
