"""Unit tests for metrics_collector module."""

import datetime
import json
import os
import shutil
import tempfile

import pytest

from server.metrics_collector import (
    get_default_metrics,
    increment_counter,
    read_metrics,
    record_health,
    record_snapshot_statuses,
    write_metrics,
)


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test metrics files."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def metrics_file(tmp_dir):
    """Return a path to a metrics file inside the temp directory."""
    return os.path.join(tmp_dir, 'metrics', 'snapshot_metrics.json')


class TestGetDefaultMetrics(object):
    def test_has_required_sections(self):
        m = get_default_metrics()
        assert 'daily_counters' in m
        assert 'utility_health' in m
        assert 'snapshot_statuses' in m

    def test_daily_counters_zero(self):
        m = get_default_metrics()
        c = m['daily_counters']
        assert c['snapshots_created'] == 0
        assert c['snapshots_deleted'] == 0
        assert c['indices_deleted_ilm'] == 0

    def test_daily_counters_date_is_today(self):
        m = get_default_metrics()
        today = datetime.date.today().strftime('%Y-%m-%d')
        assert m['daily_counters']['date'] == today

    def test_utility_health_empty(self):
        assert get_default_metrics()['utility_health'] == {}

    def test_snapshot_statuses_all_zero(self):
        statuses = get_default_metrics()['snapshot_statuses']
        for key in ('SUCCESS', 'FAILED', 'PARTIAL', 'IN_PROGRESS', 'INCOMPATIBLE'):
            assert statuses[key] == 0


class TestReadMetrics(object):
    def test_missing_file_returns_default(self, tmp_dir):
        path = os.path.join(tmp_dir, 'nonexistent.json')
        m = read_metrics(path)
        assert m['daily_counters']['snapshots_created'] == 0

    def test_corrupt_file_returns_default(self, tmp_dir):
        path = os.path.join(tmp_dir, 'bad.json')
        with open(path, 'w') as f:
            f.write('not json at all {{{')
        m = read_metrics(path)
        assert 'daily_counters' in m

    def test_non_dict_json_returns_default(self, tmp_dir):
        path = os.path.join(tmp_dir, 'list.json')
        with open(path, 'w') as f:
            json.dump([1, 2, 3], f)
        m = read_metrics(path)
        assert isinstance(m, dict)
        assert 'daily_counters' in m

    def test_valid_file_returns_contents(self, tmp_dir):
        path = os.path.join(tmp_dir, 'ok.json')
        data = {'daily_counters': {'date': '2025-01-01', 'snapshots_created': 5,
                                   'snapshots_deleted': 0, 'indices_deleted_ilm': 0},
                'utility_health': {},
                'snapshot_statuses': {}}
        write_metrics(path, data)
        m = read_metrics(path)
        assert m['daily_counters']['snapshots_created'] == 5


class TestWriteMetrics(object):
    def test_creates_parent_directory(self, metrics_file):
        data = get_default_metrics()
        write_metrics(metrics_file, data)
        # The database file is a .db sibling of the .json path
        db_path = metrics_file.replace('.json', '.db')
        assert os.path.isfile(db_path)

    def test_round_trip(self, metrics_file):
        data = get_default_metrics()
        data['daily_counters']['snapshots_created'] = 42
        write_metrics(metrics_file, data)
        loaded = read_metrics(metrics_file)
        assert loaded == data

    def test_overwrites_existing(self, metrics_file):
        data1 = get_default_metrics()
        data1['daily_counters']['snapshots_created'] = 10
        write_metrics(metrics_file, data1)

        data2 = get_default_metrics()
        data2['daily_counters']['snapshots_created'] = 99
        write_metrics(metrics_file, data2)

        loaded = read_metrics(metrics_file)
        assert loaded['daily_counters']['snapshots_created'] == 99

    def test_no_temp_file_left_on_success(self, metrics_file):
        write_metrics(metrics_file, get_default_metrics())
        parent = os.path.dirname(metrics_file)
        tmp_files = [f for f in os.listdir(parent) if f.endswith('.tmp')]
        assert tmp_files == []


class TestIncrementCounter(object):
    def test_creates_file_if_missing(self, metrics_file):
        increment_counter(metrics_file, 'snapshots_created')
        m = read_metrics(metrics_file)
        assert m['daily_counters']['snapshots_created'] == 1

    def test_increments_existing(self, metrics_file):
        increment_counter(metrics_file, 'snapshots_deleted', 3)
        increment_counter(metrics_file, 'snapshots_deleted', 2)
        m = read_metrics(metrics_file)
        assert m['daily_counters']['snapshots_deleted'] == 5

    def test_custom_amount(self, metrics_file):
        increment_counter(metrics_file, 'indices_deleted_ilm', 10)
        m = read_metrics(metrics_file)
        assert m['daily_counters']['indices_deleted_ilm'] == 10

    def test_preserves_other_counters(self, metrics_file):
        increment_counter(metrics_file, 'snapshots_created', 1)
        increment_counter(metrics_file, 'snapshots_deleted', 2)
        m = read_metrics(metrics_file)
        assert m['daily_counters']['snapshots_created'] == 1
        assert m['daily_counters']['snapshots_deleted'] == 2


class TestRecordHealth(object):
    def test_records_success(self, metrics_file):
        record_health(metrics_file, 'cold_snapshots', True, '2025-01-15T02:00:00')
        m = read_metrics(metrics_file)
        entry = m['utility_health']['cold_snapshots']
        assert entry['success'] is True
        assert entry['last_run'] == '2025-01-15T02:00:00'

    def test_records_failure(self, metrics_file):
        record_health(metrics_file, 'retention_enforcer', False, '2025-01-15T03:00:00')
        m = read_metrics(metrics_file)
        assert m['utility_health']['retention_enforcer']['success'] is False

    def test_default_timestamp(self, metrics_file):
        record_health(metrics_file, 'ilm_curator', True)
        m = read_metrics(metrics_file)
        ts = m['utility_health']['ilm_curator']['last_run']
        # Should be a valid ISO-ish timestamp
        assert 'T' in ts

    def test_multiple_utilities(self, metrics_file):
        record_health(metrics_file, 'a', True, '2025-01-01T00:00:00')
        record_health(metrics_file, 'b', False, '2025-01-01T01:00:00')
        m = read_metrics(metrics_file)
        assert 'a' in m['utility_health']
        assert 'b' in m['utility_health']

    def test_overwrites_previous_entry(self, metrics_file):
        record_health(metrics_file, 'x', True, '2025-01-01T00:00:00')
        record_health(metrics_file, 'x', False, '2025-01-02T00:00:00')
        m = read_metrics(metrics_file)
        assert m['utility_health']['x']['success'] is False
        assert m['utility_health']['x']['last_run'] == '2025-01-02T00:00:00'

    def test_archives_previous_day_on_date_rollover(self, metrics_file):
        """record_health archives yesterday's counters into daily_history."""
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        data = get_default_metrics()
        data['daily_counters'] = {
            'date': yesterday,
            'snapshots_created': 12,
            'snapshots_deleted': 4,
            'indices_deleted_ilm': 2,
        }
        write_metrics(metrics_file, data)

        # record_health should trigger the rollover
        record_health(metrics_file, 'cold_snapshots', True)
        m = read_metrics(metrics_file)

        # Yesterday's counters should be archived
        assert 'daily_history' in m
        assert len(m['daily_history']) == 1
        entry = m['daily_history'][0]
        assert entry['date'] == yesterday
        assert entry['snapshots_created'] == 12
        assert entry['snapshots_deleted'] == 4

        # Today's counters should be reset
        today = datetime.date.today().strftime('%Y-%m-%d')
        assert m['daily_counters']['date'] == today
        assert m['daily_counters']['snapshots_created'] == 0

    def test_no_archive_when_date_is_current(self, metrics_file):
        """record_health does not archive when date is already today."""
        today = datetime.date.today().strftime('%Y-%m-%d')
        data = get_default_metrics()
        data['daily_counters'] = {
            'date': today,
            'snapshots_created': 5,
            'snapshots_deleted': 0,
            'indices_deleted_ilm': 0,
        }
        write_metrics(metrics_file, data)

        record_health(metrics_file, 'test_util', True)
        m = read_metrics(metrics_file)

        # No history should be created
        history = m.get('daily_history', [])
        assert len(history) == 0
        # Counters should be untouched
        assert m['daily_counters']['snapshots_created'] == 5


class TestRecordSnapshotStatuses(object):
    def test_records_statuses(self, metrics_file):
        counts = {'SUCCESS': 100, 'FAILED': 2, 'PARTIAL': 0,
                  'IN_PROGRESS': 1, 'INCOMPATIBLE': 0}
        record_snapshot_statuses(metrics_file, counts)
        m = read_metrics(metrics_file)
        assert m['snapshot_statuses'] == counts

    def test_overwrites_previous(self, metrics_file):
        record_snapshot_statuses(metrics_file, {'SUCCESS': 10})
        record_snapshot_statuses(metrics_file, {'SUCCESS': 20, 'FAILED': 1})
        m = read_metrics(metrics_file)
        assert m['snapshot_statuses'] == {'SUCCESS': 20, 'FAILED': 1}

    def test_preserves_other_sections(self, metrics_file):
        increment_counter(metrics_file, 'snapshots_created', 5)
        record_snapshot_statuses(metrics_file, {'SUCCESS': 99})
        m = read_metrics(metrics_file)
        assert m['daily_counters']['snapshots_created'] == 5
        assert m['snapshot_statuses'] == {'SUCCESS': 99}


class TestArchiveAndPruneHistory(object):
    """Tests for daily_history archival during date rollover."""

    def test_date_rollover_archives_previous_day(self, metrics_file, monkeypatch):
        """When the date changes, the old day's counters are saved to daily_history."""
        # Seed with yesterday's counters
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        data = get_default_metrics()
        data['daily_counters'] = {
            'date': yesterday,
            'snapshots_created': 7,
            'snapshots_deleted': 3,
            'indices_deleted_ilm': 1,
        }
        write_metrics(metrics_file, data)

        # Incrementing today triggers the rollover
        increment_counter(metrics_file, 'snapshots_created', 1)
        m = read_metrics(metrics_file)

        assert 'daily_history' in m
        assert len(m['daily_history']) == 1
        entry = m['daily_history'][0]
        assert entry['date'] == yesterday
        assert entry['snapshots_created'] == 7
        assert entry['snapshots_deleted'] == 3
        assert entry['indices_deleted_ilm'] == 1

        # Today's counter should be fresh
        assert m['daily_counters']['snapshots_created'] == 1

    def test_no_duplicate_archive_entries(self, metrics_file):
        """Archiving the same date twice does not create duplicates."""
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        data = get_default_metrics()
        data['daily_counters'] = {
            'date': yesterday,
            'snapshots_created': 5,
            'snapshots_deleted': 0,
            'indices_deleted_ilm': 0,
        }
        data['daily_history'] = [{
            'date': yesterday,
            'snapshots_created': 5,
            'snapshots_deleted': 0,
            'indices_deleted_ilm': 0,
        }]
        write_metrics(metrics_file, data)

        increment_counter(metrics_file, 'snapshots_created', 1)
        m = read_metrics(metrics_file)
        dates = [e['date'] for e in m['daily_history']]
        assert dates.count(yesterday) == 1

    def test_history_pruned_to_90_days(self, metrics_file):
        """History is capped at 90 entries after archival."""
        base = datetime.date.today() - datetime.timedelta(days=100)
        history = []
        for i in range(95):
            d = (base + datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': i,
                'snapshots_deleted': 0,
                'indices_deleted_ilm': 0,
            })

        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        data = get_default_metrics()
        data['daily_history'] = history
        data['daily_counters'] = {
            'date': yesterday,
            'snapshots_created': 99,
            'snapshots_deleted': 0,
            'indices_deleted_ilm': 0,
        }
        write_metrics(metrics_file, data)

        increment_counter(metrics_file, 'snapshots_created', 1)
        m = read_metrics(metrics_file)
        assert len(m['daily_history']) <= 90

    def test_same_day_no_archive(self, metrics_file):
        """Incrementing on the same day does not create history entries."""
        increment_counter(metrics_file, 'snapshots_created', 1)
        increment_counter(metrics_file, 'snapshots_created', 2)
        m = read_metrics(metrics_file)
        history = m.get('daily_history', [])
        assert len(history) == 0
        assert m['daily_counters']['snapshots_created'] == 3

    def test_empty_date_not_archived(self, metrics_file):
        """Counters with no date field are not archived."""
        data = get_default_metrics()
        data['daily_counters'] = {
            'snapshots_created': 5,
            'snapshots_deleted': 0,
            'indices_deleted_ilm': 0,
        }
        write_metrics(metrics_file, data)

        increment_counter(metrics_file, 'snapshots_created', 1)
        m = read_metrics(metrics_file)
        history = m.get('daily_history', [])
        assert len(history) == 0
