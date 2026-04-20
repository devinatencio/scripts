#!/usr/bin/python3
"""
Disk Cleanup Utility - System Health Module

This module contains system health monitoring, disk usage calculations,
and health display/comparison UI functions.

Author: Devin Acosta
Version: 3.0.0
Date: 2026-04-18
"""

import logging
import os
import shutil
import subprocess
from typing import Optional, Dict, Tuple, Union

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from diskcleanup.logging import LogHelper, OperationMetrics
from diskcleanup.config import format_size, convert_size_to_bytes


# ── Module-level runtime (set via init_runtime) ─────────────────────
logger = LogHelper()
log = None  # type: Optional[logging.Logger]
global_metrics = None  # type: Optional[OperationMetrics]


# ── Disk usage helpers ───────────────────────────────────────────────
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


# ── System health checks ────────────────────────────────────────────
def check_system_health() -> Dict[str, Dict[str, Union[str, int, float]]]:
    """Check system health including disk usage for all mount points."""
    health_data = {}

    try:
        result = subprocess.run(['df', '-h'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header

        for line in lines:
            parts = line.split()
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


# ── UI / Display ─────────────────────────────────────────────────────
def print_health_comparison(health_before: Dict, health_after: Dict,
                            execution_time: float, space_freed: int,
                            console: Optional[Console] = None) -> None:
    """Print a professional side-by-side comparison of system health."""
    if console is None:
        console = Console()

    table = Table(title="🏥 System Health Comparison - Before vs After Cleanup",
                  show_header=True, header_style="bold magenta")
    table.add_column("Mount Point", justify="left", style="cyan", no_wrap=True)
    table.add_column("Before", justify="center", style="red")
    table.add_column("After", justify="center", style="green")
    table.add_column("Freed", justify="center", style="bold green")
    table.add_column("Improvement", justify="center", style="bold yellow")

    for mount_point in sorted(health_before.keys()):
        if mount_point in health_after:
            before_pct = health_before[mount_point]['percent_used']
            after_pct = health_after[mount_point]['percent_used']

            improvement = before_pct - after_pct
            improvement_str = f"-{improvement:.1f}%" if improvement > 0 else "0%"

            mount_space_freed = 0
            try:
                used_before = health_before[mount_point]['used']
                used_after = health_after[mount_point]['used']
                before_bytes = convert_size_to_bytes(used_before)
                after_bytes = convert_size_to_bytes(used_after)
                if before_bytes > after_bytes:
                    mount_space_freed = before_bytes - after_bytes
            except (KeyError, ValueError):
                mount_space_freed = 0

            before_status = health_before[mount_point]['status']
            after_status = health_after[mount_point]['status']

            before_color = {"Good": "green", "Caution": "yellow", "Warning": "orange", "Critical": "red"}.get(before_status, "white")
            after_color = {"Good": "green", "Caution": "yellow", "Warning": "orange", "Critical": "red"}.get(after_status, "white")

            if mount_space_freed > 0:
                freed_display = format_size(mount_space_freed)
            elif improvement > 0 and mount_point == '/':
                freed_display = f"{format_size(space_freed)}"
            elif improvement > 0:
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


def print_compact_health_summary(health_before: Dict, health_after: Dict,
                                  console: Optional[Console] = None) -> None:
    """Print a compact system health summary."""
    if console is None:
        console = Console()

    summary_text = Text()
    summary_text.append("🖥  System Status: ", style="bold")

    critical_mounts = [mp for mp, data in health_before.items() if data['percent_used'] >= 90]
    if critical_mounts:
        summary_text.append(f"{len(critical_mounts)} critical mount(s)", style="bold red")
    else:
        summary_text.append("All systems nominal", style="bold green")

    if health_before:
        highest_usage = max(health_before.items(), key=lambda x: x[1]['percent_used'])
        mount_point, data = highest_usage
        summary_text.append(f" • Highest usage: {mount_point} ({data['percent_used']}%)", style="yellow")

    console.print(summary_text)
