"""Small, dependency-free content transforms used by guarded apply."""
from typing import List

TOOL_NAMES = {"Read": "view_file", "Write": "write_to_file", "Edit": "replace_file_content", "Grep": "grep_search", "Glob": "find_by_name", "Bash": "run_command", "WebSearch": "search_web", "WebFetch": "read_url_content"}
MODEL_NAMES = {"haiku": "flash", "sonnet": "pro", "opus": "pro"}


def _tools(value: str) -> List[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    names = [part.strip().strip("'\"") for part in value.split(",")]
    return list(dict.fromkeys(TOOL_NAMES[name] for name in names if name in TOOL_NAMES))


def adapt_antigravity_agent(source: bytes, label: str = "<unknown>") -> bytes:
    text = source.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    if len(lines) < 3 or lines[0] != "---":
        raise ValueError(f"cannot adapt Antigravity agent {label}: missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError(f"cannot adapt Antigravity agent {label}: missing YAML frontmatter end") from error
    output = ["---"]
    for line in lines[1:end]:
        stripped = line.strip()
        if stripped.startswith("color:") and not line.startswith((" ", "\t")):
            continue
        if stripped.startswith("tools:") and not line.startswith((" ", "\t")):
            values = _tools(stripped.split(":", 1)[1])
            output.append("tools:")
            output.extend(f"  - {item}" for item in values)
            continue
        if stripped.startswith("model:") and not line.startswith((" ", "\t")):
            value = stripped.split(":", 1)[1].strip().strip("'\"")
            output.append(f"model: {MODEL_NAMES.get(value, value)}")
            continue
        output.append(line)
    output.append("---")
    output.extend(lines[end + 1:])
    return (newline.join(output) + (newline if text.endswith(("\n", "\r")) else "")).encode("utf-8")
