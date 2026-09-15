# PowerShell adapter

`adapters/powershell.py` reports PowerShell availability and builds `-NoProfile -NonInteractive -Command` argv lists without shell interpolation. `adapters/windows.py` exposes the same contract for Windows. Policy analysis remains in the Python core.
