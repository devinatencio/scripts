#!/usr/bin/env bash
# Unified log viewer for all Elasticsearch utility logs.
# Usage: ./run_log_viewer.sh [options]
#   --tail N        Show last N lines per file (default: 50)
#   --level LEVEL   Minimum level: DEBUG|INFO|WARNING|ERROR|CRITICAL
#   --utility NAME  Filter to specific utility (repeatable)
#   --follow / -f   Live tail mode

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

exec "$PYTHON" -m server.log_viewer "$@"
