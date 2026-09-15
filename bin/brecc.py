#!/usr/bin/env python3
"""Source-tree launcher for BRECC."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
