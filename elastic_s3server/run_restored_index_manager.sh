#!/usr/bin/env bash
# run_restored_index_manager.sh — Clean up aged restored indices
#
# Usage:
#   ./run_restored_index_manager.sh                          # standard run
#   ./run_restored_index_manager.sh --dry-run                # dry run
#   ./run_restored_index_manager.sh --max-days 7             # override max age
#   ./run_restored_index_manager.sh --server PROD            # use PROD config
#   ./run_restored_index_manager.sh --debug                  # verbose logging
#
# Cron example:
#   0 */6 * * * /path/to/run_restored_index_manager.sh >> /dev/null 2>&1

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

exec "$PYTHON" -m server.restored_index_manager "$@"
