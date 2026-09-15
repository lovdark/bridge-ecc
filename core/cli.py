#!/usr/bin/env python3
"""BRECC Python-first command line interface."""
import argparse
import json
from pathlib import Path
from typing import List, Optional

from adapters.hermes import to_hermes_decision
from adapters.node import NodeAdapter
from adapters.windows import status as windows_status
from adapters.posix import status as posix_status
from adapters.powershell import status as powershell_status
from core.catalog import catalog
from core.doctor import repository_status, runtime_status
from core.policy import inspect_command
from core.install_plan import build_install_plan
from core.validate import validate_tree


def emit(value: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2))
    elif isinstance(value, dict):
        for key, item in value.items():
            print(f"{key}: {item}")
    else:
        print(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brecc", description="Python-first BRECC compatibility bridge")
    subparsers = parser.add_subparsers(dest="action", required=True)
    analyze = subparsers.add_parser("analyze", help="inspect a command without executing it")
    source = analyze.add_mutually_exclusive_group(required=True)
    source.add_argument("command", nargs="?")
    source.add_argument("--file", type=Path)
    analyze.add_argument("--json", action="store_true")
    analyze.add_argument("--hermes", action="store_true", help="also emit the Hermes approval contract")
    for name, help_text in (("catalog", "catalog ECC-compatible directories"), ("doctor", "report runtime and repository capabilities"), ("validate", "validate ECC-compatible components")):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("root", nargs="?", default=".", type=Path)
        command.add_argument("--json", action="store_true")
    plan = subparsers.add_parser("plan", help="create a read-only component installation plan")
    plan.add_argument("source", type=Path)
    plan.add_argument("target", type=Path)
    plan.add_argument("--component", action="append", dest="components", help="limit to a component kind")
    plan.add_argument("--json", action="store_true")
    adapters = subparsers.add_parser("adapters", help="report optional adapter capabilities")
    adapters.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action == "analyze":
        try:
            command = args.file.read_text(encoding="utf-8") if args.file else args.command
        except OSError as error:
            parser.error(f"cannot read {args.file}: {error}")
        analysis = inspect_command(command)
        result = {"analysis": analysis, "hermes": to_hermes_decision(analysis)} if args.hermes else analysis
        selected = result["analysis"] if args.hermes else result
        if args.json:
            emit(result, True)
        else:
            print(f"Decision: {str(selected['decision']).upper()}")
            if selected["reasons"]:
                print("Reasons: " + "; ".join(selected["reasons"]))
            print(f"Segments: {len(selected['segments'])}")
        return 1 if selected["decision"] == "deny" else 0
    if args.action == "catalog":
        emit(catalog(args.root), args.json)
        return 0
    if args.action == "validate":
        result = validate_tree(args.root)
        emit(result, args.json)
        return 0 if result["valid"] else 1
    if args.action == "plan":
        result = build_install_plan(args.source, args.target, args.components)
        emit(result, args.json)
        return 0 if result["valid"] else 1
    if args.action == "doctor":
        result = {"runtime": runtime_status(), "repository": repository_status(args.root)}
        emit(result, args.json)
        return 0 if result["repository"]["healthy"] else 1
    emit({"node": NodeAdapter().status(), "powershell": powershell_status(), "windows": windows_status(), "posix": posix_status()}, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
