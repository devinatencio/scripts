#!/usr/bin/env bash
# run_snapshot_cli.sh — Interactive snapshot CLI
#
# Usage:
#   ./run_snapshot_cli.sh list                       # list all snapshots
#   ./run_snapshot_cli.sh list "logs-gan-.*"         # filter by regex
#   ./run_snapshot_cli.sh list-restored              # show restored indices
#   ./run_snapshot_cli.sh list-history               # show last 50 history entries
#   ./run_snapshot_cli.sh ping                       # test ES connectivity
#   ./run_snapshot_cli.sh show-config                # display config
#   ./run_snapshot_cli.sh --locations PROD list      # use PROD server config
#   ./run_snapshot_cli.sh --password ping            # prompt for password
#   ./run_snapshot_cli.sh help                       # show help

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

exec "$PYTHON" -m server.snapshot_cli "$@"
