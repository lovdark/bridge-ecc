#!/usr/bin/env bash
# Fail-closed Hermes repair and recovery wrapper for BRECC.
set -euo pipefail

TARGET_ROOT="${BRECC_HERMES_ROOT:-/root/.hermes}"
BACKUP_ROOT="${BRECC_BACKUP_ROOT:-/root/backups}"
ECC_ROOT="${BRECC_ECC_ROOT:-/tmp/ecc-latest}"
PROFILE="${BRECC_PROFILE:-developer}"
TARGET="${BRECC_TARGET:-hermes}"

usage() {
  cat <<'EOF'
Usage:
  hermes-repair.sh diagnose
  hermes-repair.sh backup
  hermes-repair.sh plan [--json]
  hermes-repair.sh apply PLAN_SHA256
  hermes-repair.sh restore BACKUP_ARCHIVE CONFIRM_RESTORE

Environment overrides:
  BRECC_HERMES_ROOT  (default: /root/.hermes)
  BRECC_BACKUP_ROOT  (default: /root/backups)
  BRECC_ECC_ROOT     (default: /tmp/ecc-latest)
  BRECC_PROFILE      (default: developer)
  BRECC_TARGET       (default: hermes)

Safety:
  diagnose and plan never write target files.
  apply requires a plan hash and creates a sanitized local backup first.
  restore requires CONFIRM_RESTORE=RESTORE-HERMES and quarantines the
  current target before extracting the archive.
  This script never uploads to Google Drive and never handles credentials.
EOF
}

fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }

require_target() { [[ -d "$TARGET_ROOT" ]] || fail "Hermes target is not a directory: $TARGET_ROOT"; }
require_source() { [[ -d "$ECC_ROOT" ]] || fail "ECC source is not a directory: $ECC_ROOT"; }

archive_name() { printf '%s/batz-hermes-repair-%s.tar.gz' "$BACKUP_ROOT" "$(date -u +%Y%m%dT%H%M%SZ)"; }

backup() {
  require_target
  mkdir -p "$BACKUP_ROOT"
  local archive
  archive="$(archive_name)"
  [[ ! -e "$archive" ]] || fail "backup destination already exists: $archive"
  tar -C "$(dirname "$TARGET_ROOT")" --exclude='.hermes/.env' --exclude='.hermes/auth.json' \
    --exclude='.hermes/shared/nous_auth.json' --exclude='.hermes/*.log' \
    --exclude='.hermes/**/__pycache__' -czf "$archive" "$(basename "$TARGET_ROOT")"
  sha256sum "$archive" | tee "$archive.sha256"
  gzip -t "$archive"
  printf 'backup_archive=%s\n' "$archive"
  printf 'backup_manifest=%s\n' "$archive.sha256"
}

diagnose() {
  require_target
  printf 'target_root=%s\n' "$TARGET_ROOT"
  printf 'target_owner=%s\n' "$(stat -c '%U:%G' "$TARGET_ROOT")"
  printf 'target_mode=%s\n' "$(stat -c '%a' "$TARGET_ROOT")"
  printf 'file_count=%s\n' "$(find "$TARGET_ROOT" -type f | wc -l)"
  printf 'directory_count=%s\n' "$(find "$TARGET_ROOT" -type d | wc -l)"
  printf 'brecc_state=%s\n' "$( [[ -f "$TARGET_ROOT/.brecc-state.json" ]] && printf present || printf absent )"
  printf 'ecc_state=%s\n' "$( [[ -f "$TARGET_ROOT/ecc-install-state.json" ]] && printf present || printf absent )"
  printf 'backup_root=%s\n' "$BACKUP_ROOT"
}

plan() {
  require_source
  local args=("$ECC_ROOT" "$PROFILE" --target "$TARGET" --home-dir "${TARGET_ROOT%/.hermes}" --project-root /root/projects)
  [[ "${1:-}" == '--json' ]] && args+=(--json)
  python3 -m brecc ecc-plan "${args[@]}"
}

apply_plan() {
  require_source
  [[ "${1:-}" =~ ^[0-9a-f]{64}$ ]] || fail 'apply requires a 64-character hexadecimal plan hash'
  backup
  python3 -m brecc apply-plan "$ECC_ROOT" "$PROFILE" --target "$TARGET" \
    --home-dir "${TARGET_ROOT%/.hermes}" --project-root /root/projects \
    --allow-writes --confirm-plan "$1" --json
}

restore() {
  require_target
  local archive="${1:-}" confirmation="${2:-}"
  [[ -f "$archive" ]] || fail "backup archive not found: $archive"
  [[ "$confirmation" == 'RESTORE-HERMES' ]] || fail 'restore requires confirmation RESTORE-HERMES'
  gzip -t "$archive"
  local listing
  listing="$(tar -tzf "$archive")"
  printf '%s\n' "$listing" | grep -Fxq "$(basename "$TARGET_ROOT")/" || fail 'archive layout is not recognized'
  if printf '%s\n' "$listing" | grep -Eq '(^|/)\.\./|^/' ; then
    fail 'archive contains unsafe traversal paths'
  fi
  local quarantine="${TARGET_ROOT}.before-repair-$(date -u +%Y%m%dT%H%M%SZ)"
  [[ ! -e "$quarantine" ]] || fail "quarantine destination already exists: $quarantine"
  mv "$TARGET_ROOT" "$quarantine"
  mkdir -p "$(dirname "$TARGET_ROOT")"
  mkdir "$TARGET_ROOT"
  if ! tar -xzf "$archive" -C "$(dirname "$TARGET_ROOT")"; then
    rm -rf "$TARGET_ROOT"
    mv "$quarantine" "$TARGET_ROOT"
    fail 'restore extraction failed; original target was restored'
  fi
  printf 'restored_target=%s\n' "$TARGET_ROOT"
  printf 'quarantine=%s\n' "$quarantine"
}

command="${1:-diagnose}"
case "$command" in
  diagnose) diagnose ;;
  backup) backup ;;
  plan) shift; plan "${1:-}" ;;
  apply) shift; apply_plan "${1:-}" ;;
  restore) shift; restore "${1:-}" "${2:-}" ;;
  -h|--help|help) usage ;;
  *) usage; fail "unknown command: $command" ;;
esac
