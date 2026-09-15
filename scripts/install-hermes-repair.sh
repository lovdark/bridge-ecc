#!/usr/bin/env bash
# Ensure the portable BRECC Hermes repair script exists for this installation.
set -euo pipefail

SOURCE="${BRECC_REPAIR_SOURCE:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/hermes-repair.sh}"
REPLACE=0
for arg in "$@"; do
  case "$arg" in
    --replace) REPLACE=1 ;;
    -h|--help)
      printf '%s\n' 'Usage: install-hermes-repair.sh [--replace]'
      printf '%s\n' 'Ensures the repair script exists in the discovered Hermes scripts directory.'
      exit 0
      ;;
    *) printf 'ERROR: unknown argument: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

[[ -f "$SOURCE" ]] || { printf 'ERROR: repair script source not found: %s\n' "$SOURCE" >&2; exit 1; }

if [[ -n "${BRECC_HERMES_ROOT:-}" ]]; then
  TARGET_ROOT="$BRECC_HERMES_ROOT"
else
  if ! TARGET_ROOT="$(python3 - <<'PY'
import os
import sys
from pathlib import Path
home = Path.home()
config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
candidates = [home / ".hermes", config / "hermes", config / "hermes-agent"]
markers = {"config.yaml", "skills", "state.db", "cron", "scripts"}
found = []
seen = set()
for path in candidates:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        continue
    if str(resolved) in seen or not resolved.is_dir():
        continue
    seen.add(str(resolved))
    if any((resolved / marker).exists() for marker in markers):
        found.append(resolved)
if len(found) == 1:
    print(found[0])
    raise SystemExit(0)
if not found:
    print("No Hermes directory was discovered. Set BRECC_HERMES_ROOT.", file=sys.stderr)
else:
    print("Multiple Hermes directories were discovered; set BRECC_HERMES_ROOT:", file=sys.stderr)
    for path in found:
        print(f"  {path}", file=sys.stderr)
raise SystemExit(2)
PY
  )"; then
    exit 2
  fi
fi

[[ -d "$TARGET_ROOT" ]] || { printf 'ERROR: Hermes target is not a directory: %s\n' "$TARGET_ROOT" >&2; exit 1; }
DEST_DIR="$TARGET_ROOT/scripts"
DEST="$DEST_DIR/hermes-repair.sh"
mkdir -p "$DEST_DIR"

if [[ -e "$DEST" ]]; then
  if cmp -s "$SOURCE" "$DEST"; then
    chmod 755 "$DEST"
    printf 'repair_script_status=present\nrepair_script=%s\n' "$DEST"
    exit 0
  fi
  if [[ "$REPLACE" -ne 1 ]]; then
    printf 'ERROR: a different repair script already exists: %s\n' "$DEST" >&2
    printf '%s\n' 'Review it or rerun with --replace to explicitly update it.' >&2
    exit 3
  fi
fi

install -m 755 "$SOURCE" "$DEST"
printf 'repair_script_status=installed\nrepair_script=%s\n' "$DEST"
