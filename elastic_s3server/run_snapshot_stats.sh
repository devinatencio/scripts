#!/usr/bin/env bash
# run_snapshot_stats.sh — Collect snapshot status distribution for the dashboard
#
# Queries _cat/snapshots for the full status breakdown and writes it
# to the metrics database.  Runs independently so cold_snapshots and
# ilm_curator stay fast.
#
# Usage:
#   ./run_snapshot_stats.sh           # standard run
#   ./run_snapshot_stats.sh --debug   # verbose logging
#
# Cron example:
#   */30 * * * * /path/to/run_snapshot_stats.sh >> /dev/null 2>&1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-detect virtualenv: local venv first, then production path, then PATH
if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/venv/bin/python"
elif [ -f "/opt/s3server/venv/bin/python" ]; then
    PYTHON="/opt/s3server/venv/bin/python"
else
    PYTHON="$(command -v python3 || command -v python)"
fi

exec "$PYTHON" -m server.snapshot_stats "$@"
