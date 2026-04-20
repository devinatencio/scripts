"""
retention_enforcer.py - Purge old snapshots by retention policy.

Cron utility that retrieves all snapshots, calculates their age, matches
each against per-pattern retention policies from a YAML file, and deletes
those exceeding their applicable retention period.  Supports regex
filtering, dry-run mode, default-days override, and repository override.
"""

import argparse
import os
import re
import sys
import time

from server.config_loader import (
    find_config_file,
    load_retention_config,
    load_server_config,
)
from server.es_client import ESClient
from server.log_manager import setup_logger
from server.metrics_collector import increment_counter, record_health

# Version
from server import __version__

# Metrics path reference — metrics_collector derives the .db path from this
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_METRICS_FILE = os.path.join(_MODULE_DIR, 'metrics', 'snapshot_metrics.json')


def calculate_snapshot_age_days(start_epoch_str):
    # type: (str) -> int
    """Calculate age in days from an epoch timestamp string.

    Converts *start_epoch_str* to an integer epoch, computes the
    difference from the current time, and returns the floor of the
    result in days.

    Args:
        start_epoch_str: Epoch timestamp as a string (seconds since
            1970-01-01 00:00:00 UTC).

    Returns:
        Non-negative integer representing the age in whole days.
    """
    start_epoch = int(start_epoch_str)
    now_epoch = int(time.time())
    diff_seconds = now_epoch - start_epoch
    return diff_seconds // 86400


def get_retention_days(snapshot_name, retention_policies, default_days):
    # type: (str, dict, int) -> int
    """Determine the retention period for a snapshot.

    Strips the ``snapshot_`` prefix from *snapshot_name*, then iterates
    through *retention_policies* (a dict of ``{regex_pattern: max_days}``).
    Returns the ``max_days`` of the first matching pattern, or
    *default_days* if no pattern matches.

    Args:
        snapshot_name: Full snapshot name (e.g.
            ``'snapshot_.ds-logs-foo-2024.01.01'``).
        retention_policies: Dict mapping regex pattern strings to
            integer max_days values.
        default_days: Fallback retention period when no pattern matches.

    Returns:
        Integer retention period in days.
    """
    # Strip the snapshot_ prefix for matching
    if snapshot_name.startswith('snapshot_'):
        name_for_matching = snapshot_name[len('snapshot_'):]
    else:
        name_for_matching = snapshot_name

    for pattern, max_days in retention_policies.items():
        if re.match(pattern, name_for_matching):
            return max_days

    return default_days


def process_snapshots_for_deletion(snapshots, retention_policies, default_days, regex_pattern='.*'):
    # type: (dict, dict, int, str) -> dict
    """Evaluate snapshots against retention policies.

    For each snapshot in *snapshots*, filters by *regex_pattern*,
    calculates the snapshot age, determines the applicable retention
    period, and collects those whose age exceeds their retention.

    Args:
        snapshots: Dict of ``{snapshot_name: metadata_dict}`` where
            each metadata dict contains at least a ``'start_epoch'``
            key.  This matches the inner dict returned by
            ``ESClient.get_snapshots_with_metadata(location)``.
        retention_policies: Dict mapping regex pattern strings to
            integer max_days values.
        default_days: Fallback retention period when no policy matches.
        regex_pattern: Only snapshots whose name matches this regex
            are considered.  Defaults to ``'.*'`` (match everything).

    Returns:
        Dict of ``{snapshot_name: age_days}`` for snapshots exceeding
        their applicable retention period.
    """
    to_delete = {}

    for snapshot_name, metadata in snapshots.items():
        # Filter by regex pattern
        if not re.match(regex_pattern, snapshot_name):
            continue

        start_epoch_str = metadata.get('start_epoch', '')
        if not start_epoch_str:
            continue

        try:
            age_days = calculate_snapshot_age_days(start_epoch_str)
        except (ValueError, TypeError):
            continue

        retention_days = get_retention_days(
            snapshot_name, retention_policies, default_days
        )

        if age_days > retention_days:
            to_delete[snapshot_name] = age_days

    return to_delete


def main():
    # type: () -> None
    """Entry point for the retention enforcer utility.

    Parses command-line arguments, loads configuration and retention
    policies, connects to Elasticsearch, evaluates each snapshot against
    its applicable retention period, and either reports (``--noaction``)
    or deletes the expired snapshots.

    CLI arguments:
        --debug      Enable verbose DEBUG logging.
        --days       Override the default retention period (days).
        --pattern    Regex to limit which snapshots are processed.
        --noaction   Dry-run mode; log what would be done without acting.
        --repository Override the configured S3 repository name.
    """
    parser = argparse.ArgumentParser(
        description='Purge old Elasticsearch snapshots by retention policy.'
    )
    parser.add_argument(
        '--debug', '-debug',
        action='store_true',
        default=False,
        help='Enable verbose debug logging.',
    )
    parser.add_argument(
        '--days', '-days',
        type=int,
        default=None,
        help='Override default retention period in days.',
    )
    parser.add_argument(
        '--pattern', '-pattern',
        type=str,
        default='.*',
        help='Regex pattern to filter snapshots.',
    )
    parser.add_argument(
        '--noaction', '-noaction',
        action='store_true',
        default=False,
        help='Report snapshots that would be deleted without performing deletions.',
    )
    parser.add_argument(
        '--repository', '-repository', '-repos',
        type=str,
        default=None,
        help='Override the configured S3 repository.',
    )
    args = parser.parse_args()

    # Set up logging
    logger = setup_logger('retention-enforcer', debug=args.debug)
    logger.info('Retention-enforcer v%s starting...', __version__)

    # Load configuration
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = find_config_file('elastic_servers.yml', [script_dir, '.'])
        config = load_server_config(config_file)
    except (FileNotFoundError, ValueError) as exc:
        logger.error('Configuration error: %s', exc)
        sys.exit(1)

    logger.info('Config file: %s', config_file)

    # Load retention policies
    try:
        retention_file = find_config_file('elastic_retention.yml', [script_dir, '.'])
        retention_policies = load_retention_config(retention_file)
    except FileNotFoundError:
        logger.info('No retention config found; using default retention only.')
        retention_policies = {}

    # Determine default retention days
    default_days = config.get('default_retention_maxdays', 30)
    if args.days is not None:
        default_days = args.days
    logger.info('Default retention days: %d', default_days)

    # Determine repository
    repository = args.repository if args.repository is not None else config.get('repository', '')
    logger.info('Using repository: %s', repository)

    # Connect to Elasticsearch
    try:
        es = ESClient(
            hostname=config['hostname'],
            port=config['port'],
            use_ssl=config.get('use_ssl', False),
            username=config.get('elastic_username'),
            password=config.get('elastic_password'),
            timeout=config.get('elastic_default_timeout', 300),
        )
    except ConnectionError as exc:
        logger.error('Elasticsearch connection failed: %s', exc)
        record_health(_METRICS_FILE, 'retention_enforcer', False)
        sys.exit(1)

    # Retrieve snapshots with metadata
    snapshots_data = es.get_snapshots_with_metadata(location=repository)
    snapshots = snapshots_data.get(repository, {})
    logger.info('STATS: Snapshots: [ %d ] found.', len(snapshots))

    if args.debug:
        logger.debug('Retention policies: %s', retention_policies)

    # Process snapshots for deletion
    to_delete = process_snapshots_for_deletion(
        snapshots, retention_policies, default_days, args.pattern
    )
    logger.info(
        'Snapshots exceeding retention: [ %d ] List: %s',
        len(to_delete), list(to_delete.keys()),
    )

    # Execute or dry-run
    if args.noaction:
        logger.info('--noaction specified; no snapshots will be deleted.')
        for snap_name, age in to_delete.items():
            logger.info('Would delete: %s (age: %d days)', snap_name, age)
    else:
        deleted_count = 0
        for snap_name, age in to_delete.items():
            ok, result = es.delete_snapshot(snap_name, repository)
            if ok:
                logger.info('Deleted snapshot: %s (age: %d days)', snap_name, age)
                deleted_count += 1
            else:
                logger.error('Failed to delete snapshot %s: %s', snap_name, result)

        # Record metrics
        if deleted_count > 0:
            increment_counter(_METRICS_FILE, 'snapshots_deleted', deleted_count)

    # Record health
    record_health(_METRICS_FILE, 'retention_enforcer', True)
    logger.info('Retention-enforcer script ending.')

    es.close()


if __name__ == '__main__':
    main()
