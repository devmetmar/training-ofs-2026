#!/usr/bin/env bash
# Wrapper: assign participants + clone/pull training-ofs-2026 into each workdir.
# Usage:
#   sudo ./scripts/sync-participant-workdirs.sh --dry-run
#   sudo ./scripts/sync-participant-workdirs.sh
#   sudo ./scripts/sync-participant-workdirs.sh --pull-only
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/sync_participant_workdirs.py" "$@"
