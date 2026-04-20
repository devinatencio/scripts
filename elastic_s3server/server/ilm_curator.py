"""
ilm_curator.py - Delete cold indices with verified snapshots.

Cron utility that retrieves all snapshots with metadata and all indices
with their ILM phase information, then deletes cold indices only after
verifying a matching successful snapshot exists (status SUCCESS, zero
failed shards) and is older than a configurable delay.  This acts as a
safety gate for ILM-driven index removal.
"""

import argparse
import os
import sys
import time

from server.config_loader import find_config_file, load_server_config
from server.es_client import ESClient
from server.log_manager import setup_logger
from server.metrics_collector import increment_counter, record_health

# Version
from server import __version__

# Metrics path reference — metrics_collector derives the .db path from this
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_METRICS_FILE = os.path.join(_MODULE_DIR, 'metrics', 'snapshot_metrics.json')


def get_cold_indices(ilm_data):
    # type: (dict) -> list
    """Extract index names in the cold ILM phase.

    Args:
        ilm_data: Dict returned by ``ESClient.get_index_ilms(short=True)``,
            mapping index names to ``{phase, age, policy}`` dicts.

    Returns:
        List of index name strings whose phase is ``'cold'``.
    """
    result = []
    for index_name, info in ilm_data.items():
        if info.get('phase') == 'cold':
            result.append(index_name)
    return result


def hours_since_epoch(epoch_timestamp):
    # type: (int) -> float
    """Calculate hours between now and an epoch timestamp.

    Args:
        epoch_timestamp: Epoch timestamp (int or string) in seconds.

    Returns:
        Float representing the number of hours since the given epoch.
    """
    epoch_int = int(epoch_timestamp)
    now_epoch = int(time.time())
    diff_seconds = now_epoch - epoch_int
    return diff_seconds / 3600.0


def format_age(hours):
    # type: (float) -> str
    """Format an age in hours into the most readable unit.

    Picks the largest unit where the value is >= 1:
        - days   if >= 24 h
        - hours  if >= 1 h
        - minutes otherwise

    Args:
        hours: Age expressed as a float in hours.

    Returns:
        Human-readable string like ``'2.5 days'``, ``'6.0 hours'``,
        or ``'42.0 minutes'``.
    """
    if hours >= 24:
        return '%.1f days' % (hours / 24.0)
    if hours >= 1:
        return '%.1f hours' % hours
    return '%.1f minutes' % (hours * 60)


def process_indices_for_deletion(es_client, snapshots_metadata, ilm_data, hours_delay=6, logger=None, dry_run=False):
    # type: (ESClient, dict, dict, int, object, bool) -> tuple
    """Delete cold indices that have a verified successful snapshot.

    Iterates over *snapshots_metadata* (the inner dict from
    ``get_snapshots_with_metadata``).  For each snapshot whose name
    follows the ``snapshot_{index_name}`` convention:

    1. Check if the corresponding index is in the cold ILM phase.
    2. Check if the snapshot status is ``SUCCESS`` and failed_shards is
       ``'0'`` or ``0``.
    3. Check if the snapshot age (via ``hours_since_epoch(end_epoch)``)
       is >= *hours_delay*.

    If all conditions are met the index is deleted via
    ``es_client.delete_index()`` — unless *dry_run* is True, in which
    case the action is only logged.

    Args:
        es_client: Connected ESClient instance.
        snapshots_metadata: Dict of
            ``{snapshot_id: {status, failed_shards, end_epoch, ...}}``.
        ilm_data: Dict returned by ``ESClient.get_index_ilms(short=True)``.
        hours_delay: Minimum snapshot age in hours before deletion is
            allowed.  Defaults to 6.
        logger: Optional logger instance for status messages.
        dry_run: If True, log what would be done without deleting.

    Returns:
        Tuple of (deleted_count, skipped_count).
    """
    cold_indices = set(get_cold_indices(ilm_data))
    deleted_count = 0
    skipped_count = 0

    for snapshot_name, metadata in snapshots_metadata.items():
        # Derive index name from snapshot name
        if not snapshot_name.startswith('snapshot_'):
            continue
        index_name = snapshot_name[len('snapshot_'):]

        # Check if the index is in the cold phase
        if index_name not in cold_indices:
            continue

        status = metadata.get('status', '')
        failed_shards = metadata.get('failed_shards', '')
        end_epoch = metadata.get('end_epoch', '')

        # Check snapshot status
        if status != 'SUCCESS':
            if logger:
                logger.info(
                    'Skipping %s: snapshot status is %s (not SUCCESS).',
                    snapshot_name, status,
                )
            skipped_count += 1
            continue

        # Check failed shards
        if str(failed_shards) != '0':
            if logger:
                logger.info(
                    'Skipping %s: failed_shards is %s (not 0).',
                    snapshot_name, failed_shards,
                )
            skipped_count += 1
            continue

        # Check snapshot age
        if not end_epoch:
            if logger:
                logger.info(
                    'Skipping %s: no end_epoch available.',
                    snapshot_name,
                )
            skipped_count += 1
            continue

        try:
            age_hours = hours_since_epoch(end_epoch)
        except (ValueError, TypeError):
            if logger:
                logger.info(
                    'Skipping %s: could not parse end_epoch %s.',
                    snapshot_name, end_epoch,
                )
            skipped_count += 1
            continue

        if age_hours < hours_delay:
            if logger:
                logger.info(
                    'Skipping %s: age %s < delay %s.',
                    snapshot_name, format_age(age_hours),
                    format_age(hours_delay),
                )
            skipped_count += 1
            continue

        # All checks passed — log the verified status at DEBUG level
        if logger:
            logger.debug(
                'Verified %s: status=%s, failed_shards=%s, age=%s — safe to delete index.',
                snapshot_name, status, failed_shards, format_age(age_hours),
            )

        # All conditions met - delete the index
        if logger:
            logger.info(
                '%sDeleting index %s: snapshot %s, end_epoch %s, age %s.',
                '[dry-run] Would delete — ' if dry_run else '',
                index_name, snapshot_name, end_epoch, format_age(age_hours),
            )

        if dry_run:
            deleted_count += 1
            continue

        ok = es_client.delete_index(index_name)
        if ok:
            deleted_count += 1
            if logger:
                logger.info('Successfully deleted index %s.', index_name)
        else:
            if logger:
                logger.error('Failed to delete index %s.', index_name)
            skipped_count += 1

    return (deleted_count, skipped_count)


def main():
    # type: () -> None
    """Entry point for the ILM curator utility.

    Parses command-line arguments, loads configuration, connects to
    Elasticsearch, retrieves snapshot metadata and ILM data, and deletes
    cold indices that have a verified successful snapshot older than the
    configured delay.

    CLI arguments:
        --debug     Enable verbose DEBUG logging.
        --noaction  Dry-run mode; log what would be done without acting.
    """
    parser = argparse.ArgumentParser(
        description='Delete cold Elasticsearch indices with verified S3 snapshots.'
    )
    parser.add_argument(
        '--debug', '-debug',
        action='store_true',
        default=False,
        help='Enable verbose debug logging.',
    )
    parser.add_argument(
        '--noaction', '-noaction',
        action='store_true',
        default=False,
        help='Report indices that would be deleted without performing deletions.',
    )
    args = parser.parse_args()

    # Set up logging
    logger = setup_logger('ilm-curator', debug=args.debug)
    logger.info('ILM-curator v%s starting...', __version__)

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
    repository = config.get('repository', '')
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
        record_health(_METRICS_FILE, 'ilm_curator', False)
        sys.exit(1)

    # ── Step 1: Fast-list all snapshots (verbose=false — includes state) ──
    all_snapshots_brief = es.get_snapshots_brief(repository)
    logger.info('STATS: Snapshots: [ %d ] found (fast list).', len(all_snapshots_brief))

    # Build lookup: snapshot_name -> brief data
    snapshot_lookup = {}
    for s in all_snapshots_brief:
        snapshot_lookup[s.get('snapshot', '')] = s

    # Retrieve ILM data
    ilm_data = es.get_index_ilms(short=True)
    cold_indices = get_cold_indices(ilm_data)
    logger.info('STATS: Cold indices: [ %d ] found.', len(cold_indices))

    if args.debug:
        logger.debug('Cold indices: %s', cold_indices)

    # ── Step 2: Pre-filter to SUCCESS snapshots, then targeted detail query ──
    # Only query details for snapshots that are SUCCESS in the fast list —
    # we need end_epoch for the age check, which verbose=false doesn't provide.
    candidate_snapshot_names = []
    for index_name in cold_indices:
        snap_name = 'snapshot_%s' % index_name
        snap_info = snapshot_lookup.get(snap_name)
        if snap_info is None:
            continue  # no snapshot exists
        state = str(snap_info.get('state', '')).upper()
        indices_count = len(snap_info.get('indices', []))
        data_streams = len(snap_info.get('data_streams', []))
        if state != 'SUCCESS':
            if args.debug:
                logger.debug(
                    'Skipping %s: state=%s, indices=%d, data_streams=%d — no detail query needed.',
                    snap_name, state, indices_count, data_streams,
                )
            continue
        if args.debug:
            logger.debug(
                'Candidate %s: state=%s, indices=%d, data_streams=%d — querying age.',
                snap_name, state, indices_count, data_streams,
            )
        candidate_snapshot_names.append(snap_name)

    logger.info(
        'Checking age of [ %d ] SUCCESS snapshots (targeted query).',
        len(candidate_snapshot_names),
    )

    snapshot_details = es.get_snapshot_details(
        repository, candidate_snapshot_names, logger=logger,
    )

    # Convert to the format process_indices_for_deletion expects:
    # {snapshot_name: {status, failed_shards, end_epoch, ...}}
    snapshots = {}
    for snap_name, detail in snapshot_details.items():
        snapshots[snap_name] = {
            'status': detail.get('state', ''),
            'failed_shards': detail.get('failed_shards', 0),
            'end_epoch': detail.get('end_epoch', ''),
        }

    logger.info(
        'Retrieved detailed status for [ %d ] of [ %d ] candidates.',
        len(snapshots), len(candidate_snapshot_names),
    )

    # Process indices for deletion
    hours_delay = config.get('ilm_curator_delay', 6.0)
    logger.info('Using ILM curator delay: %s', format_age(hours_delay))

    if args.noaction:
        logger.info('--noaction specified; no indices will be deleted.')

    deleted, skipped = process_indices_for_deletion(
        es, snapshots, ilm_data, hours_delay=hours_delay, logger=logger,
        dry_run=args.noaction,
    )
    logger.info(
        'ILM curation complete. %s%d, Skipped: %d',
        'Would delete: ' if args.noaction else 'Deleted: ',
        deleted, skipped,
    )

    # Record metrics (skip counters during dry-run)
    if deleted > 0 and not args.noaction:
        increment_counter(_METRICS_FILE, 'indices_deleted_ilm', deleted)

    record_health(_METRICS_FILE, 'ilm_curator', True)
    logger.info('ILM-curator script ending.')

    es.close()


if __name__ == '__main__':
    main()
