"""Tests for snapshot_cli.py."""

import argparse
import sys

import pytest

from server.snapshot_cli import (
    display_snapshots_table,
    display_restored_table,
    display_history_table,
    _build_parser,
    _cmd_list,
    _cmd_ping,
    COMMANDS,
    console,
)


class FakeESClient(object):
    """Minimal fake ES client for CLI tests."""

    def __init__(self, snapshots=None, snapshots_brief=None, scroll_hits=None,
                 ping_ok=True, health=('green', '[green]green[/green]')):
        self._snapshots = snapshots or []
        self._snapshots_brief = snapshots_brief or []
        self._scroll_hits = scroll_hits or []
        self._ping_ok = ping_ok
        self._health = health
        self.es = self  # allow es.es.cat.snapshots

    # cat.snapshots chain
    @property
    def cat(self):
        return self

    def snapshots(self, format='json'):
        return list(self._snapshots)

    # fast snapshot listing
    def get_snapshots_brief(self, repository):
        return list(self._snapshots_brief)

    def ping(self):
        return self._ping_ok

    def get_cluster_health(self):
        return self._health

    def search_scroll(self, index_name, query, scroll_timeout='2m', batch_size=100):
        return list(self._scroll_hits)

    def close(self):
        pass


# ---------------------------------------------------------------------------
# display_snapshots_table
# ---------------------------------------------------------------------------

class TestDisplaySnapshotsTable(object):

    def test_empty_list(self, capsys):
        """No snapshots prints a warning message."""
        display_snapshots_table([])
        captured = capsys.readouterr()
        assert 'No snapshots found' in captured.out

    def test_renders_rows(self, capsys):
        """Snapshots are rendered in a table with expected columns."""
        data = [
            {'id': 'snap_a', 'status': 'SUCCESS', 'end_time': '2025-01-01',
             'duration': '5s', 'total_shards': '10'},
            {'id': 'snap_b', 'status': 'FAILED', 'end_time': '2025-01-02',
             'duration': '3s', 'total_shards': '5'},
        ]
        display_snapshots_table(data)
        captured = capsys.readouterr()
        assert 'snap_a' in captured.out
        assert 'snap_b' in captured.out
        assert 'SUCCESS' in captured.out
        assert 'FAILED' in captured.out

    def test_partial_status(self, capsys):
        """PARTIAL status is rendered."""
        data = [{'id': 'snap_p', 'status': 'PARTIAL', 'end_time': '',
                 'duration': '', 'total_shards': ''}]
        display_snapshots_table(data)
        captured = capsys.readouterr()
        assert 'PARTIAL' in captured.out


# ---------------------------------------------------------------------------
# display_restored_table
# ---------------------------------------------------------------------------

class TestDisplayRestoredTable(object):

    def test_empty_results(self, capsys):
        """No records prints a warning."""
        es = FakeESClient(scroll_hits=[])
        display_restored_table(es, 'rc_snapshots')
        captured = capsys.readouterr()
        assert 'No restored index records found' in captured.out

    def test_renders_records(self, capsys):
        """Records are rendered in a table."""
        hits = [
            {'_source': {'index_name': 'idx-1', 'restore_date': '2025-01-01',
                         'status': 'restored', 'username': 'admin',
                         'message': 'test restore'}},
        ]
        es = FakeESClient(scroll_hits=hits)
        display_restored_table(es, 'rc_snapshots')
        captured = capsys.readouterr()
        assert 'idx-1' in captured.out
        assert 'admin' in captured.out


# ---------------------------------------------------------------------------
# display_history_table
# ---------------------------------------------------------------------------

class TestDisplayHistoryTable(object):

    def test_empty_results(self, capsys):
        """No history prints a warning."""
        es = FakeESClient(scroll_hits=[])
        display_history_table(es, 'rc_snapshots_history')
        captured = capsys.readouterr()
        assert 'No history entries found' in captured.out

    def test_renders_entries(self, capsys):
        """History entries are rendered."""
        hits = [
            {'_source': {'datetime': '2025-01-01T00:00:00', 'username': 'op1',
                         'status': 'success', 'message': 'Restored index'}},
        ]
        es = FakeESClient(scroll_hits=hits)
        display_history_table(es, 'rc_snapshots_history')
        captured = capsys.readouterr()
        assert 'op1' in captured.out
        assert 'success' in captured.out

    def test_limits_to_50(self, capsys):
        """Only first 50 entries are displayed even if more are returned."""
        hits = [
            {'_source': {'datetime': 'dt-%d' % i, 'username': 'u',
                         'status': 's', 'message': 'm'}}
            for i in range(80)
        ]
        es = FakeESClient(scroll_hits=hits)
        display_history_table(es, 'rc_snapshots_history')
        captured = capsys.readouterr()
        # dt-49 should be present (index 49), dt-50 should not
        assert 'dt-49' in captured.out
        assert 'dt-50' not in captured.out


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

class TestBuildParser(object):

    def test_default_command(self):
        """Default command is help."""
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.command == 'help'

    def test_list_command(self):
        """list command is parsed."""
        parser = _build_parser()
        args = parser.parse_args(['list'])
        assert args.command == 'list'

    def test_regex_argument(self):
        """Regex positional arg is captured."""
        parser = _build_parser()
        args = parser.parse_args(['list', 'snap_.*'])
        assert args.regex == 'snap_.*'

    def test_locations_flag(self):
        """--locations flag is parsed."""
        parser = _build_parser()
        args = parser.parse_args(['--locations', 'PROD', 'list'])
        assert args.locations == 'PROD'

    def test_password_flag(self):
        """--password flag is parsed."""
        parser = _build_parser()
        args = parser.parse_args(['--password', 'ping'])
        assert args.password is True

    def test_size_flag(self):
        """--size flag is parsed."""
        parser = _build_parser()
        args = parser.parse_args(['--size', 'list'])
        assert args.size is True

    def test_all_commands_valid(self):
        """All documented commands are accepted."""
        parser = _build_parser()
        for cmd in COMMANDS:
            args = parser.parse_args([cmd])
            assert args.command == cmd


# ---------------------------------------------------------------------------
# _cmd_list
# ---------------------------------------------------------------------------

class TestCmdList(object):

    def test_no_snapshots(self, capsys):
        """Empty snapshot list prints warning."""
        es = FakeESClient(snapshots_brief=[])
        args = argparse.Namespace(regex=None, size=False, verbose=False)
        _cmd_list(es, args, {'repository': 'test-repo'})
        captured = capsys.readouterr()
        assert 'No snapshots found' in captured.out

    def test_regex_filter(self, capsys):
        """Regex filters snapshots by name (fast path)."""
        brief = [
            {'snapshot': 'snapshot_logs', 'uuid': 'uuid-1', 'state': 'SUCCESS', 'indices': ['logs']},
            {'snapshot': 'snapshot_metrics', 'uuid': 'uuid-2', 'state': 'SUCCESS', 'indices': ['metrics']},
        ]
        es = FakeESClient(snapshots_brief=brief)
        args = argparse.Namespace(regex='logs', size=False, verbose=False)
        _cmd_list(es, args, {'repository': 'test-repo'})
        captured = capsys.readouterr()
        assert 'snapshot_logs' in captured.out
        assert 'snapshot_metrics' not in captured.out

    def test_invalid_regex(self, capsys):
        """Invalid regex prints error."""
        brief = [{'snapshot': 'snap', 'uuid': 'uuid-1', 'state': 'SUCCESS', 'indices': []}]
        es = FakeESClient(snapshots_brief=brief)
        args = argparse.Namespace(regex='[invalid', size=False, verbose=False)
        _cmd_list(es, args, {'repository': 'test-repo'})
        captured = capsys.readouterr()
        assert 'Invalid regex' in captured.out

    def test_verbose_uses_cat_snapshots(self, capsys):
        """--verbose flag uses the slower cat/snapshots API."""
        snaps = [
            {'id': 'snapshot_logs', 'status': 'SUCCESS', 'end_time': '',
             'duration': '5s', 'total_shards': '1'},
        ]
        es = FakeESClient(snapshots=snaps)
        args = argparse.Namespace(regex=None, size=False, verbose=True)
        _cmd_list(es, args, {'repository': 'test-repo'})
        captured = capsys.readouterr()
        assert 'snapshot_logs' in captured.out
        assert 'SUCCESS' in captured.out


# ---------------------------------------------------------------------------
# _cmd_ping
# ---------------------------------------------------------------------------

class TestCmdPing(object):

    def test_ping_success(self, capsys):
        """Successful ping reports connection and health."""
        es = FakeESClient(ping_ok=True, health=('green', '[green]green[/green]'))
        _cmd_ping(es)
        captured = capsys.readouterr()
        assert 'Connection successful' in captured.out
        assert 'green' in captured.out

    def test_ping_failure(self, capsys):
        """Failed ping reports failure."""
        es = FakeESClient(ping_ok=False)
        _cmd_ping(es)
        captured = capsys.readouterr()
        assert 'Connection failed' in captured.out
