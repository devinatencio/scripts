# server — Elasticsearch S3 Snapshot Management System v2.1

A modular Python package for managing the full Elasticsearch S3 snapshot lifecycle: creating snapshots of cold indices, enforcing retention policies, cleaning up restored indices, curating ILM-driven deletions, collecting operational metrics, and providing a CLI and Rich terminal dashboard.

## Version

The current version is defined in `server/__init__.py` and logged at startup by every utility and the daemon.

| Version | Date | Summary |
|---------|------|---------|
| 2.1.0 | 2026-04-19 | Daemon `dry_run` config option, ILM curator `--noaction`, version logging |
| 2.0.0 | — | Initial modular rewrite (daemon, metrics, Rich dashboard, tests) |

## Project Layout

```
project_root/
├── run_cold_snapshots.sh            # Shell wrapper for cron
├── run_retention_enforcer.sh        # Shell wrapper for cron
├── run_restored_index_manager.sh    # Shell wrapper for cron
├── run_ilm_curator.sh               # Shell wrapper for cron
├── run_snapshot_cli.sh              # Shell wrapper for interactive CLI
├── run_metrics_dashboard.sh         # Shell wrapper for metrics dashboard
├── run_log_viewer.sh               # Shell wrapper for unified log viewer
├── run_daemon.sh                    # Shell wrapper for daemon mode
├── elastic_servers.yml              # Server config
├── elastic_retention.yml            # Retention config
├── daemon_config.yml                # Daemon scheduler config
├── logs/                            # Auto-created log files (at project root)
│
├── server/
│   ├── __init__.py                  # Package init + __version__
│   ├── config_loader.py             # YAML config reading, validation, defaults
│   ├── es_client.py                 # Elasticsearch client wrapper with retry logic
│   ├── log_manager.py               # Per-utility logging with file rotation
│   ├── metrics_collector.py         # JSON metrics read/write with atomic updates
│   ├── daemon.py                    # Master scheduler daemon (replaces cron)
│   ├── cold_snapshots.py            # Utility: snapshot cold indices to S3
│   ├── retention_enforcer.py        # Utility: purge old snapshots by retention policy
│   ├── restored_index_manager.py    # Utility: clean up aged restored indices
│   ├── ilm_curator.py               # Utility: delete cold indices with verified snapshots
│   ├── snapshot_cli.py              # Interactive CLI for snapshot operations
│   ├── metrics_dashboard.py         # Rich terminal dashboard for metrics
│   ├── log_viewer.py               # Unified Rich log viewer for all utilities
│   ├── requirements.txt             # Python dependencies
│   ├── metrics/                     # Auto-created metrics SQLite database
│   └── tests/                       # Unit + property-based tests
│
├── contrib/
│   └── systemd/                     # systemd unit file for production daemon
│       ├── es-daemon.service
│       ├── es-daemon.env
│       └── README.md
│
└── server_v1/                       # Legacy v1 code (preserved)
```

## Prerequisites

- Python 3.6+ (tested with 3.12.8)
- Elasticsearch 7.x cluster (tested with 7.17.12)
- An S3 snapshot repository configured in Elasticsearch

## Installation

```bash
cd server
pip install -r requirements.txt
```

## Configuration

### Server Configuration — `elastic_servers.yml`

Place this file in the `server/` directory or the current working directory. The config loader searches both locations.

```yaml
settings:
  elastic_clustername: my-cluster
  elastic_default_timeout: 300
  elastic_restored_indice: rc_snapshots
  elastic_history_indice: rc_snapshots_history
  elastic_restored_maxdays: 3
  elastic_restore_batch_size: 3
  elastic_max_shards_per_node: 1000
  default_retention_maxdays: 30

servers:
  - name: DEFAULT
    hostname: 10.0.0.1
    port: 9200
    use_ssl: true
    repository: my-s3-repo
    elastic_authentication: false
    elastic_username: null
    elastic_password: null

  - name: PROD
    hostname: prod-es.example.com
    port: 9200
    use_ssl: true
    repository: prod-s3-repo
    elastic_authentication: true
    elastic_username: admin
    elastic_password: secret
```

Required fields per server: `hostname`, `port`, `repository`. Everything else has defaults.

### Retention Configuration — `elastic_retention.yml`

Optional. Defines per-pattern retention overrides. Snapshots not matching any pattern use `default_retention_maxdays` from the server config.

```yaml
retention:
  - name: Retention for logs-gan
    pattern: .*logs-gan-.*
    max_days: 90
  - name: Retention for logs-gas
    pattern: .*logs-gas-.*
    max_days: 90
```

Patterns are matched against the index name (with the `snapshot_` prefix stripped).

### Daemon Configuration — `daemon_config.yml`

Controls the master daemon scheduler. Each task maps to an existing utility module and defines when and how often it runs.

```yaml
# Set to true to run all tasks in dry-run / no-action mode.
# Tasks will log what they *would* do without making any changes.
dry_run: false

tasks:
  cold_snapshots:
    enabled: true
    schedule_type: interval        # run every N minutes
    interval_minutes: 30
    jitter_minutes: 5              # random delay 0-5m before each run
    description: "Snapshot cold indices to S3"

  ilm_curator:
    enabled: true
    schedule_type: window          # run only within a daily time window
    interval_minutes: 60
    window_start: "00:00"
    window_end: "05:00"
    jitter_minutes: 10
    description: "Delete cold indices with verified snapshots"

  retention_enforcer:
    enabled: true
    schedule_type: window
    interval_minutes: 120
    window_start: "01:00"
    window_end: "04:00"
    jitter_minutes: 15
    description: "Purge old snapshots by retention policy"

  restored_index_manager:
    enabled: true
    schedule_type: interval
    interval_minutes: 360
    jitter_minutes: 10
    description: "Clean up aged restored indices"
```

| Field | Description |
|-------|-------------|
| `dry_run` | **Global.** When `true`, every task runs in dry-run mode — connects to ES, queries data, evaluates what it *would* do, and logs the decisions, but never mutates Elasticsearch state and never updates metrics counters. Defaults to `false`. |
| `enabled` | `true`/`false` to toggle the task |
| `schedule_type` | `interval` (fixed period) or `window` (time-of-day restricted) |
| `interval_minutes` | How often to run (applies to both schedule types) |
| `window_start` / `window_end` | 24-hour `HH:MM` bounds (window type only). Overnight windows like `23:00`–`03:00` are supported |
| `jitter_minutes` | Random delay added before each run to prevent thundering herd (0 = exact) |
| `description` | Human-readable note (informational only) |

### Dry-Run Mode

Dry-run mode lets you validate the daemon's behaviour against a live cluster without making any destructive changes. It is the recommended first step when deploying to a new environment or after changing configuration.

There are two ways to enable it:

1. **Config file** — set `dry_run: true` in `daemon_config.yml`. This is the preferred approach for production validation because it persists across restarts and is visible in version control.

2. **CLI flag** — pass `--dry-run` when starting the daemon. The CLI flag takes precedence over the config file (i.e. `--dry-run` enables dry-run even if the config says `false`).

When dry-run is active:

- The daemon logs `DRY-RUN mode enabled` at startup.
- Each task is dispatched normally (including jitter delays) so you see realistic scheduling behaviour.
- Each task connects to Elasticsearch, queries indices/snapshots/ILM data, and evaluates what actions it would take — all of this is logged.
- **No state-modifying operations are performed**: no snapshots are created, no indices are deleted, no snapshots are purged.
- **No metrics counters are updated** (`snapshots_created`, `snapshots_deleted`, `indices_deleted_ilm`). Health status is still recorded so the dashboard shows the task ran.

The per-task dry-run flags used internally:

| Task | Flag injected by daemon |
|------|------------------------|
| `cold_snapshots` | `--noaction` |
| `ilm_curator` | `--noaction` |
| `retention_enforcer` | `--noaction` |
| `restored_index_manager` | `--dry-run` |

You can also run any utility standalone with its dry-run flag for one-off validation — see the individual utility sections below.

## Running the Utilities

All scripts are run as Python modules from the parent directory of `server/`. Every utility logs its version at startup (e.g. `Cold-snapshots v2.1.0 starting...`).

### Daemon Mode — Master scheduler (replaces cron)

A single long-running process that replaces individual cron jobs. The daemon ticks every 30 seconds, checks each task's schedule, and dispatches due tasks in background threads with configurable jitter. It writes a heartbeat to the metrics file every tick so the metrics dashboard can show live daemon status.

```bash
# Foreground (Ctrl+C to stop)
python -m server.daemon

# Custom config file
python -m server.daemon --config /path/to/daemon_config.yml

# Verbose logging
python -m server.daemon --debug

# Dry run via CLI flag — tasks go through the motions without acting
python -m server.daemon --dry-run

# Background with nohup
nohup ./run_daemon.sh &
```

| Flag | Description |
|------|-------------|
| `--config` / `-c` | Path to `daemon_config.yml` (default: searches `server/` and cwd) |
| `--debug` | Enable DEBUG-level logging |
| `--dry-run` | Run all tasks in dry-run mode (overrides config file) |

The daemon handles `SIGINT` and `SIGTERM` for clean shutdown. It waits for in-flight tasks to finish before exiting.

For production deployments, a systemd unit file is provided in `contrib/systemd/`. See `contrib/systemd/README.md` for installation instructions. Key features of the unit:

- Automatic restart on failure (30s delay, max 5 attempts per 5 minutes)
- Runs as a dedicated `elastic` user with filesystem hardening (`ProtectSystem=strict`, `NoNewPrivileges`, `PrivateTmp`)
- Logs to journald (`journalctl -u es-daemon -f`)

### Cold Snapshots — Create S3 backups of cold indices

Detects indices in the cold ILM phase that don't have a corresponding snapshot and creates one.

```bash
# Standard run
python -m server.cold_snapshots

# Dry run — report what would be done without creating snapshots
python -m server.cold_snapshots --noaction

# Filter to specific indices by regex
python -m server.cold_snapshots --pattern "logs-gan-.*"

# Override the S3 repository
python -m server.cold_snapshots --repository my-other-repo

# Verbose logging
python -m server.cold_snapshots --debug
```

| Flag | Description |
|------|-------------|
| `--debug` | Enable DEBUG-level logging |
| `--pattern REGEX` | Only process cold indices matching this regex |
| `--noaction` | Dry run — log what would happen, don't create snapshots. Metrics counters are not updated. |
| `--repository NAME` | Override the configured S3 repository |

### Retention Enforcer — Purge old snapshots

Evaluates each snapshot against retention policies and deletes those exceeding their retention period.

```bash
# Standard run
python -m server.retention_enforcer

# Dry run
python -m server.retention_enforcer --noaction

# Override default retention to 60 days
python -m server.retention_enforcer --days 60

# Only process snapshots matching a pattern
python -m server.retention_enforcer --pattern "snapshot_logs-.*"

# Override repository
python -m server.retention_enforcer --repository my-other-repo

# Verbose logging
python -m server.retention_enforcer --debug
```

| Flag | Description |
|------|-------------|
| `--debug` | Enable DEBUG-level logging |
| `--days N` | Override default retention period (days) |
| `--pattern REGEX` | Only process snapshots matching this regex |
| `--noaction` | Dry run — log what would be deleted, don't delete. Metrics counters are not updated. |
| `--repository NAME` | Override the configured S3 repository |

### ILM Curator — Delete cold indices with verified snapshots

Safety gate for ILM-driven index removal. Only deletes a cold index when a matching snapshot exists with SUCCESS status, 0 failed shards, and is older than the configured delay (default 6 hours).

```bash
# Standard run
python -m server.ilm_curator

# Dry run — report what would be deleted without acting
python -m server.ilm_curator --noaction

# Verbose logging
python -m server.ilm_curator --debug
```

| Flag | Description |
|------|-------------|
| `--debug` | Enable DEBUG-level logging |
| `--noaction` | Dry run — log indices that would be deleted, don't delete. Metrics counters are not updated. |

### Restored Index Manager — Clean up aged restores

Queries the tracking index for restored indices and deletes those exceeding the max age. Also removes stale records where the index no longer exists.

```bash
# Standard run
python -m server.restored_index_manager

# Select a different server config
python -m server.restored_index_manager --server PROD

# Override max age to 7 days
python -m server.restored_index_manager --max-days 7

# Dry run
python -m server.restored_index_manager --dry-run

# Custom config file path
python -m server.restored_index_manager --config-file /path/to/elastic_servers.yml

# Verbose logging
python -m server.restored_index_manager --debug
```

| Flag | Description |
|------|-------------|
| `--debug` | Enable DEBUG-level logging |
| `--server NAME` | Server name from config (default: DEFAULT) |
| `--max-days N` | Override max age for restored indices (days) |
| `--dry-run` | Log actions without performing deletions |
| `--config-file PATH` | Path to a specific config YAML file |

### Snapshot CLI — Interactive snapshot operations

Command-line tool for listing snapshots, viewing restore history, and checking cluster connectivity.

```bash
# List all snapshots
python -m server.snapshot_cli list

# List snapshots matching a regex
python -m server.snapshot_cli list "logs-gan-.*"

# List with snapshot sizes
python -m server.snapshot_cli --size list

# View restored index records
python -m server.snapshot_cli list-restored

# View last 50 history entries
python -m server.snapshot_cli list-history

# Test cluster connectivity
python -m server.snapshot_cli ping

# Show current configuration
python -m server.snapshot_cli show-config

# Use a different server config
python -m server.snapshot_cli --locations PROD list

# Prompt for password interactively
python -m server.snapshot_cli --password ping

# Show help
python -m server.snapshot_cli help
```

| Command | Description |
|---------|-------------|
| `list [REGEX]` | List snapshots, optionally filtered by regex |
| `list-restored` | Show restored index tracking records |
| `list-history` | Show last 50 restore history entries |
| `clear-staged` | Clear staged snapshot entries |
| `show-config` | Display current configuration |
| `ping` | Test Elasticsearch connectivity and show cluster health |
| `help` | Show available commands |

| Flag | Description |
|------|-------------|
| `--locations NAME` | Server config name (default: DEFAULT) |
| `--password` | Prompt for ES password interactively |
| `--size` | Include snapshot sizes in list output |

### Metrics Dashboard — Terminal metrics visualization

Rich terminal dashboard showing operational metrics at a glance. The live view displays four sections: daemon status (running/stopped/stale with per-task breakdown), daily counters scoreboard, utility health table with color-coded time-ago indicators, and snapshot status distribution with proportional gradient bar charts.

The history mode renders trend tables for the past 7, 30, or 90 days with sparklines, gradient bars, trend arrows, and highlighted min/max rows.

```bash
# Live dashboard (default)
python -m server.metrics_dashboard

# Historical trends — last 7 days
python -m server.metrics_dashboard --history 7

# Historical trends — last 30 days
python -m server.metrics_dashboard --history 30

# Historical trends — last 90 days
python -m server.metrics_dashboard --history 90

# Custom metrics file
python -m server.metrics_dashboard --metrics-file /path/to/snapshot_metrics.json
```

| Flag | Description |
|------|-------------|
| `--metrics-file PATH` | Path to metrics file (default: `server/metrics/snapshot_metrics.json`; actual storage uses a `.db` sibling) |
| `--history DAYS` | Show historical trends instead of live view. Choices: `7`, `30`, `90` |

Live dashboard sections:

| Section | What it shows |
|---------|---------------|
| Daemon | Running/Stopped/Stale status, PID, heartbeat age, per-task state |
| Daily Counters | Snapshots created, snapshots deleted, ILM indices deleted (today) |
| Utility Health | Last run time, time-ago, success/fail status per utility |
| Snapshot Status | SUCCESS/FAILED/PARTIAL/IN_PROGRESS/INCOMPATIBLE counts with gradient bars |

History mode sections:

| Section | What it shows |
|---------|---------------|
| Scoreboard | Total, daily average, peak, sparkline, and trend arrow per counter |
| Trend Tables | Per-day breakdown with day-of-week, gradient bar, percentage, highlighted min/max rows |

### Log Viewer — Unified Rich log viewer

Merges and color-codes log output from all utilities into a single chronological view. Each utility gets its own color for easy visual separation. Supports filtering by log level, utility name, and a live-tail mode.

```bash
# Show last 50 lines from all logs (default)
python -m server.log_viewer

# Show last 100 lines per file
python -m server.log_viewer --tail 100

# Only show ERROR and above
python -m server.log_viewer --level ERROR

# Filter to specific utilities (repeatable)
python -m server.log_viewer --utility daemon --utility ilm-curator

# Live tail — streams new lines from all logs in real time
python -m server.log_viewer --follow

# Combine filters with live tail
python -m server.log_viewer --follow --level WARNING --utility cold-snapshots
```

| Flag | Description |
|------|-------------|
| `--tail N` | Number of recent lines to read per log file (default: 50) |
| `--level LEVEL` | Minimum log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `--utility NAME` | Show only specific utility (repeatable). Available: `cold-snapshots`, `retention-enforcer`, `restored-index-manager`, `ilm-curator`, `snapshot-cli`, `daemon` |
| `--follow` / `-f` | Live-tail mode — streams new lines as they are written |
| `--logs-dir PATH` | Override the logs directory path |

The viewer displays a summary panel at the top showing each discovered log file with its size and last-modified timestamp, followed by a merged chronological table of all matching entries.

## Shell Scripts

Dedicated shell scripts live at the project root for easy cron integration. Each script `cd`s to the project directory automatically, so cron can call them with absolute paths. All CLI flags pass through.

| Script | Purpose | Suggested Schedule |
|--------|---------|-------------------|
| `run_cold_snapshots.sh` | Snapshot cold indices to S3 | Every 2 hours |
| `run_retention_enforcer.sh` | Purge old snapshots by retention policy | Daily at 3 AM |
| `run_restored_index_manager.sh` | Clean up aged restored indices | Every 6 hours |
| `run_ilm_curator.sh` | Delete cold indices with verified snapshots | Every hour |
| `run_snapshot_cli.sh` | Interactive snapshot CLI | Manual use |
| `run_metrics_dashboard.sh` | Terminal metrics dashboard | Manual use |
| `run_log_viewer.sh` | Unified Rich log viewer | Manual use |
| `run_daemon.sh` | Master daemon scheduler | Long-running / systemd |

### Usage Examples

```bash
# Run cold snapshots with dry run
./run_cold_snapshots.sh --noaction

# Run retention enforcer with custom retention and debug logging
./run_retention_enforcer.sh --days 60 --debug

# Run restored index manager against PROD server
./run_restored_index_manager.sh --server PROD --dry-run

# Run ILM curator in dry-run mode
./run_ilm_curator.sh --noaction

# Use the snapshot CLI
./run_snapshot_cli.sh list "logs-gan-.*"
./run_snapshot_cli.sh ping
./run_snapshot_cli.sh --locations PROD list

# View the metrics dashboard
./run_metrics_dashboard.sh

# View merged logs from all utilities
./run_log_viewer.sh

# Live tail with level filter
./run_log_viewer.sh --follow --level WARNING

# Start the daemon in foreground
./run_daemon.sh

# Daemon dry run via CLI
./run_daemon.sh --dry-run

# Daemon in background
nohup ./run_daemon.sh &
```

## Cron Setup

The daemon mode (`run_daemon.sh`) is the recommended way to schedule utilities — it replaces cron entirely with a single process. If you prefer traditional cron, use the shell scripts below. Each script handles `cd` internally so absolute paths work correctly.

```cron
# Cold snapshots — every 2 hours
0 */2 * * * /path/to/project/run_cold_snapshots.sh >> /dev/null 2>&1

# Retention enforcer — daily at 3 AM
0 3 * * * /path/to/project/run_retention_enforcer.sh >> /dev/null 2>&1

# Restored index manager — every 6 hours
0 */6 * * * /path/to/project/run_restored_index_manager.sh >> /dev/null 2>&1

# ILM curator — every hour
0 * * * * /path/to/project/run_ilm_curator.sh >> /dev/null 2>&1
```

You can also pass flags through cron if needed:

```cron
# Cold snapshots with a specific pattern filter
0 */2 * * * /path/to/project/run_cold_snapshots.sh --pattern "logs-.*" >> /dev/null 2>&1

# Retention enforcer with custom retention period
0 3 * * * /path/to/project/run_retention_enforcer.sh --days 90 >> /dev/null 2>&1
```

Each utility writes its own log file under `logs/` at the project root (e.g., `logs/cold-snapshots.log`, `logs/retention-enforcer.log`). Logs rotate at 100 MB with 1 backup.

## Metrics

Utilities automatically record operational metrics to a SQLite database at `server/metrics/snapshot_metrics.db`. SQLite handles all locking internally, making concurrent access from daemon threads and manual script runs fully safe.

The database contains:

| Section | Description |
|---------|-------------|
| `daily_counters` | Today's snapshots created, snapshots deleted, ILM indices deleted |
| `utility_health` | Last run timestamp and success/failure per utility |
| `snapshot_statuses` | Distribution: SUCCESS, FAILED, PARTIAL, IN_PROGRESS, INCOMPATIBLE |
| `daemon_heartbeat` | Daemon PID, timestamp, and per-task state (written every 30s by the daemon) |
| `daily_history` | Archived daily counters for the past 90 days (used by `--history` mode) |

**Note:** When running in dry-run mode, mutation counters (`snapshots_created`, `snapshots_deleted`, `indices_deleted_ilm`) are **not** updated. Health status is still recorded so the dashboard shows the task ran.

View metrics with the dashboard:

```bash
python -m server.metrics_dashboard              # live view
python -m server.metrics_dashboard --history 7  # weekly trends
```

## Logging

Each utility writes to its own log file in `logs/` at the project root:

| Utility | Log File |
|---------|----------|
| Cold Snapshots | `logs/cold-snapshots.log` |
| Retention Enforcer | `logs/retention-enforcer.log` |
| Restored Index Manager | `logs/restored-index-manager.log` |
| ILM Curator | `logs/ilm-curator.log` |
| Snapshot CLI | `logs/snapshot-cli.log` |
| Daemon | `logs/daemon.log` |

Log format: `2025-01-15 02:00:00,123 - INFO - Message text`

Every utility logs its version at startup, e.g.:

```
2026-04-19 10:00:00,000 - INFO - Cold-snapshots v2.1.0 starting...
2026-04-19 10:00:00,000 - INFO - Elasticsearch Utilities Daemon v2.1.0 starting...
```

Rotation: 100 MB max file size, 1 backup file retained.

Pass `--debug` to any utility to enable DEBUG-level logging.

To view all logs merged into a single color-coded stream, use the log viewer:

```bash
python -m server.log_viewer            # snapshot view
python -m server.log_viewer --follow   # live tail
```

## Running Tests

```bash
# Run all tests
python -m pytest server/tests/ -v

# Run only property-based tests
python -m pytest server/tests/ -v -k "properties or retry"

# Run tests for a specific module
python -m pytest server/tests/test_config_loader_properties.py -v
python -m pytest server/tests/test_es_client.py -v
python -m pytest server/tests/test_cold_snapshots.py -v
```
