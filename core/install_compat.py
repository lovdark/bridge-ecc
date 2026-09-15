"""Read ECC install manifests and resolve profile plans without writing files."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


REQUIRED_MANIFESTS = ("install-profiles.json", "install-modules.json")


def _load(root: Path, name: str) -> Dict[str, Any]:
    path = root / "manifests" / name
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {path}: {error}")
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def list_profiles(root: Path) -> List[Dict[str, Any]]:
    profiles = _load(Path(root).expanduser().resolve(), "install-profiles.json").get("profiles", {})
    return [{"id": profile_id, "description": value.get("description", ""), "moduleCount": len(value.get("modules", []))} for profile_id, value in profiles.items()]


def resolve_profile(root: Path, profile: str, target: Optional[str] = None) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    profiles = _load(root, "install-profiles.json").get("profiles", {})
    modules = {item.get("id"): item for item in _load(root, "install-modules.json").get("modules", [])}
    selected = profiles.get(profile)
    if not isinstance(selected, dict):
        return {"valid": False, "error": f"unknown install profile: {profile}", "profile": profile, "modules": [], "operations": []}
    module_ids = selected.get("modules", [])
    missing = [module_id for module_id in module_ids if module_id not in modules]
    if missing:
        return {"valid": False, "error": "profile references missing modules", "missing_modules": missing, "profile": profile, "modules": [], "operations": []}
    chosen = []
    skipped = []
    operations = []
    visited = set()

    def select(module_id: str) -> None:
        if module_id in visited:
            return
        visited.add(module_id)
        module = modules[module_id]
        targets = module.get("targets", [])
        if target and target not in targets:
            skipped.append(module_id)
            return
        for dependency in module.get("dependencies", []):
            if dependency in modules:
                select(dependency)
        chosen.append(module_id)
        for relative in module.get("paths", []):
            source = root / relative
            if source.exists():
                operations.append({"module": module_id, "source": relative, "target": relative, "strategy": "copy", "read_only": True})
    for module_id in module_ids:
        select(module_id)
    return {"valid": True, "profile": profile, "description": selected.get("description", ""), "target": target, "modules": chosen, "skipped_modules": skipped, "operations": operations, "write_required": bool(operations)}
