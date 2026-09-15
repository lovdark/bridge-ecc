"""Validate an ECC-compatible repository surface without third-party packages."""
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


COMPONENT_DIRS = (("skills", "skill"), ("commands", "command"), ("agents", "agent"), ("rules", "rule"), ("hooks", "hook"), ("scripts", "script"))


def _frontmatter(text: str) -> Tuple[Dict[str, str], bool]:
    if not text.startswith("---"):
        return {}, False
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, False
    values: Dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values, True


def validate_tree(root: Path) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    errors: List[Dict[str, str]] = []
    checked = 0
    for directory, kind in COMPONENT_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
                continue
            checked += 1
            relative = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                if path.name != "__init__.py":
                    errors.append({"path": relative, "error": "file is empty"})
                continue
            if kind == "skill" and path.name == "SKILL.md":
                metadata, has_frontmatter = _frontmatter(text)
                if not has_frontmatter:
                    errors.append({"path": relative, "error": "skill is missing valid frontmatter"})
                for marker in ("name", "description"):
                    if not metadata.get(marker):
                        errors.append({"path": relative, "error": f"skill frontmatter missing {marker}"})
            elif kind == "agent":
                metadata, has_frontmatter = _frontmatter(text)
                if not has_frontmatter:
                    errors.append({"path": relative, "error": "agent is missing valid frontmatter"})
                for marker in ("name", "description"):
                    if not metadata.get(marker):
                        errors.append({"path": relative, "error": f"agent frontmatter missing {marker}"})
            elif kind == "command":
                metadata, has_frontmatter = _frontmatter(text)
                if not has_frontmatter or not metadata.get("description"):
                    errors.append({"path": relative, "error": "command requires description frontmatter"})
            elif kind == "hook" and path.suffix.lower() == ".json":
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError as error:
                    errors.append({"path": relative, "error": f"invalid JSON: {error.msg}"})
                    continue
                if not isinstance(payload, dict) or not (
                    isinstance(payload.get("hooks"), dict)
                    or isinstance(payload.get("entries"), dict)
                    or isinstance(payload.get("events"), list)
                ):
                    errors.append({"path": relative, "error": "hook JSON requires hooks, entries, or events"})
    return {"root": str(root), "checked": checked, "valid": not errors, "errors": errors}
