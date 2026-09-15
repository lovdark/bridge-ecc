"""macOS / POSIX capability adapter. It builds argv without shell interpolation."""
import platform
import shutil
from typing import Dict, List, Optional


def status() -> Dict[str, object]:
    shell = shutil.which("sh")
    return {"available": bool(shell), "executable": shell, "platform": platform.system().lower(), "mode": "argv-only"}


def argv(script: str, executable: Optional[str] = None) -> List[str]:
    return [executable or shutil.which("sh") or "sh", "-c", script]
