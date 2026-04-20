"""Unit tests for cold_snapshots module."""

import logging

import pytest

from server.cold_snapshots import (
    get_cold_indices_needing_backup,
    backup_cold_indices,
)


class TestGetColdIndicesNeedingBackup(object):
    """Tests for get_cold_indices_needing_backup."""

    def test_empty_cold_indices(self):
        """No cold indices returns empty list."""
        result = get_cold_indices_needing_backup([], ['snapshot_foo'], '.*')
        assert result == []

    def test_all_already_backed_up(self):
        """All cold indices have matching snapshots."""
        cold = ['idx-a', 'idx-b']
        snaps = ['snapshot_idx-a', 'snapshot_idx-b']
        result = get_cold_indices_needing_backup(cold, snaps)
        assert result == []

    def test_none_backed_up(self):
        """No matching snapshots exist."""
        cold = ['idx-a', 'idx-b']
        snaps = ['snapshot_other']
        result = get_cold_indices_needing_backup(cold, snaps)
        assert result == ['idx-a', 'idx-b']

    def test_partial_backup(self):
        """Some indices backed up, some not."""
        cold = ['idx-a', 'idx-b', 'idx-c']
        snaps = ['snapshot_idx-b']
        result = get_cold_indices_needing_backup(cold, snaps)
        assert result == ['idx-a', 'idx-c']

    def test_regex_filter(self):
        """Regex pattern filters which indices are considered."""
        cold = ['logs-2024', 'metrics-2024', 'logs-2025']
        snaps = []
        result = get_cold_indices_needing_backup(cold, snaps, regex_pattern='logs-.*')
        assert result == ['logs-2024', 'logs-2025']

    def test_regex_default_matches_all(self):
        """Default regex '.*' matches everything."""
        cold = ['a', 'b', 'c']
        snaps = []
        result = get_cold_indices_needing_backup(cold, snaps)
        assert result == ['a', 'b', 'c']

    def test_empty_snapshots(self):
        """Empty snapshot list means all cold indices need backup."""
        cold = ['idx-1', 'idx-2']
        result = get_cold_indices_needing_backup(cold, [])
        assert result == ['idx-1', 'idx-2']

    def test_snapshot_naming_convention(self):
        """Only exact snapshot_{name} match counts as backed up."""
        cold = ['my-index']
        # A snapshot with a different naming convention should not match
        snaps = ['my-index', 'snap_my-index', 'snapshot_my-index-extra']
        result = get_cold_indices_needing_backup(cold, snaps)
        assert result == ['my-index']

    def test_snapshot_exact_match(self):
        """Exact snapshot_{name} match is recognized."""
        cold = ['my-index']
        snaps = ['snapshot_my-index']
        result = get_cold_indices_needing_backup(cold, snaps)
        assert result == []


class TestBackupColdIndices(object):
    """Tests for backup_cold_indices."""

    def test_all_succeed(self):
        """All snapshots created successfully."""
        class MockES(object):
            def create_snapshot(self, index_name, snapshot_name, repository):
                return (True, {'accepted': True})

        logger = logging.getLogger('test-backup')
        success, failure = backup_cold_indices(
            MockES(), ['idx-a', 'idx-b'], 'my-repo', logger
        )
        assert success == 2
        assert failure == 0

    def test_all_fail(self):
        """All snapshot creations fail."""
        class MockES(object):
            def create_snapshot(self, index_name, snapshot_name, repository):
                return (False, 'Connection error')

        logger = logging.getLogger('test-backup')
        success, failure = backup_cold_indices(
            MockES(), ['idx-a', 'idx-b'], 'my-repo', logger
        )
        assert success == 0
        assert failure == 2

    def test_mixed_results(self):
        """Some succeed, some fail."""
        class MockES(object):
            def __init__(self):
                self.call_count = 0

            def create_snapshot(self, index_name, snapshot_name, repository):
                self.call_count += 1
                if self.call_count % 2 == 0:
                    return (False, 'error')
                return (True, {'accepted': True})

        logger = logging.getLogger('test-backup')
        success, failure = backup_cold_indices(
            MockES(), ['a', 'b', 'c'], 'repo', logger
        )
        assert success == 2
        assert failure == 1

    def test_empty_indices(self):
        """No indices to backup returns zero counts."""
        class MockES(object):
            def create_snapshot(self, index_name, snapshot_name, repository):
                raise AssertionError('Should not be called')

        logger = logging.getLogger('test-backup')
        success, failure = backup_cold_indices(MockES(), [], 'repo', logger)
        assert success == 0
        assert failure == 0

    def test_snapshot_naming(self):
        """Snapshot name follows snapshot_{index_name} convention."""
        created_names = []

        class MockES(object):
            def create_snapshot(self, index_name, snapshot_name, repository):
                created_names.append(snapshot_name)
                return (True, {})

        logger = logging.getLogger('test-backup')
        backup_cold_indices(MockES(), ['my-idx'], 'repo', logger)
        assert created_names == ['snapshot_my-idx']
