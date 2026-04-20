"""
Property-based tests for cold_snapshots.py

Feature: server-v2-modernization, Property 4: Cold indices needing backup identification
Validates: Requirements 4.2
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from server.cold_snapshots import get_cold_indices_needing_backup


# --- Strategies ---

# Index names: realistic Elasticsearch index name characters
index_name_st = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_."),
    min_size=1,
    max_size=40,
).filter(lambda s: s[0].isalnum())

# Lists of unique index names
cold_indices_st = st.lists(index_name_st, min_size=0, max_size=20, unique=True)

# Snapshot IDs: mix of snapshot_{name} formatted and arbitrary names
snapshot_id_st = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_."),
    min_size=1,
    max_size=60,
)

snapshot_list_st = st.lists(snapshot_id_st, min_size=0, max_size=30)


# --- Property Test ---

@given(
    cold_indices=cold_indices_st,
    extra_snapshots=snapshot_list_st,
)
@settings(max_examples=200)
def test_cold_indices_needing_backup_exact_set(cold_indices, extra_snapshots):
    """
    Property 4: Cold indices needing backup identification

    For any list of cold index names and any list of existing snapshot IDs,
    get_cold_indices_needing_backup should return exactly those cold indices
    for which no snapshot with the name snapshot_{index_name} exists in the
    snapshot list.

    **Validates: Requirements 4.2**
    """
    # Build the full snapshot list: extra_snapshots may or may not contain
    # snapshot_{name} entries for some cold indices
    existing_snapshots = list(extra_snapshots)

    result = get_cold_indices_needing_backup(cold_indices, existing_snapshots)

    snapshot_set = set(existing_snapshots)

    # Compute the expected set: cold indices without a matching snapshot
    expected = [
        idx for idx in cold_indices
        if ('snapshot_%s' % idx) not in snapshot_set
    ]

    assert result == expected, (
        "Mismatch:\n  cold_indices=%r\n  existing_snapshots=%r\n"
        "  expected=%r\n  got=%r"
        % (cold_indices, existing_snapshots, expected, result)
    )


@given(
    cold_indices=cold_indices_st,
)
@settings(max_examples=200)
def test_all_backed_up_returns_empty(cold_indices):
    """
    Property 4 (corollary): When every cold index has a matching snapshot,
    the result should be empty.

    **Validates: Requirements 4.2**
    """
    # Build a snapshot list that covers every cold index
    existing_snapshots = ['snapshot_%s' % idx for idx in cold_indices]

    result = get_cold_indices_needing_backup(cold_indices, existing_snapshots)

    assert result == [], (
        "Expected empty list when all indices are backed up, got %r" % result
    )


@given(
    cold_indices=cold_indices_st,
)
@settings(max_examples=200)
def test_none_backed_up_returns_all(cold_indices):
    """
    Property 4 (corollary): When no snapshots exist, all cold indices
    should be returned.

    **Validates: Requirements 4.2**
    """
    result = get_cold_indices_needing_backup(cold_indices, [])

    assert result == cold_indices, (
        "Expected all cold indices when no snapshots exist.\n"
        "  cold_indices=%r\n  got=%r"
        % (cold_indices, result)
    )
