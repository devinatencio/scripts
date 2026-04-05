#!/usr/bin/env python3
"""
Terminal Session Module for ESterm

Main coordination class that brings together all ESterm modules:
- Manages the overall terminal session state
- Coordinates between different modules
- Handles the main run loop and user interaction
- Manages session initialization and cleanup
"""

import os
import sys
from typing import Optional

# Ensure the escmd root is on sys.path so version.py is importable
_parent_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from version import VERSION as _DEFAULT_VERSION, DATE as _DEFAULT_DATE
except ImportError:
    _DEFAULT_VERSION = "3.8.4"
    _DEFAULT_DATE = "04/04/2026"

# Import Rich components
from rich.console import Console

# Import ESterm modules
from .cluster_manager import ClusterManager
from .command_processor import CommandProcessor
from .themed_terminal_ui import ThemedTerminalUI
from .health_monitor import HealthMonitor
from .help_system import HelpSystem


class TerminalSession:
    """
    Main coordination class for ESterm interactive sessions.

    This class manages the overall terminal session, coordinating between
    all the different modules and handling the main interaction loop.
    """

    def __init__(self, version: str = _DEFAULT_VERSION, date: str = _DEFAULT_DATE):
        """
        Initialize the terminal session.

        Args:
            version: ESterm version string
            date: Version date string
        """
        self.version = version
        self.date = date
        self.running = True

        # Initialize Rich console
        self.console = Console()

        # Initialize all modules
        self.cluster_manager = ClusterManager(self.console)
        self.terminal_ui = ThemedTerminalUI(self.console)
        self.health_monitor = HealthMonitor(self.console)

        # Initialize command processor first to get builtin commands
        self.command_processor = CommandProcessor(
            self.console,
            version=self.version,
            date=self.date,
            theme_manager=getattr(self.terminal_ui, 'theme_manager', None)
        )

        # Initialize help system with builtin commands
        self.help_system = HelpSystem(self.console, self.command_processor.builtin_commands)

        # Update command processor with help system
        self.command_processor.help_system = self.help_system

        # Load state and setup
        self._setup_session()

    def _setup_session(self):
        """Setup the terminal session environment."""
        try:
            # Clear cache on startup to ensure clean state
            self._clear_performance_cache()
        except Exception:
            # Continue if cache clearing fails
            pass

        # Load cluster configuration
        self.cluster_manager.load_cluster_configuration()

    def _clear_performance_cache(self):
        """Clear the performance cache on startup."""
        try:
            from performance import default_cache
            default_cache.invalidate()  # Clear all cached data on startup
        except ImportError:
            # Performance module not available, continue without clearing cache
            pass

    def run(self):
        """Main terminal loop."""
        self.console.clear()
        self.terminal_ui.show_banner(self.version, self.date)

        # Try to auto-connect to default cluster, if that fails show cluster selection
        if not self.cluster_manager.is_connected():
            # Try to connect to default cluster
            default_cluster = None
            if self.cluster_manager.config_manager:
                default_cluster = self.cluster_manager.config_manager.get_default_cluster()

            self._handle_initial_connection(default_cluster)

        # Main interaction loop
        while self.running:
            try:
                # Get user input with proper prompt
                prompt_text = self.terminal_ui.get_prompt(self.cluster_manager)

                try:
                    command_line = self.terminal_ui.get_user_input_with_history(prompt_text)
                except EOFError:
                    self.console.print("\n[yellow]Goodbye![/yellow]")
                    break
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Use 'exit' to quit or Ctrl+D to exit gracefully.[/yellow]")
                    continue

                # Handle empty input
                if not command_line or not command_line.strip():
                    continue

                # Parse the command
                command, args = self.command_processor.parse_command(command_line)
                if command is None:
                    continue

                # Validate command before execution
                is_valid, error_msg = self.command_processor.validate_command(command, args)
                if not is_valid:
                    self.console.print(error_msg)
                    continue

                # Check for built-in commands first
                if self.command_processor.is_builtin_command(command):
                    should_continue = self.command_processor.execute_builtin_command(
                        command, args,
                        self.cluster_manager,
                        self.terminal_ui,
                        self.health_monitor
                    )
                    if not should_continue:
                        # Built-in command requested exit
                        self.running = False
                        break
                    continue



                # Execute ESCMD command
                success = self.command_processor.execute_escmd_command(
                    command, args, self.cluster_manager
                )

                if not success:
                    # Command execution failed, but continue session
                    pass

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit.[/yellow]")
                continue
            except EOFError:
                # Ctrl+D pressed
                self.console.print("\n[yellow]Goodbye![/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Unexpected error: {e}[/red]")
                # In debug mode, show full traceback
                if os.environ.get('ESTERM_DEBUG'):
                    import traceback
                    self.console.print(f"[red]Traceback:[/red]\n{traceback.format_exc()}")

        # Cleanup on exit
        self._cleanup_session()



    def connect_to_cluster(self, location: Optional[str] = None) -> bool:
        """
        Connect to a specific cluster or show cluster selection.

        Args:
            location: Specific cluster location to connect to

        Returns:
            bool: True if connection successful
        """
        if location:
            return self.cluster_manager.connect_to_cluster(location)
        else:
            return self.cluster_manager.show_cluster_selection()

    def disconnect_from_cluster(self):
        """Disconnect from current cluster."""
        self.cluster_manager.disconnect()

    def show_status(self):
        """Show current session status."""
        self.terminal_ui.show_status(self.cluster_manager)

    def show_help(self, command: Optional[str] = None):
        """
        Show help information.

        Args:
            command: Optional specific command to show help for
        """
        if command:
            self.help_system.show_command_help(command)
        else:
            self.help_system.show_general_help()

    def clear_screen(self):
        """Clear the terminal screen."""
        self.terminal_ui.clear_screen()

    def get_current_cluster(self) -> Optional[str]:
        """
        Get the currently connected cluster name.

        Returns:
            str or None: Current cluster name or None if not connected
        """
        return self.cluster_manager.get_current_cluster()

    def is_connected(self) -> bool:
        """
        Check if currently connected to a cluster.

        Returns:
            bool: True if connected
        """
        return self.cluster_manager.is_connected()

    def get_available_clusters(self) -> list:
        """
        Get list of available cluster names.

        Returns:
            list: List of available cluster names
        """
        return self.cluster_manager.get_available_clusters()

    def execute_command(self, command_line: str) -> bool:
        """
        Execute a command programmatically.

        Args:
            command_line: Full command line to execute

        Returns:
            bool: True if command executed successfully
        """
        try:
            command, args = self.command_processor.parse_command(command_line)
            if command is None:
                return False

            # Validate command
            is_valid, error_msg = self.command_processor.validate_command(command, args)
            if not is_valid:
                self.console.print(error_msg)
                return False

            # Execute built-in or ESCMD command
            if self.command_processor.is_builtin_command(command):
                return self.command_processor.execute_builtin_command(
                    command, args,
                    self.cluster_manager,
                    self.terminal_ui,
                    self.health_monitor
                )
            else:
                return self.command_processor.execute_escmd_command(
                    command, args, self.cluster_manager
                )

        except Exception as e:
            self.console.print(f"[red]Command execution error: {e}[/red]")
            return False

    def stop_session(self):
        """Stop the terminal session gracefully."""
        self.running = False

    def _cleanup_session(self):
        """Cleanup session resources."""
        try:
            # Stop any ongoing monitoring
            if self.health_monitor:
                self.health_monitor.stop_monitoring(silent=True)

            # Disconnect from cluster
            if self.cluster_manager:
                self.cluster_manager.disconnect()

        except Exception:
            # Don't let cleanup errors prevent exit
            pass

    def get_session_info(self) -> dict:
        """
        Get information about the current session.

        Returns:
            dict: Session information
        """
        return {
            'version': self.version,
            'date': self.date,
            'connected': self.is_connected(),
            'current_cluster': self.get_current_cluster(),
            'available_clusters': len(self.get_available_clusters()),
            'running': self.running
        }

    def set_debug_mode(self, enabled: bool):
        """
        Enable or disable debug mode.

        Args:
            enabled: Whether to enable debug mode
        """
        if enabled:
            os.environ['ESTERM_DEBUG'] = '1'
        else:
            os.environ.pop('ESTERM_DEBUG', None)

    def is_debug_mode(self) -> bool:
        """
        Check if debug mode is enabled.

        Returns:
            bool: True if debug mode is enabled
        """
        return bool(os.environ.get('ESTERM_DEBUG'))

    # Context manager support for programmatic use
    def __enter__(self):
        """Context manager entry."""
        return self

    def _handle_initial_connection(self, default_cluster):
        """Handle initial cluster connection setup."""
        if default_cluster:
            self.console.print(f"[blue]Attempting to connect to default cluster: {default_cluster}[/blue]")
            if not self.cluster_manager.connect_to_cluster(default_cluster):
                # Default connection failed, show cluster selection
                self.console.print("[yellow]Failed to connect to default cluster. Showing cluster selection...[/yellow]")
                self.cluster_manager.show_cluster_selection()
        else:
            # No default cluster, show selection
            available_clusters = self.cluster_manager.get_available_clusters()
            if available_clusters:
                self.console.print("[yellow]No default cluster configured. Showing cluster selection...[/yellow]")
                self.cluster_manager.show_cluster_selection()
            else:
                self.console.print("[yellow]No clusters configured. You can use ESterm without a connection or configure clusters first.[/yellow]")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self._cleanup_session()
        return False  # Don't suppress exceptions
