"""Unit tests for index_traffic_analyzer."""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from processors.index_traffic_analyzer import analyze_index_traffic


def _row(name: str, docs: int, store: int = 0) -> dict:
    return {
        "index": name,
        "health": "green",
        "status": "open",
        "docs.count": docs,
        "store.size": store,
    }


class TestIndexTrafficAnalyzer(unittest.TestCase):
    def test_flags_high_doc_outlier(self):
        base = "logs-foo"
        indices = [
            _row(f"{base}-2026.03.01-000001", 20_000_000, 10_000_000_000),
            _row(f"{base}-2026.03.08-000002", 19_000_000, 9_500_000_000),
            _row(f"{base}-2026.03.15-000003", 21_000_000, 10_500_000_000),
            _row(f"{base}-2026.03.22-000004", 110_000_000, 50_000_000_000),
        ]
        result = analyze_index_traffic(indices, min_peers=1, min_ratio=2.0)
        rows = result["rows"]
        self.assertGreaterEqual(len(rows), 1)
        top = rows[0]
        self.assertTrue(top["index"].endswith("-000004"))
        self.assertGreaterEqual(top["docs_ratio"], 4.0)
        self.assertEqual(result["summary"]["rollover_groups"], 1)

    def test_skips_single_index_groups(self):
        indices = [_row("solo-2026.03.01-000001", 1000)]
        result = analyze_index_traffic(indices, min_peers=1, min_ratio=1.1)
        self.assertEqual(result["rows"], [])

    def test_skips_non_pattern_indices(self):
        indices = [
            _row("no-date-suffix", 1000),
            _row("other", 2000),
        ]
        result = analyze_index_traffic(indices, min_peers=1, min_ratio=1.1)
        self.assertEqual(result["summary"]["skipped_no_date_pattern"], 2)
        self.assertEqual(result["rows"], [])

    def test_top_limits_rows(self):
        base = "x"
        indices = [
            _row(f"{base}-2026.01.01-000001", 10),
            _row(f"{base}-2026.01.08-000002", 10),
            _row(f"{base}-2026.01.15-000003", 100),
            _row(f"{base}-2026.01.22-000004", 90),
        ]
        result = analyze_index_traffic(
            indices, min_peers=1, min_ratio=2.0, top=1, min_docs=0
        )
        self.assertEqual(len(result["rows"]), 1)

    def test_within_days_filters_by_rollover_date(self):
        base = "logs-z"
        indices = [
            _row(f"{base}-2026.03.10-000001", 10),
            _row(f"{base}-2026.03.10-000010", 500),
            _row(f"{base}-2026.03.17-000002", 10),
            _row(f"{base}-2026.03.24-000003", 200),
        ]
        fixed_today = date(2026, 3, 27)
        result = analyze_index_traffic(
            indices,
            min_peers=1,
            min_ratio=2.0,
            within_days=7,
            as_of_date_utc=fixed_today,
            min_docs=0,
        )
        names = {r["index"] for r in result["rows"]}
        self.assertIn(f"{base}-2026.03.24-000003", names)
        self.assertNotIn(f"{base}-2026.03.10-000010", names)
        self.assertEqual(result["summary"]["rollover_date_cutoff_utc"], "2026-03-20")

    def test_min_docs_hides_small_high_ratio_indices(self):
        base = "tiny"
        indices = [
            _row(f"{base}-2026.01.01-000001", 1000),
            _row(f"{base}-2026.01.08-000002", 1000),
            _row(f"{base}-2026.01.15-000003", 50_000),
        ]
        strict = analyze_index_traffic(
            indices, min_peers=1, min_ratio=2.0, min_docs=1_000_000
        )
        self.assertEqual(strict["rows"], [])
        loose = analyze_index_traffic(
            indices, min_peers=1, min_ratio=2.0, min_docs=0
        )
        self.assertEqual(len(loose["rows"]), 1)
        self.assertTrue(loose["rows"][0]["index"].endswith("-000003"))


if __name__ == "__main__":
    unittest.main()
