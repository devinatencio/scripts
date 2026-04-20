"""
Property-based tests for regex pattern filtering in cold_snapshots.py

Feature: server-v2-modernization, Property 5: Regex pattern filtering preserves only matches
Validates: Requirements 4.4, 5.5, 9.3
"""

import re

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

# Safe regex patterns: prefix-based patterns that are always valid
# These mimic real-world usage (e.g., "logs-.*", "metrics-.*")
_PREFIXES = ["logs-", "metrics-", "audit-", "data-", "app-", "sys-", "test-"]

prefix_pattern_st = st.sampled_from(_PREFIXES).map(lambda p: p + ".*")

# Character class patterns like "[a-m].*" or "[0-9].*"
char_class_pattern_st = st.sampled_from([
    "[a-m].*",
    "[n-z].*",
    "[0-9].*",
    "[a-z].*",
    "[a-z0-9].*",
])

# Combine all safe pattern strategies, including the catch-all ".*"
regex_pattern_st = st.one_of(
    prefix_pattern_st,
    char_class_pattern_st,
    st.just(".*"),
)


# --- Property Tests ---

@given(
    cold_indices=cold_indices_st,
    pattern=regex_pattern_st,
)
@settings(max_examples=200)
def test_regex_filter_every_result_matches_pattern(cold_indices, pattern):
    """
    Property 5 (part 1): Every element in the result matches the regex pattern.

    When a regex_pattern is provided, only cold indices matching the pattern
    should appear in the output. We pass an empty snapshot list so that
    snapshot filtering does not interfere.

    **Validates: Requirements 4.4, 5.5, 9.3**
    """
    result = get_cold_indices_needing_backup(cold_indices, [], regex_pattern=pattern)

    for idx in result:
        assert re.match(pattern, idx), (
            "Result contains index %r which does not match pattern %r"
            % (idx, pattern)
        )


@given(
    cold_indices=cold_indices_st,
    pattern=regex_pattern_st,
)
@settings(max_examples=200)
def test_regex_filter_no_matching_element_excluded(cold_indices, pattern):
    """
    Property 5 (part 2): No element matching the pattern from the original
    cold indices list is excluded (assuming no matching snapshot exists).

    Every cold index that matches the pattern should appear in the result
    when there are no existing snapshots.

    **Validates: Requirements 4.4, 5.5, 9.3**
    """
    result = get_cold_indices_needing_backup(cold_indices, [], regex_pattern=pattern)

    expected = [idx for idx in cold_indices if re.match(pattern, idx)]

    assert result == expected, (
        "Mismatch: pattern=%r\n  cold_indices=%r\n  expected=%r\n  got=%r"
        % (pattern, cold_indices, expected, result)
    )


@given(
    cold_indices=cold_indices_st,
    pattern=regex_pattern_st,
)
@settings(max_examples=200)
def test_regex_filter_result_is_subset(cold_indices, pattern):
    """
    Property 5 (corollary): The filtered result is always a subset of the
    original cold indices list, preserving order.

    **Validates: Requirements 4.4, 5.5, 9.3**
    """
    result = get_cold_indices_needing_backup(cold_indices, [], regex_pattern=pattern)

    # Every result element must be in the original list
    for idx in result:
        assert idx in cold_indices, (
            "Result contains %r which is not in cold_indices" % idx
        )

    # Order must be preserved: result should be a subsequence of cold_indices
    result_iter = iter(result)
    current = next(result_iter, None)
    for idx in cold_indices:
        if current is None:
            break
        if idx == current:
            current = next(result_iter, None)

    assert current is None, (
        "Result is not a subsequence of cold_indices.\n"
        "  cold_indices=%r\n  result=%r"
        % (cold_indices, result)
    )
