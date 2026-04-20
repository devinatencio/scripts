"""
Property-based tests for retention_enforcer.py

Feature: server-v2-modernization, Property 6: Age calculation correctness
Validates: Requirements 5.1, 6.2
"""

import time
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from server.retention_enforcer import calculate_snapshot_age_days


# --- Strategies ---

# Generate a number of days in the past (0 to ~3650 days ≈ 10 years)
days_ago_st = st.integers(min_value=0, max_value=3650)

# Additional intra-day offset in seconds (0 to 86399)
intra_day_offset_st = st.integers(min_value=0, max_value=86399)


# --- Property Test ---

@given(
    days_ago=days_ago_st,
    extra_seconds=intra_day_offset_st,
)
@settings(max_examples=200)
def test_age_calculation_correctness(days_ago, extra_seconds):
    """
    Property 6: Age calculation correctness

    For any past epoch timestamp, calculate_snapshot_age_days should return
    a non-negative integer equal to the floor of the difference in days
    between the current time and that epoch.

    We freeze time.time() to a fixed value so there is no drift between
    the epoch generation and the function call.

    **Validates: Requirements 5.1, 6.2**
    """
    # Use a fixed "now" to eliminate timing drift
    frozen_now = 1_750_000_000  # a recent-ish epoch

    # Build the past epoch: frozen_now minus (days_ago full days + extra seconds)
    past_epoch = frozen_now - (days_ago * 86400) - extra_seconds

    # Freeze time.time inside the retention_enforcer module
    with patch("server.retention_enforcer.time.time", return_value=float(frozen_now)):
        result = calculate_snapshot_age_days(str(past_epoch))

    # Expected: floor((frozen_now - past_epoch) / 86400)
    expected = (frozen_now - past_epoch) // 86400

    assert result == expected, (
        "Age mismatch: days_ago=%d, extra_seconds=%d, "
        "past_epoch=%d, expected=%d, got=%d"
        % (days_ago, extra_seconds, past_epoch, expected, result)
    )

    # The result must always be non-negative
    assert result >= 0, "Age should be non-negative, got %d" % result

    # The result must be an integer (floor division)
    assert isinstance(result, int), "Age should be an int, got %r" % type(result)


# ---------------------------------------------------------------------------
# Property 7: Retention enforcement decision
# Feature: server-v2-modernization, Property 7: Retention enforcement decision
# Validates: Requirements 5.2, 5.3, 5.4
# ---------------------------------------------------------------------------

from server.retention_enforcer import (
    get_retention_days,
    process_snapshots_for_deletion,
)

# --- Strategies for Property 7 ---

# Safe prefix strings for building snapshot names and regex patterns
_PREFIXES = ["logs", "metrics", "audit", "system", "app", "data"]

# Strategy: a simple prefix-based retention policy entry
# Produces tuples of (prefix, max_days) where the regex is "prefix-.*"
_retention_entry_st = st.tuples(
    st.sampled_from(_PREFIXES),
    st.integers(min_value=1, max_value=3650),
)

# Strategy: a retention policy dict with 0-4 entries (prefix-based regexes)
_retention_policies_st = (
    st.lists(_retention_entry_st, min_size=0, max_size=4, unique_by=lambda x: x[0])
    .map(lambda entries: {p + "-.*": d for p, d in entries})
)

# Strategy: default retention days
_default_days_st = st.integers(min_value=1, max_value=3650)

# Strategy: a single snapshot entry
# Produces (snapshot_name, days_old) where days_old controls the epoch
_snapshot_entry_st = st.tuples(
    # Optionally pick a prefix that may match a policy, or use a random one
    st.sampled_from(_PREFIXES + ["other", "unknown"]),
    # A suffix to make names unique
    st.integers(min_value=0, max_value=9999),
    # Age in days (0 to ~20 years, but practically bounded)
    st.integers(min_value=0, max_value=7300),
)

# Strategy: list of snapshot entries (0-10 snapshots)
_snapshot_entries_st = st.lists(_snapshot_entry_st, min_size=0, max_size=10)


def _build_test_data(snapshot_entries, frozen_now):
    """Build a snapshots dict from generated entries, using frozen_now as reference."""
    snapshots = {}
    for prefix, suffix, age_days in snapshot_entries:
        name = "snapshot_%s-%05d" % (prefix, suffix)
        # Avoid duplicate names by skipping if already present
        if name in snapshots:
            continue
        epoch = frozen_now - (age_days * 86400)
        snapshots[name] = {"start_epoch": str(epoch)}
    return snapshots


def _expected_deletions(snapshots, retention_policies, default_days, frozen_now):
    """Manually compute which snapshots should be deleted."""
    expected = {}
    for snap_name, meta in snapshots.items():
        start_epoch = int(meta["start_epoch"])
        age_days = (frozen_now - start_epoch) // 86400

        retention = get_retention_days(snap_name, retention_policies, default_days)

        if age_days > retention:
            expected[snap_name] = age_days
    return expected


@given(
    snapshot_entries=_snapshot_entries_st,
    retention_policies=_retention_policies_st,
    default_days=_default_days_st,
)
@settings(max_examples=200)
def test_retention_enforcement_decision(snapshot_entries, retention_policies, default_days):
    """
    Property 7: Retention enforcement decision

    For any list of snapshots (each with a name and start epoch), any
    retention policy dict (mapping regex patterns to max_days), and any
    default retention days value, process_snapshots_for_deletion should
    return exactly those snapshots whose age exceeds the applicable
    retention period — where the applicable period is the max_days of
    the first matching regex pattern, or the default if no pattern matches.

    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    frozen_now = 1_750_000_000

    snapshots = _build_test_data(snapshot_entries, frozen_now)

    with patch("server.retention_enforcer.time.time", return_value=float(frozen_now)):
        result = process_snapshots_for_deletion(
            snapshots, retention_policies, default_days
        )

    expected = _expected_deletions(snapshots, retention_policies, default_days, frozen_now)

    # The deletion set must match exactly
    assert set(result.keys()) == set(expected.keys()), (
        "Deletion set mismatch.\n"
        "  Extra in result: %s\n"
        "  Missing from result: %s"
        % (
            set(result.keys()) - set(expected.keys()),
            set(expected.keys()) - set(result.keys()),
        )
    )

    # Age values must also match
    for snap_name in expected:
        assert result[snap_name] == expected[snap_name], (
            "Age mismatch for %s: expected=%d, got=%d"
            % (snap_name, expected[snap_name], result[snap_name])
        )
