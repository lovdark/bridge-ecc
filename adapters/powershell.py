"""PowerShell capability adapter. It builds argv without invoking a shell."""
import shutil
from typing import Dict, List, Optional


def status() -> Dict[str, object]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    return {"available": bool(executable), "executable": executable, "mode": "argv-only"}


def argv(script: str, executable: Optional[str] = None) -> List[str]:
    selected = executable or shutil.which("pwsh") or shutil.which("powershell") or "pwsh"
    return [selected, "-NoProfile", "-NonInteractive", "-Command", script]
