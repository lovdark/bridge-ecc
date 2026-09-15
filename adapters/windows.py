"""Windows adapter using PowerShell when available."""
from typing import Dict, List, Optional

from adapters.powershell import argv as powershell_argv
from adapters.powershell import status as powershell_status


def status() -> Dict[str, object]:
    result = powershell_status()
    result["platform_adapter"] = "windows-powershell"
    return result


def argv(script: str, executable: Optional[str] = None) -> List[str]:
    return powershell_argv(script, executable)
