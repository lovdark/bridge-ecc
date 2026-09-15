"""Hook request adapter: analyze first, never execute."""
from typing import Any, Dict

from adapters.hermes import to_hermes_decision
from core.policy import inspect_command


def build_hook_request(event: str, command: str) -> Dict[str, Any]:
    analysis = inspect_command(command)
    return {"event": event, "analysis": analysis, "approval": to_hermes_decision(analysis), "execute": False}
