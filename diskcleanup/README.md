# diskcleanup.py

This script is a comprehensive disk cleanup utility designed to help maintain clean systems with intelligent file management and detailed reporting. The utility provides robust cleanup capabilities with comprehensive logging and metrics tracking.

## Features

- **Directory Cleanup**: Remove files older than specified age with configurable file extension patterns
- **Log File Management**: Monitor and truncate log files when they exceed size limits  
- **ABRT Crash Management**: Clean up crash dumps based on age and size thresholds
- **Pattern-Based Cleanup**: Advanced directory cleanup with regex pattern matching
- **Exclude Patterns**: Whitelist files/paths from cleanup using regex (global and per-directory)
- **Audit Log Management**: Cleanup audit logs when disk usage exceeds thresholds
- **Journald Cleanup**: Vacuum systemd journal logs by size and age thresholds
- **Daemon Mode**: Run continuously with configurable interval — no cron required
- **Service Management**: Detect and restart services with deleted file handles
- **Dry-Run Support**: Preview cleanup operations without making changes
- **Run History & Trending**: Track space freed per run with per-directory breakdown
- **Trending Reports**: View cleanup effectiveness over time with `--report` or `--report-csv`
- **Rich Logging**: Detailed operation tracking with correlation IDs and metrics
- **Health Monitoring**: Before/after system health comparison

## Compressed File Age Detection

When evaluating `.gz`, `.tar.gz`, and `.tgz` files for age-based cleanup, the utility looks beyond the filesystem modification time (mtime). Compressed files often carry a recent mtime from the moment they were created by log rotation, even though the data inside may be much older.

To handle this, the cleanup functions peek at the internal timestamp stored in the archive:

- **`.gz` files** — The gzip header contains a 4-byte timestamp of the original file. Only the first 8 bytes of the file are read.
- **`.tar.gz` / `.tgz` files** — The modification time of the first tar member is read from the archive header.

The older of the two timestamps (filesystem mtime vs. internal timestamp) is used for the age comparison. This means a log that was compressed yesterday but contains 60-day-old data will correctly be treated as 60 days old.

For performance, the internal timestamp check is skipped when the filesystem mtime already qualifies the file for deletion. The archive is only opened for files whose mtime is newer than the configured age threshold — the exact case this feature is designed to catch. On systems with large numbers of tar.gz files this keeps overhead minimal.

This applies to both `directory_cleanup` (the main config-driven path) and `advanced_cleanup_directory` (per-directory pattern rules).

This feature is enabled by default. To disable it, set `compressed_age_detection: false` in the `main` section of your YAML configuration:

```yml
main:
  compressed_age_detection: false
```

When disabled, all files are evaluated using only their filesystem mtime, which was the behavior prior to this feature.

## Architecture

The application uses a modular 3-file architecture:
- `diskcleanup.py` - Main orchestration script
- `diskcleanup_core.py` - Core business logic and cleanup functions  
- `diskcleanup_logging.py` - Logging infrastructure and metrics

## Testing

Comprehensive test scripts are provided to validate all cleanup functionality:
- `generate_test_files.sh` - Creates test files for all cleanup scenarios
- `cleanup_test_files.sh` - Removes all test files after validation
- `TEST_SCRIPTS_USAGE.md` - Complete testing documentation


## Installation of Python Modules

Install required Python Modules using the requirements.txt, Requires Python 3.6+

```bash
pip3 -r requirements.txt
```

## Usage

### Command Line Options

```bash
# Show version information
python diskcleanup.py --version
python diskcleanup.py -V

# Show version in GUI dialog (if GUI support available)
python diskcleanup.py --version-dialog

# Standard cleanup
sudo python diskcleanup.py

# Dry-run mode (preview only)
sudo python diskcleanup.py --dry-run

# Custom configuration file
sudo python diskcleanup.py --config /path/to/config.yaml

# Verbose output (shows excluded files, debug info)
sudo python diskcleanup.py --verbose

# View trending report (last 20 runs)
python diskcleanup.py --report

# View last 50 runs
python diskcleanup.py --report --last 50

# Export history as CSV
python diskcleanup.py --report-csv
python diskcleanup.py --report-csv --last 100 > cleanup_history.csv
```

### Testing Your Configuration

```bash
# 1. Generate test files
sudo ./generate_test_files.sh

# 2. Run cleanup (dry-run first recommended)
sudo python diskcleanup.py --dry-run

# 3. Run actual cleanup
sudo python diskcleanup.py

# 4. Clean up test files
sudo ./cleanup_test_files.sh
```

## Installation (using CRONTAB)

For automated cleanup, install via CRON:

```bash
# Hourly cleanup
00 * * * * /opt/diskcleanup/diskcleanup.py

# Daily cleanup with logging
00 2 * * * /opt/diskcleanup/diskcleanup.py 2>&1 | logger -t diskcleanup
```

## Daemon Mode

The `--daemon` flag runs diskcleanup in a continuous loop, sleeping between cleanup cycles. This is useful on systems without cron (containers, minimal AMIs, appliances) or when you want a single long-running process instead of scheduled invocations.

### Quick Start

```bash
# Run as daemon with default 1-hour interval
sudo python diskcleanup.py --daemon

# Override interval from the command line (every 30 minutes)
sudo python diskcleanup.py --daemon --interval 1800

# Combine with dry-run to test daemon behavior without deleting anything
sudo python diskcleanup.py --daemon --dry-run
```

### YAML Configuration

Add an optional `daemon` section to your YAML config:

```yml
daemon:
  interval: 3600                              # Seconds between cycles (default: 3600)
  pid_file: /var/run/diskcleanup.pid          # PID file location (default: /var/run/diskcleanup.pid)
  max_consecutive_errors: 5                   # Exit after N consecutive failures (default: 5)
```

| Config Parameter | Value | Explanation |
| :---: | :---: | :---: |
| interval | seconds | Time to sleep between cleanup cycles (default: 3600) |
| pid_file | path | PID file to prevent duplicate instances (default: /var/run/diskcleanup.pid) |
| max_consecutive_errors | integer | Daemon exits after this many consecutive cycle failures (default: 5) |

The `--interval` CLI flag takes precedence over the YAML value. If neither is set, the default is 3600 seconds (1 hour).

### How It Works

1. On startup, the daemon writes a PID file and registers signal handlers
2. Each cycle re-reads the YAML config, so changes take effect on the next cycle without a restart
3. Between cycles, the process sleeps using a kernel-level sleep — zero CPU usage
4. The daemon responds to signals:
   - `SIGTERM` / `SIGINT` — graceful shutdown (finishes current cycle, removes PID file)
   - `SIGHUP` — interrupts the sleep and starts the next cycle immediately (useful after config changes)
5. If a cleanup cycle crashes, the error is logged and the daemon continues. After `max_consecutive_errors` consecutive failures, the daemon exits to avoid silent broken loops

### PID File

The daemon writes its PID to the configured `pid_file` path. If the file already exists and the PID inside it belongs to a running process, the daemon refuses to start (prevents duplicate instances). Stale PID files from crashed processes are automatically detected and overwritten.

### Systemd Integration

Example systemd unit files are provided in `contrib/systemd/`. There are two approaches:

#### Option A: Daemon Mode (built-in sleep loop)

Use `diskcleanup-daemon.service` — the script runs continuously with `--daemon`:

```bash
sudo cp contrib/systemd/diskcleanup-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now diskcleanup-daemon.service

# Check status
sudo systemctl status diskcleanup-daemon

# Reload config (sends SIGHUP, triggers immediate next cycle)
sudo systemctl reload diskcleanup-daemon

# View logs
journalctl -u diskcleanup-daemon -f
```

#### Option B: Systemd Timer (process starts/stops each cycle)

Use `diskcleanup.service` + `diskcleanup.timer` — systemd handles the scheduling, the script runs once per invocation and exits:

```bash
sudo cp contrib/systemd/diskcleanup.service /etc/systemd/system/
sudo cp contrib/systemd/diskcleanup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now diskcleanup.timer

# Check timer schedule
systemctl list-timers diskcleanup.timer

# Manual trigger
sudo systemctl start diskcleanup.service
```

The timer approach frees all memory between runs and is preferred for production servers with systemd. The daemon approach is simpler for environments without systemd or cron.

## YAML Configuration

The script reads a YAML configuration file to tell the script all the settings that it needs to know in order to function properly.

### Main Section

```yml
main:
  cleanup: true
  abrt_maxage: 30
  abrt_maxsize: 50 MB
  abrt_directory: /var/log/crash/abrt
  max_filesize: 2 GiB
  max_fileage: 30
  check_services:
    - filebeat
  file_extensions:
    - "tar.gz"
    - ".gz"
  exclude_patterns:
    - '\.keep$'
    - 'compliance'
    - 'do-not-delete'
  directories_to_check:
    - "/var/log"
  recursive: true
  audit_percent: 50
  compressed_age_detection: true
  log_file: diskcleanup.log
  history_file: diskcleanup_history.jsonl
```
The above configuration is explained as follows:

| Config Parameter | Value |  Explanation |
| :---: | :---: | :---: |
| abrt_maxage | days | Set max file age of ABRT files |
| abrt_maxsize | size | Purge if directory over this size (MB or GB) |
| abrt_directory | directory | Directory of ABRT crash files |
| cleanup | (true,false) | (this tells the program whether or not to perform cleanup of the /var/log directory)|
| max_filesize | (KiB,MiB,GiB,TiB) | Sets file Limit Size (There must be space between value and size (i.e.: 2 GiB) |
| max_fileage | days | Set file Max Age in number of days (i.e.: 30 days) |
| check_services | List | List of services to check for deleted open file handles | 
| file_extensions | anything |  List of extensions to pay attention to, only will action files matching these extensions |
| exclude_patterns | List | Regex patterns — files matching any pattern are never deleted (matched against full path and filename) |
| directories_to_check | /var/log | This really should only be set to /var/log |
| recursive | (true,false) | When true, directories_to_check are scanned recursively into subdirectories (default: false) |
| audit_percent | 0-100 | Setting this value in (%) percent it will delete files until this percent of disk space is free |
| compressed_age_detection | (true,false) | When true, `.gz`/`.tar.gz`/`.tgz` files are inspected for their internal timestamp to determine true data age (default: true) |
| log_file | anything | Location to write the log file |
| history_file | anything | Location to write the JSONL run history for trending reports (default: diskcleanup_history.jsonl) |

### Files Section

This section of the YAML is to list individual files that you want to monitor specifically and the max value setting for this file. If the file r

```yml
files:
  "/var/log/mysqld.log": "2 GiB"
  "/var/log/mysql/mysql-slow.log" : "3 GiB"
  "/var/log/logstash/logstash-plain.log": {}
```
In the above example of files to watch, the following will happen:
- File /var/log/mysqld.log will be truncated to 0 bytes once it reaches 2 GiB in size.
- File /var/log/mysql-slow.log will be truncated to 0 bytes once it reaches 3 GiB in size.
- File /var/log/logstash/logstash-plain.log will be truncated to 0 bytes once it reaches whatever the MAX Global setting is configured (max_filesize) which in this case is 2 GiB, so once it reaches 2 GiB it will be truncated.

### Journald Section

This optional section controls cleanup of systemd journal logs (`/var/log/journal`). On systems without systemd the section is silently skipped.

```yml
journald:
  cleanup: true
  max_size: "500 MB"
  max_age: "30d"
```

| Config Parameter | Value | Explanation |
| :---: | :---: | :---: |
| cleanup | (true,false) | Enable or disable journald vacuum cleanup |
| max_size | size | Maximum total journal size — maps to `journalctl --vacuum-size` (e.g. "500 MB", "1 GB") |
| max_age | duration | Maximum journal age — maps to `journalctl --vacuum-time` (e.g. "30d", "2weeks") |

Both constraints are applied together; whichever is more aggressive wins (this matches journalctl's own behavior). In dry-run mode the current journal usage is compared against `max_size` to estimate potential savings without actually vacuuming.

### Directories Section

This section allows you to specifically individual directories to check across the filesystem and the appropriate configuration settings.

If you plan to watch multiple file REGEX patterns within a single directory, you will need to use the REGEX | parameter, something like:
**file_pattern: "[logfile1_.\*|filebeat-.\*]"**. This would look for logs beginning with logfile1_\*, or filebeat-\*.

```yml
directories:
  "/var/log/directory_1":
    file_pattern: "[log_.*\\.log]"
  "/var/log/directory_2":
    max_fileage: 3
    file_pattern: "file_.*\\.csv"
    exclude_pattern: "file_important.*"
  "/var/log/directory_3":
    max_fileage: 7
    file_pattern: ".*\\.log"
    recursive: false
```

In the example of directories to watch, the following will happen:
- Directory /var/log/directory_1, any file that matches REGEX pattern will be deleted recursively (default), since no max_fileage was provided it will default to using Global Default [max_fileage] which in this case would be 30 days.
- Directory /var/log/directory_2, any file that matches REGEX pattern will be deleted recursively, in this case anything over 3 days. Files matching `file_important.*` will never be deleted.
- Directory /var/log/directory_3, only top-level files matching the pattern older than 7 days are deleted. Subdirectories are not scanned because `recursive: false`.

The optional `exclude_pattern` field accepts a single regex string or a list of patterns. These are merged with the global `exclude_patterns` from the main section, so global excludes always apply everywhere.

The optional `recursive` field defaults to `true` for pattern directories (preserving the original behavior). Set to `false` to scan only the top-level directory.

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Trending Reports

Each run automatically records a summary to the history file (JSONL format). Use the `--report` flag to view cleanup trends:

```bash
# Rich-formatted report
python diskcleanup.py --report

# Show last 50 runs
python diskcleanup.py --report --last 50

# Export as CSV for spreadsheets or monitoring tools
python diskcleanup.py --report-csv > cleanup_history.csv
```

The report shows:
- **Summary** — total space freed, files processed, error count across all runs
- **Run History** — each run with timestamp, mode (live/dry-run), freed, files, errors, duration
- **Top Paths by Space Freed** — which directories/files contribute most to cleanup (including journald), aggregated across runs
- **Mount Point Trends** — disk usage change per mount from oldest to newest run

The history file is automatically trimmed to the most recent 500 entries.
