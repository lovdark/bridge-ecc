#!/usr/bin/env bash
# Provision the generic BRECC repair helper for one supported target.
set -euo pipefail

usage() {
  printf '%s\n' 'Usage: install-target-repair.sh TARGET [--home-dir DIR] [--project-root DIR] [--target-root DIR] [--replace]'
}
TARGET_NAME="${1:-}"
[[ -n "$TARGET_NAME" ]] || { usage >&2; exit 2; }
shift
HOME_DIR="${BRECC_HOME_DIR:-$HOME}"
PROJECT_ROOT="${BRECC_PROJECT_ROOT:-$PWD}"
TARGET_ROOT="${BRECC_TARGET_ROOT:-}"
SOURCE="${BRECC_TARGET_REPAIR_SOURCE:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/brecc-target-repair.sh}"
REPLACE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --home-dir) HOME_DIR="${2:-}"; shift 2 ;;
    --project-root) PROJECT_ROOT="${2:-}"; shift 2 ;;
    --target-root) TARGET_ROOT="${2:-}"; shift 2 ;;
    --replace) REPLACE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done
[[ -f "$SOURCE" ]] || { printf 'ERROR: repair helper source not found: %s\n' "$SOURCE" >&2; exit 1; }

if [[ -z "$TARGET_ROOT" ]]; then
  case "$TARGET_NAME" in
    claude|codex|hermes|openclaw|qwen) TARGET_ROOT="$HOME_DIR/.${TARGET_NAME}" ;;
    opencode) TARGET_ROOT="$HOME_DIR/.config/opencode" ;;
    claude-project) TARGET_ROOT="$PROJECT_ROOT/.claude" ;;
    cursor) TARGET_ROOT="$PROJECT_ROOT/.cursor" ;;
    antigravity) TARGET_ROOT="$PROJECT_ROOT/.agents" ;;
    gemini) TARGET_ROOT="$PROJECT_ROOT/.gemini" ;;
    codebuddy) TARGET_ROOT="$PROJECT_ROOT/.codebuddy" ;;
    joycode) TARGET_ROOT="$PROJECT_ROOT/.joycode" ;;
    kimi) TARGET_ROOT="$PROJECT_ROOT/.kimi-code" ;;
    zed) TARGET_ROOT="$PROJECT_ROOT/.zed" ;;
    *) printf 'ERROR: unsupported BRECC target: %s\n' "$TARGET_NAME" >&2; exit 2 ;;
  esac
fi
[[ -d "$TARGET_ROOT" ]] || { printf 'ERROR: target directory does not exist: %s\n' "$TARGET_ROOT" >&2; exit 1; }
DEST_DIR="$TARGET_ROOT/.brecc"
DEST="$DEST_DIR/repair.sh"
mkdir -p "$DEST_DIR"
if [[ -e "$DEST" ]] && cmp -s "$SOURCE" "$DEST"; then
  chmod 755 "$DEST"
  printf 'repair_status=present\ntarget=%s\ntarget_root=%s\nrepair_script=%s\n' "$TARGET_NAME" "$TARGET_ROOT" "$DEST"
  exit 0
fi
if [[ -e "$DEST" && "$REPLACE" -ne 1 ]]; then
  printf 'ERROR: different repair helper already exists: %s\n' "$DEST" >&2
  printf '%s\n' 'Review it or rerun with --replace to explicitly update it.' >&2
  exit 3
fi
install -m 755 "$SOURCE" "$DEST"
printf 'repair_status=installed\ntarget=%s\ntarget_root=%s\nrepair_script=%s\n' "$TARGET_NAME" "$TARGET_ROOT" "$DEST"
