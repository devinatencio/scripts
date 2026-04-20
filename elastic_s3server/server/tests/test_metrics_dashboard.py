"""Tests for metrics_dashboard.py."""

import datetime
import json
import os

import pytest

from server.metrics_dashboard import render_dashboard, main, console


# ---------------------------------------------------------------------------
# Ensure the Rich console is wide enough for the full table layout.
# In test environments stdout is not a real terminal so Rich defaults to
# 80 columns.  The dashboard table needs more room.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _wide_console():
    """Temporarily widen the module-level Rich console for all tests."""
    original = console.width
    console.width = 120
    yield
    console.width = original


# ---------------------------------------------------------------------------
# render_dashboard
# ---------------------------------------------------------------------------

class TestRenderDashboard(object):

    def _make_metrics(self, **overrides):
        """Build a complete metrics dict with optional overrides."""
        now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        today = datetime.date.today().strftime('%Y-%m-%d')
        data = {
            'daily_counters': {
                'date': today,
                'snapshots_created': 5,
                'snapshots_deleted': 2,
                'indices_deleted_ilm': 1,
            },
            'utility_health': {
                'cold_snapshots': {'last_run': now, 'success': True},
                'retention_enforcer': {'last_run': now, 'success': False},
            },
            'snapshot_statuses': {
                'SUCCESS': 100,
                'FAILED': 3,
                'PARTIAL': 0,
                'IN_PROGRESS': 1,
                'INCOMPATIBLE': 0,
            },
        }
        data.update(overrides)
        return data

    def test_daily_counters_displayed(self, capsys):
        """Daily counters panel shows date and counts."""
        metrics = self._make_metrics()
        render_dashboard(metrics)
        out = capsys.readouterr().out
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        assert today_str in out
        assert 'Snapshots Created' in out
        assert '5' in out
        assert 'Snapshots Deleted' in out
        assert 'ILM Indices Deleted' in out

    def test_stale_date_shows_zeros(self, capsys):
        """When stored date is yesterday, counters show 0 with a note."""
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        metrics = self._make_metrics(daily_counters={
            'date': yesterday,
            'snapshots_created': 99,
            'snapshots_deleted': 50,
            'indices_deleted_ilm': 25,
        })
        render_dashboard(metrics)
        out = capsys.readouterr().out
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        # Should show today's date, not yesterday's
        assert today_str in out
        # Should NOT show yesterday's counts
        assert '99' not in out
        # Should show the stale note
        assert 'no activity yet today' in out

    def test_today_date_shows_actual_counts(self, capsys):
        """When stored date is today, counters show actual values."""
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        metrics = self._make_metrics(daily_counters={
            'date': today_str,
            'snapshots_created': 42,
            'snapshots_deleted': 7,
            'indices_deleted_ilm': 3,
        })
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert today_str in out
        assert '42' in out
        assert 'no activity yet today' not in out

    def test_utility_health_green(self, capsys):
        """Successful utility with recent run shows OK."""
        now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        metrics = self._make_metrics(
            utility_health={'my_util': {'last_run': now, 'success': True}}
        )
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'my_util' in out
        assert 'OK' in out

    def test_utility_health_red_failure(self, capsys):
        """Failed utility shows FAIL."""
        now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        metrics = self._make_metrics(
            utility_health={'bad_util': {'last_run': now, 'success': False}}
        )
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'bad_util' in out
        assert 'FAIL' in out

    def test_utility_health_red_stale(self, capsys):
        """Utility with last_run older than 24h shows red even if success."""
        old_time = (datetime.datetime.now() - datetime.timedelta(hours=25)).strftime(
            '%Y-%m-%dT%H:%M:%S'
        )
        metrics = self._make_metrics(
            utility_health={'stale_util': {'last_run': old_time, 'success': True}}
        )
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'stale_util' in out
        assert 'OK' in out

    def test_utility_health_overdue(self, capsys):
        """Utility that hasn't run within 2x its interval shows OVERDUE."""
        # Configured for every 30m (1800s) with 5m jitter (300s)
        # Grace = 2*1800 + 300 = 3900s = 65 minutes
        # Last run 2 hours ago = well past grace
        old_time = (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime(
            '%Y-%m-%dT%H:%M:%S'
        )
        metrics = self._make_metrics(
            utility_health={'cold_snapshots': {'last_run': old_time, 'success': True}}
        )
        metrics['daemon_heartbeat'] = {
            'pid': '99999',
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'tasks': {
                'cold_snapshots': {
                    'enabled': True,
                    'schedule_type': 'interval',
                    'interval_seconds': 1800,
                    'jitter_seconds': 300,
                    'running': False,
                    'last_run_epoch': 0,
                },
            },
        }
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'OVERDUE' in out

    def test_utility_health_not_overdue_within_grace(self, capsys):
        """Utility that ran recently within grace period shows OK."""
        recent_time = (datetime.datetime.now() - datetime.timedelta(minutes=10)).strftime(
            '%Y-%m-%dT%H:%M:%S'
        )
        metrics = self._make_metrics(
            utility_health={'cold_snapshots': {'last_run': recent_time, 'success': True}}
        )
        metrics['daemon_heartbeat'] = {
            'pid': '99999',
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'tasks': {
                'cold_snapshots': {
                    'enabled': True,
                    'schedule_type': 'interval',
                    'interval_seconds': 1800,
                    'jitter_seconds': 300,
                    'running': False,
                    'last_run_epoch': 0,
                },
            },
        }
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'OK' in out
        assert 'OVERDUE' not in out

    def test_window_task_not_overdue_outside_window(self, capsys):
        """Window task outside its window is not flagged overdue even if stale."""
        # Window is 20:00-03:00, last ran 8h ago, but we're outside the window
        # so it's expected to not have run.
        old_time = (datetime.datetime.now() - datetime.timedelta(hours=8)).strftime(
            '%Y-%m-%dT%H:%M:%S'
        )
        # Pick a window that does NOT include the current time
        now_hour = datetime.datetime.now().hour
        # Create a window that's definitely not now (offset by 12 hours)
        w_start_h = (now_hour + 10) % 24
        w_end_h = (now_hour + 12) % 24
        w_start = '%02d:00' % w_start_h
        w_end = '%02d:00' % w_end_h

        metrics = self._make_metrics(
            utility_health={'ilm_curator': {'last_run': old_time, 'success': True}}
        )
        metrics['daemon_heartbeat'] = {
            'pid': '99999',
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'tasks': {
                'ilm_curator': {
                    'enabled': True,
                    'schedule_type': 'window',
                    'interval_seconds': 60,
                    'jitter_seconds': 300,
                    'window_start': w_start,
                    'window_end': w_end,
                    'running': False,
                    'last_run_epoch': 0,
                },
            },
        }
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'OVERDUE' not in out

    def test_window_task_overdue_inside_window(self, capsys):
        """Window task inside its window that hasn't run is flagged overdue."""
        old_time = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime(
            '%Y-%m-%dT%H:%M:%S'
        )
        # Create a window that includes the current time
        now_hour = datetime.datetime.now().hour
        w_start_h = (now_hour - 1) % 24
        w_end_h = (now_hour + 2) % 24
        w_start = '%02d:00' % w_start_h
        w_end = '%02d:00' % w_end_h

        metrics = self._make_metrics(
            utility_health={'ilm_curator': {'last_run': old_time, 'success': True}}
        )
        metrics['daemon_heartbeat'] = {
            'pid': '99999',
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'tasks': {
                'ilm_curator': {
                    'enabled': True,
                    'schedule_type': 'window',
                    'interval_seconds': 60,
                    'jitter_seconds': 60,
                    'window_start': w_start,
                    'window_end': w_end,
                    'running': False,
                    'last_run_epoch': 0,
                },
            },
        }
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'OVERDUE' in out

    def test_empty_health(self, capsys):
        """Empty utility_health with no daemon shows no-data row."""
        metrics = self._make_metrics(utility_health={})
        # Remove daemon heartbeat so no task names are seeded
        metrics.pop('daemon_heartbeat', None)
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'No data' in out

    def test_daemon_tasks_seeded_in_health(self, capsys):
        """Utilities from daemon heartbeat appear even without health data."""
        metrics = self._make_metrics(utility_health={})
        metrics['daemon_heartbeat'] = {
            'pid': '99999',
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'tasks': {
                'cold_snapshots': {'enabled': True},
                'ilm_curator': {'enabled': True},
                'retention_enforcer': {'enabled': True},
                'restored_index_manager': {'enabled': True},
            },
        }
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'cold_snapshots' in out
        assert 'ilm_curator' in out
        assert 'retention_enforcer' in out
        assert 'restored_index_manager' in out
        assert 'Awaiting first run' in out

    def test_daemon_task_config_displayed(self, capsys):
        """Daemon panel shows config details for each task."""
        metrics = self._make_metrics()
        metrics['daemon_heartbeat'] = {
            'pid': '99999',
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'tasks': {
                'cold_snapshots': {
                    'enabled': True,
                    'schedule_type': 'interval',
                    'running': False,
                    'last_run_epoch': 0,
                    'interval_seconds': 1800,
                    'jitter_seconds': 300,
                },
                'ilm_curator': {
                    'enabled': True,
                    'schedule_type': 'window',
                    'running': False,
                    'last_run_epoch': 0,
                    'interval_seconds': 3600,
                    'jitter_seconds': 600,
                    'window_start': '00:00',
                    'window_end': '05:00',
                },
            },
        }
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'every 30m' in out
        assert 'jitter 5m' in out
        assert 'every 1h' in out
        assert 'jitter 10m' in out
        assert '00:00' in out

    def test_snapshot_statuses_displayed(self, capsys):
        """Snapshot status distribution panel shows all status types."""
        metrics = self._make_metrics()
        render_dashboard(metrics)
        out = capsys.readouterr().out
        assert 'SUCCESS' in out
        assert 'FAILED' in out
        assert 'PARTIAL' in out
        assert 'IN_PROGRESS' in out
        assert 'INCOMPATIBLE' in out
        assert '100' in out

    def test_missing_sections_handled(self, capsys):
        """Dashboard handles metrics dict with missing sections gracefully."""
        render_dashboard({})
        out = capsys.readouterr().out
        assert 'Snapshot Overview' in out
        assert 'Utility Health' in out
        assert 'SUCCESS' in out


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain(object):

    def test_missing_file(self, capsys, monkeypatch, tmp_path):
        """Missing metrics file shows no-data message."""
        fake_path = str(tmp_path / 'nonexistent.json')
        monkeypatch.setattr(
            'sys.argv', ['metrics_dashboard', '--metrics-file', fake_path]
        )
        main()
        out = capsys.readouterr().out
        assert 'No metrics data available' in out

    def test_empty_file(self, capsys, monkeypatch, tmp_path):
        """Empty metrics file shows no-data message."""
        empty_file = str(tmp_path / 'empty.json')
        with open(empty_file, 'w') as f:
            pass  # create empty file
        monkeypatch.setattr(
            'sys.argv', ['metrics_dashboard', '--metrics-file', empty_file]
        )
        main()
        out = capsys.readouterr().out
        assert 'No metrics data available' in out

    def test_valid_file(self, capsys, monkeypatch, tmp_path):
        """Valid metrics file renders the dashboard."""
        now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        today = datetime.date.today().strftime('%Y-%m-%d')
        data = {
            'daily_counters': {
                'date': today,
                'snapshots_created': 10,
                'snapshots_deleted': 3,
                'indices_deleted_ilm': 2,
            },
            'utility_health': {
                'cold_snapshots': {'last_run': now, 'success': True},
            },
            'snapshot_statuses': {
                'SUCCESS': 50,
                'FAILED': 1,
                'PARTIAL': 0,
                'IN_PROGRESS': 0,
                'INCOMPATIBLE': 0,
            },
        }
        metrics_file = str(tmp_path / 'metrics.json')
        # Seed the SQLite database via write_metrics
        from server.metrics_collector import write_metrics
        write_metrics(metrics_file, data)
        # Also create the .json file so main()'s existence check passes
        with open(metrics_file, 'w') as f:
            json.dump(data, f)
        monkeypatch.setattr(
            'sys.argv', ['metrics_dashboard', '--metrics-file', metrics_file]
        )
        main()
        out = capsys.readouterr().out
        assert today in out
        assert 'Snapshot Overview' in out


# ---------------------------------------------------------------------------
# render_history
# ---------------------------------------------------------------------------

from server.metrics_dashboard import render_history, _build_bar


class TestBuildBar(object):

    def test_zero_max_returns_empty(self):
        assert _build_bar(5, 0) == ''

    def test_zero_value_returns_empty(self):
        assert _build_bar(0, 10) == ''

    def test_max_value_fills_width(self):
        bar = _build_bar(10, 10, width=20)
        assert len(bar) == 20

    def test_half_value_half_width(self):
        bar = _build_bar(5, 10, width=20)
        assert len(bar) == 10

    def test_small_nonzero_gets_at_least_one_block(self):
        bar = _build_bar(1, 1000, width=30)
        assert len(bar) >= 1


class TestRenderHistory(object):

    def _make_history_metrics(self, num_days=10):
        """Build metrics with daily_history spanning num_days."""
        today = datetime.date.today()
        history = []
        for i in range(num_days, 0, -1):
            d = (today - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': i * 2,
                'snapshots_deleted': i,
                'indices_deleted_ilm': max(i - 5, 0),
            })
        return {
            'daily_counters': {
                'date': today.strftime('%Y-%m-%d'),
                'snapshots_created': 3,
                'snapshots_deleted': 1,
                'indices_deleted_ilm': 0,
            },
            'daily_history': history,
            'utility_health': {},
            'snapshot_statuses': {},
        }

    def test_renders_all_three_counters(self, capsys):
        """History view shows tables for all three counter types."""
        metrics = self._make_history_metrics(10)
        render_history(metrics, days=30)
        out = capsys.readouterr().out
        assert 'Snapshots Created' in out
        assert 'Snapshots Deleted' in out
        assert 'ILM Indices Deleted' in out

    def test_includes_today_in_output(self, capsys):
        """Today's live counters appear in the history view."""
        metrics = self._make_history_metrics(5)
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        render_history(metrics, days=7)
        out = capsys.readouterr().out
        assert today_str in out

    def test_trims_to_requested_days(self, capsys):
        """Only the last N days are shown when days < history length."""
        metrics = self._make_history_metrics(20)
        render_history(metrics, days=7)
        out = capsys.readouterr().out
        # Should show "last 7 days" in the title
        assert 'last 7 days' in out

    def test_empty_history_shows_message(self, capsys):
        """No history data shows a friendly message."""
        render_history({'daily_counters': {}, 'daily_history': []}, days=30)
        out = capsys.readouterr().out
        assert 'No historical data available' in out

    def test_shows_total_and_average(self, capsys):
        """History tables include total and avg summary."""
        metrics = self._make_history_metrics(5)
        render_history(metrics, days=30)
        out = capsys.readouterr().out
        assert 'total:' in out
        assert 'avg:' in out

    def test_no_duplicate_today_when_already_in_history(self, capsys):
        """If today is already in daily_history, it is not duplicated."""
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        metrics = {
            'daily_counters': {
                'date': today_str,
                'snapshots_created': 5,
                'snapshots_deleted': 0,
                'indices_deleted_ilm': 0,
            },
            'daily_history': [{
                'date': today_str,
                'snapshots_created': 5,
                'snapshots_deleted': 0,
                'indices_deleted_ilm': 0,
            }],
        }
        render_history(metrics, days=7)
        out = capsys.readouterr().out
        # Today's date should appear only once in the Date column
        # (it will also appear in the title, so count table rows)
        assert out.count(today_str) >= 1


class TestMainHistory(object):

    def test_history_flag_renders_history(self, capsys, monkeypatch, tmp_path):
        """--history flag triggers render_history instead of render_dashboard."""
        today = datetime.date.today()
        history = []
        for i in range(7, 0, -1):
            d = (today - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': i,
                'snapshots_deleted': 0,
                'indices_deleted_ilm': 0,
            })
        data = {
            'daily_counters': {
                'date': today.strftime('%Y-%m-%d'),
                'snapshots_created': 1,
                'snapshots_deleted': 0,
                'indices_deleted_ilm': 0,
            },
            'daily_history': history,
            'utility_health': {},
            'snapshot_statuses': {},
        }
        metrics_file = str(tmp_path / 'metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(data, f)
        monkeypatch.setattr(
            'sys.argv', ['metrics_dashboard', '--metrics-file', metrics_file, '--history', '7']
        )
        main()
        out = capsys.readouterr().out
        assert 'Snapshots Created' in out
        assert 'last 7 days' in out
        # Should NOT show the regular dashboard panels
        assert 'Utility Health' not in out

# ---------------------------------------------------------------------------
# render_forecast
# ---------------------------------------------------------------------------

from server.metrics_dashboard import render_forecast


class TestRenderForecast(object):

    def _make_forecast_metrics(self, num_days=30):
        """Build metrics with enough history for forecasting."""
        today = datetime.date.today()
        history = []
        for i in range(num_days, 0, -1):
            d = (today - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': 10 + i % 5,
                'snapshots_deleted': 3 + i % 3,
                'indices_deleted_ilm': max(i % 4, 0),
            })
        return {
            'daily_counters': {
                'date': today.strftime('%Y-%m-%d'),
                'snapshots_created': 12,
                'snapshots_deleted': 4,
                'indices_deleted_ilm': 1,
            },
            'daily_history': history,
            'utility_health': {},
            'snapshot_statuses': {},
        }

    def test_renders_net_growth_headline(self, capsys):
        """Forecast view shows the net growth headline panel."""
        metrics = self._make_forecast_metrics(30)
        render_forecast(metrics)
        out = capsys.readouterr().out
        assert 'Net Snapshot Growth' in out

    def test_renders_actionable_insights(self, capsys):
        """Forecast view shows the actionable insights panel."""
        metrics = self._make_forecast_metrics(30)
        render_forecast(metrics)
        out = capsys.readouterr().out
        assert 'Actionable Insights' in out

    def test_renders_all_counter_forecasts(self, capsys):
        """Forecast view shows cards for all four metrics."""
        metrics = self._make_forecast_metrics(30)
        render_forecast(metrics)
        out = capsys.readouterr().out
        assert 'Snapshots Created' in out
        assert 'Snapshots Deleted' in out
        assert 'ILM Indices Deleted' in out
        assert 'Net Snapshot Growth' in out

    def test_renders_cumulative_table(self, capsys):
        """Forecast view shows the cumulative projections table."""
        metrics = self._make_forecast_metrics(30)
        render_forecast(metrics)
        out = capsys.readouterr().out
        assert 'Cumulative Projections' in out

    def test_renders_weekly_trend(self, capsys):
        """Forecast view shows weekly net growth trend table."""
        metrics = self._make_forecast_metrics(30)
        render_forecast(metrics)
        out = capsys.readouterr().out
        assert 'Weekly Net Growth Trend' in out

    def test_renders_confidence_indicator(self, capsys):
        """Forecast view shows confidence level."""
        metrics = self._make_forecast_metrics(30)
        render_forecast(metrics)
        out = capsys.readouterr().out
        # Should contain one of the confidence levels
        assert any(level in out for level in ('high', 'medium', 'low'))

    def test_renders_activity_forecast_title(self, capsys):
        """Outer panel has the Activity Forecast title."""
        metrics = self._make_forecast_metrics(10)
        render_forecast(metrics)
        out = capsys.readouterr().out
        assert 'Activity Forecast' in out

    def test_empty_history_still_renders(self, capsys):
        """Forecast with no history data renders without error."""
        metrics = {
            'daily_counters': {},
            'daily_history': [],
        }
        render_forecast(metrics)
        out = capsys.readouterr().out
        assert 'Activity Forecast' in out

    def test_renders_slope_info(self, capsys):
        """Forecast view shows slope information."""
        metrics = self._make_forecast_metrics(30)
        render_forecast(metrics)
        out = capsys.readouterr().out
        assert 'slope' in out.lower()

    def test_renders_r_squared(self, capsys):
        """Forecast view shows R-squared value."""
        metrics = self._make_forecast_metrics(30)
        render_forecast(metrics)
        out = capsys.readouterr().out
        assert 'R\u00b2' in out


class TestMainForecast(object):

    def test_forecast_flag_renders_forecast(self, capsys, monkeypatch, tmp_path):
        """--forecast flag triggers render_forecast instead of render_dashboard."""
        today = datetime.date.today()
        history = []
        for i in range(14, 0, -1):
            d = (today - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': 10,
                'snapshots_deleted': 3,
                'indices_deleted_ilm': 1,
            })
        data = {
            'daily_counters': {
                'date': today.strftime('%Y-%m-%d'),
                'snapshots_created': 10,
                'snapshots_deleted': 3,
                'indices_deleted_ilm': 1,
            },
            'daily_history': history,
            'utility_health': {},
            'snapshot_statuses': {},
        }
        metrics_file = str(tmp_path / 'metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(data, f)
        monkeypatch.setattr(
            'sys.argv', ['metrics_dashboard', '--metrics-file', metrics_file, '--forecast']
        )
        main()
        out = capsys.readouterr().out
        assert 'Activity Forecast' in out
        assert 'Net Snapshot Growth' in out
        # Should NOT show the regular dashboard panels
        assert 'Utility Health' not in out


# ---------------------------------------------------------------------------
# _build_dashboard / _build_forecast (renderable builders)
# ---------------------------------------------------------------------------

from server.metrics_dashboard import _build_dashboard, _build_forecast


class TestBuildDashboard(object):

    def test_returns_panel(self):
        """_build_dashboard returns a Rich Panel, not None."""
        now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        metrics = {
            'daily_counters': {
                'date': '2025-06-01',
                'snapshots_created': 5,
                'snapshots_deleted': 2,
                'indices_deleted_ilm': 1,
            },
            'utility_health': {
                'cold_snapshots': {'last_run': now, 'success': True},
            },
            'snapshot_statuses': {
                'SUCCESS': 50, 'FAILED': 1, 'PARTIAL': 0,
                'IN_PROGRESS': 0, 'INCOMPATIBLE': 0,
            },
        }
        result = _build_dashboard(metrics)
        assert result is not None
        # Should be a Panel (has a title attribute)
        assert hasattr(result, 'title')


class TestBuildForecast(object):

    def test_returns_panel(self):
        """_build_forecast returns a Rich Panel, not None."""
        today = datetime.date.today()
        history = []
        for i in range(10, 0, -1):
            d = (today - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': 10,
                'snapshots_deleted': 3,
                'indices_deleted_ilm': 1,
            })
        metrics = {
            'daily_counters': {
                'date': today.strftime('%Y-%m-%d'),
                'snapshots_created': 10,
                'snapshots_deleted': 3,
                'indices_deleted_ilm': 1,
            },
            'daily_history': history,
        }
        result = _build_forecast(metrics)
        assert result is not None
        assert hasattr(result, 'title')


# ---------------------------------------------------------------------------
# _watch_loop
# ---------------------------------------------------------------------------

from server.metrics_dashboard import _watch_loop


class TestWatchLoop(object):

    def test_watch_reads_file_and_exits_on_interrupt(self, tmp_path, monkeypatch):
        """Watch loop reads the metrics file and exits cleanly on KeyboardInterrupt."""
        today = datetime.date.today().strftime('%Y-%m-%d')
        data = {
            'daily_counters': {
                'date': today,
                'snapshots_created': 1,
                'snapshots_deleted': 0,
                'indices_deleted_ilm': 0,
            },
            'utility_health': {},
            'snapshot_statuses': {
                'SUCCESS': 10, 'FAILED': 0, 'PARTIAL': 0,
                'IN_PROGRESS': 0, 'INCOMPATIBLE': 0,
            },
        }
        metrics_file = str(tmp_path / 'metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(data, f)

        # Patch time.sleep to raise KeyboardInterrupt on first call
        # so the loop runs exactly once then exits
        call_count = [0]

        def fake_sleep(seconds):
            call_count[0] += 1
            raise KeyboardInterrupt()

        monkeypatch.setattr('time.sleep', fake_sleep)

        # Should not raise — KeyboardInterrupt is caught internally
        _watch_loop(metrics_file, interval=5, forecast=False)
        assert call_count[0] == 1

    def test_watch_forecast_mode(self, tmp_path, monkeypatch):
        """Watch loop works with forecast=True."""
        today = datetime.date.today()
        history = []
        for i in range(5, 0, -1):
            d = (today - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': 5,
                'snapshots_deleted': 1,
                'indices_deleted_ilm': 0,
            })
        data = {
            'daily_counters': {
                'date': today.strftime('%Y-%m-%d'),
                'snapshots_created': 5,
                'snapshots_deleted': 1,
                'indices_deleted_ilm': 0,
            },
            'daily_history': history,
            'utility_health': {},
            'snapshot_statuses': {},
        }
        metrics_file = str(tmp_path / 'metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(data, f)

        call_count = [0]

        def fake_sleep(seconds):
            call_count[0] += 1
            raise KeyboardInterrupt()

        monkeypatch.setattr('time.sleep', fake_sleep)

        _watch_loop(metrics_file, interval=10, forecast=True)
        assert call_count[0] == 1

    def test_watch_enforces_minimum_interval(self, tmp_path, monkeypatch):
        """Interval below 1 is clamped to 1."""
        data = {
            'daily_counters': {'date': '2025-01-01',
                               'snapshots_created': 0,
                               'snapshots_deleted': 0,
                               'indices_deleted_ilm': 0},
            'utility_health': {},
            'snapshot_statuses': {
                'SUCCESS': 0, 'FAILED': 0, 'PARTIAL': 0,
                'IN_PROGRESS': 0, 'INCOMPATIBLE': 0,
            },
        }
        metrics_file = str(tmp_path / 'metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(data, f)

        sleep_args = []

        def fake_sleep(seconds):
            sleep_args.append(seconds)
            raise KeyboardInterrupt()

        monkeypatch.setattr('time.sleep', fake_sleep)

        _watch_loop(metrics_file, interval=0, forecast=False)
        # Should have been clamped to 1, not 0
        assert sleep_args[0] == 1
