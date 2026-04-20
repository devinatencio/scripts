#!/usr/bin/env bash
# run_retention_enforcer.sh — Purge old snapshots by retention policy
#
# Usage:
#   ./run_retention_enforcer.sh                      # standard run
#   ./run_retention_enforcer.sh --noaction            # dry run
#   ./run_retention_enforcer.sh --days 60             # override default retention
#   ./run_retention_enforcer.sh --pattern "snap_.*"   # filter by regex
#   ./run_retention_enforcer.sh --debug               # verbose logging
#
# Cron example:
#   0 3 * * * /path/to/run_retention_enforcer.sh >> /dev/null 2>&1

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

exec "$PYTHON" -m server.retention_enforcer "$@"
