"""
restored_index_manager.py - Clean up aged restored indices.

Cron utility that queries the tracking index for all recorded restored
indices, calculates their age, and deletes those exceeding the configured
maximum age.  Stale records (where the index no longer exists in the
cluster) are also removed.  Supports dry-run mode, server selection,
max-days override, and custom config file path.
"""

import argparse
import datetime
import os
import sys

from server.config_loader import find_config_file, load_server_config
from server.es_client import ESClient, retry_with_backoff
from server.log_manager import setup_logger
from server.metrics_collector import record_health

# Version
from server import __version__

# Mapping for the tracking index (rc_snapshots)
_TRACKING_INDEX_MAPPINGS = {
    'properties': {
        'index_name': {'type': 'keyword'},
        'restore_date': {'type': 'date'},
        'status': {'type': 'keyword'},
        'username': {'type': 'keyword'},
        'message': {'type': 'text'},
    }
}

# Metrics path reference — metrics_collector derives the .db path from this
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_METRICS_FILE = os.path.join(_MODULE_DIR, 'metrics', 'snapshot_metrics.json')


def ensure_tracking_index(es_client, tracking_index, logger):
    # type: (ESClient, str, object) -> bool
    """Create the tracking index with explicit mappings if it doesn't exist.

    Args:
        es_client: Connected ESClient instance.
        tracking_index: Name of the tracking index.
        logger: Logger instance.

    Returns:
        True if the index exists (or was created), False on failure.
    """
    try:
        if es_client.es.indices.exists(index=tracking_index):
            return True
    except Exception as exc:
        logger.error(
            'Failed to check tracking index %s: %s', tracking_index, exc
        )
        return False

    logger.info(
        'Tracking index %s does not exist. Creating it.', tracking_index
    )
    try:
        es_client.es.indices.create(
            index=tracking_index,
            settings={
                'number_of_shards': 1,
                'number_of_replicas': 1,
            },
            mappings=_TRACKING_INDEX_MAPPINGS,
        )
        logger.info('Created tracking index %s.', tracking_index)
        return True
    except Exception as exc:
        logger.error(
            'Failed to create tracking index %s: %s', tracking_index, exc
        )
        return False


def calculate_days_since_restore(restore_date_str):
    # type: (str) -> int or None
    """Calculate days since restore from an ISO date string.

    Parses *restore_date_str* as an ISO 8601 datetime (e.g.
    ``"2025-01-12T10:30:00.000Z"``) and returns the number of whole
    days between that date and now.

    Args:
        restore_date_str: ISO 8601 datetime string.

    Returns:
        Non-negative integer representing the age in whole days,
        or ``None`` if the date string cannot be parsed.
    """
    if not restore_date_str:
        return None

    try:
        # Handle ISO format with optional milliseconds and Z suffix
        date_str = restore_date_str.replace('Z', '+00:00')
        # Strip sub-second precision for Python 3.6 compat
        if '.' in date_str:
            # Split at dot, keep date part, strip fractional before timezone
            base, rest = date_str.split('.', 1)
            # rest might be like "000+00:00" or "000Z" (already replaced)
            # Find the timezone part (+ or - after the fractional seconds)
            tz_part = ''
            for i, ch in enumerate(rest):
                if ch in ('+', '-'):
                    tz_part = rest[i:]
                    break
            date_str = base + tz_part

        if '+' in date_str or date_str.endswith('Z'):
            # Has timezone info - parse with %z
            # Python 3.6 strptime %z expects +HHMM not +HH:MM
            # Normalize +00:00 -> +0000
            if '+' in date_str:
                parts = date_str.rsplit('+', 1)
                tz = parts[1].replace(':', '')
                date_str = parts[0] + '+' + tz
            elif '-' in date_str and 'T' in date_str:
                # Negative timezone offset
                parts = date_str.rsplit('-', 1)
                tz = parts[1].replace(':', '')
                date_str = parts[0] + '-' + tz

            restore_dt = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z')
            now = datetime.datetime.now(datetime.timezone.utc)
        else:
            # No timezone info - treat as UTC
            restore_dt = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
            now = datetime.datetime.utcnow()

        diff = now - restore_dt
        return max(0, diff.days)
    except (ValueError, TypeError, AttributeError):
        return None


def process_restored_indices(es_client, tracking_index, max_days, logger, dry_run=False):
    # type: (ESClient, str, int, object, bool) -> tuple
    """Scroll through tracking index and clean up expired or stale records.

    For each record in the tracking index:
    - If the index no longer exists in the cluster, remove the stale
      record from the tracking index.
    - If the index exists and its age >= *max_days*, delete the index
      from the cluster and remove the record from the tracking index.
    - If the index exists and its age < *max_days*, skip it.

    Uses ``retry_with_backoff`` for Elasticsearch operations.

    Args:
        es_client: Connected ESClient instance.
        tracking_index: Name of the tracking index to query.
        max_days: Maximum age in days before a restored index is deleted.
        logger: Logger instance for status messages.
        dry_run: If True, log actions without performing them.

    Returns:
        Tuple of (processed_count, deleted_count, error_count).
    """
    processed_count = 0
    deleted_count = 0
    error_count = 0

    # Scroll through all records in the tracking index
    query = {"query": {"match_all": {}}}

    try:
        hits = retry_with_backoff(
            lambda: es_client.search_scroll(tracking_index, query),
            max_retries=3,
            delay=1,
        )
    except Exception as exc:
        logger.error('Failed to scroll tracking index %s: %s', tracking_index, exc)
        return (0, 0, 1)

    logger.info('Found %d records in tracking index %s.', len(hits), tracking_index)

    for hit in hits:
        processed_count += 1
        doc_id = hit.get('_id', '')
        source = hit.get('_source', {})
        index_name = source.get('index_name', '')
        restore_date = source.get('restore_date', '')

        if not index_name:
            logger.warning('Record %s has no index_name, skipping.', doc_id)
            continue

        # Check if the index still exists in the cluster
        try:
            index_exists = retry_with_backoff(
                lambda idx=index_name: es_client.es.indices.exists(index=idx),
                max_retries=3,
                delay=1,
            )
        except Exception as exc:
            logger.error(
                'Failed to check existence of index %s: %s', index_name, exc
            )
            error_count += 1
            continue

        if not index_exists:
            # Stale record - index no longer exists, remove tracking record
            logger.info(
                'Index %s no longer exists. Removing stale record %s.',
                index_name, doc_id,
            )
            if not dry_run:
                try:
                    retry_with_backoff(
                        lambda did=doc_id: es_client.es.delete(
                            index=tracking_index, id=did
                        ),
                        max_retries=3,
                        delay=1,
                    )
                except Exception as exc:
                    logger.error(
                        'Failed to remove stale record %s: %s', doc_id, exc
                    )
                    error_count += 1
            deleted_count += 1
            continue

        # Index exists - check age
        age_days = calculate_days_since_restore(restore_date)
        if age_days is None:
            logger.error(
                'Could not parse restore_date for index %s (value: %s). Skipping.',
                index_name, restore_date,
            )
            error_count += 1
            continue

        logger.info(
            'Index %s: age %d days (max: %d days).', index_name, age_days, max_days
        )

        if age_days >= max_days:
            # Expired - delete the index and remove the tracking record
            logger.info(
                'Index %s has expired (%d >= %d days). Deleting.',
                index_name, age_days, max_days,
            )
            if not dry_run:
                # Delete the index
                try:
                    success = retry_with_backoff(
                        lambda idx=index_name: es_client.delete_index(idx),
                        max_retries=3,
                        delay=1,
                    )
                    if success:
                        logger.info('Deleted index %s.', index_name)
                    else:
                        logger.error('Failed to delete index %s.', index_name)
                        error_count += 1
                        continue
                except Exception as exc:
                    logger.error(
                        'Failed to delete index %s: %s', index_name, exc
                    )
                    error_count += 1
                    continue

                # Remove the tracking record
                try:
                    retry_with_backoff(
                        lambda did=doc_id: es_client.es.delete(
                            index=tracking_index, id=did
                        ),
                        max_retries=3,
                        delay=1,
                    )
                except Exception as exc:
                    logger.error(
                        'Failed to remove record %s after deleting index: %s',
                        doc_id, exc,
                    )
                    error_count += 1
            deleted_count += 1
        else:
            logger.info(
                'Index %s is within retention (%d < %d days). Skipping.',
                index_name, age_days, max_days,
            )

    return (processed_count, deleted_count, error_count)


def main():
    # type: () -> None
    """Entry point for the restored index manager utility.

    Parses command-line arguments, loads configuration, connects to
    Elasticsearch, and processes restored indices for cleanup.

    CLI arguments:
        --server      Server name to select from configuration.
        --max-days    Override the configured maximum age in days.
        --dry-run     Log actions without performing deletions.
        --debug       Enable verbose DEBUG logging.
        --config-file Path to the configuration YAML file.
    """
    parser = argparse.ArgumentParser(
        description='Clean up aged restored Elasticsearch indices.'
    )
    parser.add_argument(
        '--server', '-server',
        type=str,
        default='DEFAULT',
        help='Server name to select from configuration.',
    )
    parser.add_argument(
        '--max-days', '-max-days',
        type=int,
        default=None,
        help='Override the configured maximum age in days.',
    )
    parser.add_argument(
        '--dry-run', '-dry-run',
        action='store_true',
        default=False,
        help='Report actions without performing deletions.',
    )
    parser.add_argument(
        '--debug', '-debug',
        action='store_true',
        default=False,
        help='Enable verbose debug logging.',
    )
    parser.add_argument(
        '--config-file', '-config-file',
        type=str,
        default=None,
        help='Path to the configuration YAML file.',
    )
    args = parser.parse_args()

    # Set up logging
    logger = setup_logger('restored-index-manager', debug=args.debug)
    logger.info('Restored-index-manager v%s starting...', __version__)

    # Load configuration
    try:
        if args.config_file:
            config_file = args.config_file
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = find_config_file(
                'elastic_servers.yml', [script_dir, '.']
            )
        config = load_server_config(config_file, server_name=args.server)
    except (FileNotFoundError, ValueError) as exc:
        logger.error('Configuration error: %s', exc)
        sys.exit(1)

    logger.info('Config file: %s', config_file)

    # Determine max days
    max_days = config.get('elastic_restored_maxdays', 3)
    if args.max_days is not None:
        max_days = args.max_days
    logger.info('Max days for restored indices: %d', max_days)

    # Determine tracking index name
    tracking_index = config.get('elastic_restored_indice', 'rc_snapshots')
    logger.info('Tracking index: %s', tracking_index)

    if args.dry_run:
        logger.info('--dry-run specified; no deletions will be performed.')

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
        record_health(_METRICS_FILE, 'restored_index_manager', False)
        sys.exit(1)

    # Ensure tracking index exists (create if missing)
    if not ensure_tracking_index(es, tracking_index, logger):
        record_health(_METRICS_FILE, 'restored_index_manager', False)
        es.close()
        sys.exit(1)

    # Process restored indices
    processed, deleted, errors = process_restored_indices(
        es, tracking_index, max_days, logger, dry_run=args.dry_run
    )

    logger.info(
        'Processing complete. Processed: %d, Deleted: %d, Errors: %d',
        processed, deleted, errors,
    )

    # Record health
    success = errors == 0
    record_health(_METRICS_FILE, 'restored_index_manager', success)
    logger.info('Restored-index-manager script ending.')

    es.close()


if __name__ == '__main__':
    main()
