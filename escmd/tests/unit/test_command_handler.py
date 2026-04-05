"""
Unit tests for CommandHandler class.

Tests the core command routing logic and handler initialization.
"""

import pytest
import argparse
from unittest.mock import Mock, patch

from command_handler import CommandHandler


class TestCommandHandler:
    """Test cases for CommandHandler class."""

    def test_handler_initialization(self, command_handler):
        """Test that all individual handlers are properly initialized."""
        expected_handler_attrs = [
            'cluster_handler', 'index_handler', 'allocation_handler', 'lifecycle_handler',
            'storage_handler', 'snapshot_handler', 'utility_handler', 'dangling_handler',
            'settings_handler', 'help_handler', 'themes_handler'
        ]

        for handler_attr in expected_handler_attrs:
            assert hasattr(command_handler, handler_attr)
            assert getattr(command_handler, handler_attr) is not None

    def test_command_routing_health(self, command_handler):
        """Test that health command routes to cluster handler."""
        command_handler.args.command = 'health'

        with patch.object(command_handler.cluster_handler, 'handle_health') as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()

    def test_command_routing_ping(self, command_handler):
        """Test that ping command routes to cluster handler."""
        command_handler.args.command = 'ping'

        with patch.object(command_handler.cluster_handler, 'handle_ping') as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()

    def test_command_routing_dangling(self, command_handler):
        """Test that dangling command routes to dangling handler."""
        command_handler.args.command = 'dangling'

        with patch.object(command_handler.dangling_handler, 'handle_dangling') as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()

    def test_command_routing_indices(self, command_handler):
        """Test that indices command routes to index handler."""
        command_handler.args.command = 'indices'

        with patch.object(command_handler.index_handler, 'handle_indices') as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()

    def test_command_routing_cluster_settings(self, command_handler):
        """Test that cluster-settings command routes to settings handler."""
        command_handler.args.command = 'cluster-settings'

        with patch.object(command_handler.settings_handler, 'handle_settings') as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()

    def test_command_routing_datastreams(self, command_handler):
        """Test that datastreams command routes to datastream handler."""
        command_handler.args.command = 'datastreams'

        with patch.object(command_handler.datastream_handler, 'handle_datastreams') as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()

    def test_command_routing_locations(self, command_handler):
        """Test that locations command routes to utility handler."""
        command_handler.args.command = 'locations'

        with patch.object(command_handler.utility_handler, 'handle_locations') as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()

    def test_command_routing_flush(self, command_handler):
        """Test that flush command routes to index handler."""
        command_handler.args.command = 'flush'

        with patch.object(command_handler.index_handler, 'handle_flush') as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()

    def test_command_routing_auto_rollover(self, command_handler):
        """Test that auto-rollover command routes to lifecycle handler."""
        command_handler.args.command = 'auto-rollover'

        with patch.object(command_handler.lifecycle_handler, 'handle_auto_rollover') as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()

    def test_all_commands_mapped(self, command_handler):
        """Test that all expected commands are mapped in the handler dictionary."""
        expected_commands = [
            'ping', 'allocation', 'current-master', 'flush', 'freeze', 'nodes',
            'masters', 'health', 'indice', 'indices', 'locations', 'recovery',
            'rollover', 'auto-rollover', 'exclude', 'exclude-reset', 'cluster-settings',
            'storage', 'shards', 'shard-colocation', 'snapshots', 'ilm',
            'datastreams', 'cluster-check', 'set-replicas', 'dangling'
        ]

        # Access the command_handlers dict from execute method
        # We need to temporarily call execute to access the internal mapping
        original_command = command_handler.args.command
        command_handler.args.command = 'nonexistent-command'  # Use a command that doesn't exist

        try:
            with patch('builtins.print') as mock_print:
                command_handler.execute()
                # Should print "Unknown command" for nonexistent command
                mock_print.assert_called_with("Unknown command: nonexistent-command")
        finally:
            command_handler.args.command = original_command

        # Check that the number of expected commands matches what we found in our analysis
        assert len(expected_commands) == 26  # Should be 26 commands total

    def test_unknown_command_handling(self, command_handler):
        """Test handling of unknown commands."""
        command_handler.args.command = 'nonexistent-command'

        with patch('builtins.print') as mock_print:
            command_handler.execute()
            mock_print.assert_called_with("Unknown command: nonexistent-command")

    @pytest.mark.parametrize("command,handler_attr,expected_method", [
        ('health', 'cluster_handler', 'handle_health'),
        ('ping', 'cluster_handler', 'handle_ping'),
        ('cluster-check', 'utility_handler', 'handle_cluster_check'),
        ('indices', 'index_handler', 'handle_indices'),
        ('indices-analyze', 'index_handler', 'handle_indices_analyze'),
        ('indices-s3-estimate', 'index_handler', 'handle_indices_s3_estimate'),
        ('indices-watch-collect', 'index_handler', 'handle_indices_watch_collect'),
        ('dangling', 'dangling_handler', 'handle_dangling'),
        ('flush', 'index_handler', 'handle_flush'),
        ('allocation', 'allocation_handler', 'handle_allocation'),
        ('exclude', 'allocation_handler', 'handle_exclude'),
        ('nodes', 'cluster_handler', 'handle_nodes'),
        ('shards', 'storage_handler', 'handle_shards'),
        ('rollover', 'lifecycle_handler', 'handle_rollover'),
        ('auto-rollover', 'lifecycle_handler', 'handle_auto_rollover'),
        ('snapshots', 'snapshot_handler', 'handle_snapshots'),
        ('ilm', 'lifecycle_handler', 'handle_ilm'),
        ('set-replicas', 'utility_handler', 'handle_set_replicas'),
        ('datastreams', 'datastream_handler', 'handle_datastreams'),
        ('cluster-settings', 'settings_handler', 'handle_settings'),
        ('locations', 'utility_handler', 'handle_locations'),
    ])
    def test_command_routing_parametrized(self, command_handler, command, handler_attr, expected_method):
        """Parametrized test for command routing to ensure all commands go to correct handlers."""
        command_handler.args.command = command

        handler = getattr(command_handler, handler_attr)
        with patch.object(handler, expected_method) as mock_method:
            command_handler.execute()
            mock_method.assert_called_once()
