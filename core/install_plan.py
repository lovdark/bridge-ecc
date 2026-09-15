"""Read-only install planning for ECC-compatible component trees."""
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from core.catalog import catalog


def build_install_plan(source: Path, target: Path, components: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    source = Path(source).expanduser().resolve()
    target = Path(target).expanduser().resolve()
    if not source.is_dir():
        return {"valid": False, "source": str(source), "target": str(target), "error": "source directory does not exist", "actions": []}
    selected = set(components or ())
    inventory = catalog(source)
    actions = []
    for item in inventory["items"]:
        if selected and item["kind"] not in selected:
            continue
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            return {"valid": False, "source": str(source), "target": str(target), "error": "unsafe relative path in catalog", "actions": []}
        actions.append({"operation": "copy", "kind": item["kind"], "source": str(source / relative), "target": str(target / relative)})
    return {"valid": True, "source": str(source), "target": str(target), "actions": actions, "write_required": bool(actions)}
