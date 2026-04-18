#!/usr/bin/python3
"""
Disk Cleanup Utility - Core Cleanup Operations Module

This module contains the core cleanup business logic:
- Directory cleanup (basic and advanced/pattern-based)
- File size monitoring and truncation
- ABRT crash dump management
- Journald log cleanup
- Audit log cleanup
- Service management (deleted file handle detection, restarts)

Author: Devin Acosta
Version: 3.0.0
Date: 2026-04-18
"""

import arrow
import datetime
import logging
import os
import re
import shutil
import struct
import subprocess
import tarfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Union

from diskcleanup.logging import LogHelper, LogSampler, OperationMetrics

# Re-export everything that diskcleanup.py expects from this module so
# existing imports continue to work without changes to the main script.
from diskcleanup.config import (                       # noqa: F401
    DiskCleanupError, ConfigError, CleanupOperationError,
    format_size, convert_size_to_bytes, has_slashes,
    is_path_protected, validate_path_safety,
    find_yaml_config, readConfig, validate_config,
    PROTECTED_PATHS, MIN_DIRECTORY_DEPTH,
)
from diskcleanup.health import (                       # noqa: F401
    check_system_health, calculate_space_freed,
    get_health_status, partition_usage,
    disk_usage, same_partition,
    print_health_comparison, print_compact_health_summary,
)
from diskcleanup.history import (                      # noqa: F401
    get_history_path, save_run_history, load_run_history,
    trim_history_file, print_report, print_report_csv,
    DEFAULT_HISTORY_FILE, MAX_HISTORY_ENTRIES,
)


# ── Module-level runtime (set via init_runtime) ─────────────────────
logger = LogHelper()
log = None  # type: Optional[logging.Logger]
global_metrics = None  # type: Optional[OperationMetrics]

# Global variables
rc_files: Dict[str, Dict[str, int]] = {}
SCRIPTVER = "3.0.0"
SCRIPTDATE = "2026-04-18"


def init_runtime(log_instance: logging.Logger, logger_helper: LogHelper,
                 metrics: OperationMetrics) -> None:
    """Initialize the module-level runtime dependencies.

    Call this once per cleanup cycle (after setup_logging) instead of
    reaching into the module and reassigning globals from the outside.
    Also propagates to sub-modules that need the same runtime state.
    """
    global log, logger, global_metrics
    log = log_instance
    logger = logger_helper
    global_metrics = metrics

    # Propagate to sub-modules
    import diskcleanup.config
    diskcleanup.config.log = log_instance
    diskcleanup.config.logger = logger_helper

    import diskcleanup.health
    diskcleanup.health.log = log_instance
    diskcleanup.health.logger = logger_helper
    diskcleanup.health.global_metrics = metrics

    import diskcleanup.history
    diskcleanup.history.log = log_instance
    diskcleanup.history.logger = logger_helper


# ── File Operations ──────────────────────────────────────────────────
def truncate_log_file(filename: str, file_size: str) -> None:
    """Truncates a log file if it exceeds a specified size."""
    file_path = Path(filename)
    try:
        bytes_to_compare = convert_size_to_bytes(file_size)
        actual_size = file_path.stat().st_size if file_path.exists() else 0
    except OSError:
        actual_size = 0
    if actual_size > bytes_to_compare:
        with open(filename, 'r+') as file:
            file.truncate(bytes_to_compare)
        if log is not None:
            log.info(logger.action(f"truncated file {filename}",
                                  target_size=file_size))


def truncate_file(filename: str) -> None:
    """Truncate a file to 0 bytes."""
    try:
        Path(filename).write_text('')
        log.info(logger.action(f"truncated file {filename} to 0 bytes"))
        global_metrics.add_file()
    except OSError as e:
        log.error(logger.error_with_context(filename, e))
        global_metrics.add_error()


def setup_rc_files(files: Dict[str, Any], max_filesize: str) -> None:
    """Set up the global rc_files dictionary."""
    global rc_files
    rc_files = {}

    for filename, file_config in files.items():
        try:
            file_path = Path(filename)
            file_size = file_path.stat().st_size if file_path.exists() else 0

            if isinstance(file_config, dict) and file_config:
                file_maxsize = convert_size_to_bytes(file_config.get('max_size', max_filesize))
            elif isinstance(file_config, str):
                file_maxsize = convert_size_to_bytes(file_config)
            else:
                file_maxsize = convert_size_to_bytes(max_filesize)

            rc_files[filename] = {
                'file_size': file_size,
                'file_maxsize': file_maxsize
            }
        except Exception as e:
            if log is not None:
                log.warning(logger.config(f"failed to process file {filename}", error=str(e)))


def disk_cleanup() -> int:
    """Performs disk cleanup by truncating files that exceed their maximum allowed size."""
    global rc_files
    space_freed = 0
    for file in rc_files:
        file_size = rc_files[file]['file_size']
        file_maxsize = rc_files[file]['file_maxsize']
        if ((file_size >= file_maxsize) and file_size != 0):
            log.info(logger.action(f"truncating file {file}",
                                  current_size=format_size(file_size),
                                  max_size=format_size(file_maxsize)))
            space_freed += file_size
            truncate_file(file)
        else:
            log.debug(logger.system(f"skipping file {file} (within size limit)",
                                   current_size=format_size(file_size)))
    return space_freed


# ── Compressed file age detection ────────────────────────────────────
def get_compressed_file_age(file_path: Path) -> Optional[datetime.datetime]:
    """Peek inside a .gz or .tar.gz file to extract the original data timestamp.

    For .tar.gz files: reads the mtime of the first tar member.
    For plain .gz files: reads the 4-byte timestamp from the gzip header (bytes 4-7).

    Returns a datetime if a valid internal timestamp is found, otherwise None.
    A zero or missing timestamp is treated as unavailable.
    """
    name = file_path.name.lower()
    try:
        if name.endswith('.tar.gz') or name.endswith('.tgz'):
            log.debug(logger.system(f"peeking at tar archive header for {file_path}"))
            with tarfile.open(str(file_path), 'r:gz') as tf:
                for member in tf:
                    if member.mtime and member.mtime > 0:
                        internal_ts = datetime.datetime.fromtimestamp(member.mtime)
                        log.debug(logger.system(f"tar internal timestamp for {file_path}",
                                               internal_mtime=str(internal_ts)))
                        return internal_ts
            log.debug(logger.system(f"no valid member timestamp found in {file_path}"))
            return None
        elif name.endswith('.gz'):
            log.debug(logger.system(f"peeking at gzip header for {file_path}"))
            with open(str(file_path), 'rb') as f:
                header = f.read(8)
                if len(header) < 8 or header[0:2] != b'\x1f\x8b':
                    log.debug(logger.system(f"invalid gzip header in {file_path}"))
                    return None
                ts = struct.unpack('<I', header[4:8])[0]
                if ts == 0:
                    log.debug(logger.system(f"gzip header timestamp is zero for {file_path}"))
                    return None
                internal_ts = datetime.datetime.fromtimestamp(ts)
                log.debug(logger.system(f"gzip internal timestamp for {file_path}",
                                       internal_mtime=str(internal_ts)))
                return internal_ts
    except (OSError, tarfile.TarError, struct.error, OverflowError, ValueError) as e:
        log.debug(logger.system(f"could not read internal timestamp from {file_path}", error=str(e)))
    return None


def get_effective_file_age(file_path: Path, filesystem_mtime: datetime.datetime,
                          max_age_threshold: Optional[datetime.datetime] = None,
                          compressed_age_detection: bool = True) -> datetime.datetime:
    """Return the older of the filesystem mtime and the compressed internal timestamp."""
    if not compressed_age_detection:
        return filesystem_mtime
    name = file_path.name.lower()
    if name.endswith('.gz') or name.endswith('.tgz'):
        if max_age_threshold is not None and filesystem_mtime < max_age_threshold:
            return filesystem_mtime
        internal_ts = get_compressed_file_age(file_path)
        if internal_ts is not None and internal_ts < filesystem_mtime:
            log.debug(logger.system(
                f"using internal timestamp for {file_path}",
                internal_age=str(internal_ts), fs_mtime=str(filesystem_mtime)))
            return internal_ts
    return filesystem_mtime


# ── Pattern / extension matching ─────────────────────────────────────
def check_filename_pattern(file_path: Path, file_extensions: List[str]) -> bool:
    """Check if a file matches any of the specified extensions."""
    filename = file_path.name
    for extension in file_extensions:
        if re.search(extension, filename):
            return True
    return False


def check_exclude_pattern(file_path: Path, exclude_patterns: List[str]) -> bool:
    """Check if a file matches any exclude pattern (should be skipped)."""
    if not exclude_patterns:
        return False
    full_path = str(file_path)
    filename = file_path.name
    for pattern in exclude_patterns:
        if re.search(pattern, full_path) or re.search(pattern, filename):
            return True
    return False


# ── Directory Cleanup ────────────────────────────────────────────────
def advanced_cleanup_directory(directory: str, max_age_days: int, file_pattern: str,
                               dry_run: bool = False,
                               exclude_patterns: Optional[List[str]] = None,
                               recursive: bool = True,
                               compressed_age_detection: bool = True) -> int:
    """Performs advanced cleanup of a directory based on file age and regex pattern."""
    validate_path_safety(directory, context="advanced_cleanup_directory")
    if exclude_patterns is None:
        exclude_patterns = []
    if not Path(directory).exists():
        log.warning(f"Directory does not exist: {directory}")
        return 0

    space_freed = 0
    current_time = datetime.datetime.now()
    threshold_date = current_time - datetime.timedelta(days=max_age_days)

    log.info(logger.system(f"starting directory cleanup for {directory}",
                          max_age=max_age_days, pattern=file_pattern,
                          recursive=recursive))

    try:
        pattern = re.compile(file_pattern)
        directory_path = Path(directory)

        sampler = LogSampler(50)
        files_processed = 0
        file_iter = directory_path.rglob('*') if recursive else directory_path.glob('*')

        for file_path in file_iter:
            if file_path.is_file():
                files_processed += 1
                if check_exclude_pattern(file_path, exclude_patterns):
                    log.debug(logger.system(f"excluded file {file_path}"))
                    continue
                try:
                    if pattern.search(file_path.name):
                        file_mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                        file_mtime = get_effective_file_age(file_path, file_mtime,
                                                            max_age_threshold=threshold_date,
                                                            compressed_age_detection=compressed_age_detection)
                        if file_mtime < threshold_date:
                            file_size = file_path.stat().st_size
                            age_days = (current_time - file_mtime).days

                            if dry_run:
                                space_freed += file_size
                                global_metrics.add_file(file_size)
                                if sampler.should_log():
                                    log.info(logger.dry_run(f"remove file {file_path}",
                                                           age_days=age_days, size=format_size(file_size)))
                            else:
                                file_path.unlink()
                                space_freed += file_size
                                global_metrics.add_file(file_size)
                                if sampler.should_log():
                                    log.info(logger.action(f"removed old file {file_path}",
                                                          age_days=age_days, size=format_size(file_size)))
                        if files_processed % 1000 == 0:
                            log.debug(logger.progress(files_processed, files_processed + 1000,
                                                     directory=directory))
                except (OSError, FileNotFoundError) as e:
                    log.debug(logger.error_with_context(str(file_path), e))
                    global_metrics.add_error()
                    continue

        log.info(logger.system(f"completed cleanup for {directory}",
                              files_processed=files_processed, space_freed=format_size(space_freed)))

    except Exception as e:
        log.error(logger.error_with_context(directory, e))
        global_metrics.add_error()

    return space_freed


def directory_cleanup(directory: str, max_fileage: int, file_extensions: List[str],
                      dry_run: bool = False, exclude_patterns: Optional[List[str]] = None,
                      recursive: bool = False, compressed_age_detection: bool = True) -> int:
    """Performs cleanup of files in a directory based on age and extensions."""
    validate_path_safety(directory, context="directory_cleanup")
    if exclude_patterns is None:
        exclude_patterns = []
    space_freed = 0
    log.info(logger.system(f"starting cleanup for {directory}",
                          max_age=max_fileage, extensions=file_extensions,
                          recursive=recursive))

    dir_max_fileage = int(f"-{max_fileage}")
    dir_max_fileage_tstamp = arrow.now().shift(hours=-7).shift(days=dir_max_fileage)

    sampler = LogSampler(25)
    dir_path = Path(directory)
    file_iter = dir_path.rglob('*') if recursive else dir_path.glob('*')

    for item in file_iter:
        if item.is_file():
            if check_exclude_pattern(item, exclude_patterns):
                log.debug(logger.system(f"excluded file {item}"))
                continue
            itemTime = arrow.get(item.stat().st_mtime)
            effective_mtime = get_effective_file_age(
                item, itemTime.datetime.replace(tzinfo=None),
                max_age_threshold=dir_max_fileage_tstamp.datetime.replace(tzinfo=None),
                compressed_age_detection=compressed_age_detection)
            itemTime = arrow.get(effective_mtime)
            if itemTime < dir_max_fileage_tstamp:
                if check_filename_pattern(item, file_extensions):
                    try:
                        file_size = item.stat().st_size
                        age_days = (arrow.now() - itemTime).days
                        if dry_run:
                            space_freed += file_size
                            global_metrics.add_file(file_size)
                            if sampler.should_log():
                                log.info(logger.dry_run(f"remove file {item}",
                                                       age_days=age_days, size=format_size(file_size)))
                        else:
                            item.unlink()
                            space_freed += file_size
                            global_metrics.add_file(file_size)
                            if sampler.should_log():
                                log.info(logger.action(f"removed file {item}",
                                                      age_days=age_days, size=format_size(file_size)))
                    except PermissionError:
                        log.warning(logger.system(f"permission denied removing file {item}"))
                        global_metrics.add_error()
    return space_freed


# ── ABRT Cleanup ─────────────────────────────────────────────────────
def extract_date_from_directory_name(directory_name: str) -> Optional[datetime.datetime]:
    """Extracts a datetime from a directory name like YYYY-MM-DD-HH-MM-SS."""
    pattern = r'(\d{4})[-_](\d{2})[-_](\d{2})[-_](\d{2})[-_](\d{2})[-_](\d{2})'
    match = re.search(pattern, directory_name)
    if match:
        try:
            return datetime.datetime(*map(int, match.groups()))
        except Exception:
            return None
    return None


def simulate_cleanup(directory: str) -> int:
    """Simulate cleanup and return estimated space freed."""
    total_size = 0
    try:
        for file_path in Path(directory).rglob('*'):
            try:
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            except OSError:
                continue
    except OSError:
        pass
    return total_size


def delete_old_abrt_directories(abrt_directory: str, max_age_days: int, dry_run: bool = False) -> int:
    """Delete ABRT directories older than max_age_days."""
    validate_path_safety(abrt_directory, context="delete_old_abrt_directories")
    abrt_path = Path(abrt_directory)
    if not abrt_path.exists():
        log.warning(logger.system(f"ABRT directory does not exist: {abrt_directory}"))
        return 0

    space_freed = 0
    threshold_date = datetime.datetime.now() - datetime.timedelta(days=max_age_days)

    try:
        for entry in abrt_path.iterdir():
            if entry.is_dir():
                dir_date = extract_date_from_directory_name(entry.name)
                if dir_date and dir_date < threshold_date:
                    freed = simulate_cleanup(str(entry))
                    space_freed += freed
                    if dry_run:
                        log.info(logger.dry_run("ABRT directory cleanup",
                                               target=str(entry),
                                               potential_savings=format_size(freed)))
                    else:
                        shutil.rmtree(entry)
                        log.info(logger.action("ABRT directory removed",
                                              target=str(entry),
                                              freed=format_size(freed)))
    except Exception as e:
        log.error(logger.error_with_context(abrt_directory, e))
        global_metrics.add_error()

    return space_freed


def cleanup_empty_abrt_directories(abrt_directory: str) -> None:
    """Clean up empty ABRT directories and old files."""
    validate_path_safety(abrt_directory, context="cleanup_empty_abrt_directories")
    abrt_path = Path(abrt_directory)
    threshold_date = datetime.datetime.now() - datetime.timedelta(days=30)
    try:
        for file_path in sorted(abrt_path.rglob('*'), reverse=True):
            try:
                if file_path.is_file():
                    file_timestamp = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_timestamp < threshold_date:
                        file_path.unlink()
                        log.info(logger.action(f"deleted file {file_path}"))
                        global_metrics.add_file()
                elif file_path.is_dir() and not any(file_path.iterdir()):
                    file_path.rmdir()
                    log.info(logger.action(f"removed empty directory {file_path}"))
                    global_metrics.add_directory()
            except OSError:
                continue
    except Exception as e:
        log.error(logger.error_with_context(abrt_directory, e))
        global_metrics.add_error()


def delete_abrt_directories_by_size(abrt_directory: str, max_size: str, dry_run: bool = False) -> int:
    """Delete ABRT directories when total size exceeds max_size."""
    validate_path_safety(abrt_directory, context="delete_abrt_directories_by_size")
    abrt_path = Path(abrt_directory)
    if not abrt_path.exists():
        return 0

    size_threshold_bytes = convert_size_to_bytes(max_size)
    space_freed = 0

    try:
        directories_with_sizes = []
        for entry in abrt_path.iterdir():
            if entry.is_dir():
                try:
                    dir_size = sum(
                        f.stat().st_size
                        for f in entry.rglob('*')
                        if f.is_file()
                    )
                    directories_with_sizes.append((entry, dir_size))
                except OSError:
                    continue

        directories_with_sizes.sort(key=lambda x: x[1], reverse=True)
        total_size = sum(size for _, size in directories_with_sizes)

        for dir_path, dir_size in directories_with_sizes:
            if total_size > size_threshold_bytes:
                if dry_run:
                    space_freed += dir_size
                    global_metrics.add_directory()
                    log.info(logger.dry_run(f"remove directory over size limit {dir_path}",
                                           size=format_size(dir_size), operation="size_cleanup"))
                else:
                    shutil.rmtree(dir_path)
                    space_freed += dir_size
                    global_metrics.add_directory()
                    log.info(logger.action(f"deleted directory over size limit {dir_path}",
                                          size=format_size(dir_size)))
                total_size -= dir_size
    except Exception as e:
        log.error(logger.error_with_context(abrt_directory, e))
        global_metrics.add_error()

    return space_freed


# ── Journald Cleanup ─────────────────────────────────────────────────
def is_systemd_available() -> bool:
    """Check if the system is running systemd."""
    return os.path.isdir('/run/systemd/system')


def get_journald_disk_usage() -> int:
    """Return current journald disk usage in bytes, or 0 on failure."""
    try:
        result = subprocess.run(
            ['journalctl', '--disk-usage'],
            capture_output=True, text=True, check=True
        )
        match = re.search(r'([\d.]+)\s*([KMGTP]?i?B?)', result.stdout, re.IGNORECASE)
        if match:
            return convert_size_to_bytes(match.group(0))
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        pass
    return 0


def cleanup_journald(max_size: str, max_age: str, dry_run: bool = False) -> int:
    """Vacuum systemd journal logs by size and/or age."""
    if not is_systemd_available():
        log.info(logger.system("systemd not detected, skipping journald cleanup"))
        return 0

    usage_before = get_journald_disk_usage()
    if usage_before == 0:
        log.info(logger.system("could not determine journald disk usage, skipping"))
        return 0

    log.info(logger.system("journald disk usage before cleanup",
                          current_usage=format_size(usage_before),
                          max_size=max_size, max_age=max_age))

    if dry_run:
        max_size_bytes = convert_size_to_bytes(max_size)
        potential_savings = max(0, usage_before - max_size_bytes)
        log.info(logger.dry_run("vacuum journald logs",
                               current_usage=format_size(usage_before),
                               potential_savings=format_size(potential_savings)))
        return potential_savings

    size_bytes = convert_size_to_bytes(max_size)
    if size_bytes >= 1024 ** 3:
        vacuum_size_arg = f"{size_bytes // (1024 ** 3)}G"
    elif size_bytes >= 1024 ** 2:
        vacuum_size_arg = f"{size_bytes // (1024 ** 2)}M"
    elif size_bytes >= 1024:
        vacuum_size_arg = f"{size_bytes // 1024}K"
    else:
        vacuum_size_arg = f"{size_bytes}"

    cmd = [
        'journalctl',
        f'--vacuum-size={vacuum_size_arg}',
        f'--vacuum-time={max_age}',
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log.info(logger.action("journalctl vacuum completed", output=result.stdout.strip()))
    except subprocess.CalledProcessError as e:
        log.error(logger.error_with_context("journalctl vacuum", e))
        global_metrics.add_error()
        return 0

    usage_after = get_journald_disk_usage()
    space_freed = max(0, usage_before - usage_after)

    log.info(logger.action("journald cleanup completed",
                          before=format_size(usage_before),
                          after=format_size(usage_after),
                          freed=format_size(space_freed)))
    return space_freed


# ── Audit Cleanup ────────────────────────────────────────────────────
def audit_scan_files(audit_path: str, disk_percent: float) -> Tuple[int, int]:
    """Scans and deletes audit log files until disk usage drops below 50%."""
    audit_dir = Path(audit_path)
    sorted_audit_files = sorted(audit_dir.glob('audit.log.*'))
    current_disk_usage = disk_percent
    bytes_freed = 0
    files_removed = 0

    while current_disk_usage > 50 and sorted_audit_files:
        audit_last_file = sorted_audit_files.pop(-1)
        try:
            file_size = audit_last_file.stat().st_size
        except OSError:
            file_size = 0
        audit_last_file.unlink()
        bytes_freed += file_size
        files_removed += 1
        total, used, free, percent = disk_usage(audit_path)
        current_disk_usage = percent
        log.info(logger.action(f"removed file {audit_last_file}",
                               size=format_size(file_size),
                               disk_usage_after=f"{current_disk_usage}%"))
        global_metrics.add_file()

    log.info(logger.system("disk cleanup completed"))
    return bytes_freed, files_removed


def check_auditd(audit_percent: int = 50) -> Tuple[int, int]:
    """Check and clean up audit logs if disk usage exceeds threshold."""
    audit_path = '/var/log/audit'
    disk_total, disk_used, disk_percent = partition_usage(audit_path)

    log.info(logger.system("AuditD cleanup starting",
                          path=audit_path,
                          current_usage=f"{disk_percent}%",
                          threshold=f"{audit_percent}%"))

    if same_partition(audit_path, '/var/log'):
        log.warning(logger.system("AuditD not on dedicated partition, skipping cleanup"))
        return 0, 0
    elif disk_percent > int(audit_percent):
        return audit_scan_files(audit_path, disk_percent)
    else:
        return 0, 0


# ── Service Management ───────────────────────────────────────────────
def count_deleted_files_procfs(service_name: str) -> int:
    """Count deleted open file handles for a service using /proc filesystem."""
    count = 0
    try:
        pids = subprocess.check_output(['pgrep', service_name], text=True).strip().split('\n')
        for pid in pids:
            if pid:
                try:
                    fd_dir = Path(f"/proc/{pid}/fd")
                    if fd_dir.exists():
                        for fd in fd_dir.iterdir():
                            try:
                                link_target = os.readlink(str(fd))
                                if '(deleted)' in link_target:
                                    count += 1
                            except OSError:
                                continue
                except OSError:
                    continue
    except subprocess.CalledProcessError:
        pass
    except Exception as e:
        log.debug(logger.error_with_context(f"count_deleted_files for {service_name}", e))

    return count


def run_check_services(services: List[str]) -> None:
    """Checks each service for open deleted file handles and restarts if needed."""
    for service in services:
        log.info(logger.system(f"checking {service} for open file handles"))
        service_count = count_deleted_files_procfs(service)
        log.info(logger.system(f"found {service_count} deleted open file handles",
                              service=service))
        if service_count > 0:
            restart_service(service)


def restart_service(service_name: str) -> None:
    """Restart a systemd service."""
    try:
        subprocess.run(["systemctl", "restart", service_name], check=True)
        log.info(logger.action(f"restarted service {service_name} successfully"))
    except subprocess.CalledProcessError as e:
        log.error(logger.error_with_context(service_name, e))
        global_metrics.add_error()
