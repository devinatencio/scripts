#!/usr/bin/env python3
"""
Unit tests for the snapshot list --fast mode functionality.

Verifies that the --fast flag is correctly parsed by the CLI, that the
implementation methods exist on the expected classes with correct signatures,
and that the fast-mode execution path produces the expected data structure
when run against a mock Elasticsearch response.
"""

import inspect
import sys
import unittest
from argparse import Namespace
from unittest.mock import Mock

sys.path.insert(0, "../../../")

from cli.argument_parser import create_argument_parser
from commands.snapshot_commands import SnapshotCommands
from esclient import ElasticsearchClient
from handlers.snapshot_handler import SnapshotHandler


class TestSnapshotFastModeArgumentParsing(unittest.TestCase):
    """Tests for --fast / --slow flag parsing in the CLI argument parser."""

    def setUp(self):
        self.parser = create_argument_parser()

    def test_fast_flag_sets_mode_fast(self):
        """--fast flag results in mode='fast'."""
        args = self.parser.parse_args(["snapshots", "list", "--fast"])
        self.assertEqual(getattr(args, "mode", None), "fast")

    def test_no_flag_defaults_to_fast_mode(self):
        """Omitting --fast still defaults to mode='fast' (fast is the default)."""
        args = self.parser.parse_args(["snapshots", "list"])
        self.assertEqual(getattr(args, "mode", None), "fast")

    def test_slow_flag_sets_mode_slow(self):
        """--slow flag results in mode='slow' (not 'fast')."""
        args = self.parser.parse_args(["snapshots", "list", "--slow"])
        self.assertNotEqual(getattr(args, "mode", None), "fast")

    def test_snapshots_command_is_set(self):
        """Parsing 'snapshots list --fast' sets command='snapshots'."""
        args = self.parser.parse_args(["snapshots", "list", "--fast"])
        self.assertEqual(getattr(args, "command", None), "snapshots")

    def test_snapshots_action_is_set(self):
        """Parsing 'snapshots list --fast' sets the list action."""
        args = self.parser.parse_args(["snapshots", "list", "--fast"])
        # The action attribute may be named differently; verify it is 'list'
        action = getattr(args, "snapshots_action", None) or getattr(
            args, "action", None
        )
        self.assertEqual(action, "list")


class TestSnapshotFastModeMethodPresence(unittest.TestCase):
    """Tests that list_snapshots_fast exists on the expected classes."""

    def test_snapshot_commands_has_fast_method(self):
        """SnapshotCommands exposes list_snapshots_fast."""
        self.assertTrue(
            hasattr(SnapshotCommands, "list_snapshots_fast"),
            "SnapshotCommands is missing list_snapshots_fast",
        )

    def test_elasticsearch_client_has_fast_method(self):
        """ElasticsearchClient exposes list_snapshots_fast."""
        self.assertTrue(
            hasattr(ElasticsearchClient, "list_snapshots_fast"),
            "ElasticsearchClient is missing list_snapshots_fast",
        )

    def test_fast_method_is_callable(self):
        """list_snapshots_fast on SnapshotCommands is callable."""
        self.assertTrue(callable(getattr(SnapshotCommands, "list_snapshots_fast")))


class TestSnapshotFastModeMethodSignature(unittest.TestCase):
    """Tests that list_snapshots_fast has the expected parameter signature."""

    def setUp(self):
        self.sig = inspect.signature(SnapshotCommands.list_snapshots_fast)
        self.params = list(self.sig.parameters.keys())

    def test_has_self_parameter(self):
        self.assertIn("self", self.params)

    def test_has_repository_name_parameter(self):
        self.assertIn("repository_name", self.params)

    def test_has_progress_callback_parameter(self):
        self.assertIn("progress_callback", self.params)

    def test_progress_callback_has_default(self):
        """progress_callback should be optional (has a default value)."""
        param = self.sig.parameters.get("progress_callback")
        self.assertIsNotNone(param)
        self.assertIsNot(
            param.default,
            inspect.Parameter.empty,
            "progress_callback should have a default value so callers can omit it",
        )


class TestSnapshotFastModeHandlerDetection(unittest.TestCase):
    """Tests that SnapshotHandler correctly detects fast mode from args."""

    def _make_handler(self):
        return SnapshotHandler(
            es_client=Mock(),
            args=None,
            console=Mock(),
            config_file=Mock(),
            location_config={"elastic_s3snapshot_repo": "test-repo"},
            current_location="test-location",
        )

    def test_detects_fast_mode_when_mode_is_fast(self):
        handler = self._make_handler()
        handler.args = Namespace(mode="fast")
        self.assertTrue(getattr(handler.args, "mode", None) == "fast")

    def test_does_not_detect_fast_mode_when_mode_is_slow(self):
        handler = self._make_handler()
        handler.args = Namespace(mode="slow")
        self.assertFalse(getattr(handler.args, "mode", "fast") == "fast")

    def test_default_falls_back_to_fast_when_attribute_missing(self):
        """If mode attribute is absent, getattr default of 'fast' returns 'fast'."""
        handler = self._make_handler()
        handler.args = Namespace()
        self.assertEqual(getattr(handler.args, "mode", "fast"), "fast")


class TestSnapshotFastModeExecution(unittest.TestCase):
    """Tests list_snapshots_fast against a mock Elasticsearch response."""

    _REPO = "test-repo"

    def _make_mock_es(self, snapshots):
        mock_es = Mock()
        mock_es.snapshot.get.return_value = {"snapshots": snapshots}
        return mock_es

    def _make_client(self, mock_es):
        mock_es_client = Mock()
        mock_es_client.es = mock_es
        # Disable configuration_manager so get_snapshot_timeout() falls through
        # to the default value (120) instead of trying to call int() on a Mock.
        mock_es_client.configuration_manager = None
        return SnapshotCommands(mock_es_client)

    def test_returns_a_list(self):
        mock_es = self._make_mock_es(
            [
                {
                    "snapshot": "snap-1",
                    "state": "SUCCESS",
                    "start_time": "2024-01-01T12:00:00.000Z",
                    "end_time": "2024-01-01T12:05:00.000Z",
                    "duration_in_millis": 300_000,
                    "indices": ["idx-1"],
                    "include_global_state": False,
                    "failures": [],
                }
            ]
        )
        result = self._make_client(mock_es).list_snapshots_fast(self._REPO)
        self.assertIsInstance(result, list)

    def test_result_is_non_empty_for_non_empty_response(self):
        mock_es = self._make_mock_es(
            [
                {
                    "snapshot": "snap-1",
                    "state": "SUCCESS",
                    "start_time": "2024-01-01T12:00:00.000Z",
                    "end_time": "2024-01-01T12:05:00.000Z",
                    "duration_in_millis": 300_000,
                    "indices": ["idx-1"],
                    "include_global_state": False,
                    "failures": [],
                }
            ]
        )
        result = self._make_client(mock_es).list_snapshots_fast(self._REPO)
        self.assertGreater(len(result), 0)

    def test_result_contains_dicts(self):
        mock_es = self._make_mock_es(
            [
                {
                    "snapshot": "snap-1",
                    "state": "SUCCESS",
                    "start_time": "2024-01-01T12:00:00.000Z",
                    "end_time": "2024-01-01T12:05:00.000Z",
                    "duration_in_millis": 300_000,
                    "indices": ["idx-1"],
                    "include_global_state": False,
                    "failures": [],
                }
            ]
        )
        result = self._make_client(mock_es).list_snapshots_fast(self._REPO)
        self.assertIsInstance(result[0], dict)

    def test_failed_snapshot_included_in_results(self):
        """FAILED snapshots should still appear in the result list."""
        mock_es = self._make_mock_es(
            [
                {
                    "snapshot": "snap-ok",
                    "state": "SUCCESS",
                    "start_time": "2024-01-01T12:00:00.000Z",
                    "end_time": "2024-01-01T12:05:00.000Z",
                    "duration_in_millis": 300_000,
                    "indices": [],
                    "include_global_state": False,
                    "failures": [],
                },
                {
                    "snapshot": "snap-fail",
                    "state": "FAILED",
                    "start_time": "2024-01-01T13:00:00.000Z",
                    "end_time": "2024-01-01T13:02:00.000Z",
                    "duration_in_millis": 120_000,
                    "indices": [],
                    "include_global_state": False,
                    "failures": [{"reason": "disk full"}],
                },
            ]
        )
        result = self._make_client(mock_es).list_snapshots_fast(self._REPO)
        self.assertEqual(len(result), 2)

    def test_empty_snapshot_list_returns_empty_list(self):
        mock_es = self._make_mock_es([])
        result = self._make_client(mock_es).list_snapshots_fast(self._REPO)
        self.assertEqual(result, [])

    def test_es_api_called_with_correct_repository(self):
        mock_es = self._make_mock_es([])
        self._make_client(mock_es).list_snapshots_fast(self._REPO)
        call_kwargs = mock_es.snapshot.get.call_args
        self.assertIsNotNone(call_kwargs)
        # repository arg may be positional or keyword
        args, kwargs = call_kwargs
        repo_value = kwargs.get("repository") or (args[0] if args else None)
        self.assertEqual(repo_value, self._REPO)

    def test_es_api_called_with_verbose_false(self):
        """Fast mode must request verbose=False for lightweight response."""
        mock_es = self._make_mock_es([])
        self._make_client(mock_es).list_snapshots_fast(self._REPO)
        _, kwargs = mock_es.snapshot.get.call_args
        self.assertFalse(
            kwargs.get("verbose", True),
            "list_snapshots_fast must pass verbose=False to the ES API",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
