"""
ESterm Modules Package

This package contains modular components for the ESterm interactive terminal,
broken out from the monolithic esterm.py for better maintainability.

Modules:
- cluster_manager: Handles cluster connection and selection logic
- command_processor: Handles command parsing and execution
- terminal_ui: Handles user interface and display logic (original)
- themed_terminal_ui: Handles themed user interface and display logic
- theme_manager: Manages ESterm-specific themes independent from ESCMD
- health_monitor: Handles health monitoring and watching functionality
- help_system: Handles help display and command extraction
- terminal_session: Main session management and coordination
"""

from .cluster_manager import ClusterManager
from .command_processor import CommandProcessor
from .terminal_ui import TerminalUI
from .themed_terminal_ui import ThemedTerminalUI
from .theme_manager import EstermThemeManager
from .health_monitor import HealthMonitor
from .help_system import HelpSystem
from .terminal_session import TerminalSession

__all__ = [
    'ClusterManager',
    'CommandProcessor',
    'TerminalUI',
    'ThemedTerminalUI',
    'EstermThemeManager',
    'HealthMonitor',
    'HelpSystem',
    'TerminalSession'
]

__version__ = '1.0.0'
