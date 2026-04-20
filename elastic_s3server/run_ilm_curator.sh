#!/usr/bin/env bash
# run_ilm_curator.sh — Delete cold indices with verified S3 snapshots
#
# Only deletes a cold index when a matching snapshot exists with
# SUCCESS status, 0 failed shards, and age >= 6 hours.
#
# Usage:
#   ./run_ilm_curator.sh              # standard run
#   ./run_ilm_curator.sh --noaction   # dry run — log what would be done
#   ./run_ilm_curator.sh --debug      # verbose logging
#
# Cron example:
#   0 * * * * /path/to/run_ilm_curator.sh >> /dev/null 2>&1

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

exec "$PYTHON" -m server.ilm_curator "$@"
