"""
Property-based tests for restored_index_manager.py

Feature: server-v2-modernization, Property 8: Restored index cleanup decision
Validates: Requirements 6.3, 6.4
"""

import datetime
import logging

from hypothesis import given, settings
from hypothesis import strategies as st

from server.restored_index_manager import process_restored_indices


# ---------------------------------------------------------------------------
# Fake ES infrastructure for testing
# ---------------------------------------------------------------------------

class FakeIndices(object):
    """Fake Elasticsearch indices namespace."""

    def __init__(self, existing_indices):
        self._existing = set(existing_indices)

    def exists(self, index):
        return index in self._existing


class FakeES(object):
    """Fake low-level Elasticsearch client."""

    def __init__(self, existing_indices):
        self.indices = FakeIndices(existing_indices)
        self.deleted_docs = []

    def delete(self, index, id):
        self.deleted_docs.append({"index": index, "id": id})
        return {"result": "deleted"}


class FakeESClient(object):
    """Fake ESClient wrapper for process_restored_indices."""

    def __init__(self, existing_indices, scroll_hits):
        self.es = FakeES(existing_indices)
        self._scroll_hits = scroll_hits
        self.deleted_indices = []

    def search_scroll(self, index_name, query, scroll_timeout="2m", batch_size=100):
        return self._scroll_hits

    def delete_index(self, index_name):
        self.deleted_indices.append(index_name)
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_logger():
    logger = logging.getLogger("test-restored-index-properties")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Index name components
_INDEX_PREFIXES = ["logs", "metrics", "audit", "system", "app", "data"]

_index_name_st = st.builds(
    lambda prefix, suffix: "%s-%05d" % (prefix, suffix),
    st.sampled_from(_INDEX_PREFIXES),
    st.integers(min_value=0, max_value=9999),
)

# Age in days for a tracking record (0 to ~10 years)
_age_days_st = st.integers(min_value=0, max_value=3650)

# max_days configuration value (1 to 365)
_max_days_st = st.integers(min_value=1, max_value=365)

# A single tracking record: (index_name, age_in_days)
_record_st = st.tuples(_index_name_st, _age_days_st)

# List of tracking records (0-15 records)
_records_st = st.lists(_record_st, min_size=0, max_size=15)

# Fraction of indices that actually exist in the cluster (0.0 to 1.0)
_exist_fraction_st = st.floats(min_value=0.0, max_value=1.0)


def _build_test_scenario(records, exist_fraction, max_days, frozen_now):
    """Build scroll hits, existing indices set, and expected outcomes.

    Returns:
        (scroll_hits, existing_indices, expected_deleted_indices,
         expected_stale_removals, expected_skipped)
    """
    scroll_hits = []
    all_index_names = []
    record_ages = {}  # index_name -> age_days

    for i, (index_name, age_days) in enumerate(records):
        # Deduplicate: skip if we already have this index_name
        if index_name in record_ages:
            continue

        record_ages[index_name] = age_days

        # Build a restore_date that is age_days old from frozen_now
        restore_dt = frozen_now - datetime.timedelta(days=age_days, hours=1)
        restore_date_str = restore_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        doc_id = "doc_%d" % i
        scroll_hits.append({
            "_id": doc_id,
            "_source": {
                "index_name": index_name,
                "restore_date": restore_date_str,
            },
        })
        all_index_names.append(index_name)

    # Determine which indices "exist" in the cluster based on exist_fraction
    # Use a deterministic split: first N indices exist
    n_exist = int(len(all_index_names) * exist_fraction)
    existing_indices = set(all_index_names[:n_exist])

    # Compute expected outcomes
    expected_deleted_indices = set()   # indices deleted from cluster
    expected_stale_removals = set()    # stale record removals (index gone)
    expected_skipped = set()           # young indices, left alone

    for index_name in all_index_names:
        age = record_ages[index_name]
        if index_name not in existing_indices:
            # Stale: index doesn't exist -> record removed
            expected_stale_removals.add(index_name)
        elif age >= max_days:
            # Expired: index exists and old enough -> delete index + remove record
            expected_deleted_indices.add(index_name)
        else:
            # Young: index exists and age < max_days -> skip
            expected_skipped.add(index_name)

    return (
        scroll_hits,
        existing_indices,
        expected_deleted_indices,
        expected_stale_removals,
        expected_skipped,
    )


# ---------------------------------------------------------------------------
# Property Test
# ---------------------------------------------------------------------------

@given(
    records=_records_st,
    exist_fraction=_exist_fraction_st,
    max_days=_max_days_st,
)
@settings(max_examples=200)
def test_restored_index_cleanup_decision(records, exist_fraction, max_days):
    """
    Property 8: Restored index cleanup decision

    For any set of tracking index records (each with index_name and
    restore_date) and any set of indices currently existing in the cluster,
    the cleanup logic should:
      (a) mark for deletion any record whose index exists and whose
          age >= max_days,
      (b) mark for removal any record whose index does not exist in the
          cluster (stale record),
      (c) no record with age < max_days and an existing index should be
          marked for any action.

    **Validates: Requirements 6.3, 6.4**
    """
    # Use a fixed "now" to eliminate timing drift between building test data
    # and the function's internal datetime.now() call
    frozen_now = datetime.datetime(2025, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)

    (
        scroll_hits,
        existing_indices,
        expected_deleted_indices,
        expected_stale_removals,
        expected_skipped,
    ) = _build_test_scenario(records, exist_fraction, max_days, frozen_now)

    # Build the fake ES client
    es = FakeESClient(
        existing_indices=existing_indices,
        scroll_hits=scroll_hits,
    )
    logger = _make_logger()

    # Patch datetime so calculate_days_since_restore uses our frozen_now
    import server.restored_index_manager as rim_module
    _orig_dt = rim_module.datetime

    class FrozenDatetime(object):
        """Proxy that freezes 'now' and 'utcnow' to frozen_now."""
        timezone = datetime.timezone

        class datetime(object):
            timezone = datetime.timezone

            @staticmethod
            def now(tz=None):
                return frozen_now

            @staticmethod
            def utcnow():
                return frozen_now.replace(tzinfo=None)

            @staticmethod
            def strptime(date_string, fmt):
                return datetime.datetime.strptime(date_string, fmt)

    rim_module.datetime = FrozenDatetime
    try:
        processed, deleted, errors = process_restored_indices(
            es, "rc_snapshots", max_days, logger, dry_run=False
        )
    finally:
        rim_module.datetime = _orig_dt

    # Total unique records processed
    unique_count = len(scroll_hits)

    # --- Assertions ---

    # 1. processed_count should equal the number of unique records
    assert processed == unique_count, (
        "processed mismatch: expected=%d, got=%d" % (unique_count, processed)
    )

    # 2. deleted_count = stale removals + expired deletions
    expected_deleted_count = len(expected_stale_removals) + len(expected_deleted_indices)
    assert deleted == expected_deleted_count, (
        "deleted mismatch: expected=%d (stale=%d + expired=%d), got=%d"
        % (
            expected_deleted_count,
            len(expected_stale_removals),
            len(expected_deleted_indices),
            deleted,
        )
    )

    # 3. No errors expected with our fake client
    assert errors == 0, "unexpected errors: %d" % errors

    # 4. Indices actually deleted from cluster = only expired ones
    assert set(es.deleted_indices) == expected_deleted_indices, (
        "deleted indices mismatch.\n"
        "  Expected: %s\n  Got: %s"
        % (expected_deleted_indices, set(es.deleted_indices))
    )

    # 5. Stale record removals: docs deleted from tracking index for
    #    non-existing indices
    stale_removed_ids = set()
    expired_removed_ids = set()
    for doc in es.es.deleted_docs:
        # Find which index_name this doc_id corresponds to
        for hit in scroll_hits:
            if hit["_id"] == doc["id"]:
                idx_name = hit["_source"]["index_name"]
                if idx_name in expected_stale_removals:
                    stale_removed_ids.add(idx_name)
                elif idx_name in expected_deleted_indices:
                    expired_removed_ids.add(idx_name)
                break

    assert stale_removed_ids == expected_stale_removals, (
        "stale removal mismatch.\n"
        "  Expected: %s\n  Got: %s"
        % (expected_stale_removals, stale_removed_ids)
    )

    assert expired_removed_ids == expected_deleted_indices, (
        "expired record removal mismatch.\n"
        "  Expected: %s\n  Got: %s"
        % (expected_deleted_indices, expired_removed_ids)
    )

    # 6. Skipped indices: should NOT appear in any deletion list
    for idx_name in expected_skipped:
        assert idx_name not in es.deleted_indices, (
            "Young index %s was incorrectly deleted" % idx_name
        )
        deleted_doc_indices = set()
        for doc in es.es.deleted_docs:
            for hit in scroll_hits:
                if hit["_id"] == doc["id"]:
                    deleted_doc_indices.add(hit["_source"]["index_name"])
                    break
        assert idx_name not in deleted_doc_indices, (
            "Young index %s had its tracking record incorrectly removed"
            % idx_name
        )
