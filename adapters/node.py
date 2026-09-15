"""Optional Node.js bridge for ECC scripts that have no Python equivalent yet."""
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class NodeAdapter:
    def __init__(self, executable: Optional[str] = None):
        self.executable = shutil.which(executable) if executable else shutil.which("node")

    def status(self) -> Dict[str, object]:
        return {"available": bool(self.executable), "executable": self.executable, "mode": "optional-compatibility"}

    def run_script(self, script: Path, args: Optional[List[str]] = None, timeout: int = 30) -> Dict[str, object]:
        if not self.executable:
            return {"ok": False, "error": "Node.js is not installed; use the Python implementation or install Node for this adapter."}
        script = Path(script).expanduser().resolve()
        if not script.is_file():
            return {"ok": False, "error": "JavaScript script does not exist", "script": str(script)}
        command = [self.executable, str(script), *(args or [])]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Node script timed out", "script": str(script)}
        return {"ok": completed.returncode == 0, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "script": str(script)}
