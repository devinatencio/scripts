"""
Compare each dated rollover index to its siblings using leave-one-out medians.

Uses the same index name shape as IndexProcessor: ...-YYYY.MM.DD-NNNNNN.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from processors.index_processor import IndexProcessor


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0


def _parse_index_row(
    entry: Dict[str, Any], date_re: Any
) -> Optional[Tuple[str, datetime, int, str]]:
    name = entry.get("index") or ""
    match = date_re.match(name)
    if not match:
        return None
    base, date_str, suffix_str = match.group(1), match.group(2), match.group(3)
    try:
        dt = datetime.strptime(date_str, "%Y.%m.%d")
        suffix = int(suffix_str)
    except ValueError:
        return None
    return base, dt, suffix, name


def _row_docs(entry: Dict[str, Any]) -> int:
    raw = entry.get("docs.count", 0)
    try:
        return int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        return 0


def _row_store(entry: Dict[str, Any]) -> int:
    raw = entry.get("store.size", 0)
    try:
        return int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        return 0


def _median_rollover_gap_days(sorted_entries: List[Dict[str, Any]]) -> Optional[float]:
    if len(sorted_entries) < 2:
        return None
    deltas: List[float] = []
    for i in range(1, len(sorted_entries)):
        prev_d = sorted_entries[i - 1]["date"]
        cur_d = sorted_entries[i]["date"]
        deltas.append(float((cur_d - prev_d).days))
    return _median(deltas) if deltas else None


def analyze_index_traffic(
    indices: List[Dict[str, Any]],
    *,
    min_peers: int = 1,
    min_ratio: float = 5.0,
    top: Optional[int] = None,
    within_days: Optional[int] = None,
    as_of_date_utc: Optional[date] = None,
    min_docs: int = 1_000_000,
) -> Dict[str, Any]:
    """
    Flag indices whose doc count (and store size) are high vs. siblings in the same base pattern.

    Args:
        indices: Rows from list_indices_stats (must include 'index', 'docs.count', 'store.size').
        min_peers: Require at least this many *other* indices in the group (baseline pool size).
        min_ratio: Only include rows where docs_ratio >= this (and baseline docs > 0).
        top: If set, keep only the top N rows after sorting by docs_ratio descending.
        within_days: If set, only emit outliers whose rollover date in the index name is on or after
            (UTC today minus this many calendar days). Peers and medians still use the full group.
        as_of_date_utc: If set, use this calendar date as 'today' (UTC) for within_days; otherwise
            the system UTC date. Intended for tests.
        min_docs: Only include outliers with at least this many documents on the index itself.
            Use 0 to disable (ratio-only filtering).

    Returns:
        JSON-serializable dict with 'summary' and 'rows'.
    """
    proc = IndexProcessor()
    date_re = proc.date_pattern_regex

    rollover_cutoff_date: Optional[date] = None
    as_of_utc: Optional[str] = None
    if within_days is not None:
        if within_days < 0:
            within_days = 0
        today_utc = (
            as_of_date_utc
            if as_of_date_utc is not None
            else datetime.now(timezone.utc).date()
        )
        rollover_cutoff_date = today_utc - timedelta(days=within_days)
        as_of_utc = today_utc.isoformat()

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    skipped_no_pattern = 0

    for entry in indices:
        parsed = _parse_index_row(entry, date_re)
        if not parsed:
            skipped_no_pattern += 1
            continue
        base, dt, suffix, name = parsed
        grouped.setdefault(base, []).append(
            {
                "index": name,
                "base_pattern": base,
                "date": dt,
                "suffix": suffix,
                "docs": _row_docs(entry),
                "store": _row_store(entry),
            }
        )

    rows_out: List[Dict[str, Any]] = []
    groups_with_enough_peers = 0

    for base, members in grouped.items():
        sorted_m = sorted(members, key=lambda x: (x["date"], x["suffix"]))
        latest = sorted_m[-1]
        median_gap = _median_rollover_gap_days(sorted_m)

        if len(sorted_m) <= min_peers:
            continue
        groups_with_enough_peers += 1

        for i, m in enumerate(sorted_m):
            peers_docs = [x["docs"] for j, x in enumerate(sorted_m) if j != i]
            peers_store = [x["store"] for j, x in enumerate(sorted_m) if j != i]
            if len(peers_docs) < min_peers:
                continue

            med_docs = _median([float(d) for d in peers_docs])
            med_store = _median([float(s) for s in peers_store])

            if med_docs <= 0:
                continue

            docs_ratio = float(m["docs"]) / med_docs
            store_ratio = (float(m["store"]) / med_store) if med_store > 0 else None

            if docs_ratio < min_ratio:
                continue

            if rollover_cutoff_date is not None:
                idx_day = m["date"].date()
                if idx_day < rollover_cutoff_date:
                    continue

            if min_docs > 0 and m["docs"] < min_docs:
                continue

            prev_date: Optional[datetime] = None
            if i > 0:
                prev_date = sorted_m[i - 1]["date"]
            days_since_prev = (
                float((m["date"] - prev_date).days) if prev_date is not None else None
            )

            rows_out.append(
                {
                    "base_pattern": base,
                    "index": m["index"],
                    "rollover_date": m["date"].strftime("%Y.%m.%d"),
                    "generation": m["suffix"],
                    "docs": m["docs"],
                    "peer_median_docs": int(round(med_docs)),
                    "docs_ratio": round(docs_ratio, 3),
                    "store_size_bytes": m["store"],
                    "peer_median_store_bytes": int(round(med_store)),
                    "store_ratio": round(store_ratio, 3) if store_ratio is not None else None,
                    "is_latest_generation": m["index"] == latest["index"],
                    "group_backing_index_count": len(sorted_m),
                    "median_days_between_rollovers": round(median_gap, 2)
                    if median_gap is not None
                    else None,
                    "days_since_previous_generation": int(days_since_prev)
                    if days_since_prev is not None
                    else None,
                }
            )

    rows_out.sort(key=lambda r: r["docs_ratio"], reverse=True)
    if top is not None and top > 0:
        rows_out = rows_out[:top]

    summary: Dict[str, Any] = {
        "indices_input": len(indices),
        "skipped_no_date_pattern": skipped_no_pattern,
        "rollover_groups": len(grouped),
        "groups_with_enough_peers": groups_with_enough_peers,
        "flagged_rows": len(rows_out),
        "min_docs": min_docs,
    }
    if within_days is not None:
        summary["within_days"] = within_days
        summary["as_of_date_utc"] = as_of_utc
        summary["rollover_date_cutoff_utc"] = rollover_cutoff_date.isoformat()

    return {"summary": summary, "rows": rows_out}
