#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from processors.index_processor import IndexProcessor


class TestIndexProcessor(unittest.TestCase):
    """Test cases for IndexProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = IndexProcessor()

    def test_filter_indices_sorts_alphabetically_no_filters(self):
        """Test that filter_indices sorts indices alphabetically when no filters are applied."""
        # Mock data in random order
        unsorted_indices = [
            {'index': 'zebra-index', 'health': 'green'},
            {'index': 'apple-index', 'health': 'yellow'},
            {'index': 'beta-index', 'health': 'green'},
            {'index': 'Alpha-index', 'health': 'red'}
        ]

        # Call filter_indices with no filters
        result = self.processor.filter_indices(unsorted_indices)

        # Verify the result is sorted alphabetically (case-insensitive)
        expected_order = ['Alpha-index', 'apple-index', 'beta-index', 'zebra-index']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_order,
                        "Indices should be sorted alphabetically (case-insensitive)")

    @patch.object(IndexProcessor, '_compile_pattern_regex')
    def test_filter_indices_sorts_alphabetically_with_pattern(self, mock_compile_regex):
        """Test that filter_indices sorts filtered indices alphabetically when pattern is provided."""
        # Mock data in random order
        unsorted_indices = [
            {'index': 'zebra-logs', 'health': 'green'},
            {'index': 'apple-logs', 'health': 'yellow'},
            {'index': 'beta-index', 'health': 'green'},
            {'index': 'Alpha-logs', 'health': 'red'}
        ]

        # Mock regex to match only "*-logs" patterns
        mock_regex = Mock()
        mock_regex.search.side_effect = lambda name: '-logs' in name
        mock_compile_regex.return_value = mock_regex

        # Call filter_indices with pattern
        result = self.processor.filter_indices(unsorted_indices, pattern="*-logs")

        # Verify the filter was applied and result is sorted
        expected_indices = ['Alpha-logs', 'apple-logs', 'zebra-logs']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_indices,
                        "Pattern-filtered indices should be sorted alphabetically")

    def test_filter_indices_sorts_alphabetically_with_status(self):
        """Test that filter_indices sorts filtered indices alphabetically when status is provided."""
        # Mock data in random order
        unsorted_indices = [
            {'index': 'zebra-index', 'health': 'green'},
            {'index': 'apple-index', 'health': 'yellow'},
            {'index': 'beta-index', 'health': 'green'},
            {'index': 'Alpha-index', 'health': 'red'},
            {'index': 'charlie-index', 'health': 'green'}
        ]

        # Call filter_indices with status filter
        result = self.processor.filter_indices(unsorted_indices, status="green")

        # Verify only green indices are returned and sorted alphabetically
        expected_order = ['beta-index', 'charlie-index', 'zebra-index']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_order,
                        "Status-filtered indices should be sorted alphabetically")

    @patch.object(IndexProcessor, '_compile_pattern_regex')
    def test_filter_indices_sorts_alphabetically_with_both_filters(self, mock_compile_regex):
        """Test that filter_indices sorts indices alphabetically when both pattern and status are provided."""
        # Mock data in random order
        unsorted_indices = [
            {'index': 'zebra-logs', 'health': 'green'},
            {'index': 'apple-logs', 'health': 'yellow'},
            {'index': 'beta-logs', 'health': 'green'},
            {'index': 'Alpha-logs', 'health': 'red'},
            {'index': 'charlie-logs', 'health': 'green'}
        ]

        # Mock regex to match only "*-logs" patterns
        mock_regex = Mock()
        mock_regex.search.side_effect = lambda name: '-logs' in name
        mock_compile_regex.return_value = mock_regex

        # Call filter_indices with both pattern and status filters
        result = self.processor.filter_indices(unsorted_indices, pattern="*-logs", status="green")

        # Verify both filters were applied and result is sorted
        expected_order = ['beta-logs', 'charlie-logs', 'zebra-logs']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_order,
                        "Indices filtered by both pattern and status should be sorted alphabetically")

    def test_filter_indices_case_insensitive_sorting(self):
        """Test that sorting is case-insensitive."""
        # Mock data with mixed case
        unsorted_indices = [
            {'index': 'zulu-Index', 'health': 'green'},
            {'index': 'Alpha-index', 'health': 'green'},
            {'index': 'BRAVO-INDEX', 'health': 'green'},
            {'index': 'charlie-index', 'health': 'green'}
        ]

        # Call filter_indices
        result = self.processor.filter_indices(unsorted_indices)

        # Verify case-insensitive alphabetical sorting
        expected_order = ['Alpha-index', 'BRAVO-INDEX', 'charlie-index', 'zulu-Index']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_order,
                        "Indices should be sorted alphabetically in a case-insensitive manner")

    def test_filter_indices_preserves_all_fields(self):
        """Test that sorting preserves all fields in the index objects."""
        # Mock data with multiple fields
        unsorted_indices = [
            {'index': 'zebra-index', 'health': 'green', 'status': 'open', 'docs.count': 100, 'store.size': 1024},
            {'index': 'apple-index', 'health': 'yellow', 'status': 'open', 'docs.count': 200, 'store.size': 2048}
        ]

        # Call filter_indices
        result = self.processor.filter_indices(unsorted_indices)

        # Verify all fields are preserved and indices are sorted
        self.assertEqual(len(result), 2, "Should return all indices")

        # First index should be apple-index (alphabetically first)
        first_index = result[0]
        self.assertEqual(first_index['index'], 'apple-index')
        self.assertEqual(first_index['health'], 'yellow')
        self.assertEqual(first_index['status'], 'open')
        self.assertEqual(first_index['docs.count'], 200)
        self.assertEqual(first_index['store.size'], 2048)

        # Second index should be zebra-index (alphabetically second)
        second_index = result[1]
        self.assertEqual(second_index['index'], 'zebra-index')
        self.assertEqual(second_index['health'], 'green')
        self.assertEqual(second_index['status'], 'open')
        self.assertEqual(second_index['docs.count'], 100)
        self.assertEqual(second_index['store.size'], 1024)

    def test_filter_indices_handles_missing_index_field(self):
        """Test that filter_indices handles indices with missing or empty index field gracefully."""
        # Mock data with missing/empty index fields
        unsorted_indices = [
            {'index': 'zebra-index', 'health': 'green'},
            {'health': 'yellow'},  # Missing index field
            {'index': '', 'health': 'green'},  # Empty index field
            {'index': 'apple-index', 'health': 'red'}
        ]

        # Call filter_indices
        result = self.processor.filter_indices(unsorted_indices)

        # Verify sorting handles missing/empty fields (they should sort to beginning)
        expected_order = ['', 'apple-index', 'zebra-index', '']  # Empty strings and missing treated as empty
        actual_indices = [index.get('index', '') for index in result]

        # Count expected positions
        empty_count = sum(1 for idx in actual_indices if idx == '')
        named_indices = [idx for idx in actual_indices if idx != '']

        self.assertEqual(empty_count, 2, "Should have 2 entries with empty/missing index names")
        self.assertEqual(named_indices, ['apple-index', 'zebra-index'],
                        "Named indices should be sorted alphabetically")

    def test_filter_indices_empty_list(self):
        """Test that filter_indices handles empty input list correctly."""
        # Call filter_indices with empty list
        result = self.processor.filter_indices([])

        # Verify empty list is returned
        self.assertEqual(result, [], "Should return empty list for empty input")

    def test_filter_indices_single_item(self):
        """Test that filter_indices handles single item list correctly."""
        # Mock data with single item
        single_index = [{'index': 'single-index', 'health': 'green'}]

        # Call filter_indices
        result = self.processor.filter_indices(single_index)

        # Verify single item is returned unchanged
        self.assertEqual(len(result), 1, "Should return single item")
        self.assertEqual(result[0]['index'], 'single-index')


if __name__ == '__main__':
    unittest.main()
