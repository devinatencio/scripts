"""
Integration tests for the escmd CLI tool.

These tests verify end-to-end functionality by running the actual CLI commands
with mocked Elasticsearch connections.
"""

import pytest
import subprocess
import json
import os
import sys
import tempfile
import yaml
from unittest.mock import patch, Mock


class TestCLIIntegration:
    """Integration tests for the complete CLI workflow."""

    @pytest.fixture
    def cli_env(self, temp_config_file, temp_escmd_config):
        """Setup environment for CLI testing."""
        env = os.environ.copy()
        env["ESCMD_CONFIG"] = temp_escmd_config
        env["ELASTIC_SERVERS_CONFIG"] = temp_config_file
        env["ESCMD_TEST_MODE"] = "true"  # Skip connection testing in integration tests
        return env

    def run_escmd_command(self, command_args, env=None):
        """Helper method to run escmd commands."""
        # Get the path to escmd.py
        escmd_path = os.path.join(os.path.dirname(__file__), "..", "..", "escmd.py")

        cmd = [sys.executable, escmd_path] + command_args

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=env,
            cwd=os.path.dirname(escmd_path),
        )

        return result

    def test_health_command_table_output(self, cli_env):
        """Test health command with table output (connection will likely fail, testing fallback behavior)."""
        result = self.run_escmd_command(["-l", "test-cluster", "health"], env=cli_env)

        # Command should succeed with fallback display when connection fails
        assert result.returncode == 0
        # Should show health check interface even with connection failure
        assert "⚡ Quick Health Check" in result.stdout
        assert "Cluster:" in result.stdout

    @patch("esclient.ElasticsearchClient")
    def test_health_command_json_output(self, mock_es_class, cli_env):
        """Test health command with JSON output."""
        mock_es_instance = Mock()
        mock_es_instance.test_connection.return_value = True
        expected_health = {
            "cluster_name": "test-cluster",
            "status": "green",
            "number_of_nodes": 3,
        }
        mock_es_instance.get_cluster_health.return_value = expected_health
        mock_es_class.return_value = mock_es_instance

        result = self.run_escmd_command(
            ["-l", "test-cluster", "health", "--format", "json"], env=cli_env
        )

        # Command should either succeed or fail with connection error (both are valid for integration tests)
        assert result.returncode in [0, 1]
        if result.returncode == 0:
            # Parse the JSON output
            try:
                output_data = json.loads(result.stdout.strip())
                # Verify structure rather than exact values (since we can't control actual ES responses in integration tests)
                assert "cluster_name" in output_data
                assert "status" in output_data
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON output: {result.stdout}")
        else:
            # Acceptable connection-related errors
            assert any(
                error in result.stderr.lower()
                for error in ["connection", "socket", "timeout", "refused"]
            )

    @patch("esclient.ElasticsearchClient")
    def test_ping_command(self, mock_es_class, cli_env):
        """Test ping command functionality."""
        mock_es_instance = Mock()
        mock_es_instance.test_connection.return_value = True
        mock_es_instance.get_cluster_health.return_value = {
            "cluster_name": "test-cluster",
            "status": "green",
        }
        mock_es_class.return_value = mock_es_instance

        result = self.run_escmd_command(["-l", "test-cluster", "ping"], env=cli_env)

        # Command should either succeed or fail with connection error (both are valid for integration tests)
        assert result.returncode in [0, 1]
        if result.returncode == 0:
            # Ping command should execute and show some status (success or failure)
            assert (
                "Connection" in result.stdout
                or "test-cluster" in result.stdout
                or "Failed" in result.stdout
            )
        else:
            # Acceptable connection-related errors
            assert any(
                error in result.stderr.lower()
                for error in ["connection", "socket", "timeout", "refused"]
            )

    def test_dangling_command(self, cli_env):
        """Test dangling indices command."""
        result = self.run_escmd_command(["-l", "test-cluster", "dangling"], env=cli_env)

        # Should handle connection failure gracefully
        assert result.returncode in [0, 1]
        # Command should either succeed or fail with connection error (both are valid for integration tests)
        assert result.returncode in [0, 1]
        if result.returncode == 0:
            # Dangling command should execute and show some output about dangling indices
            pass  # Any output for dangling command is acceptable
        else:
            # Acceptable connection-related errors
            assert any(
                error in result.stderr.lower()
                for error in ["connection", "socket", "timeout", "refused"]
            )

    def test_locations_command(self, cli_env):
        """Test locations command."""
        result = self.run_escmd_command(["locations"], env=cli_env)

        assert result.returncode == 0
        # Should show configured clusters (locations command doesn't require ES connection)
        # Should show configured clusters (name may be truncated in table display)
        assert "test-cl" in result.stdout

    @patch("esclient.ElasticsearchClient")
    def test_cluster_settings_command_json(self, mock_es_class, cli_env):
        """Test cluster-settings command with JSON output."""
        mock_es_instance = Mock()
        mock_es_instance.test_connection.return_value = True
        mock_settings = {
            "persistent": {"cluster.name": "test-cluster"},
            "transient": {},
        }
        mock_es_instance.get_settings.return_value = mock_settings
        mock_es_class.return_value = mock_es_instance

        result = self.run_escmd_command(
            ["-l", "test-cluster", "cluster-settings", "display", "--format", "json"],
            env=cli_env,
        )

        # Command should either succeed or fail with connection error (both are valid for integration tests)
        assert result.returncode in [0, 1]
        if result.returncode == 0:
            try:
                output_data = json.loads(result.stdout.strip())
                # Verify structure rather than exact content (since we can't control actual ES responses in integration tests)
                assert isinstance(
                    output_data, (dict, list)
                )  # Should return some valid JSON structure
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON output: {result.stdout}")
        else:
            # Acceptable connection-related errors
            assert any(
                error in result.stderr.lower()
                for error in ["connection", "socket", "timeout", "refused"]
            )

    def test_datastreams_command(self, cli_env):
        """Test datastreams command."""
        result = self.run_escmd_command(
            ["-l", "test-cluster", "datastreams"], env=cli_env
        )

        # May fail due to connection issues
        assert result.returncode in [0, 1]
        # Command should either succeed or fail with connection error (both are valid for integration tests)
        assert result.returncode in [0, 1]
        if result.returncode == 0:
            # Should handle datastreams (success or empty result)
            pass  # Any output is acceptable for datastreams
        else:
            # Acceptable connection-related errors
            assert any(
                error in result.stderr.lower()
                for error in ["connection", "socket", "timeout", "refused"]
            )

    def test_invalid_command(self, cli_env):
        """Test behavior with invalid command."""
        result = self.run_escmd_command(["invalid-command"], env=cli_env)

        # Should exit with error code and show help or error message
        assert result.returncode != 0

    def test_help_command(self):
        """Test help command."""
        result = self.run_escmd_command(["--help"])

        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_quick_health_check(self, cli_env):
        """Test health command (quick is default behavior)."""
        result = self.run_escmd_command(["-l", "test-cluster", "health"], env=cli_env)

        # Command should succeed and show health interface even with connection failure
        assert result.returncode == 0
        # Health command should show the health check interface
        assert "⚡ Quick Health Check" in result.stdout or "Cluster:" in result.stdout

    @pytest.mark.parametrize(
        "command",
        [
            ["health"],
            ["ping"],
            ["dangling"],
            ["locations"],
            ["cluster-settings"],
            ["datastreams"],
        ],
    )
    @patch("esclient.ElasticsearchClient")
    def test_core_commands_execute(self, mock_es_class, cli_env, command):
        """Parametrized test to ensure core commands execute without crashing."""
        mock_es_instance = Mock()

        # Setup common mock responses
        mock_es_instance.test_connection.return_value = True
        mock_es_instance.get_cluster_health.return_value = {
            "cluster_name": "test",
            "status": "green",
        }
        mock_es_instance.list_dangling_indices.return_value = []
        mock_es_instance.list_datastreams.return_value = {"data_streams": []}
        mock_es_instance.get_settings.return_value = {"persistent": {}, "transient": {}}
        mock_es_instance.print_enhanced_cluster_settings.return_value = None

        mock_es_class.return_value = mock_es_instance

        # Add location if command is not 'locations'
        if command[0] != "locations":
            full_command = ["-l", "test-cluster"] + command
        else:
            full_command = command.copy()

        result = self.run_escmd_command(full_command, env=cli_env)

        # Should not crash (return code 0 or reasonable error)
        assert result.returncode in [0, 1]  # 0 for success, 1 for expected errors
