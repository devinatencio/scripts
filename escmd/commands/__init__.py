"""
Commands module for Elasticsearch command-line tool.

This module provides a clean separation of command processing logic from the main
ElasticsearchClient class, making it easier to test, maintain, and extend functionality.
"""

# Import the base command class
from .base_command import BaseCommand, CommandRegistry, create_command_registry

# Import command processors as they are created
try:
    from .cluster_commands import ClusterCommands
    from .indices_commands import IndicesCommands
    from .nodes_commands import NodesCommands
    from .snapshot_commands import SnapshotCommands
    from .allocation_commands import AllocationCommands
    from .settings_commands import SettingsCommands
    from .health_commands import HealthCommands
    from .utility_commands import UtilityCommands
    from .ilm_commands import ILMCommands
    from .replica_commands import ReplicaCommands
    from .datastream_commands import DatastreamCommands
    from .template_commands import TemplateCommands

    __all__ = [
        'BaseCommand',
        'CommandRegistry',
        'create_command_registry',
        'ClusterCommands',
        'IndicesCommands',
        'NodesCommands',
        'SnapshotCommands',
        'AllocationCommands',
        'SettingsCommands',
        'HealthCommands',
        'UtilityCommands',
        'ILMCommands',
        'ReplicaCommands',
        'DatastreamCommands',
        'TemplateCommands'
    ]
except ImportError as e:
    # Fallback during development - only include base classes
    __all__ = [
        'BaseCommand',
        'CommandRegistry',
        'create_command_registry'
    ]
    print(f"Warning: Could not import all command components: {e}")
