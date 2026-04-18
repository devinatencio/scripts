#!/usr/bin/python3
"""
Disk Cleanup Utility - Core Functions Module

This module contains all the core business logic including:
- Configuration management and validation
- File and directory cleanup operations
- ABRT crash dump management
- System health monitoring
- Service management
- Disk usage calculations

Author: Devin Atencio
Version: 2.5.0
Date: 2026-04-17
"""

import arrow
import datetime
import json
import logging
import os
import re
import shutil
import subprocess
import time
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

# Import from our logging module
from diskcleanup_logging import LogHelper, LogSampler, OperationMetrics


# Custom exceptions for clearer error handling
class DiskCleanupError(Exception):
    """Base exception for disk cleanup operations."""
    pass

class ConfigError(DiskCleanupError):
    """Raised when configuration is invalid or cannot be read."""
    pass

class CleanupOperationError(DiskCleanupError):
    """Raised when a cleanup operation fails."""
    pass


# Global instances - will be initialized by main script
logger = LogHelper()
log = None  # Will be set by main script
global_metrics = None  # Will be set by main script

# Global variables
rc_files: Dict[str, Dict[str, int]] = {}
SCRIPTVER = "2.5.0"
SCRIPTDATE = "2026-04-17"

# ── Safety: Protected paths that must never be targeted for cleanup ──
PROTECTED_PATHS = frozenset({
    '/',
    '/bin', '/sbin', '/usr', '/usr/bin', '/usr/sbin', '/usr/lib', '/usr/lib64',
    '/lib', '/lib64',
    '/boot',
    '/dev',
    '/etc',
    '/home',
    '/proc', '/sys',
    '/root',
    '/run',
    '/snap',
    '/srv',
    '/opt',
})

# Minimum directory depth required (e.g. /var/log = depth 2)
MIN_DIRECTORY_DEPTH = 2


def is_path_protected(path: str) -> bool:
    """Check whether a path is protected from cleanup operations.

    A path is considered protected if:
    - It resolves to one of the PROTECTED_PATHS (exact match after normalization)
    - It is shallower than MIN_DIRECTORY_DEPTH (e.g. single-level like /var)
    - It is a parent of any protected path (e.g. / is parent of /etc)
    """
    resolved = os.path.realpath(os.path.normpath(path))

    # Exact match against protected set
    if resolved in PROTECTED_PATHS:
        return True

    # Depth check — count non-empty components after splitting on /
    parts = [p for p in resolved.split('/') if p]
    if len(parts) < MIN_DIRECTORY_DEPTH:
        return True

    # Check if the resolved path is a parent of any protected path
    # (catches symlinks or bind-mounts that effectively point to /)
    resolved_with_sep = resolved if resolved.endswith('/') else resolved + '/'
    for protected in PROTECTED_PATHS:
        if protected != '/' and protected.startswith(resolved_with_sep):
            return True

    return False


def validate_path_safety(path: str, context: str = "") -> None:
    """Raise ConfigError if *path* is protected.

    Call this before any destructive operation.  *context* is included in the
    error message to help the operator locate the offending config entry.
    """
    if is_path_protected(path):
        msg = (
            f"SAFETY BLOCK: refusing to operate on protected path '{path}'"
            f"{' (' + context + ')' if context else ''}. "
            "This path is either a critical system directory or too shallow to be safe."
        )
        if log is not None:
            log.critical(msg)
        raise ConfigError(msg)

@dataclass
class CleanupConfig:
    """Configuration settings for disk cleanup operations."""
    # Main settings
    max_fileage: int
    max_filesize: str
    audit_percent: int
    abrt_maxage: int
    abrt_maxsize: str
    abrt_directory: str
    log_file: str
    directories_to_check: List[str]
    file_extensions: List[str]
    check_services: List[str]

    # Files to monitor
    files: Dict[str, Any]

    # Advanced directory settings
    directories: Dict[str, Dict[str, Any]]

    @classmethod
    def from_config_dict(cls, files: Dict[str, Any], main: Dict[str, Any], directories: Dict[str, Any]) -> 'CleanupConfig':
        """Create CleanupConfig from configuration dictionaries."""
        return cls(
            max_fileage=main['max_fileage'],
            max_filesize=main['max_filesize'],
            audit_percent=main['audit_percent'],
            abrt_maxage=main['abrt_maxage'],
            abrt_maxsize=main['abrt_maxsize'],
            abrt_directory=main['abrt_directory'],
            log_file=main['log_file'],
            directories_to_check=main['directories_to_check'],
            file_extensions=main['file_extensions'],
            check_services=main.get('check_services', []),
            files=files,
            directories=directories
        )

# Utility Functions
def format_size(size_bytes: int) -> str:
    """Format bytes into human readable format."""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def convert_size_to_bytes(size_str: str) -> int:
    """Convert human readable size to bytes."""
    size_str = size_str.strip()
    if not size_str:
        return 0

    # Extract number and unit
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?i?B?)$', size_str, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")

    number = float(match.group(1))
    unit = match.group(2).upper()

    # Convert to bytes based on unit
    multipliers = {
        'B': 1,
        'K': 1024, 'KB': 1024, 'KIB': 1024,
        'M': 1024**2, 'MB': 1024**2, 'MIB': 1024**2,
        'G': 1024**3, 'GB': 1024**3, 'GIB': 1024**3,
        'T': 1024**4, 'TB': 1024**4, 'TIB': 1024**4
    }

    if unit in multipliers:
        return int(number * multipliers[unit])
    else:
        # Default to bytes if no unit specified
        return int(number)

def has_slashes(filename: str) -> bool:
    """Check if filename contains slashes (absolute path)."""
    return '/' in filename

# ABRT Functions
def extract_date_from_directory_name(directory_name: str) -> Optional[datetime.datetime]:
    """
    Extracts a datetime object from a directory name using a pattern like YYYY-MM-DD-HH-MM-SS.
    Returns None if no date is found.
    """
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
    """
    Delete ABRT directories older than max_age_days.
    """
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
        # Clean up old files first (bottom-up so we can remove empty dirs after)
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

        # Sort by size (largest first) and delete until under threshold
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

# File Operations
def truncate_log_file(filename: str, file_size: str) -> None:
    """
    Truncates a log file if it exceeds a specified size.
    """
    file_path = Path(filename)
    try:
        bytes_to_compare = convert_size_to_bytes(file_size)
        actual_size = file_path.stat().st_size if file_path.exists() else 0
    except OSError:
        actual_size = 0
    if actual_size > bytes_to_compare:
        with open(filename, 'r+') as file:
            file.truncate(bytes_to_compare)
        # Only log if logging system is available
        if log is not None:
            log.info(logger.action(f"truncated file {filename}",
                                  target_size=file_size))

def find_yaml_config() -> Optional[str]:
    """Find YAML configuration file in current directory."""
    current_dir = Path(__file__).resolve().parent
    for name in ('diskcleanup.yaml', 'diskcleanup.yml', 'config.yaml', 'config.yml'):
        config_path = current_dir / name
        if config_path.exists():
            return str(config_path)
    return None

def truncate_file(filename: str) -> None:
    """Truncate a file to 0 bytes."""
    try:
        Path(filename).write_text('')
        log.info(logger.action(f"truncated file {filename} to 0 bytes"))
        global_metrics.add_file()
    except OSError as e:
        log.error(logger.error_with_context(filename, e))
        global_metrics.add_error()

def check_filename_pattern(file_path: Path, file_extensions: List[str]) -> bool:
    """Check if a file matches any of the specified extensions."""
    filename = file_path.name
    for extension in file_extensions:
        # Support regex patterns
        if re.search(extension, filename):
            return True
    return False


def check_exclude_pattern(file_path: Path, exclude_patterns: List[str]) -> bool:
    """Check if a file matches any exclude pattern (should be skipped).

    Patterns are matched against the full path and the filename.
    Returns True if the file should be excluded.
    """
    if not exclude_patterns:
        return False
    full_path = str(file_path)
    filename = file_path.name
    for pattern in exclude_patterns:
        if re.search(pattern, full_path) or re.search(pattern, filename):
            return True
    return False

# Directory Cleanup Functions
def advanced_cleanup_directory(directory: str, max_age_days: int, file_pattern: str,
                               dry_run: bool = False,
                               exclude_patterns: Optional[List[str]] = None,
                               recursive: bool = True) -> int:
    """
    Performs advanced cleanup of a directory based on file age and regex pattern.
    Recursive by default. Set recursive=False to scan only the top-level directory.
    """
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

        sampler = LogSampler(50)  # Log every 50th file for large operations
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
                        # Progress logging for large operations
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
                      recursive: bool = False) -> int:
    """
    Performs cleanup of files in a directory based on age and extensions.
    Set recursive=True to scan subdirectories as well.
    """
    validate_path_safety(directory, context="directory_cleanup")
    if exclude_patterns is None:
        exclude_patterns = []
    space_freed = 0
    log.info(logger.system(f"starting cleanup for {directory}",
                          max_age=max_fileage, extensions=file_extensions,
                          recursive=recursive))

    dir_max_fileage = int(f"-{max_fileage}")
    dir_max_fileage_tstamp = arrow.now().shift(hours=-7).shift(days=dir_max_fileage)

    sampler = LogSampler(25)  # Log every 25th file
    dir_path = Path(directory)
    file_iter = dir_path.rglob('*') if recursive else dir_path.glob('*')

    for item in file_iter:
        if item.is_file():
            if check_exclude_pattern(item, exclude_patterns):
                log.debug(logger.system(f"excluded file {item}"))
                continue
            itemTime = arrow.get(item.stat().st_mtime)
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

# Disk Operations
def disk_cleanup() -> int:
    """
    Performs disk cleanup by truncating files that exceed their maximum allowed size.
    """
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

# Configuration Functions
def readConfig(filename: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    try:
        with open(filename, 'r') as yaml_file:
            config = yaml.safe_load(yaml_file)

        required_keys = ['files', 'main', 'directories']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ConfigError(f"Missing required configuration sections: {', '.join(missing_keys)}")

        return config['files'], config['main'], config['directories']
    except yaml.YAMLError as e:
        if log is not None:
            log.error(logger.config("failed to parse YAML configuration", error=str(e)))
        raise ConfigError(f"Invalid YAML: {e}") from e
    except ConfigError:
        raise
    except Exception as e:
        if log is not None:
            log.error(logger.config("failed to read configuration file", error=str(e)))
        raise ConfigError(f"Failed to read config: {e}") from e

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

# System Health and Monitoring Functions
def check_system_health() -> Dict[str, Dict[str, Union[str, int, float]]]:
    """Check system health including disk usage for all mount points."""
    health_data = {}

    try:
        # Get all mount points
        result = subprocess.run(['df', '-h'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header

        for line in lines:
            parts = line.split()
            # Handle both Linux (6 columns) and macOS (8+ columns) df output formats
            if len(parts) >= 6:
                filesystem = parts[0]
                size = parts[1]
                used = parts[2]
                available = parts[3]
                percent_used_str = parts[4].rstrip('%')

                # macOS df -h shows: Filesystem Size Used Avail Capacity iused ifree %iused Mounted_on
                # Linux df -h shows: Filesystem Size Used Avail Use% Mounted_on
                if len(parts) >= 8:  # macOS format with inode columns
                    mount_point = parts[8] if len(parts) > 8 else parts[7]
                else:  # Linux format
                    mount_point = parts[5]

                # Skip special filesystems and invalid mount points
                if (mount_point.startswith(('/dev', '/sys', '/proc', '/run')) or
                    filesystem.startswith('tmpfs') or
                    mount_point in ['-', 'none']):
                    continue

                try:
                    percent_used = int(percent_used_str)
                except ValueError:
                    percent_used = 0

                health_data[mount_point] = {
                    'filesystem': filesystem,
                    'size': size,
                    'used': used,
                    'available': available,
                    'percent_used': percent_used,
                    'status': get_health_status(percent_used)
                }
    except subprocess.CalledProcessError as e:
        log.error(logger.error_with_context("df command", e))
    except Exception as e:
        log.error(logger.error_with_context("system health check", e))

    return health_data

def get_health_status(percent_used: int) -> str:
    """Get health status based on disk usage percentage."""
    if percent_used >= 95:
        return "Critical"
    elif percent_used >= 85:
        return "Warning"
    elif percent_used >= 75:
        return "Caution"
    else:
        return "Good"

def partition_usage(path: str) -> Tuple[int, int, float]:
    """Get partition usage for a given path."""
    try:
        usage = shutil.disk_usage(path)
        percent = (usage.used / usage.total) * 100 if usage.total > 0 else 0
        return usage.total, usage.used, percent
    except OSError:
        return 0, 0, 0.0

def disk_usage(path: str) -> Tuple[int, int, int, float]:
    """Get disk usage for a path."""
    try:
        usage = shutil.disk_usage(path)
        percent = (usage.used / usage.total) * 100 if usage.total > 0 else 0
        return usage.total, usage.used, usage.free, percent
    except OSError:
        return 0, 0, 0, 0.0

def same_partition(path1: str, path2: str) -> bool:
    """Check if two paths are on the same partition."""
    try:
        stat1 = os.stat(path1)
        stat2 = os.stat(path2)
        return stat1.st_dev == stat2.st_dev
    except OSError:
        return False

def calculate_space_freed(health_before: Dict, health_after: Dict) -> int:
    """
    Calculate actual space freed based on health data.

    Note: df -h uses rounded values (e.g., 1.2G, 456M) which may not detect
    small changes accurately. This function attempts to calculate based on
    the 'used' field differences, but may return 0 for small cleanups due
    to rounding precision in df output.
    """
    total_freed = 0
    detected_changes = False

    for mount_point in health_before:
        if mount_point in health_after:
            try:
                used_before = health_before[mount_point]['used']
                used_after = health_after[mount_point]['used']

                # Convert human readable sizes to bytes for calculation
                before_bytes = convert_size_to_bytes(used_before)
                after_bytes = convert_size_to_bytes(used_after)

                if before_bytes > after_bytes:
                    freed_amount = before_bytes - after_bytes
                    total_freed += freed_amount
                    detected_changes = True
                    log.debug(logger.system(f"detected space freed on {mount_point}",
                                          before=used_before, after=used_after,
                                          freed=format_size(freed_amount)))
            except (KeyError, ValueError) as e:
                log.debug(logger.system(f"could not calculate space freed for {mount_point}",
                                      error=str(e)))
                continue

    if not detected_changes:
        log.debug(logger.system("df -h precision insufficient to detect space freed",
                              note="This is normal for small cleanups on large filesystems"))

    return total_freed

# Audit Functions
def audit_scan_files(audit_path: str, disk_percent: float) -> Tuple[int, int]:
    """
    Scans and deletes audit log files until disk usage drops below 50%.
    Returns a tuple of (bytes_freed, files_removed).
    """
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
    """Check and clean up audit logs if disk usage exceeds threshold.
    Returns a tuple of (bytes_freed, files_removed).
    """
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

# Service Management Functions
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
                                # Use os.readlink directly — Path.resolve()
                                # follows the link and loses the '(deleted)' marker
                                link_target = os.readlink(str(fd))
                                if '(deleted)' in link_target:
                                    count += 1
                            except OSError:
                                continue
                except OSError:
                    continue
    except subprocess.CalledProcessError:
        # Service not running
        pass
    except Exception as e:
        log.debug(logger.error_with_context(f"count_deleted_files for {service_name}", e))

    return count

def run_check_services(services: List[str]) -> None:
    """
    Checks each service for open deleted file handles and restarts if needed.
    """
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

# Configuration Validation
def validate_config(config: Dict[str, Any]) -> bool:
    """Enhanced configuration validation with detailed checks."""
    try:
        main_config = config['main']

        # Validate required fields
        required_fields = ['max_fileage', 'max_filesize', 'directories_to_check', 'file_extensions']
        missing_fields = [field for field in required_fields if field not in main_config]
        if missing_fields:
            if log is not None:
                log.error(logger.config("validation failed - missing required fields",
                                       missing_fields=missing_fields))
            return False

        # Validate data types and ranges
        if not isinstance(main_config['max_fileage'], int) or main_config['max_fileage'] <= 0:
            if log is not None:
                log.error(logger.config("validation failed - max_fileage must be a positive integer"))
            return False

        if not isinstance(main_config['audit_percent'], int) or not (0 <= main_config['audit_percent'] <= 100):
            if log is not None:
                log.error(logger.config("validation failed - audit_percent must be an integer between 0 and 100"))
            return False

        # Validate file size format
        try:
            convert_size_to_bytes(main_config['max_filesize'])
        except ValueError as e:
            if log is not None:
                log.error(logger.config("validation failed - invalid max_filesize format", error=str(e)))
            return False

        # Validate directories exist
        missing_dirs = []
        for dir_path in main_config['directories_to_check']:
            if is_path_protected(dir_path):
                if log is not None:
                    log.error(logger.config(
                        f"validation failed - protected path in directories_to_check: {dir_path}"))
                return False
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)

        if missing_dirs:
            if log is not None:
                log.warning(logger.config("directories do not exist", missing_dirs=missing_dirs))
            # Don't fail validation, just warn

        # Validate advanced directories section
        directories = config.get('directories', {})
        if directories:
            for dir_path in directories:
                if is_path_protected(dir_path):
                    if log is not None:
                        log.error(logger.config(
                            f"validation failed - protected path in directories section: {dir_path}"))
                    return False

        # Validate abrt_directory if present
        abrt_dir = main_config.get('abrt_directory', '')
        if abrt_dir and is_path_protected(abrt_dir):
            if log is not None:
                log.error(logger.config(
                    f"validation failed - protected path for abrt_directory: {abrt_dir}"))
            return False

        return True
    except Exception as e:
        if log is not None:
            log.error(logger.config("validation failed with exception", error=str(e)))
        return False

# Run History and Trending Functions
DEFAULT_HISTORY_FILE = "diskcleanup_history.jsonl"
MAX_HISTORY_ENTRIES = 500

def get_history_path(config_settings: Dict[str, Any], script_dir: str) -> str:
    """Resolve the history file path from config or defaults."""
    history_file = config_settings.get('history_file', DEFAULT_HISTORY_FILE)
    if '/' in history_file:
        return history_file
    return f"{script_dir}/{history_file}"

def save_run_history(
    history_path: str,
    health_before: Dict[str, Dict[str, Any]],
    health_after: Dict[str, Dict[str, Any]],
    space_freed: int,
    files_processed: int,
    dirs_processed: int,
    errors: int,
    execution_time: float,
    dry_run: bool,
    config_file: str,
    cleanup_breakdown: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    """Append a run summary to the JSONL history file."""
    mount_usage = {}
    for mp, data in health_after.items():
        before_pct = health_before.get(mp, {}).get('percent_used', 0)
        mount_usage[mp] = {
            'before_pct': before_pct,
            'after_pct': data['percent_used'],
            'size': data.get('size', ''),
            'available': data.get('available', ''),
        }

    # Convert breakdown to serializable format
    breakdown = {}
    if cleanup_breakdown:
        for path, info in cleanup_breakdown.items():
            breakdown[path] = {
                'bytes_freed': info.get('bytes_freed', 0),
                'freed': format_size(info.get('bytes_freed', 0)),
                'files': info.get('files', 0),
                'type': info.get('type', ''),
            }

    entry = {
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'hostname': _get_hostname(),
        'config_file': config_file,
        'dry_run': dry_run,
        'space_freed_bytes': space_freed,
        'space_freed': format_size(space_freed),
        'files_processed': files_processed,
        'dirs_processed': dirs_processed,
        'errors': errors,
        'execution_time_sec': round(execution_time, 2),
        'mounts': mount_usage,
        'breakdown': breakdown,
    }

    history_file = Path(history_path)
    try:
        with open(history_file, 'a') as f:
            f.write(json.dumps(entry, separators=(',', ':')) + '\n')
    except OSError as e:
        if log is not None:
            log.warning(logger.system(f"failed to write run history to {history_path}", error=str(e)))


def load_run_history(history_path: str, last_n: int = 0) -> List[Dict[str, Any]]:
    """Load run history from the JSONL file. Returns newest-first."""
    history_file = Path(history_path)
    if not history_file.exists():
        return []

    entries = []
    try:
        with open(history_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []

    # Newest first
    entries.reverse()

    if last_n > 0:
        entries = entries[:last_n]

    return entries


def trim_history_file(history_path: str) -> None:
    """Trim history file to MAX_HISTORY_ENTRIES if it grows too large."""
    history_file = Path(history_path)
    if not history_file.exists():
        return

    try:
        with open(history_file, 'r') as f:
            lines = f.readlines()

        if len(lines) > MAX_HISTORY_ENTRIES:
            # Keep the most recent entries
            with open(history_file, 'w') as f:
                f.writelines(lines[-MAX_HISTORY_ENTRIES:])
    except OSError:
        pass


def print_report(history_path: str, last_n: int = 20) -> None:
    """Print a trending report from run history."""
    console = Console()
    entries = load_run_history(history_path, last_n=last_n)

    if not entries:
        console.print("[yellow]No run history found.[/yellow]")
        console.print(f"[dim]History file: {history_path}[/dim]")
        return

    hostname = entries[0].get('hostname', 'unknown')

    # Summary stats
    total_freed = sum(e.get('space_freed_bytes', 0) for e in entries if not e.get('dry_run'))
    total_files = sum(e.get('files_processed', 0) for e in entries if not e.get('dry_run'))
    total_errors = sum(e.get('errors', 0) for e in entries)
    prod_runs = [e for e in entries if not e.get('dry_run')]
    dry_runs = [e for e in entries if e.get('dry_run')]

    # Header
    console.rule(f"[bold cyan]📊 Disk Cleanup Trending Report — {hostname}", style="cyan")

    summary = Text()
    summary.append(f"History: ", style="bold")
    summary.append(f"{len(entries)} runs", style="cyan")
    summary.append(f"  ({len(prod_runs)} live, {len(dry_runs)} dry-run)\n", style="dim")
    summary.append(f"Total Space Freed: ", style="bold")
    summary.append(f"{format_size(total_freed)}\n", style="green")
    summary.append(f"Total Files Processed: ", style="bold")
    summary.append(f"{total_files:,}\n", style="cyan")
    if total_errors > 0:
        summary.append(f"Total Errors: ", style="bold")
        summary.append(f"{total_errors:,}\n", style="red")
    summary.append(f"History File: ", style="bold")
    summary.append(f"{history_path}\n", style="dim")

    console.print(Panel(summary, title="Summary", border_style="cyan", padding=(0, 2)))

    # Run history table
    table = Table(title="Run History (newest first)", show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Timestamp", style="cyan", no_wrap=True)
    table.add_column("Mode", justify="center")
    table.add_column("Freed", justify="right", style="green")
    table.add_column("Files", justify="right")
    table.add_column("Dirs", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Duration", justify="right")

    for entry in entries:
        mode = "[magenta]dry-run[/magenta]" if entry.get('dry_run') else "[green]live[/green]"
        errors_str = f"[red]{entry.get('errors', 0)}[/red]" if entry.get('errors', 0) > 0 else "[dim]0[/dim]"
        table.add_row(
            entry.get('timestamp', ''),
            mode,
            entry.get('space_freed', '0 B'),
            str(entry.get('files_processed', 0)),
            str(entry.get('dirs_processed', 0)),
            errors_str,
            f"{entry.get('execution_time_sec', 0):.1f}s",
        )

    console.print(table)

    # Top paths by space freed — aggregate across all runs
    path_totals = {}  # type: Dict[str, Dict[str, Any]]
    for entry in entries:
        breakdown = entry.get('breakdown', {})
        for path, info in breakdown.items():
            if path not in path_totals:
                path_totals[path] = {'bytes_freed': 0, 'files': 0, 'runs': 0, 'type': info.get('type', '')}
            path_totals[path]['bytes_freed'] += info.get('bytes_freed', 0)
            path_totals[path]['files'] += info.get('files', 0)
            path_totals[path]['runs'] += 1

    if path_totals:
        sorted_paths = sorted(path_totals.items(), key=lambda x: x[1]['bytes_freed'], reverse=True)

        path_table = Table(title="Top Paths by Space Freed (all runs)", show_header=True, header_style="bold magenta", expand=True)
        path_table.add_column("Path", style="cyan", no_wrap=True)
        path_table.add_column("Type", justify="center")
        path_table.add_column("Total Freed", justify="right", style="green")
        path_table.add_column("Files", justify="right")
        path_table.add_column("Runs", justify="right")
        path_table.add_column("Avg/Run", justify="right", style="yellow")

        type_labels = {
            'directory_cleanup': 'dir',
            'pattern_cleanup': 'pattern',
            'file_truncate': 'truncate',
            'abrt_cleanup': 'abrt',
            'audit_cleanup': 'audit',
        }

        for path, info in sorted_paths:
            avg = info['bytes_freed'] // info['runs'] if info['runs'] > 0 else 0
            path_table.add_row(
                path,
                type_labels.get(info['type'], info['type']),
                format_size(info['bytes_freed']),
                str(info['files']),
                str(info['runs']),
                format_size(avg),
            )

        console.print(path_table)

    # Mount point trending — show current vs oldest entry for each mount
    if len(prod_runs) >= 2:
        oldest = prod_runs[-1]
        newest = prod_runs[0]

        trend_table = Table(title="Mount Point Trends (oldest → newest live run)", show_header=True, header_style="bold magenta", expand=True)
        trend_table.add_column("Mount Point", style="cyan", no_wrap=True)
        trend_table.add_column("First Seen", justify="center")
        trend_table.add_column("Latest", justify="center")
        trend_table.add_column("Change", justify="center")

        oldest_mounts = oldest.get('mounts', {})
        newest_mounts = newest.get('mounts', {})
        all_mounts = sorted(set(list(oldest_mounts.keys()) + list(newest_mounts.keys())))

        for mp in all_mounts:
            old_pct = oldest_mounts.get(mp, {}).get('after_pct', '—')
            new_pct = newest_mounts.get(mp, {}).get('after_pct', '—')

            if isinstance(old_pct, (int, float)) and isinstance(new_pct, (int, float)):
                delta = new_pct - old_pct
                if delta > 0:
                    change_str = f"[red]+{delta:.1f}%[/red]"
                elif delta < 0:
                    change_str = f"[green]{delta:.1f}%[/green]"
                else:
                    change_str = "[dim]0%[/dim]"
                old_str = f"{old_pct}%"
                new_str = f"{new_pct}%"
            else:
                change_str = "[dim]—[/dim]"
                old_str = str(old_pct)
                new_str = str(new_pct)

            trend_table.add_row(mp, old_str, new_str, change_str)

        console.print(trend_table)

    console.rule(style="cyan")


def print_report_csv(history_path: str, last_n: int = 0) -> None:
    """Export run history as CSV to stdout."""
    entries = load_run_history(history_path, last_n=last_n)
    if not entries:
        print("No run history found.")
        return

    # Header
    print("timestamp,hostname,mode,space_freed_bytes,space_freed,files_processed,dirs_processed,errors,execution_time_sec")
    # Oldest first for CSV
    for entry in reversed(entries):
        mode = "dry-run" if entry.get('dry_run') else "live"
        print(f"{entry.get('timestamp','')},{entry.get('hostname','')},{mode},"
              f"{entry.get('space_freed_bytes',0)},{entry.get('space_freed','0 B')},"
              f"{entry.get('files_processed',0)},{entry.get('dirs_processed',0)},"
              f"{entry.get('errors',0)},{entry.get('execution_time_sec',0)}")


def _get_hostname() -> str:
    """Get the system hostname."""
    import socket
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


# UI and Display Functions
def print_health_comparison(health_before: Dict, health_after: Dict, execution_time: float, space_freed: int) -> None:
    """Print a professional side-by-side comparison of system health."""
    console = Console()

    # Create comparison table
    table = Table(title="🏥 System Health Comparison - Before vs After Cleanup", show_header=True, header_style="bold magenta")
    table.add_column("Mount Point", justify="left", style="cyan", no_wrap=True)
    table.add_column("Before", justify="center", style="red")
    table.add_column("After", justify="center", style="green")
    table.add_column("Freed", justify="center", style="bold green")
    table.add_column("Improvement", justify="center", style="bold yellow")

    # Add rows for each mount point
    for mount_point in sorted(health_before.keys()):
        if mount_point in health_after:
            before_pct = health_before[mount_point]['percent_used']
            after_pct = health_after[mount_point]['percent_used']

            # Calculate improvement
            improvement = before_pct - after_pct
            improvement_str = f"-{improvement:.1f}%" if improvement > 0 else "0%"

            # Calculate space freed for this specific mount point
            mount_space_freed = 0
            try:
                used_before = health_before[mount_point]['used']
                used_after = health_after[mount_point]['used']

                # Convert human readable sizes to bytes for calculation
                before_bytes = convert_size_to_bytes(used_before)
                after_bytes = convert_size_to_bytes(used_after)

                if before_bytes > after_bytes:
                    mount_space_freed = before_bytes - after_bytes
            except (KeyError, ValueError):
                mount_space_freed = 0

            # Get status indicators
            before_status = health_before[mount_point]['status']
            after_status = health_after[mount_point]['status']

            # Color coding for status
            before_color = {"Good": "green", "Caution": "yellow", "Warning": "orange", "Critical": "red"}.get(before_status, "white")
            after_color = {"Good": "green", "Caution": "yellow", "Warning": "orange", "Critical": "red"}.get(after_status, "white")

            # Show space freed logic - assign total to root filesystem if no per-mount detection
            if mount_space_freed > 0:
                freed_display = format_size(mount_space_freed)
            elif improvement > 0 and mount_point == '/':
                # Show total space freed on root filesystem since that's where most cleanup occurs
                freed_display = f"{format_size(space_freed)}"
            elif improvement > 0:
                # Other mount points with improvement but no detected space
                freed_display = "< 1 MB"
            else:
                freed_display = "0 B"

            table.add_row(
                mount_point,
                f"[{before_color}]{before_pct}% ({before_status})[/{before_color}]",
                f"[{after_color}]{after_pct}% ({after_status})[/{after_color}]",
                freed_display,
                f"[bold green]{improvement_str}[/bold green]" if improvement > 0 else "[dim]0%[/dim]"
            )

    console.print()
    console.print(table)

    # Summary panel
    summary_text = Text()
    summary_text.append("📊 Cleanup Summary\n\n", style="bold")
    summary_text.append("Files Processed: ", style="bold")
    summary_text.append(f"{global_metrics.files_processed:,}", style="cyan")
    summary_text.append("  •  ", style="dim")
    summary_text.append("Space Freed: ", style="bold")
    summary_text.append(format_size(space_freed), style="green")
    summary_text.append("  •  ", style="dim")
    summary_text.append("Execution Time: ", style="bold")
    summary_text.append(f"{execution_time:.1f}s", style="yellow")

    if global_metrics.errors_encountered > 0:
        summary_text.append("\n⚠️ Errors: ", style="bold red")
        summary_text.append(str(global_metrics.errors_encountered), style="red")

    panel = Panel(
        Align.center(summary_text),
        title="✅ Operation Complete",
        border_style="green",
        padding=(1, 2)
    )
    console.print(panel)

def print_compact_health_summary(health_before: Dict, health_after: Dict) -> None:
    """Print a compact system health summary."""
    console = Console()

    summary_text = Text()
    summary_text.append("🖥  System Status: ", style="bold")

    critical_mounts = [mp for mp, data in health_before.items() if data['percent_used'] >= 90]
    if critical_mounts:
        summary_text.append(f"{len(critical_mounts)} critical mount(s)", style="bold red")
    else:
        summary_text.append("All systems nominal", style="bold green")

    # Show highest usage mount
    if health_before:
        highest_usage = max(health_before.items(), key=lambda x: x[1]['percent_used'])
        mount_point, data = highest_usage
        summary_text.append(f" • Highest usage: {mount_point} ({data['percent_used']}%)", style="yellow")

    console.print(summary_text)
