"""Unit tests for indices watch sampling and trend analysis."""

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
