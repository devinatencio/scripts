#!/usr/bin/env python3
"""
Unit tests for DanglingReport class.

Tests the multi-cluster dangling indices reporting functionality,
including data collection, aggregation, and formatted output.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os
from datetime import datetime
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from reports.dangling_report import DanglingReport
from rich.console import Console


class TestDanglingReport(unittest.TestCase):
    """Test cases for DanglingReport class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config_manager = Mock()
        self.mock_console = Mock()
        self.theme_styles = {
            'border_style': 'white',
            'header_style': 'bold white',
            'panel_styles': {
                'success': 'bold',
                'warning': 'bold',
                'error': 'bold',
                'info': 'bold',
                'title': 'bold white'
            },
            'health_styles': {
                'green': {'text': 'bold', 'icon': 'bold'},
                'yellow': {'text': 'bold', 'icon': 'bold'},
                'red': {'text': 'bold', 'icon': 'bold'}
            }
        }

        # Mock cluster groups
        self.mock_config_manager.get_cluster_groups.return_value = {
            'test': ['cluster1', 'cluster2'],
            'prod': ['prod-cluster1', 'prod-cluster2', 'prod-cluster3']
        }

        # Mock cluster group members
        self.mock_config_manager.get_cluster_group_members.return_value = ['cluster1', 'cluster2']
        self.mock_config_manager.is_cluster_group.return_value = True

        self.report = DanglingReport(
            configuration_manager=self.mock_config_manager,
            console=self.mock_console,
            theme_styles=self.theme_styles
        )

    def test_init(self):
        """Test DanglingReport initialization."""
        self.assertEqual(self.report.config_manager, self.mock_config_manager)
        self.assertEqual(self.report.console, self.mock_console)
        self.assertEqual(self.report.theme_styles, self.theme_styles)
        self.assertIsNotNone(self.report.logger)

    def test_init_with_defaults(self):
        """Test DanglingReport initialization with default values."""
        report = DanglingReport(self.mock_config_manager)
        self.assertIsNotNone(report.console)
        self.assertIsNotNone(report.theme_styles)

    def test_generate_cluster_group_report_invalid_group(self):
        """Test report generation with invalid cluster group."""
        self.mock_config_manager.is_cluster_group.return_value = False
        self.mock_config_manager.get_cluster_groups.return_value = {'prod': ['prod1', 'prod2']}

        result = self.report.generate_cluster_group_report('nonexistent', 'json')

        self.assertIn('error', result)
        self.assertIn('available_groups', result)
        self.assertEqual(result['available_groups'], ['prod'])

    def test_generate_cluster_group_report_empty_group(self):
        """Test report generation with empty cluster group."""
        self.mock_config_manager.is_cluster_group.return_value = True
        self.mock_config_manager.get_cluster_group_members.return_value = []

        result = self.report.generate_cluster_group_report('empty-group', 'json')

        self.assertIn('error', result)
        self.assertIn('group_name', result)
        self.assertEqual(result['group_name'], 'empty-group')

    @patch('reports.dangling_report.subprocess.run')
    def test_get_cluster_dangling_data_success(self, mock_subprocess):
        """Test successful cluster data collection."""
        # Mock successful subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'dangling_indices': [
                {
                    'index_name': 'test-index-001',
                    'index_uuid': 'abc123-def456-ghi789',
                    'creation_date_millis': 1640995200000,
                    'node_ids': ['node1', 'node2']
                }
            ]
        })
        mock_result.stderr = 'Cluster: test-cluster\nNodes: 3'
        mock_subprocess.return_value = mock_result

        result = self.report._get_cluster_dangling_data('test-cluster')

        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['dangling_indices']), 1)
        self.assertEqual(result['dangling_indices'][0]['index_name'], 'test-index-001')
        self.assertIn('cluster_info', result)

    @patch('reports.dangling_report.subprocess.run')
    def test_get_cluster_dangling_data_error(self, mock_subprocess):
        """Test cluster data collection with error."""
        # Mock failed subprocess response
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ''
        mock_result.stderr = 'Connection refused'
        mock_subprocess.return_value = mock_result

        result = self.report._get_cluster_dangling_data('failed-cluster')

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error'], 'Connection refused')
        self.assertEqual(len(result['dangling_indices']), 0)

    @patch('reports.dangling_report.subprocess.run')
    def test_get_cluster_dangling_data_timeout(self, mock_subprocess):
        """Test cluster data collection with timeout."""
        from subprocess import TimeoutExpired
        mock_subprocess.side_effect = TimeoutExpired('cmd', 60)

        result = self.report._get_cluster_dangling_data('slow-cluster')

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error'], 'Query timeout (60s)')

    @patch('reports.dangling_report.subprocess.run')
    def test_get_cluster_dangling_data_invalid_json(self, mock_subprocess):
        """Test cluster data collection with invalid JSON response."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'invalid json response'
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result

        result = self.report._get_cluster_dangling_data('bad-json-cluster')

        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid JSON response', result['error'])

    def test_extract_cluster_info(self):
        """Test cluster info extraction from stderr."""
        stderr_output = "Cluster: my-test-cluster\nNodes: 5\nOther info"

        result = self.report._extract_cluster_info(stderr_output)

        self.assertEqual(result['cluster_name'], 'my-test-cluster')
        self.assertEqual(result['node_count'], 5)

    def test_extract_cluster_info_empty(self):
        """Test cluster info extraction with empty stderr."""
        result = self.report._extract_cluster_info('')
        self.assertEqual(result, {})

    @patch.object(DanglingReport, '_collect_dangling_data')
    def test_format_json_report(self, mock_collect):
        """Test JSON report formatting."""
        # Mock collected data
        mock_collect.return_value = {
            'group_name': 'test',
            'cluster_count': 2,
            'clusters': {
                'cluster1': {
                    'status': 'success',
                    'dangling_indices': [
                        {
                            'index_name': 'test-index',
                            'index_uuid': 'uuid-123',
                            'creation_date_millis': 1640995200000,
                            'node_ids': ['node1']
                        }
                    ],
                    'cluster_info': {'cluster_name': 'cluster1'},
                    'query_time': '2025-01-01T12:00:00'
                },
                'cluster2': {
                    'status': 'success',
                    'dangling_indices': [],
                    'cluster_info': {'cluster_name': 'cluster2'},
                    'query_time': '2025-01-01T12:00:01'
                }
            },
            'summary': {
                'total_dangling': 1,
                'clusters_with_dangling': 1,
                'clusters_queried': 2,
                'clusters_failed': 0,
                'unique_nodes_affected': 1,
                'oldest_dangling': 1640995200000,
                'newest_dangling': 1640995200000
            },
            'timestamp': '2025-01-01T12:00:00'
        }

        result = self.report.generate_cluster_group_report('test', 'json')

        self.assertIn('report_type', result)
        self.assertEqual(result['report_type'], 'cluster_group_dangling_analysis')
        self.assertEqual(result['group_name'], 'test')
        self.assertIn('summary', result)
        self.assertIn('clusters', result)
        self.assertEqual(result['summary']['total_dangling_indices'], 1)
        self.assertEqual(result['summary']['clusters_with_dangling'], 1)

    @patch.object(DanglingReport, '_collect_dangling_data')
    @patch.object(DanglingReport, '_display_summary_panel')
    @patch.object(DanglingReport, '_display_cluster_breakdown')
    @patch.object(DanglingReport, '_display_dangling_details')
    @patch.object(DanglingReport, '_display_recommendations')
    def test_display_table_report(self, mock_recommendations, mock_details,
                                 mock_breakdown, mock_summary, mock_collect):
        """Test table report display."""
        # Mock collected data
        mock_collect.return_value = {
            'group_name': 'test',
            'cluster_count': 2,
            'clusters': {},
            'summary': {
                'total_dangling': 0,
                'clusters_with_dangling': 0,
                'clusters_queried': 2,
                'clusters_failed': 0,
                'unique_nodes_affected': 0,
                'oldest_dangling': None,
                'newest_dangling': None
            },
            'timestamp': '2025-01-01T12:00:00'
        }

        result = self.report.generate_cluster_group_report('test', 'table')

        self.assertTrue(result['displayed'])
        self.assertIn('summary', result)
        self.assertIn('timestamp', result)

        # Verify all display methods were called
        mock_summary.assert_called_once()
        mock_breakdown.assert_called_once()
        mock_recommendations.assert_called_once()
        # mock_details should not be called when total_dangling is 0
        mock_details.assert_not_called()

    @patch.object(DanglingReport, '_collect_dangling_data')
    @patch.object(DanglingReport, '_display_summary_panel')
    @patch.object(DanglingReport, '_display_cluster_breakdown')
    @patch.object(DanglingReport, '_display_dangling_details')
    @patch.object(DanglingReport, '_display_recommendations')
    def test_display_table_report_with_dangling(self, mock_recommendations, mock_details,
                                               mock_breakdown, mock_summary, mock_collect):
        """Test table report display with dangling indices."""
        # Mock collected data with dangling indices
        mock_collect.return_value = {
            'group_name': 'test',
            'cluster_count': 2,
            'clusters': {},
            'summary': {
                'total_dangling': 5,  # Has dangling indices
                'clusters_with_dangling': 1,
                'clusters_queried': 2,
                'clusters_failed': 0,
                'unique_nodes_affected': 2,
                'oldest_dangling': None,
                'newest_dangling': None
            },
            'timestamp': '2025-01-01T12:00:00'
        }

        result = self.report.generate_cluster_group_report('test', 'table')

        self.assertTrue(result['displayed'])
        # Verify details are shown when there are dangling indices
        mock_details.assert_called_once()

    def test_show_error_panel(self):
        """Test error panel display."""
        # This method primarily calls console.print, so we just verify it doesn't crash
        try:
            self.report._show_error_panel("Test Error", "This is a test error message")
        except Exception as e:
            self.fail(f"_show_error_panel raised an exception: {e}")

    @patch('reports.dangling_report.ThreadPoolExecutor')
    @patch('reports.dangling_report.Progress')
    def test_collect_dangling_data_parallel_execution(self, mock_progress, mock_executor):
        """Test parallel data collection from multiple clusters."""
        # Mock the progress bar
        mock_progress_instance = Mock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 'task_id'

        # Mock the executor
        mock_executor_instance = Mock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance

        # Mock futures
        mock_future1 = Mock()
        mock_future2 = Mock()
        mock_future1.result.return_value = {
            'status': 'success',
            'dangling_indices': [{'index_name': 'test1', 'node_ids': ['node1']}],
            'cluster_info': {}
        }
        mock_future2.result.return_value = {
            'status': 'success',
            'dangling_indices': [],
            'cluster_info': {}
        }

        mock_executor_instance.submit.side_effect = [mock_future1, mock_future2]

        # Mock as_completed to return futures in order
        with patch('reports.dangling_report.as_completed', return_value=[mock_future1, mock_future2]):
            # Create a mapping for futures to clusters
            mock_executor_instance.submit.side_effect = lambda func, cluster: {
                'cluster1': mock_future1,
                'cluster2': mock_future2
            }[cluster]

            result = self.report._collect_dangling_data('test', ['cluster1', 'cluster2'])

        self.assertEqual(result['group_name'], 'test')
        self.assertEqual(result['cluster_count'], 2)
        self.assertEqual(result['summary']['total_dangling'], 1)
        self.assertEqual(result['summary']['clusters_with_dangling'], 1)
        self.assertEqual(result['summary']['clusters_queried'], 2)

    def test_get_default_styles(self):
        """Test default styles creation."""
        styles = self.report._get_default_styles()

        expected_keys = ['border_style', 'header_style', 'panel_styles', 'health_styles']

        for key in expected_keys:
            self.assertIn(key, styles)

        # Test nested panel_styles
        self.assertIn('success', styles['panel_styles'])
        self.assertIn('warning', styles['panel_styles'])
        self.assertIn('error', styles['panel_styles'])
        self.assertIn('info', styles['panel_styles'])

        # Test nested health_styles
        self.assertIn('green', styles['health_styles'])
        self.assertIn('yellow', styles['health_styles'])
        self.assertIn('red', styles['health_styles'])

    def test_get_health_style(self):
        """Test theme health style helper method."""
        # Test with valid health type and style part
        result = self.report._get_health_style('green', 'text')
        self.assertEqual(result, 'bold')

        # Test with valid health type, default style part
        result = self.report._get_health_style('yellow')
        self.assertEqual(result, 'bold')

        # Test with invalid health type (should return the health type itself)
        result = self.report._get_health_style('purple', 'text')
        self.assertEqual(result, 'purple')

        # Test with missing health_styles in theme
        report_no_health = DanglingReport(
            self.mock_config_manager,
            theme_styles={'other_styles': {}}
        )
        result = report_no_health._get_health_style('green', 'text')
        self.assertEqual(result, 'green')

    def test_get_panel_style(self):
        """Test theme panel style helper method."""
        # Test with valid panel type
        result = self.report._get_panel_style('info')
        self.assertEqual(result, 'bold')

        # Test with invalid panel type (should return the panel type itself)
        result = self.report._get_panel_style('custom')
        self.assertEqual(result, 'custom')

        # Test with missing panel_styles in theme
        report_no_panel = DanglingReport(
            self.mock_config_manager,
            theme_styles={'other_styles': {}}
        )
        result = report_no_panel._get_panel_style('info')
        self.assertEqual(result, 'info')


if __name__ == '__main__':
    unittest.main()
