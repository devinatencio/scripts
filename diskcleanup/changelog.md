# Changelog — diskcleanup.py

---

## 2.5.0 (2026-04-17) — Safety Guardrails: Protected Path Enforcement

### Protected Path System

- **NEW:** `PROTECTED_PATHS` frozen set of critical system directories that must never be targeted (`/`, `/etc`, `/usr`, `/home`, `/boot`, etc.)
- **NEW:** `MIN_DIRECTORY_DEPTH` constant — rejects paths shallower than depth 2 (e.g. `/var`)
- **NEW:** `is_path_protected(path)` — resolves symlinks, checks against protected set, enforces depth, and detects parent-of-protected scenarios
- **NEW:** `validate_path_safety(path, context)` — raises `ConfigError` and logs at CRITICAL level if a protected path is detected

### Config Validation Hardening

- **ENHANCED:** `validate_config()` now checks `directories_to_check`, `directories` section, and `abrt_directory` against protected paths at startup
- **ENHANCED:** `validate_config()` now receives the full `directories` dict from `main()` for complete coverage
- **BLOCKED:** Configurations referencing `/`, `/home`, `/usr`, or other system-critical paths are rejected before any cleanup runs

### Runtime Defense-in-Depth

- **ENHANCED:** `directory_cleanup()` calls `validate_path_safety()` before any file operations
- **ENHANCED:** `advanced_cleanup_directory()` calls `validate_path_safety()` before any file operations
- **ENHANCED:** `delete_old_abrt_directories()` calls `validate_path_safety()` before any file operations
- **ENHANCED:** `cleanup_empty_abrt_directories()` calls `validate_path_safety()` before any file operations
- **ENHANCED:** `delete_abrt_directories_by_size()` calls `validate_path_safety()` before any file operations

> **Note:** All changes maintain Python 3.6+ compatibility.

---

## 2.4.0 (2026-04-16) — Recursive Directory Cleanup

### Recursive Cleanup

- **NEW:** `recursive` option in YAML main section for `directories_to_check` (default: `false`)
- **NEW:** `recursive` option per directory in directories section (default: `true`, preserving existing behavior)
- **ENHANCED:** `directory_cleanup()` now accepts `recursive` flag, uses `rglob` when true
- **ENHANCED:** `advanced_cleanup_directory()` now accepts `recursive` flag, controllable per directory
- **ENHANCED:** Log output shows `recursive=True/False` for visibility
- **USE CASE:** Nested log structures (e.g. `/var/log/app/subdir/*.gz`) now cleaned in one pass

> **Note:** All changes maintain Python 3.6+ compatibility.

---

## 2.3.0 (2025-07-26) — Exclude Patterns & Documentation Update

### Exclude Patterns

- **NEW:** Global `exclude_patterns` list in YAML main section
- **NEW:** Per-directory `exclude_pattern` in directories section
- **NEW:** Patterns matched against both full path and filename (regex)
- **NEW:** Global and per-directory excludes are merged for pattern directories
- **NEW:** Excluded files logged at DEBUG level for transparency
- **ENHANCED:** `directory_cleanup()` and `advanced_cleanup_directory()` accept `exclude_patterns`
- **USE CASE:** Preserve compliance logs, rotated logs, or specific files from cleanup

### Per-Directory Breakdown in Trending

- **NEW:** Each run records per-directory/file space freed in JSONL history
- **NEW:** "Top Paths by Space Freed" table in `--report` aggregates across all runs
- **NEW:** Shows type (dir/pattern/truncate/abrt), total freed, file count, runs, avg/run
- **ENHANCED:** All report tables now expand to full terminal width for consistent alignment

### Bug Fix

- **FIXED:** `OperationMetrics.add_directory()` called with wrong arguments in dry-run ABRT cleanup

### Documentation

- **UPDATED:** `README.md` with trending report, CSV export, exclude patterns, `history_file` config
- **UPDATED:** `diskcleanup.yaml` with `exclude_patterns` example
- **UPDATED:** `diskcleanup_test.yaml` with global and per-directory exclude examples

> **Note:** All changes maintain Python 3.6+ compatibility.

---

## 2.2.0 (2025-07-26) — Run History & Trending Reports

### Run History Tracking

- **NEW:** Each cleanup run (live and dry-run) appends a JSON summary to a history file
- **NEW:** History stored as JSONL (JSON Lines) — one record per line, append-safe
- **NEW:** Tracks timestamp, hostname, space freed, files/dirs processed, errors, duration
- **NEW:** Per-mount-point disk usage recorded (before/after percentages) for trending
- **NEW:** Configurable `history_file` path in YAML config (defaults to `diskcleanup_history.jsonl`)
- **NEW:** Auto-trim keeps history file capped at 500 entries

### Trending Report (`--report`)

- **NEW:** `--report` flag renders a Rich-formatted trending report and exits
- **NEW:** Summary panel with total space freed, files processed, error count
- **NEW:** Run history table showing each run with mode, freed, files, errors, duration
- **NEW:** Mount point trends table comparing oldest vs newest live run per mount
- **NEW:** Color-coded change indicators (green = improving, red = growing)
- **NEW:** `--last N` flag to control how many recent runs to display (default: 20)

### CSV Export (`--report-csv`)

- **NEW:** `--report-csv` flag exports history as CSV to stdout for external tooling
- **NEW:** Suitable for piping into spreadsheets, monitoring dashboards, or scripts

### Bug Fix

- **FIXED:** `convert_size_to_bytes()` did not recognize bare suffixes (`M`, `G`, `K`, `T`)
- **FIXED:** `100M` was parsed as 100 bytes instead of 100 MB, causing log file truncation on every run and loss of previous session data

> **Note:** All changes maintain Python 3.6+ compatibility.

---

## 2.1.0 (2026-04-16) — Code Modernization: Pathlib & Cleanup

### Pathlib Standardization

- **ENHANCED:** Converted all file/directory operations to use `pathlib` consistently
- **ENHANCED:** `simulate_cleanup()`, `delete_old_abrt_directories()`, `cleanup_empty_abrt_directories()`
- **ENHANCED:** `delete_abrt_directories_by_size()`, `find_yaml_config()`, `truncate_log_file()`
- **ENHANCED:** `truncate_file()`, `setup_rc_files()`, `directory_cleanup()`, `advanced_cleanup_directory()`
- **ENHANCED:** `audit_scan_files()`, `count_deleted_files_procfs()`, `validate_config()`
- **KEPT:** `os.readlink` for `/proc` fd symlinks, `os.stat` for partition device comparison

### Stdlib Disk Usage

- **ENHANCED:** `partition_usage()` and `disk_usage()` now use `shutil.disk_usage()`
- **REMOVED:** Raw `os.statvfs()` calls replaced with cleaner stdlib API (available since Python 3.3)

### Custom Exceptions

- **NEW:** `DiskCleanupError` base exception class
- **NEW:** `ConfigError` for configuration parsing and validation failures
- **NEW:** `CleanupOperationError` for cleanup operation failures
- **ENHANCED:** `readConfig()` now raises `ConfigError` with proper exception chaining

### Type Hints

- **ENHANCED:** Added return type annotations to `audit_scan_files()`, `run_check_services()`, `check_auditd()`

### Import Cleanup

- **REMOVED:** Unused `json` import from `diskcleanup_core.py`
- **REMOVED:** Unused `glob` import from `diskcleanup_core.py` (replaced by `pathlib.glob`)
- **REMOVED:** Unused `sys` import from `diskcleanup_core.py`
- **REMOVED:** Unused `os` import from `diskcleanup.py`

### Bug Fixes

- **FIXED:** Removed redundant duplicate existence check in `advanced_cleanup_directory()`
- **FIXED:** `delete_abrt_directories_by_size()` error handler referenced unbound variable

> **Note:** All changes maintain Python 3.6+ compatibility.

---

## 2.0.4 (2025-07-23) — Critical Bug Fixes: Metrics & ABRT Improvements

### Critical Bug Fixes

- **FIXED:** ABRT cleanup metrics not being tracked (space freed always showed 0 bytes)
- **FIXED:** Operation metrics always showing 0 files/directories processed
- **FIXED:** ABRT directory counting not working in age cleanup phase
- **FIXED:** ABRT size cleanup missing dry-run support (always performed live deletions)
- **ENHANCED:** Proper synchronization between global metrics and operation context metrics
- **ENHANCED:** All cleanup operations now show accurate file counts, directory counts, and duration

### ABRT Cleanup Improvements

- **FIXED:** `delete_old_abrt_directories()` now properly tracks directory removal
- **FIXED:** `delete_abrt_directories_by_size()` now supports dry-run mode
- **ENHANCED:** ABRT cleanup now shows accurate space freed and directory counts

### Metrics Tracking Overhaul

- **FIXED:** File and directory counts now properly synchronized across all operations
- **ENHANCED:** Accurate duration tracking for all cleanup phases
- **ENHANCED:** Proper metrics accumulation from cleanup functions to operation context

### Test Infrastructure

- **NEW:** `generate_test_files.sh` — Comprehensive test file generator
- **NEW:** `cleanup_test_files.sh` — Test file cleanup script
- **NEW:** `TEST_SCRIPTS_USAGE.md` — Complete testing documentation
- **ENHANCED:** Validation scripts for all cleanup scenarios (age, size, patterns, ABRT)

---

## 2.0.3 (2025-07-23) — Operation ID Simplification

### Improved Operation ID Format

- **ENHANCED:** Simplified operation ID format — removed extra underscores
- **ENHANCED:** More compact and readable operation IDs
- **ENHANCED:** Easier visual scanning in logs

**Before:**

```
[session_1556_bfd]
[dir_cleanup_1556_35a]
[abrt_cleanup_1553_0cd]
```

**After:**

```
[session_1556bfd]
[dir_cleanup_155635a]
[abrt_cleanup_15530cd]
```

**Benefits:** Shorter log lines, easier to type when searching, improved readability in monitoring tools.

---

## 2.0.2 (2025-07-23) — Major Refactoring: Modular Architecture

### Complete Code Restructuring

- **NEW:** Modular 3-file architecture for better maintainability
- **NEW:** `diskcleanup_logging.py` — Dedicated logging infrastructure module
- **NEW:** `diskcleanup_core.py` — All business logic and core functions
- **NEW:** `diskcleanup.py` — Clean main script with orchestration logic
- **ENHANCED:** Clear separation of concerns across modules
- **ENHANCED:** Improved testability with isolated components
- **ENHANCED:** Better code organization and readability

**Before:** Single monolithic file

```
diskcleanup.py: 1570 lines (everything mixed together)
```

**After:** Clean modular architecture

```
diskcleanup.py:         299 lines (main script + orchestration)
diskcleanup_logging.py: 281 lines (logging infrastructure)
diskcleanup_core.py:    813 lines (business logic)
Total:                 1393 lines (177 lines saved through optimization)
```

**Benefits:** Independent module testing, clear interfaces, easier debugging, better reusability, simpler collaboration.

---

## 2.0.1 (2025-07-23) — Logging Enhancement: Clean Operation Tracking

### Enhanced Operation Tracking

- **NEW:** Operation IDs now prefixed to every log line for instant visual tracking
- **NEW:** Custom `OperationIdFormatter` and `OperationIdRichHandler` for dual logging
- **NEW:** Thread-local operation context management for nested operations
- **NEW:** Simplified operation ID format — much shorter and cleaner
- **NEW:** Simplified log messages — removed redundant `[SYSTEM][COMPONENT]` prefixes
- **ENHANCED:** Log format now shows: `[operation_id] timestamp LEVEL : clean_message`
- **ENHANCED:** Easy grep filtering with compact IDs
- **ENHANCED:** Visual scanning — related operations grouped together
- **ENHANCED:** Console width no longer artificially limited to 100 chars

### Operation ID Simplification

**Before:**

```
dir_cleanup_143052_a1b2_scanning_3_dirs
pattern_cleanup_143058_e5f6_scanning_2_pattern_dirs
session_20250123_143020_a1b2
```

**After:**

```
dir_cleanup_1430_c3d
pattern_cleanup_1431_e5f
session_1430_a1b
```

### Log Format Improvement

**Before:**

```
2025-01-23 14:30:52 INFO : [SYSTEM][CLEANUP] starting dir_cleanup (operation_id: dir_cleanup_143052_c3d4_scanning_3_dirs)
```

**After:**

```
[dir_cleanup_1430_c3d] 2025-01-23 14:30:52 INFO : Starting operation
[dir_cleanup_1430_c3d] 2025-01-23 14:30:56 INFO : Removed old file /var/log/app.log.old (age_days: 45)
```

---

## 2.0.0 (2025-07-23) — Major Release: Enterprise Edition

### Complete Logging System Overhaul

- **NEW:** `LogHelper` class with standardized message formatting across all operations
- **NEW:** `OperationContext` class with correlation IDs for tracking complex operations
- **NEW:** `LogSampler` class for intelligent log sampling during high-volume operations
- **NEW:** `OperationMetrics` dataclass for comprehensive performance tracking
- **NEW:** Structured error logging with contextual information and error categorization
- **ENHANCED:** All log messages now use consistent `[SYSTEM][ACTION][DRY-RUN][CONFIG][PERF]` formatting
- **ENHANCED:** Performance logging with execution times, files processed, and error counts
- **ENHANCED:** Log levels properly assigned (DEBUG/INFO/WARNING/ERROR) for better filtering
- **FIXED:** Console and file logging now have identical formatting (resolved markup issues)

### Advanced System Health Monitoring

- **NEW:** Professional before/after system health comparison with visual improvements
- **NEW:** Color-coded health status indicators (Good/Caution/Warning/Critical)
- **NEW:** Compact health summary display for improved readability
- **NEW:** Side-by-side comparison tables showing exactly what was freed and where
- **NEW:** Real-time improvement percentage calculations for each mount point
- **ENHANCED:** Rich console UI with panels, tables, and professional formatting
- **ENHANCED:** Dry-run mode shows potential savings analysis with detailed breakdown

### Performance & Metrics Tracking

- **NEW:** Global metrics aggregation across all cleanup operations
- **NEW:** Context managers for automatic operation start/finish logging
- **NEW:** Execution time tracking with sub-second precision
- **NEW:** Files and directories processed counters with sampling
- **NEW:** Progress reporting for large directory operations (every 1000 files)
- **NEW:** Error tracking and reporting in final summary
- **ENHANCED:** Memory-efficient processing with `pathlib.rglob()` for directory traversal

### Enhanced User Interface

- **NEW:** Professional Rich-based console output with emoji indicators
- **NEW:** Summary panels showing key metrics at completion
- **NEW:** Color-coded improvements highlighting significant space savings
- **NEW:** Clean startup display with current system status
- **ENHANCED:** Removed verbose rule separators and redundant health displays
- **ENHANCED:** Consolidated information into single, easy-to-read comparison views

### Code Quality & Architecture

- **NEW:** `CleanupConfig` dataclass for structured configuration management
- **NEW:** Type hints throughout with `Union` types and comprehensive annotations
- **NEW:** Professional documentation header with features, requirements, and usage
- **NEW:** Context managers for safe file operations with proper error handling
- **ENHANCED:** Configuration validation with detailed error messages and field checking
- **ENHANCED:** Better separation of concerns with logical function grouping
- **FIXED:** Replaced unsafe `os.system()` calls with native Python file operations
- **FIXED:** Added missing imports and resolved dependency issues

### Security & Reliability

- **ENHANCED:** Safe file operations with comprehensive exception handling
- **ENHANCED:** Configuration validation prevents runtime errors
- **ENHANCED:** Permission error handling with graceful degradation
- **ENHANCED:** File operation safety with proper context management
- **FIXED:** Error propagation and recovery mechanisms

### Efficiency Improvements

- **OPTIMIZED:** Smart log sampling reduces output volume by 80% for large operations
- **OPTIMIZED:** Single-pass directory traversal with `pathlib` for better performance
- **OPTIMIZED:** Reduced redundant file system calls and improved I/O efficiency
- **OPTIMIZED:** Memory usage improvements for large directory processing
- **OPTIMIZED:** Progress tracking prevents UI freezing during long operations

### Monitoring & Observability

- **NEW:** Correlation IDs for tracking related operations across log files
- **NEW:** Structured metrics suitable for monitoring tools and automation
- **NEW:** Performance baselines and execution time trending capability
- **NEW:** Error categorization and detailed error context for debugging
- **ENHANCED:** Professional log format suitable for enterprise monitoring systems

---

## 1.3.4 (2025-07-18)

- Added `format_size()` function to consistently format file sizes in human-readable format
- Added `validate_config()` function to verify configuration values before execution
- Added `check_system_health()` function to monitor system metrics before/after cleanup
- Improved logging messages with standardized format and human-readable sizes
- Added dry-run support for ABRT directory cleanup operations
- Updated disk space reporting to use consistent units across all operations
- Added missing docstrings and type hints for better code documentation
- Reorganized functions into logical sections for better maintainability
- Added calculation of actual space freed by comparing system health metrics
- Added email notification with cleanup results
- Fixed bug in directory cleanup size tracking
- Added support for file pattern matching in advanced directory cleanup
- Added better error handling for configuration file parsing
- Added validation for required configuration sections

---

## 1.3.2 (2025-07-10)

- AI performed some refactoring of code, adding lots of comments
- Removed a duplicate function found
- Updated `requirements.txt` to latest pip3 packages

---

## 1.3.0 (2025-02-12)

- Added service restart for apps hanging onto deleted open files — see `diskcleanup.yaml`, `check_services` feature

---

## 1.2.6 (2024-02-29)

- Fixed bug discovered not deleting files if it finds an `ENOENT` error

---

## 1.2.5 (2024-02-26)

- Fixed issue with log path having slashes

---

## 1.2.2 (2024-02-05)

- Fixed issue when script was called from another directory

---

## 1.2.1 (2023-09-28)

- Added functionality to deal with ABRT files

---

## 1.1.1 (2023-09-03)

- Added automatic configuration search on startup of script — will search for config file `.yml`, `.yaml`
- Added a few more debug fixes and minor updates to script
- Added `Changelog.txt` file to repository
- Included WHL files for Python 3.6 and Python 3.9 for PyYAML
