"""
snapshot_stats.py - Collect snapshot status distribution for the dashboard.

Lightweight utility that queries the full snapshot list via
``_cat/snapshots``, tallies the status distribution (SUCCESS, FAILED,
PARTIAL, IN_PROGRESS, INCOMPATIBLE), and writes it to the metrics
database.  Designed to run on its own schedule so that heavier
utilities like cold_snapshots and ilm_curator stay fast.

Usage:
    python -m server.snapshot_stats              # standard run
    python -m server.snapshot_stats --debug      # verbose logging
"""

import argparse
import os
import sys

from server.config_loader import find_config_file, load_server_config
from server.es_client import ESClient
from server.log_manager import setup_logger
from server.metrics_collector import record_health, record_snapshot_statuses, record_total_snapshots

# Version
from server import __version__

# Metrics path reference — metrics_collector derives the .db path from this
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_METRICS_FILE = os.path.join(_MODULE_DIR, 'metrics', 'snapshot_metrics.json')


def main():
    # type: () -> None
    """Entry point for the snapshot stats collector.

    Connects to Elasticsearch, retrieves the full snapshot list via
    ``_cat/snapshots``, tallies status counts, and writes them to the
    metrics database for the dashboard.

    CLI arguments:
        --debug      Enable verbose DEBUG logging.
        --repository Override the configured S3 repository name.
    """
    parser = argparse.ArgumentParser(
        description='Collect snapshot status distribution for the metrics dashboard.',
    )
    parser.add_argument(
        '--debug', '-debug',
        action='store_true',
        default=False,
        help='Enable verbose debug logging.',
    )
    parser.add_argument(
        '--repository', '-repository', '-repos',
        type=str,
        default=None,
        help='Override the configured S3 repository.',
    )
    args = parser.parse_args()

    # Set up logging
    logger = setup_logger('snapshot-stats', debug=args.debug)
    logger.info('Snapshot-stats v%s starting...', __version__)

    # Load configuration
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = find_config_file('elastic_servers.yml', [script_dir, '.'])
        config = load_server_config(config_file)
    except (FileNotFoundError, ValueError) as exc:
        logger.error('Configuration error: %s', exc)
        sys.exit(1)

    logger.info('Config file: %s', config_file)

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
        record_health(_METRICS_FILE, 'snapshot_stats', False)
        sys.exit(1)

    # Retrieve full snapshot list via _cat/snapshots
    try:
        cat_snapshots = es.es.cat.snapshots(format='json')
    except Exception as exc:
        logger.error('Failed to retrieve snapshots: %s', exc)
        record_health(_METRICS_FILE, 'snapshot_stats', False)
        es.close()
        sys.exit(1)

    logger.info('STATS: Snapshots: [ %d ] found.', len(cat_snapshots))

    # Tally status distribution
    status_counts = {}
    for snap in cat_snapshots:
        status = str(snap.get('status', 'UNKNOWN')).upper()
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in sorted(status_counts.items()):
        logger.info('  %-15s %d', status, count)

    # Write to metrics database
    try:
        record_snapshot_statuses(_METRICS_FILE, status_counts)
        record_total_snapshots(_METRICS_FILE, len(cat_snapshots))
        logger.info('Snapshot status distribution and total count recorded to metrics.')
    except Exception as exc:
        logger.error('Failed to record snapshot statuses: %s', exc)
        record_health(_METRICS_FILE, 'snapshot_stats', False)
        es.close()
        sys.exit(1)

    record_health(_METRICS_FILE, 'snapshot_stats', True)
    logger.info('Snapshot-stats script ending.')

    es.close()


if __name__ == '__main__':
    main()
