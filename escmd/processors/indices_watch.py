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
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = captured_at.strftime("%Y%m%dT%H%M%S")
    fname = f"{ts}_{sequence:04d}.json"
    path = out_dir / fname
    payload = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at.isoformat(),
        "cluster": cluster,
        "host_used": host_used,
        "indices": indices,
    }
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
    common = sorted(set(m0.keys()) & set(m1.keys()))

    proc = IndexProcessor()
    date_re = proc.date_pattern_regex

    # docs/s for every index in both samples (including Δ docs = 0) — peer baseline
    docs_per_sec_all: Dict[str, float] = {}
    for name in common:
        d0 = _row_docs(m0[name])
        d1 = _row_docs(m1[name])
        docs_per_sec_all[name] = float(d1 - d0) / elapsed

    # Rollover series membership: all common indices, not only rows we will print
    base_to_names: Dict[str, List[str]] = {}
    index_to_base: Dict[str, Optional[str]] = {}
    for name in common:
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
    for name in common:
        d0 = _row_docs(m0[name])
        d1 = _row_docs(m1[name])
        s0 = _row_store(m0[name])
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
        "indices_compared": len(common),
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
