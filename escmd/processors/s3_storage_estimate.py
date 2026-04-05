"""
Estimate rough S3 monthly storage cost from _cat/indices rows (primary size only).

Uses the same rollover date-in-name convention as indices-analyze (YYYY.MM.DD).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from processors.index_processor import IndexProcessor
from processors.index_traffic_analyzer import _parse_index_row

GIB = 1024**3


def _row_pri_store(entry: Dict[str, Any]) -> int:
    raw = entry.get("pri.store.size", 0)
    try:
        return int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        return 0


def estimate_s3_monthly_storage_cost(
    indices: List[Dict[str, Any]],
    *,
    within_days: int = 30,
    buffer_percent: float = 0.0,
    price_per_gib_month_usd: float,
    include_undated: bool = False,
    as_of_date_utc: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Sum pri.store.size for indices whose rollover date in the name falls in the UTC window.

    Args:
        indices: Rows from list_indices_stats (needs 'index', 'pri.store.size').
        within_days: Include indices with rollover date on or after (UTC today - N days).
        buffer_percent: Non-negative; scales bytes by (1 + buffer_percent/100) before cost.
        price_per_gib_month_usd: S3 (or archive) list price per gibibyte-month in USD.
        include_undated: If True, add pri.store.size for indices without rollover date in name.
        as_of_date_utc: Reference "today" for the window (tests); default: UTC now.

    Returns:
        JSON-serializable dict with assumptions, counts, bytes, and cost (including
        cumulative buffered GiB/bytes and USD for months 2–3 vs the one-month slice).
    """
    if price_per_gib_month_usd <= 0:
        raise ValueError("price_per_gib_month_usd must be positive")
    if buffer_percent < 0:
        raise ValueError("buffer_percent must be non-negative")
    if within_days < 0:
        within_days = 0

    today_utc = (
        as_of_date_utc
        if as_of_date_utc is not None
        else datetime.now(timezone.utc).date()
    )
    rollover_cutoff_date = today_utc - timedelta(days=within_days)

    proc = IndexProcessor()
    date_re = proc.date_pattern_regex

    dated_bytes = 0
    matched_dated = 0
    excluded_dated_before_cutoff = 0
    undated_skipped = 0
    undated_bytes_included = 0
    undated_included = 0

    for entry in indices:
        parsed = _parse_index_row(entry, date_re)
        pri = _row_pri_store(entry)
        if not parsed:
            if include_undated:
                undated_bytes_included += pri
                undated_included += 1
            else:
                undated_skipped += 1
            continue
        _base, dt, _suffix, _name = parsed
        idx_day = dt.date()
        if idx_day < rollover_cutoff_date:
            excluded_dated_before_cutoff += 1
            continue
        matched_dated += 1
        dated_bytes += pri

    total_pri_bytes = dated_bytes + undated_bytes_included
    factor = 1.0 + (buffer_percent / 100.0)
    buffered_pri_bytes = int(round(total_pri_bytes * factor))
    buffered_gib = buffered_pri_bytes / GIB
    estimated_month_1_usd = buffered_gib * price_per_gib_month_usd
    # Steady state: same monthly footprint accrues each month → cumulative GiB = M × slice.
    cumulative_gib_m2 = 2.0 * buffered_gib
    cumulative_gib_m3 = 3.0 * buffered_gib
    estimated_month_2_usd = cumulative_gib_m2 * price_per_gib_month_usd
    estimated_month_3_usd = cumulative_gib_m3 * price_per_gib_month_usd

    return {
        "assumptions": {
            "within_days": within_days,
            "buffer_percent": buffer_percent,
            "price_per_gib_month_usd": price_per_gib_month_usd,
            "storage_field": "pri.store.size",
            "date_source": "rollover_date_in_index_name",
            "as_of_date_utc": today_utc.isoformat(),
            "rollover_date_cutoff_utc": rollover_cutoff_date.isoformat(),
            "include_undated": include_undated,
            "multi_month_model": (
                "Months 2–3: cumulative buffered GiB = month_number × one-month slice; "
                "cost = cumulative_gib × price_per_gib_month (steady accrual)."
            ),
            "note": (
                "Sizes are current cluster primary bytes; S3 snapshot size and compression "
                "may differ."
            ),
        },
        "counts": {
            "indices_matched_dated": matched_dated,
            "indices_excluded_dated_before_cutoff": excluded_dated_before_cutoff,
            "indices_undated_skipped": undated_skipped if not include_undated else 0,
            "indices_undated_included": undated_included if include_undated else 0,
        },
        "bytes": {
            "total_pri_dated": dated_bytes,
            "total_pri_undated_included": undated_bytes_included if include_undated else 0,
            "total_pri": total_pri_bytes,
            "buffered_pri": buffered_pri_bytes,
            "cumulative_buffered_pri_month_2": int(round(buffered_pri_bytes * 2)),
            "cumulative_buffered_pri_month_3": int(round(buffered_pri_bytes * 3)),
        },
        "cost": {
            "total_pri_gib": round(total_pri_bytes / GIB, 6),
            "buffered_pri_gib": round(buffered_gib, 6),
            "cumulative_buffered_pri_gib_month_2": round(cumulative_gib_m2, 6),
            "cumulative_buffered_pri_gib_month_3": round(cumulative_gib_m3, 6),
            "estimated_monthly_usd": round(estimated_month_1_usd, 4),
            "estimated_month_1_usd": round(estimated_month_1_usd, 4),
            "estimated_month_2_usd": round(estimated_month_2_usd, 4),
            "estimated_month_3_usd": round(estimated_month_3_usd, 4),
        },
    }
