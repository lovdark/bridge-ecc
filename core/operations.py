"""Deterministic, read-only target operation planning."""
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

FLATTEN_TARGETS = {"antigravity", "codebuddy", "joycode", "zed"}
MERGE_JSON_TARGETS = {"cursor", "kimi"}
HERMES_PLATFORM_PATHS = {".pi", "mcp-configs", "scripts/auto-update.js", "scripts/setup-package-manager.js", ".hermes"}
COMMON_PLATFORM_PATHS = HERMES_PLATFORM_PATHS
TARGET_PLATFORM_PATHS = {
    "claude": (COMMON_PLATFORM_PATHS - {".hermes"}) | {".claude-plugin"},
    "claude-project": (COMMON_PLATFORM_PATHS - {".hermes"}) | {".claude-plugin"},
    "opencode": (COMMON_PLATFORM_PATHS - {".hermes"}) | {".opencode"},
    "codex": (COMMON_PLATFORM_PATHS - {".hermes"}) | {".codex"},
}
KIMI_PLATFORM_PATHS = (COMMON_PLATFORM_PATHS - {".hermes"}) | {".kimi"}
FLATTEN_MODULE_PATHS = {
    "rules-core": ("rules",),
    "agents-core": ("agents",),
    "commands-core": ("commands",),
    "platform-configs": (),
}
CURSOR_FLATTEN_MODULES = {"agents-core", "rules-core"}
CURSOR_RULE_PATHS = {"angular", "arkts", "cpp", "csharp", "dart", "fsharp", "java", "nuxt", "perl", "react", "react-native", "ruby", "rust", "vue", "web"}
CURSOR_RULE_EXCEPTIONS = {"rules/common/code-review.md", "rules/python/fastapi.md"}
CURSOR_PLATFORM_PATHS = {".cursor", ".pi", "mcp-configs", "scripts/auto-update.js", "scripts/setup-package-manager.js"}
FLAT_PLATFORM_PATHS = {".pi", "mcp-configs", "scripts/auto-update.js", "scripts/setup-package-manager.js"}


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
        if target == "cursor" and module_id == "rules-core" and raw.startswith("rules/"):
            parts = relative.parts
            if raw not in CURSOR_RULE_EXCEPTIONS and (len(parts) < 2 or parts[1] not in CURSOR_RULE_PATHS):
                continue
        if target == "cursor" and module_id == "agents-core" and raw == "AGENTS.md":
            continue
        if target == "cursor" and module_id == "hooks-runtime" and raw == "hooks":
            continue
        if target in {"joycode", "zed"} and module_id == "platform-configs" and raw not in FLAT_PLATFORM_PATHS and not (target == "zed" and raw == ".zed"):
            continue
        if target == "cursor" and module_id == "platform-configs" and raw not in CURSOR_PLATFORM_PATHS and not raw.startswith(".cursor/rules") and raw != ".mcp.json":
            continue
        if target == "antigravity" and module_id in FLATTEN_MODULE_PATHS:
            allowed = FLATTEN_MODULE_PATHS[module_id]
            if not any(raw == prefix or raw.startswith(prefix + "/") for prefix in allowed):
                continue
        allowed_platform = KIMI_PLATFORM_PATHS if target == "kimi" else TARGET_PLATFORM_PATHS.get(target, COMMON_PLATFORM_PATHS)
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
        if target == "cursor" and module_id == "agents-core" and relative == Path(".agents") and source_path.is_dir():
            operations.append({"kind": "copy-path", "module": module_id, "source": raw, "target": str(root / relative), "strategy": "preserve-relative-path", "ownership": "managed", "read_only": True})
            continue
        if target == "cursor" and module_id == "platform-configs" and relative == Path(".cursor/rules") and source_path.is_dir():
            for child in sorted(item for item in source_path.rglob("*") if item.is_file()):
                flattened = "-".join(child.relative_to(source_path).parts)
                operations.append({"kind": "copy-path", "module": module_id, "source": child.relative_to(source).as_posix(), "target": str(root / "rules" / (Path(flattened).stem + ".mdc")), "strategy": "flatten-copy", "ownership": "managed", "read_only": True})
            continue
        if target == "cursor" and module_id == "platform-configs" and relative == Path(".cursor") and source_path.is_dir():
            for child_name in (".cursor/hooks", ".cursor/hooks.json", ".cursor/skills"):
                child = source / child_name
                if child.exists():
                    operations.append({"kind": "copy-path", "module": module_id, "source": child_name, "target": str(root / Path(child_name).relative_to(".cursor")), "strategy": "preserve-relative-path", "ownership": "managed", "read_only": True})
            rules = source / ".cursor/rules"
            if rules.is_dir():
                for child in sorted(item for item in rules.rglob("*") if item.is_file()):
                    flattened = "-".join(child.relative_to(rules).parts)
                    operations.append({"kind": "copy-path", "module": module_id, "source": child.relative_to(source).as_posix(), "target": str(root / "rules" / (Path(flattened).stem + ".mdc")), "strategy": "flatten-copy", "ownership": "managed", "read_only": True})
            if (source / ".mcp.json").is_file():
                try:
                    merge_payload = json.loads((source / ".mcp.json").read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    merge_payload = None
                operation = {"kind": "merge-json", "module": module_id, "source": ".mcp.json", "target": str(root / "mcp.json"), "strategy": "merge-json", "read_only": True}
                if merge_payload is not None:
                    operation["merge_payload"] = merge_payload
                operations.append(operation)
            continue
        if target in {"joycode", "zed"} and module_id == "platform-configs" and relative in {Path(".pi"), Path("mcp-configs"), Path(".zed")} and source_path.is_dir():
            strategy = "sync-root-children" if target == "zed" and relative == Path(".zed") else "preserve-relative-path"
            operations.append({"kind": "copy-path", "module": module_id, "source": raw, "target": str(root / relative), "strategy": strategy, "ownership": "managed", "read_only": True})
            continue
        if target in {"joycode", "zed"} and module_id in {"agents-core", "commands-core"} and source_path.is_dir():
            operations.append({"kind": "copy-path", "module": module_id, "source": raw, "target": str(root / relative), "strategy": "preserve-relative-path", "ownership": "managed", "read_only": True})
            continue
        if target in FLATTEN_TARGETS and relative.parts[:1] == ("skills",) and source_path.is_dir():
            operations.append({"kind": "copy-path", "module": module_id, "source": raw, "target": str(root / relative), "strategy": "preserve-relative-path", "ownership": "managed", "read_only": True})
            continue
        if target in {"claude", "claude-project"} and module_id == "hooks-runtime" and relative == Path("hooks") and source_path.is_dir():
            for child_name in ("hooks/hooks.json", "hooks/codex-hooks.json", "hooks/memory-persistence", "hooks/README.md"):
                child = source / child_name
                if not child.exists():
                    continue
                if child_name == "hooks/hooks.json":
                    operations.append({"kind": "update-claude-settings", "module": module_id, "source": child_name, "target": str(root / "settings.json"), "strategy": "merge-hook-ids", "ownership": "managed", "read_only": True})
                else:
                    operations.append({"kind": "copy-path", "module": module_id, "source": child_name, "target": str(root / child_name), "strategy": "preserve-relative-path", "ownership": "managed", "read_only": True})
            continue
        if target == "antigravity" and module_id in {"agents-core", "commands-core"} and relative in {Path("agents"), Path("commands")} and source_path.is_dir():
            destination = root / ("workflows" if relative == Path("commands") else "agents")
            operation = {"kind": "copy-path", "module": module_id, "source": raw, "target": str(destination), "strategy": "preserve-relative-path", "ownership": "managed", "read_only": True}
            if target == "antigravity" and relative == Path("agents"):
                operation["content_transform"] = "antigravity-agent-frontmatter"
            operations.append(operation)
            continue
        if source_path.is_dir() and (target not in FLATTEN_TARGETS and (target != "cursor" or module_id not in CURSOR_FLATTEN_MODULES)):
            sync_paths = {"hermes": Path(".hermes"), "kimi": Path(".kimi"), "claude": Path(".claude-plugin"), "claude-project": Path(".claude-plugin"), "opencode": Path(".opencode"), "codex": Path(".codex")}
            strategy = "sync-root-children" if sync_paths.get(target) == relative else "preserve-relative-path"
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
            if target == "cursor" and module_id == "rules-core" and file_relative.parts and file_relative.parts[0] == "rules":
                parts = file_relative.parts
                if file_relative.as_posix() not in CURSOR_RULE_EXCEPTIONS and (len(parts) < 3 or parts[1] not in CURSOR_RULE_PATHS):
                    continue
            cursor_rule = target == "cursor" and file_relative.parts and (file_relative.parts[0] == "rules" or file_relative.parts[:2] == (".cursor", "rules"))
            cursor_agent = target == "cursor" and file_relative.parts and file_relative.parts[0] == "agents"
            if target in FLATTEN_TARGETS and file_relative.parts and file_relative.parts[0] == "rules":
                flattened = "-".join(file_relative.parts[1:])
                destination = root / "rules" / flattened
                strategy = "flatten-copy"
            elif cursor_agent:
                flattened = "-".join(file_relative.parts[1:])
                destination = root / "agents" / ("ecc-" + flattened)
                strategy = "flatten-copy"
            elif cursor_rule:
                start = 1 if file_relative.parts[0] == "rules" else 2
                flattened = "-".join(file_relative.parts[start:])
                destination = root / "rules" / (Path(flattened).stem + ".mdc")
                strategy = "flatten-copy"
            else:
                destination = root / file_relative
                strategy = "preserve-relative-path"
            operations.append({"kind": "copy-path", "module": module_id, "source": file_relative.as_posix(), "target": str(destination), "strategy": strategy, "ownership": "managed", "read_only": True})
    return operations
