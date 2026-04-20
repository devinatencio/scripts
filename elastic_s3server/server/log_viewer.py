"""
log_viewer.py - Unified Rich log viewer for all utility logs.

Tails and merges log files from every utility into a single
color-coded, filterable live view.  Each utility gets its own color
so you can visually separate cold-snapshots activity from ILM curator
work at a glance.

Usage:
    python -m server.log_viewer                    # all logs, last 50 lines
    python -m server.log_viewer --tail 100         # last 100 lines each
    python -m server.log_viewer --level ERROR      # only ERROR+ lines
    python -m server.log_viewer --follow            # live tail (like tail -f)
    python -m server.log_viewer --utility daemon   # single utility only
"""

import argparse
import datetime
import os
import re
import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.columns import Columns

console = Console()

# Maps utility name -> display color.  Matches the log file stems
# produced by log_manager.setup_logger().
UTILITY_COLORS = {
    'cold-snapshots': 'green',
    'retention-enforcer': 'red',
    'restored-index-manager': 'cyan',
    'ilm-curator': 'magenta',
    'snapshot-cli': 'yellow',
    'daemon': 'bright_blue',
}

LEVEL_STYLES = {
    'DEBUG': 'dim',
    'INFO': 'white',
    'WARNING': 'yellow',
    'ERROR': 'bold red',
    'CRITICAL': 'bold white on red',
}

LEVEL_PRIORITY = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4}

# Regex matching the log format: 2024-01-15 08:30:00,123 - INFO - message
_LOG_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\s+-\s+(\w+)\s+-\s+(.*)$'
)


def _find_logs_dir():
    # type: () -> str
    """Return the path to the logs/ directory at the project root."""
    module_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(module_dir)
    return os.path.join(project_root, 'logs')


def _discover_log_files(logs_dir, utilities=None):
    # type: (str, list) -> dict
    """Discover available log files and map utility name -> path.

    Args:
        logs_dir: Path to the logs directory.
        utilities: Optional list of utility names to include.
                   None means all known utilities.

    Returns:
        dict mapping utility name to log file path (only existing files).
    """
    found = {}
    if not os.path.isdir(logs_dir):
        return found

    for name in UTILITY_COLORS:
        if utilities and name not in utilities:
            continue
        path = os.path.join(logs_dir, '%s.log' % name)
        if os.path.isfile(path):
            found[name] = path
    return found


def _parse_line(raw_line):
    # type: (str) -> tuple
    """Parse a single log line into (timestamp_str, level, message).

    Returns (None, None, raw_line) for lines that don't match the
    expected format (e.g. continuation / traceback lines).
    """
    m = _LOG_RE.match(raw_line.rstrip())
    if m:
        return m.group(1), m.group(2), m.group(3)
    return None, None, raw_line.rstrip()


def _read_tail(filepath, n):
    # type: (str, int) -> list
    """Read the last *n* lines from a file efficiently."""
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        return lines[-n:] if len(lines) > n else lines
    except (IOError, OSError):
        return []


def _merge_entries(log_files, tail_n, min_level):
    # type: (dict, int, int) -> list
    """Read, parse, and merge log entries from all files.

    Returns a list of (timestamp_str, utility, level, message) tuples
    sorted chronologically.
    """
    entries = []
    for utility, path in log_files.items():
        raw_lines = _read_tail(path, tail_n)
        for line in raw_lines:
            ts, level, msg = _parse_line(line)
            if ts is None:
                # Continuation line — attach to previous entry's utility
                if min_level <= 0:
                    entries.append(('', utility, '', msg))
                continue
            if LEVEL_PRIORITY.get(level, 1) >= min_level:
                entries.append((ts, utility, level, msg))

    # Sort by timestamp string (ISO-ish, so lexicographic works)
    entries.sort(key=lambda e: e[0])
    return entries


def _render_table(entries):
    # type: (list) -> Table
    """Build a Rich Table from merged log entries."""
    table = Table(
        show_header=True,
        header_style='bold',
        border_style='dim',
        expand=True,
        show_lines=False,
        pad_edge=False,
    )
    table.add_column('Time', style='dim', width=23, no_wrap=True)
    table.add_column('Utility', width=24, no_wrap=True)
    table.add_column('Level', width=8, no_wrap=True)
    table.add_column('Message', ratio=1)

    for ts, utility, level, msg in entries:
        color = UTILITY_COLORS.get(utility, 'white')
        level_style = LEVEL_STYLES.get(level, 'white')

        table.add_row(
            ts,
            '[%s]%s[/%s]' % (color, utility, color),
            '[%s]%s[/%s]' % (level_style, level, level_style),
            msg,
        )
    return table


def _render_summary(log_files):
    # type: (dict) -> Panel
    """Build a compact summary panel showing file sizes and line counts."""
    cards = []
    for utility in sorted(log_files):
        path = log_files[utility]
        color = UTILITY_COLORS.get(utility, 'white')
        try:
            size = os.path.getsize(path)
            if size >= 1024 * 1024:
                size_str = '%.1f MB' % (size / (1024.0 * 1024.0))
            elif size >= 1024:
                size_str = '%.1f KB' % (size / 1024.0)
            else:
                size_str = '%d B' % size
            mtime = os.path.getmtime(path)
            mod_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        except OSError:
            size_str = '?'
            mod_str = '?'

        cards.append(Panel(
            '[%s bold]%s[/%s bold]\n[dim]Size:[/dim] %s\n[dim]Modified:[/dim] %s'
            % (color, utility, color, size_str, mod_str),
            border_style=color,
            expand=True,
        ))

    if not cards:
        return Panel('[yellow]No log files found.[/yellow]', title='Log Files')

    return Panel(
        Columns(cards, equal=True, expand=True),
        title='\U0001f4c2 Log Files',
        border_style='bright_blue',
        padding=(0, 1),
    )


def _follow_logs(log_files, min_level):
    # type: (dict, int) -> None
    """Live-tail all log files, printing new lines as they appear."""
    # Record current file positions
    positions = {}
    for utility, path in log_files.items():
        try:
            fh = open(path, 'r')
            fh.seek(0, 2)  # seek to end
            positions[utility] = fh
        except (IOError, OSError):
            pass

    console.print('[dim]Following logs (Ctrl+C to stop)...[/dim]\n')

    try:
        while True:
            found_new = False
            for utility, fh in list(positions.items()):
                line = fh.readline()
                while line:
                    found_new = True
                    ts, level, msg = _parse_line(line)
                    color = UTILITY_COLORS.get(utility, 'white')
                    if ts is None:
                        console.print('  %s' % msg, style='dim')
                    elif LEVEL_PRIORITY.get(level, 1) >= min_level:
                        level_style = LEVEL_STYLES.get(level, 'white')
                        console.print(
                            '[dim]%s[/dim] [%s]%-24s[/%s] [%s]%-8s[/%s] %s'
                            % (ts, color, utility, color, level_style, level, level_style, msg)
                        )
                    line = fh.readline()
            if not found_new:
                time.sleep(0.5)
    except KeyboardInterrupt:
        console.print('\n[dim]Stopped.[/dim]')
    finally:
        for fh in positions.values():
            fh.close()


def main():
    # type: () -> None
    """Entry point for the unified log viewer."""
    parser = argparse.ArgumentParser(
        description='Unified Rich log viewer for all Elasticsearch utilities'
    )
    parser.add_argument(
        '--tail', type=int, default=50,
        help='Number of recent lines to show per log file (default: 50)',
    )
    parser.add_argument(
        '--level', default='DEBUG',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Minimum log level to display (default: DEBUG)',
    )
    parser.add_argument(
        '--utility', action='append', default=None,
        help='Show only specific utility (repeatable). '
             'Choices: %s' % ', '.join(sorted(UTILITY_COLORS)),
    )
    parser.add_argument(
        '--follow', '-f', action='store_true',
        help='Live-tail mode (like tail -f)',
    )
    parser.add_argument(
        '--logs-dir', default=None,
        help='Override logs directory path',
    )
    args = parser.parse_args()

    logs_dir = args.logs_dir or _find_logs_dir()
    min_level = LEVEL_PRIORITY.get(args.level, 0)

    log_files = _discover_log_files(logs_dir, utilities=args.utility)

    if not log_files:
        console.print('[yellow]No log files found in %s[/yellow]' % logs_dir)
        console.print('[dim]Utilities write logs after their first run.[/dim]')
        return

    # Summary header
    console.print()
    console.print(_render_summary(log_files))
    console.print()

    if args.follow:
        # Show historical tail first, then switch to live follow
        entries = _merge_entries(log_files, args.tail, min_level)
        if entries:
            console.print(Panel(
                _render_table(entries),
                title='\U0001f4dc Merged Logs (last %d lines/file, level >= %s)'
                      % (args.tail, args.level),
                border_style='bright_blue',
                padding=(0, 0),
            ))
            console.print()
        _follow_logs(log_files, min_level)
    else:
        entries = _merge_entries(log_files, args.tail, min_level)
        if not entries:
            console.print('[yellow]No log entries match the current filters.[/yellow]')
            return

        console.print(Panel(
            _render_table(entries),
            title='\U0001f4dc Merged Logs (last %d lines/file, level >= %s)'
                  % (args.tail, args.level),
            border_style='bright_blue',
            padding=(0, 0),
        ))
        console.print(
            '\n[dim]%d entries shown. Use --follow for live tail, '
            '--level to filter.[/dim]' % len(entries)
        )


if __name__ == '__main__':
    main()
