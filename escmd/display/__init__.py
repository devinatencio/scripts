"""
Display module for Elasticsearch command-line tool.

This module provides a clean separation of display logic from business logic,
making it easier to manage themes and presentation across the application.
"""

# Import modules for availability
from . import theme_manager
from . import table_renderer
from . import panel_renderer
from . import json_formatter
from . import progress_display
from . import replica_renderer
from . import storage_renderer
from . import index_renderer
from . import allocation_renderer
from . import recovery_renderer
from . import style_system
from . import version_renderer
from . import version_data
from . import locations_renderer
from . import locations_data
from . import settings_renderer
from . import settings_data
from . import repositories_renderer

# Import classes for direct access
try:
    from .theme_manager import ThemeManager
    from .table_renderer import TableRenderer
    from .panel_renderer import PanelRenderer
    from .json_formatter import JSONFormatter
    from .progress_display import ProgressDisplay
    from .replica_renderer import ReplicaRenderer
    from .storage_renderer import StorageRenderer
    from .index_renderer import IndexRenderer
    from .allocation_renderer import AllocationRenderer
    from .recovery_renderer import RecoveryRenderer
    from .style_system import StyleSystem
    from .version_renderer import VersionRenderer
    from .version_data import VersionDataCollector
    from .locations_renderer import LocationsRenderer
    from .locations_data import LocationsDataCollector
    from .settings_renderer import SettingsRenderer
    from .settings_data import SettingsDataCollector
    from .repositories_renderer import RepositoriesRenderer

    __all__ = [
        'ThemeManager',
        'TableRenderer',
        'PanelRenderer',
        'JSONFormatter',
        'ProgressDisplay',
        'ReplicaRenderer',
        'StorageRenderer',
        'IndexRenderer',
        'AllocationRenderer',
        'RecoveryRenderer',
        'StyleSystem',
        'VersionRenderer',
        'VersionDataCollector',
        'LocationsRenderer',
        'LocationsDataCollector',
        'SettingsRenderer',
        'SettingsDataCollector',
        'RepositoriesRenderer'
    ]
except ImportError as e:
    # Fallback if there are import issues during development
    __all__ = []
    print(f"Warning: Could not import display components: {e}")
