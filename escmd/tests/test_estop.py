"""
Unit tests for EsTopPoller in commands/estop_commands.py.

Covers:
- Success case: all three API calls succeed, PollSnapshot fully populated
- cluster.health() failure: cluster_health is None, error set, others populated
- nodes.stats() failure: nodes_stats is None, error set, others populated
- cat.indices() failure: cat_indices is None, error set, others populated

Requirements: 3.5, 4.5, 5.7
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commands.estop_commands import EsTopPoller, PollSnapshot


def _make_es_client(health_response=None, nodes_response=None, cat_response=None):
    """Build a mock es_client whose .es sub-attributes return the given values."""
    es_client = MagicMock()

    # cluster.health()
    if isinstance(health_response, Exception):
        es_client.es.cluster.health.side_effect = health_response
    else:
        mock_health = MagicMock()
        mock_health.body = health_response
        es_client.es.cluster.health.return_value = mock_health

    # nodes.stats()
    if isinstance(nodes_response, Exception):
        es_client.es.nodes.stats.side_effect = nodes_response
    else:
        mock_nodes = MagicMock()
        mock_nodes.body = nodes_response
        es_client.es.nodes.stats.return_value = mock_nodes

    # cat.indices()
    if isinstance(cat_response, Exception):
        es_client.es.cat.indices.side_effect = cat_response
    else:
        mock_cat = MagicMock()
        mock_cat.body = cat_response
        es_client.es.cat.indices.return_value = mock_cat

    return es_client


SAMPLE_HEALTH = {
    "cluster_name": "test-cluster",
    "status": "green",
    "number_of_nodes": 3,
    "number_of_data_nodes": 3,
    "active_shards": 10,
    "relocating_shards": 0,
    "initializing_shards": 0,
    "unassigned_shards": 0,
}

SAMPLE_NODES = {
    "nodes": {
        "node1": {
            "name": "node-1",
            "jvm": {"mem": {"heap_used_percent": 45}},
            "os": {"cpu": {"percent": 20, "load_average": {"1m": 1.5}}},
            "fs": {"total": {"total_in_bytes": 100_000_000, "available_in_bytes": 60_000_000}},
        }
    }
}

SAMPLE_CAT = [
    {
        "index": "my-index",
        "docs.count": "1000",
        "search.query_total": "500",
        "store.size": "10mb",
        "pri": "1",
        "rep": "1",
    }
]


class TestEsTopPollerSuccess(unittest.TestCase):
    """All three API calls succeed — PollSnapshot should be fully populated."""

    def setUp(self):
        self.es_client = _make_es_client(
            health_response=SAMPLE_HEALTH,
            nodes_response=SAMPLE_NODES,
            cat_response=SAMPLE_CAT,
        )
        self.poller = EsTopPoller(self.es_client)

    def test_returns_poll_snapshot(self):
        result = self.poller.poll()
        self.assertIsInstance(result, PollSnapshot)

    def test_cluster_health_populated(self):
        result = self.poller.poll()
        self.assertEqual(result.cluster_health, SAMPLE_HEALTH)

    def test_nodes_stats_populated(self):
        result = self.poller.poll()
        self.assertEqual(result.nodes_stats, SAMPLE_NODES)

    def test_cat_indices_populated(self):
        result = self.poller.poll()
        self.assertEqual(result.cat_indices, SAMPLE_CAT)

    def test_no_error_strings_on_success(self):
        result = self.poller.poll()
        self.assertIsNone(result.cluster_health_error)
        self.assertIsNone(result.nodes_stats_error)
        self.assertIsNone(result.cat_indices_error)

    def test_timestamp_is_set(self):
        from datetime import datetime
        result = self.poller.poll()
        self.assertIsInstance(result.timestamp, datetime)

    def test_correct_api_calls_made(self):
        self.poller.poll()
        self.es_client.es.cluster.health.assert_called_once()
        self.es_client.es.nodes.stats.assert_called_once_with(metric='indices,os,jvm,fs')
        self.es_client.es.cat.indices.assert_called_once_with(
            h='index,docs.count,search.query_total,store.size,pri,rep',
            format='json',
        )


class TestEsTopPollerClusterHealthFailure(unittest.TestCase):
    """cluster.health() raises — cluster_health is None, others still populated."""

    def setUp(self):
        self.error = ConnectionError("cluster health unavailable")
        self.es_client = _make_es_client(
            health_response=self.error,
            nodes_response=SAMPLE_NODES,
            cat_response=SAMPLE_CAT,
        )
        self.poller = EsTopPoller(self.es_client)
        self.result = self.poller.poll()

    def test_cluster_health_is_none(self):
        self.assertIsNone(self.result.cluster_health)

    def test_cluster_health_error_is_set(self):
        self.assertIsNotNone(self.result.cluster_health_error)
        self.assertIn("cluster health unavailable", self.result.cluster_health_error)

    def test_nodes_stats_still_populated(self):
        self.assertEqual(self.result.nodes_stats, SAMPLE_NODES)

    def test_cat_indices_still_populated(self):
        self.assertEqual(self.result.cat_indices, SAMPLE_CAT)

    def test_other_errors_are_none(self):
        self.assertIsNone(self.result.nodes_stats_error)
        self.assertIsNone(self.result.cat_indices_error)


class TestEsTopPollerNodesStatsFailure(unittest.TestCase):
    """nodes.stats() raises — nodes_stats is None, others still populated."""

    def setUp(self):
        self.error = RuntimeError("nodes stats timeout")
        self.es_client = _make_es_client(
            health_response=SAMPLE_HEALTH,
            nodes_response=self.error,
            cat_response=SAMPLE_CAT,
        )
        self.poller = EsTopPoller(self.es_client)
        self.result = self.poller.poll()

    def test_nodes_stats_is_none(self):
        self.assertIsNone(self.result.nodes_stats)

    def test_nodes_stats_error_is_set(self):
        self.assertIsNotNone(self.result.nodes_stats_error)
        self.assertIn("nodes stats timeout", self.result.nodes_stats_error)

    def test_cluster_health_still_populated(self):
        self.assertEqual(self.result.cluster_health, SAMPLE_HEALTH)

    def test_cat_indices_still_populated(self):
        self.assertEqual(self.result.cat_indices, SAMPLE_CAT)

    def test_other_errors_are_none(self):
        self.assertIsNone(self.result.cluster_health_error)
        self.assertIsNone(self.result.cat_indices_error)


class TestEsTopPollerCatIndicesFailure(unittest.TestCase):
    """cat.indices() raises — cat_indices is None, others still populated."""

    def setUp(self):
        self.error = ValueError("cat indices forbidden")
        self.es_client = _make_es_client(
            health_response=SAMPLE_HEALTH,
            nodes_response=SAMPLE_NODES,
            cat_response=self.error,
        )
        self.poller = EsTopPoller(self.es_client)
        self.result = self.poller.poll()

    def test_cat_indices_is_none(self):
        self.assertIsNone(self.result.cat_indices)

    def test_cat_indices_error_is_set(self):
        self.assertIsNotNone(self.result.cat_indices_error)
        self.assertIn("cat indices forbidden", self.result.cat_indices_error)

    def test_cluster_health_still_populated(self):
        self.assertEqual(self.result.cluster_health, SAMPLE_HEALTH)

    def test_nodes_stats_still_populated(self):
        self.assertEqual(self.result.nodes_stats, SAMPLE_NODES)

    def test_other_errors_are_none(self):
        self.assertIsNone(self.result.cluster_health_error)
        self.assertIsNone(self.result.nodes_stats_error)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# Property-based tests — require Hypothesis
# ---------------------------------------------------------------------------
from hypothesis import given, settings
from hypothesis import strategies as st
from commands.estop_commands import EsTopRenderer


# Feature: es-top, Property 7: Node panel threshold styling
class TestProperty7NodePanelThresholdStyling(unittest.TestCase):
    """Property 7: Node panel threshold styling — Validates: Requirements 4.3, 4.4"""

    def setUp(self):
        self.renderer = EsTopRenderer()

    @settings(max_examples=100)
    @given(st.floats(min_value=0, max_value=100))
    def test_heap_style_red_bold_at_or_above_85(self, pct):
        """_heap_style returns 'red bold' when pct >= 85, else not 'red bold'."""
        result = self.renderer._heap_style(pct)
        if pct >= 85:
            self.assertEqual(result, "red bold")
        else:
            self.assertNotEqual(result, "red bold")

    @settings(max_examples=100)
    @given(st.floats(min_value=0, max_value=100))
    def test_disk_style_red_bold_at_or_above_90(self, pct):
        """_disk_style returns 'red bold' when pct >= 90."""
        result = self.renderer._disk_style(pct)
        if pct >= 90:
            self.assertEqual(result, "red bold")

    @settings(max_examples=100)
    @given(st.floats(min_value=0, max_value=100))
    def test_disk_style_yellow_between_85_and_90(self, pct):
        """_disk_style returns 'yellow' when 85 <= pct < 90."""
        result = self.renderer._disk_style(pct)
        if 85 <= pct < 90:
            self.assertEqual(result, "yellow")

    @settings(max_examples=100)
    @given(st.floats(min_value=0, max_value=100))
    def test_disk_style_default_below_85(self, pct):
        """_disk_style returns default (not red bold, not yellow) when pct < 85."""
        result = self.renderer._disk_style(pct)
        if pct < 85:
            self.assertNotEqual(result, "red bold")
            self.assertNotEqual(result, "yellow")


# ---------------------------------------------------------------------------
# Property 12: Poll counter monotonicity
# ---------------------------------------------------------------------------
from datetime import datetime, timedelta
from commands.estop_commands import DeltaCalculator


@settings(max_examples=100)
@given(
    st.lists(
        st.builds(
            PollSnapshot,
            timestamp=st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2030, 1, 1),
            ),
            cluster_health=st.none(),
            nodes_stats=st.none(),
            cat_indices=st.none(),
            cluster_health_error=st.none(),
            nodes_stats_error=st.none(),
            cat_indices_error=st.none(),
        ),
        min_size=1,
        max_size=20,
    )
)
def test_property_12_poll_counter_monotonicity(snapshots):
    """
    **Validates: Requirements 1.8**

    Property 12: Poll counter monotonicity.
    For any sequence of N calls to DeltaCalculator.process(), the poll_count in
    the returned ProcessedData SHALL equal N (1-based, incrementing by exactly 1
    per call). After reset(), the counter restarts and the next process() call
    returns poll_count = 1.
    """
    # Sort snapshots by timestamp to ensure monotonically increasing order
    snapshots = sorted(snapshots, key=lambda s: s.timestamp)

    calc = DeltaCalculator()

    # Process each snapshot and verify poll_count equals 1-based index
    for i, snapshot in enumerate(snapshots, start=1):
        result = calc.process(snapshot)
        assert result.poll_count == i, (
            f"Expected poll_count={i} after {i} calls, got {result.poll_count}"
        )

    # After reset(), the next process() call should return poll_count = 1
    calc.reset()
    extra_snapshot = snapshots[-1]
    result_after_reset = calc.process(extra_snapshot)
    assert result_after_reset.poll_count == 1, (
        f"Expected poll_count=1 after reset(), got {result_after_reset.poll_count}"
    )


# ---------------------------------------------------------------------------
# Unit tests for DeltaCalculator
# Requirements: 5.1, 5.2, 5.3, 8.1, 8.2, 8.3, 8.4, 8.5, 1.7, 1.8
# ---------------------------------------------------------------------------
from datetime import datetime, timedelta
from commands.estop_commands import DeltaCalculator, PollSnapshot


def _make_snapshot(timestamp, indices=None, health=None, nodes=None):
    """Helper: build a PollSnapshot with optional cat_indices list."""
    return PollSnapshot(
        timestamp=timestamp,
        cluster_health=health,
        nodes_stats=nodes,
        cat_indices=indices,
    )


def _index_row(name, docs=0, searches=0, index_total=None, store="1mb"):
    row = {
        "index": name,
        "docs.count": str(docs),
        "search.query_total": str(searches),
        "store.size": store,
        "pri": "1",
        "rep": "0",
    }
    if index_total is not None:
        row["indexing.index_total"] = str(index_total)
    return row


T0 = datetime(2024, 1, 1, 12, 0, 0)


# --- First poll behaviour ---

def test_delta_calculator_first_poll_is_first_poll_true():
    calc = DeltaCalculator()
    snap = _make_snapshot(T0, indices=[_index_row("my-index", docs=100)])
    result = calc.process(snap)
    assert result.is_first_poll is True
    assert result.top_indices == []


def test_delta_calculator_first_poll_poll_count_is_one():
    calc = DeltaCalculator()
    snap = _make_snapshot(T0, indices=[_index_row("my-index", docs=100)])
    result = calc.process(snap)
    assert result.poll_count == 1


# --- Poll count increments ---

def test_delta_calculator_poll_count_increments():
    calc = DeltaCalculator()
    t = T0
    counts = []
    for i in range(3):
        snap = _make_snapshot(t + timedelta(seconds=30 * i), indices=[_index_row("idx", docs=i * 10)])
        result = calc.process(snap)
        counts.append(result.poll_count)
    assert counts == [1, 2, 3]


# --- Reset behaviour ---

def test_delta_calculator_reset_clears_state():
    calc = DeltaCalculator()
    snap1 = _make_snapshot(T0, indices=[_index_row("idx", docs=100)])
    snap2 = _make_snapshot(T0 + timedelta(seconds=30), indices=[_index_row("idx", docs=200)])
    calc.process(snap1)
    calc.process(snap2)

    calc.reset()

    assert calc._prior is None
    assert calc._session_totals == {}
    assert calc._poll_count == 0


def test_delta_calculator_reset_then_process_restarts_count():
    calc = DeltaCalculator()
    snap1 = _make_snapshot(T0, indices=[_index_row("idx", docs=100)])
    snap2 = _make_snapshot(T0 + timedelta(seconds=30), indices=[_index_row("idx", docs=200)])
    calc.process(snap1)
    calc.process(snap2)

    calc.reset()

    snap3 = _make_snapshot(T0 + timedelta(seconds=60), indices=[_index_row("idx", docs=300)])
    result = calc.process(snap3)
    assert result.poll_count == 1
    assert result.is_first_poll is True


# --- Elapsed time from timestamps ---

def test_delta_calculator_elapsed_from_timestamps():
    """docs_per_sec must use the 60-second gap between snapshot timestamps."""
    calc = DeltaCalculator()
    snap1 = _make_snapshot(T0, indices=[_index_row("idx", docs=0, index_total=0)])
    snap2 = _make_snapshot(T0 + timedelta(seconds=60), indices=[_index_row("idx", docs=120, index_total=120)])

    calc.process(snap1)
    result = calc.process(snap2)

    idx_delta = next(d for d in result.top_indices if d.index_name == "idx")
    expected = 120 / 60.0
    assert abs(idx_delta.docs_per_sec - expected) < 1e-9


# --- Second poll has rates ---

def test_delta_calculator_second_poll_has_rates():
    calc = DeltaCalculator()
    snap1 = _make_snapshot(T0, indices=[_index_row("idx", docs=0, index_total=0)])
    snap2 = _make_snapshot(T0 + timedelta(seconds=30), indices=[_index_row("idx", docs=60, index_total=60)])

    calc.process(snap1)
    result = calc.process(snap2)

    assert result.is_first_poll is False
    assert len(result.top_indices) > 0
    idx_delta = next(d for d in result.top_indices if d.index_name == "idx")
    assert abs(idx_delta.docs_per_sec - 2.0) < 1e-9


# --- Session totals accumulate ---

def test_delta_calculator_session_totals_accumulate():
    """session_docs should equal the sum of all per-cycle doc deltas."""
    calc = DeltaCalculator()
    # Cycle 0 → 100 docs, Cycle 1 → 200 docs (+100), Cycle 2 → 350 docs (+150)
    doc_counts = [100, 200, 350]
    for i, docs in enumerate(doc_counts):
        snap = _make_snapshot(
            T0 + timedelta(seconds=30 * i),
            indices=[_index_row("idx", docs=docs, index_total=docs)],
        )
        result = calc.process(snap)

    # Total delta = 350 - 100 = 250 (first poll seeds nothing, deltas start from poll 2)
    idx_delta = next(d for d in result.top_indices if d.index_name == "idx")
    assert idx_delta.session_docs == 250


# --- Disappeared index omitted from top_indices ---

def test_delta_calculator_disappeared_index_omitted_from_top_indices():
    calc = DeltaCalculator()
    snap1 = _make_snapshot(
        T0,
        indices=[
            _index_row("a", docs=100, index_total=100),
            _index_row("b", docs=50, index_total=50),
        ],
    )
    snap2 = _make_snapshot(
        T0 + timedelta(seconds=30),
        indices=[_index_row("a", docs=200, index_total=200)],  # "b" gone
    )

    calc.process(snap1)
    result = calc.process(snap2)

    names = [d.index_name for d in result.top_indices]
    assert "b" not in names
    assert "a" in names


# --- New index gets zero rates ---

def test_delta_calculator_new_index_zero_rates():
    calc = DeltaCalculator()
    snap1 = _make_snapshot(T0, indices=[_index_row("a", docs=100, index_total=100)])
    snap2 = _make_snapshot(
        T0 + timedelta(seconds=30),
        indices=[
            _index_row("a", docs=200, index_total=200),
            _index_row("b", docs=50, index_total=50),  # new index
        ],
    )

    calc.process(snap1)
    result = calc.process(snap2)

    b_deltas = [d for d in result.top_indices if d.index_name == "b"]
    # "b" may or may not appear in top_indices depending on session_docs filter,
    # but if it does appear its rates must be zero
    for d in b_deltas:
        assert d.docs_per_sec == 0.0
        assert d.searches_per_sec == 0.0


# ---------------------------------------------------------------------------
# Property 2: Rate computation formula
# Validates: Requirements 5.1, 5.2, 8.2, 8.6
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.lists(
        st.fixed_dictionaries({
            "name": st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-_")),
            "prior_docs": st.integers(min_value=0, max_value=1_000_000),
            "prior_searches": st.integers(min_value=0, max_value=1_000_000),
            "doc_delta": st.integers(min_value=0, max_value=100_000),
            "search_delta": st.integers(min_value=0, max_value=100_000),
        }),
        min_size=1,
        max_size=10,
        unique_by=lambda x: x["name"],
    ),
    st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)),
    st.timedeltas(min_value=timedelta(seconds=1), max_value=timedelta(days=1)),
)
def test_property_2_rate_computation_formula(index_entries, prior_ts, elapsed_td):
    """
    **Validates: Requirements 5.1, 5.2, 8.2, 8.6**

    Property 2: Rate computation formula.
    For any valid pair of successive PollSnapshots with generated doc/search counts
    and a timedelta >= 1 second between timestamps, verify:
      docs_per_sec == (curr_docs - prior_docs) / elapsed_seconds
      searches_per_sec == (curr_searches - prior_searches) / elapsed_seconds
    for each index in the result's top_indices.
    """
    current_ts = prior_ts + elapsed_td
    elapsed_seconds = elapsed_td.total_seconds()

    # Build prior and current cat_indices rows (no indexing.index_total so code uses docs.count)
    prior_rows = []
    current_rows = []
    expected = {}

    for entry in index_entries:
        name = entry["name"]
        p_docs = entry["prior_docs"]
        p_searches = entry["prior_searches"]
        c_docs = p_docs + entry["doc_delta"]
        c_searches = p_searches + entry["search_delta"]

        prior_rows.append({
            "index": name,
            "docs.count": str(p_docs),
            "search.query_total": str(p_searches),
            "store.size": "1mb",
            "pri": "1",
            "rep": "0",
        })
        current_rows.append({
            "index": name,
            "docs.count": str(c_docs),
            "search.query_total": str(c_searches),
            "store.size": "1mb",
            "pri": "1",
            "rep": "0",
        })
        expected[name] = {
            "docs_per_sec": entry["doc_delta"] / elapsed_seconds,
            "searches_per_sec": entry["search_delta"] / elapsed_seconds,
        }

    prior_snapshot = PollSnapshot(
        timestamp=prior_ts,
        cluster_health=None,
        nodes_stats=None,
        cat_indices=prior_rows,
    )
    current_snapshot = PollSnapshot(
        timestamp=current_ts,
        cluster_health=None,
        nodes_stats=None,
        cat_indices=current_rows,
    )

    calc = DeltaCalculator()
    calc.process(prior_snapshot)
    result = calc.process(current_snapshot)

    # Verify formula for each index that appears in top_indices
    result_map = {d.index_name: d for d in result.top_indices}
    for entry in index_entries:
        name = entry["name"]
        if name not in result_map:
            # Index may be filtered out if session_docs == 0 and session_searches == 0
            # (i.e., both doc_delta and search_delta are 0 and prior counts are 0)
            # This is valid behaviour per the active-index filter
            continue
        delta = result_map[name]
        exp = expected[name]
        assert abs(delta.docs_per_sec - exp["docs_per_sec"]) < 1e-9, (
            f"Index '{name}': expected docs_per_sec={exp['docs_per_sec']}, "
            f"got {delta.docs_per_sec} (doc_delta={entry['doc_delta']}, elapsed={elapsed_seconds})"
        )
        assert abs(delta.searches_per_sec - exp["searches_per_sec"]) < 1e-9, (
            f"Index '{name}': expected searches_per_sec={exp['searches_per_sec']}, "
            f"got {delta.searches_per_sec} (search_delta={entry['search_delta']}, elapsed={elapsed_seconds})"
        )
