"""
Pytest configuration and shared fixtures for escmd tests.
"""

import pytest
import argparse
from unittest.mock import Mock, MagicMock
from rich.console import Console
import tempfile
import yaml
import json

# Import the modules we want to test
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from command_handler import CommandHandler
from configuration_manager import ConfigurationManager


@pytest.fixture
def mock_es_client():
    """Mock Elasticsearch client with common methods."""
    client = Mock()

    # Health related methods
    client.get_cluster_health.return_value = {
        'cluster_name': 'test-cluster',
        'status': 'green',
        'number_of_nodes': 3,
        'number_of_data_nodes': 2,
        'active_primary_shards': 10,
        'active_shards': 20
    }

    # Connection methods
    client.ping.return_value = True
    client.test_connection.return_value = True

    # Index related methods
    client.list_dangling_indices.return_value = []
    client.list_datastreams.return_value = {'data_streams': []}
    client.get_indices_stats.return_value = {}

    # Settings
    client.get_settings.return_value = {'persistent': {}, 'transient': {}}
    client.print_enhanced_cluster_settings.return_value = None

    # Style system methods - return renderable strings instead of Mock objects
    client.style_system = Mock()
    client.style_system.create_semantic_text.return_value = "Complete"
    client.style_system.apply_status_style.return_value = "GREEN"
    client.style_system.create_status_text.return_value = "HEALTHY"

    # Other common methods
    client.flush_synced_elasticsearch.return_value = {'_shards': {'failed': 0}}
    client.host1 = 'localhost'
    client.port = 9200
    client.use_ssl = False
    client.verify_certs = True
    client.elastic_username = None
    client.elastic_authentication = False
    client.elastic_username = None
    client.elastic_password = None

    return client


@pytest.fixture
def mock_console():
    """Mock Rich console."""
    console = Mock()  # Remove spec to allow additional attributes
    console.get_time.return_value = 0.0  # Add get_time method for Progress compatibility
    console.__enter__ = Mock(return_value=console)  # Support context manager
    console.__exit__ = Mock(return_value=None)  # Support context manager
    return console


@pytest.fixture
def sample_args():
    """Create sample arguments for testing."""
    args = argparse.Namespace()
    args.command = 'health'
    args.format = 'table'
    args.locations = 'test-cluster'
    return args


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    config_data = {
        'servers': [
            {
                'name': 'DEFAULT',
                'hostname': '127.0.0.1',
                'port': 9200,
                'use_ssl': False
            },
            {
                'name': 'test-cluster',
                'hostname': 'test.example.com',
                'port': 9200,
                'use_ssl': True,
                'elastic_username': 'test_user',
                'elastic_password': 'test_pass'
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        yield f.name

    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def temp_escmd_config():
    """Create a temporary escmd.json config file."""
    config_data = {
        'current_cluster': 'test-cluster',
        'box_style': 'rounded',
        'health_style': 'dashboard'
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        yield f.name

    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def location_config():
    """Sample location configuration."""
    return {
        'hostname': 'test.example.com',
        'port': 9200,
        'use_ssl': True,
        'username': 'test_user',
        'password': 'test_pass',
        'health_style': 'dashboard'
    }


@pytest.fixture
def command_handler(mock_es_client, sample_args, mock_console, temp_config_file, location_config):
    """Create a CommandHandler instance with mocked dependencies."""
    return CommandHandler(
        es_client=mock_es_client,
        args=sample_args,
        console=mock_console,
        config_file=temp_config_file,
        location_config=location_config,
        current_location='test-cluster'
    )
