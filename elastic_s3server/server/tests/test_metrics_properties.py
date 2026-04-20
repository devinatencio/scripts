"""
Property-based tests for metrics_collector.py

Feature: server-v2-modernization, Property 11: Metrics JSON round-trip integrity
Validates: Requirements 10.1, 10.2, 10.3, 10.4
"""

import os
import shutil
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from server.metrics_collector import (
    read_metrics,
    write_metrics,
    increment_counter,
)


# --- Strategies ---

# Counter names that exist in the default daily_counters structure
counter_name_st = st.sampled_from([
    'snapshots_created',
    'snapshots_deleted',
    'indices_deleted_ilm',
])

# Date strings in YYYY-MM-DD format
date_st = st.dates().map(lambda d: d.strftime('%Y-%m-%d'))

# Daily counters section
daily_counters_st = st.builds(
    lambda date, sc, sd, idi, ts: {
        'date': date,
        'snapshots_created': sc,
        'snapshots_deleted': sd,
        'indices_deleted_ilm': idi,
        'total_snapshots': ts,
    },
    date=date_st,
    sc=st.integers(min_value=0, max_value=100000),
    sd=st.integers(min_value=0, max_value=100000),
    idi=st.integers(min_value=0, max_value=100000),
    ts=st.integers(min_value=0, max_value=100000),
)

# Utility name for health entries
utility_name_st = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_"),
    min_size=1,
    max_size=30,
)

# Single health entry
health_entry_st = st.fixed_dictionaries({
    'last_run': st.text(
        alphabet=st.sampled_from("0123456789-T:"),
        min_size=10,
        max_size=25,
    ),
    'success': st.booleans(),
})

# Utility health section: dict of utility_name -> health entry
utility_health_st = st.dictionaries(
    keys=utility_name_st,
    values=health_entry_st,
    min_size=0,
    max_size=5,
)

# Snapshot status keys
snapshot_statuses_st = st.fixed_dictionaries({
    'SUCCESS': st.integers(min_value=0, max_value=100000),
    'FAILED': st.integers(min_value=0, max_value=100000),
    'PARTIAL': st.integers(min_value=0, max_value=100000),
    'IN_PROGRESS': st.integers(min_value=0, max_value=100000),
    'INCOMPATIBLE': st.integers(min_value=0, max_value=100000),
})

# Full valid metrics dict
metrics_dict_st = st.fixed_dictionaries({
    'daily_counters': daily_counters_st,
    'utility_health': utility_health_st,
    'snapshot_statuses': snapshot_statuses_st,
})

# Increment operation: (counter_name, amount)
increment_op_st = st.tuples(
    counter_name_st,
    st.integers(min_value=1, max_value=1000),
)


# --- Property Tests ---

@given(metrics_data=metrics_dict_st)
@settings(max_examples=200)
def test_metrics_write_read_round_trip(metrics_data):
    """
    Property 11a: Metrics JSON round-trip integrity (write/read)

    For any valid metrics dictionary containing daily_counters,
    utility_health, and snapshot_statuses, writing it via write_metrics
    and reading it back via read_metrics should produce an identical
    dictionary.

    **Validates: Requirements 10.1, 10.2, 10.3, 10.4**
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        metrics_file = os.path.join(tmp_dir, 'metrics', 'test_metrics.json')
        write_metrics(metrics_file, metrics_data)
        loaded = read_metrics(metrics_file)
        assert loaded == metrics_data, (
            "Round-trip mismatch:\n  written: %r\n  read:    %r"
            % (metrics_data, loaded)
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@given(
    increments=st.lists(increment_op_st, min_size=1, max_size=20),
)
@settings(max_examples=200)
def test_increment_counter_cumulative_sums(increments):
    """
    Property 11b: Increment counter cumulative sums

    For any sequence of increment_counter calls, the final counters in
    the metrics file should reflect the cumulative sum of all increments
    for each counter name.

    **Validates: Requirements 10.1, 10.2, 10.3, 10.4**
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        metrics_file = os.path.join(tmp_dir, 'metrics', 'test_metrics.json')

        # Compute expected cumulative sums
        expected_sums = {
            'snapshots_created': 0,
            'snapshots_deleted': 0,
            'indices_deleted_ilm': 0,
        }
        for counter_name, amount in increments:
            expected_sums[counter_name] += amount

        # Apply all increments
        for counter_name, amount in increments:
            increment_counter(metrics_file, counter_name, amount)

        # Read back and verify
        result = read_metrics(metrics_file)
        counters = result['daily_counters']

        for name, expected in expected_sums.items():
            actual = counters.get(name, 0)
            assert actual == expected, (
                "Counter '%s': expected %d, got %d after increments %r"
                % (name, expected, actual, increments)
            )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
