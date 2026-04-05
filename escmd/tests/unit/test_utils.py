"""
Unit tests for utility functions in utils.py

Tests the size conversion and shard sorting utilities that fix the
'size' KeyError when running shards command with -z flag.
"""

import unittest
from utils import (
    convert_size_to_bytes,
    get_shard_size_bytes,
    safe_sort_shards_by_size,
    format_bytes_human_readable,
    validate_size_string
)


class TestSizeUtilities(unittest.TestCase):
    """Test cases for size conversion utilities."""

    def test_convert_size_to_bytes_valid_sizes(self):
        """Test conversion of valid size strings to bytes."""
        test_cases = [
            ('1.5gb', 1610612736.0),
            ('500mb', 524288000.0),
            ('10kb', 10240.0),
            ('1024b', 1024.0),
            ('2tb', 2199023255552.0),
            ('0b', 0.0),
            ('0.5gb', 536870912.0),
        ]

        for size_str, expected_bytes in test_cases:
            with self.subTest(size_str=size_str):
                result = convert_size_to_bytes(size_str)
                self.assertEqual(result, expected_bytes,
                               f"Failed to convert {size_str} to {expected_bytes} bytes")

    def test_convert_size_to_bytes_edge_cases(self):
        """Test conversion of edge cases and invalid inputs."""
        edge_cases = [
            ('-', 0),          # UNASSIGNED shard
            ('', 0),           # Empty string
            (None, 0),         # None value
            ('null', 0),       # 'null' string
            ('none', 0),       # 'none' string
            ('invalid', 0),    # Invalid format
            ('123xyz', 0),     # Invalid unit
        ]

        for size_str, expected_bytes in edge_cases:
            with self.subTest(size_str=size_str):
                result = convert_size_to_bytes(size_str)
                self.assertEqual(result, expected_bytes,
                               f"Failed to handle edge case {size_str}")

    def test_convert_size_to_bytes_case_insensitive(self):
        """Test that size conversion is case insensitive."""
        test_cases = [
            ('1GB', 1073741824.0),
            ('500MB', 524288000.0),
            ('10KB', 10240.0),
            ('1024B', 1024.0),
        ]

        for size_str, expected_bytes in test_cases:
            with self.subTest(size_str=size_str):
                result = convert_size_to_bytes(size_str)
                self.assertEqual(result, expected_bytes,
                               f"Failed case insensitive conversion for {size_str}")

    def test_get_shard_size_bytes_various_fields(self):
        """Test extracting size from shards with different field names."""
        test_cases = [
            ({'store': '1gb'}, 1073741824.0),
            ({'size': '500mb'}, 524288000.0),
            ({'store_size': '10kb'}, 10240.0),
            ({'disk.total': '2gb'}, 2147483648.0),
            ({}, 0),  # No size field
            ({'store': '-'}, 0),  # UNASSIGNED
            ({'store': None}, 0),  # None value
        ]

        for shard_dict, expected_bytes in test_cases:
            with self.subTest(shard=shard_dict):
                result = get_shard_size_bytes(shard_dict)
                self.assertEqual(result, expected_bytes,
                               f"Failed to extract size from {shard_dict}")

    def test_safe_sort_shards_by_size(self):
        """Test sorting shards by size handles missing/invalid size fields."""
        test_shards = [
            {'index': 'small', 'store': '10kb'},
            {'index': 'unassigned', 'store': '-'},
            {'index': 'large', 'store': '1gb'},
            {'index': 'medium', 'store': '100mb'},
            {'index': 'missing_size'},  # No size field
            {'index': 'null_size', 'store': None},
        ]

        # Test descending sort (default)
        sorted_desc = safe_sort_shards_by_size(test_shards, reverse=True)
        expected_order_desc = ['large', 'medium', 'small', 'unassigned', 'missing_size', 'null_size']
        actual_order_desc = [shard['index'] for shard in sorted_desc]
        self.assertEqual(actual_order_desc, expected_order_desc,
                        "Descending sort order incorrect")

        # Test ascending sort
        sorted_asc = safe_sort_shards_by_size(test_shards, reverse=False)
        expected_order_asc = ['unassigned', 'missing_size', 'null_size', 'small', 'medium', 'large']
        actual_order_asc = [shard['index'] for shard in sorted_asc]
        self.assertEqual(actual_order_asc, expected_order_asc,
                        "Ascending sort order incorrect")

    def test_safe_sort_shards_empty_list(self):
        """Test sorting empty list of shards."""
        result = safe_sort_shards_by_size([])
        self.assertEqual(result, [], "Empty list should remain empty")

    def test_format_bytes_human_readable(self):
        """Test formatting bytes into human readable format."""
        test_cases = [
            (0, '0b'),
            (512, '512b'),
            (1024, '1.0kb'),
            (1536, '1.5kb'),
            (1048576, '1.0mb'),
            (1073741824, '1.0gb'),
            (1099511627776, '1.0tb'),
        ]

        for bytes_value, expected_format in test_cases:
            with self.subTest(bytes_value=bytes_value):
                result = format_bytes_human_readable(bytes_value)
                self.assertEqual(result, expected_format,
                               f"Failed to format {bytes_value} bytes")

    def test_validate_size_string(self):
        """Test size string validation."""
        valid_strings = ['1gb', '500mb', '10kb', '1024b', '0b', '1.5gb', '0', '123']
        invalid_strings = ['', None, 'invalid', '123xyz', '-', 'null', 'none']

        for size_str in valid_strings:
            with self.subTest(size_str=size_str):
                self.assertTrue(validate_size_string(size_str),
                              f"{size_str} should be valid")

        for size_str in invalid_strings:
            with self.subTest(size_str=size_str):
                self.assertFalse(validate_size_string(size_str),
                               f"{size_str} should be invalid")

    def test_regression_keyerror_fix(self):
        """
        Regression test for the original KeyError bug.

        This test simulates the exact scenario that was failing:
        - shards -z -s node-1 command
        - UNASSIGNED shards with store: '-'
        - Missing size fields
        """
        # Data that would cause KeyError with old implementation
        problematic_shards = [
            {
                'index': 'logs-2024-01',
                'store': '2.1gb',
                'shard': '0',
                'prirep': 'p',
                'state': 'STARTED',
                'node': 'node-1'
            },
            {
                'index': 'logs-2024-02',
                'store': '-',  # This was causing KeyError
                'shard': '0',
                'prirep': 'p',
                'state': 'UNASSIGNED'
            },
            {
                'index': 'alerts-2024-01',
                # Missing store field entirely
                'shard': '0',
                'prirep': 'p',
                'state': 'STARTED',
                'node': 'node-3'
            },
        ]

        # This should not raise any exceptions
        try:
            sorted_shards = safe_sort_shards_by_size(problematic_shards, reverse=True)
            self.assertEqual(len(sorted_shards), 3, "All shards should be present after sorting")

            # Verify the largest shard is first
            largest_shard = sorted_shards[0]
            self.assertEqual(largest_shard['index'], 'logs-2024-01',
                           "Largest shard should be sorted first")

            # Verify shards with no size are handled
            zero_size_shards = [s for s in sorted_shards if get_shard_size_bytes(s) == 0]
            self.assertEqual(len(zero_size_shards), 2,
                           "Should have 2 shards with zero/missing size")

        except KeyError as e:
            self.fail(f"KeyError raised during sorting: {e}. The fix is not working.")
        except Exception as e:
            self.fail(f"Unexpected exception during sorting: {e}")


if __name__ == '__main__':
    unittest.main()
