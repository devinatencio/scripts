#!/usr/bin/python3
"""
Disk Cleanup Utility - Run History & Trending Module

This module contains run history persistence, trending reports,
and CSV export functionality.

Author: Devin Acosta
Version: 3.0.0
Date: 2026-04-18
"""

import datetime
import json
import logging
import socket
from pathlib import Path
from typing import Optional, Dict, Any, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from diskcleanup.logging import LogHelper
from diskcleanup.config import format_size


# ── Module-level runtime (set via init_runtime) ─────────────────────
logger = LogHelper()
log = None  # type: Optional[logging.Logger]

# ── Constants ────────────────────────────────────────────────────────
DEFAULT_HISTORY_FILE = "diskcleanup_history.jsonl"
MAX_HISTORY_ENTRIES = 500


def _get_hostname() -> str:
    """Get the system hostname."""
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


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

    total_freed = sum(e.get('space_freed_bytes', 0) for e in entries if not e.get('dry_run'))
    total_files = sum(e.get('files_processed', 0) for e in entries if not e.get('dry_run'))
    total_errors = sum(e.get('errors', 0) for e in entries)
    prod_runs = [e for e in entries if not e.get('dry_run')]
    dry_runs = [e for e in entries if e.get('dry_run')]

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
    table = Table(title="Run History (newest first)", show_header=True,
                  header_style="bold magenta", expand=True)
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

    # Top paths by space freed
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

        path_table = Table(title="Top Paths by Space Freed (all runs)", show_header=True,
                           header_style="bold magenta", expand=True)
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
            'journald_cleanup': 'journald',
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

    # Mount point trending
    if len(prod_runs) >= 2:
        oldest = prod_runs[-1]
        newest = prod_runs[0]

        trend_table = Table(title="Mount Point Trends (oldest → newest live run)",
                            show_header=True, header_style="bold magenta", expand=True)
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

    print("timestamp,hostname,mode,space_freed_bytes,space_freed,files_processed,dirs_processed,errors,execution_time_sec")
    for entry in reversed(entries):
        mode = "dry-run" if entry.get('dry_run') else "live"
        print(f"{entry.get('timestamp','')},{entry.get('hostname','')},{mode},"
              f"{entry.get('space_freed_bytes',0)},{entry.get('space_freed','0 B')},"
              f"{entry.get('files_processed',0)},{entry.get('dirs_processed',0)},"
              f"{entry.get('errors',0)},{entry.get('execution_time_sec',0)}")
