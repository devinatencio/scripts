#!/usr/bin/python3
"""
Disk Cleanup Utility - Configuration Module

This module contains configuration management, validation, exceptions,
path safety checks, and shared utility functions.

Author: Devin Acosta
Version: 3.0.0
Date: 2026-04-18
"""

import logging
import os
import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from diskcleanup.logging import LogHelper


# ── Custom exceptions ────────────────────────────────────────────────
class DiskCleanupError(Exception):
    """Base exception for disk cleanup operations."""
    pass

class ConfigError(DiskCleanupError):
    """Raised when configuration is invalid or cannot be read."""
    pass

class CleanupOperationError(DiskCleanupError):
    """Raised when a cleanup operation fails."""
    pass


# ── Module-level logger (may be None before init_runtime) ───────────
logger = LogHelper()
log = None  # type: Optional[logging.Logger]


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


# ── Utility functions ────────────────────────────────────────────────
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

    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?i?B?)', size_str, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")

    number = float(match.group(1))
    unit = match.group(2).upper()

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
        return int(number)


def has_slashes(filename: str) -> bool:
    """Check if filename contains slashes (absolute path)."""
    return '/' in filename


# ── Configuration reading and validation ─────────────────────────────
def find_yaml_config() -> Optional[str]:
    """Find YAML configuration file in current directory."""
    # __file__ is inside diskcleanup/ package, so go up one level
    current_dir = Path(__file__).resolve().parent.parent
    for name in ('diskcleanup.yaml', 'diskcleanup.yml', 'config.yaml', 'config.yml'):
        config_path = current_dir / name
        if config_path.exists():
            return str(config_path)
    return None


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

        # Validate compressed_age_detection if present
        if 'compressed_age_detection' in main_config:
            if not isinstance(main_config['compressed_age_detection'], bool):
                if log is not None:
                    log.error(logger.config("validation failed - compressed_age_detection must be true or false"))
                return False

        return True
    except Exception as e:
        if log is not None:
            log.error(logger.config("validation failed with exception", error=str(e)))
        return False
