"""
Property-based tests for ilm_curator.py

Feature: server-v2-modernization, Property 9: ILM curator deletion decision
Validates: Requirements 7.2, 7.3, 7.4
"""

import logging
import time

from hypothesis import given, settings
from hypothesis import strategies as st

from server.ilm_curator import process_indices_for_deletion


# ---------------------------------------------------------------------------
# Fake ES infrastructure for testing
# ---------------------------------------------------------------------------

class FakeESClient(object):
    """Fake ESClient that tracks which indices were deleted."""

    def __init__(self):
        self.deleted_indices = []

    def delete_index(self, index_name):
        self.deleted_indices.append(index_name)
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_logger():
    logger = logging.getLogger("test-ilm-curator-properties")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_STATUSES = ["SUCCESS", "FAILED", "PARTIAL", "IN_PROGRESS"]
_PHASES = ["cold", "hot", "warm"]

# Index name: short identifiers to keep things readable
_INDEX_PREFIXES = ["logs", "metrics", "audit", "system", "app"]

_index_name_st = st.builds(
    lambda prefix, suffix: "%s-%04d" % (prefix, suffix),
    st.sampled_from(_INDEX_PREFIXES),
    st.integers(min_value=0, max_value=999),
)

# A single snapshot metadata entry
_snapshot_entry_st = st.fixed_dictionaries({
    "status": st.sampled_from(_STATUSES),
    "failed_shards": st.sampled_from(["0", 0, "1", "2", "5", 1, 3]),
    "age_hours": st.floats(min_value=0.0, max_value=720.0),
})

# ILM phase for an index
_ilm_phase_st = st.sampled_from(_PHASES)

# A single index entry: (index_name, snapshot_metadata, ilm_phase)
_index_entry_st = st.tuples(_index_name_st, _snapshot_entry_st, _ilm_phase_st)

# List of index entries (0-20)
_entries_st = st.lists(_index_entry_st, min_size=0, max_size=20)

# hours_delay parameter (1-48)
_hours_delay_st = st.integers(min_value=1, max_value=48)


# ---------------------------------------------------------------------------
# Property Test
# ---------------------------------------------------------------------------

@given(
    entries=_entries_st,
    hours_delay=_hours_delay_st,
)
@settings(max_examples=200)
def test_ilm_curator_deletion_decision(entries, hours_delay):
    """
    Property 9: ILM curator deletion decision

    For any set of snapshot metadata entries (each with status,
    failed_shards, and end_epoch) and any set of index ILM data, and any
    hours_delay threshold, the curator should delete a cold index only
    when:
      (a) a matching snapshot exists with status SUCCESS and 0 failed
          shards, AND
      (b) the snapshot's age in hours >= hours_delay.
    All other cold indices should be skipped.

    **Validates: Requirements 7.2, 7.3, 7.4**
    """
    # Freeze time: use a fixed "now" to avoid drift
    frozen_now = 1750000000  # a fixed epoch in seconds

    # Deduplicate entries by index_name (first occurrence wins)
    seen_names = set()
    unique_entries = []
    for index_name, snap_meta, ilm_phase in entries:
        if index_name not in seen_names:
            seen_names.add(index_name)
            unique_entries.append((index_name, snap_meta, ilm_phase))

    # Build snapshots_metadata and ilm_data from the generated entries
    snapshots_metadata = {}
    ilm_data = {}

    for index_name, snap_meta, ilm_phase in unique_entries:
        snapshot_name = "snapshot_%s" % index_name

        # Compute end_epoch from the generated age_hours relative to frozen_now
        age_hours = snap_meta["age_hours"]
        end_epoch = str(int(frozen_now - age_hours * 3600))

        snapshots_metadata[snapshot_name] = {
            "status": snap_meta["status"],
            "failed_shards": snap_meta["failed_shards"],
            "end_epoch": end_epoch,
        }

        ilm_data[index_name] = {
            "phase": ilm_phase,
            "age": "30d",
            "policy": "default",
        }

    # Compute expected deletions manually
    expected_deleted = set()
    expected_skipped = set()

    for index_name, snap_meta, ilm_phase in unique_entries:
        if ilm_phase != "cold":
            # Not a cold index - function skips entirely (no skip count)
            continue

        status = snap_meta["status"]
        failed_shards = snap_meta["failed_shards"]
        age_hours = snap_meta["age_hours"]

        is_success = status == "SUCCESS"
        is_zero_failed = str(failed_shards) == "0"
        is_old_enough = age_hours >= hours_delay

        if is_success and is_zero_failed and is_old_enough:
            expected_deleted.add(index_name)
        else:
            expected_skipped.add(index_name)

    # Patch time.time to return our frozen_now so hours_since_epoch is stable
    import server.ilm_curator as ilm_module
    _orig_time = time.time

    def _frozen_time():
        return float(frozen_now)

    ilm_module.time = type("FakeTime", (), {"time": staticmethod(_frozen_time)})()
    try:
        es = FakeESClient()
        logger = _make_logger()

        deleted_count, skipped_count = process_indices_for_deletion(
            es, snapshots_metadata, ilm_data,
            hours_delay=hours_delay, logger=logger,
        )
    finally:
        ilm_module.time = time

    # --- Assertions ---

    # 1. Deleted indices should be exactly the expected set
    assert set(es.deleted_indices) == expected_deleted, (
        "Deleted indices mismatch.\n"
        "  Expected: %s\n  Got: %s"
        % (expected_deleted, set(es.deleted_indices))
    )

    # 2. deleted_count matches
    assert deleted_count == len(expected_deleted), (
        "deleted_count mismatch: expected=%d, got=%d"
        % (len(expected_deleted), deleted_count)
    )

    # 3. skipped_count matches
    assert skipped_count == len(expected_skipped), (
        "skipped_count mismatch: expected=%d, got=%d"
        % (len(expected_skipped), skipped_count)
    )

    # 4. No index outside expected_deleted was deleted
    for idx in es.deleted_indices:
        assert idx in expected_deleted, (
            "Index %s was deleted but should not have been" % idx
        )

    # 5. No expected-skipped index was deleted
    for idx in expected_skipped:
        assert idx not in es.deleted_indices, (
            "Index %s should have been skipped but was deleted" % idx
        )
