"""Small, dependency-free repository catalog compatible with ECC layouts."""
from pathlib import Path
from typing import Any, Dict

KINDS = {"skills": "skill", "commands": "command", "agents": "agent", "rules": "rule", "hooks": "hook", "scripts": "script"}


def catalog(root: Path) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    items = []
    counts = {kind: 0 for kind in KINDS.values()}
    for directory, kind in KINDS.items():
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
                continue
            rel = path.relative_to(root).as_posix()
            items.append({"kind": kind, "path": rel})
            counts[kind] += 1
    return {"root": str(root), "counts": counts, "total": len(items), "items": items}
