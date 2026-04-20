"""
es_client.py - Shared Elasticsearch client wrapper.

Provides connection management with retry logic, authentication support,
warning suppression, and all common Elasticsearch operations used across
the server utilities.
"""

import json
import re
import time
import warnings

import urllib3
from collections import defaultdict
from elasticsearch import Elasticsearch, ElasticsearchWarning
from elasticsearch.exceptions import (
    ConnectionError as ESConnectionError,
    NotFoundError,
    AuthenticationException,
)
from requests.auth import HTTPBasicAuth

try:
    import requests
except ImportError:
    requests = None

# Suppress Elasticsearch UserWarning (deprecation notices)
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")
# Suppress DeprecationWarning from Elasticsearch library
warnings.filterwarnings("ignore", category=DeprecationWarning, module="elasticsearch")
# Suppress ElasticsearchWarning (security-not-enabled notices)
warnings.filterwarnings("ignore", category=ElasticsearchWarning)
# Suppress urllib3 InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def retry_with_backoff(func, max_retries, delay):
    # type: (callable, int, float) -> object
    """
    Retry a callable with exponential backoff.

    Calls func() up to max_retries + 1 times total. Sleeps delay * 2^attempt
    between retries (attempt starts at 0 for the first retry).

    Args:
        func: Callable to invoke (no arguments).
        max_retries: Number of retry attempts after the initial call.
        delay: Base delay in seconds; actual sleep is delay * 2^attempt.

    Returns:
        The return value of func() on success.

    Raises:
        The last exception raised by func() after all attempts are exhausted.
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as exc:
            last_exception = exc
            if attempt < max_retries:
                time.sleep(delay * (2 ** attempt))
    raise last_exception


class ESClient(object):
    """Elasticsearch client wrapper with connection retry, auth, and common operations."""

    def __init__(self, hostname, port, use_ssl=False, username=None,
                 password=None, timeout=300, max_retries=3, retry_delay=5):
        # type: (str, int, bool, str, str, int, int, int) -> None
        """
        Connect to Elasticsearch with retry logic.

        Args:
            hostname: Elasticsearch host address.
            port: Elasticsearch port.
            use_ssl: Whether to use SSL/TLS.
            username: Optional username for authentication.
            password: Optional password for authentication.
            timeout: Request timeout in seconds.
            max_retries: Maximum connection retry attempts.
            retry_delay: Seconds to wait between retries.
        """
        self.hostname = hostname
        self.port = int(port)
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.timeout = int(timeout)
        self.max_retries = int(max_retries)
        self.retry_delay = int(retry_delay)
        self.es = None  # type: Elasticsearch

        # Determine if authentication is needed
        self.authentication = (
            self.username is not None and self.password is not None
        )

        # Connect with retry
        self._connect()

    def _build_es_url(self):
        # type: () -> str
        """Build the base Elasticsearch URL."""
        protocol = "https" if self.use_ssl else "http"
        return "%s://%s:%d" % (protocol, self.hostname, self.port)

    def _connect(self):
        # type: () -> None
        """
        Establish connection to Elasticsearch with retry logic.

        Retries up to max_retries times with retry_delay between attempts.
        Raises ConnectionError after all attempts are exhausted.
        """
        for attempt in range(self.max_retries):
            try:
                kwargs = {
                    'hosts': [self.hostname],
                    'port': self.port,
                    'use_ssl': self.use_ssl,
                    'verify_certs': False,
                    'timeout': self.timeout,
                }
                if self.authentication:
                    kwargs['http_auth'] = (self.username, self.password)

                self.es = Elasticsearch(**kwargs)

                if self.es.ping():
                    return
            except (ESConnectionError, AuthenticationException):
                pass
            except Exception:
                pass

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)

        raise ConnectionError(
            "Could not connect to Elasticsearch after %d attempts." % self.max_retries
        )

    def ping(self):
        # type: () -> bool
        """Ping the Elasticsearch cluster and return True if reachable."""
        try:
            return self.es.ping()
        except Exception:
            return False

    def get_all_snapshots(self):
        # type: () -> list
        """
        Retrieve all snapshot IDs in the cluster.

        Returns:
            List of snapshot ID strings.
        """
        snapshots = []
        try:
            cat_snapshots = self.es.cat.snapshots(format="json")
            for snapshot_info in cat_snapshots:
                snapshots.append(snapshot_info['id'])
        except Exception:
            pass
        return snapshots

    def get_snapshots_brief(self, repository):
        # type: (str) -> list
        """Retrieve snapshot names quickly without per-shard validation.

        Uses the ``_snapshot`` API with ``verbose=false`` which skips
        the expensive per-shard integrity check that ``_cat/snapshots``
        performs.  Returns only snapshot name and UUID — no status,
        duration, or shard counts.

        Args:
            repository: S3 repository name.

        Returns:
            List of dicts with ``snapshot`` and ``uuid`` keys.
            Returns an empty list on error.
        """
        try:
            resp = self.es.snapshot.get(
                repository=repository,
                snapshot='_all',
                verbose=False,
            )
            return resp.get('snapshots', [])
        except Exception:
            return []

    def get_snapshot_details(self, repository, snapshot_names, logger=None):
        # type: (str, list, object) -> dict
        """Retrieve full metadata for specific snapshots by name.

        Uses the ``_snapshot`` API with ``verbose=true`` (default) but
        only for the requested snapshots, avoiding the cost of
        validating every snapshot in the repository.  Requests are
        batched to avoid exceeding URL length limits.

        Args:
            repository: S3 repository name.
            snapshot_names: List of snapshot name strings to query.
            logger: Optional logger for error reporting.

        Returns:
            Dict of ``{snapshot_name: {state, ...}}`` for each
            requested snapshot.  Missing or errored snapshots are
            silently omitted.
        """
        if not snapshot_names:
            return {}

        result = {}
        # Batch into groups to stay well under URL length limits.
        batch_size = 10
        for i in range(0, len(snapshot_names), batch_size):
            batch = snapshot_names[i:i + batch_size]
            joined = ','.join(batch)
            try:
                resp = self.es.snapshot.get(
                    repository=repository,
                    snapshot=joined,
                    ignore_unavailable=True,
                )
                for snap in resp.get('snapshots', []):
                    name = snap.get('snapshot', '')
                    shards_info = snap.get('shards', {})
                    result[name] = {
                        'state': snap.get('state', ''),
                        'failed_shards': shards_info.get('failed', 0),
                        'start_epoch': str(snap.get('start_time_in_millis', 0) // 1000) if snap.get('start_time_in_millis') else '',
                        'end_epoch': str(snap.get('end_time_in_millis', 0) // 1000) if snap.get('end_time_in_millis') else '',
                        'duration_in_millis': snap.get('duration_in_millis', 0),
                    }
            except Exception as exc:
                if logger:
                    logger.warning(
                        'Failed to get snapshot details for batch %d-%d: %s',
                        i, i + len(batch), exc,
                    )
        return result

    def get_snapshots_with_metadata(self, location=None):
        # type: (str) -> dict
        """
        Retrieve all snapshots with their metadata.

        Args:
            location: Repository name used as the top-level key.

        Returns:
            dict of {location: {snapshot_id: {status, total_shards,
            failed_shards, duration, start_epoch, end_epoch, ...}}}.
            If location is None, returns a flat dict keyed by snapshot_id.
        """
        try:
            if not self.es.ping():
                if location is not None:
                    return {location: {}}
                return {}
        except Exception:
            if location is not None:
                return {location: {}}
            return {}

        cat_snapshots = self.es.cat.snapshots(format="json")

        if location is not None:
            result = defaultdict(dict)
            for index in cat_snapshots:
                snapshot_id = index['id']
                result[location][snapshot_id] = {
                    'location': location,
                    'port': self.port,
                    'status': index.get('status', ''),
                    'total_shards': index.get('total_shards', '0'),
                    'failed_shards': index.get('failed_shards', '0'),
                    'duration': index.get('duration', ''),
                    'start_epoch': index.get('start_epoch', ''),
                    'end_epoch': index.get('end_epoch', ''),
                }
            return dict(result)
        else:
            result = {}
            for index in cat_snapshots:
                snapshot_id = index['id']
                result[snapshot_id] = {
                    'status': index.get('status', ''),
                    'total_shards': index.get('total_shards', '0'),
                    'failed_shards': index.get('failed_shards', '0'),
                    'duration': index.get('duration', ''),
                    'start_epoch': index.get('start_epoch', ''),
                    'end_epoch': index.get('end_epoch', ''),
                }
            return result

    def create_snapshot(self, index_name, snapshot_name, repository):
        # type: (str, str, str) -> tuple
        """
        Create an S3 snapshot of an Elasticsearch index.

        Args:
            index_name: Name of the index to snapshot.
            snapshot_name: Name for the snapshot.
            repository: S3 repository name.

        Returns:
            Tuple of (success_bool, response_dict_or_error_message).
        """
        try:
            snapshot_body = {
                "indices": index_name,
                "ignore_unavailable": True,
                "include_global_state": False,
            }
            response = self.es.snapshot.create(
                repository=repository,
                snapshot=snapshot_name,
                body=snapshot_body,
            )
            return (True, response)
        except Exception as e:
            return (False, "Exception has occurred: %s" % str(e))

    def delete_snapshot(self, snapshot_name, repository):
        # type: (str, str) -> tuple
        """
        Delete a snapshot from the repository.

        Args:
            snapshot_name: Name of the snapshot to delete.
            repository: S3 repository name.

        Returns:
            Tuple of (success_bool, response_dict_or_error_message).
        """
        try:
            response = self.es.snapshot.delete(
                repository=repository,
                snapshot=snapshot_name,
            )
            return (True, response)
        except Exception as e:
            return (False, "Exception has occurred: %s" % str(e))

    def delete_index(self, index_name):
        # type: (str) -> bool
        """
        Delete an index from Elasticsearch.

        Args:
            index_name: Name of the index to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        try:
            if self.es.indices.exists(index=index_name):
                response = self.es.indices.delete(index=index_name)
                return response.get('acknowledged', False)
            return False
        except Exception:
            return False

    def get_index_ilms(self, short=False):
        # type: (bool) -> dict
        """
        Retrieve ILM status for all indices.

        Args:
            short: If True, return simplified dict with phase, age, policy
                   per index. If False, return full ILM explain response.

        Returns:
            dict of ILM data.
        """
        es_url = self._build_es_url()

        try:
            if self.authentication:
                response = requests.get(
                    '%s/_all/_ilm/explain' % es_url,
                    auth=HTTPBasicAuth(self.username, self.password),
                    verify=False,
                )
            else:
                response = requests.get(
                    '%s/_all/_ilm/explain' % es_url,
                    verify=False,
                )

            response.raise_for_status()
            indices_data = json.loads(response.text)

            if short:
                return self._get_index_ilm_short(indices_data)
            return indices_data
        except Exception:
            return {}

    def _get_index_ilm_short(self, data):
        # type: (dict) -> dict
        """
        Extract short ILM summary from full ILM explain data.

        Args:
            data: Full ILM explain response dict.

        Returns:
            dict of {index_name: {phase, age, policy}}.
        """
        result = {}
        indices_data = data.get("indices", {})

        for index_name, metadata in indices_data.items():
            phase = metadata.get('phase', None)
            age = metadata.get('age', 0)
            policy = metadata.get('policy', None)
            result[index_name] = {
                'phase': phase,
                'age': age,
                'policy': policy,
            }

        return result

    def get_cluster_health(self):
        # type: () -> tuple
        """
        Get Elasticsearch cluster health status.

        Returns:
            Tuple of (status_str, rich_formatted_str).
            status_str is one of 'green', 'yellow', 'red'.
        """
        try:
            cluster_health = self.es.cluster.health()
            cluster_status = cluster_health['status']

            color_map = {
                'green': '[green]%s[/green]',
                'yellow': '[yellow]%s[/yellow]',
                'red': '[red]%s[/red]',
            }
            fmt = color_map.get(cluster_status, '%s')
            return (cluster_status, fmt % cluster_status)
        except Exception:
            return ('unknown', '[red]unknown[/red]')

    def get_shards_per_node(self):
        # type: () -> dict
        """
        Get active shard count per node.

        Returns:
            dict of {node_name: shard_count}.
        """
        try:
            shards_info = self.es.cat.shards(format='json', h=['node', 'shard'])
            active_shards = {}
            for shard_info in shards_info:
                node_id = shard_info.get('node', '')
                if node_id not in active_shards:
                    active_shards[node_id] = 1
                else:
                    active_shards[node_id] += 1
            return active_shards
        except Exception:
            return {}

    def search_scroll(self, index_name, query, scroll_timeout='2m', batch_size=100):
        # type: (str, dict, str, int) -> list
        """
        Scroll through all documents matching a query.

        Uses the Elasticsearch scroll API to iterate through all matching
        documents in batches.

        Args:
            index_name: Index to search.
            query: Elasticsearch query body dict.
            scroll_timeout: How long to keep the scroll context alive.
            batch_size: Number of documents per scroll batch.

        Returns:
            List of all hit dicts (each containing _id, _source, etc.).
        """
        all_hits = []
        try:
            response = self.es.search(
                index=index_name,
                body=query,
                scroll=scroll_timeout,
                size=batch_size,
            )

            scroll_id = response.get('_scroll_id')
            hits = response.get('hits', {}).get('hits', [])
            all_hits.extend(hits)

            while hits:
                response = self.es.scroll(
                    scroll_id=scroll_id,
                    scroll=scroll_timeout,
                )
                scroll_id = response.get('_scroll_id')
                hits = response.get('hits', {}).get('hits', [])
                all_hits.extend(hits)

            # Clean up scroll context
            if scroll_id:
                try:
                    self.es.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    pass

        except NotFoundError:
            # Index doesn't exist
            pass
        except Exception:
            pass

        return all_hits

    def close(self):
        # type: () -> None
        """Close the Elasticsearch client connection."""
        if self.es:
            try:
                self.es.transport.close()
            except Exception:
                pass
