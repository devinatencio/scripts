"""
snapshot_cli.py - Interactive CLI for snapshot operations.

Provides commands for listing snapshots, viewing restore history,
checking cluster connectivity, and inspecting configuration.
Uses Rich tables for formatted terminal output.
"""

import argparse
import datetime
import getpass
import os
import re
import sys

from rich.console import Console
from rich.table import Table

from server.config_loader import find_config_file, load_server_config
from server.es_client import ESClient
from server.log_manager import setup_logger
from server.metrics_collector import record_snapshot_statuses

# Module-level console for Rich output
console = Console()

# Available commands
COMMANDS = ['list', 'list-restored', 'list-history',
            'clear-staged', 'show-config', 'ping', 'help']


def display_snapshots_table(snapshots_data):
    # type: (list) -> None
    """Render snapshots in a Rich table.

    Displays a table with columns: id, status, end_time, duration,
    total_shards.  Status values are color-coded: green for SUCCESS,
    red for FAILED, yellow for PARTIAL.

    Args:
        snapshots_data: List of dicts from ``es.cat.snapshots``
            (each dict has keys id, status, end_time, duration,
            total_shards, etc.).
    """
    if not snapshots_data:
        console.print('[yellow]No snapshots found.[/yellow]')
        return

    table = Table(title='Snapshots')
    table.add_column('ID', style='cyan')
    table.add_column('Status')
    table.add_column('End Time')
    table.add_column('Duration')
    table.add_column('Total Shards')

    status_colors = {
        'SUCCESS': 'green',
        'FAILED': 'red',
        'PARTIAL': 'yellow',
    }

    for snap in snapshots_data:
        snap_id = str(snap.get('id', ''))
        status = str(snap.get('status', ''))
        duration = str(snap.get('duration', ''))
        total_shards = str(snap.get('total_shards', ''))

        # Format end_epoch into a full date+time string; fall back to
        # the cat API's end_time (time-only) if end_epoch is missing.
        end_epoch = snap.get('end_epoch')
        if end_epoch:
            try:
                end_dt = datetime.datetime.fromtimestamp(int(end_epoch))
                end_time = end_dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError, OSError):
                end_time = str(snap.get('end_time', ''))
        else:
            end_time = str(snap.get('end_time', ''))

        color = status_colors.get(status, 'white')
        styled_status = '[%s]%s[/%s]' % (color, status, color)

        table.add_row(snap_id, styled_status, end_time, duration, total_shards)

    console.print(table)


def display_restored_table(es_client, tracking_index):
    # type: (ESClient, str) -> None
    """Query and display tracking index records in a Rich table.

    Scrolls through all documents in the tracking index and renders
    them in a table with columns: index_name, restore_date, status,
    username, message.

    Args:
        es_client: Connected ESClient instance.
        tracking_index: Name of the tracking index to query.
    """
    query = {'query': {'match_all': {}}}
    hits = es_client.search_scroll(tracking_index, query)

    if not hits:
        console.print('[yellow]No restored index records found.[/yellow]')
        return

    table = Table(title='Restored Indices')
    table.add_column('Index Name', style='cyan')
    table.add_column('Restore Date')
    table.add_column('Status')
    table.add_column('Username')
    table.add_column('Message')

    for hit in hits:
        source = hit.get('_source', {})
        table.add_row(
            str(source.get('index_name', '')),
            str(source.get('restore_date', '')),
            str(source.get('status', '')),
            str(source.get('username', '')),
            str(source.get('message', '')),
        )

    console.print(table)


def display_history_table(es_client, history_index):
    # type: (ESClient, str) -> None
    """Display last 50 history entries in a Rich table.

    Queries the history index sorted by datetime descending, limited
    to 50 entries.  Columns: datetime, username, status, message.

    Args:
        es_client: Connected ESClient instance.
        history_index: Name of the history index to query.
    """
    query = {
        'query': {'match_all': {}},
        'sort': [{'datetime': {'order': 'desc'}}],
        'size': 50,
    }

    try:
        hits = es_client.search_scroll(history_index, query)
    except Exception:
        hits = []

    if not hits:
        console.print('[yellow]No history entries found.[/yellow]')
        return

    # Limit to 50 entries (scroll may return more if index is small)
    entries = hits[:50]

    table = Table(title='Snapshot History (last 50)')
    table.add_column('Datetime')
    table.add_column('Username')
    table.add_column('Status')
    table.add_column('Message')

    for hit in entries:
        source = hit.get('_source', {})
        table.add_row(
            str(source.get('datetime', '')),
            str(source.get('username', '')),
            str(source.get('status', '')),
            str(source.get('message', '')),
        )

    console.print(table)


def _build_parser():
    # type: () -> argparse.ArgumentParser
    """Build the argument parser for the snapshot CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description='Snapshot CLI - list, search, and inspect snapshots.',
        usage='%(prog)s [options] command [regex]',
    )
    parser.add_argument(
        'command',
        nargs='?',
        default='help',
        choices=COMMANDS,
        help='Command to execute: %s' % ', '.join(COMMANDS),
    )
    parser.add_argument(
        'regex',
        nargs='?',
        default=None,
        help='Optional regex pattern to filter snapshots (list command).',
    )
    parser.add_argument(
        '--locations', '-locations',
        type=str,
        default='DEFAULT',
        help='Server configuration name to use.',
    )
    parser.add_argument(
        '--password', '-password',
        action='store_true',
        default=False,
        help='Prompt for Elasticsearch password interactively.',
    )
    parser.add_argument(
        '--size', '-size',
        action='store_true',
        default=False,
        help='Query and display snapshot sizes (list command).',
    )
    parser.add_argument(
        '--verbose', '-verbose',
        action='store_true',
        default=False,
        help='Use the slower cat/snapshots API for full detail '
             '(status, duration, shards). Default list uses the fast '
             'snapshot handler that skips per-shard validation.',
    )
    return parser


def _print_help():
    # type: () -> None
    """Print available commands and usage information."""
    console.print('\n[bold]Snapshot CLI Commands:[/bold]\n')
    console.print('  [cyan]list[/cyan]            List all snapshots (optional regex filter)')
    console.print('  [cyan]list-restored[/cyan]   Show restored index tracking records')
    console.print('  [cyan]list-history[/cyan]    Show last 50 history entries')
    console.print('  [cyan]clear-staged[/cyan]    Clear staged snapshot entries')
    console.print('  [cyan]show-config[/cyan]     Display current configuration')
    console.print('  [cyan]ping[/cyan]            Test Elasticsearch connectivity')
    console.print('  [cyan]help[/cyan]            Show this help message')
    console.print('\n[bold]Options:[/bold]\n')
    console.print('  --locations NAME  Select server configuration')
    console.print('  --password        Prompt for password interactively')
    console.print('  --size            Show snapshot sizes (list command)')
    console.print('  --verbose         Full detail via cat/snapshots (slower)')
    console.print('  regex             Filter snapshots by regex pattern\n')


def main():
    # type: () -> None
    """Entry point for the snapshot CLI.

    Commands: list, list-restored, list-history, clear-staged,
    show-config, ping, help.

    Args (via argparse):
        command: One of the supported commands.
        regex: Optional regex to filter snapshots in list command.
        --locations: Server config name (default: DEFAULT).
        --password: Prompt for password interactively.
        --size: Query snapshot sizes in list command.
    """
    parser = _build_parser()
    args = parser.parse_args()

    command = args.command

    # Handle help early (no ES connection needed)
    if command == 'help':
        _print_help()
        return

    # Set up logging
    logger = setup_logger('snapshot-cli')

    # Load configuration
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = find_config_file('elastic_servers.yml', [script_dir, '.'])
        config = load_server_config(config_file, server_name=args.locations)
    except (FileNotFoundError, ValueError) as exc:
        console.print('[red]Configuration error: %s[/red]' % exc)
        logger.error('Configuration error: %s', exc)
        sys.exit(1)

    # Handle show-config (no ES connection needed)
    if command == 'show-config':
        console.print('\n[bold]Current Configuration:[/bold]\n')
        for key, value in sorted(config.items()):
            if 'password' in key.lower():
                console.print('  %s: ********' % key)
            else:
                console.print('  %s: %s' % (key, value))
        console.print('')
        return

    # Determine password
    password = config.get('elastic_password')
    if args.password:
        password = getpass.getpass('Elasticsearch password: ')

    # Connect to Elasticsearch
    try:
        es = ESClient(
            hostname=config['hostname'],
            port=config['port'],
            use_ssl=config.get('use_ssl', False),
            username=config.get('elastic_username'),
            password=password,
            timeout=config.get('elastic_default_timeout', 300),
        )
    except ConnectionError as exc:
        console.print('[red]Connection failed: %s[/red]' % exc)
        logger.error('Elasticsearch connection failed: %s', exc)
        sys.exit(1)

    try:
        if command == 'list':
            _cmd_list(es, args, config)
        elif command == 'list-restored':
            tracking_index = config.get('elastic_restored_indice', 'rc_snapshots')
            display_restored_table(es, tracking_index)
        elif command == 'list-history':
            history_index = config.get('elastic_history_indice', 'rc_snapshots_history')
            display_history_table(es, history_index)
        elif command == 'clear-staged':
            console.print('[yellow]Clear-staged: no staged entries to clear.[/yellow]')
            logger.info('clear-staged command executed.')
        elif command == 'ping':
            _cmd_ping(es)
    finally:
        es.close()


def _cmd_list(es, args, config):
    # type: (ESClient, argparse.Namespace, dict) -> None
    """Execute the list command.

    By default uses the fast ``_snapshot`` API with ``verbose=false``
    which skips per-shard validation and returns only snapshot names.
    Pass ``--verbose`` (or ``--size``) to use the slower
    ``_cat/snapshots`` API that includes status, duration, and shard
    counts.

    Args:
        es: Connected ESClient instance.
        args: Parsed CLI arguments.
        config: Server configuration dict.
    """
    use_verbose = args.verbose or args.size
    repository = config.get('repository', '')

    if use_verbose:
        # Full detail via cat/snapshots (slower — validates each snapshot)
        try:
            snapshots_data = es.es.cat.snapshots(format='json')
        except Exception as exc:
            console.print('[red]Failed to retrieve snapshots: %s[/red]' % exc)
            return

        if not snapshots_data:
            console.print('[yellow]No snapshots found.[/yellow]')
            return

        # Filter by regex if provided
        if args.regex:
            try:
                pattern = re.compile(args.regex)
            except re.error as exc:
                console.print('[red]Invalid regex pattern: %s[/red]' % exc)
                return
            snapshots_data = [
                s for s in snapshots_data
                if pattern.search(str(s.get('id', '')))
            ]

        display_snapshots_table(snapshots_data)
        console.print('\nTotal: %d snapshots' % len(snapshots_data))

        # Record snapshot status distribution to metrics
        status_counts = {}
        for snap in snapshots_data:
            status = str(snap.get('status', 'UNKNOWN')).upper()
            status_counts[status] = status_counts.get(status, 0) + 1
        metrics_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'metrics',
            'snapshot_metrics.json',
        )
        try:
            record_snapshot_statuses(metrics_file, status_counts)
        except Exception:
            pass  # metrics recording is best-effort
    else:
        # Fast path via _snapshot API (verbose=false, no per-shard validation)
        if not repository:
            console.print('[red]No repository configured. Use --verbose to list via cat/snapshots.[/red]')
            return

        snapshots_brief = es.get_snapshots_brief(repository)

        if not snapshots_brief:
            console.print('[yellow]No snapshots found.[/yellow]')
            return

        # Filter by regex if provided
        if args.regex:
            try:
                pattern = re.compile(args.regex)
            except re.error as exc:
                console.print('[red]Invalid regex pattern: %s[/red]' % exc)
                return
            snapshots_brief = [
                s for s in snapshots_brief
                if pattern.search(str(s.get('snapshot', '')))
            ]

        # Render a lightweight table
        status_colors = {
            'SUCCESS': 'green',
            'FAILED': 'red',
            'PARTIAL': 'yellow',
            'IN_PROGRESS': 'bright_blue',
            'INCOMPATIBLE': 'magenta',
        }

        table = Table(title='Snapshots')
        table.add_column('#', style='dim', justify='right')
        table.add_column('Snapshot', style='cyan')
        table.add_column('State')
        table.add_column('Indices', justify='right')

        for idx, snap in enumerate(snapshots_brief, 1):
            state = str(snap.get('state', '')).upper()
            color = status_colors.get(state, 'white')
            indices = snap.get('indices', [])
            table.add_row(
                str(idx),
                str(snap.get('snapshot', '')),
                '[%s]%s[/%s]' % (color, state, color),
                str(len(indices)),
            )

        console.print(table)
        console.print('\nTotal: %d snapshots' % len(snapshots_brief))
        console.print('[dim]Use --verbose for full detail (duration, shards, end time).[/dim]')


def _cmd_ping(es):
    # type: (ESClient) -> None
    """Execute the ping command.

    Tests the Elasticsearch connection and reports cluster health.

    Args:
        es: Connected ESClient instance.
    """
    if es.ping():
        status, rich_status = es.get_cluster_health()
        console.print('[green]Connection successful.[/green]')
        console.print('Cluster health: %s' % rich_status)
    else:
        console.print('[red]Connection failed. Cluster is not reachable.[/red]')


if __name__ == '__main__':
    main()
