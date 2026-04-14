"""Unit tests for indices watch sampling and trend analysis."""

import pytest

from processors.indices_watch import (
    analyze_watch_trends,
    default_run_dir,
    format_doc_count_compact,
    load_samples,
    sanitize_cluster_slug,
)


def test_sanitize_cluster_slug():
    assert sanitize_cluster_slug("iad41-c03") == "iad41-c03"
    assert ".." not in sanitize_cluster_slug('a/b:c\\d*e?f"g')
    assert sanitize_cluster_slug("") == "unknown"


def test_analyze_watch_trends_delta_and_hot():
    samples = [
        {
            "captured_at": "2026-03-30T12:00:00+00:00",
            "indices": [
                {
                    "index": ".ds-logs-2026.03.30-000001",
                    "docs.count": 1000,
                    "store.size": 1000,
                },
                {
                    "index": ".ds-logs-2026.03.29-000001",
                    "docs.count": 500,
                    "store.size": 500,
                },
            ],
        },
        {
            "captured_at": "2026-03-30T12:01:00+00:00",
            "indices": [
                {
                    "index": ".ds-logs-2026.03.30-000001",
                    "docs.count": 61000,
                    "store.size": 50000,
                },
                {
                    "index": ".ds-logs-2026.03.29-000001",
                    "docs.count": 550,
                    "store.size": 520,
                },
            ],
        },
    ]
    out = analyze_watch_trends(samples, min_docs_delta=0, hot_ratio=2.0, min_peers=1)
    assert "error" not in out["summary"]
    rows = {r["index"]: r for r in out["rows"]}
    assert ".ds-logs-2026.03.30-000001" in rows
    r_hot = rows[".ds-logs-2026.03.30-000001"]
    assert r_hot["delta_docs"] == 60000
    assert r_hot["docs_per_sec"] == 1000.0
    assert r_hot["hot"] is True
    assert r_hot["peer_median_docs_count"] == 550
    assert r_hot["docs_vs_peer_docs_ratio"] is not None
    assert r_hot["docs_vs_peer_docs_ratio"] > 5.0
    assert r_hot["docs_level_elevated"] is True
    assert r_hot["interval_rate_count"] == 1
    assert r_hot["docs_per_sec_interval_median"] == pytest.approx(1000.0)
    assert r_hot["docs_per_sec_interval_p90"] == pytest.approx(1000.0)
    assert r_hot["docs_per_sec_interval_max"] == pytest.approx(1000.0)
    assert out["summary"]["rate_stats_primary"] == "span"


def test_analyze_watch_trends_three_samples_median_p90_max():
    """Span docs/s differs from per-interval median when multiple samples exist."""
    samples = [
        {
            "captured_at": "2026-03-30T12:00:00+00:00",
            "indices": [
                {
                    "index": "grow-2026.03.30-000001",
                    "docs.count": 0,
                    "store.size": 0,
                },
            ],
        },
        {
            "captured_at": "2026-03-30T12:01:00+00:00",
            "indices": [
                {
                    "index": "grow-2026.03.30-000001",
                    "docs.count": 1000,
                    "store.size": 100,
                },
            ],
        },
        {
            "captured_at": "2026-03-30T12:02:00+00:00",
            "indices": [
                {
                    "index": "grow-2026.03.30-000001",
                    "docs.count": 6000,
                    "store.size": 200,
                },
            ],
        },
    ]
    out = analyze_watch_trends(samples, min_docs_delta=0, rate_stats="auto")
    assert out["summary"]["rate_stats_primary"] == "intervals"
    row = out["rows"][0]
    assert row["delta_docs"] == 6000
    assert row["docs_per_sec"] == pytest.approx(50.0)
    assert row["interval_rate_count"] == 2
    assert row["docs_per_sec_interval_median"] == pytest.approx(50.0)
    assert row["docs_per_sec_interval_max"] == pytest.approx(5000.0 / 60.0)
    assert row["docs_per_sec_interval_p90"] == pytest.approx(
        (1000.0 / 60.0) * 0.1 + (5000.0 / 60.0) * 0.9
    )

    span_primary = analyze_watch_trends(samples, min_docs_delta=0, rate_stats="span")
    assert span_primary["summary"]["rate_stats_primary"] == "span"


def test_analyze_watch_trends_insufficient_samples():
    out = analyze_watch_trends([], min_docs_delta=0)
    assert out["summary"].get("error") == "need_at_least_two_samples"


def test_analyze_watch_trends_peer_includes_zero_delta_siblings():
    """Siblings omitted from the table (Δ docs = 0) still define the peer median."""
    samples = [
        {
            "captured_at": "2026-03-30T12:00:00+00:00",
            "indices": [
                {
                    "index": ".ds-logs-2026.03.28-000001",
                    "docs.count": 100,
                    "store.size": 100,
                },
                {
                    "index": ".ds-logs-2026.03.29-000001",
                    "docs.count": 100,
                    "store.size": 100,
                },
                {
                    "index": ".ds-logs-2026.03.30-000001",
                    "docs.count": 1000,
                    "store.size": 1000,
                },
            ],
        },
        {
            "captured_at": "2026-03-30T12:01:00+00:00",
            "indices": [
                {
                    "index": ".ds-logs-2026.03.28-000001",
                    "docs.count": 60100,
                    "store.size": 100,
                },
                {
                    "index": ".ds-logs-2026.03.29-000001",
                    "docs.count": 30100,
                    "store.size": 100,
                },
                {
                    "index": ".ds-logs-2026.03.30-000001",
                    "docs.count": 1000,
                    "store.size": 1000,
                },
            ],
        },
    ]
    out = analyze_watch_trends(samples, min_docs_delta=0, hot_ratio=2.0, min_peers=1)
    by_name = {r["index"]: r for r in out["rows"]}
    assert ".ds-logs-2026.03.30-000001" not in by_name
    r_a = by_name[".ds-logs-2026.03.28-000001"]
    r_b = by_name[".ds-logs-2026.03.29-000001"]
    assert r_a["rate_vs_peer_median"] is not None
    assert r_b["rate_vs_peer_median"] is not None
    assert r_a["peer_median_docs_count"] is not None
    assert r_a["docs_vs_peer_docs_ratio"] is not None


def test_format_doc_count_compact():
    assert format_doc_count_compact(None) == "—"
    assert "M" in format_doc_count_compact(150_000_000)


def test_analyze_watch_trends_omits_zero_doc_delta():
    samples = [
        {
            "captured_at": "2026-03-30T12:00:00+00:00",
            "indices": [
                {
                    "index": "static-index",
                    "docs.count": 100,
                    "store.size": 100,
                },
                {
                    "index": "growing-index",
                    "docs.count": 10,
                    "store.size": 10,
                },
            ],
        },
        {
            "captured_at": "2026-03-30T12:01:00+00:00",
            "indices": [
                {
                    "index": "static-index",
                    "docs.count": 100,
                    "store.size": 200,
                },
                {
                    "index": "growing-index",
                    "docs.count": 1000,
                    "store.size": 500,
                },
            ],
        },
    ]
    out = analyze_watch_trends(samples, min_docs_delta=0)
    names = {r["index"] for r in out["rows"]}
    assert "static-index" not in names
    assert "growing-index" in names


def test_default_run_dir_structure(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCMD_INDEX_WATCH_DIR", str(tmp_path))
    p = default_run_dir("my-cluster", "2026-03-30")
    assert p == tmp_path / "my-cluster" / "2026-03-30"


def test_load_samples_skips_run_json(tmp_path):
    (tmp_path / "run.json").write_text('{"kind":"indices-watch-run"}', encoding="utf-8")
    (tmp_path / "a.json").write_text(
        '{"captured_at":"2026-03-30T00:00:00+00:00","indices":[]}', encoding="utf-8"
    )
    s = load_samples(tmp_path)
    assert len(s) == 1


def test_index_watch_storage_slug_uses_canonical_key():
    from unittest.mock import MagicMock

    from processors.indices_watch import index_watch_storage_slug

    cm = MagicMock()
    cm.canonical_cluster_name_for_location.return_value = "aex20-glip"
    assert index_watch_storage_slug("aex20", cm) == "aex20-glip"


def test_resolve_default_watch_sample_dir_finds_legacy_short_slug_dir(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from processors.indices_watch import resolve_default_watch_sample_dir

    monkeypatch.setenv("ESCMD_INDEX_WATCH_DIR", str(tmp_path))

    cm = MagicMock()
    cm.get_default_cluster.return_value = "aex20-glip"
    cm.canonical_cluster_name_for_location.return_value = "aex20-glip"
    cm.servers_dict = {}
    cm.get_server_config.return_value = None

    args = SimpleNamespace(locations=None, cluster=None)
    day = "2026-04-07"
    legacy = tmp_path / "aex20" / day
    legacy.mkdir(parents=True)
    (legacy / "20260407T000000_0001.json").write_text(
        '{"captured_at":"2026-04-07T00:00:00+00:00","indices":[]}', encoding="utf-8"
    )
    (legacy / "20260407T000001_0002.json").write_text(
        '{"captured_at":"2026-04-07T00:01:00+00:00","indices":[]}', encoding="utf-8"
    )

    d, samples = resolve_default_watch_sample_dir(args, cm, day)
    assert d == legacy
    assert len(samples) == 2


# ---------------------------------------------------------------------------
# Session-related unit tests (Task 12)
# ---------------------------------------------------------------------------

import json as _json
from datetime import timezone

from processors.indices_watch import (
    SessionInfo,
    is_legacy_date_dir,
    list_sessions,
    make_session_id,
    resolve_session_dir,
    sanitize_session_label,
)


# --- sanitize_session_label -------------------------------------------------

def test_sanitize_session_label_empty():
    assert sanitize_session_label("") == ""


def test_sanitize_session_label_all_invalid():
    assert sanitize_session_label("!@#$%") == "_____"


def test_sanitize_session_label_exactly_40_chars():
    label = "a" * 40
    assert sanitize_session_label(label) == label


def test_sanitize_session_label_41_chars_truncated():
    label = "a" * 41
    assert sanitize_session_label(label) == "a" * 40


def test_sanitize_session_label_valid_only():
    label = "load-test_123"
    assert sanitize_session_label(label) == label


def test_sanitize_session_label_mixed():
    assert sanitize_session_label("load test!") == "load_test_"


# --- make_session_id --------------------------------------------------------

def test_make_session_id_no_label():
    from datetime import datetime
    dt = datetime(2026, 4, 13, 14, 30, tzinfo=timezone.utc)
    assert make_session_id(dt) == "1430"


def test_make_session_id_with_label():
    from datetime import datetime
    dt = datetime(2026, 4, 13, 14, 30, tzinfo=timezone.utc)
    assert make_session_id(dt, "load-test") == "1430-load-test"


def test_make_session_id_label_with_spaces():
    from datetime import datetime
    dt = datetime(2026, 4, 13, 14, 30, tzinfo=timezone.utc)
    assert make_session_id(dt, "load test") == "1430-load_test"


def test_make_session_id_label_sanitizes_to_empty():
    from datetime import datetime
    dt = datetime(2026, 4, 13, 14, 30, tzinfo=timezone.utc)
    # Empty string sanitizes to "" → no hyphen appended
    assert make_session_id(dt, "") == "1430"


# --- resolve_session_dir ----------------------------------------------------

def test_resolve_session_dir_no_collision(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCMD_INDEX_WATCH_DIR", str(tmp_path))
    from datetime import datetime
    dt = datetime(2026, 4, 13, 14, 30, tzinfo=timezone.utc)
    result = resolve_session_dir("mycluster", "2026-04-13", dt=dt)
    expected = tmp_path / "mycluster" / "2026-04-13" / "1430"
    assert result == expected
    assert not result.exists()


def test_resolve_session_dir_single_collision(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCMD_INDEX_WATCH_DIR", str(tmp_path))
    from datetime import datetime
    dt = datetime(2026, 4, 13, 14, 30, tzinfo=timezone.utc)
    base = tmp_path / "mycluster" / "2026-04-13"
    (base / "1430").mkdir(parents=True)
    result = resolve_session_dir("mycluster", "2026-04-13", dt=dt)
    assert result == base / "1430-2"
    assert not result.exists()


def test_resolve_session_dir_double_collision(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCMD_INDEX_WATCH_DIR", str(tmp_path))
    from datetime import datetime
    dt = datetime(2026, 4, 13, 14, 30, tzinfo=timezone.utc)
    base = tmp_path / "mycluster" / "2026-04-13"
    (base / "1430").mkdir(parents=True)
    (base / "1430-2").mkdir(parents=True)
    result = resolve_session_dir("mycluster", "2026-04-13", dt=dt)
    assert result == base / "1430-3"
    assert not result.exists()


def test_resolve_session_dir_does_not_create(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCMD_INDEX_WATCH_DIR", str(tmp_path))
    from datetime import datetime
    dt = datetime(2026, 4, 13, 9, 5, tzinfo=timezone.utc)
    result = resolve_session_dir("mycluster", "2026-04-13", dt=dt)
    assert not result.exists()


# --- list_sessions ----------------------------------------------------------

def _write_run_json(session_dir: "Path", **extra):
    meta = {"schema_version": 2, "started_at": "2026-04-13T14:30:00+00:00", **extra}
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "run.json").write_text(_json.dumps(meta), encoding="utf-8")


def test_list_sessions_empty_dir(tmp_path):
    assert list_sessions(tmp_path) == []


def test_list_sessions_one_valid_v2(tmp_path):
    session_dir = tmp_path / "1430"
    _write_run_json(session_dir)
    sessions = list_sessions(tmp_path)
    assert len(sessions) == 1
    assert isinstance(sessions[0], SessionInfo)
    assert sessions[0].session_id == "1430"


def test_list_sessions_mixed(tmp_path):
    # Valid v2 session
    _write_run_json(tmp_path / "1430")
    # Subdir with no run.json
    (tmp_path / "no-run").mkdir()
    # Subdir with invalid JSON
    bad = tmp_path / "bad-json"
    bad.mkdir()
    (bad / "run.json").write_text("not-json", encoding="utf-8")
    sessions = list_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0].session_id == "1430"


def test_list_sessions_sorted_ascending(tmp_path):
    _write_run_json(tmp_path / "1500", started_at="2026-04-13T15:00:00+00:00")
    _write_run_json(tmp_path / "1430", started_at="2026-04-13T14:30:00+00:00")
    sessions = list_sessions(tmp_path)
    assert len(sessions) == 2
    assert sessions[0].session_id == "1430"
    assert sessions[1].session_id == "1500"


def test_list_sessions_legacy_flat_dir(tmp_path):
    # Flat .json sample files, no session subdirs
    (tmp_path / "20260413T143000_0001.json").write_text(
        '{"captured_at":"2026-04-13T14:30:00+00:00","indices":[]}', encoding="utf-8"
    )
    assert list_sessions(tmp_path) == []


# --- is_legacy_date_dir -----------------------------------------------------

def test_is_legacy_date_dir_flat_samples(tmp_path):
    (tmp_path / "20260413T143000_0001.json").write_text(
        '{"captured_at":"2026-04-13T14:30:00+00:00","indices":[]}', encoding="utf-8"
    )
    assert is_legacy_date_dir(tmp_path) is True


def test_is_legacy_date_dir_only_session_subdirs(tmp_path):
    _write_run_json(tmp_path / "1430")
    assert is_legacy_date_dir(tmp_path) is False


def test_is_legacy_date_dir_both_flat_and_sessions(tmp_path):
    # Sessions take precedence → not legacy
    (tmp_path / "20260413T143000_0001.json").write_text(
        '{"captured_at":"2026-04-13T14:30:00+00:00","indices":[]}', encoding="utf-8"
    )
    _write_run_json(tmp_path / "1430")
    assert is_legacy_date_dir(tmp_path) is False


def test_is_legacy_date_dir_nonexistent(tmp_path):
    assert is_legacy_date_dir(tmp_path / "does-not-exist") is False


def test_is_legacy_date_dir_empty(tmp_path):
    assert is_legacy_date_dir(tmp_path) is False
