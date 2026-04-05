#!/usr/bin/env python3
"""
Test script to validate the improved JSON deletion output format.

This script tests the new JSON format functionality for index deletion
to ensure it provides proper structured output for automation.
"""

import json
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add the project root to the path to import escmd modules
sys.path.insert(0, '../../')

from handlers.index_handler import IndexHandler


class TestJSONDeletionOutput(unittest.TestCase):
    """Test cases for the improved JSON deletion output."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock ES client
        self.mock_es_client = Mock()

        # Mock console
        self.mock_console = Mock()

        # Mock args with JSON format and deletion
        self.mock_args = Mock()
        self.mock_args.format = "json"
        self.mock_args.delete = True
        self.mock_args.yes = True  # Auto-confirm for testing
        self.mock_args.status = None
        self.mock_args.cold = False
        self.mock_args.regex = False

        # Create handler instance
        self.handler = IndexHandler(
            es_client=self.mock_es_client,
            args=self.mock_args,
            console=self.mock_console,
            config_file=None,
            location_config=None,
            current_location=None,
        )

    def test_successful_deletion_json_output(self):
        """Test JSON output for successful deletion."""
        # Mock index data
        mock_indices = [
            {
                "index": "test-index-1",
                "health": "green",
                "status": "open",
                "pri": "1",
                "rep": "0",
            },
            {
                "index": "test-index-2",
                "health": "green",
                "status": "open",
                "pri": "1",
                "rep": "0",
            },
        ]

        # Mock successful deletion result
        mock_deletion_result = {
            "successful_deletions": ["test-index-1", "test-index-2"],
            "failed_deletions": [],
            "total_requested": 2,
        }

        self.mock_es_client.filter_indices.return_value = mock_indices
        self.mock_es_client.delete_indices.return_value = mock_deletion_result

        # Capture print output
        with patch("builtins.print") as mock_print:
            self.handler.handle_indices()

            # Verify print was called once with JSON output
            self.assertEqual(mock_print.call_count, 1)

            # Parse the printed JSON
            printed_json = mock_print.call_args[0][0]
            output_data = json.loads(printed_json)

            # Verify structure
            self.assertIn("indices", output_data)
            self.assertIn("deletion_requested", output_data)
            self.assertIn("deletion_results", output_data)

            # Verify content
            self.assertEqual(output_data["deletion_requested"], True)
            self.assertEqual(output_data["indices"], mock_indices)

            deletion_results = output_data["deletion_results"]
            self.assertEqual(deletion_results["status"], "completed")
            self.assertEqual(len(deletion_results["successful_deletions"]), 2)
            self.assertEqual(len(deletion_results["failed_deletions"]), 0)

    def test_mixed_results_json_output(self):
        """Test JSON output for mixed deletion results."""
        mock_indices = [
            {"index": "deletable-index", "health": "green"},
            {"index": "protected-index", "health": "green"},
        ]

        mock_deletion_result = {
            "successful_deletions": ["deletable-index"],
            "failed_deletions": [
                {"index": "protected-index", "error": "index read-only"}
            ],
            "total_requested": 2,
        }

        self.mock_es_client.filter_indices.return_value = mock_indices
        self.mock_es_client.delete_indices.return_value = mock_deletion_result

        with patch("builtins.print") as mock_print:
            self.handler.handle_indices()

            printed_json = mock_print.call_args[0][0]
            output_data = json.loads(printed_json)

            deletion_results = output_data["deletion_results"]
            self.assertEqual(deletion_results["status"], "completed")
            self.assertEqual(len(deletion_results["successful_deletions"]), 1)
            self.assertEqual(len(deletion_results["failed_deletions"]), 1)
            self.assertEqual(
                deletion_results["failed_deletions"][0]["index"], "protected-index"
            )

    def test_user_cancellation_json_output(self):
        """Test JSON output when user cancels deletion."""
        # Disable auto-confirm
        self.mock_args.yes = False

        mock_indices = [{"index": "important-index", "health": "green"}]
        self.mock_es_client.filter_indices.return_value = mock_indices

        # Mock user cancellation
        with patch("rich.prompt.Confirm.ask", return_value=False):
            with patch("builtins.print") as mock_print:
                self.handler.handle_indices()

                printed_json = mock_print.call_args[0][0]
                output_data = json.loads(printed_json)

                deletion_results = output_data["deletion_results"]
                self.assertEqual(deletion_results["status"], "cancelled")
                self.assertIn(
                    "Operation cancelled by user", deletion_results["message"]
                )

    def test_deletion_error_json_output(self):
        """Test JSON output when deletion encounters an error."""
        mock_indices = [{"index": "problem-index", "health": "red"}]
        self.mock_es_client.filter_indices.return_value = mock_indices

        # Mock deletion error
        self.mock_es_client.delete_indices.side_effect = Exception("Connection timeout")

        with patch("builtins.print") as mock_print:
            self.handler.handle_indices()

            printed_json = mock_print.call_args[0][0]
            output_data = json.loads(printed_json)

            deletion_results = output_data["deletion_results"]
            self.assertEqual(deletion_results["status"], "error")
            self.assertIn("Connection timeout", deletion_results["message"])
            self.assertEqual(len(deletion_results["successful_deletions"]), 0)

    def test_no_deletion_json_output(self):
        """Test JSON output when deletion is not requested."""
        # Disable deletion
        self.mock_args.delete = False

        mock_indices = [{"index": "some-index", "health": "green"}]
        self.mock_es_client.filter_indices.return_value = mock_indices

        with patch("builtins.print") as mock_print:
            self.handler.handle_indices()

            printed_json = mock_print.call_args[0][0]
            output_data = json.loads(printed_json)

            # Should only contain indices, no deletion info
            self.assertEqual(output_data, mock_indices)

    def test_json_format_validation(self):
        """Test that output is valid JSON format."""
        mock_indices = [{"index": "test", "health": "green"}]
        mock_deletion_result = {
            "successful_deletions": ["test"],
            "failed_deletions": [],
            "total_requested": 1,
        }

        self.mock_es_client.filter_indices.return_value = mock_indices
        self.mock_es_client.delete_indices.return_value = mock_deletion_result

        with patch("builtins.print") as mock_print:
            self.handler.handle_indices()

            printed_output = mock_print.call_args[0][0]

            # Should not raise any exception
            try:
                json.loads(printed_output)
            except json.JSONDecodeError:
                self.fail("Output is not valid JSON")


if __name__ == "__main__":
    unittest.main()
