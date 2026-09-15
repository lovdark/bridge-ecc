"""ECC-compatible target roots and install-state locations."""
from pathlib import Path
from typing import Dict, Optional

TARGETS: Dict[str, Dict[str, object]] = {
    "claude": {"kind": "home", "root": ".claude"},
    "claude-project": {"kind": "project", "root": ".claude"},
    "cursor": {"kind": "project", "root": ".cursor"},
    "antigravity": {"kind": "project", "root": ".agents"},
    "codex": {"kind": "home", "root": ".codex"},
    "gemini": {"kind": "project", "root": ".gemini"},
    "hermes": {"kind": "home", "root": ".hermes"},
    "opencode": {"kind": "home", "root": ".config/opencode"},
    "openclaw": {"kind": "home", "root": ".openclaw"},
    "codebuddy": {"kind": "project", "root": ".codebuddy"},
    "joycode": {"kind": "project", "root": ".joycode"},
    "kimi": {"kind": "project", "root": ".kimi-code"},
    "qwen": {"kind": "home", "root": ".qwen"},
    "zed": {"kind": "project", "root": ".zed"},
}


def resolve_target(target: str, home_dir: Optional[Path] = None, project_root: Optional[Path] = None) -> Dict[str, str]:
    definition = TARGETS.get(target)
    if not definition:
        raise ValueError(f"unknown install target: {target}")
    base = Path(home_dir or Path.home()) if definition["kind"] == "home" else Path(project_root or Path.cwd())
    root = (base / str(definition["root"])).resolve()
    state = root / "ecc-install-state.json" if target != "claude" and target != "claude-project" else (root / "ecc" / "install-state.json")
    return {"id": f"{target}-{'home' if definition['kind'] == 'home' else 'project'}", "target": target, "kind": str(definition["kind"]), "root": str(root), "install_state": str(state)}
