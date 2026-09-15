"""Validate an ECC-compatible repository surface without third-party packages."""
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_MARKERS = {
    "skill": "SKILL.md",
    "command": None,
    "agent": None,
    "rule": None,
    "hook": None,
    "script": None,
}


def validate_tree(root: Path) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    errors: List[Dict[str, str]] = []
    checked = 0
    for directory, kind in (("skills", "skill"), ("commands", "command"), ("agents", "agent"), ("rules", "rule"), ("hooks", "hook"), ("scripts", "script")):
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
                continue
            checked += 1
            if path.stat().st_size == 0:
                errors.append({"path": path.relative_to(root).as_posix(), "error": "file is empty"})
            if kind == "skill" and path.name == "SKILL.md":
                text = path.read_text(encoding="utf-8", errors="replace")
                if not text.startswith("---"):
                    errors.append({"path": path.relative_to(root).as_posix(), "error": "skill is missing frontmatter"})
                frontmatter = text.split("---", 2)[1] if text.startswith("---") and text.count("---") >= 2 else ""
                for marker in ("name:", "description:"):
                    if marker not in frontmatter:
                        errors.append({"path": path.relative_to(root).as_posix(), "error": f"skill frontmatter missing {marker}"})
    return {"root": str(root), "checked": checked, "valid": not errors, "errors": errors}
