#!/usr/bin/env python3
"""BRECC command-line interface; Python standard library only."""
import argparse
import json
import sys
from typing import List, Optional

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.policy import inspect_command  # noqa: E402


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="brecc", description="Advisory BRECC command-safety analyzer")
    subparsers = parser.add_subparsers(dest="action", required=True)
    analyze = subparsers.add_parser("analyze")
    source = analyze.add_mutually_exclusive_group(required=True)
    source.add_argument("command", nargs="?")
    source.add_argument("--file", type=Path)
    analyze.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    command = args.file.read_text(encoding="utf-8") if args.file else args.command
    result = inspect_command(command)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Decision: {result['decision'].upper()}")
        if result["reasons"]:
            print("Reasons: " + "; ".join(result["reasons"]))
        print(f"Segments: {len(result['segments'])}")
    return 1 if result["decision"] == "deny" else 0


if __name__ == "__main__":
    raise SystemExit(main())
