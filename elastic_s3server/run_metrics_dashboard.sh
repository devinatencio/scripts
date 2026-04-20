#!/usr/bin/env bash
# run_metrics_dashboard.sh — Rich terminal metrics dashboard
#
# Usage:
#   ./run_metrics_dashboard.sh                                       # default metrics file
#   ./run_metrics_dashboard.sh --metrics-file /path/to/metrics.json  # custom path
#   ./run_metrics_dashboard.sh --history 7                           # weekly trends
#   ./run_metrics_dashboard.sh --watch                               # auto-refresh

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

exec "$PYTHON" -m server.metrics_dashboard "$@"
