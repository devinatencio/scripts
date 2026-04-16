"""
Index stats sampling and trend analysis for indices-watch-collect / indices-watch-report.

Stores JSON snapshots under ~/.escmd/index-watch/<cluster>/<YYYY-MM-DD>/ (override with
ESCMD_INDEX_WATCH_DIR or --output-dir / --dir).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from processors.index_processor import IndexProcessor
from processors.index_traffic_analyzer import _median, _parse_index_row

SCHEMA_VERSION = 1
RUN_META_FILENAME = "run.json"


def sanitize_cluster_slug(name: str) -> str:
    """Filesystem-safe cluster / location label."""
    if not name or not str(name).strip():
        return "unknown"
    s = str(name).strip()
    s = re.sub(r'[<>:"/\\|?*]+', "_", s)
    s = s.replace(" ", "_")
    return s[:200] if len(s) > 200 else s


def default_watch_base_dir() -> Path:
    env = os.environ.get("ESCMD_INDEX_WATCH_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".escmd" / "index-watch"


def utc_today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def default_run_dir(cluster_slug: str, day_iso: str) -> Path:
    return default_watch_base_dir() / sanitize_cluster_slug(cluster_slug) / day_iso


def sanitize_session_label(label: str) -> str:
    """Replace any character not in [a-zA-Z0-9_-] with '_', truncate to 40 chars."""
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', label)
    return sanitized[:40]


def make_session_id(dt: datetime, label: Optional[str] = None) -> str:
    """Return 'HHMM' or 'HHMM-<sanitized_label>' for the given UTC datetime."""
    hhmm = dt.strftime("%H%M")
    if label is not None:
        sanitized = sanitize_session_label(label)
        if sanitized:
            return f"{hhmm}-{sanitized}"
    return hhmm


def resolve_session_dir(
    cluster_slug: str,
    day_iso: str,
    *,
    label: Optional[str] = None,
    dt: Optional[datetime] = None,
) -> Path:
    """Compute a non-conflicting session directory path under default_run_dir().

    Uses datetime.now(timezone.utc) if dt is None. Appends -2, -3, … if the
    computed path already exists on disk. Does NOT create the directory.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    session_id = make_session_id(dt, label)
    base = default_run_dir(cluster_slug, day_iso)
    candidate = base / session_id
    if not candidate.exists():
        return candidate
    suffix = 2
    while True:
        candidate = base / f"{session_id}-{suffix}"
        if not candidate.exists():
            return candidate
        suffix += 1


@dataclass
class SessionInfo:
    session_id: str
    session_dir: Path
    started_at: str
    label: Optional[str]
    sample_count: int
    schema_version: int


def list_sessions(date_dir: Path) -> List[SessionInfo]:
    """Scan date_dir for subdirectories containing a valid v2 run.json.

    Returns SessionInfo objects sorted ascending by started_at.
    Returns [] if date_dir does not exist.
    """
    if not date_dir.is_dir():
        return []
    sessions: List[SessionInfo] = []
    for subdir in date_dir.iterdir():
        if not subdir.is_dir():
            continue
        run_json = subdir / RUN_META_FILENAME
        if not run_json.is_file():
            continue
        try:
            with open(run_json, encoding="utf-8") as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(meta, dict):
            continue
        if meta.get("schema_version") != 2:
            continue
        started_at = meta.get("started_at", "")
        label = meta.get("label") or None
        sample_count = sum(
            1 for p in subdir.iterdir() if p.is_file() and _is_sample_file(p)
        )
        sessions.append(
            SessionInfo(
                session_id=str(subdir.name),
                session_dir=subdir,
                started_at=str(started_at),
                label=label,
                sample_count=sample_count,
                schema_version=2,
            )
        )
    sessions.sort(key=lambda s: s.started_at)
    return sessions


def is_legacy_date_dir(date_dir: Path) -> bool:
    """Return True if date_dir contains flat .json sample files but no valid v2 sessions."""
    if not date_dir.is_dir():
        return False
    has_flat_samples = any(
        p.is_file() and _is_sample_file(p) for p in date_dir.iterdir()
    )
    if not has_flat_samples:
        return False
    return len(list_sessions(date_dir)) == 0


def format_session_list(sessions: List[SessionInfo]) -> str:
    """Return a human-readable numbered list of sessions.

    Each line shows: number, session_id, start time (HH:MM UTC), sample count, label (or —).
    """
    lines: List[str] = []
    for i, s in enumerate(sessions, start=1):
        # Parse ISO-8601 started_at to extract HH:MM UTC
        try:
            dt = datetime.fromisoformat(s.started_at.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M") + " UTC"
        except (ValueError, AttributeError):
            time_str = s.started_at
        label_str = s.label if s.label is not None else "\u2014"
        lines.append(
            f"  {i}. {s.session_id}  started {time_str}  {s.sample_count} samples  label: {label_str}"
        )
    return "\n".join(lines)


def pick_or_create_session_dir(
    cluster_slug: str,
    day_iso: str,
    *,
    new_session: bool = False,
    join_latest: bool = False,
    label: Optional[str] = None,
    console: Any = None,
    is_tty: bool = True,
) -> Tuple[Path, bool]:
    """Central session-resolution helper.

    Returns (session_dir, is_new) where is_new=True means a fresh session was
    created (caller must write run.json), is_new=False means joining an existing
    session (caller must NOT write run.json).
    """

    def _print(msg: str) -> None:
        if console is not None:
            console.print(msg)
        else:
            print(msg)

    # 1. --new-session takes precedence over everything
    if new_session:
        return resolve_session_dir(cluster_slug, day_iso, label=label), True

    # 2. Build date_dir and list sessions
    date_dir = default_run_dir(cluster_slug, day_iso)
    sessions = list_sessions(date_dir)

    # 4. --join-latest with sessions present
    if join_latest and sessions:
        return sessions[-1].session_dir, False

    # 5. --join-latest with no sessions
    if join_latest and not sessions:
        return resolve_session_dir(cluster_slug, day_iso, label=label), True

    # 6. No sessions and not a legacy dir → create new
    if not sessions and not is_legacy_date_dir(date_dir):
        return resolve_session_dir(cluster_slug, day_iso, label=label), True

    # 7. Legacy flat directory
    if is_legacy_date_dir(date_dir):
        if not is_tty:
            print(
                "[indices-watch] Non-interactive: starting new session in legacy date directory",
                file=sys.stderr,
            )
            return resolve_session_dir(cluster_slug, day_iso, label=label), True
        # TTY: show picker with legacy option + new session
        _print("  1. legacy (continue appending to date directory)")
        _print("  2. (Create new session)")
        n_options = 2
        while True:
            try:
                choice = int(input(f"Select session [1-{n_options}]: ").strip())
            except (ValueError, EOFError):
                continue
            if choice == 1:
                return date_dir, False
            if choice == 2:
                return resolve_session_dir(cluster_slug, day_iso, label=label), True

    # 8. Sessions exist (non-empty, not legacy)
    if not is_tty:
        selected = sessions[-1]
        print(
            f"[indices-watch] Non-interactive: joining latest session {selected.session_id}",
            file=sys.stderr,
        )
        return selected.session_dir, False

    # TTY: show picker
    _print(format_session_list(sessions))
    n = len(sessions)
    _print(f"  {n + 1}. (Create new session)")
    while True:
        try:
            choice = int(input(f"Select session [1-{n + 1}]: ").strip())
        except (ValueError, EOFError):
            continue
        if 1 <= choice <= n:
            return sessions[choice - 1].session_dir, False
        if choice == n + 1:
            return resolve_session_dir(cluster_slug, day_iso, label=label), True


def _raw_index_watch_location_slug(args: Any, config_manager: Any) -> str:
    loc = getattr(args, "locations", None)
    if loc and str(loc).strip():
        return str(loc).strip()
    cluster = getattr(args, "cluster", None)
    if cluster and str(cluster).strip():
        return str(cluster).strip()
    dc = config_manager.get_default_cluster()
    if dc and str(dc).strip():
        return str(dc).strip()
    return "default"


def index_watch_storage_slug(raw_slug: str, config_manager: Any) -> str:
    """Canonical servers_dict key when resolvable; else a filesystem-safe raw slug."""
    if not raw_slug or not str(raw_slug).strip():
        return "unknown"
    raw = str(raw_slug).strip()
    canonical = config_manager.canonical_cluster_name_for_location(raw)
    if canonical:
        return canonical
    return sanitize_cluster_slug(raw)


def resolve_cluster_slug(args: Any, config_manager: Any) -> str:
    """Slug used for index-watch paths; normalized to config key when possible."""
    return index_watch_storage_slug(
        _raw_index_watch_location_slug(args, config_manager), config_manager
    )


def _index_watch_sample_dir_candidates(raw: str, config_manager: Any) -> List[str]:
    """Ordered directory slugs to try under index-watch (canonical, legacy short name, aliases)."""
    primary = index_watch_storage_slug(raw, config_manager)
    ordered: List[str] = []

    def add(s: Optional[str]) -> None:
        if s and str(s).strip() and s not in ordered:
            ordered.append(s)

    add(primary)
    add(sanitize_cluster_slug(raw))
    if "-" in primary:
        add(primary.rsplit("-", 1)[0])
    server_config = config_manager.get_server_config(raw)
    if not server_config:
        server_config = config_manager.get_server_config(primary)
    if server_config:
        for name, cfg in config_manager.servers_dict.items():
            if cfg == server_config:
                add(name)
    return ordered


def resolve_default_watch_sample_dir(
    args: Any, config_manager: Any, day_iso: str
) -> Tuple[Path, List[Dict[str, Any]]]:
    """
    Default sample directory when --dir is not set.

    Prefer the canonical config key directory, then legacy paths (short -l slug,
    hyphen prefix of the canonical name, or other servers_dict keys for the same
    host config) so reports still find samples from older escmd versions.
    """
    raw = _raw_index_watch_location_slug(args, config_manager)
    slug_order = _index_watch_sample_dir_candidates(raw, config_manager)
    chosen: Optional[Path] = None
    samples: List[Dict[str, Any]] = []
    for slug in slug_order:
        d = default_run_dir(slug, day_iso)
        samples = load_samples(d)
        if samples:
            chosen = d
            break
    if chosen is None:
        chosen = default_run_dir(slug_order[0], day_iso)
        samples = load_samples(chosen)
    return chosen, samples


def write_run_metadata(
    out_dir: Path,
    *,
    cluster: str,
    interval_seconds: int,
    duration_seconds: Optional[int],
    pattern: Optional[str],
    status: Optional[str],
    session_id: Optional[str] = None,
    label: Optional[str] = None,
) -> None:
    if session_id is not None:
        meta: Dict[str, Any] = {
            "kind": "indices-watch-run",
            "schema_version": 2,
            "cluster": cluster,
            "session_id": session_id,
            "label": label,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "interval_seconds": interval_seconds,
            "duration_seconds": duration_seconds,
            "pattern": pattern,
            "status": status,
        }
    else:
        meta = {
            "kind": "indices-watch-run",
            "schema_version": SCHEMA_VERSION,
            "cluster": cluster,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "interval_seconds": interval_seconds,
            "duration_seconds": duration_seconds,
            "pattern": pattern,
            "status": status,
        }
    p = out_dir / RUN_META_FILENAME
    with open(p, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def save_sample_file(
    out_dir: Path,
    *,
    cluster: str,
    indices: List[Dict[str, Any]],
    captured_at: datetime,
    host_used: Optional[str],
    sequence: int,
    nodes_stats: Optional[Dict[str, Any]] = None,
    cluster_health: Optional[Dict[str, Any]] = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = captured_at.strftime("%Y%m%dT%H%M%S")
    fname = f"{ts}_{sequence:04d}.json"
    path = out_dir / fname
    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at.isoformat(),
        "cluster": cluster,
        "host_used": host_used,
        "indices": indices,
    }
    if nodes_stats is not None:
        payload["nodes_stats"] = nodes_stats
    if cluster_health is not None:
        payload["cluster_health"] = cluster_health
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def _is_sample_file(path: Path) -> bool:
    if path.name == RUN_META_FILENAME:
        return False
    return path.suffix.lower() == ".json"


def load_samples(sample_dir: Path) -> List[Dict[str, Any]]:
    if not sample_dir.is_dir():
        return []
    files = sorted(p for p in sample_dir.iterdir() if p.is_file() and _is_sample_file(p))
    samples: List[Dict[str, Any]] = []
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "indices" not in data:
                continue
            cap = data.get("captured_at")
            if not cap:
                continue
            samples.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    def sort_key(d: Dict[str, Any]) -> str:
        return str(d.get("captured_at", ""))

    samples.sort(key=sort_key)
    return samples


def _index_map(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        name = r.get("index")
        if name:
            out[str(name)] = r
    return out


def _parse_ts(iso_s: str) -> Optional[datetime]:
    if not iso_s:
        return None
    try:
        s = str(iso_s).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _linear_quantile(sorted_vals: List[float], q: float) -> float:
    """Linear interpolation quantile; q in [0, 1]."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    q = max(0.0, min(1.0, float(q)))
    pos = (n - 1) * q
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    w = pos - lo
    return sorted_vals[lo] * (1.0 - w) + sorted_vals[hi] * w


def _interval_docs_rates_per_index(samples: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    """For each adjacent sample pair, docs/s for indices present in both."""
    by_index: Dict[str, List[float]] = {}
    for i in range(len(samples) - 1):
        a = samples[i]
        b = samples[i + 1]
        t0 = _parse_ts(str(a.get("captured_at", "")))
        t1 = _parse_ts(str(b.get("captured_at", "")))
        if not t0 or not t1:
            continue
        elapsed = (t1 - t0).total_seconds()
        if elapsed <= 0:
            elapsed = 1.0
        m0 = _index_map(a.get("indices") or [])
        m1 = _index_map(b.get("indices") or [])
        for name in sorted(set(m0.keys()) & set(m1.keys())):
            rate = float(_row_docs(m1[name]) - _row_docs(m0[name])) / elapsed
            by_index.setdefault(str(name), []).append(rate)
    return by_index


def _interval_rate_summary(rates: List[float]) -> Dict[str, Any]:
    if not rates:
        return {
            "docs_per_sec_interval_median": None,
            "docs_per_sec_interval_p90": None,
            "docs_per_sec_interval_max": None,
            "interval_rate_count": 0,
        }
    s = sorted(rates)
    return {
        "docs_per_sec_interval_median": round(_linear_quantile(s, 0.5), 6),
        "docs_per_sec_interval_p90": round(_linear_quantile(s, 0.9), 6),
        "docs_per_sec_interval_max": round(float(s[-1]), 6),
        "interval_rate_count": len(rates),
    }


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


def format_doc_count_compact(n: Optional[int]) -> str:
    """Compact doc count for table cells (e.g. 150.25M)."""
    if n is None:
        return "—"
    x = float(abs(int(n)))
    neg = int(n) < 0
    sign = "-" if neg else ""
    if x >= 1_000_000_000:
        return f"{sign}{x / 1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"{sign}{x / 1_000_000:.2f}M"
    if x >= 10_000:
        return f"{sign}{x / 1_000:.2f}K"
    return f"{sign}{int(x):,}"


def analyze_watch_trends(
    samples: List[Dict[str, Any]],
    *,
    min_docs_delta: int = 0,
    hot_ratio: float = 2.0,
    min_peers: int = 1,
    docs_peer_ratio: float = 5.0,
    rate_stats: str = "auto",
) -> Dict[str, Any]:
    """
    Compare last sample to first; compute deltas and optional HOT vs rollover-group median rate.

    Indices with no document count change (delta_docs == 0) are omitted from rows.
    Peer median for vs peer / HOT still includes those siblings (docs/s = 0) when they
    exist in both samples and share the same rollover base pattern.

    Also compares last-sample doc count to leave-one-out median doc count among siblings
    (same idea as indices-analyze) via peer_median_docs_count and docs_vs_peer_docs_ratio.

    Per-interval docs/s (adjacent samples) yields median / p90 / max when multiple
    intervals exist. rate_stats: \"auto\" uses interval-primary display when len(samples)>=3,
    \"span\" keeps a single full-window docs/s column, \"intervals\" always uses med/p90/max.
    HOT and rate/med still use full-span docs/s.
    """
    if len(samples) < 2:
        return {
            "summary": {
                "error": "need_at_least_two_samples",
                "sample_count": len(samples),
            },
            "rows": [],
        }

    first = samples[0]
    last = samples[-1]
    t0 = _parse_ts(str(first.get("captured_at", "")))
    t1 = _parse_ts(str(last.get("captured_at", "")))
    if not t0 or not t1:
        return {
            "summary": {"error": "invalid_timestamps", "sample_count": len(samples)},
            "rows": [],
        }

    elapsed = (t1 - t0).total_seconds()
    if elapsed <= 0:
        elapsed = 1.0

    rs = str(rate_stats or "auto").strip().lower()
    if rs not in ("auto", "span", "intervals"):
        rs = "auto"
    use_interval_primary = rs == "intervals" or (rs == "auto" and len(samples) >= 3)

    interval_rates_by_index = _interval_docs_rates_per_index(samples)

    m0 = _index_map(first.get("indices") or [])
    m1 = _index_map(last.get("indices") or [])
    # Include indices present in both samples plus indices that are new (only in last sample).
    # New indices are treated as having 0 docs/store in the first sample.
    common = sorted(set(m0.keys()) & set(m1.keys()))
    new_indices = sorted(set(m1.keys()) - set(m0.keys()))
    all_last_indices = sorted(set(m1.keys()))

    proc = IndexProcessor()
    date_re = proc.date_pattern_regex

    # docs/s for every index in the last sample — peer baseline
    # For new indices (not in m0), baseline starts at 0
    docs_per_sec_all: Dict[str, float] = {}
    for name in all_last_indices:
        d0 = _row_docs(m0[name]) if name in m0 else 0
        d1 = _row_docs(m1[name])
        docs_per_sec_all[name] = float(d1 - d0) / elapsed

    # Rollover series membership: all last-sample indices, not only rows we will print
    base_to_names: Dict[str, List[str]] = {}
    index_to_base: Dict[str, Optional[str]] = {}
    for name in all_last_indices:
        parsed = _parse_index_row(
            {"index": name, "docs.count": 0, "store.size": 0}, date_re
        )
        if not parsed:
            index_to_base[name] = None
            continue
        base, _dt, _suf, _nm = parsed
        index_to_base[name] = base
        base_to_names.setdefault(base, []).append(name)

    raw_rows: List[Dict[str, Any]] = []
    for name in all_last_indices:
        d0 = _row_docs(m0[name]) if name in m0 else 0
        d1 = _row_docs(m1[name])
        s0 = _row_store(m0[name]) if name in m0 else 0
        s1 = _row_store(m1[name])
        delta_docs = d1 - d0
        delta_store = s1 - s0
        if delta_docs == 0:
            continue
        if delta_docs < min_docs_delta:
            continue
        docs_per_sec = docs_per_sec_all[name]
        store_per_sec = float(delta_store) / elapsed
        raw_rows.append(
            {
                "index": name,
                "delta_docs": delta_docs,
                "delta_store_bytes": delta_store,
                "docs_per_sec": docs_per_sec,
                "store_per_sec": store_per_sec,
                "docs_end": d1,
                "store_end": s1,
            }
        )

    for row in raw_rows:
        name = row["index"]
        base = index_to_base.get(name)
        row["base_pattern"] = base
        row["peer_median_docs_count"] = None
        row["docs_vs_peer_docs_ratio"] = None
        row["docs_level_elevated"] = False
        if base is None:
            row["peer_median_docs_per_sec"] = None
            row["hot"] = False
            row["hot_reason"] = "no_rollover_pattern"
            row["rate_vs_peer_median"] = None
            continue

        peer_names = [n for n in base_to_names.get(base, []) if n != name]
        pr = [docs_per_sec_all[n] for n in peer_names]
        med = _median(pr) if pr else 0.0
        row["peer_median_docs_per_sec"] = med

        if len(peer_names) >= min_peers:
            peer_doc_vals = [float(_row_docs(m1[n])) for n in peer_names]
            med_docs = _median(peer_doc_vals) if peer_doc_vals else 0.0
            if med_docs > 0:
                row["peer_median_docs_count"] = int(round(med_docs))
                my_docs = float(row["docs_end"])
                dratio = my_docs / med_docs
                row["docs_vs_peer_docs_ratio"] = round(dratio, 3)
                if docs_peer_ratio > 0 and dratio >= docs_peer_ratio:
                    row["docs_level_elevated"] = True

        if len(pr) < min_peers:
            row["hot"] = False
            row["hot_reason"] = "not_enough_peers"
            row["rate_vs_peer_median"] = None
            continue
        if med <= 0:
            row["hot"] = False
            row["hot_reason"] = "zero_median"
            row["rate_vs_peer_median"] = None
            continue
        ratio = float(row["docs_per_sec"]) / med
        row["hot"] = ratio >= hot_ratio
        row["hot_reason"] = None
        row["rate_vs_peer_median"] = round(ratio, 3)

    for row in raw_rows:
        name = str(row["index"])
        ir = _interval_rate_summary(interval_rates_by_index.get(name, []))
        row.update(ir)

    def _sort_key(r: Dict[str, Any]) -> float:
        if use_interval_primary:
            med = r.get("docs_per_sec_interval_median")
            if med is not None:
                return float(med)
        return float(r.get("docs_per_sec", 0.0))

    raw_rows.sort(key=_sort_key, reverse=True)

    summary = {
        "sample_count": len(samples),
        "first_captured_at": first.get("captured_at"),
        "last_captured_at": last.get("captured_at"),
        "elapsed_seconds": round(elapsed, 3),
        "interval_count": max(0, len(samples) - 1),
        "indices_compared": len(all_last_indices),
        "new_indices": len(new_indices),
        "rows_shown": len(raw_rows),
        "min_docs_delta": min_docs_delta,
        "hot_ratio": hot_ratio,
        "min_peers": min_peers,
        "docs_peer_ratio": docs_peer_ratio,
        "rate_stats": rs,
        "rate_stats_primary": "intervals" if use_interval_primary else "span",
    }

    return {"summary": summary, "rows": raw_rows}


def list_indices_stats_with_failover(
    es_client: Any,
    *,
    pattern: Optional[str],
    status: Optional[str],
    retries_per_host: int,
    retry_delay_sec: float,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Try host1, host2, host3 (deduped); retry per host. Returns (indices, host_used).
    Mutates es_client.es to the working connection.
    """
    hosts: List[str] = []
    seen = set()
    for h in (
        getattr(es_client, "host1", None),
        getattr(es_client, "host2", None),
        getattr(es_client, "host3", None),
    ):
        if not h or h in seen:
            continue
        seen.add(h)
        hosts.append(h)

    if not hosts:
        return [], None

    last_err: Optional[Exception] = None
    for host in hosts:
        for _attempt in range(max(1, retries_per_host)):
            try:
                es_client.es = es_client.create_es_client(host)
                if not es_client.es.ping():
                    raise ConnectionError("ping failed")
                data = es_client.list_indices_stats(pattern, status)
                if data is None:
                    data = []
                return data, host
            except Exception as e:
                last_err = e
                print(
                    f"[indices-watch-collect] host={host} attempt failed: {e}",
                    file=sys.stderr,
                )
                time.sleep(retry_delay_sec)

    if last_err:
        print(f"[indices-watch-collect] all hosts failed: {last_err}", file=sys.stderr)
    return [], None


def collect_indices_and_nodes_with_failover(
    es_client: Any,
    *,
    pattern: Optional[str],
    status: Optional[str],
    retries_per_host: int,
    retry_delay_sec: float,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """
    Collect index stats, node stats, and cluster health in a single failover pass.

    Returns (indices, nodes_stats, cluster_health, host_used).
    Node stats and cluster health are best-effort — failures don't prevent
    index data from being returned.
    """
    hosts: List[str] = []
    seen: set = set()
    for h in (
        getattr(es_client, "host1", None),
        getattr(es_client, "host2", None),
        getattr(es_client, "host3", None),
    ):
        if not h or h in seen:
            continue
        seen.add(h)
        hosts.append(h)

    if not hosts:
        return [], None, None, None

    last_err: Optional[Exception] = None
    for host in hosts:
        for _attempt in range(max(1, retries_per_host)):
            try:
                es_client.es = es_client.create_es_client(host)
                if not es_client.es.ping():
                    raise ConnectionError("ping failed")
                data = es_client.list_indices_stats(pattern, status)
                if data is None:
                    data = []

                # Best-effort node stats
                nodes_stats: Optional[Dict[str, Any]] = None
                try:
                    resp = es_client.es.nodes.stats(metric='indices,os,jvm,fs')
                    nodes_stats = resp.body if hasattr(resp, 'body') else resp
                except Exception:
                    pass

                # Best-effort cluster health
                cluster_health: Optional[Dict[str, Any]] = None
                try:
                    resp = es_client.es.cluster.health()
                    cluster_health = resp.body if hasattr(resp, 'body') else resp
                except Exception:
                    pass

                return data, nodes_stats, cluster_health, host
            except Exception as e:
                last_err = e
                print(
                    f"[indices-watch-collect] host={host} attempt failed: {e}",
                    file=sys.stderr,
                )
                time.sleep(retry_delay_sec)

    if last_err:
        print(f"[indices-watch-collect] all hosts failed: {last_err}", file=sys.stderr)
    return [], None, None, None


def run_indices_watch_report(args: Any, console: Any, config_manager: Any) -> None:
    """CLI entry for indices-watch-report (no Elasticsearch connection)."""
    from rich.panel import Panel
    from rich.text import Text

    from display.style_system import StyleSystem
    from display.table_renderer import TableRenderer
    from display.theme_manager import ThemeManager

    import sys as _sys

    out_dir_arg = getattr(args, "report_sample_dir", None)
    day_iso = getattr(args, "date", None) or utc_today_iso()
    session_id_arg = getattr(args, "session_id", None)
    list_sessions_flag = getattr(args, "list_sessions", False)

    # Resolve the date directory for session operations
    if out_dir_arg and str(out_dir_arg).strip():
        # --dir supplied: load directly, no session logic
        sample_dir = Path(str(out_dir_arg).strip()).expanduser()
        samples = load_samples(sample_dir)
    else:
        # Resolve the date directory
        raw = _raw_index_watch_location_slug(args, config_manager)
        slug_order = _index_watch_sample_dir_candidates(raw, config_manager)
        date_dir = default_run_dir(slug_order[0], day_iso)
        # Try to find a date_dir that exists
        for slug in slug_order:
            candidate = default_run_dir(slug, day_iso)
            if candidate.is_dir():
                date_dir = candidate
                break

        # Handle --list-sessions
        if list_sessions_flag:
            sessions = list_sessions(date_dir)
            if not sessions:
                console.print(f"[dim]No sessions found in {date_dir}[/dim]")
            else:
                console.print(format_session_list(sessions))
            return

        # Handle --session SESSION_ID
        if session_id_arg:
            sessions = list_sessions(date_dir)
            matched = next((s for s in sessions if s.session_id == session_id_arg), None)
            if matched is None:
                console.print(f"[red]Session '{session_id_arg}' not found in {date_dir}[/red]")
                if sessions:
                    console.print("Available sessions:")
                    console.print(format_session_list(sessions))
                raise SystemExit(1)
            sample_dir = matched.session_dir
            samples = load_samples(sample_dir)
        else:
            # Auto-detect: sessions, legacy, or empty
            sessions = list_sessions(date_dir)
            if len(sessions) > 1:
                # Multiple sessions: prompt if TTY, else auto-select latest
                if _sys.stdin.isatty():
                    console.print(f"Multiple sessions found in {date_dir}:")
                    console.print(format_session_list(sessions))
                    n = len(sessions)
                    while True:
                        try:
                            choice = int(input(f"Select session [1-{n}]: ").strip())
                        except (ValueError, EOFError):
                            continue
                        if 1 <= choice <= n:
                            sample_dir = sessions[choice - 1].session_dir
                            break
                else:
                    selected = sessions[-1]
                    print(
                        f"[indices-watch-report] Non-interactive: using latest session {selected.session_id}",
                        file=_sys.stderr,
                    )
                    sample_dir = selected.session_dir
                samples = load_samples(sample_dir)
            elif len(sessions) == 1:
                # Exactly one session: load without prompting
                sample_dir = sessions[0].session_dir
                samples = load_samples(sample_dir)
            else:
                # Legacy flat dir or empty: use existing resolve logic
                sample_dir, samples = resolve_default_watch_sample_dir(
                    args, config_manager, day_iso
                )

    min_docs_delta = int(getattr(args, "min_docs_delta", 0) or 0)
    hot_ratio = float(getattr(args, "hot_ratio", 2.0) or 2.0)
    min_peers = int(getattr(args, "min_peers", 1) or 1)
    docs_peer_ratio = float(getattr(args, "docs_peer_ratio", 5.0) or 5.0)
    top_n = getattr(args, "top", None)
    fmt = getattr(args, "format", "table") or "table"

    rate_stats_arg = getattr(args, "watch_rate_stats", None) or "auto"

    result = analyze_watch_trends(
        samples,
        min_docs_delta=min_docs_delta,
        hot_ratio=hot_ratio,
        min_peers=min_peers,
        docs_peer_ratio=docs_peer_ratio,
        rate_stats=rate_stats_arg,
    )

    if fmt == "json":
        print(json.dumps(result, indent=2))
        return

    theme_manager = ThemeManager(config_manager)
    style_system = StyleSystem(theme_manager)
    table_renderer = TableRenderer(theme_manager, console)

    summary = result.get("summary") or {}
    if summary.get("error"):
        err_msg = (
            f"Cannot report: {summary.get('error')} "
            f"(samples={summary.get('sample_count', len(samples))}, dir={sample_dir})"
        )
        console.print(
            Panel(
                Text(err_msg, style=style_system.get_semantic_style("error")),
                title=Text("indices-watch-report", style=style_system.get_semantic_style("error")),
                border_style=theme_manager.get_themed_style(
                    "table_styles", "border_style", "red"
                ),
                padding=(1, 2),
            )
        )
        return

    rows = result.get("rows") or []
    if top_n is not None and int(top_n) > 0:
        rows = rows[: int(top_n)]

    show_rate_med = any(r.get("rate_vs_peer_median") is not None for r in rows)
    show_hot = any(r.get("hot") or r.get("docs_level_elevated") for r in rows)
    show_delta_store = any(int(r.get("delta_store_bytes", 0)) != 0 for r in rows)

    border_style = theme_manager.get_themed_style(
        "table_styles", "border_style", "bright_magenta"
    )
    primary = summary.get("rate_stats_primary", "span")
    sub = (
        f"{sample_dir} | samples={summary.get('sample_count')} | "
        f"intervals={summary.get('interval_count', 0)} | "
        f"elapsed≈{summary.get('elapsed_seconds')}s | "
        f"rates={primary} | rows={len(rows)}"
    )
    title_panel = Panel(
        Text("Index ingest watch report", style="bold", justify="center"),
        subtitle=sub,
        border_style=border_style,
        padding=(1, 2),
    )

    if not rows:
        console.print()
        console.print(title_panel)
        console.print()
        console.print(
            "[dim]No indices with a non-zero document count change between the first and last "
            "sample. Run indices-watch-collect longer, or widen filters; Δ docs = 0 rows are "
            "always omitted.[/dim]"
        )
        console.print()
        return

    interval_primary = summary.get("rate_stats_primary") == "intervals"
    sort_hint = "med docs/s" if interval_primary else "span docs/s"
    table = style_system.create_standard_table(
        title=f"Non-zero doc Δ only (sorted by {sort_hint})",
        style_variant="dashboard",
    )
    if show_hot:
        style_system.add_themed_column(table, "Hot", "status", justify="center", width=6)
    style_system.add_themed_column(table, "Index", "name", overflow="fold", min_width=32)
    style_system.add_themed_column(table, "Δ docs", "count", justify="right", width=14)
    if interval_primary:
        style_system.add_themed_column(table, "med/s", "count", justify="right", width=10)
        style_system.add_themed_column(table, "p90/s", "count", justify="right", width=10)
        style_system.add_themed_column(table, "max/s", "count", justify="right", width=10)
        style_system.add_themed_column(table, "span/s", "count", justify="right", width=10)
    else:
        style_system.add_themed_column(table, "docs/s", "count", justify="right", width=12)
    if show_delta_store:
        style_system.add_themed_column(table, "Δ store", "size", justify="right", width=12)
    style_system.add_themed_column(table, "docs", "count", justify="right", width=11)
    style_system.add_themed_column(table, "med peer", "count", justify="right", width=11)
    style_system.add_themed_column(table, "docs/med", "percentage", justify="right", width=9)
    if show_rate_med:
        style_system.add_themed_column(table, "rate/med", "percentage", justify="right", width=9)

    hot_ratio_arg = float(getattr(args, "hot_ratio", 2.0) or 2.0)
    docs_peer_ratio_arg = float(getattr(args, "docs_peer_ratio", 5.0) or 5.0)
    for r in rows:
        marks = []
        if r.get("hot"):
            marks.append("🔥")
        if r.get("docs_level_elevated"):
            marks.append("⚠")
        hot_mark = "".join(marks)
        rate_vs = r.get("rate_vs_peer_median")
        rate_s = f"{rate_vs}x" if rate_vs is not None else "—"
        rate_cells: Tuple[str, ...] = (rate_s,) if show_rate_med else ()
        doc_vs = r.get("docs_vs_peer_docs_ratio")
        doc_vs_s = f"{doc_vs}x" if doc_vs is not None else "—"
        row_style = None
        if r.get("hot"):
            row_style = "bright_red"
        elif r.get("docs_level_elevated"):
            row_style = "yellow"
        elif rate_vs is not None and rate_vs >= hot_ratio_arg * 0.75:
            row_style = "yellow"
        elif (
            doc_vs is not None
            and docs_peer_ratio_arg > 0
            and doc_vs >= docs_peer_ratio_arg * 0.75
        ):
            row_style = "cyan"

        def _fmt_rate(v: Any) -> str:
            if v is None:
                return "—"
            return f"{float(v):.2f}"

        store_cells: Tuple[str, ...] = (table_renderer.format_bytes(int(r.get("delta_store_bytes", 0))),) if show_delta_store else ()
        hot_cells: Tuple[str, ...] = (hot_mark,) if show_hot else ()
        if interval_primary:
            table.add_row(
                *hot_cells,
                r.get("index", ""),
                f"{r.get('delta_docs', 0):,}",
                _fmt_rate(r.get("docs_per_sec_interval_median")),
                _fmt_rate(r.get("docs_per_sec_interval_p90")),
                _fmt_rate(r.get("docs_per_sec_interval_max")),
                f"{r.get('docs_per_sec', 0):.2f}",
                *store_cells,
                format_doc_count_compact(int(r.get("docs_end", 0))),
                format_doc_count_compact(r.get("peer_median_docs_count")),
                doc_vs_s,
                *rate_cells,
                style=row_style,
            )
        else:
            table.add_row(
                *hot_cells,
                r.get("index", ""),
                f"{r.get('delta_docs', 0):,}",
                f"{r.get('docs_per_sec', 0):.2f}",
                *store_cells,
                format_doc_count_compact(int(r.get("docs_end", 0))),
                format_doc_count_compact(r.get("peer_median_docs_count")),
                doc_vs_s,
                *rate_cells,
                style=row_style,
            )

    console.print()
    console.print(title_panel)
    console.print()
    console.print(table)
    console.print()
    foot = (
        "docs / med peer = last-sample doc count vs leave-one-out median doc count among "
        "other backing indices in the same rollover series (like indices-analyze). docs/med is "
        "that ratio; ⚠ when ≥ --docs-peer-ratio (default 5)."
        + (" Negative Δ store is normal (merges/compaction)." if show_delta_store else "")
    )
    if show_rate_med:
        foot += (
            " rate/med = your span docs/s ÷ median peer span docs/s in that series; "
            "🔥 when ≥ --hot-ratio."
        )
    if interval_primary:
        foot += (
            " med/s, p90/s, max/s = distribution of per-interval docs/s between adjacent samples; "
            "span/s = first-to-last window. With ≥3 samples, --rate-stats auto shows interval stats "
            "(override: span | intervals)."
        )
    console.print(f"[dim]{foot}[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# indices-watch-sessions: session management (list / detail / delete)
# ---------------------------------------------------------------------------


def list_clusters(base_dir: Optional[Path] = None) -> List[str]:
    """Return sorted cluster slug names under the watch base directory."""
    base = base_dir or default_watch_base_dir()
    if not base.is_dir():
        return []
    return sorted(
        d.name for d in base.iterdir() if d.is_dir() and not d.name.startswith(".")
    )


def list_dates(cluster_slug: str, base_dir: Optional[Path] = None) -> List[str]:
    """Return sorted date folder names (YYYY-MM-DD) for a cluster."""
    base = base_dir or default_watch_base_dir()
    cluster_dir = base / sanitize_cluster_slug(cluster_slug)
    if not cluster_dir.is_dir():
        return []
    return sorted(
        d.name for d in cluster_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    )


def session_disk_size(session_dir: Path) -> int:
    """Total bytes of all files in a session directory."""
    if not session_dir.is_dir():
        return 0
    return sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file())


def delete_session(session_dir: Path) -> bool:
    """Remove a session directory and all its contents. Returns True on success."""
    import shutil

    if not session_dir.is_dir():
        return False
    shutil.rmtree(session_dir)
    return True


def delete_date_dir(cluster_slug: str, day_iso: str, base_dir: Optional[Path] = None) -> int:
    """Delete all sessions under a date directory. Returns count of sessions removed."""
    import shutil

    base = base_dir or default_watch_base_dir()
    date_dir = base / sanitize_cluster_slug(cluster_slug) / day_iso
    if not date_dir.is_dir():
        return 0
    sessions = list_sessions(date_dir)
    # Also count legacy flat files
    legacy = is_legacy_date_dir(date_dir)
    count = len(sessions) + (1 if legacy else 0)
    shutil.rmtree(date_dir)
    return max(count, 1)


def _format_size(nbytes: int) -> str:
    """Human-readable file size."""
    if nbytes < 1024:
        return f"{nbytes} B"
    elif nbytes < 1024 * 1024:
        return f"{nbytes / 1024:.1f} KB"
    elif nbytes < 1024 * 1024 * 1024:
        return f"{nbytes / (1024 * 1024):.1f} MB"
    else:
        return f"{nbytes / (1024 * 1024 * 1024):.2f} GB"


def run_indices_watch_sessions(args: Any, console: Any, config_manager: Any) -> None:
    """CLI entry for indices-watch-sessions (no Elasticsearch connection)."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    from display.style_system import StyleSystem
    from display.table_renderer import TableRenderer
    from display.theme_manager import ThemeManager

    action = getattr(args, "sessions_action", None)

    theme_manager = ThemeManager(config_manager)
    ss = StyleSystem(theme_manager)

    if not action:
        _show_sessions_help(console, ss, theme_manager)
        return
    fmt = getattr(args, "format", "table") or "table"

    table_renderer = TableRenderer(theme_manager, console)

    base_dir = default_watch_base_dir()

    # --- Common style lookups (§3) ---
    ts = ss._get_style('semantic', 'primary', 'bold cyan')
    border_style = ss._get_style('table_styles', 'border_style', 'bright_magenta')
    muted_style = ss._get_style('semantic', 'muted', 'dim')
    info_style = ss._get_style('semantic', 'info', 'cyan')
    success_style = ss.get_semantic_style("success")
    error_style = ss.get_semantic_style("error")
    header_style = theme_manager.get_theme_styles().get('header_style', 'bold white') if theme_manager else 'bold white'
    title_style = theme_manager.get_themed_style('panel_styles', 'title', 'bold white') if theme_manager else 'bold white'
    box_style = ss.get_table_box()

    # --- Resolve cluster slug ---
    cluster_arg = getattr(args, "cluster", None)
    if cluster_arg and str(cluster_arg).strip():
        cluster_slug = str(cluster_arg).strip()
    else:
        raw = _raw_index_watch_location_slug(args, config_manager)
        cluster_slug = index_watch_storage_slug(raw, config_manager)

    day_iso = getattr(args, "date", None) or utc_today_iso()

    # ── LIST ──────────────────────────────────────────────────────────────
    if action == "list":
        date_filter = getattr(args, "date", None)

        # Resolve the effective cluster slug via fallback chain
        raw = _raw_index_watch_location_slug(args, config_manager)
        slug_order = _index_watch_sample_dir_candidates(raw, config_manager)

        # Find the first slug that has data on disk
        effective_slug = cluster_slug
        for slug in slug_order:
            slug_dir = base_dir / sanitize_cluster_slug(slug)
            if slug_dir.is_dir():
                effective_slug = slug
                break

        # Determine which dates to show
        if date_filter:
            dates_to_show = [date_filter]
        else:
            dates_to_show = list_dates(effective_slug)

        # Collect all sessions across the selected dates
        all_rows: List[Dict[str, Any]] = []
        for d in (dates_to_show or []):
            date_dir = default_run_dir(effective_slug, d)
            if not date_dir.is_dir():
                continue
            sessions = list_sessions(date_dir)
            for s in sessions:
                all_rows.append({"date": d, "session": s, "legacy": False})
            if is_legacy_date_dir(date_dir):
                n_legacy = sum(
                    1 for p in date_dir.iterdir() if p.is_file() and _is_sample_file(p)
                )
                legacy_size = sum(
                    f.stat().st_size for f in date_dir.iterdir() if f.is_file()
                )
                all_rows.append({
                    "date": d,
                    "session": SessionInfo(
                        session_id="(legacy)",
                        session_dir=date_dir,
                        started_at="",
                        label=None,
                        sample_count=n_legacy,
                        schema_version=1,
                    ),
                    "legacy": True,
                    "legacy_size": legacy_size,
                })

        if fmt == "json":
            import json as _json

            out = []
            for row in all_rows:
                s = row["session"]
                out.append({
                    "date": row["date"],
                    "session_id": s.session_id,
                    "started_at": s.started_at,
                    "label": s.label,
                    "sample_count": s.sample_count,
                    "disk_size": row.get("legacy_size") if row["legacy"] else session_disk_size(s.session_dir),
                    "path": str(s.session_dir),
                })
            print(_json.dumps(out, indent=2))
            return

        # Empty state (§7)
        if not all_rows:
            label = f"{effective_slug} / {date_filter}" if date_filter else effective_slug
            console.print()
            console.print(Panel(
                Text(f"No sessions found for {label}", style="bold yellow", justify="center"),
                title=f"[{title_style}]📂 Watch Sessions[/{title_style}]",
                border_style="yellow",
                padding=(1, 2),
            ))
            console.print()
            return

        # Title panel (§1)
        total_sessions = len(all_rows)
        total_samples = sum(r["session"].sample_count for r in all_rows)
        n_dates = len(set(r["date"] for r in all_rows))
        title_suffix = f" / {date_filter}" if date_filter else ""

        subtitle_rich = Text()
        subtitle_rich.append("Sessions: ", style="default")
        subtitle_rich.append(str(total_sessions), style=info_style)
        subtitle_rich.append(" | Samples: ", style="default")
        subtitle_rich.append(str(total_samples), style=info_style)
        subtitle_rich.append(" | Dates: ", style="default")
        subtitle_rich.append(str(n_dates), style=info_style)

        title_panel = Panel(
            Text(
                f"✅ {total_sessions} Session{'s' if total_sessions != 1 else ''} — {effective_slug}{title_suffix}",
                style="bold green",
                justify="center",
            ),
            title=f"[{title_style}]📂 Watch Sessions[/{title_style}]",
            subtitle=subtitle_rich,
            border_style=border_style,
            padding=(1, 2),
        )

        # Table — no title, title panel above (§8)
        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border_style,
            box=box_style,
            show_lines=False,
            expand=True,
        )
        table.add_column("Date", width=12)
        table.add_column("Session ID")
        table.add_column("Started", width=11)
        table.add_column("Samples", justify="right", width=8)
        table.add_column("Size", justify="right", width=9)

        for i, row in enumerate(all_rows):
            s = row["session"]
            zebra = ss.get_zebra_style(i)
            if row["legacy"]:
                table.add_row(
                    row["date"], "(legacy flat)", "—",
                    str(s.sample_count),
                    _format_size(row.get("legacy_size", 0)),
                    style=f"dim {zebra}" if zebra else "dim",
                )
            else:
                try:
                    dt = datetime.fromisoformat(s.started_at.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M") + " UTC"
                except (ValueError, AttributeError):
                    time_str = s.started_at or "—"
                size_str = _format_size(session_disk_size(s.session_dir))
                table.add_row(
                    row["date"], s.session_id, time_str,
                    str(s.sample_count), size_str,
                    style=zebra,
                )

        # Layout (§9)
        console.print()
        console.print(title_panel)
        console.print()
        console.print(table)
        console.print()

    # ── DETAIL ────────────────────────────────────────────────────────────
    elif action == "detail":
        session_id_arg = getattr(args, "session_id", None)
        if not session_id_arg:
            _show_sessions_help(console, ss, theme_manager)
            return

        date_hint = getattr(args, "date", None)
        try:
            matched = _find_session_across_dates(
                session_id_arg, cluster_slug, date_hint, args, config_manager,
            )
        except AmbiguousSessionError as exc:
            _print_ambiguous_error(console, exc, title_style, border_style, muted_style)
            raise SystemExit(1)
        if matched is None:
            # Error panel (§6)
            console.print()
            console.print(Panel(
                Text(f"❌ Session '{session_id_arg}' not found", style="bold red", justify="center"),
                title=f"[{title_style}]📂 Watch Sessions[/{title_style}]",
                border_style="red",
                padding=(1, 2),
            ))
            console.print()
            raise SystemExit(1)

        # Load run.json metadata
        run_json_path = matched.session_dir / RUN_META_FILENAME
        meta: Dict[str, Any] = {}
        if run_json_path.is_file():
            try:
                with open(run_json_path, encoding="utf-8") as f:
                    meta = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        samples = load_samples(matched.session_dir)
        disk_size = session_disk_size(matched.session_dir)

        if fmt == "json":
            import json as _json

            detail = {
                "session_id": matched.session_id,
                "path": str(matched.session_dir),
                "started_at": matched.started_at,
                "label": matched.label,
                "sample_count": matched.sample_count,
                "disk_size": disk_size,
                "metadata": meta,
            }
            if samples:
                detail["first_sample_at"] = samples[0].get("captured_at", "")
                detail["last_sample_at"] = samples[-1].get("captured_at", "")
                detail["indices_in_last_sample"] = len(samples[-1].get("indices") or [])
            print(_json.dumps(detail, indent=2))
            return

        # Title panel (§1)
        # Derive date from session path (parent dir name)
        session_date = matched.session_dir.parent.name
        subtitle_rich = Text()
        subtitle_rich.append("Samples: ", style="default")
        subtitle_rich.append(str(matched.sample_count), style=info_style)
        subtitle_rich.append(" | Size: ", style="default")
        subtitle_rich.append(_format_size(disk_size), style=info_style)
        subtitle_rich.append(" | Cluster: ", style="default")
        subtitle_rich.append(meta.get("cluster", cluster_slug), style=info_style)

        title_panel = Panel(
            Text(
                f"📋 {matched.session_id}" + (f" — {matched.label}" if matched.label else ""),
                style="bold green",
                justify="center",
            ),
            title=f"[{title_style}]📂 Session Detail[/{title_style}]",
            subtitle=subtitle_rich,
            border_style=border_style,
            padding=(1, 2),
        )

        # Inner panel table (§4)
        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_column("Label", style="bold", no_wrap=True)
        info_table.add_column("Icon", justify="left", width=3)
        info_table.add_column("Value", no_wrap=True)

        info_table.add_row("Session ID:", "🆔", matched.session_id)
        info_table.add_row("Cluster:", "💻", meta.get("cluster", cluster_slug))
        info_table.add_row("Date:", "📅", session_date)
        info_table.add_row("Started:", "🕐", matched.started_at)
        info_table.add_row("Label:", "📝", matched.label or "—")
        info_table.add_row("Samples:", "📊", str(matched.sample_count))
        info_table.add_row("Disk size:", "💾", _format_size(disk_size))
        info_table.add_row("Path:", "📦", str(matched.session_dir))

        # Collection parameters from run.json
        interval = meta.get("interval_seconds")
        duration = meta.get("duration_seconds")
        pattern = meta.get("pattern")
        status_val = meta.get("status")
        if interval is not None:
            info_table.add_row("Interval:", "🔄", f"{interval}s")
        if duration is not None:
            info_table.add_row("Duration:", "🔄", f"{duration}s")
        if pattern:
            info_table.add_row("Pattern:", "🔍", str(pattern))
        if status_val:
            info_table.add_row("Status:", "🔶", str(status_val))

        if samples:
            first_ts = samples[0].get("captured_at", "")
            last_ts = samples[-1].get("captured_at", "")
            n_indices = len(samples[-1].get("indices") or [])
            host = samples[-1].get("host_used", "")
            info_table.add_row("", "", "")
            info_table.add_row("First sample:", "📈", str(first_ts))
            info_table.add_row("Last sample:", "📈", str(last_ts))
            info_table.add_row("Indices (last):", "📊", str(n_indices))
            if host:
                info_table.add_row("Host (last):", "💻", str(host))

        detail_panel = Panel(
            info_table,
            border_style=border_style,
            padding=(1, 2),
        )

        # Layout (§9)
        console.print()
        console.print(title_panel)
        console.print()
        console.print(detail_panel)
        console.print()

    # ── DELETE ────────────────────────────────────────────────────────────
    elif action == "delete":
        session_id_arg = getattr(args, "session_id", None)
        force = getattr(args, "force", False)

        if not session_id_arg:
            _show_sessions_help(console, ss, theme_manager)
            return

        date_hint = getattr(args, "date", None)
        try:
            matched = _find_session_across_dates(
                session_id_arg, cluster_slug, date_hint, args, config_manager,
            )
        except AmbiguousSessionError as exc:
            _print_ambiguous_error(console, exc, title_style, border_style, muted_style)
            raise SystemExit(1)
        if matched is None:
            console.print()
            console.print(Panel(
                Text(f"❌ Session '{session_id_arg}' not found", style="bold red", justify="center"),
                title=f"[{title_style}]📂 Watch Sessions[/{title_style}]",
                border_style="red",
                padding=(1, 2),
            ))
            console.print()
            raise SystemExit(1)

        size = session_disk_size(matched.session_dir)
        if not force:
            console.print(
                f"Delete session [bold]{matched.session_id}[/bold] "
                f"({matched.sample_count} samples, {_format_size(size)})?"
            )
            console.print(f"  path: {matched.session_dir}")
            if sys.stdin.isatty():
                try:
                    answer = input("Confirm [y/N]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    answer = ""
                if answer not in ("y", "yes"):
                    console.print(f"[{muted_style}]Cancelled[/{muted_style}]")
                    return
            else:
                console.print(f"[{error_style}]Non-interactive: use --force to skip confirmation[/{error_style}]")
                raise SystemExit(1)

        # Success/error output (§6)
        if delete_session(matched.session_dir):
            console.print()
            console.print(Panel(
                Text(
                    f"✅ Deleted session {matched.session_id} ({matched.sample_count} samples, {_format_size(size)})",
                    style="bold green",
                    justify="center",
                ),
                title=f"[{title_style}]📂 Session Deleted[/{title_style}]",
                border_style=border_style,
                padding=(1, 2),
            ))
            console.print()
        else:
            console.print()
            console.print(Panel(
                Text(f"❌ Failed to delete session {matched.session_id}", style="bold red", justify="center"),
                title=f"[{title_style}]📂 Session Delete[/{title_style}]",
                border_style="red",
                padding=(1, 2),
            ))
            console.print()
            raise SystemExit(1)

    # ── DELETE-DAY ────────────────────────────────────────────────────────
    elif action == "delete-day":
        force = getattr(args, "force", False)

        # Resolve date_dir with fallback chain
        raw = _raw_index_watch_location_slug(args, config_manager)
        slug_order = _index_watch_sample_dir_candidates(raw, config_manager)
        date_dir = default_run_dir(slug_order[0], day_iso)
        for slug in slug_order:
            candidate = default_run_dir(slug, day_iso)
            if candidate.is_dir():
                date_dir = candidate
                cluster_slug = slug
                break

        if not date_dir.is_dir():
            # Empty state (§7)
            console.print()
            console.print(Panel(
                Text(f"No data found for {cluster_slug} / {day_iso}", style="bold yellow", justify="center"),
                title=f"[{title_style}]📂 Watch Sessions[/{title_style}]",
                border_style="yellow",
                padding=(1, 2),
            ))
            console.print()
            return

        sessions = list_sessions(date_dir)
        legacy = is_legacy_date_dir(date_dir)
        total_samples = sum(s.sample_count for s in sessions)
        if legacy:
            total_samples += sum(
                1 for p in date_dir.iterdir() if p.is_file() and _is_sample_file(p)
            )
        total_size = sum(
            f.stat().st_size for f in date_dir.rglob("*") if f.is_file()
        )
        n_sessions = len(sessions) + (1 if legacy else 0)

        if not force:
            console.print(
                f"Delete [bold]all[/bold] data for [bold]{cluster_slug} / {day_iso}[/bold]?"
            )
            console.print(
                f"  {n_sessions} session(s), {total_samples} total samples, "
                f"{_format_size(total_size)}"
            )
            console.print(f"  path: {date_dir}")
            if sys.stdin.isatty():
                try:
                    answer = input("Confirm [y/N]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    answer = ""
                if answer not in ("y", "yes"):
                    console.print(f"[{muted_style}]Cancelled[/{muted_style}]")
                    return
            else:
                console.print(f"[{error_style}]Non-interactive: use --force to skip confirmation[/{error_style}]")
                raise SystemExit(1)

        count = delete_date_dir(cluster_slug, day_iso)
        # Success output (§6)
        console.print()
        console.print(Panel(
            Text(
                f"✅ Deleted {day_iso} for {cluster_slug} ({count} session(s), {_format_size(total_size)})",
                style="bold green",
                justify="center",
            ),
            title=f"[{title_style}]📂 Day Deleted[/{title_style}]",
            border_style=border_style,
            padding=(1, 2),
        ))
        console.print()

    # ── CLUSTERS ──────────────────────────────────────────────────────────
    elif action == "clusters":
        clusters = list_clusters()
        if fmt == "json":
            import json as _json

            out = []
            for c in clusters:
                dates = list_dates(c)
                out.append({"cluster": c, "dates": dates})
            print(_json.dumps(out, indent=2))
            return

        # Empty state (§7)
        if not clusters:
            console.print()
            console.print(Panel(
                Text("No watch data found", style="bold yellow", justify="center"),
                title=f"[{title_style}]📂 Watch Clusters[/{title_style}]",
                subtitle=Text(str(base_dir), style=muted_style),
                border_style="yellow",
                padding=(1, 2),
            ))
            console.print()
            return

        # Title panel (§1)
        total_dates = sum(len(list_dates(c)) for c in clusters)
        subtitle_rich = Text()
        subtitle_rich.append("Clusters: ", style="default")
        subtitle_rich.append(str(len(clusters)), style=info_style)
        subtitle_rich.append(" | Total dates: ", style="default")
        subtitle_rich.append(str(total_dates), style=info_style)

        title_panel = Panel(
            Text(
                f"✅ {len(clusters)} Cluster{'s' if len(clusters) != 1 else ''} with Watch Data",
                style="bold green",
                justify="center",
            ),
            title=f"[{title_style}]📂 Watch Clusters[/{title_style}]",
            subtitle=subtitle_rich,
            border_style=border_style,
            padding=(1, 2),
        )

        # Table — no title, title panel above (§8)
        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border_style,
            box=box_style,
            show_lines=False,
            expand=True,
        )
        table.add_column("Cluster", min_width=20)
        table.add_column("Dates", justify="right", width=8)
        table.add_column("Latest", width=12)

        for i, c in enumerate(clusters):
            dates = list_dates(c)
            latest = dates[-1] if dates else "—"
            table.add_row(c, str(len(dates)), latest, style=ss.get_zebra_style(i))

        # Layout (§9)
        console.print()
        console.print(title_panel)
        console.print()
        console.print(table)
        console.print()

    else:
        _show_sessions_help(console, ss, theme_manager)


class AmbiguousSessionError(Exception):
    """Raised when a partial session query matches more than one session."""

    def __init__(self, query: str, matches: List[SessionInfo]):
        self.query = query
        self.matches = matches
        super().__init__(f"'{query}' matches {len(matches)} sessions")


def _find_session_across_dates(
    session_id: str,
    cluster_slug: str,
    date_hint: Optional[str],
    args: Any,
    config_manager: Any,
) -> Optional[SessionInfo]:
    """Search for a session by ID, prefix, or label across dates.

    Matching priority:
      1. Exact session_id match
      2. Prefix match on session_id  (e.g. '0011' → '0011-afternoon')
      3. Label substring match        (e.g. 'afternoon' → '0011-afternoon')

    Raises AmbiguousSessionError when a partial query matches multiple sessions.
    Returns the matching SessionInfo or None.
    """
    raw = _raw_index_watch_location_slug(args, config_manager)
    slug_order = _index_watch_sample_dir_candidates(raw, config_manager)

    # Find the effective slug that has data on disk
    base_dir = default_watch_base_dir()
    effective_slug = cluster_slug
    for slug in slug_order:
        slug_dir = base_dir / sanitize_cluster_slug(slug)
        if slug_dir.is_dir():
            effective_slug = slug
            break

    if date_hint:
        dates_to_search = [date_hint]
    else:
        dates_to_search = list_dates(effective_slug)

    # Collect all sessions to search through
    all_sessions: List[SessionInfo] = []
    for d in (dates_to_search or []):
        date_dir = default_run_dir(effective_slug, d)
        if not date_dir.is_dir():
            continue
        all_sessions.extend(list_sessions(date_dir))

    query = session_id
    query_lower = query.lower()

    # 1) Exact match
    for s in all_sessions:
        if s.session_id == query:
            return s

    # 2) Prefix match on session_id
    prefix_matches = [s for s in all_sessions if s.session_id.lower().startswith(query_lower)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        raise AmbiguousSessionError(query, prefix_matches)

    # 3) Label substring match (case-insensitive)
    label_matches = [
        s for s in all_sessions
        if s.label and query_lower in s.label.lower()
    ]
    if len(label_matches) == 1:
        return label_matches[0]
    if len(label_matches) > 1:
        raise AmbiguousSessionError(query, label_matches)

    return None


def _print_ambiguous_error(
    console: Any,
    exc: AmbiguousSessionError,
    title_style: str,
    border_style: str,
    muted_style: str,
) -> None:
    """Display a themed panel listing the ambiguous matches so the user can refine."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Session ID", style="bold cyan", no_wrap=True)
    table.add_column("Label", no_wrap=True)
    table.add_column("Started", style="dim")
    for s in exc.matches:
        table.add_row(s.session_id, s.label or "—", s.started_at)

    group = Text.assemble(
        (f"⚠  '{exc.query}' matches {len(exc.matches)} sessions — please be more specific:\n\n", "bold yellow"),
    )
    console.print()
    console.print(Panel(
        group,
        title=f"[{title_style}]📂 Ambiguous Session[/{title_style}]",
        border_style="yellow",
        padding=(1, 2),
    ))
    console.print(table)
    console.print()


def _show_sessions_help(console: Any, ss: Any, tm: Any) -> None:
    """Display themed help table for indices-watch-sessions (§2 pattern)."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    primary_style = ss.get_semantic_style("primary")
    success_style = ss.get_semantic_style("success")
    muted_style = ss._get_style('semantic', 'muted', 'dim')
    border_style = ss._get_style('table_styles', 'border_style', 'white')
    header_style = tm.get_theme_styles().get('header_style', 'bold white') if tm else 'bold white'
    title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
    box_style = ss.get_table_box()

    header_panel = Panel(
        Text("Run ./escmd.py indices-watch-sessions <action> [options]", style="bold white"),
        title=f"[{title_style}]📂 Watch Session Management[/{title_style}]",
        subtitle=Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]for full options[/dim]"),
        border_style=border_style,
        padding=(1, 2),
        expand=True,
    )

    table = Table(
        show_header=True,
        header_style=header_style,
        border_style=border_style,
        box=box_style,
        show_lines=False,
        expand=True,
    )
    table.add_column("Command / Option", style=primary_style, ratio=2)
    table.add_column("Description", style="white", ratio=3)
    table.add_column("Example", style=success_style, ratio=3)

    rows = [
        ("list", "List all sessions (all dates)", "indices-watch-sessions list"),
        ("list --date YYYY-MM-DD", "List sessions for a specific date", "indices-watch-sessions list --date 2025-01-15"),
        ("detail <session-id>", "Show session detail", "indices-watch-sessions detail 1430"),
        ("delete <session-id>", "Delete a session", "indices-watch-sessions delete 1430"),
        ("delete-day", "Delete all sessions for a date", "indices-watch-sessions delete-day --date 2025-01-15"),
        ("clusters", "List clusters with watch data", "indices-watch-sessions clusters"),
    ]
    for i, (cmd, desc, ex) in enumerate(rows):
        table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i))

    # Options section separator
    table.add_row(
        Text("── Options ──", style=muted_style),
        Text("", style=muted_style),
        Text("", style=muted_style),
    )
    options = [
        ("--cluster NAME", "Target a specific cluster slug", "indices-watch-sessions list --cluster prod"),
        ("--date YYYY-MM-DD", "Target a specific date", "indices-watch-sessions list --date 2025-01-15"),
        ("--format json", "Machine-readable JSON output", "indices-watch-sessions list --format json"),
        ("--force", "Skip delete confirmation", "indices-watch-sessions delete 1430 --force"),
    ]
    for i, (opt, desc, ex) in enumerate(options):
        table.add_row(
            Text(opt, style=ss._get_style('semantic', 'secondary', 'magenta')),
            desc,
            Text(f"./escmd.py {ex}", style=muted_style),
            style=ss.get_zebra_style(i),
        )

    console.print()
    console.print(header_panel)
    console.print()
    console.print(table)
    console.print()
