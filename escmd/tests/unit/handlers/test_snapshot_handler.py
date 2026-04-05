"""
Unit tests for the SnapshotHandler class repository creation functionality.

Tests the repository creation command handling including validation,
dry-run functionality, and error handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from argparse import Namespace

# Add the parent directories to the path to import our modules
sys.path.insert(0, '../../../')

from handlers.snapshot_handler import SnapshotHandler


class TestSnapshotHandlerRepositories(unittest.TestCase):
    """Test cases for SnapshotHandler repository functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_es_client = Mock()
        self.mock_console = Mock()
        self.mock_config_file = Mock()
        self.mock_location_config = Mock()
        self.current_location = "test-location"

        # Set up mock ES client components
        self.mock_es_client.snapshot_commands = Mock()
        self.mock_es_client.style_system = Mock()
        self.mock_es_client.show_message_box = Mock()

        # Set up style system responses
        self.mock_es_client.style_system.get_semantic_style.return_value = "cyan"

        self.handler = SnapshotHandler(
            self.mock_es_client,
            None,  # args - will be set per test
            self.mock_console,
            self.mock_config_file,
            self.mock_location_config,
            self.current_location
        )

    def test_handle_repositories_list_action(self):
        """Test handling repositories list action."""
        # Set up args with repositories_action
        self.handler.args = Namespace(repositories_action='list', format='table')

        with patch.object(self.handler, '_handle_list_repositories') as mock_list:
            self.handler.handle_repositories()
            mock_list.assert_called_once()

    def test_handle_repositories_create_action(self):
        """Test handling repositories create action."""
        # Set up args with repositories_action
        self.handler.args = Namespace(repositories_action='create')

        with patch.object(self.handler, '_handle_create_repository') as mock_create:
            self.handler.handle_repositories()
            mock_create.assert_called_once()

    def test_handle_repositories_backward_compatibility(self):
        """Test backward compatibility when no repositories_action is provided."""
        # Set up args without repositories_action
        self.handler.args = Namespace(format='table')

        with patch.object(self.handler, '_handle_list_repositories') as mock_list:
            self.handler.handle_repositories()
            mock_list.assert_called_once()

    def test_handle_repositories_unknown_action(self):
        """Test handling unknown repositories action."""
        # Set up args with unknown action
        self.handler.args = Namespace(repositories_action='unknown')

        self.handler.handle_repositories()

        # Should show error message
        self.mock_es_client.show_message_box.assert_called_once()
        call_args = self.mock_es_client.show_message_box.call_args
        self.assertIn("Unknown repositories action", call_args[0][1])

    def test_create_repository_s3_success(self):
        """Test successful S3 repository creation."""
        # Set up args for S3 repository
        self.handler.args = Namespace(
            name='test-s3-repo',
            type='s3',
            bucket='my-test-bucket',
            base_path='backups',
            region='us-west-2',
            compress=True,
            verify=True,
            force=True  # Skip confirmation
        )

        # Mock successful repository creation
        self.mock_es_client.snapshot_commands.create_repository.return_value = {
            "acknowledged": True
        }

        self.handler._handle_create_repository()

        # Verify repository creation was called with correct parameters
        self.mock_es_client.snapshot_commands.create_repository.assert_called_once()
        call_args = self.mock_es_client.snapshot_commands.create_repository.call_args

        self.assertEqual(call_args[0][0], 'test-s3-repo')  # repository name
        self.assertEqual(call_args[0][1], 's3')  # repository type

        settings = call_args[0][2]  # settings
        self.assertEqual(settings['bucket'], 'my-test-bucket')
        self.assertEqual(settings['base_path'], 'backups')
        self.assertEqual(settings['region'], 'us-west-2')
        self.assertTrue(settings['compress'])
        self.assertTrue(settings['verify'])

        # Should show success message
        success_calls = [call for call in self.mock_es_client.show_message_box.call_args_list
                        if 'Success' in call[0][0]]
        self.assertEqual(len(success_calls), 1)

    def test_create_repository_fs_success(self):
        """Test successful filesystem repository creation."""
        # Set up args for filesystem repository
        self.handler.args = Namespace(
            name='test-fs-repo',
            type='fs',
            location='/var/backups/elasticsearch',
            compress=True,
            readonly=True,
            force=True  # Skip confirmation
        )

        # Mock successful repository creation
        self.mock_es_client.snapshot_commands.create_repository.return_value = {
            "acknowledged": True
        }

        self.handler._handle_create_repository()

        # Verify repository creation was called with correct parameters
        call_args = self.mock_es_client.snapshot_commands.create_repository.call_args
        settings = call_args[0][2]  # settings

        self.assertEqual(settings['location'], '/var/backups/elasticsearch')
        self.assertTrue(settings['compress'])
        self.assertTrue(settings['readonly'])

    def test_create_repository_s3_missing_bucket(self):
        """Test S3 repository creation with missing bucket."""
        # Set up args for S3 repository without bucket
        self.handler.args = Namespace(
            name='test-s3-repo',
            type='s3',
            bucket=None  # Missing required bucket
        )

        self.handler._handle_create_repository()

        # Should show error message about missing bucket
        self.mock_es_client.show_message_box.assert_called_once()
        call_args = self.mock_es_client.show_message_box.call_args
        self.assertIn("Bucket is required", call_args[0][1])

        # Should not attempt to create repository
        self.mock_es_client.snapshot_commands.create_repository.assert_not_called()

    def test_create_repository_fs_missing_location(self):
        """Test filesystem repository creation with missing location."""
        # Set up args for filesystem repository without location
        self.handler.args = Namespace(
            name='test-fs-repo',
            type='fs',
            location=None  # Missing required location
        )

        self.handler._handle_create_repository()

        # Should show error message about missing location
        self.mock_es_client.show_message_box.assert_called_once()
        call_args = self.mock_es_client.show_message_box.call_args
        self.assertIn("Location is required", call_args[0][1])

        # Should not attempt to create repository
        self.mock_es_client.snapshot_commands.create_repository.assert_not_called()

    @patch('rich.console.Console')
    def test_create_repository_dry_run(self, mock_console_class):
        """Test repository creation dry run."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Set up args with dry-run
        self.handler.args = Namespace(
            name='test-repo',
            type='s3',
            bucket='test-bucket',
            dry_run=True
        )

        self.handler._handle_create_repository()

        # Should print dry-run information
        mock_console.print.assert_called()

        # Should not attempt to create repository
        self.mock_es_client.snapshot_commands.create_repository.assert_not_called()

    def test_create_repository_api_error(self):
        """Test repository creation with API error."""
        # Set up args
        self.handler.args = Namespace(
            name='test-repo',
            type='s3',
            bucket='test-bucket',
            force=True
        )

        # Mock API error
        self.mock_es_client.snapshot_commands.create_repository.return_value = {
            "error": "Repository already exists"
        }

        self.handler._handle_create_repository()

        # Should show error message
        error_calls = [call for call in self.mock_es_client.show_message_box.call_args_list
                      if 'Error' in call[0][0]]
        self.assertEqual(len(error_calls), 1)
        self.assertIn("Repository already exists", error_calls[0][0][1])

    @patch('rich.prompt.Confirm.ask')
    @patch('rich.console.Console')
    def test_create_repository_user_confirmation_yes(self, mock_console_class, mock_confirm):
        """Test repository creation with user confirmation - yes."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        mock_confirm.return_value = True  # User confirms

        # Set up args without force flag
        self.handler.args = Namespace(
            name='test-repo',
            type='s3',
            bucket='test-bucket'
            # No force=True, so should ask for confirmation
        )

        # Mock successful repository creation
        self.mock_es_client.snapshot_commands.create_repository.return_value = {
            "acknowledged": True
        }

        self.handler._handle_create_repository()

        # Should ask for confirmation
        mock_confirm.assert_called_once()

        # Should create repository
        self.mock_es_client.snapshot_commands.create_repository.assert_called_once()

    @patch('rich.prompt.Confirm.ask')
    @patch('rich.console.Console')
    def test_create_repository_user_confirmation_no(self, mock_console_class, mock_confirm):
        """Test repository creation with user confirmation - no."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        mock_confirm.return_value = False  # User cancels

        # Set up args without force flag
        self.handler.args = Namespace(
            name='test-repo',
            type='s3',
            bucket='test-bucket'
            # No force=True, so should ask for confirmation
        )

        self.handler._handle_create_repository()

        # Should ask for confirmation
        mock_confirm.assert_called_once()

        # Should not create repository
        self.mock_es_client.snapshot_commands.create_repository.assert_not_called()

        # Should show cancellation message
        info_calls = [call for call in self.mock_es_client.show_message_box.call_args_list
                     if 'Info' in call[0][0]]
        self.assertEqual(len(info_calls), 1)
        self.assertIn("cancelled", info_calls[0][0][1])

    def test_show_repository_dry_run(self):
        """Test _show_repository_dry_run method."""
        repository_name = "test-repo"
        repo_type = "s3"
        settings = {
            "bucket": "test-bucket",
            "compress": True,
            "region": "us-west-2"
        }

        with patch('rich.console.Console') as mock_console_class:
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            self.handler._show_repository_dry_run(repository_name, repo_type, settings)

            # Should create and print a panel
            mock_console.print.assert_called()

    def test_confirm_repository_creation(self):
        """Test _confirm_repository_creation method."""
        repository_name = "test-repo"
        repo_type = "s3"
        settings = {"bucket": "test-bucket"}

        with patch('rich.prompt.Confirm.ask') as mock_confirm, \
             patch.object(self.handler, '_show_repository_dry_run') as mock_dry_run:

            mock_confirm.return_value = True

            result = self.handler._confirm_repository_creation(repository_name, repo_type, settings)

            # Should show dry run info first
            mock_dry_run.assert_called_once_with(repository_name, repo_type, settings)

            # Should ask for confirmation
            mock_confirm.assert_called_once()

            # Should return True
            self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
