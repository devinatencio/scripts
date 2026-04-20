"""Tests for capacity_forecast.py."""

import datetime

import pytest

from server.capacity_forecast import (
    _linear_regression,
    _r_squared,
    _weekly_averages,
    compute_all_forecasts,
    compute_forecast,
    compute_net_growth_forecast,
    generate_insights,
)


# ---------------------------------------------------------------------------
# _linear_regression
# ---------------------------------------------------------------------------

class TestLinearRegression(object):

    def test_perfect_positive_slope(self):
        """y = 2x + 1 should give slope=2, intercept=1."""
        xs = [0.0, 1.0, 2.0, 3.0, 4.0]
        ys = [1.0, 3.0, 5.0, 7.0, 9.0]
        slope, intercept = _linear_regression(xs, ys)
        assert abs(slope - 2.0) < 1e-9
        assert abs(intercept - 1.0) < 1e-9

    def test_flat_line(self):
        """Constant values should give slope=0."""
        xs = [0.0, 1.0, 2.0, 3.0]
        ys = [5.0, 5.0, 5.0, 5.0]
        slope, intercept = _linear_regression(xs, ys)
        assert abs(slope) < 1e-9
        assert abs(intercept - 5.0) < 1e-9

    def test_negative_slope(self):
        """Decreasing values should give negative slope."""
        xs = [0.0, 1.0, 2.0, 3.0]
        ys = [10.0, 7.0, 4.0, 1.0]
        slope, intercept = _linear_regression(xs, ys)
        assert slope < 0

    def test_single_point_returns_zero_slope(self):
        """Single data point returns slope=0."""
        slope, intercept = _linear_regression([1.0], [5.0])
        assert slope == 0.0

    def test_empty_returns_zeros(self):
        """Empty input returns (0, 0)."""
        slope, intercept = _linear_regression([], [])
        assert slope == 0.0
        assert intercept == 0.0

    def test_two_points(self):
        """Two points should give exact fit."""
        xs = [0.0, 10.0]
        ys = [0.0, 50.0]
        slope, intercept = _linear_regression(xs, ys)
        assert abs(slope - 5.0) < 1e-9
        assert abs(intercept) < 1e-9


# ---------------------------------------------------------------------------
# _r_squared
# ---------------------------------------------------------------------------

class TestRSquared(object):

    def test_perfect_fit(self):
        """Perfect linear data should give R^2 = 1.0."""
        xs = [0.0, 1.0, 2.0, 3.0]
        ys = [2.0, 4.0, 6.0, 8.0]
        r2 = _r_squared(xs, ys, 2.0, 2.0)
        assert abs(r2 - 1.0) < 1e-9

    def test_constant_values(self):
        """All identical values should give R^2 = 1.0."""
        xs = [0.0, 1.0, 2.0]
        ys = [3.0, 3.0, 3.0]
        r2 = _r_squared(xs, ys, 0.0, 3.0)
        assert abs(r2 - 1.0) < 1e-9

    def test_poor_fit(self):
        """Random-looking data with wrong model should give low R^2."""
        xs = [0.0, 1.0, 2.0, 3.0]
        ys = [1.0, 100.0, 2.0, 99.0]
        r2 = _r_squared(xs, ys, 0.0, 50.0)
        assert r2 < 0.5

    def test_single_point(self):
        """Single point returns 0.0."""
        r2 = _r_squared([1.0], [5.0], 0.0, 5.0)
        assert r2 == 0.0


# ---------------------------------------------------------------------------
# _weekly_averages
# ---------------------------------------------------------------------------

class TestWeeklyAverages(object):

    def test_single_week(self):
        """Seven consecutive days in one week produce one entry."""
        # 2025-01-06 (Mon) to 2025-01-12 (Sun) = ISO week 2
        dates = ['2025-01-06', '2025-01-07', '2025-01-08',
                 '2025-01-09', '2025-01-10', '2025-01-11', '2025-01-12']
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
        result = _weekly_averages(values, dates)
        assert len(result) == 1
        assert abs(result[0][1] - 40.0) < 1e-9

    def test_two_weeks(self):
        """Data spanning two weeks produces two entries."""
        dates = ['2025-01-06', '2025-01-07', '2025-01-13', '2025-01-14']
        values = [10.0, 20.0, 30.0, 40.0]
        result = _weekly_averages(values, dates)
        assert len(result) == 2

    def test_empty_input(self):
        """Empty data returns empty list."""
        assert _weekly_averages([], []) == []

    def test_invalid_dates_skipped(self):
        """Invalid date strings are silently skipped."""
        result = _weekly_averages([1.0, 2.0], ['bad-date', '2025-01-06'])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# compute_forecast
# ---------------------------------------------------------------------------

class TestComputeForecast(object):

    def _make_history(self, num_days, base_value=10, slope=0):
        """Generate synthetic daily history."""
        today = datetime.date.today()
        history = []
        for i in range(num_days):
            d = (today - datetime.timedelta(days=num_days - i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': base_value + int(slope * i),
            })
        return history

    def test_empty_history(self):
        """Empty history returns zero forecast with low confidence."""
        result = compute_forecast([], 'snapshots_created')
        assert result['data_points'] == 0
        assert result['confidence'] == 'low'
        assert result['projections'][30] == 0.0

    def test_flat_data_zero_slope(self):
        """Constant daily values produce near-zero slope."""
        history = self._make_history(30, base_value=10, slope=0)
        result = compute_forecast(history, 'snapshots_created')
        assert abs(result['slope_per_day']) < 0.01
        assert result['current_avg'] == 10.0

    def test_growing_data_positive_slope(self):
        """Increasing daily values produce positive slope."""
        history = self._make_history(30, base_value=5, slope=1)
        result = compute_forecast(history, 'snapshots_created')
        assert result['slope_per_day'] > 0

    def test_projections_increase_with_horizon(self):
        """Cumulative projections should grow with longer horizons."""
        history = self._make_history(30, base_value=10, slope=0)
        result = compute_forecast(history, 'snapshots_created')
        cum = result['cumulative_projections']
        assert cum[60] >= cum[30]
        assert cum[90] >= cum[60]

    def test_high_confidence_with_good_data(self):
        """30+ days of linear data should yield high confidence."""
        history = self._make_history(35, base_value=5, slope=2)
        result = compute_forecast(history, 'snapshots_created')
        assert result['confidence'] in ('high', 'medium')
        assert result['r_squared'] > 0.3

    def test_low_confidence_with_few_points(self):
        """Very few data points yield low confidence."""
        history = self._make_history(3, base_value=10, slope=0)
        result = compute_forecast(history, 'snapshots_created')
        assert result['confidence'] == 'low'

    def test_projections_non_negative(self):
        """Projected daily rates should never be negative."""
        history = self._make_history(20, base_value=100, slope=-10)
        result = compute_forecast(history, 'snapshots_created')
        for horizon in (30, 60, 90):
            assert result['projections'][horizon] >= 0.0


# ---------------------------------------------------------------------------
# compute_net_growth_forecast
# ---------------------------------------------------------------------------

class TestComputeNetGrowthForecast(object):

    def test_empty_history(self):
        result = compute_net_growth_forecast([])
        assert result['data_points'] == 0
        assert result['counter'] == 'net_growth'

    def test_net_growth_calculation(self):
        """Net growth = created - deleted."""
        today = datetime.date.today()
        history = []
        for i in range(10):
            d = (today - datetime.timedelta(days=10 - i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': 20,
                'snapshots_deleted': 5,
            })
        result = compute_net_growth_forecast(history)
        assert result['current_avg'] == 15.0

    def test_negative_net_growth(self):
        """More deletions than creations gives negative average."""
        today = datetime.date.today()
        history = []
        for i in range(10):
            d = (today - datetime.timedelta(days=10 - i)).strftime('%Y-%m-%d')
            history.append({
                'date': d,
                'snapshots_created': 2,
                'snapshots_deleted': 10,
            })
        result = compute_net_growth_forecast(history)
        assert result['current_avg'] < 0


# ---------------------------------------------------------------------------
# compute_all_forecasts
# ---------------------------------------------------------------------------

class TestComputeAllForecasts(object):

    def test_returns_all_keys(self):
        """Result contains all four forecast keys."""
        result = compute_all_forecasts({})
        assert 'snapshots_created' in result
        assert 'snapshots_deleted' in result
        assert 'indices_deleted_ilm' in result
        assert 'net_growth' in result

    def test_merges_today_counters(self):
        """Today's live counters are included in the forecast data."""
        today = datetime.date.today().strftime('%Y-%m-%d')
        metrics = {
            'daily_counters': {
                'date': today,
                'snapshots_created': 42,
                'snapshots_deleted': 0,
                'indices_deleted_ilm': 0,
            },
            'daily_history': [],
        }
        result = compute_all_forecasts(metrics)
        assert result['snapshots_created']['data_points'] == 1

    def test_no_duplicate_today(self):
        """Today is not duplicated if already in history."""
        today = datetime.date.today().strftime('%Y-%m-%d')
        metrics = {
            'daily_counters': {
                'date': today,
                'snapshots_created': 5,
                'snapshots_deleted': 0,
                'indices_deleted_ilm': 0,
            },
            'daily_history': [{
                'date': today,
                'snapshots_created': 5,
                'snapshots_deleted': 0,
                'indices_deleted_ilm': 0,
            }],
        }
        result = compute_all_forecasts(metrics)
        assert result['snapshots_created']['data_points'] == 1


# ---------------------------------------------------------------------------
# generate_insights
# ---------------------------------------------------------------------------

class TestGenerateInsights(object):

    def _make_forecasts(self, days=30, created_avg=10, deleted_avg=3,
                        ilm_avg=2, net_avg=7, net_slope=0.1,
                        confidence='medium', wow_pct=None):
        """Build a synthetic forecasts dict for testing insights."""
        return {
            'snapshots_created': {
                'data_points': days,
                'current_avg': float(created_avg),
                'slope_per_day': 0.0,
                'confidence': confidence,
                'r_squared': 0.5,
                'wow_change_pct': None,
            },
            'snapshots_deleted': {
                'data_points': days,
                'current_avg': float(deleted_avg),
                'slope_per_day': 0.0,
                'confidence': confidence,
                'r_squared': 0.5,
                'wow_change_pct': None,
            },
            'indices_deleted_ilm': {
                'data_points': days,
                'current_avg': float(ilm_avg),
                'slope_per_day': 0.0,
                'confidence': confidence,
                'r_squared': 0.5,
                'wow_change_pct': None,
            },
            'net_growth': {
                'data_points': days,
                'current_avg': float(net_avg),
                'slope_per_day': float(net_slope),
                'confidence': confidence,
                'r_squared': 0.5,
                'wow_change_pct': wow_pct,
                'cumulative_projections': {
                    30: net_avg * 30,
                    60: net_avg * 60,
                    90: net_avg * 90,
                },
            },
        }

    def test_empty_data_returns_no_data_message(self):
        """Zero data points produces a single info insight."""
        forecasts = self._make_forecasts(days=0)
        insights = generate_insights(forecasts)
        assert len(insights) == 1
        assert insights[0]['level'] == 'info'
        assert 'No historical data' in insights[0]['message']

    def test_few_days_warns_about_accuracy(self):
        """Less than 7 days produces a data-sufficiency caveat."""
        forecasts = self._make_forecasts(days=3)
        insights = generate_insights(forecasts)
        messages = [i['message'] for i in insights]
        assert any('3 day' in m for m in messages)
        assert any('rough estimates' in m for m in messages)

    def test_moderate_data_mentions_improving(self):
        """7-13 days mentions trends are forming."""
        forecasts = self._make_forecasts(days=10)
        insights = generate_insights(forecasts)
        messages = [i['message'] for i in insights]
        assert any('starting to form' in m for m in messages)

    def test_low_confidence_mentions_noisy(self):
        """Low confidence with enough data mentions noisy pattern."""
        forecasts = self._make_forecasts(days=20, confidence='low')
        insights = generate_insights(forecasts)
        messages = [i['message'] for i in insights]
        assert any('noisy' in m for m in messages)

    def test_growing_and_accelerating_warns(self):
        """Positive avg + high slope triggers a warning."""
        forecasts = self._make_forecasts(
            days=30, net_avg=15, net_slope=1.0, confidence='medium'
        )
        insights = generate_insights(forecasts)
        levels = [i['level'] for i in insights]
        messages = [i['message'] for i in insights]
        assert 'warning' in levels
        assert any('accelerating' in m for m in messages)

    def test_steady_growth_is_info(self):
        """Positive avg + low slope is informational."""
        forecasts = self._make_forecasts(
            days=30, net_avg=5, net_slope=0.1, confidence='medium'
        )
        insights = generate_insights(forecasts)
        messages = [i['message'] for i in insights]
        assert any('steady' in m for m in messages)

    def test_shrinking_repo_noted(self):
        """Negative net avg is reported as shrinking."""
        forecasts = self._make_forecasts(
            days=30, net_avg=-3, net_slope=-0.1, confidence='medium'
        )
        insights = generate_insights(forecasts)
        messages = [i['message'] for i in insights]
        assert any('shrinking' in m.lower() for m in messages)

    def test_wow_spike_warns(self):
        """Large WoW increase triggers a warning."""
        forecasts = self._make_forecasts(
            days=30, wow_pct=75.0, confidence='medium'
        )
        insights = generate_insights(forecasts)
        levels = [i['level'] for i in insights]
        assert 'warning' in levels
        messages = [i['message'] for i in insights]
        assert any('week-over-week' in m for m in messages)

    def test_wow_drop_is_info(self):
        """Large WoW decrease is informational."""
        forecasts = self._make_forecasts(
            days=30, wow_pct=-60.0, confidence='medium'
        )
        insights = generate_insights(forecasts)
        messages = [i['message'] for i in insights]
        assert any('cleanup' in m.lower() for m in messages)

    def test_low_deletion_ratio_warns(self):
        """Deletion rate far below creation rate triggers warning."""
        forecasts = self._make_forecasts(
            days=30, created_avg=20, deleted_avg=2, confidence='medium'
        )
        insights = generate_insights(forecasts)
        levels = [i['level'] for i in insights]
        messages = [i['message'] for i in insights]
        assert 'warning' in levels
        assert any('retention policies' in m.lower() for m in messages)

    def test_ilm_inactive_noted(self):
        """Zero ILM activity with active creation is noted."""
        forecasts = self._make_forecasts(
            days=10, ilm_avg=0, created_avg=10, confidence='medium'
        )
        insights = generate_insights(forecasts)
        messages = [i['message'] for i in insights]
        assert any('ILM curator' in m for m in messages)

    def test_ilm_outpacing_creation_warns(self):
        """ILM deleting faster than creation triggers warning."""
        forecasts = self._make_forecasts(
            days=30, ilm_avg=20, created_avg=5, confidence='medium'
        )
        insights = generate_insights(forecasts)
        levels = [i['level'] for i in insights]
        assert 'warning' in levels
        messages = [i['message'] for i in insights]
        assert any('before they' in m for m in messages)

    def test_sorted_by_severity(self):
        """Warnings come before info insights."""
        forecasts = self._make_forecasts(
            days=30, net_avg=15, net_slope=1.0,
            created_avg=20, deleted_avg=2, confidence='medium'
        )
        insights = generate_insights(forecasts)
        levels = [i['level'] for i in insights]
        # All warnings should come before all infos
        warning_indices = [i for i, l in enumerate(levels) if l == 'warning']
        info_indices = [i for i, l in enumerate(levels) if l == 'info']
        if warning_indices and info_indices:
            assert max(warning_indices) < min(info_indices)

    def test_low_confidence_skips_directional_insights(self):
        """Low confidence suppresses growth/shrink commentary."""
        forecasts = self._make_forecasts(
            days=20, net_avg=15, net_slope=1.0, confidence='low'
        )
        insights = generate_insights(forecasts)
        messages = [i['message'] for i in insights]
        assert not any('accelerating' in m for m in messages)
        assert not any('steady' in m for m in messages)
