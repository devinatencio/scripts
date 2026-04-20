"""Unit tests for restored_index_manager module."""

import datetime
import logging

import pytest

from server.restored_index_manager import (
    calculate_days_since_restore,
    process_restored_indices,
)


class TestCalculateDaysSinceRestore(object):
    """Tests for calculate_days_since_restore."""

    def test_recent_iso_date(self):
        """A date from a few seconds ago should be 0 days old."""
        now = datetime.datetime.now(datetime.timezone.utc)
        iso_str = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        assert calculate_days_since_restore(iso_str) == 0

    def test_one_day_old(self):
        """A date from 1 day ago should return 1."""
        yesterday = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1, hours=1)
        iso_str = yesterday.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        assert calculate_days_since_restore(iso_str) == 1

    def test_thirty_days_old(self):
        """A date from 30 days ago should return 30."""
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30, hours=1)
        iso_str = past.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        assert calculate_days_since_restore(iso_str) == 30

    def test_with_milliseconds(self):
        """ISO date with milliseconds is parsed correctly."""
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5, hours=1)
        iso_str = past.strftime('%Y-%m-%dT%H:%M:%S') + '.123Z'
        assert calculate_days_since_restore(iso_str) == 5

    def test_without_z_suffix(self):
        """ISO date without Z suffix is treated as UTC."""
        past = datetime.datetime.utcnow() - datetime.timedelta(days=3, hours=1)
        iso_str = past.strftime('%Y-%m-%dT%H:%M:%S')
        assert calculate_days_since_restore(iso_str) == 3

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert calculate_days_since_restore('') is None

    def test_none_returns_none(self):
        """None input returns None."""
        assert calculate_days_since_restore(None) is None

    def test_invalid_format_returns_none(self):
        """Invalid date format returns None."""
        assert calculate_days_since_restore('not-a-date') is None

    def test_partial_date_returns_none(self):
        """Partial date string returns None."""
        assert calculate_days_since_restore('2025-01-12') is None

    def test_exact_format_from_spec(self):
        """The exact format from the spec doc is parsed correctly."""
        # Use a date far enough in the past to get a stable result
        result = calculate_days_since_restore('2020-01-01T00:00:00.000Z')
        assert result is not None
        assert result > 0

    def test_returns_non_negative(self):
        """Result is always non-negative even for future dates."""
        future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)
        iso_str = future.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        result = calculate_days_since_restore(iso_str)
        assert result is not None
        assert result >= 0


class FakeIndices(object):
    """Fake Elasticsearch indices namespace for testing."""

    def __init__(self, existing_indices=None):
        self._existing = set(existing_indices or [])
        self.deleted = []

    def exists(self, index):
        return index in self._existing

    def delete(self, index):
        if index in self._existing:
            self._existing.discard(index)
            self.deleted.append(index)
            return {'acknowledged': True}
        return {'acknowledged': False}


class FakeES(object):
    """Fake low-level Elasticsearch client for testing."""

    def __init__(self, existing_indices=None):
        self.indices = FakeIndices(existing_indices)
        self.deleted_docs = []

    def delete(self, index, id):
        self.deleted_docs.append({'index': index, 'id': id})
        return {'result': 'deleted'}


class FakeESClient(object):
    """Fake ESClient wrapper for testing process_restored_indices."""

    def __init__(self, existing_indices=None, scroll_hits=None):
        self.es = FakeES(existing_indices)
        self._scroll_hits = scroll_hits or []
        self._deleted_indices = []

    def search_scroll(self, index_name, query, scroll_timeout='2m', batch_size=100):
        return self._scroll_hits

    def delete_index(self, index_name):
        if self.es.indices.exists(index_name):
            self.es.indices.delete(index_name)
            self._deleted_indices.append(index_name)
            return True
        return False


class TestProcessRestoredIndices(object):
    """Tests for process_restored_indices."""

    def _make_logger(self):
        logger = logging.getLogger('test-restored-index-manager')
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        return logger

    def _make_hit(self, doc_id, index_name, restore_date, status='restored'):
        return {
            '_id': doc_id,
            '_source': {
                'index_name': index_name,
                'restore_date': restore_date,
                'status': status,
            },
        }

    def test_empty_tracking_index(self):
        """No records returns (0, 0, 0)."""
        es = FakeESClient(existing_indices=[])
        logger = self._make_logger()
        result = process_restored_indices(es, 'rc_snapshots', 3, logger)
        assert result == (0, 0, 0)

    def test_stale_record_removed(self):
        """Record for non-existing index is counted as deleted."""
        hits = [self._make_hit('doc1', 'old-index', '2020-01-01T00:00:00.000Z')]
        es = FakeESClient(existing_indices=[], scroll_hits=hits)
        logger = self._make_logger()
        processed, deleted, errors = process_restored_indices(
            es, 'rc_snapshots', 3, logger
        )
        assert processed == 1
        assert deleted == 1
        assert errors == 0
        # Verify the tracking record was deleted
        assert len(es.es.deleted_docs) == 1
        assert es.es.deleted_docs[0]['id'] == 'doc1'

    def test_expired_index_deleted(self):
        """Index older than max_days is deleted along with its record."""
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)
        iso_str = past.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        hits = [self._make_hit('doc1', 'restored-index', iso_str)]
        es = FakeESClient(
            existing_indices=['restored-index'],
            scroll_hits=hits,
        )
        logger = self._make_logger()
        processed, deleted, errors = process_restored_indices(
            es, 'rc_snapshots', 3, logger
        )
        assert processed == 1
        assert deleted == 1
        assert errors == 0
        assert 'restored-index' in es._deleted_indices

    def test_young_index_skipped(self):
        """Index within max_days is not deleted."""
        now = datetime.datetime.now(datetime.timezone.utc)
        iso_str = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        hits = [self._make_hit('doc1', 'fresh-index', iso_str)]
        es = FakeESClient(
            existing_indices=['fresh-index'],
            scroll_hits=hits,
        )
        logger = self._make_logger()
        processed, deleted, errors = process_restored_indices(
            es, 'rc_snapshots', 3, logger
        )
        assert processed == 1
        assert deleted == 0
        assert errors == 0
        assert len(es._deleted_indices) == 0

    def test_invalid_restore_date_counted_as_error(self):
        """Record with unparseable restore_date increments error count."""
        hits = [self._make_hit('doc1', 'some-index', 'not-a-date')]
        es = FakeESClient(
            existing_indices=['some-index'],
            scroll_hits=hits,
        )
        logger = self._make_logger()
        processed, deleted, errors = process_restored_indices(
            es, 'rc_snapshots', 3, logger
        )
        assert processed == 1
        assert deleted == 0
        assert errors == 1

    def test_dry_run_no_deletions(self):
        """Dry run mode does not delete anything."""
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)
        iso_str = past.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        hits = [self._make_hit('doc1', 'expired-index', iso_str)]
        es = FakeESClient(
            existing_indices=['expired-index'],
            scroll_hits=hits,
        )
        logger = self._make_logger()
        processed, deleted, errors = process_restored_indices(
            es, 'rc_snapshots', 3, logger, dry_run=True
        )
        assert processed == 1
        assert deleted == 1  # counted as would-be-deleted
        assert errors == 0
        # But no actual deletions
        assert len(es._deleted_indices) == 0
        assert len(es.es.deleted_docs) == 0

    def test_dry_run_stale_no_deletions(self):
        """Dry run mode does not remove stale records."""
        hits = [self._make_hit('doc1', 'gone-index', '2020-01-01T00:00:00.000Z')]
        es = FakeESClient(existing_indices=[], scroll_hits=hits)
        logger = self._make_logger()
        processed, deleted, errors = process_restored_indices(
            es, 'rc_snapshots', 3, logger, dry_run=True
        )
        assert processed == 1
        assert deleted == 1
        assert errors == 0
        assert len(es.es.deleted_docs) == 0

    def test_mixed_records(self):
        """Mix of stale, expired, and young records processed correctly."""
        now = datetime.datetime.now(datetime.timezone.utc)
        old_date = (now - datetime.timedelta(days=10)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        fresh_date = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        hits = [
            self._make_hit('doc1', 'stale-index', old_date),       # stale (not in cluster)
            self._make_hit('doc2', 'expired-index', old_date),     # expired
            self._make_hit('doc3', 'fresh-index', fresh_date),     # young
        ]
        es = FakeESClient(
            existing_indices=['expired-index', 'fresh-index'],
            scroll_hits=hits,
        )
        logger = self._make_logger()
        processed, deleted, errors = process_restored_indices(
            es, 'rc_snapshots', 3, logger
        )
        assert processed == 3
        assert deleted == 2  # stale + expired
        assert errors == 0

    def test_record_without_index_name_skipped(self):
        """Record with empty index_name is skipped."""
        hits = [{'_id': 'doc1', '_source': {'index_name': '', 'restore_date': '2020-01-01T00:00:00.000Z'}}]
        es = FakeESClient(existing_indices=[], scroll_hits=hits)
        logger = self._make_logger()
        processed, deleted, errors = process_restored_indices(
            es, 'rc_snapshots', 3, logger
        )
        assert processed == 1
        assert deleted == 0
        assert errors == 0
