"""Unit tests for retention_enforcer module."""

import time

import pytest

from server.retention_enforcer import (
    calculate_snapshot_age_days,
    get_retention_days,
    process_snapshots_for_deletion,
)


class TestCalculateSnapshotAgeDays(object):
    """Tests for calculate_snapshot_age_days."""

    def test_recent_epoch(self):
        """An epoch from a few seconds ago should be 0 days old."""
        now_str = str(int(time.time()) - 10)
        assert calculate_snapshot_age_days(now_str) == 0

    def test_one_day_old(self):
        """An epoch from exactly 1 day ago should return 1."""
        one_day_ago = str(int(time.time()) - 86400)
        assert calculate_snapshot_age_days(one_day_ago) == 1

    def test_thirty_days_old(self):
        """An epoch from 30 days ago should return 30."""
        thirty_days_ago = str(int(time.time()) - 30 * 86400)
        assert calculate_snapshot_age_days(thirty_days_ago) == 30

    def test_floor_division(self):
        """Partial days are floored (1.5 days -> 1)."""
        partial = str(int(time.time()) - int(1.5 * 86400))
        assert calculate_snapshot_age_days(partial) == 1

    def test_string_input(self):
        """Epoch passed as string is handled correctly."""
        epoch_str = str(int(time.time()) - 5 * 86400)
        assert calculate_snapshot_age_days(epoch_str) == 5

    def test_invalid_string_raises(self):
        """Non-numeric string raises ValueError."""
        with pytest.raises(ValueError):
            calculate_snapshot_age_days('not-a-number')


class TestGetRetentionDays(object):
    """Tests for get_retention_days."""

    def test_no_policies_returns_default(self):
        """With empty policies, default_days is returned."""
        result = get_retention_days('snapshot_foo', {}, 30)
        assert result == 30

    def test_matching_policy(self):
        """A matching regex pattern returns its max_days."""
        policies = {'.*logs-gan-.*': 90, '.*logs-gas-.*': 90}
        result = get_retention_days('snapshot_.ds-logs-gan-2024.01.01', policies, 30)
        assert result == 90

    def test_no_match_returns_default(self):
        """When no pattern matches, default_days is returned."""
        policies = {'.*logs-gan-.*': 90}
        result = get_retention_days('snapshot_.ds-metrics-2024.01.01', policies, 30)
        assert result == 30

    def test_prefix_stripping(self):
        """The snapshot_ prefix is stripped before matching."""
        policies = {'^foo-.*': 60}
        result = get_retention_days('snapshot_foo-bar', policies, 30)
        assert result == 60

    def test_no_prefix(self):
        """Snapshot name without snapshot_ prefix still works."""
        policies = {'^foo-.*': 60}
        result = get_retention_days('foo-bar', policies, 30)
        assert result == 60

    def test_first_match_wins(self):
        """The first matching pattern's max_days is returned."""
        # Python 3.7+ dicts are ordered; use an OrderedDict for 3.6 safety
        from collections import OrderedDict
        policies = OrderedDict([('.*logs.*', 90), ('.*', 10)])
        result = get_retention_days('snapshot_logs-foo', policies, 30)
        assert result == 90


class TestProcessSnapshotsForDeletion(object):
    """Tests for process_snapshots_for_deletion."""

    def test_empty_snapshots(self):
        """Empty snapshot dict returns empty result."""
        result = process_snapshots_for_deletion({}, {}, 30)
        assert result == {}

    def test_all_within_retention(self):
        """Snapshots within retention are not included."""
        now = int(time.time())
        snapshots = {
            'snapshot_idx-a': {'start_epoch': str(now - 10 * 86400)},
        }
        result = process_snapshots_for_deletion(snapshots, {}, 30)
        assert result == {}

    def test_exceeds_retention(self):
        """Snapshots exceeding retention are included."""
        now = int(time.time())
        snapshots = {
            'snapshot_idx-a': {'start_epoch': str(now - 40 * 86400)},
        }
        result = process_snapshots_for_deletion(snapshots, {}, 30)
        assert 'snapshot_idx-a' in result
        assert result['snapshot_idx-a'] == 40

    def test_regex_filter(self):
        """Only snapshots matching regex_pattern are considered."""
        now = int(time.time())
        snapshots = {
            'snapshot_logs-a': {'start_epoch': str(now - 40 * 86400)},
            'snapshot_metrics-a': {'start_epoch': str(now - 40 * 86400)},
        }
        result = process_snapshots_for_deletion(
            snapshots, {}, 30, regex_pattern='snapshot_logs-.*'
        )
        assert 'snapshot_logs-a' in result
        assert 'snapshot_metrics-a' not in result

    def test_missing_start_epoch_skipped(self):
        """Snapshots without start_epoch are skipped."""
        snapshots = {
            'snapshot_idx-a': {'status': 'SUCCESS'},
        }
        result = process_snapshots_for_deletion(snapshots, {}, 30)
        assert result == {}

    def test_empty_start_epoch_skipped(self):
        """Snapshots with empty start_epoch string are skipped."""
        snapshots = {
            'snapshot_idx-a': {'start_epoch': ''},
        }
        result = process_snapshots_for_deletion(snapshots, {}, 30)
        assert result == {}

    def test_retention_policy_applied(self):
        """Per-pattern retention policy overrides default."""
        now = int(time.time())
        snapshots = {
            'snapshot_.ds-logs-gan-2024.01.01': {
                'start_epoch': str(now - 50 * 86400),
            },
        }
        policies = {'.*logs-gan-.*': 90}
        # 50 days old, 90 day retention -> should NOT be deleted
        result = process_snapshots_for_deletion(snapshots, policies, 30)
        assert result == {}

    def test_retention_policy_exceeded(self):
        """Snapshot exceeding per-pattern retention is included."""
        now = int(time.time())
        snapshots = {
            'snapshot_.ds-logs-gan-2024.01.01': {
                'start_epoch': str(now - 100 * 86400),
            },
        }
        policies = {'.*logs-gan-.*': 90}
        # 100 days old, 90 day retention -> should be deleted
        result = process_snapshots_for_deletion(snapshots, policies, 30)
        assert 'snapshot_.ds-logs-gan-2024.01.01' in result

    def test_boundary_not_deleted(self):
        """Snapshot exactly at retention boundary is NOT deleted (age must exceed)."""
        now = int(time.time())
        snapshots = {
            'snapshot_idx-a': {'start_epoch': str(now - 30 * 86400)},
        }
        result = process_snapshots_for_deletion(snapshots, {}, 30)
        assert result == {}
