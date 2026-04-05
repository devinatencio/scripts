"""Unit tests for S3 storage estimate from index rows."""

import unittest
from datetime import date

from processors.s3_storage_estimate import estimate_s3_monthly_storage_cost, GIB


class TestS3StorageEstimate(unittest.TestCase):
    def test_dated_within_window_sums_pri_only(self):
        rows = [
            {
                "index": "logs-2026.04.02-000001",
                "pri.store.size": GIB,
                "store.size": 2 * GIB,
            },
            {
                "index": "logs-2026.04.01-000001",
                "pri.store.size": GIB // 2,
                "store.size": GIB,
            },
        ]
        r = estimate_s3_monthly_storage_cost(
            rows,
            within_days=7,
            buffer_percent=0.0,
            price_per_gib_month_usd=1.0,
            as_of_date_utc=date(2026, 4, 2),
        )
        self.assertEqual(r["bytes"]["total_pri"], GIB + GIB // 2)
        self.assertEqual(r["cost"]["estimated_monthly_usd"], 1.5)
        self.assertEqual(r["cost"]["estimated_month_1_usd"], 1.5)
        self.assertEqual(r["cost"]["estimated_month_2_usd"], 3.0)
        self.assertEqual(r["cost"]["estimated_month_3_usd"], 4.5)
        self.assertEqual(r["cost"]["cumulative_buffered_pri_gib_month_2"], 3.0)
        self.assertEqual(r["cost"]["cumulative_buffered_pri_gib_month_3"], 4.5)
        self.assertEqual(r["bytes"]["cumulative_buffered_pri_month_2"], 2 * (GIB + GIB // 2))
        self.assertEqual(r["bytes"]["cumulative_buffered_pri_month_3"], 3 * (GIB + GIB // 2))
        self.assertEqual(r["counts"]["indices_matched_dated"], 2)
        self.assertEqual(r["counts"]["indices_undated_skipped"], 0)

    def test_excludes_before_cutoff(self):
        rows = [
            {"index": "logs-2026.03.01-000001", "pri.store.size": 100},
            {"index": "logs-2026.04.01-000001", "pri.store.size": 200},
        ]
        r = estimate_s3_monthly_storage_cost(
            rows,
            within_days=30,
            buffer_percent=0.0,
            price_per_gib_month_usd=0.023,
            as_of_date_utc=date(2026, 4, 2),
        )
        self.assertEqual(r["counts"]["indices_matched_dated"], 1)
        self.assertEqual(r["counts"]["indices_excluded_dated_before_cutoff"], 1)
        self.assertEqual(r["bytes"]["total_pri"], 200)

    def test_undated_skipped_by_default(self):
        rows = [
            {"index": "logs-2026.04.02-000001", "pri.store.size": 10},
            {"index": "no-date-index", "pri.store.size": 999},
        ]
        r = estimate_s3_monthly_storage_cost(
            rows,
            within_days=30,
            buffer_percent=0.0,
            price_per_gib_month_usd=1.0,
            as_of_date_utc=date(2026, 4, 2),
        )
        self.assertEqual(r["counts"]["indices_undated_skipped"], 1)
        self.assertEqual(r["bytes"]["total_pri"], 10)

    def test_include_undated(self):
        rows = [
            {"index": "logs-2026.04.02-000001", "pri.store.size": 10},
            {"index": "no-date-index", "pri.store.size": 90},
        ]
        r = estimate_s3_monthly_storage_cost(
            rows,
            within_days=30,
            buffer_percent=0.0,
            price_per_gib_month_usd=1.0,
            include_undated=True,
            as_of_date_utc=date(2026, 4, 2),
        )
        self.assertEqual(r["counts"]["indices_undated_included"], 1)
        self.assertEqual(r["bytes"]["total_pri"], 100)

    def test_buffer_percent(self):
        rows = [
            {"index": "logs-2026.04.02-000001", "pri.store.size": 100},
        ]
        r = estimate_s3_monthly_storage_cost(
            rows,
            within_days=30,
            buffer_percent=10.0,
            price_per_gib_month_usd=1.0,
            as_of_date_utc=date(2026, 4, 2),
        )
        self.assertEqual(r["bytes"]["buffered_pri"], 110)

    def test_invalid_price(self):
        with self.assertRaises(ValueError):
            estimate_s3_monthly_storage_cost(
                [],
                price_per_gib_month_usd=0,
            )

    def test_negative_buffer(self):
        with self.assertRaises(ValueError):
            estimate_s3_monthly_storage_cost(
                [{"index": "logs-2026.04.02-000001", "pri.store.size": 1}],
                buffer_percent=-1.0,
                price_per_gib_month_usd=0.1,
                as_of_date_utc=date(2026, 4, 2),
            )


if __name__ == "__main__":
    unittest.main()
