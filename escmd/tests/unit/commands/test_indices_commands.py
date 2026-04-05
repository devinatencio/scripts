#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from commands.indices_commands import IndicesCommands


class TestIndicesCommands(unittest.TestCase):
    """Test cases for IndicesCommands class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_es_client = Mock()
        self.mock_index_processor = Mock()
        self.mock_es_client.index_processor = self.mock_index_processor
        self.indices_commands = IndicesCommands(self.mock_es_client)

    def test_list_indices_stats_sorts_alphabetically_no_pattern(self):
        """Test that list_indices_stats sorts indices alphabetically when no pattern is provided."""
        # Mock data in random order
        unsorted_indices = [
            {'index': 'zebra-index', 'health': 'green', 'status': 'open', 'docs.count': 100},
            {'index': 'apple-index', 'health': 'yellow', 'status': 'open', 'docs.count': 200},
            {'index': 'beta-index', 'health': 'green', 'status': 'open', 'docs.count': 50},
            {'index': 'Alpha-index', 'health': 'red', 'status': 'close', 'docs.count': 75}
        ]

        # Mock the Elasticsearch client response
        mock_response = Mock()
        mock_response.body = unsorted_indices
        self.mock_es_client.es.cat.indices.return_value = mock_response

        # Call the method
        result = self.indices_commands.list_indices_stats()

        # Verify the result is sorted alphabetically (case-insensitive)
        expected_order = ['Alpha-index', 'apple-index', 'beta-index', 'zebra-index']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_order,
                        "Indices should be sorted alphabetically (case-insensitive)")

    def test_list_indices_stats_sorts_alphabetically_with_pattern(self):
        """Test that list_indices_stats sorts filtered indices alphabetically when pattern is provided."""
        # Mock data in random order
        unsorted_indices = [
            {'index': 'zebra-index', 'health': 'green', 'status': 'open', 'docs.count': 100},
            {'index': 'apple-index', 'health': 'yellow', 'status': 'open', 'docs.count': 200},
            {'index': 'beta-index', 'health': 'green', 'status': 'open', 'docs.count': 50},
            {'index': 'Alpha-index', 'health': 'red', 'status': 'close', 'docs.count': 75}
        ]

        # Mock filtered data (subset of above)
        filtered_indices = [
            {'index': 'zebra-index', 'health': 'green', 'status': 'open', 'docs.count': 100},
            {'index': 'beta-index', 'health': 'green', 'status': 'open', 'docs.count': 50},
            {'index': 'Alpha-index', 'health': 'red', 'status': 'close', 'docs.count': 75}
        ]

        # Mock the Elasticsearch client response
        mock_response = Mock()
        mock_response.body = unsorted_indices
        self.mock_es_client.es.cat.indices.return_value = mock_response

        # Mock the filter_indices method to return filtered data (unsorted)
        self.mock_index_processor.filter_indices.return_value = filtered_indices.copy()

        # Call the method with a pattern
        result = self.indices_commands.list_indices_stats(pattern="*-index")

        # Verify the filter_indices was called
        self.mock_index_processor.filter_indices.assert_called_once()

        # The result should be sorted alphabetically
        expected_order = ['Alpha-index', 'beta-index', 'zebra-index']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_order,
                        "Filtered indices should be sorted alphabetically (case-insensitive)")

    def test_list_indices_stats_sorts_alphabetically_with_status(self):
        """Test that list_indices_stats sorts filtered indices alphabetically when status is provided."""
        # Mock data in random order
        unsorted_indices = [
            {'index': 'zebra-index', 'health': 'green', 'status': 'open', 'docs.count': 100},
            {'index': 'apple-index', 'health': 'yellow', 'status': 'open', 'docs.count': 200},
            {'index': 'beta-index', 'health': 'green', 'status': 'open', 'docs.count': 50},
            {'index': 'Alpha-index', 'health': 'red', 'status': 'close', 'docs.count': 75}
        ]

        # Mock filtered data (green indices only)
        filtered_indices = [
            {'index': 'zebra-index', 'health': 'green', 'status': 'open', 'docs.count': 100},
            {'index': 'beta-index', 'health': 'green', 'status': 'open', 'docs.count': 50}
        ]

        # Mock the Elasticsearch client response
        mock_response = Mock()
        mock_response.body = unsorted_indices
        self.mock_es_client.es.cat.indices.return_value = mock_response

        # Mock the filter_indices method to return filtered data (unsorted)
        self.mock_index_processor.filter_indices.return_value = filtered_indices.copy()

        # Call the method with a status filter
        result = self.indices_commands.list_indices_stats(status="green")

        # Verify the filter_indices was called
        self.mock_index_processor.filter_indices.assert_called_once()

        # The result should be sorted alphabetically
        expected_order = ['beta-index', 'zebra-index']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_order,
                        "Status-filtered indices should be sorted alphabetically (case-insensitive)")

    def test_list_indices_stats_case_insensitive_sorting(self):
        """Test that sorting is case-insensitive."""
        # Mock data with mixed case
        unsorted_indices = [
            {'index': 'zulu-Index', 'health': 'green', 'status': 'open', 'docs.count': 100},
            {'index': 'Alpha-index', 'health': 'green', 'status': 'open', 'docs.count': 200},
            {'index': 'BRAVO-INDEX', 'health': 'green', 'status': 'open', 'docs.count': 50},
            {'index': 'charlie-index', 'health': 'green', 'status': 'open', 'docs.count': 75}
        ]

        # Mock the Elasticsearch client response
        mock_response = Mock()
        mock_response.body = unsorted_indices
        self.mock_es_client.es.cat.indices.return_value = mock_response

        # Call the method
        result = self.indices_commands.list_indices_stats()

        # Verify case-insensitive alphabetical sorting
        expected_order = ['Alpha-index', 'BRAVO-INDEX', 'charlie-index', 'zulu-Index']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_order,
                        "Indices should be sorted alphabetically in a case-insensitive manner")

    def test_get_indices_stats_delegates_to_list_indices_stats(self):
        """Test that get_indices_stats delegates to list_indices_stats and returns sorted results."""
        # Mock data
        unsorted_indices = [
            {'index': 'zebra-index', 'health': 'green', 'status': 'open', 'docs.count': 100},
            {'index': 'apple-index', 'health': 'yellow', 'status': 'open', 'docs.count': 200}
        ]

        # Mock the Elasticsearch client response
        mock_response = Mock()
        mock_response.body = unsorted_indices
        self.mock_es_client.es.cat.indices.return_value = mock_response

        # Call get_indices_stats
        result = self.indices_commands.get_indices_stats()

        # Verify the result is sorted alphabetically
        expected_order = ['apple-index', 'zebra-index']
        actual_order = [index['index'] for index in result]

        self.assertEqual(actual_order, expected_order,
                        "get_indices_stats should return sorted indices via list_indices_stats")


if __name__ == '__main__':
    unittest.main()
