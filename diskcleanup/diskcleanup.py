#!/usr/bin/env python3
"""
Disk Cleanup Utility - Main Script

A comprehensive disk cleanup solution with intelligent file management, health monitoring,
and detailed reporting capabilities. Supports dry-run analysis, pattern-based cleanup,
service restart detection, real-time system health tracking, and daemon mode for
continuous scheduled cleanup.

Author: Devin Acosta
Version: 3.0.0
Date: 2026-04-18
License: MIT

Features:
    - Intelligent directory cleanup with configurable age and pattern matching
    - Log file size monitoring and truncation
    - System health monitoring with before/after comparison
    - ABRT crash dump management
    - Systemd journal log cleanup (vacuum by size/age)
    - Daemon mode with configurable interval (no cron required)
    - Service restart for applications with deleted file handles
    - Audit log cleanup with disk usage thresholds
    - Dry-run mode with potential savings analysis
    - Rich console output with progress tracking
    - Comprehensive logging with correlation IDs
    - YAML-based configuration management

Requirements:
    - Python 3.6+
    - PyYAML, rich, arrow packages
    - Root privileges for system cleanup operations
    - Linux system with /proc filesystem

Usage:
    ./diskcleanup.py [--dry-run] [--config /path/to/config.yaml] [--verbose]
    ./diskcleanup.py --daemon [--interval 3600]   # Run as daemon
    ./diskcleanup.py --report [--last N]          # Show trending report
    ./diskcleanup.py --report-csv [--last N]      # Export history as CSV
    ./diskcleanup.py --version | -V               # Show version information
    ./diskcleanup.py --version-dialog             # Show version in GUI dialog

Configuration:
    See diskcleanup.yaml for configuration options and examples.
"""

import argparse
import logging
import os
import signal
import sys
import time
import yaml
from pathlib import Path
# Conditional import for GUI support
HAS_GUI = False
tk = None
messagebox = None
try:
    import tkinter as tk
    from tkinter import messagebox
    HAS_GUI = True
except ImportError:
    # tkinter not available - GUI features will be disabled
    pass

# Import from our modular components
from diskcleanup.logging import (
    setup_logging, OperationContext, set_current_operation_id
)
from diskcleanup.core import (
    # Core functionality
    readConfig, validate_config, setup_rc_files, find_yaml_config,
    init_runtime,
    # Cleanup operations
    directory_cleanup, advanced_cleanup_directory, disk_cleanup,
    delete_old_abrt_directories, delete_abrt_directories_by_size,
    cleanup_journald,
    check_auditd, run_check_services,
    # System monitoring
    check_system_health, calculate_space_freed,
    # UI functions
    print_health_comparison, print_compact_health_summary,
    # Run history / trending
    get_history_path, save_run_history, trim_history_file,
    print_report, print_report_csv,
    # Utilities
    format_size, has_slashes, truncate_log_file,
    # Exceptions
    ConfigError,
    # Safety
    is_path_protected, validate_path_safety,
    # Global variables
    SCRIPTVER, SCRIPTDATE, log, logger, global_metrics
)

# Shared version metadata
VERSION_FEATURES = [
    "Intelligent directory cleanup with configurable patterns",
    "Log file size monitoring and truncation",
    "System health monitoring with before/after comparison",
    "ABRT crash dump management",
    "Systemd journal log cleanup (vacuum by size/age)",
    "Daemon mode with configurable interval (no cron required)",
    "Service restart for applications with deleted file handles",
    "Audit log cleanup with disk usage thresholds",
    "Dry-run mode with potential savings analysis",
    "Rich console output with progress tracking",
]

VERSION_DESCRIPTION = (
    "A comprehensive disk cleanup solution with intelligent file management,\n"
    "health monitoring, and detailed reporting capabilities."
)

def show_version_dialog():
    """Display version information in a GUI dialog box."""
    if not HAS_GUI:
        print("GUI support not available. Showing version in console format instead.")
        show_version_console()
        return

    try:
        # Only proceed if tkinter modules are actually available
        if tk is None or messagebox is None:
            show_version_console()
            return

        # Create a hidden root window
        root = tk.Tk()
        root.withdraw()

        features_text = "\n".join(f"• {f}" for f in VERSION_FEATURES)
        version_info = f"""Disk Cleanup Utility

Version: {SCRIPTVER}
Author: Devin Acosta
Date: {SCRIPTDATE}
License: MIT

{VERSION_DESCRIPTION}

Features:
{features_text}"""

        messagebox.showinfo("Disk Cleanup Utility - Version Information", version_info)
        root.destroy()

    except Exception as e:
        # Fallback to console output if GUI fails
        print(f"GUI dialog failed: {e}")
        show_version_console()

def show_version_console():
    """Display version information in console format."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console()

    version_text = Text()
    version_text.append("Disk Cleanup Utility\n\n", style="bold cyan")
    version_text.append(f"Version: ", style="bold")
    version_text.append(f"{SCRIPTVER}\n", style="green")
    version_text.append(f"Author: ", style="bold")
    version_text.append(f"Devin Acosta\n", style="white")
    version_text.append(f"Date: ", style="bold")
    version_text.append(f"{SCRIPTDATE}\n", style="white")
    version_text.append(f"License: ", style="bold")
    version_text.append(f"MIT\n\n", style="white")

    for line in VERSION_DESCRIPTION.split('\n'):
        version_text.append(f"{line}\n", style="dim")
    version_text.append("\n")

    version_text.append("Features:\n", style="bold yellow")

    for feature in VERSION_FEATURES:
        version_text.append(f"• {feature}\n", style="dim")

    panel = Panel(version_text, title="Version Information", border_style="cyan")
    console.print(panel)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Advanced disk cleanup utility with health monitoring"
    )
    parser.add_argument(
        '--version', '-V',
        action='store_true',
        help='Show version information'
    )
    parser.add_argument(
        '--version-dialog',
        action='store_true',
        help='Show version information in a GUI dialog box'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be cleaned without actually removing files'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to YAML configuration file'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help='Increase verbosity (use -v or -vv)'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as a daemon, performing cleanup on a recurring interval'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=None,
        metavar='SECONDS',
        help='Override daemon interval in seconds (default: from YAML config or 3600)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Show trending report from run history and exit'
    )
    parser.add_argument(
        '--report-csv',
        action='store_true',
        help='Export run history as CSV to stdout and exit'
    )
    parser.add_argument(
        '--last',
        type=int,
        default=20,
        metavar='N',
        help='Number of recent runs to show in report (default: 20)'
    )
    return parser.parse_args()

def write_pid_file(pid_path):
    """Write the current PID to a file. Returns True on success."""
    try:
        pid_file = Path(pid_path)
        if pid_file.exists():
            try:
                old_pid = int(pid_file.read_text().strip())
                os.kill(old_pid, 0)
                print(f"ERROR: Another daemon instance is already running (PID {old_pid}). "
                      f"Remove {pid_path} if this is stale.")
                return False
            except (ValueError, ProcessLookupError, PermissionError):
                pass
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()))
        return True
    except OSError as e:
        print(f"WARNING: Could not write PID file {pid_path}: {e}")
        return True


def remove_pid_file(pid_path):
    """Remove the PID file on shutdown."""
    try:
        pid_file = Path(pid_path)
        if pid_file.exists():
            pid_file.unlink()
    except OSError:
        pass


# Global flag for daemon shutdown
_daemon_shutdown = False


def _handle_shutdown(signum, frame):
    """Signal handler for graceful daemon shutdown."""
    global _daemon_shutdown
    _daemon_shutdown = True


def _handle_reload(signum, frame):
    """Signal handler for SIGHUP — config is re-read each cycle, so this just wakes the sleep."""
    pass


def run_cleanup(args, yml_config, files, files_main_settings, directories_to_check,
                current_directory, script_name):
    """Execute a single cleanup pass. Returns normally on success, raises on fatal error."""
    dirtochk = files_main_settings["directories_to_check"]
    max_fileage = files_main_settings["max_fileage"]
    file_extensions = files_main_settings["file_extensions"]
    exclude_patterns = files_main_settings.get("exclude_patterns", [])
    recursive = files_main_settings.get("recursive", False)
    audit_percent = files_main_settings['audit_percent']
    abrt_maxage = files_main_settings['abrt_maxage']
    abrt_maxsize = files_main_settings['abrt_maxsize']
    abrt_directory = files_main_settings['abrt_directory']
    LOGFILE = files_main_settings['log_file']
    check_services = files_main_settings.get('check_services', [])
    compressed_age_detection = files_main_settings.get('compressed_age_detection', True)

    journald_config = {}
    try:
        with open(yml_config, 'r') as f:
            full_config = yaml.safe_load(f)
        journald_config = full_config.get('journald', {}) or {}
    except Exception:
        pass
    journald_cleanup = journald_config.get('cleanup', False)
    journald_max_size = journald_config.get('max_size', '500 MB')
    journald_max_age = journald_config.get('max_age', '30d')

    history_path = get_history_path(files_main_settings, current_directory)

    if has_slashes(LOGFILE):
        LOGFILE_PATH = LOGFILE
    else:
        LOGFILE_PATH = f"{current_directory}/{LOGFILE}"

    truncate_log_file(LOGFILE_PATH, '100M')

    with open(LOGFILE_PATH, 'a') as f:
        f.write("\n" + "=" * 72 + "\n")

    console, logger_helper, global_metrics_instance = setup_logging(
        LOGFILE_PATH, verbose=args.verbose > 0, quiet=args.daemon
    )

    import diskcleanup.core as diskcleanup_core
    init_runtime(logging.getLogger("diskcleanup"), logger_helper, global_metrics_instance)

    set_current_operation_id(global_metrics_instance.operation_id)

    start_time = time.time()
    health_before = check_system_health()
    mode_label = "daemon" if args.daemon else "standalone"
    diskcleanup_core.log.info(logger_helper.system(f"{script_name} v{SCRIPTVER} starting",
                          config_file=yml_config, dry_run=args.dry_run, mode=mode_label))
    diskcleanup_core.log.info(logger_helper.system("System health check - before cleanup"))

    # Show initial system status
    console.rule(f"[bold cyan]🚀 Disk Cleanup v{SCRIPTVER} Starting", style="cyan")
    print_compact_health_summary(health_before, health_before)
    console.rule(style="cyan")

    # Track potential/actual space savings
    total_space_freed = 0
    cleanup_breakdown = {}  # {path: {bytes_freed, files, type}}

    # Set up file monitoring
    setup_rc_files(files, files_main_settings["max_filesize"])

    # Perform Basic Directory Cleanup
    with OperationContext("dir_cleanup", "cleanup", f"scanning_{len(dirtochk)}_dirs") as metrics:
        start_files = diskcleanup_core.global_metrics.files_processed
        start_dirs = diskcleanup_core.global_metrics.directories_processed
        diskcleanup_core.log.info(logger_helper.system("Directory cleanup configuration",
                              directories=len(dirtochk), max_age=max_fileage,
                              extensions=file_extensions, targets=dirtochk))
        for dir in dirtochk:
            dir_start_files = diskcleanup_core.global_metrics.files_processed
            space = directory_cleanup(dir, max_fileage, file_extensions, args.dry_run,
                                     exclude_patterns=exclude_patterns,
                                     recursive=recursive,
                                     compressed_age_detection=compressed_age_detection)
            total_space_freed += space
            metrics.bytes_freed += space
            if space > 0:
                cleanup_breakdown[dir] = {
                    'bytes_freed': space,
                    'files': diskcleanup_core.global_metrics.files_processed - dir_start_files,
                    'type': 'directory_cleanup',
                }
                if args.dry_run:
                    diskcleanup_core.log.info(logger_helper.dry_run(f"clean directory {dir}",
                                          potential_savings=format_size(space)))
                else:
                    diskcleanup_core.log.info(logger_helper.action(f"cleaned directory {dir}",
                                         freed=format_size(space)))
        # Sync global metrics to operation metrics
        metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
        metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # File size monitoring and truncation
    with OperationContext("file_truncate", "files", f"checking_{len(files)}_files") as metrics:
        start_files = diskcleanup_core.global_metrics.files_processed
        start_dirs = diskcleanup_core.global_metrics.directories_processed
        diskcleanup_core.log.info(logger_helper.system("File truncation configuration",
                              monitored_files=len(files),
                              max_size=files_main_settings["max_filesize"]))
        if not args.dry_run:
            space = disk_cleanup()
            total_space_freed += space
            metrics.bytes_freed += space
            if space > 0:
                # Break down per-file truncations
                for file_path in diskcleanup_core.rc_files:
                    rc = diskcleanup_core.rc_files[file_path]
                    if rc['file_size'] >= rc['file_maxsize'] and rc['file_size'] != 0:
                        cleanup_breakdown[file_path] = {
                            'bytes_freed': rc['file_size'],
                            'files': 1,
                            'type': 'file_truncate',
                        }
                diskcleanup_core.log.info(logger_helper.action("disk cleanup completed", freed=format_size(space)))
        else:
            for file in diskcleanup_core.rc_files:
                file_size = diskcleanup_core.rc_files[file]['file_size']
                file_maxsize = diskcleanup_core.rc_files[file]['file_maxsize']
                if file_size >= file_maxsize and file_size != 0:
                    space = file_size
                    total_space_freed += space
                    metrics.bytes_freed += space
                    cleanup_breakdown[file] = {
                        'bytes_freed': space,
                        'files': 1,
                        'type': 'file_truncate',
                    }
                    diskcleanup_core.log.info(logger_helper.dry_run(f"truncate {file}", saving=format_size(space)))
        # Sync global metrics to operation metrics
        metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
        metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # Advanced Directory Cleanup
    with OperationContext("pattern_cleanup", "cleanup", f"scanning_{len(directories_to_check)}_pattern_dirs") as metrics:
        start_files = diskcleanup_core.global_metrics.files_processed
        start_dirs = diskcleanup_core.global_metrics.directories_processed
        diskcleanup_core.log.info(logger_helper.system("Pattern cleanup configuration",
                              directories=len(directories_to_check),
                              targets=list(directories_to_check.keys())))
        for directory in directories_to_check:
            # Use directory-specific max_fileage or fall back to global default
            dir_max_fileage = directories_to_check[directory].get('max_fileage', max_fileage)
            file_pattern = directories_to_check[directory]['file_pattern']
            # Merge global excludes with per-directory excludes
            dir_excludes = list(exclude_patterns)
            dir_exclude = directories_to_check[directory].get('exclude_pattern')
            if dir_exclude:
                if isinstance(dir_exclude, list):
                    dir_excludes.extend(dir_exclude)
                else:
                    dir_excludes.append(dir_exclude)

            # Per-directory recursive setting, falls back to global, then True (original behavior)
            dir_recursive = directories_to_check[directory].get('recursive', True)

            dir_start_files = diskcleanup_core.global_metrics.files_processed
            space = advanced_cleanup_directory(directory, dir_max_fileage, file_pattern, args.dry_run,
                                              exclude_patterns=dir_excludes,
                                              recursive=dir_recursive,
                                              compressed_age_detection=compressed_age_detection)
            total_space_freed += space
            metrics.bytes_freed += space
            if space > 0:
                cleanup_breakdown[directory] = {
                    'bytes_freed': space,
                    'files': diskcleanup_core.global_metrics.files_processed - dir_start_files,
                    'type': 'pattern_cleanup',
                }
                if args.dry_run:
                    diskcleanup_core.log.info(logger_helper.dry_run(f"clean {directory}",
                                          potential_savings=format_size(space)))
                else:
                    diskcleanup_core.log.info(logger_helper.action(f"advanced cleanup of {directory} completed",
                                         freed=format_size(space)))
        # Sync global metrics to operation metrics
        metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
        metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # AuditD Disk Cleanup
    with OperationContext("audit_cleanup", "audit", "/var/log/audit") as metrics:
        start_files = diskcleanup_core.global_metrics.files_processed
        start_dirs = diskcleanup_core.global_metrics.directories_processed
        audit_freed, audit_files = check_auditd(audit_percent)
        total_space_freed += audit_freed
        metrics.bytes_freed += audit_freed
        if audit_freed > 0:
            cleanup_breakdown['/var/log/audit'] = {
                'bytes_freed': audit_freed,
                'files': audit_files,
                'type': 'audit_cleanup',
            }
            if args.dry_run:
                diskcleanup_core.log.info(logger_helper.dry_run("audit cleanup",
                                      potential_savings=format_size(audit_freed)))
            else:
                diskcleanup_core.log.info(logger_helper.action("AuditD cleanup completed",
                                     freed=format_size(audit_freed), files=audit_files))
        metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
        metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # Perform ABRT Cleanups
    with OperationContext("abrt_cleanup", "abrt", abrt_directory.replace('/', '_')) as metrics:
        start_files = diskcleanup_core.global_metrics.files_processed
        start_dirs = diskcleanup_core.global_metrics.directories_processed
        diskcleanup_core.log.info(logger_helper.system("ABRT cleanup configuration",
                              max_age=abrt_maxage, max_size=abrt_maxsize))
        diskcleanup_core.log.info(logger_helper.system("checking crash dumps by age"))
        space_age = delete_old_abrt_directories(abrt_directory, abrt_maxage, args.dry_run)
        total_space_freed += space_age
        metrics.bytes_freed += space_age
        diskcleanup_core.log.info(logger_helper.system("checking crash dumps by size"))
        space_size = delete_abrt_directories_by_size(abrt_directory, abrt_maxsize, args.dry_run)
        total_space_freed += space_size
        metrics.bytes_freed += space_size
        abrt_total = space_age + space_size
        if abrt_total > 0:
            cleanup_breakdown[abrt_directory] = {
                'bytes_freed': abrt_total,
                'files': diskcleanup_core.global_metrics.files_processed - start_files,
                'type': 'abrt_cleanup',
            }
            diskcleanup_core.log.info(logger_helper.action("ABRT cleanup completed",
                                     freed=format_size(abrt_total)))
        # Sync global metrics to operation metrics
        metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
        metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # Journald Cleanup
    if journald_cleanup:
        with OperationContext("journald_cleanup", "journald", "/var/log/journal") as metrics:
            start_files = diskcleanup_core.global_metrics.files_processed
            start_dirs = diskcleanup_core.global_metrics.directories_processed
            diskcleanup_core.log.info(logger_helper.system("Journald cleanup configuration",
                                  max_size=journald_max_size, max_age=journald_max_age))
            space = cleanup_journald(journald_max_size, journald_max_age, args.dry_run)
            total_space_freed += space
            metrics.bytes_freed += space
            if space > 0:
                cleanup_breakdown['/var/log/journal'] = {
                    'bytes_freed': space,
                    'files': 0,
                    'type': 'journald_cleanup',
                }
                if args.dry_run:
                    diskcleanup_core.log.info(logger_helper.dry_run("vacuum journald",
                                          potential_savings=format_size(space)))
                else:
                    diskcleanup_core.log.info(logger_helper.action("Journald cleanup completed",
                                         freed=format_size(space)))
            metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
            metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # Check Services
    if len(check_services) > 0:
        with OperationContext("service_restart", "services", f"checking_{len(check_services)}_services") as metrics:
            start_files = diskcleanup_core.global_metrics.files_processed
            start_dirs = diskcleanup_core.global_metrics.directories_processed
            diskcleanup_core.log.info(logger_helper.system("Checking for open file handles",
                                  services=len(check_services)))
            run_check_services(check_services)
            # Sync global metrics to operation metrics
            metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
            metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # Check system health after cleanup
    health_after = check_system_health()
    execution_time = time.time() - start_time

    # Display results
    if args.dry_run:
        # Dry run - show potential savings
        console.rule("[bold magenta]📋 Dry Run Complete - Analysis Results", style="magenta")

        from rich.text import Text
        from rich.panel import Panel
        from rich.align import Align

        savings_text = Text()
        savings_text.append("💾 Potential Space Savings\n\n", style="bold magenta")
        savings_text.append("Estimated Space to Free: ", style="bold")
        savings_text.append(format_size(total_space_freed), style="bold green")
        savings_text.append(f"\nFiles to Process: ", style="bold")
        savings_text.append(str(global_metrics_instance.files_processed), style="yellow")
        savings_text.append(f"\nDirectories to Process: ", style="bold")
        savings_text.append(str(global_metrics_instance.directories_processed), style="yellow")
        savings_text.append(f"\nAnalysis Time: ", style="bold")
        savings_text.append(f"{execution_time:.1f}s", style="cyan")

        panel = Panel(
            Align.center(savings_text),
            title="📊 Dry Run Summary",
            border_style="magenta",
            padding=(1, 2)
        )
        console.print(panel)

        diskcleanup_core.log.info(logger_helper.performance(mode="dry_run",
                                   potential_savings=format_size(total_space_freed),
                                   files_processed=global_metrics_instance.files_processed,
                                   dirs_processed=global_metrics_instance.directories_processed,
                                   errors=global_metrics_instance.errors_encountered,
                                   execution_time=f"{execution_time:.2f}s"))
        diskcleanup_core.log.info(logger_helper.system("dry run completed - no files were modified"))
    else:
        # Production run - show before/after comparison
        console.rule("[bold green]✅ Cleanup Complete - Results Summary", style="green")

        actual_space_freed = calculate_space_freed(health_before, health_after)

        # Use df-calculated space freed if it's meaningful, otherwise use tracked total
        # If tracked amount is significant but df shows very little, it's likely a rounding error
        threshold = max(1024 * 1024, total_space_freed * 0.1)  # 1MB or 10% of tracked amount, whichever is larger

        if actual_space_freed > threshold and total_space_freed > 0:
            space_freed_display = actual_space_freed
            diskcleanup_core.log.debug(logger_helper.system("Using df-calculated space freed",
                                      calculated=format_size(actual_space_freed),
                                      tracked=format_size(total_space_freed)))
        else:
            space_freed_display = total_space_freed
            if actual_space_freed > 0 and actual_space_freed <= threshold:
                diskcleanup_core.log.debug(logger_helper.system("df calculation too small compared to tracked, using tracked total",
                                          df_calculated=format_size(actual_space_freed),
                                          tracked=format_size(total_space_freed),
                                          note="df -h rounding may cause small false positives"))
            else:
                diskcleanup_core.log.debug(logger_helper.system("df precision insufficient, using tracked total",
                                          tracked=format_size(total_space_freed),
                                          note="df -h may not detect small changes on large filesystems"))

        print_health_comparison(health_before, health_after, execution_time, space_freed_display)

        diskcleanup_core.log.info(logger_helper.performance(mode="production",
                                   space_freed=format_size(space_freed_display),
                                   files_processed=global_metrics_instance.files_processed,
                                   dirs_processed=global_metrics_instance.directories_processed,
                                   errors=global_metrics_instance.errors_encountered,
                                   execution_time=f"{execution_time:.2f}s"))

    # Determine final space freed value for history
    if args.dry_run:
        history_space_freed = total_space_freed
    else:
        history_space_freed = space_freed_display

    # Save run history for trending
    save_run_history(
        history_path=history_path,
        health_before=health_before,
        health_after=health_after,
        space_freed=history_space_freed,
        files_processed=global_metrics_instance.files_processed,
        dirs_processed=global_metrics_instance.directories_processed,
        errors=global_metrics_instance.errors_encountered,
        execution_time=execution_time,
        dry_run=args.dry_run,
        config_file=yml_config,
        cleanup_breakdown=cleanup_breakdown,
    )
    trim_history_file(history_path)

    # Email notification (send_notification function not implemented)
    if 'email' in files_main_settings:
        diskcleanup_core.log.info(logger_helper.system("Email notification configured but send_notification function not implemented"))

    diskcleanup_core.log.info(logger_helper.system("disk cleanup completed successfully",
                          total_execution_time=f"{execution_time:.2f}s"))


def run_daemon(args, yml_config, files, files_main_settings, directories_to_check,
               current_directory, script_name):
    """Run cleanup in a loop with a configurable sleep interval."""
    global _daemon_shutdown

    # Determine interval: CLI flag > YAML config > default 3600
    daemon_config = {}
    try:
        with open(yml_config, 'r') as f:
            full_config = yaml.safe_load(f)
        daemon_config = full_config.get('daemon', {}) or {}
    except Exception:
        pass

    interval = args.interval or daemon_config.get('interval', 3600)
    pid_file = daemon_config.get('pid_file', '/var/run/diskcleanup.pid')
    max_consecutive_errors = daemon_config.get('max_consecutive_errors', 5)

    # Write PID file
    if not write_pid_file(pid_file):
        sys.exit(1)

    # Register signal handlers
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, _handle_reload)

    print(f"Daemon started (PID {os.getpid()}, interval {interval}s, pid_file {pid_file})")

    consecutive_errors = 0
    cycle = 0

    try:
        while not _daemon_shutdown:
            cycle += 1
            try:
                # Re-read config each cycle to pick up changes
                try:
                    files, files_main_settings, directories_to_check = readConfig(filename=yml_config)
                except ConfigError as e:
                    print(f"WARNING: Config reload failed on cycle {cycle}, using previous config: {e}")

                run_cleanup(args, yml_config, files, files_main_settings, directories_to_check,
                            current_directory, script_name)
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                print(f"ERROR: Cleanup cycle {cycle} failed: {e}")
                if consecutive_errors >= max_consecutive_errors:
                    print(f"FATAL: {max_consecutive_errors} consecutive failures, daemon exiting.")
                    break

            # Sleep in small increments so we can respond to signals promptly
            if not _daemon_shutdown:
                sleep_remaining = interval
                while sleep_remaining > 0 and not _daemon_shutdown:
                    chunk = min(sleep_remaining, 5)
                    time.sleep(chunk)
                    sleep_remaining -= chunk
    finally:
        remove_pid_file(pid_file)
        print("Daemon stopped.")


def main():
    """Main execution function."""
    args = parse_arguments()

    if args.version:
        show_version_console()
        sys.exit(0)

    if args.version_dialog:
        show_version_dialog()
        sys.exit(0)

    script_name = Path(__file__).name
    current_directory = str(Path(__file__).resolve().parent)

    yml_config = args.config if args.config else find_yaml_config()
    if yml_config is None:
        print("ERROR: No YAML configuration file found. Exiting.")
        sys.exit(1)

    try:
        files, files_main_settings, directories_to_check = readConfig(filename=yml_config)
    except ConfigError as e:
        print(f"ERROR: Failed to read configuration: {e}")
        sys.exit(1)

    if not validate_config({"main": files_main_settings, "directories": directories_to_check}):
        print("ERROR: Configuration validation failed. Exiting.")
        sys.exit(1)

    history_path = get_history_path(files_main_settings, current_directory)

    if args.report:
        print_report(history_path, last_n=args.last)
        sys.exit(0)

    if args.report_csv:
        print_report_csv(history_path, last_n=args.last)
        sys.exit(0)

    if args.daemon:
        run_daemon(args, yml_config, files, files_main_settings, directories_to_check,
                   current_directory, script_name)
    else:
        run_cleanup(args, yml_config, files, files_main_settings, directories_to_check,
                    current_directory, script_name)


if __name__ == '__main__':
    main()
