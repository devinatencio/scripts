"""
Property-based tests for retry_with_backoff in es_client.py

Feature: server-v2-modernization, Property 10: Retry with exponential backoff
Validates: Requirements 3.2, 6.5
"""

from unittest.mock import patch, call

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from server.es_client import retry_with_backoff


# --- Strategies ---

max_retries_st = st.integers(min_value=1, max_value=10)
delay_st = st.floats(min_value=0.01, max_value=5.0, allow_nan=False, allow_infinity=False)


# --- Property Test ---

@given(
    max_retries=max_retries_st,
    delay=delay_st,
)
@settings(max_examples=200)
def test_retry_with_exponential_backoff(max_retries, delay):
    """
    Property 10: Retry with exponential backoff

    For any max_retries (1-10) and initial delay, when an operation fails on
    every attempt, the retry mechanism should:
      (a) attempt exactly max_retries + 1 total calls,
      (b) apply delays following the pattern delay * 2^attempt for each retry,
      (c) raise the last exception after all attempts are exhausted.

    **Validates: Requirements 3.2, 6.5**
    """
    error = RuntimeError("always fails")
    call_count = [0]

    def failing_func():
        call_count[0] += 1
        raise error

    with patch("server.es_client.time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError) as exc_info:
            retry_with_backoff(failing_func, max_retries, delay)

        # (c) The last exception is raised
        assert exc_info.value is error

    # (a) Exactly max_retries + 1 total calls
    assert call_count[0] == max_retries + 1, (
        "Expected %d total calls, got %d" % (max_retries + 1, call_count[0])
    )

    # (b) Delays follow delay * 2^attempt pattern
    expected_sleep_calls = [
        call(delay * (2 ** attempt))
        for attempt in range(max_retries)
    ]
    assert mock_sleep.call_count == max_retries, (
        "Expected %d sleep calls, got %d" % (max_retries, mock_sleep.call_count)
    )
    mock_sleep.assert_has_calls(expected_sleep_calls)
