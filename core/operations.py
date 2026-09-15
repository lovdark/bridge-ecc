"""Deterministic, read-only target operation planning."""
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

FLATTEN_TARGETS = {"antigravity", "codebuddy", "joycode", "zed"}
MERGE_JSON_TARGETS = {"cursor", "kimi"}
HERMES_PLATFORM_PATHS = {".pi", "mcp-configs", "scripts/auto-update.js", "scripts/setup-package-manager.js", ".hermes"}
COMMON_PLATFORM_PATHS = HERMES_PLATFORM_PATHS
KIMI_PLATFORM_PATHS = (COMMON_PLATFORM_PATHS - {".hermes"}) | {".kimi"}
FLATTEN_MODULE_PATHS = {
    "rules-core": ("rules",),
    "agents-core": ("agents",),
    "commands-core": ("commands",),
    "platform-configs": (),
}


def _files(source: Path, relative: Path) -> Iterable[Path]:
    path = source / relative
    if path.is_dir():
        return sorted(item for item in path.rglob("*") if item.is_file())
    return [path] if path.is_file() else []


def plan_operations(source: Path, target_info: Dict[str, str], module_id: str, paths: List[str]) -> List[Dict[str, Any]]:
    target = target_info["target"]
    root = Path(target_info["root"])
    operations: List[Dict[str, Any]] = []
    for raw in paths:
        relative = Path(raw)
        if target in FLATTEN_TARGETS and module_id in FLATTEN_MODULE_PATHS:
            allowed = FLATTEN_MODULE_PATHS[module_id]
            if not any(raw == prefix or raw.startswith(prefix + "/") for prefix in allowed):
                continue
        allowed_platform = KIMI_PLATFORM_PATHS if target == "kimi" else COMMON_PLATFORM_PATHS
        if target != "cursor" and target not in FLATTEN_TARGETS and module_id == "platform-configs" and raw not in allowed_platform:
            continue
        if relative.is_absolute() or ".." in relative.parts:
            continue
        if target in MERGE_JSON_TARGETS and raw == ".mcp.json" and (source / relative).is_file():
            try:
                merge_payload = json.loads((source / relative).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                merge_payload = None
            operation: Dict[str, Any] = {"kind": "merge-json", "module": module_id, "source": raw, "target": str(root / "mcp.json"), "strategy": "merge-json", "read_only": True}
            if merge_payload is not None:
                operation["merge_payload"] = merge_payload
            operations.append(operation)
            continue
        source_path = source / relative
        if not source_path.exists():
            continue
        if target == "kimi" and module_id == "agents-core" and relative == Path(".agents"):
            source_path = source / ".agents/skills"
            if not source_path.is_dir():
                continue
            operations.append({"kind": "copy-path", "module": module_id, "source": ".agents/skills", "target": str(root / ".agents/skills"), "strategy": "preserve-relative-path", "ownership": "managed", "read_only": True})
            continue
        if target in FLATTEN_TARGETS and module_id in {"agents-core", "commands-core"} and relative in {Path("agents"), Path("commands")} and source_path.is_dir():
            destination = root / ("workflows" if relative == Path("commands") else "agents")
            operation = {"kind": "copy-path", "module": module_id, "source": raw, "target": str(destination), "strategy": "preserve-relative-path", "ownership": "managed", "read_only": True}
            if target == "antigravity" and relative == Path("agents"):
                operation["content_transform"] = "antigravity-agent-frontmatter"
            operations.append(operation)
            continue
        if source_path.is_dir() and target not in FLATTEN_TARGETS and target != "cursor":
            strategy = "sync-root-children" if ((target == "hermes" and relative == Path(".hermes")) or (target == "kimi" and relative == Path(".kimi"))) else "preserve-relative-path"
            operations.append({"kind": "copy-path", "module": module_id, "source": raw, "target": str(root / relative), "strategy": strategy, "ownership": "managed", "read_only": True})
            if target == "kimi" and module_id == "platform-configs" and raw == "mcp-configs" and (source / ".mcp.json").is_file():
                try:
                    merge_payload = json.loads((source / ".mcp.json").read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    merge_payload = None
                operation = {"kind": "merge-json", "module": module_id, "source": ".mcp.json", "target": str(root / "mcp.json"), "strategy": "merge-json", "read_only": True}
                if merge_payload is not None:
                    operation["merge_payload"] = merge_payload
                operations.append(operation)
            continue
        for file_path in _files(source, relative):
            file_relative = file_path.relative_to(source)
            cursor_rule = target == "cursor" and len(file_relative.parts) > 2 and file_relative.parts[:2] == (".cursor", "rules")
            if target in FLATTEN_TARGETS and file_relative.parts and file_relative.parts[0] == "rules":
                flattened = "-".join(file_relative.parts[1:])
                destination = root / "rules" / flattened
                strategy = "flatten-copy"
            elif cursor_rule:
                flattened = "-".join(file_relative.parts[2:])
                destination = root / "rules" / (Path(flattened).stem + ".mdc")
                strategy = "flatten-copy"
            else:
                destination = root / file_relative
                strategy = "preserve-relative-path"
            operations.append({"kind": "copy-path", "module": module_id, "source": file_relative.as_posix(), "target": str(destination), "strategy": strategy, "ownership": "managed", "read_only": True})
    return operations
