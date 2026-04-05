"""
Unit tests for the RepositoriesRenderer class.

Tests the repositories display functionality including table formatting,
statistics calculation, and theme integration.
"""

import unittest
from unittest.mock import Mock, patch
from io import StringIO
import sys

# Add the parent directory to the path to import our modules
sys.path.insert(0, '../../')

from display.repositories_renderer import RepositoriesRenderer


class TestRepositoriesRenderer(unittest.TestCase):
    """Test cases for RepositoriesRenderer."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_theme_manager = Mock()
        self.mock_statistics_processor = Mock()
        self.mock_style_system = Mock()

        # Set up mock theme manager responses
        self.mock_theme_manager.get_full_theme_data.return_value = {
            'table_styles': {
                'border_style': 'bright_magenta',
                'header_style': 'bold bright_white on dark_magenta'
            }
        }
        self.mock_theme_manager.get_themed_style.return_value = 'cyan'

        # Set up mock style system responses
        self.mock_style_system._get_style.return_value = 'cyan'
        self.mock_style_system.get_table_box.return_value = None

        self.renderer = RepositoriesRenderer(
            theme_manager=self.mock_theme_manager,
            statistics_processor=self.mock_statistics_processor,
            style_system=self.mock_style_system
        )

    def test_init(self):
        """Test renderer initialization."""
        renderer = RepositoriesRenderer()
        self.assertIsNone(renderer.theme_manager)
        self.assertIsNone(renderer.statistics_processor)
        self.assertIsNone(renderer.style_system)

    def test_get_themed_style_with_theme_manager(self):
        """Test get_themed_style when theme manager is available."""
        self.mock_theme_manager.get_themed_style.return_value = 'red'
        result = self.renderer.get_themed_style('category', 'key', 'default')
        self.assertEqual(result, 'red')
        self.mock_theme_manager.get_themed_style.assert_called_once_with('category', 'key', 'default')

    def test_get_themed_style_without_theme_manager(self):
        """Test get_themed_style when theme manager is None."""
        renderer = RepositoriesRenderer()
        result = renderer.get_themed_style('category', 'key', 'default')
        self.assertEqual(result, 'default')

    def test_extract_repository_location_fs(self):
        """Test location extraction for filesystem repositories."""
        settings = {'location': '/path/to/backup'}
        result = self.renderer._extract_repository_location('fs', settings)
        self.assertEqual(result, '/path/to/backup')

    def test_extract_repository_location_s3(self):
        """Test location extraction for S3 repositories."""
        settings = {'bucket': 'my-bucket', 'base_path': 'backups/prod'}
        result = self.renderer._extract_repository_location('s3', settings)
        self.assertEqual(result, 's3://my-bucket/backups/prod')

    def test_extract_repository_location_s3_no_base_path(self):
        """Test location extraction for S3 repositories without base path."""
        settings = {'bucket': 'my-bucket'}
        result = self.renderer._extract_repository_location('s3', settings)
        self.assertEqual(result, 's3://my-bucket')

    def test_extract_repository_location_gcs(self):
        """Test location extraction for GCS repositories."""
        settings = {'bucket': 'my-gcs-bucket', 'base_path': 'es-backups'}
        result = self.renderer._extract_repository_location('gcs', settings)
        self.assertEqual(result, 'gs://my-gcs-bucket/es-backups')

    def test_extract_repository_location_azure(self):
        """Test location extraction for Azure repositories."""
        settings = {'account': 'mystorageaccount', 'container': 'backups'}
        result = self.renderer._extract_repository_location('azure', settings)
        self.assertEqual(result, 'azure://mystorageaccount/backups')

    def test_extract_repository_location_unknown_type(self):
        """Test location extraction for unknown repository types."""
        settings = {'path': '/some/path'}
        result = self.renderer._extract_repository_location('unknown', settings)
        self.assertEqual(result, '/some/path')

    def test_format_repository_settings(self):
        """Test repository settings formatting."""
        settings = {
            'compress': 'true',
            'chunk_size': '1GB',
            'access_key': 'secret123',  # Should be filtered out
            'readonly': 'false',
            'very_long_setting_name_that_should_be_truncated': 'very_long_value_that_exceeds_twenty_characters'
        }
        result = self.renderer._format_repository_settings(settings)

        # Should contain non-sensitive settings
        self.assertIn('compress: true', result)
        self.assertIn('chunk_size: 1GB', result)
        self.assertIn('readonly: false', result)

        # Should not contain sensitive settings
        self.assertNotIn('access_key', result)

        # Should show "+X more" when there are too many settings
        self.assertIn('(+', result)
        self.assertIn('more)', result)

    def test_format_repository_settings_empty(self):
        """Test repository settings formatting with empty settings."""
        settings = {}
        result = self.renderer._format_repository_settings(settings)
        self.assertEqual(result, "Default configuration")

    def test_get_repository_status_readonly(self):
        """Test repository status for readonly repositories."""
        settings = {'readonly': True}
        icon, text, style = self.renderer._get_repository_status('s3', settings)
        self.assertEqual(icon, "🔒")
        self.assertEqual(text, "Read-Only")

    def test_get_repository_status_cloud(self):
        """Test repository status for cloud repositories."""
        settings = {}
        icon, text, style = self.renderer._get_repository_status('s3', settings)
        self.assertEqual(icon, "✅")
        self.assertEqual(text, "Active")

    def test_get_repository_status_fs(self):
        """Test repository status for filesystem repositories."""
        settings = {}
        icon, text, style = self.renderer._get_repository_status('fs', settings)
        self.assertEqual(icon, "📁")
        self.assertEqual(text, "Local")

    def test_get_repository_status_unknown(self):
        """Test repository status for unknown types."""
        settings = {}
        icon, text, style = self.renderer._get_repository_status('unknown', settings)
        self.assertEqual(icon, "❓")
        self.assertEqual(text, "Unknown")

    def test_get_type_icon(self):
        """Test type icon retrieval."""
        self.assertEqual(self.renderer._get_type_icon('s3'), '🌐')
        self.assertEqual(self.renderer._get_type_icon('gcs'), '🌐')
        self.assertEqual(self.renderer._get_type_icon('azure'), '🌐')
        self.assertEqual(self.renderer._get_type_icon('fs'), '📁')
        self.assertEqual(self.renderer._get_type_icon('hdfs'), '📂')
        self.assertEqual(self.renderer._get_type_icon('unknown'), '❓')

    def test_format_bytes_simple(self):
        """Test simple byte formatting."""
        self.assertEqual(self.renderer._format_bytes_simple(512), "512B")
        self.assertEqual(self.renderer._format_bytes_simple(1024), "1.0KB")
        self.assertEqual(self.renderer._format_bytes_simple(1048576), "1.0MB")
        self.assertEqual(self.renderer._format_bytes_simple(1073741824), "1.0GB")
        self.assertEqual(self.renderer._format_bytes_simple(1099511627776), "1.0TB")

    def test_print_enhanced_repositories_table_empty(self):
        """Test printing with empty repository data."""
        mock_console = Mock()
        self.renderer.print_enhanced_repositories_table({}, mock_console)

        # Should show empty state panel (not just a simple message)
        mock_console.print.assert_called_once()

        # Get the call arguments
        call_args = mock_console.print.call_args
        panel_arg = call_args[0][0]  # First positional argument

        # Verify it's a Panel object (enhanced empty state)
        from rich.panel import Panel
        self.assertIsInstance(panel_arg, Panel)

    def test_print_enhanced_repositories_table_with_data(self):
        """Test printing with repository data."""
        repositories_data = {
            'backup-repo': {
                'type': 's3',
                'settings': {
                    'bucket': 'my-backup-bucket',
                    'base_path': 'elasticsearch',
                    'compress': 'true'
                }
            },
            'local-repo': {
                'type': 'fs',
                'settings': {
                    'location': '/var/backups/elasticsearch',
                    'readonly': True
                }
            }
        }

        mock_console = Mock()

        # This should not raise any exceptions
        try:
            self.renderer.print_enhanced_repositories_table(repositories_data, mock_console)
        except Exception as e:
            self.fail(f"print_enhanced_repositories_table raised an exception: {e}")

        # Verify console.print was called (multiple times for panels and table)
        self.assertTrue(mock_console.print.called)
        self.assertGreater(mock_console.print.call_count, 1)


if __name__ == '__main__':
    unittest.main()
