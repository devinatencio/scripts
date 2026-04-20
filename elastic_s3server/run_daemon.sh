#!/usr/bin/env bash
# Start the master daemon scheduler.
# Replaces individual cron jobs with a single long-running process.
#
# Usage:
#   ./run_daemon.sh                  # foreground
#   ./run_daemon.sh --debug          # verbose logging
#   ./run_daemon.sh --dry-run        # dry-run mode
#   nohup ./run_daemon.sh &          # background with nohup

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Auto-detect virtualenv: local venv first, then production path, then PATH
if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/venv/bin/python"
elif [ -f "/opt/s3server/venv/bin/python" ]; then
    PYTHON="/opt/s3server/venv/bin/python"
else
    PYTHON="$(command -v python3 || command -v python)"
fi

"$PYTHON" -m server.daemon "$@"
