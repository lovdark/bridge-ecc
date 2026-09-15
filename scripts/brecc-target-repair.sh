#!/usr/bin/env bash
# Portable repair and recovery helper for one BRECC target installation.
set -euo pipefail

TARGET_NAME="${BRECC_TARGET_NAME:-unknown}"
TARGET_ROOT="${BRECC_TARGET_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKUP_ROOT="${BRECC_BACKUP_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/brecc/backups/${TARGET_NAME}}"

usage() {
  printf '%s\n' \
    'Usage: repair.sh diagnose|backup|restore ARCHIVE CONFIRM_RESTORE' \
    'Environment: BRECC_TARGET_NAME, BRECC_TARGET_ROOT, BRECC_BACKUP_ROOT'
}
fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }
require_target() { [[ -d "$TARGET_ROOT" ]] || fail "target is not a directory: $TARGET_ROOT"; }
archive_name() { printf '%s/brecc-%s-repair-%s.tar.gz' "$BACKUP_ROOT" "$TARGET_NAME" "$(date -u +%Y%m%dT%H%M%SZ)"; }

diagnose() {
  require_target
  printf 'target=%s\n' "$TARGET_NAME"
  printf 'target_root=%s\n' "$TARGET_ROOT"
  printf 'target_mode=%s\n' "$(stat -c '%a' "$TARGET_ROOT")"
  printf 'file_count=%s\n' "$(find "$TARGET_ROOT" -type f | wc -l)"
  printf 'directory_count=%s\n' "$(find "$TARGET_ROOT" -type d | wc -l)"
  printf 'repair_state=%s\n' "$( [[ -f "$TARGET_ROOT/.brecc/repair-state.json" ]] && printf present || printf absent )"
  printf 'backup_root=%s\n' "$BACKUP_ROOT"
}

backup() {
  require_target
  mkdir -p "$BACKUP_ROOT"
  local archive
  archive="$(archive_name)"
  [[ ! -e "$archive" ]] || fail "backup destination already exists: $archive"
  tar -C "$(dirname "$TARGET_ROOT")" \
    --exclude="$(basename "$TARGET_ROOT")/.env" \
    --exclude="$(basename "$TARGET_ROOT")/auth.json" \
    --exclude="$(basename "$TARGET_ROOT")/logs" \
    --exclude="$(basename "$TARGET_ROOT")/cache" \
    --exclude="$(basename "$TARGET_ROOT")/**/__pycache__" \
    -czf "$archive" "$(basename "$TARGET_ROOT")"
  sha256sum "$archive" | tee "$archive.sha256"
  gzip -t "$archive"
  printf 'backup_archive=%s\nbackup_manifest=%s\n' "$archive" "$archive.sha256"
}

restore() {
  require_target
  local archive="${1:-}" confirmation="${2:-}"
  [[ -f "$archive" ]] || fail "backup archive not found: $archive"
  [[ "$confirmation" == 'RESTORE-BRECC-TARGET' ]] || fail 'restore requires confirmation RESTORE-BRECC-TARGET'
  gzip -t "$archive"
  local root_name listing
  root_name="$(basename "$TARGET_ROOT")"
  listing="$(tar -tzf "$archive")"
  printf '%s\n' "$listing" | grep -Fxq "$root_name/" || fail 'archive layout is not recognized'
  if printf '%s\n' "$listing" | grep -Eq '(^|/)\.\./|^/'; then fail 'archive contains unsafe traversal paths'; fi
  local quarantine="${TARGET_ROOT}.before-brecc-repair-$(date -u +%Y%m%dT%H%M%SZ)"
  [[ ! -e "$quarantine" ]] || fail "quarantine destination already exists: $quarantine"
  mv "$TARGET_ROOT" "$quarantine"
  if ! tar -xzf "$archive" -C "$(dirname "$TARGET_ROOT")"; then
    rm -rf "$TARGET_ROOT"
    mv "$quarantine" "$TARGET_ROOT"
    fail 'restore extraction failed; original target was restored'
  fi
  printf 'restored_target=%s\nquarantine=%s\n' "$TARGET_ROOT" "$quarantine"
}

case "${1:-diagnose}" in
  diagnose) diagnose ;;
  backup) backup ;;
  restore) restore "${2:-}" "${3:-}" ;;
  -h|--help|help) usage ;;
  *) usage; fail "unknown command: ${1:-}" ;;
esac
