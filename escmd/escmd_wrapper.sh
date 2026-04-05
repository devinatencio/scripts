#!/bin/bash
cd /opt/escmd
source venv/bin/activate
exec python3 escmd.py "$@"

