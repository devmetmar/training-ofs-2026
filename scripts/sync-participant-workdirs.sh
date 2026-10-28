#!/usr/bin/env bash
# Admin wrapper (branch `admin` only). Syncs participant-facing branch `main`
# into each workdir — safe even when this mirror is checked out on `admin`.
#
# Usage:
#   sudo ./scripts/sync-participant-workdirs.sh --dry-run
#   sudo ./scripts/sync-participant-workdirs.sh --pull-only --force
#   sudo ./scripts/sync-participant-workdirs.sh -w 'john-doe' --pull-only --force
#   sudo ./scripts/sync-participant-workdirs.sh --env-only
#   sudo ./scripts/sync-participant-workdirs.sh --clear-outputs-only
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/sync_participant_workdirs.py" "$@"
