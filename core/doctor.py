"""Runtime and repository diagnostics; no command execution is performed."""
import platform
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional


def runtime_status() -> Dict[str, object]:
    python = shutil.which("python3") or shutil.which("python")
    node = shutil.which("node")
    return {
        "platform": platform.system().lower(),
        "python": {"available": bool(python), "path": python, "version": platform.python_version()},
        "node": {"available": bool(node), "path": node},
        "python_canonical": True,
        "node_optional": True,
    }


def repository_status(root: Path) -> Dict[str, object]:
    root = Path(root).expanduser().resolve()
    required = ["core/policy.py", "bin/brecc.py", "tests/test_policy.py"]
    missing = [path for path in required if not (root / path).is_file()]
    return {"root": str(root), "exists": root.is_dir(), "missing_required": missing, "healthy": root.is_dir() and not missing}
