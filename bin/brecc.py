#!/usr/bin/env python3
"""BRECC Python-first command line interface."""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.hermes import to_hermes_decision  # noqa: E402
from adapters.node import NodeAdapter  # noqa: E402
from adapters.posix import status as posix_status  # noqa: E402
from adapters.powershell import status as powershell_status  # noqa: E402
from core.catalog import catalog  # noqa: E402
from core.doctor import repository_status, runtime_status  # noqa: E402
from core.policy import inspect_command  # noqa: E402


def emit(value: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2))
    elif isinstance(value, dict):
        for key, item in value.items():
            print(f"{key}: {item}")
    else:
        print(value)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="brecc", description="Python-first BRECC compatibility bridge")
    subparsers = parser.add_subparsers(dest="action", required=True)

    analyze = subparsers.add_parser("analyze", help="inspect a command without executing it")
    source = analyze.add_mutually_exclusive_group(required=True)
    source.add_argument("command", nargs="?")
    source.add_argument("--file", type=Path)
    analyze.add_argument("--json", action="store_true")
    analyze.add_argument("--hermes", action="store_true", help="also emit the Hermes approval contract")

    catalog_parser = subparsers.add_parser("catalog", help="catalog ECC-compatible directories")
    catalog_parser.add_argument("root", nargs="?", default=".", type=Path)
    catalog_parser.add_argument("--json", action="store_true")

    doctor = subparsers.add_parser("doctor", help="report runtime and repository capabilities")
    doctor.add_argument("root", nargs="?", default=".", type=Path)
    doctor.add_argument("--json", action="store_true")

    adapters = subparsers.add_parser("adapters", help="report optional adapter capabilities")
    adapters.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.action == "analyze":
        try:
            command = args.file.read_text(encoding="utf-8") if args.file else args.command
        except OSError as error:
            parser.error(f"cannot read {args.file}: {error}")
        result = inspect_command(command)
        if args.hermes:
            result = {"analysis": result, "hermes": to_hermes_decision(result)}
        analysis = result["analysis"] if args.hermes else result
        decision = str(analysis["decision"])
        if args.json:
            emit(result, True)
        else:
            print(f"Decision: {decision.upper()}")
            if analysis["reasons"]:
                print("Reasons: " + "; ".join(analysis["reasons"]))
            print(f"Segments: {len(analysis['segments'])}")
        return 1 if decision == "deny" else 0
    if args.action == "catalog":
        emit(catalog(args.root), args.json)
        return 0
    if args.action == "doctor":
        result = {"runtime": runtime_status(), "repository": repository_status(args.root)}
        emit(result, args.json)
        return 0 if result["repository"]["healthy"] else 1
    emit({"node": NodeAdapter().status(), "powershell": powershell_status(), "posix": posix_status()}, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
