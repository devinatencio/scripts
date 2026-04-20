"""Unit tests for server.ilm_curator."""

import time

import pytest

from server.ilm_curator import (
    get_cold_indices,
    hours_since_epoch,
    process_indices_for_deletion,
)


class TestGetColdIndices(object):
    """Tests for get_cold_indices()."""

    def test_returns_cold_indices(self):
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
            'index-b': {'phase': 'hot', 'age': '1d', 'policy': 'default'},
            'index-c': {'phase': 'cold', 'age': '60d', 'policy': 'default'},
        }
        result = get_cold_indices(ilm_data)
        assert sorted(result) == ['index-a', 'index-c']

    def test_empty_ilm_data(self):
        assert get_cold_indices({}) == []

    def test_no_cold_indices(self):
        ilm_data = {
            'index-a': {'phase': 'hot', 'age': '1d', 'policy': 'default'},
            'index-b': {'phase': 'warm', 'age': '10d', 'policy': 'default'},
        }
        assert get_cold_indices(ilm_data) == []

    def test_missing_phase_key(self):
        ilm_data = {
            'index-a': {'age': '30d', 'policy': 'default'},
        }
        assert get_cold_indices(ilm_data) == []


class TestHoursSinceEpoch(object):
    """Tests for hours_since_epoch()."""

    def test_recent_epoch(self):
        # 1 hour ago
        one_hour_ago = int(time.time()) - 3600
        result = hours_since_epoch(one_hour_ago)
        assert 0.9 < result < 1.1

    def test_string_epoch(self):
        one_hour_ago = str(int(time.time()) - 3600)
        result = hours_since_epoch(one_hour_ago)
        assert 0.9 < result < 1.1

    def test_24_hours_ago(self):
        day_ago = int(time.time()) - 86400
        result = hours_since_epoch(day_ago)
        assert 23.9 < result < 24.1

    def test_returns_float(self):
        result = hours_since_epoch(int(time.time()) - 5400)  # 1.5 hours
        assert isinstance(result, float)


class _FakeESClient(object):
    """Minimal fake ES client for testing process_indices_for_deletion."""

    def __init__(self):
        self.deleted = []

    def delete_index(self, index_name):
        self.deleted.append(index_name)
        return True


class _FailingESClient(object):
    """Fake ES client where delete_index always fails."""

    def __init__(self):
        self.deleted = []

    def delete_index(self, index_name):
        return False


class TestProcessIndicesForDeletion(object):
    """Tests for process_indices_for_deletion()."""

    def _old_epoch(self, hours=12):
        """Return an epoch string *hours* in the past."""
        return str(int(time.time()) - int(hours * 3600))

    def _recent_epoch(self, hours=1):
        """Return an epoch string *hours* in the past."""
        return str(int(time.time()) - int(hours * 3600))

    def test_deletes_qualifying_index(self):
        es = _FakeESClient()
        snapshots = {
            'snapshot_index-a': {
                'status': 'SUCCESS',
                'failed_shards': '0',
                'end_epoch': self._old_epoch(12),
            },
        }
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, snapshots, ilm_data, hours_delay=6)
        assert deleted == 1
        assert skipped == 0
        assert es.deleted == ['index-a']

    def test_skips_non_success_status(self):
        es = _FakeESClient()
        snapshots = {
            'snapshot_index-a': {
                'status': 'FAILED',
                'failed_shards': '0',
                'end_epoch': self._old_epoch(12),
            },
        }
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, snapshots, ilm_data, hours_delay=6)
        assert deleted == 0
        assert skipped == 1
        assert es.deleted == []

    def test_skips_nonzero_failed_shards(self):
        es = _FakeESClient()
        snapshots = {
            'snapshot_index-a': {
                'status': 'SUCCESS',
                'failed_shards': '2',
                'end_epoch': self._old_epoch(12),
            },
        }
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, snapshots, ilm_data, hours_delay=6)
        assert deleted == 0
        assert skipped == 1

    def test_skips_too_young_snapshot(self):
        es = _FakeESClient()
        snapshots = {
            'snapshot_index-a': {
                'status': 'SUCCESS',
                'failed_shards': '0',
                'end_epoch': self._recent_epoch(1),
            },
        }
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, snapshots, ilm_data, hours_delay=6)
        assert deleted == 0
        assert skipped == 1

    def test_skips_non_cold_index(self):
        es = _FakeESClient()
        snapshots = {
            'snapshot_index-a': {
                'status': 'SUCCESS',
                'failed_shards': '0',
                'end_epoch': self._old_epoch(12),
            },
        }
        ilm_data = {
            'index-a': {'phase': 'hot', 'age': '1d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, snapshots, ilm_data, hours_delay=6)
        assert deleted == 0
        assert skipped == 0

    def test_skips_snapshot_without_prefix(self):
        es = _FakeESClient()
        snapshots = {
            'index-a': {
                'status': 'SUCCESS',
                'failed_shards': '0',
                'end_epoch': self._old_epoch(12),
            },
        }
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, snapshots, ilm_data, hours_delay=6)
        assert deleted == 0
        assert skipped == 0

    def test_failed_shards_as_int_zero(self):
        es = _FakeESClient()
        snapshots = {
            'snapshot_index-a': {
                'status': 'SUCCESS',
                'failed_shards': 0,
                'end_epoch': self._old_epoch(12),
            },
        }
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, snapshots, ilm_data, hours_delay=6)
        assert deleted == 1

    def test_delete_failure_counts_as_skipped(self):
        es = _FailingESClient()
        snapshots = {
            'snapshot_index-a': {
                'status': 'SUCCESS',
                'failed_shards': '0',
                'end_epoch': self._old_epoch(12),
            },
        }
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, snapshots, ilm_data, hours_delay=6)
        assert deleted == 0
        assert skipped == 1

    def test_empty_snapshots(self):
        es = _FakeESClient()
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, {}, ilm_data, hours_delay=6)
        assert deleted == 0
        assert skipped == 0

    def test_multiple_indices(self):
        es = _FakeESClient()
        snapshots = {
            'snapshot_index-a': {
                'status': 'SUCCESS',
                'failed_shards': '0',
                'end_epoch': self._old_epoch(12),
            },
            'snapshot_index-b': {
                'status': 'FAILED',
                'failed_shards': '0',
                'end_epoch': self._old_epoch(12),
            },
            'snapshot_index-c': {
                'status': 'SUCCESS',
                'failed_shards': '0',
                'end_epoch': self._old_epoch(12),
            },
        }
        ilm_data = {
            'index-a': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
            'index-b': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
            'index-c': {'phase': 'cold', 'age': '30d', 'policy': 'default'},
        }
        deleted, skipped = process_indices_for_deletion(es, snapshots, ilm_data, hours_delay=6)
        assert deleted == 2
        assert skipped == 1
        assert sorted(es.deleted) == ['index-a', 'index-c']
