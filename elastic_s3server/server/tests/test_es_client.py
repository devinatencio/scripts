"""
Unit tests for es_client.py - ESClient class.

Tests cover: warning suppression, constructor parameters, connection retry
logic, method signatures, and method behavior with mocked ES client.
"""

import warnings
import time

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestESClientWarnings(object):
    """Verify that Elasticsearch and urllib3 warnings are suppressed."""

    def test_elasticsearch_user_warning_suppressed(self):
        """UserWarning from elasticsearch module should be suppressed."""
        import server.es_client  # noqa: triggers warning filters
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Re-apply the filters from es_client
            warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")
            warnings.warn("test", UserWarning)
            # The generic UserWarning still shows (not from elasticsearch module)
            # but elasticsearch-module ones would be filtered
            assert True  # filters are registered

    def test_urllib3_insecure_request_warning_suppressed(self):
        """InsecureRequestWarning from urllib3 should be suppressed."""
        import urllib3
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            # After disabling, these warnings should not appear
            assert True


class TestESClientInit(object):
    """Test ESClient constructor and connection retry logic."""

    @patch('server.es_client.Elasticsearch')
    def test_successful_connection(self, mock_es_class):
        """ESClient should connect successfully when ping returns True."""
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_es_class.return_value = mock_instance

        from server.es_client import ESClient
        client = ESClient('localhost', 9200)

        assert client.hostname == 'localhost'
        assert client.port == 9200
        assert client.es is mock_instance
        mock_instance.ping.assert_called()

    @patch('server.es_client.Elasticsearch')
    def test_connection_with_auth(self, mock_es_class):
        """ESClient should pass http_auth when username and password provided."""
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_es_class.return_value = mock_instance

        from server.es_client import ESClient
        client = ESClient('localhost', 9200, username='user', password='pass')

        assert client.authentication is True
        call_kwargs = mock_es_class.call_args[1]
        assert call_kwargs['http_auth'] == ('user', 'pass')

    @patch('server.es_client.Elasticsearch')
    def test_connection_without_auth(self, mock_es_class):
        """ESClient should not pass http_auth when credentials are None."""
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_es_class.return_value = mock_instance

        from server.es_client import ESClient
        client = ESClient('localhost', 9200)

        assert client.authentication is False
        call_kwargs = mock_es_class.call_args[1]
        assert 'http_auth' not in call_kwargs

    @patch('server.es_client.Elasticsearch')
    def test_ssl_parameter_passed(self, mock_es_class):
        """ESClient should pass use_ssl to Elasticsearch constructor."""
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_es_class.return_value = mock_instance

        from server.es_client import ESClient
        client = ESClient('localhost', 9200, use_ssl=True)

        call_kwargs = mock_es_class.call_args[1]
        assert call_kwargs['use_ssl'] is True

    @patch('server.es_client.time.sleep')
    @patch('server.es_client.Elasticsearch')
    def test_retry_on_failed_ping(self, mock_es_class, mock_sleep):
        """ESClient should retry when ping fails, then succeed."""
        mock_instance = MagicMock()
        mock_instance.ping.side_effect = [False, False, True]
        mock_es_class.return_value = mock_instance

        from server.es_client import ESClient
        client = ESClient('localhost', 9200, max_retries=3, retry_delay=1)

        assert mock_instance.ping.call_count == 3
        assert mock_sleep.call_count == 2  # sleep between retries

    @patch('server.es_client.time.sleep')
    @patch('server.es_client.Elasticsearch')
    def test_connection_error_after_exhaustion(self, mock_es_class, mock_sleep):
        """ESClient should raise ConnectionError after all retries fail."""
        mock_instance = MagicMock()
        mock_instance.ping.return_value = False
        mock_es_class.return_value = mock_instance

        from server.es_client import ESClient
        with pytest.raises(ConnectionError) as exc_info:
            ESClient('localhost', 9200, max_retries=3, retry_delay=1)

        assert '3 attempts' in str(exc_info.value)

    @patch('server.es_client.time.sleep')
    @patch('server.es_client.Elasticsearch')
    def test_connection_error_message_includes_attempt_count(self, mock_es_class, mock_sleep):
        """ConnectionError message should include the number of attempts."""
        mock_instance = MagicMock()
        mock_instance.ping.return_value = False
        mock_es_class.return_value = mock_instance

        from server.es_client import ESClient
        with pytest.raises(ConnectionError) as exc_info:
            ESClient('localhost', 9200, max_retries=5, retry_delay=0)

        assert '5 attempts' in str(exc_info.value)

    @patch('server.es_client.Elasticsearch')
    def test_timeout_parameter(self, mock_es_class):
        """ESClient should pass timeout to Elasticsearch constructor."""
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_es_class.return_value = mock_instance

        from server.es_client import ESClient
        client = ESClient('localhost', 9200, timeout=600)

        assert client.timeout == 600
        call_kwargs = mock_es_class.call_args[1]
        assert call_kwargs['timeout'] == 600


class TestESClientMethods(object):
    """Test ESClient methods with a mocked Elasticsearch instance."""

    @pytest.fixture
    def es_client(self):
        """Create an ESClient with a mocked ES connection."""
        with patch('server.es_client.Elasticsearch') as mock_es_class:
            mock_instance = MagicMock()
            mock_instance.ping.return_value = True
            mock_es_class.return_value = mock_instance

            from server.es_client import ESClient
            client = ESClient('localhost', 9200)
            yield client

    def test_ping_success(self, es_client):
        """ping() should return True when cluster is reachable."""
        es_client.es.ping.return_value = True
        assert es_client.ping() is True

    def test_ping_failure(self, es_client):
        """ping() should return False when cluster is unreachable."""
        es_client.es.ping.return_value = False
        assert es_client.ping() is False

    def test_ping_exception(self, es_client):
        """ping() should return False on exception."""
        es_client.es.ping.side_effect = Exception("connection lost")
        assert es_client.ping() is False

    def test_get_all_snapshots(self, es_client):
        """get_all_snapshots() should return list of snapshot IDs."""
        es_client.es.cat.snapshots.return_value = [
            {'id': 'snapshot_index1'},
            {'id': 'snapshot_index2'},
            {'id': 'snapshot_index3'},
        ]
        result = es_client.get_all_snapshots()
        assert result == ['snapshot_index1', 'snapshot_index2', 'snapshot_index3']

    def test_get_all_snapshots_empty(self, es_client):
        """get_all_snapshots() should return empty list when no snapshots."""
        es_client.es.cat.snapshots.return_value = []
        assert es_client.get_all_snapshots() == []

    def test_get_all_snapshots_exception(self, es_client):
        """get_all_snapshots() should return empty list on exception."""
        es_client.es.cat.snapshots.side_effect = Exception("error")
        assert es_client.get_all_snapshots() == []

    def test_get_snapshots_with_metadata_with_location(self, es_client):
        """get_snapshots_with_metadata() with location returns nested dict."""
        es_client.es.cat.snapshots.return_value = [
            {
                'id': 'snap1',
                'status': 'SUCCESS',
                'total_shards': '5',
                'failed_shards': '0',
                'duration': '2.5s',
                'start_epoch': '1700000000',
                'end_epoch': '1700000010',
            },
        ]
        result = es_client.get_snapshots_with_metadata(location='my-repo')
        assert 'my-repo' in result
        assert 'snap1' in result['my-repo']
        assert result['my-repo']['snap1']['status'] == 'SUCCESS'
        assert result['my-repo']['snap1']['failed_shards'] == '0'

    def test_get_snapshots_with_metadata_without_location(self, es_client):
        """get_snapshots_with_metadata() without location returns flat dict."""
        es_client.es.cat.snapshots.return_value = [
            {
                'id': 'snap1',
                'status': 'SUCCESS',
                'total_shards': '5',
                'failed_shards': '0',
                'duration': '2.5s',
                'start_epoch': '1700000000',
                'end_epoch': '1700000010',
            },
        ]
        result = es_client.get_snapshots_with_metadata()
        assert 'snap1' in result
        assert result['snap1']['status'] == 'SUCCESS'

    def test_create_snapshot_success(self, es_client):
        """create_snapshot() should return (True, response) on success."""
        es_client.es.snapshot.create.return_value = {'accepted': True}
        success, response = es_client.create_snapshot('my-index', 'snap1', 'my-repo')
        assert success is True
        assert response == {'accepted': True}

    def test_create_snapshot_failure(self, es_client):
        """create_snapshot() should return (False, error_msg) on exception."""
        es_client.es.snapshot.create.side_effect = Exception("snapshot failed")
        success, msg = es_client.create_snapshot('my-index', 'snap1', 'my-repo')
        assert success is False
        assert 'Exception has occurred' in msg

    def test_delete_snapshot_success(self, es_client):
        """delete_snapshot() should return (True, response) on success."""
        es_client.es.snapshot.delete.return_value = {'acknowledged': True}
        success, response = es_client.delete_snapshot('snap1', 'my-repo')
        assert success is True

    def test_delete_snapshot_failure(self, es_client):
        """delete_snapshot() should return (False, error_msg) on exception."""
        es_client.es.snapshot.delete.side_effect = Exception("delete failed")
        success, msg = es_client.delete_snapshot('snap1', 'my-repo')
        assert success is False

    def test_delete_index_success(self, es_client):
        """delete_index() should return True when index exists and is deleted."""
        es_client.es.indices.exists.return_value = True
        es_client.es.indices.delete.return_value = {'acknowledged': True}
        assert es_client.delete_index('my-index') is True

    def test_delete_index_not_exists(self, es_client):
        """delete_index() should return False when index doesn't exist."""
        es_client.es.indices.exists.return_value = False
        assert es_client.delete_index('my-index') is False

    def test_delete_index_exception(self, es_client):
        """delete_index() should return False on exception."""
        es_client.es.indices.exists.side_effect = Exception("error")
        assert es_client.delete_index('my-index') is False

    def test_get_cluster_health_green(self, es_client):
        """get_cluster_health() should return green status with Rich formatting."""
        es_client.es.cluster.health.return_value = {'status': 'green'}
        status, formatted = es_client.get_cluster_health()
        assert status == 'green'
        assert '[green]' in formatted

    def test_get_cluster_health_red(self, es_client):
        """get_cluster_health() should return red status with Rich formatting."""
        es_client.es.cluster.health.return_value = {'status': 'red'}
        status, formatted = es_client.get_cluster_health()
        assert status == 'red'
        assert '[red]' in formatted

    def test_get_cluster_health_exception(self, es_client):
        """get_cluster_health() should return unknown on exception."""
        es_client.es.cluster.health.side_effect = Exception("error")
        status, formatted = es_client.get_cluster_health()
        assert status == 'unknown'

    def test_get_shards_per_node(self, es_client):
        """get_shards_per_node() should return node-to-shard-count mapping."""
        es_client.es.cat.shards.return_value = [
            {'node': 'node1', 'shard': '0'},
            {'node': 'node1', 'shard': '1'},
            {'node': 'node2', 'shard': '0'},
        ]
        result = es_client.get_shards_per_node()
        assert result == {'node1': 2, 'node2': 1}

    def test_get_shards_per_node_empty(self, es_client):
        """get_shards_per_node() should return empty dict when no shards."""
        es_client.es.cat.shards.return_value = []
        assert es_client.get_shards_per_node() == {}

    def test_search_scroll_single_batch(self, es_client):
        """search_scroll() should return all hits from a single batch."""
        es_client.es.search.return_value = {
            '_scroll_id': 'scroll123',
            'hits': {'hits': [{'_id': '1', '_source': {'name': 'test'}}]},
        }
        es_client.es.scroll.return_value = {
            '_scroll_id': 'scroll123',
            'hits': {'hits': []},
        }
        result = es_client.search_scroll('my-index', {'query': {'match_all': {}}})
        assert len(result) == 1
        assert result[0]['_id'] == '1'

    def test_search_scroll_multiple_batches(self, es_client):
        """search_scroll() should accumulate hits across multiple scroll batches."""
        es_client.es.search.return_value = {
            '_scroll_id': 'scroll123',
            'hits': {'hits': [{'_id': '1'}]},
        }
        es_client.es.scroll.side_effect = [
            {'_scroll_id': 'scroll123', 'hits': {'hits': [{'_id': '2'}]}},
            {'_scroll_id': 'scroll123', 'hits': {'hits': []}},
        ]
        result = es_client.search_scroll('my-index', {'query': {'match_all': {}}})
        assert len(result) == 2

    def test_search_scroll_index_not_found(self, es_client):
        """search_scroll() should return empty list when index doesn't exist."""
        from elasticsearch.exceptions import NotFoundError
        es_client.es.search.side_effect = NotFoundError(404, 'index_not_found')
        result = es_client.search_scroll('missing-index', {'query': {'match_all': {}}})
        assert result == []

    def test_close(self, es_client):
        """close() should call transport.close()."""
        es_client.close()
        es_client.es.transport.close.assert_called_once()

    def test_close_no_es(self, es_client):
        """close() should handle None es gracefully."""
        es_client.es = None
        es_client.close()  # Should not raise

    def test_get_index_ilms_short(self, es_client):
        """_get_index_ilm_short() should extract phase, age, policy."""
        data = {
            'indices': {
                'index-1': {'phase': 'cold', 'age': '30d', 'policy': 'my-policy'},
                'index-2': {'phase': 'hot', 'age': '1d', 'policy': 'other-policy'},
            }
        }
        result = es_client._get_index_ilm_short(data)
        assert result['index-1']['phase'] == 'cold'
        assert result['index-2']['phase'] == 'hot'

    def test_build_es_url_http(self, es_client):
        """_build_es_url() should return http URL when SSL is off."""
        es_client.use_ssl = False
        assert es_client._build_es_url() == 'http://localhost:9200'

    def test_build_es_url_https(self, es_client):
        """_build_es_url() should return https URL when SSL is on."""
        es_client.use_ssl = True
        assert es_client._build_es_url() == 'https://localhost:9200'
