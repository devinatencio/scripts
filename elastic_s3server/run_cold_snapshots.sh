#!/usr/bin/env bash
# run_cold_snapshots.sh — Create S3 snapshots for cold indices
#
# Usage:
#   ./run_cold_snapshots.sh                          # standard run
#   ./run_cold_snapshots.sh --noaction               # dry run
#   ./run_cold_snapshots.sh --pattern "logs-gan-.*"  # filter by regex
#   ./run_cold_snapshots.sh --debug                  # verbose logging
#
# Cron example:
#   0 */2 * * * /path/to/run_cold_snapshots.sh >> /dev/null 2>&1

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

exec "$PYTHON" -m server.cold_snapshots "$@"
