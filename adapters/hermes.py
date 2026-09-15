"""Translate BRECC policy results into a stable Hermes approval contract."""
from typing import Any, Dict


def to_hermes_decision(result: Dict[str, Any]) -> Dict[str, Any]:
    decision = result.get("decision", "deny")
    return {
        "decision": decision if decision in {"allow", "review", "deny"} else "deny",
        "requires_approval": decision == "review",
        "blocked": decision == "deny",
        "reasons": list(result.get("reasons", [])),
        "source": "brecc-python-policy",
    }
