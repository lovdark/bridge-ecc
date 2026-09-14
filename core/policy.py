"""Portable, advisory command-safety policy for BRECC."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

DEFAULT_LIMITS = {"max_command_length": 8192, "max_segments": 200}

@dataclass(frozen=True)
class Rule:
    id: str
    pattern: re.Pattern[str]
    reason: str

DENY_RULES = (
    Rule("powershell-remove-force", re.compile(r"\b(remove-item|ri|del|erase)\b[^\r\n]*\s-(?:recurse|r)\b[^\r\n]*\s-(?:force|f)\b", re.I), "recursive forced deletion"),
    Rule("shell-rm-rf", re.compile(r"(^|[;&|])\s*rm\s+(?:-[^\s]+\s+)*-rf\b", re.I), "recursive forced deletion"),
    Rule("powershell-format", re.compile(r"\bformat-volume\b|\bformat\s+[a-z]:", re.I), "disk formatting"),
    Rule("powershell-shutdown", re.compile(r"\b(stop-computer|restart-computer|shutdown|reboot)\b", re.I), "system shutdown or restart"),
    Rule("git-destructive-reset", re.compile(r"\bgit\s+reset\s+--hard\b|\bgit\s+clean\s+-fd\b", re.I), "destructive git operation"),
    Rule("disk-wipe", re.compile(r"\b(dd\s+if=|diskpart\b|clear-disk\b|wipefs\b)", re.I), "disk or partition modification"),
)

REVIEW_RULES = (
    Rule("network-write", re.compile(r"\b(invoke-webrequest|invoke-restmethod|curl|wget|bitsadmin|scp|ftp)\b", re.I), "network access may transfer data"),
    Rule("permission-change", re.compile(r"\b(set-acl|icacls|chmod|chown|sudo)\b", re.I), "permission or privilege change"),
    Rule("process-control", re.compile(r"\b(stop-process|kill|taskkill|launchctl|systemctl)\b", re.I), "process or service control"),
    Rule("shell-evaluation", re.compile(r"\b(invoke-expression|iex|eval)\b|\$\([^)]*\)", re.I), "dynamic command evaluation"),
)


def split_segments(command: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?:\r?\n|&&|\|\||(?<!\|)\|(?!\|)|;)", command) if part.strip()]


def inspect_command(command: Any, **limits: int) -> dict[str, Any]:
    configured = {**DEFAULT_LIMITS, **limits}
    if not isinstance(command, str) or not command.strip():
        return {"decision": "review", "reasons": ["command must be a non-empty string"], "findings": [], "segments": []}
    if len(command) > configured["max_command_length"]:
        return {"decision": "deny", "reasons": ["analysis budget exceeded: command is too long"], "findings": [], "segments": []}
    segments = split_segments(command)
    if len(segments) > configured["max_segments"]:
        return {"decision": "deny", "reasons": ["analysis budget exceeded: too many command segments"], "findings": [], "segments": []}
    findings: list[dict[str, str]] = []
    for segment in segments:
        for rule in DENY_RULES:
            if rule.pattern.search(segment):
                findings.append({"id": rule.id, "reason": rule.reason, "decision": "deny", "segment": segment})
        for rule in REVIEW_RULES:
            if rule.pattern.search(segment):
                findings.append({"id": rule.id, "reason": rule.reason, "decision": "review", "segment": segment})
    decision = "deny" if any(item["decision"] == "deny" for item in findings) else "review" if findings else "allow"
    reasons = list(dict.fromkeys(item["reason"] for item in findings))
    return {"decision": decision, "reasons": reasons, "findings": findings, "segments": segments}
