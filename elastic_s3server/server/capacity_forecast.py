"""
capacity_forecast.py - Activity volume forecasting from historical metrics.

Analyses daily_history data to compute linear trends and project future
snapshot creation/deletion volumes and net growth rates.  Uses simple
linear regression (no external dependencies) to fit trend lines and
extrapolate forward 30, 60, and 90 days.  All math is Python 3.6
compatible.

Note: This module forecasts operational *counts* (how many snapshots
are created, deleted, etc.) — not storage sizes.  It answers "is
retention keeping up with creation?" rather than "how many GB will
we use?"
"""

import datetime

from typing import List, Tuple, Optional  # noqa: F401


def _linear_regression(xs, ys):
    # type: (List[float], List[float]) -> Tuple[float, float]
    """Compute slope and intercept via ordinary least squares.

    Args:
        xs: Independent variable values (e.g. day offsets 0, 1, 2 ...).
        ys: Dependent variable values.

    Returns:
        Tuple of (slope, intercept).  Returns (0.0, 0.0) when fewer
        than 2 data points are provided.
    """
    n = len(xs)
    if n < 2:
        return (0.0, 0.0)

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return (0.0, sum_y / n if n else 0.0)

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return (slope, intercept)


def _r_squared(xs, ys, slope, intercept):
    # type: (List[float], List[float], float, float) -> float
    """Compute R-squared (coefficient of determination).

    Args:
        xs: Independent variable values.
        ys: Dependent variable values.
        slope: Regression slope.
        intercept: Regression intercept.

    Returns:
        R-squared value between 0.0 and 1.0.  Returns 0.0 when
        variance is zero or data is insufficient.
    """
    n = len(ys)
    if n < 2:
        return 0.0

    mean_y = sum(ys) / n
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    if ss_tot == 0:
        return 1.0  # perfect fit when all values are identical

    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    return max(0.0, 1.0 - ss_res / ss_tot)


def _weekly_averages(values, dates):
    # type: (List[float], List[str]) -> List[Tuple[str, float]]
    """Group daily values into ISO-week averages.

    Args:
        values: Daily metric values aligned with *dates*.
        dates: YYYY-MM-DD date strings.

    Returns:
        List of (week_label, average) tuples sorted chronologically.
        Week labels are ``'YYYY-Www'`` strings.
    """
    weeks = {}  # type: dict
    for val, date_str in zip(values, dates):
        try:
            dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            iso = dt.isocalendar()
            week_key = '%04d-W%02d' % (iso[0], iso[1])
        except (ValueError, TypeError):
            continue
        weeks.setdefault(week_key, []).append(val)

    result = []
    for wk in sorted(weeks):
        vals = weeks[wk]
        result.append((wk, sum(vals) / len(vals)))
    return result


def compute_forecast(history, counter_key):
    # type: (list, str) -> dict
    """Compute a linear forecast for a single counter.

    Args:
        history: List of daily_history entry dicts, each containing
            ``'date'`` and the named counter key.
        counter_key: Key to forecast (e.g. ``'snapshots_created'``).

    Returns:
        Dict with forecast data::

            {
                'counter': str,
                'data_points': int,
                'slope_per_day': float,
                'intercept': float,
                'r_squared': float,
                'current_avg': float,
                'weekly_trend': list of (week_label, avg),
                'wow_change_pct': float or None,
                'projections': {30: float, 60: float, 90: float},
                'cumulative_projections': {30: float, 60: float, 90: float},
                'confidence': str,  # 'high', 'medium', 'low'
            }

        Returns a dict with ``data_points=0`` when history is empty.
    """
    if not history:
        return {
            'counter': counter_key,
            'data_points': 0,
            'slope_per_day': 0.0,
            'intercept': 0.0,
            'r_squared': 0.0,
            'current_avg': 0.0,
            'weekly_trend': [],
            'wow_change_pct': None,
            'projections': {30: 0.0, 60: 0.0, 90: 0.0},
            'cumulative_projections': {30: 0.0, 60: 0.0, 90: 0.0},
            'confidence': 'low',
        }

    dates = [e.get('date', '') for e in history]
    values = [float(e.get(counter_key, 0)) for e in history]
    n = len(values)

    xs = list(range(n))
    ys = values

    slope, intercept = _linear_regression(
        [float(x) for x in xs], ys
    )
    r2 = _r_squared([float(x) for x in xs], ys, slope, intercept)

    current_avg = sum(values) / n if n else 0.0

    # Weekly averages and week-over-week change
    weekly = _weekly_averages(values, dates)
    wow_pct = None  # type: Optional[float]
    if len(weekly) >= 2:
        prev_avg = weekly[-2][1]
        curr_avg = weekly[-1][1]
        if prev_avg > 0:
            wow_pct = ((curr_avg - prev_avg) / prev_avg) * 100.0

    # Projections: predicted daily rate at day N, and cumulative sum
    projections = {}
    cumulative = {}
    for horizon in (30, 60, 90):
        future_day = n + horizon
        predicted_daily = max(0.0, slope * future_day + intercept)
        projections[horizon] = round(predicted_daily, 1)

        # Cumulative = sum of predicted values from day n to n+horizon
        cum = 0.0
        for d in range(horizon):
            cum += max(0.0, slope * (n + d) + intercept)
        cumulative[horizon] = round(cum, 0)

    # Confidence based on data points and R-squared
    if n >= 30 and r2 >= 0.5:
        confidence = 'high'
    elif n >= 14 and r2 >= 0.3:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'counter': counter_key,
        'data_points': n,
        'slope_per_day': round(slope, 4),
        'intercept': round(intercept, 2),
        'r_squared': round(r2, 4),
        'current_avg': round(current_avg, 2),
        'weekly_trend': weekly,
        'wow_change_pct': round(wow_pct, 1) if wow_pct is not None else None,
        'projections': projections,
        'cumulative_projections': cumulative,
        'confidence': confidence,
    }


def compute_net_growth_forecast(history):
    # type: (list) -> dict
    """Compute net snapshot growth (created minus deleted) forecast.

    This is the key capacity metric: how fast is the repository growing?

    Args:
        history: List of daily_history entry dicts.

    Returns:
        Dict with the same structure as ``compute_forecast`` but for
        the derived ``net_growth`` metric (snapshots_created minus
        snapshots_deleted per day).
    """
    if not history:
        return compute_forecast([], 'net_growth')

    # Build synthetic history with net_growth values
    net_history = []
    for entry in history:
        created = entry.get('snapshots_created', 0)
        deleted = entry.get('snapshots_deleted', 0)
        net_history.append({
            'date': entry.get('date', ''),
            'net_growth': created - deleted,
        })

    return compute_forecast(net_history, 'net_growth')


def compute_all_forecasts(metrics_data):
    # type: (dict) -> dict
    """Compute forecasts for all counters plus net growth.

    Merges today's live counters into the history before forecasting.

    Args:
        metrics_data: Full metrics dict from ``read_metrics``.

    Returns:
        Dict mapping counter names to their forecast dicts::

            {
                'snapshots_created': {...},
                'snapshots_deleted': {...},
                'indices_deleted_ilm': {...},
                'net_growth': {...},
            }
    """
    history = list(metrics_data.get('daily_history', []))

    # Merge today's live counters
    today_counters = metrics_data.get('daily_counters', {})
    if today_counters.get('date'):
        existing_dates = {e.get('date') for e in history}
        if today_counters['date'] not in existing_dates:
            history.append({
                'date': today_counters['date'],
                'snapshots_created': today_counters.get('snapshots_created', 0),
                'snapshots_deleted': today_counters.get('snapshots_deleted', 0),
                'indices_deleted_ilm': today_counters.get('indices_deleted_ilm', 0),
            })

    history.sort(key=lambda e: e.get('date', ''))

    return {
        'snapshots_created': compute_forecast(history, 'snapshots_created'),
        'snapshots_deleted': compute_forecast(history, 'snapshots_deleted'),
        'indices_deleted_ilm': compute_forecast(history, 'indices_deleted_ilm'),
        'net_growth': compute_net_growth_forecast(history),
    }


def generate_insights(forecasts):
    # type: (dict) -> list
    """Produce plain-English actionable insights from forecast data.

    Examines the forecast dict (output of ``compute_all_forecasts``)
    and returns a list of insight dicts, each with:

    - ``level``: ``'info'``, ``'warning'``, or ``'critical'``
    - ``message``: Human-readable sentence describing the finding.

    The function is deliberately conservative: when data is sparse or
    confidence is low it says so plainly rather than speculating.

    Args:
        forecasts: Dict from ``compute_all_forecasts``.

    Returns:
        List of insight dicts sorted by severity (critical first).
    """
    insights = []  # type: list
    net = forecasts.get('net_growth', {})
    created = forecasts.get('snapshots_created', {})
    deleted = forecasts.get('snapshots_deleted', {})
    ilm = forecasts.get('indices_deleted_ilm', {})

    data_points = net.get('data_points', 0)
    confidence = net.get('confidence', 'low')

    # --- Data sufficiency check (always first) ---
    if data_points == 0:
        insights.append({
            'level': 'info',
            'message': (
                'No historical data yet. Forecasts will become available '
                'after the utilities have been running for a few days.'
            ),
        })
        return insights

    if data_points < 7:
        insights.append({
            'level': 'info',
            'message': (
                'Only %d day(s) of data collected so far. '
                'Trends need at least 2 weeks to be meaningful \u2014 '
                'treat all projections as rough estimates for now.'
            ) % data_points,
        })
    elif data_points < 14:
        insights.append({
            'level': 'info',
            'message': (
                '%d days of data collected. Trends are starting to form '
                'but another week or two will improve accuracy.'
            ) % data_points,
        })
    elif confidence == 'low':
        insights.append({
            'level': 'info',
            'message': (
                '%d days of data but the pattern is noisy (R\u00b2 %.2f). '
                'Daily volumes vary a lot, so projections are rough.'
            ) % (data_points, net.get('r_squared', 0.0)),
        })

    # --- Net growth direction ---
    net_avg = net.get('current_avg', 0.0)
    net_slope = net.get('slope_per_day', 0.0)
    net_cum_90 = net.get('cumulative_projections', {}).get(90, 0)

    if confidence != 'low':
        if net_avg > 0 and net_slope > 0.5:
            insights.append({
                'level': 'warning',
                'message': (
                    'Repository is growing and accelerating '
                    '(+%.1f snapshots/day, trending upward). '
                    'At this pace, ~%.0f net new snapshots in 90 days. '
                    'Consider tightening retention policies or adding storage.'
                ) % (net_avg, net_cum_90),
            })
        elif net_avg > 0 and net_slope <= 0.5:
            insights.append({
                'level': 'info',
                'message': (
                    'Repository is growing at a steady +%.1f snapshots/day. '
                    'Projected ~%.0f net new snapshots in 90 days.'
                ) % (net_avg, net_cum_90),
            })
        elif net_avg < 0:
            insights.append({
                'level': 'info',
                'message': (
                    'Repository is shrinking (%.1f snapshots/day net). '
                    'Retention is outpacing creation \u2014 snapshot count '
                    'is decreasing.'
                ) % net_avg,
            })
        else:
            insights.append({
                'level': 'info',
                'message': (
                    'Repository size is roughly stable. '
                    'Creation and deletion rates are balanced.'
                ),
            })

    # --- Week-over-week spike detection ---
    net_wow = net.get('wow_change_pct')
    if net_wow is not None and confidence != 'low':
        if net_wow > 50:
            insights.append({
                'level': 'warning',
                'message': (
                    'Net growth jumped %.1f%% week-over-week. '
                    'Could be a burst of new indices or a retention job '
                    'that didn\'t run. Worth investigating.'
                ) % net_wow,
            })
        elif net_wow < -50:
            insights.append({
                'level': 'info',
                'message': (
                    'Net growth dropped %.1f%% week-over-week. '
                    'Likely a large retention cleanup ran recently.'
                ) % abs(net_wow),
            })

    # --- Creation vs deletion imbalance ---
    created_avg = created.get('current_avg', 0.0)
    deleted_avg = deleted.get('current_avg', 0.0)
    if created_avg > 0 and confidence != 'low':
        ratio = deleted_avg / created_avg if created_avg > 0 else 0
        if ratio < 0.3:
            insights.append({
                'level': 'warning',
                'message': (
                    'Deletion rate (%.1f/day) is well below creation rate '
                    '(%.1f/day). Only %.0f%% of created snapshots are being '
                    'cleaned up. Review retention policies.'
                ) % (deleted_avg, created_avg, ratio * 100),
            })
        elif ratio > 1.5:
            insights.append({
                'level': 'info',
                'message': (
                    'Deleting more snapshots (%.1f/day) than creating '
                    '(%.1f/day). Repository is being drawn down \u2014 '
                    'verify this is intentional.'
                ) % (deleted_avg, created_avg),
            })

    # --- ILM curator activity ---
    ilm_avg = ilm.get('current_avg', 0.0)
    if ilm_avg == 0 and data_points >= 7 and created_avg > 0:
        insights.append({
            'level': 'info',
            'message': (
                'ILM curator has not deleted any indices in the tracked '
                'period. If cold indices exist, check that the curator '
                'is running and the hours_delay setting is appropriate.'
            ),
        })
    elif ilm_avg > 0 and created_avg > 0 and ilm_avg > created_avg * 1.5:
        insights.append({
            'level': 'warning',
            'message': (
                'ILM curator is deleting indices (%.1f/day) faster than '
                'new snapshots are being created (%.1f/day). Indices may '
                'be deleted before they\'re backed up.'
            ) % (ilm_avg, created_avg),
        })

    # --- Sort by severity ---
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    insights.sort(key=lambda i: severity_order.get(i['level'], 9))

    return insights
