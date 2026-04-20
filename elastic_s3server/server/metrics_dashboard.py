"""
metrics_dashboard.py - Rich terminal dashboard for metrics visualization.

Reads the SQLite metrics database produced by metrics_collector and displays
an at-a-glance operational view using Rich panels and tables with
color-coded health status.  Supports historical trend views for the
past 7, 30, or 90 days using inline bar charts with gradient colors,
sparklines, trend arrows, and highlighted min/max rows.
"""

import argparse
import datetime
import os
import time

from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from server.capacity_forecast import compute_all_forecasts, generate_insights
from server.metrics_collector import read_metrics

# Version
from server import __version__

# Module-level console for Rich output
console = Console()

# Sparkline characters (8 levels, low to high)
_SPARK_CHARS = '\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588'

# Gradient palette from dim to bright for bar charts
_GRADIENT_PALETTES = {
    'green': ['#2d5016', '#3a6b1e', '#4a8526', '#5ca02e', '#6ebb36', '#82d64a', '#96f05e', '#aaff72'],
    'red': ['#501616', '#6b1e1e', '#852626', '#a02e2e', '#bb3636', '#d64a4a', '#f05e5e', '#ff7272'],
    'cyan': ['#163850', '#1e4d6b', '#266285', '#2e78a0', '#368ebb', '#4aa4d6', '#5ebaf0', '#72d0ff'],
}


def _format_time_ago(iso_timestamp, now=None):
    # type: (str, datetime.datetime | None) -> str
    """Return a human-friendly 'time ago' string from an ISO timestamp.

    Args:
        iso_timestamp: Datetime string in ``%Y-%m-%dT%H:%M:%S`` format.
        now: Reference time (defaults to ``datetime.datetime.now()``).

    Returns:
        A string like ``'2h ago'``, ``'15m ago'``, or ``'3d ago'``.
        Returns ``'N/A'`` on parse failure.
    """
    if not iso_timestamp:
        return 'N/A'
    if now is None:
        now = datetime.datetime.now()
    try:
        run_dt = datetime.datetime.strptime(iso_timestamp, '%Y-%m-%dT%H:%M:%S')
    except (ValueError, TypeError):
        return 'N/A'
    delta = now - run_dt 
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return 'just now'
    if total_seconds < 60:
        return '%ds ago' % total_seconds
    if total_seconds < 3600:
        return '%dm ago' % (total_seconds // 60)
    if total_seconds < 86400:
        return '%dh ago' % (total_seconds // 3600)
    return '%dd ago' % (total_seconds // 86400)


def _build_countdown_bar(remaining, interval, width=6):
    # type: (int, int, int) -> str
    """Return a small Rich-styled progress bar for a countdown.

    The bar fills from left to right as the scheduled time approaches.

    Args:
        remaining: Seconds until the next run.
        interval: Total interval in seconds (full cycle length).
        width: Bar width in characters.

    Returns:
        A Rich markup string with filled and empty block characters.
    """
    if interval <= 0:
        return ''
    elapsed = max(interval - remaining, 0)
    ratio = min(elapsed / float(interval), 1.0)
    filled = int(round(ratio * width))
    empty = width - filled
    return '[bright_cyan]%s[/bright_cyan][dim]%s[/dim]' % (
        '\u2588' * filled, '\u2591' * empty,
    )


def _calc_next_run(task_cfg, last_epoch, now, daemon_alive):
    # type: (dict, float, datetime.datetime, bool) -> str
    """Calculate a human-friendly next-run estimate for a task.

    For interval tasks: last_run + interval.
    For window tasks: next window open if outside, or last_run + interval
    if inside.  Returns a dim dash when no schedule info is available.
    """
    if not task_cfg or not daemon_alive:
        return '[dim]\u2014[/dim]'

    interval = task_cfg.get('interval_seconds', 0)
    stype = task_cfg.get('schedule_type', 'interval')
    enabled = task_cfg.get('enabled', True)

    if not enabled:
        return '[dim]disabled[/dim]'

    now_epoch = time.time()

    if stype == 'window':
        w_start = task_cfg.get('window_start', '')
        w_end = task_cfg.get('window_end', '')
        if w_start and w_end:
            try:
                ps = w_start.strip().split(':')
                pe = w_end.strip().split(':')
                t_start = datetime.time(int(ps[0]), int(ps[1]))
                t_end = datetime.time(int(pe[0]), int(pe[1]))
            except (ValueError, IndexError):
                return '[dim]\u2014[/dim]'

            now_t = now.time()
            # Check if currently inside the window
            if t_start <= t_end:
                in_window = t_start <= now_t < t_end
            else:
                in_window = now_t >= t_start or now_t < t_end

            if not in_window:
                # Calculate when the window next opens
                today_open = now.replace(
                    hour=t_start.hour, minute=t_start.minute, second=0, microsecond=0,
                )
                if today_open <= now:
                    # Window already passed today, next is tomorrow
                    next_open = today_open + datetime.timedelta(days=1)
                else:
                    next_open = today_open

                # Show relative time until window opens
                secs_until = (next_open - now).total_seconds()
                if secs_until < 3600:
                    eta = 'in %dm' % (int(secs_until) // 60)
                elif secs_until < 86400:
                    h = int(secs_until) // 3600
                    m = (int(secs_until) % 3600) // 60
                    eta = 'in %dh%dm' % (h, m) if m else 'in %dh' % h
                else:
                    eta = next_open.strftime('%m-%d')

                # Total wait is from last window close to next window open;
                # approximate as 24h for the countdown bar.
                total_wait = 86400
                bar = _build_countdown_bar(int(secs_until), total_wait)
                ts = next_open.strftime('%Y-%m-%dT%H:%M')
                return '[bright_cyan]%s[/bright_cyan] %s [dim](%s)[/dim]' % (
                    ts, bar, eta,
                )

            # Inside window: fall through to interval logic below

    # Interval-based (or inside a window)
    if interval > 0 and last_epoch > 0:
        next_epoch = last_epoch + interval
        remaining = int(next_epoch - now_epoch)
        if remaining <= 0:
            return '[bold bright_green]due now[/bold bright_green]'
        next_dt = datetime.datetime.fromtimestamp(next_epoch)
        # Show relative countdown alongside the time
        if remaining < 3600:
            eta = 'in %dm' % (remaining // 60)
        else:
            h = remaining // 3600
            m = (remaining % 3600) // 60
            eta = 'in %dh%dm' % (h, m) if m else 'in %dh' % h
        bar = _build_countdown_bar(remaining, interval)
        ts = next_dt.strftime('%Y-%m-%dT%H:%M')
        return '[bright_cyan]%s[/bright_cyan] %s [dim](%s)[/dim]' % (ts, bar, eta)
    elif interval > 0 and last_epoch == 0:
        return '[bold bright_green]due now[/bold bright_green]'

    return '[dim]\u2014[/dim]'


def _build_dashboard(metrics_data):
    # type: (dict) -> Panel
    """Build the full metrics dashboard as a Rich renderable.

    Returns the outer Panel so callers can either print it directly
    or feed it to a ``Live`` display for watch mode.

    Args:
        metrics_data: dict from ``read_metrics`` containing
            daily_counters, utility_health, and snapshot_statuses.

    Returns:
        A ``rich.panel.Panel`` containing the complete dashboard.
    """
    sections = []

    # --- Daemon Status ---
    heartbeat = metrics_data.get('daemon_heartbeat', {})
    if heartbeat:
        hb_ts = heartbeat.get('timestamp', '')
        hb_pid = heartbeat.get('pid', '?')
        hb_tasks = heartbeat.get('tasks', {})
        ago = _format_time_ago(hb_ts, now=datetime.datetime.now())

        # Check if the daemon process is actually alive
        pid_alive = False
        try:
            os.kill(int(hb_pid), 0)
            pid_alive = True
        except (OSError, ValueError, TypeError):
            pass

        # Consider the daemon alive if heartbeat is < 90 seconds old AND pid exists
        stale = True
        try:
            hb_dt = datetime.datetime.strptime(hb_ts, '%Y-%m-%dT%H:%M:%S')
            stale = (datetime.datetime.now() - hb_dt).total_seconds() > 90
        except (ValueError, TypeError):
            pass

        if not pid_alive:
            status_label = '[red]\u25cf Stopped[/red]'
            status_color = 'red'
        elif stale:
            status_label = '[yellow]\u25cf Stale[/yellow]'
            status_color = 'yellow'
        else:
            status_label = '[green]\u25cf Running[/green]'
            status_color = 'green'

        # Right side: daemon info table
        from rich.box import ROUNDED as INFO_BOX
        info_table = Table(
            show_header=False,
            box=INFO_BOX,
            pad_edge=True,
            padding=(0, 1),
            expand=False,
            border_style='dim',
        )
        info_table.add_column('Label', style='dim', no_wrap=True)
        info_table.add_column('Value', no_wrap=True)
        info_table.add_row('Status', status_label)
        info_table.add_row('PID', '[bold]%s[/bold]' % hb_pid)
        info_table.add_row('Heartbeat', '[bold]%s[/bold]' % ago)

        # Left side: task table
        task_table = Table(
            show_header=False,
            box=None,
            pad_edge=False,
            padding=(0, 1),
            expand=False,
        )
        task_table.add_column('Name', no_wrap=True)
        task_table.add_column('Status', no_wrap=True)
        task_table.add_column('Type', no_wrap=True)
        task_table.add_column('Config', no_wrap=True)

        now_epoch = time.time()
        for tname, tinfo in sorted(hb_tasks.items()):
            enabled = tinfo.get('enabled', False)
            running = tinfo.get('running', False)
            stype = tinfo.get('schedule_type', '?')
            last_epoch = tinfo.get('last_run_epoch', 0)
            interval = tinfo.get('interval_seconds', 0)
            jitter = tinfo.get('jitter_seconds', 0)
            window_start = tinfo.get('window_start', '')
            window_end = tinfo.get('window_end', '')

            name_cell = '[cyan]%s[/cyan]' % tname
            type_cell = '[white on #2a2a5a] %-8s [/white on #2a2a5a]' % stype

            # Build config summary with fixed-width background badges
            config_parts = []
            if interval > 0:
                interval_min = interval // 60
                if interval_min >= 60 and interval_min % 60 == 0:
                    label = 'every %dh' % (interval_min // 60)
                elif interval_min >= 60:
                    label = 'every %dh%dm' % (interval_min // 60, interval_min % 60)
                else:
                    label = 'every %dm' % interval_min
                config_parts.append('[white on #2d4a1e] %-10s[/white on #2d4a1e]' % label)
            if jitter > 0:
                jitter_min = jitter // 60
                label = 'jitter %dm' % jitter_min
                config_parts.append('[white on #4a3a1e] %-10s[/white on #4a3a1e]' % label)
            if stype == 'window' and window_start and window_end:
                label = '%s\u2013%s' % (window_start, window_end)
                config_parts.append('[white on #1e3a4a] %-11s[/white on #1e3a4a]' % label)
            config_cell = ' '.join(config_parts) if config_parts else '[dim]\u2014[/dim]'

            if not pid_alive:
                status_cell = '[white on red] stopped [/white on red]'
            elif not enabled:
                status_cell = '[white on dark_red] disabled [/white on dark_red]'
            elif running:
                status_cell = '[bold white on green] running [/bold white on green]'
            else:
                if interval > 0 and last_epoch > 0:
                    next_epoch = last_epoch + interval
                    remaining = int(next_epoch - now_epoch)
                    if remaining <= 0:
                        idle_label = 'due now'
                    elif remaining < 60:
                        idle_label = 'next in %ds' % remaining
                    elif remaining < 3600:
                        idle_label = 'next in %dm' % (remaining // 60)
                    else:
                        idle_label = 'next in %dh%dm' % (remaining // 3600, (remaining % 3600) // 60)
                elif interval > 0 and last_epoch == 0:
                    idle_label = 'pending'
                else:
                    idle_label = 'idle'
                status_cell = '[white on #444444] %s [/white on #444444]' % idle_label

            task_table.add_row(name_cell, status_cell, type_cell, config_cell)

        centered_info = Align(info_table, align='center')

        daemon_layout = Table(
            show_header=False,
            box=None,
            pad_edge=False,
            padding=(0, 2),
            expand=True,
        )
        daemon_layout.add_column('Tasks', no_wrap=True)
        daemon_layout.add_column('Info', ratio=1)
        daemon_layout.add_row(task_table, centered_info)

        daemon_content = daemon_layout if hb_tasks else '[dim]no tasks[/dim]'
    else:
        daemon_content = '[dim]\u25cb Not Connected \u2014 cron mode, no daemon heartbeat found[/dim]'

    sections.append(Panel(
        daemon_content,
        title='\U0001f916 Daemon',
        border_style='dim' if not heartbeat else 'red' if not pid_alive else 'yellow' if stale else 'bright_blue',
        padding=(0, 2),
    ))

    # --- Daily Counters Scoreboard ---
    counters = metrics_data.get('daily_counters', {})
    date_str = counters.get('date', 'N/A')
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    # If the stored date is stale (yesterday or older), show today with
    # zero counters instead of misleading the operator with old numbers.
    if date_str != today_str and date_str != 'N/A':
        created = 0
        deleted = 0
        ilm_deleted = 0
        total_snapshots = counters.get('total_snapshots', 0)
        date_str = today_str
        stale_note = '  [dim yellow](no activity yet today)[/dim yellow]'
    else:
        created = counters.get('snapshots_created', 0)
        deleted = counters.get('snapshots_deleted', 0)
        ilm_deleted = counters.get('indices_deleted_ilm', 0)
        total_snapshots = counters.get('total_snapshots', 0)
        stale_note = ''

    counter_cards = [
        Panel(
            '\U0001f4e6 [bold green]%d[/bold green]\n[dim]Snapshots Created[/dim]' % created,
            expand=True,
            border_style='green',
        ),
        Panel(
            '\U0001f5d1  [bold red]%d[/bold red]\n[dim]Snapshots Deleted[/dim]' % deleted,
            expand=True,
            border_style='red',
        ),
        Panel(
            '\U0001f9f9 [bold cyan]%d[/bold cyan]\n[dim]ILM Indices Deleted[/dim]' % ilm_deleted,
            expand=True,
            border_style='cyan',
        ),
        Panel(
            '\U0001f4be [bold bright_yellow]%d[/bold bright_yellow]\n[dim]Total S3 Snapshots[/dim]' % total_snapshots,
            expand=True,
            border_style='bright_yellow',
        ),
    ]

    # --- Snapshot Status Distribution (embedded in Daily Counters) ---
    statuses = metrics_data.get('snapshot_statuses', {})
    total_snaps = sum(statuses.get(k, 0) for k in
                      ('SUCCESS', 'FAILED', 'PARTIAL', 'IN_PROGRESS', 'INCOMPATIBLE'))

    status_colors = {
        'SUCCESS': 'green',
        'FAILED': 'red',
        'PARTIAL': 'yellow',
        'IN_PROGRESS': 'bright_blue',
        'INCOMPATIBLE': 'magenta',
    }
    status_emojis = {
        'SUCCESS': '[green]\u25cf[/green] ',
        'FAILED': '[red]\u25cf[/red] ',
        'PARTIAL': '[yellow]\u25cf[/yellow] ',
        'IN_PROGRESS': '[bright_blue]\u25cf[/bright_blue] ',
        'INCOMPATIBLE': '[magenta]\u25cf[/magenta] ',
    }

    status_table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
        padding=(0, 1),
    )
    status_table.add_column('', width=3)
    status_table.add_column('Status', width=15)
    status_table.add_column('Count', justify='right', width=6)
    status_table.add_column('%', justify='right', width=6)
    status_table.add_column('', width=30)

    for key in ('SUCCESS', 'FAILED', 'PARTIAL', 'IN_PROGRESS', 'INCOMPATIBLE'):
        count = statuses.get(key, 0)
        color = status_colors.get(key, 'white')
        emoji = status_emojis.get(key, '')
        pct = int(round(count / float(total_snaps) * 100)) if total_snaps > 0 else 0
        max_count = max(statuses.get(k, 0) for k in
                        ('SUCCESS', 'FAILED', 'PARTIAL', 'IN_PROGRESS', 'INCOMPATIBLE'))
        bar_color = 'green' if key == 'SUCCESS' else 'red' if key == 'FAILED' else 'cyan'
        bar = _build_gradient_bar(count, max_count, bar_color, width=30)
        status_table.add_row(
            emoji,
            '[%s]%s[/%s]' % (color, key, color),
            '[bold]%d[/bold]' % count,
            '[dim]%d%%[/dim]' % pct,
            bar,
        )

    daily_panel = Panel(
        Columns(counter_cards, equal=True, expand=True),
        title='\U0001f4c5 Daily Counters \u2014 [bold bright_cyan]%s[/bold bright_cyan]%s' % (date_str, stale_note),
        border_style='bright_blue',
        padding=(1, 1),
    )

    status_panel = Panel(
        Align(status_table, align='center'),
        title='\U0001f4ca Snapshot Status Distribution',
        border_style='bright_blue',
        padding=(1, 1),
    )

    sections.append(Panel(
        Group(daily_panel, status_panel),
        title='\U0001f4e6 Snapshot Overview',
        border_style='bright_blue',
        padding=(1, 1),
    ))

    # --- Utility Health Table ---
    health = metrics_data.get('utility_health', {})

    # Seed from daemon task list so all known utilities always appear,
    # even before their first run.
    heartbeat_tasks = heartbeat.get('tasks', {}) if heartbeat else {}
    all_utility_names = set(health.keys()) | set(heartbeat_tasks.keys())

    health_table = Table(
        title='Utility Health',
        border_style='dim',
        title_style='bold bright_white',
        show_lines=True,
        pad_edge=True,
    )
    health_table.add_column('', width=3)  # status emoji
    health_table.add_column('Utility', style='cyan')
    health_table.add_column('Last Run')
    health_table.add_column('Ago', width=8)
    health_table.add_column('Next Run', width=38, no_wrap=True)
    health_table.add_column('Status')

    now = datetime.datetime.now()

    for name in sorted(all_utility_names):
        info = health.get(name, {})
        task_cfg = heartbeat_tasks.get(name, {})
        last_run = info.get('last_run', '')
        success = info.get('success', None)

        if success is None:
            # Utility is known from the daemon but hasn't reported yet
            emoji = '[bright_yellow]\u25cb[/bright_yellow] '
            # Calculate next run even for tasks that haven't run yet
            next_run_cell = _calc_next_run(task_cfg, 0, now, pid_alive if heartbeat else False)
            health_table.add_row(
                emoji, name,
                '[dim]\u2014[/dim]', '[dim]\u2014[/dim]',
                next_run_cell,
                '[dim]Awaiting first run[/dim]',
            )
            continue

        # Determine if the utility is overdue based on its configured
        # interval.  For window-scheduled tasks, only flag overdue if
        # we are currently inside the window OR the task missed its
        # entire last window.  For interval tasks, allow 2x interval
        # plus jitter as grace.
        overdue = False
        if success and last_run and task_cfg:
            try:
                run_dt = datetime.datetime.strptime(last_run, '%Y-%m-%dT%H:%M:%S')
                elapsed = (now - run_dt).total_seconds()
                interval_secs = task_cfg.get('interval_seconds', 0)
                jitter_secs = task_cfg.get('jitter_seconds', 0)
                sched_type = task_cfg.get('schedule_type', 'interval')

                if interval_secs > 0 and sched_type == 'window':
                    # Window task: check if we're inside the window
                    w_start = task_cfg.get('window_start', '')
                    w_end = task_cfg.get('window_end', '')
                    if w_start and w_end:
                        now_t = now.time()
                        try:
                            parts_s = w_start.strip().split(':')
                            parts_e = w_end.strip().split(':')
                            t_start = datetime.time(int(parts_s[0]), int(parts_s[1]))
                            t_end = datetime.time(int(parts_e[0]), int(parts_e[1]))
                        except (ValueError, IndexError):
                            t_start = datetime.time(0, 0)
                            t_end = datetime.time(23, 59)

                        # Determine if currently inside the window
                        if t_start <= t_end:
                            in_window = t_start <= now_t < t_end
                        else:
                            in_window = now_t >= t_start or now_t < t_end

                        if in_window:
                            # Inside window: should have run within
                            # 2x interval + jitter
                            grace = (interval_secs * 2) + jitter_secs
                            if elapsed > grace:
                                overdue = True
                        else:
                            # Outside window: calculate how long the
                            # window has been closed.  Only flag overdue
                            # if the task didn't run during the last
                            # window at all.  Approximate by checking if
                            # elapsed exceeds 24h (missed a full cycle).
                            if elapsed > 86400:
                                overdue = True

                elif interval_secs > 0:
                    # Interval task: straightforward grace check
                    grace = (interval_secs * 2) + jitter_secs
                    if elapsed > grace:
                        overdue = True
            except (ValueError, TypeError):
                pass

        # Determine color: green if success and within expected window
        color = 'red'
        if success and last_run:
            try:
                run_dt = datetime.datetime.strptime(last_run, '%Y-%m-%dT%H:%M:%S')
                delta = now - run_dt
                if delta.total_seconds() < 86400 and not overdue:
                    color = 'green'
                elif overdue:
                    color = 'yellow'
            except (ValueError, TypeError):
                pass

        if overdue:
            emoji = '[yellow]\u25cf[/yellow] '
            status_label = 'OVERDUE'
        elif success:
            emoji = '[green]\u25cf[/green] '
            status_label = 'OK'
        else:
            emoji = '[red]\u25cf[/red] '
            status_label = 'FAIL'
        styled_status = '[bold %s]%s[/bold %s]' % (color, status_label, color)
        styled_run = '[%s]%s[/%s]' % (color, last_run if last_run else 'N/A', color)
        ago = _format_time_ago(last_run, now)
        styled_ago = '[%s]%s[/%s]' % (color, ago, color)

        # Calculate next expected run
        last_epoch = task_cfg.get('last_run_epoch', 0) if task_cfg else 0
        next_run_cell = _calc_next_run(task_cfg, last_epoch, now, pid_alive if heartbeat else False)

        health_table.add_row(emoji, name, styled_run, styled_ago, next_run_cell, styled_status)

    if not all_utility_names:
        health_table.add_row('[red]\u25cf[/red] ', '\u2014', '\u2014', '\u2014', '\u2014', '[red]No data[/red]')

    sections.append(Align(health_table, align='center'))

    # --- Outer wrapper ---
    return Panel(
        Group(*sections),
        title='\U0001f4ca [bold]Snapshot Metrics Dashboard[/bold]',
        subtitle='[bold bright_green]v%s[/bold bright_green] [dim]\u2502 rendered[/dim] [bold bright_cyan]%s[/bold bright_cyan] [bold bright_yellow]%s[/bold bright_yellow]' % (
            __version__, now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'),
        ),
        border_style='bright_blue',
        padding=(1, 2),
    )


def render_dashboard(metrics_data):
    # type: (dict) -> None
    """Render the full metrics dashboard using Rich.

    Builds the dashboard and prints it to the console.

    Args:
        metrics_data: dict from ``read_metrics``.
    """
    console.print(_build_dashboard(metrics_data))


def _build_bar(value, max_value, width=30):
    # type: (int, int, int) -> str
    """Return a Unicode bar string scaled to *width* characters.

    Args:
        value: The counter value for this day.
        max_value: The maximum value across the period (for scaling).
        width: Maximum bar width in characters.

    Returns:
        A string of block characters proportional to value/max_value.
    """
    if max_value <= 0:
        return ''
    length = int(round(value / float(max_value) * width))
    return '\u2588' * max(length, 1) if value > 0 else ''


def _build_gradient_bar(value, max_value, color_name, width=30):
    # type: (int, int, str, int) -> Text
    """Return a Rich Text bar with gradient coloring.

    Each character in the bar gets a progressively brighter shade
    from the palette, creating a left-to-right intensity ramp.

    Args:
        value: The counter value for this day.
        max_value: The maximum value across the period (for scaling).
        color_name: Key into ``_GRADIENT_PALETTES``.
        width: Maximum bar width in characters.

    Returns:
        A ``rich.text.Text`` object with per-character styling.
    """
    if max_value <= 0 or value <= 0:
        return Text('')
    length = int(round(value / float(max_value) * width))
    length = max(length, 1)
    palette = _GRADIENT_PALETTES.get(color_name, _GRADIENT_PALETTES['green'])
    bar = Text()
    for i in range(length):
        # Map position to palette index
        idx = int(i / max(length - 1, 1) * (len(palette) - 1))
        bar.append('\u2588', style=palette[idx])
    return bar


def _sparkline(values):
    # type: (list) -> str
    """Build a compact sparkline string from a list of numeric values.

    Maps each value to one of 8 Unicode block characters proportional
    to the range of values.

    Args:
        values: List of ints/floats.

    Returns:
        A string of sparkline characters, one per value.
    """
    if not values:
        return ''
    lo = min(values)
    hi = max(values)
    span = hi - lo if hi != lo else 1
    chars = []
    for v in values:
        idx = int((v - lo) / span * (len(_SPARK_CHARS) - 1))
        chars.append(_SPARK_CHARS[idx])
    return ''.join(chars)


def _trend_arrow(values):
    # type: (list) -> str
    """Return a trend arrow comparing the last value to the average.

    Returns:
        One of: ``\u2191`` (up), ``\u2193`` (down), ``\u2192`` (flat).
    """
    if len(values) < 2:
        return '\u2192'
    avg = sum(values) / len(values)
    last = values[-1]
    if last > avg * 1.1:
        return '\u2191'
    elif last < avg * 0.9:
        return '\u2193'
    return '\u2192'


def _day_of_week(date_str):
    # type: (str) -> str
    """Return a 3-letter day-of-week abbreviation for a YYYY-MM-DD string."""
    try:
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%a')
    except (ValueError, TypeError):
        return '???'


def _prepare_history(metrics_data, days):
    # type: (dict, int) -> list
    """Merge today's live counters into daily_history and trim to window.

    Args:
        metrics_data: dict from ``read_metrics``.
        days: Number of past days to keep.

    Returns:
        Sorted list of history entry dicts, trimmed to *days*.
    """
    history = list(metrics_data.get('daily_history', []))

    today_counters = metrics_data.get('daily_counters', {})
    if today_counters.get('date'):
        existing_dates = {e.get('date') for e in history}
        if today_counters['date'] not in existing_dates:
            history.append({
                'date': today_counters['date'],
                'snapshots_created': today_counters.get('snapshots_created', 0),
                'snapshots_deleted': today_counters.get('snapshots_deleted', 0),
                'indices_deleted_ilm': today_counters.get('indices_deleted_ilm', 0),
                'total_snapshots': today_counters.get('total_snapshots', 0),
            })

    history.sort(key=lambda e: e.get('date', ''))
    return history[-days:]


def render_history(metrics_data, days=30):
    # type: (dict, int) -> None
    """Render historical trend tables for daily counters.

    Shows a scoreboard summary panel, then a table per counter
    (snapshots created, snapshots deleted, indices deleted) with
    day-of-week labels, gradient bar charts, percentage-of-max,
    and highlighted min/max rows.

    Args:
        metrics_data: dict from ``read_metrics``.
        days: Number of past days to display (7, 30, or 90).
    """
    history = _prepare_history(metrics_data, days)

    if not history:
        console.print('[yellow]No historical data available yet.[/yellow]')
        return

    counter_keys = [
        ('snapshots_created', 'Snapshots Created', 'green'),
        ('snapshots_deleted', 'Snapshots Deleted', 'red'),
        ('indices_deleted_ilm', 'ILM Indices Deleted', 'cyan'),
        ('total_snapshots', 'Total S3 Snapshots', 'green'),
    ]

    # --- Scoreboard summary panel ---
    scoreboard_cards = []
    for key, label, color in counter_keys:
        values = [entry.get(key, 0) for entry in history]
        total = sum(values)
        avg = total / len(values) if values else 0
        spark = _sparkline(values)
        arrow = _trend_arrow(values)
        peak = max(values) if values else 0

        card_text = (
            '[bold {color}]{label}[/bold {color}]\n'
            '[dim]total:[/dim] [bold]{total}[/bold]  '
            '[dim]avg:[/dim] [bold]{avg:.1f}[/bold]/day  '
            '[dim]peak:[/dim] [bold]{peak}[/bold]\n'
            '[{color}]{spark}[/{color}] {arrow}'
        ).format(
            color=color, label=label, total=total,
            avg=avg, peak=peak, spark=spark, arrow=arrow,
        )
        scoreboard_cards.append(Panel(card_text, expand=True))

    console.print(Panel(
        Columns(scoreboard_cards, equal=True, expand=True),
        title='\U0001f4ca [bold]Metrics Dashboard[/bold] \u2014 last %d days' % days,
        subtitle='[bold bright_green]v%s[/bold bright_green] [dim]\u2502 %s[/dim]' % (__version__, datetime.date.today().strftime('%Y-%m-%d')),
        border_style='bright_blue',
        padding=(1, 2),
    ))
    console.print()

    # --- Per-counter trend tables ---
    for key, label, color in counter_keys:
        values = [entry.get(key, 0) for entry in history]
        max_val = max(values) if values else 0
        min_val = min(values) if values else 0
        total = sum(values)
        avg = total / len(values) if values else 0

        table = Table(
            title='%s  (last %d days)  total: %d  avg: %.1f/day'
            % (label, days, total, avg),
            border_style='dim',
            title_style='bold %s' % color,
            show_lines=False,
        )
        table.add_column('Date', style='dim', width=12)
        table.add_column('Day', style='dim', width=5)
        table.add_column('Count', justify='right', width=6)
        table.add_column('%', justify='right', width=5)
        table.add_column('', width=32)  # bar column

        for entry in history:
            date_str = entry.get('date', '?')
            val = entry.get(key, 0)
            dow = _day_of_week(date_str)
            pct = int(round(val / float(max_val) * 100)) if max_val > 0 else 0
            bar = _build_gradient_bar(val, max_val, color)

            # Highlight min/max rows
            is_max = val == max_val and max_val > 0
            is_min = val == min_val and min_val != max_val

            date_cell = '[bold bright_white]%s[/bold bright_white]' % date_str if is_max else date_str
            dow_cell = '[bold bright_white]%s[/bold bright_white]' % dow if is_max else dow
            if is_max:
                count_cell = '[bold bright_white]%d \u25b2[/bold bright_white]' % val
                pct_cell = '[bold bright_white]%d%%[/bold bright_white]' % pct
            elif is_min:
                count_cell = '[dim]%d \u25bc[/dim]' % val
                pct_cell = '[dim]%d%%[/dim]' % pct
            else:
                count_cell = str(val)
                pct_cell = '[dim]%d%%[/dim]' % pct

            table.add_row(date_cell, dow_cell, count_cell, pct_cell, bar)

        console.print(table)
        console.print()


def _build_forecast(metrics_data):
    # type: (dict) -> Panel
    """Build the activity forecast as a Rich renderable.

    Returns the outer Panel so callers can either print it directly
    or feed it to a ``Live`` display for watch mode.

    Args:
        metrics_data: dict from ``read_metrics`` containing
            daily_history and daily_counters.

    Returns:
        A ``rich.panel.Panel`` containing the complete forecast view.
    """
    forecasts = compute_all_forecasts(metrics_data)
    sections = []

    # --- Actionable Insights (the "so what?" section) ---
    insights = generate_insights(forecasts)
    if insights:
        insight_icons = {
            'critical': '[bold red]\u2718[/bold red]',
            'warning': '[yellow]\u26a0[/yellow] ',
            'info': '[bright_blue]\u2139[/bright_blue] ',
        }
        insight_lines = []
        for ins in insights:
            icon = insight_icons.get(ins['level'], '')
            insight_lines.append('%s %s' % (icon, ins['message']))

        sections.append(Panel(
            '\n'.join(insight_lines),
            title='\U0001f4a1 Actionable Insights',
            border_style='bright_green',
            padding=(1, 2),
        ))

    # --- Counter metadata for display ---
    counter_meta = [
        ('snapshots_created', 'Snapshots Created', 'green', '\U0001f4e6'),
        ('snapshots_deleted', 'Snapshots Deleted', 'red', '\U0001f5d1 '),
        ('indices_deleted_ilm', 'ILM Indices Deleted', 'cyan', '\U0001f9f9'),
        ('net_growth', 'Net Snapshot Growth', 'bright_yellow', '\U0001f4c8'),
    ]

    confidence_styles = {
        'high': ('[green]\u25cf high[/green]', 'green'),
        'medium': ('[yellow]\u25cf medium[/yellow]', 'yellow'),
        'low': ('[red]\u25cf low[/red]', 'red'),
    }

    # --- Net Growth Headline ---
    net = forecasts.get('net_growth', {})
    net_slope = net.get('slope_per_day', 0.0)
    net_avg = net.get('current_avg', 0.0)
    net_conf = net.get('confidence', 'low')
    net_pts = net.get('data_points', 0)
    net_r2 = net.get('r_squared', 0.0)
    net_proj_30 = net.get('cumulative_projections', {}).get(30, 0)
    net_proj_90 = net.get('cumulative_projections', {}).get(90, 0)
    net_wow = net.get('wow_change_pct')

    if net_slope > 0:
        direction = '[bright_yellow]\u2191 Growing[/bright_yellow]'
    elif net_slope < 0:
        direction = '[green]\u2193 Shrinking[/green]'
    else:
        direction = '[dim]\u2192 Flat[/dim]'

    wow_str = ''
    if net_wow is not None:
        if net_wow > 0:
            wow_str = '  [bright_yellow]\u2191 %.1f%% WoW[/bright_yellow]' % net_wow
        elif net_wow < 0:
            wow_str = '  [green]\u2193 %.1f%% WoW[/green]' % abs(net_wow)
        else:
            wow_str = '  [dim]\u2192 0.0% WoW[/dim]'

    conf_label = confidence_styles.get(net_conf, confidence_styles['low'])[0]

    headline_text = (
        '{direction}  [bold]avg {avg:.1f}/day[/bold]  '
        '[dim]slope:[/dim] {slope:+.2f}/day  '
        '[dim]R\u00b2:[/dim] {r2:.2f}  '
        '{conf}{wow}\n'
        '[dim]Based on {pts} days of data.  '
        'Projected net +{p30:.0f} snapshots in 30d, +{p90:.0f} in 90d.[/dim]'
    ).format(
        direction=direction, avg=net_avg, slope=net_slope,
        r2=net_r2, conf=conf_label, wow=wow_str, pts=net_pts,
        p30=net_proj_30, p90=net_proj_90,
    )

    sections.append(Panel(
        headline_text,
        title='\U0001f4c8 Net Snapshot Growth',
        border_style='bright_yellow',
        padding=(1, 2),
    ))

    # --- Per-Counter Forecast Cards ---
    forecast_cards = []
    for key, label, color, emoji in counter_meta:
        fc = forecasts.get(key, {})
        slope = fc.get('slope_per_day', 0.0)
        avg = fc.get('current_avg', 0.0)
        r2 = fc.get('r_squared', 0.0)
        conf = fc.get('confidence', 'low')
        proj = fc.get('projections', {})
        wow = fc.get('wow_change_pct')
        weekly = fc.get('weekly_trend', [])

        conf_label = confidence_styles.get(conf, confidence_styles['low'])[0]

        # Weekly sparkline
        week_vals = [w[1] for w in weekly]
        spark = _sparkline(week_vals) if week_vals else ''
        arrow = _trend_arrow(week_vals) if week_vals else '\u2192'

        wow_str = ''
        if wow is not None:
            if wow > 0:
                wow_str = '[bright_yellow]\u2191 %.1f%%[/bright_yellow]' % wow
            elif wow < 0:
                wow_str = '[green]\u2193 %.1f%%[/green]' % abs(wow)
            else:
                wow_str = '[dim]\u2192 0.0%[/dim]'

        card_text = (
            '{emoji} [bold {color}]{label}[/bold {color}]\n'
            '[dim]avg:[/dim] [bold]{avg:.1f}[/bold]/day  '
            '[dim]slope:[/dim] {slope:+.3f}\n'
            '[dim]R\u00b2:[/dim] {r2:.2f}  {conf}\n'
            '[{color}]{spark}[/{color}] {arrow}  {wow}\n'
            '[dim]30d:[/dim] [bold]{p30}[/bold]  '
            '[dim]60d:[/dim] [bold]{p60}[/bold]  '
            '[dim]90d:[/dim] [bold]{p90}[/bold]'
        ).format(
            emoji=emoji, color=color, label=label,
            avg=avg, slope=slope, r2=r2, conf=conf_label,
            spark=spark, arrow=arrow, wow=wow_str,
            p30=proj.get(30, 0), p60=proj.get(60, 0), p90=proj.get(90, 0),
        )
        forecast_cards.append(Panel(card_text, expand=True, border_style=color))

    sections.append(Panel(
        Columns(forecast_cards, equal=True, expand=True),
        title='Per-Metric Forecasts  [dim](predicted daily rate at horizon)[/dim]',
        border_style='bright_blue',
        padding=(1, 1),
    ))

    # --- Cumulative Projection Table ---
    cum_table = Table(
        title='Cumulative Projections',
        border_style='dim',
        title_style='bold bright_white',
        show_lines=True,
        pad_edge=True,
    )
    cum_table.add_column('Metric', style='cyan', width=24)
    cum_table.add_column('Confidence', width=12)
    cum_table.add_column('Current Avg', justify='right', width=12)
    cum_table.add_column('30-Day Total', justify='right', width=14)
    cum_table.add_column('60-Day Total', justify='right', width=14)
    cum_table.add_column('90-Day Total', justify='right', width=14)

    for key, label, color, emoji in counter_meta:
        fc = forecasts.get(key, {})
        conf = fc.get('confidence', 'low')
        avg = fc.get('current_avg', 0.0)
        cum = fc.get('cumulative_projections', {})
        conf_label = confidence_styles.get(conf, confidence_styles['low'])[0]

        cum_table.add_row(
            '%s [%s]%s[/%s]' % (emoji, color, label, color),
            conf_label,
            '[bold]%.1f[/bold]/day' % avg,
            '[bold]%.0f[/bold]' % cum.get(30, 0),
            '[bold]%.0f[/bold]' % cum.get(60, 0),
            '[bold]%.0f[/bold]' % cum.get(90, 0),
        )

    sections.append(cum_table)

    # --- Weekly Trend Table for Net Growth ---
    weekly_data = net.get('weekly_trend', [])
    if weekly_data:
        week_table = Table(
            title='Weekly Net Growth Trend',
            border_style='dim',
            title_style='bold bright_yellow',
            show_lines=False,
        )
        week_table.add_column('Week', style='dim', width=10)
        week_table.add_column('Avg/Day', justify='right', width=10)
        week_table.add_column('', width=32)

        week_vals = [w[1] for w in weekly_data]
        max_abs = max(abs(v) for v in week_vals) if week_vals else 1

        for week_label, avg_val in weekly_data:
            if avg_val >= 0:
                bar = _build_gradient_bar(avg_val, max_abs, 'green', width=30)
                val_str = '[bright_yellow]+%.1f[/bright_yellow]' % avg_val
            else:
                bar = _build_gradient_bar(abs(avg_val), max_abs, 'red', width=30)
                val_str = '[green]%.1f[/green]' % avg_val

            week_table.add_row(week_label, val_str, bar)

        sections.append(week_table)

    # --- Outer wrapper ---
    now = datetime.datetime.now()
    return Panel(
        Group(*sections),
        title='\U0001f52e [bold]Activity Forecast[/bold]',
        subtitle='[bold bright_green]v%s[/bold bright_green] [dim]\u2502 rendered %s[/dim]' % (__version__, now.strftime('%Y-%m-%d %H:%M:%S')),
        border_style='bright_yellow',
        padding=(1, 2),
    )


def render_forecast(metrics_data):
    # type: (dict) -> None
    """Render the activity forecast and print it to the console.

    Args:
        metrics_data: dict from ``read_metrics``.
    """
    console.print(_build_forecast(metrics_data))


def _watch_loop(metrics_file, interval, forecast=False):
    # type: (str, int, bool) -> None
    """Run the dashboard in live-refresh mode.

    Re-reads the metrics database every *interval* seconds and updates
    the terminal in-place using Rich's ``Live`` display.  Press
    Ctrl-C to exit.

    Args:
        metrics_file: Path to the metrics file (the .db sibling is used).
        interval: Refresh interval in seconds (minimum 1).
        forecast: If True, show the forecast view instead of the
            default dashboard.
    """
    from rich.live import Live

    interval = max(1, interval)
    builder = _build_forecast if forecast else _build_dashboard

    try:
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while True:
                metrics_data = read_metrics(metrics_file)
                renderable = builder(metrics_data)
                live.update(renderable)
                time.sleep(interval)
    except KeyboardInterrupt:
        console.print('\n[dim]Watch mode stopped.[/dim]')


def main():
    # type: () -> None
    """Entry point for the metrics dashboard.

    Parses ``--metrics-file`` and optional ``--history`` / ``--forecast``
    arguments.  With ``--history``, displays trend charts.  With
    ``--forecast``, displays capacity projections.
    """
    parser = argparse.ArgumentParser(
        description='Snapshot Metrics Dashboard'
    )
    default_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'metrics',
        'snapshot_metrics.json',
    )
    parser.add_argument(
        '--metrics-file',
        default=default_path,
        help='Path to the metrics file (default: %(default)s)',
    )
    parser.add_argument(
        '--history',
        type=int,
        choices=[7, 30, 90],
        default=None,
        metavar='DAYS',
        help='Show historical trends for 7, 30, or 90 days',
    )
    parser.add_argument(
        '--forecast',
        action='store_true',
        default=False,
        help='Show activity volume forecasting based on historical data',
    )
    parser.add_argument(
        '--watch',
        type=int,
        default=None,
        nargs='?',
        const=5,
        metavar='SECONDS',
        help='Refresh the dashboard every N seconds (default: 5). '
             'Works with the default dashboard and --forecast views.',
    )
    args = parser.parse_args()

    # Check if metrics data exists (SQLite .db file or legacy .json)
    db_path = os.path.splitext(os.path.abspath(args.metrics_file))[0] + '.db'
    if not os.path.isfile(args.metrics_file) and not os.path.isfile(db_path):
        console.print('[yellow]No metrics data available.[/yellow]')
        return

    # For legacy .json-only setups, check the file isn't empty
    if os.path.isfile(args.metrics_file) and not os.path.isfile(db_path):
        try:
            file_size = os.path.getsize(args.metrics_file)
        except OSError:
            file_size = 0
        if file_size == 0:
            console.print('[yellow]No metrics data available.[/yellow]')
            return

    metrics_data = read_metrics(args.metrics_file)

    if args.watch is not None:
        _watch_loop(args.metrics_file, args.watch, forecast=args.forecast)
    elif args.history:
        render_history(metrics_data, days=args.history)
    elif args.forecast:
        render_forecast(metrics_data)
    else:
        render_dashboard(metrics_data)


if __name__ == '__main__':
    main()
