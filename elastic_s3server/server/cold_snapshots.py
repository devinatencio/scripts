"""
cold_snapshots.py - Snapshot cold indices to S3.

Cron utility that detects Elasticsearch indices in the cold ILM phase
that do not yet have a corresponding S3 snapshot and creates one for
each.  Supports regex filtering, dry-run mode, and repository override.
"""

import argparse
import os
import re
import sys

from server.config_loader import find_config_file, load_server_config
from server.es_client import ESClient
from server.log_manager import setup_logger
from server.metrics_collector import increment_counter, record_health

# Version
from server import __version__

# Metrics path reference — metrics_collector derives the .db path from this
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_METRICS_FILE = os.path.join(_MODULE_DIR, 'metrics', 'snapshot_metrics.json')


def get_cold_indices_needing_backup(cold_indices, successful_snapshots, regex_pattern='.*'):
    # type: (list, set, str) -> list
    """Compare cold indices against successfully snapshotted names.

    Returns a list of index names that are in the cold phase, match the
    given *regex_pattern*, and either have no corresponding
    ``snapshot_{index_name}`` entry in *successful_snapshots* or whose
    existing snapshot was not successful.

    Args:
        cold_indices: List of index name strings in the cold ILM phase.
        successful_snapshots: Set of snapshot name strings that are
            confirmed SUCCESS with zero failed shards.
        regex_pattern: Only indices whose name matches this regex are
            considered.  Defaults to ``'.*'`` (match everything).

    Returns:
        List of index name strings needing backup.
    """
    result = []

    for index_name in cold_indices:
        # Filter by regex pattern
        if not re.match(regex_pattern, index_name):
            continue

        # Check if a matching *successful* snapshot exists
        expected_snapshot = 'snapshot_%s' % index_name
        if expected_snapshot not in successful_snapshots:
            result.append(index_name)

    return result


def backup_cold_indices(es_client, indices, repository, logger):
    # type: (ESClient, list, str, object) -> tuple
    """Create snapshots for a list of indices.

    For each index in *indices*, creates a snapshot named
    ``snapshot_{index_name}`` in the given *repository*.

    Args:
        es_client: Connected ESClient instance.
        indices: List of index name strings to snapshot.
        repository: S3 repository name.
        logger: Logger instance for status messages.

    Returns:
        Tuple of (success_count, failure_count).
    """
    success_count = 0
    failure_count = 0

    for index_name in indices:
        snapshot_name = 'snapshot_%s' % index_name
        ok, result = es_client.create_snapshot(index_name, snapshot_name, repository)

        if ok:
            logger.info('Snapshot accepted for %s.', index_name)
            success_count += 1
        else:
            logger.error('Snapshot failed for %s: %s', index_name, result)
            failure_count += 1

    return (success_count, failure_count)


def main():
    # type: () -> None
    """Entry point for the cold snapshots utility.

    Parses command-line arguments, loads configuration, connects to
    Elasticsearch, identifies cold indices needing backup, and either
    reports (``--noaction``) or creates the snapshots.

    CLI arguments:
        --debug      Enable verbose DEBUG logging.
        --pattern    Regex to limit which cold indices are processed.
        --noaction   Dry-run mode; log what would be done without acting.
        --repository Override the configured S3 repository name.
    """
    parser = argparse.ArgumentParser(
        description='Snapshot cold Elasticsearch indices to S3.'
    )
    parser.add_argument(
        '--debug', '-debug',
        action='store_true',
        default=False,
        help='Enable verbose debug logging.',
    )
    parser.add_argument(
        '--pattern', '-pattern',
        type=str,
        default='.*',
        help='Regex pattern to filter cold indices.',
    )
    parser.add_argument(
        '--noaction', '-noaction',
        action='store_true',
        default=False,
        help='Report indices needing backup without creating snapshots.',
    )
    parser.add_argument(
        '--repository', '-repository', '-repos',
        type=str,
        default=None,
        help='Override the configured S3 repository.',
    )
    args = parser.parse_args()

    # Set up logging
    logger = setup_logger('cold-snapshots', debug=args.debug)
    logger.info('Cold-snapshots v%s starting...', __version__)

    # Load configuration
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = find_config_file('elastic_servers.yml', [script_dir, '.'])
        config = load_server_config(config_file)
    except (FileNotFoundError, ValueError) as exc:
        logger.error('Configuration error: %s', exc)
        sys.exit(1)

    logger.info('Config file: %s', config_file)

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
        record_health(_METRICS_FILE, 'cold_snapshots', False)
        sys.exit(1)

    # ── Step 1: Fast-list all snapshots (verbose=false — includes state) ──
    all_snapshots_brief = es.get_snapshots_brief(repository)
    logger.info('STATS: Snapshots: [ %d ] found (fast list).', len(all_snapshots_brief))

    # Build a lookup: snapshot_name -> brief data from the fast list
    # verbose=false on ES 7.17 returns state, indices, data_streams
    snapshot_lookup = {}
    for s in all_snapshots_brief:
        snapshot_lookup[s.get('snapshot', '')] = s

    # ── Step 2: Get cold indices from ILM ──
    index_ilms = es.get_index_ilms(short=True)
    cold_indices = [
        index for index, info in index_ilms.items()
        if info.get('phase') == 'cold'
    ]
    logger.info('STATS: Cold indices: [ %d ] found.', len(cold_indices))

    if args.debug:
        logger.debug('Cold indices: %s', cold_indices)

    # ── Step 3: Check snapshot state for each cold index (no extra API calls) ──
    successful_snapshots = set()
    checked = 0
    for index_name in cold_indices:
        if not re.match(args.pattern, index_name):
            continue
        snap_name = 'snapshot_%s' % index_name
        snap_info = snapshot_lookup.get(snap_name)
        if snap_info is None:
            continue  # no snapshot exists at all
        checked += 1
        state = str(snap_info.get('state', '')).upper()
        indices_count = len(snap_info.get('indices', []))
        data_streams = len(snap_info.get('data_streams', []))
        if state == 'SUCCESS':
            successful_snapshots.add(snap_name)
            if args.debug:
                logger.debug(
                    'Snapshot %s: state=%s, indices=%d, data_streams=%d — OK',
                    snap_name, state, indices_count, data_streams,
                )
        else:
            logger.info(
                'Snapshot %s: state=%s, indices=%d, data_streams=%d — will re-snapshot.',
                snap_name, state, indices_count, data_streams,
            )

    logger.info(
        'Snapshot status summary: %d checked, %d successful, %d need re-snapshot.',
        checked, len(successful_snapshots),
        checked - len(successful_snapshots),
    )

    # ── Step 4: Identify indices needing backup ──
    # An index needs backup if it has no snapshot at all OR its snapshot wasn't SUCCESS
    to_backup = get_cold_indices_needing_backup(
        cold_indices, successful_snapshots, args.pattern
    )
    logger.info(
        'Indices needing backup: [ %d ] List: %s', len(to_backup), to_backup
    )

    # Execute or dry-run
    if args.noaction:
        logger.info('--noaction specified; no snapshots will be created.')
    else:
        success, failure = backup_cold_indices(es, to_backup, repository, logger)
        logger.info(
            'Backup complete. Success: %d, Failure: %d', success, failure
        )
        # Record metrics
        if success > 0:
            increment_counter(_METRICS_FILE, 'snapshots_created', success)

    # Record health
    record_health(_METRICS_FILE, 'cold_snapshots', True)
    logger.info('Cold-snapshots script ending.')

    es.close()


if __name__ == '__main__':
    main()
