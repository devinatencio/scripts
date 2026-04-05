#!/usr/bin/env python3
"""
Command Processor Module for ESterm

Handles all command parsing and execution logic including:
- Command line parsing and argument extraction
- Built-in terminal command execution
- ESCMD command delegation and execution
- Special command handling and routing
- Error handling and user feedback
"""

import difflib
import os
import shlex
import sys
from typing import List, Tuple, Optional, Any, Dict

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
from rich.panel import Panel
from rich.text import Text

# Import core ESCMD modules
from command_handler import CommandHandler
from cli.argument_parser import create_argument_parser


class CommandProcessor:
    """
    Processes and executes commands within the ESterm interactive session.

    This class handles parsing user input, routing commands to appropriate
    handlers, and managing the execution flow for both built-in terminal
    commands and ESCMD operations.
    """

    def __init__(self, console, help_system=None, version=None, date=None, theme_manager=None):
        """
        Initialize the command processor.

        Args:
            console: Rich Console instance for output
            help_system: HelpSystem instance for enhanced help
            version: ESterm version string
            date: Version date string
            theme_manager: ESterm theme manager for styling
        """
        self.console = console
        self.help_system = help_system
        self.version = version or _DEFAULT_VERSION
        self.date = date or _DEFAULT_DATE
        self.theme_manager = theme_manager

        try:
            self.argument_parser = create_argument_parser()
        except Exception as e:
            self.console.print(f"[red]Warning: Could not create argument parser: {e}[/red]")
            self.argument_parser = None
        self.builtin_commands = {
            'exit', 'quit', 'q',
            'help', '?',
            'status', 'info',
            'clear', 'cls',
            'connect', 'switch',
            'disconnect',
            'cache-clear',
            'cache-refresh',
            'watch',
            'theme',
            'version',
            'action'
        }

    def parse_command(self, command_line: str) -> Tuple[Optional[str], List[str]]:
        """
        Parse command line into command and arguments.

        Args:
            command_line: Raw command line input from user

        Returns:
            Tuple[str, List[str]]: Command name and list of arguments
        """
        if not command_line or not command_line.strip():
            return None, []

        try:
            # Use shlex for proper argument parsing (handles quotes, escaping, etc.)
            parts = shlex.split(command_line.strip())
            if not parts:
                return None, []

            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            return command, args

        except ValueError as e:
            # Handle shlex parsing errors (unclosed quotes, etc.)
            self.console.print(f"[red]Command parsing error: {e}[/red]")
            return None, []

    def is_builtin_command(self, command: str) -> bool:
        """
        Check if a command is a built-in terminal command.

        Args:
            command: Command name to check

        Returns:
            bool: True if command is built-in
        """
        return command.lower() in self.builtin_commands

    def execute_builtin_command(self, command: str, args: List[str],
                               cluster_manager, terminal_ui, health_monitor) -> bool:
        """
        Execute built-in terminal commands.

        Args:
            command: Command name
            args: Command arguments
            cluster_manager: ClusterManager instance
            terminal_ui: TerminalUI instance
            health_monitor: HealthMonitor instance

        Returns:
            bool: True if should continue terminal session, False to exit
        """
        command = command.lower()

        if command in ['exit', 'quit', 'q']:
            self.console.print("[yellow]Goodbye![/yellow]")
            return False

        elif command in ['help', '?']:
            if self.help_system:
                # Use enhanced help system
                if args and len(args) > 0:
                    self.help_system.show_help(args[0])
                else:
                    self.help_system.show_help()
            else:
                # Fallback to basic help
                if args and len(args) > 0:
                    self._show_command_help(args[0])
                else:
                    terminal_ui.show_help()

        elif command in ['status', 'info']:
            terminal_ui.show_status(cluster_manager)

        elif command in ['clear', 'cls']:
            self.console.clear()

        elif command == 'connect':
            if args:
                # Connect to specific cluster
                cluster_name = args[0]
                success = cluster_manager.connect_to_cluster(cluster_name)
                if not success:
                    self.console.print(f"[red]Failed to connect to cluster: {cluster_name}[/red]")
            else:
                # Show cluster selection
                cluster_manager.show_cluster_selection()

        elif command == 'switch':
            # Alias for connect - show cluster selection
            cluster_manager.show_cluster_selection()

        elif command == 'version':
            # Use the enhanced version command from special_commands
            try:
                import sys
                import os

                # Add the parent directory to path to import special_commands
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)

                from cli.special_commands import handle_version
                handle_version(version=self.version, date=self.date)
            except ImportError:
                # Fallback to simple version display if import fails
                self.console.print(f"[green]ESterm version: {self.version} ({self.date})[/green]")

        elif command == 'disconnect':
            cluster_manager.disconnect()
            self.console.print("[yellow]Disconnected from cluster[/yellow]")

        elif command == 'cache-clear':
            self._clear_performance_cache()

        elif command == 'cache-refresh':
            self._refresh_indices_cache(cluster_manager)

        elif command == 'watch':
            # Handle watch health command
            if args and len(args) > 0 and args[0].lower() == 'health':
                # Extract interval from remaining args
                interval = 10  # default
                if len(args) > 1:
                    try:
                        interval = int(args[1])
                        if interval < 1:
                            interval = 1
                    except ValueError:
                        self.console.print("[yellow]Invalid interval, using 10 seconds[/yellow]")
                        interval = 10

                # Check if connected
                if not cluster_manager.is_connected():
                    self.console.print("[red]Not connected to any cluster. Use 'connect' first.[/red]")
                else:
                    # Start health monitoring
                    try:
                        # Create args-like object with interval
                        class HealthArgs:
                            def __init__(self, interval):
                                self.interval = interval
                                self.max_samples = 50

                        health_args = HealthArgs(interval)
                        health_monitor.watch_health(cluster_manager, health_args)
                    except Exception as e:
                        self.console.print(f"[red]Error in health monitoring: {e}[/red]")
            else:
                self.console.print("[red]Usage: watch health [interval][/red]")
                self.console.print("[dim]Example: watch health 5[/dim]")

        elif command == 'theme':
            # Handle theme commands - only works with ThemedTerminalUI
            if hasattr(terminal_ui, 'theme_manager'):
                if not args:
                    # List themes
                    terminal_ui.list_themes()
                elif len(args) == 1:
                    theme_name = args[0]
                    if theme_name in terminal_ui.theme_manager.get_available_themes():
                        success = terminal_ui.set_theme(theme_name)
                        if success:
                            self.console.print(f"[green]Theme changed to '{theme_name}'[/green]")
                        else:
                            self.console.print(f"[red]Failed to set theme '{theme_name}'[/red]")
                    else:
                        self.console.print(f"[red]Theme '{theme_name}' not found[/red]")
                        terminal_ui.list_themes()
                elif len(args) == 2 and args[0] == 'preview':
                    theme_name = args[1]
                    terminal_ui.preview_theme(theme_name)
                else:
                    self.console.print("[red]Usage: theme [name] | theme preview [name][/red]")
                    self.console.print("[dim]Examples:[/dim]")
                    self.console.print("[dim]  theme              - List available themes[/dim]")
                    self.console.print("[dim]  theme cyberpunk    - Switch to cyberpunk theme[/dim]")
                    self.console.print("[dim]  theme preview fire - Preview fire theme[/dim]")
            else:
                self.console.print("[yellow]Theme commands are only available with themed UI[/yellow]")

        elif command == 'action':
            # Handle action commands
            return self._handle_action_command(args, cluster_manager)

        else:
            self.console.print(f"[red]Unknown built-in command: {command}[/red]")
            self.console.print("[dim]Type 'help' for available commands[/dim]")

        return True

    def _handle_action_command(self, args: List[str], cluster_manager) -> bool:
        """
        Handle action subcommands (list, show, run).

        Args:
            args: Action command arguments
            cluster_manager: ClusterManager instance

        Returns:
            bool: True to continue session
        """
        try:
            if not args:
                # Default to list if no subcommand provided
                args = ['list']

            subcommand = args[0].lower()

            if subcommand == 'list':
                return self._execute_action_list()

            elif subcommand == 'show':
                if len(args) < 2:
                    self.console.print("[red]Usage: action show <action_name>[/red]")
                    return True
                action_name = args[1]
                return self._execute_action_show(action_name)

            elif subcommand == 'run':
                if len(args) < 2:
                    self.console.print("[red]Usage: action run <action_name> [options][/red]")
                    self.console.print("[dim]Examples:[/dim]")
                    self.console.print("[dim]  action run add-host --param-host server01[/dim]")
                    self.console.print("[dim]  action run add-host --param-host server01 --dry-run[/dim]")
                    self.console.print("[dim]  action run add-host --param-host server01 --quiet[/dim]")
                    return True

                # Check cluster connection for run commands
                if not cluster_manager.is_connected():
                    self.console.print("[red]Action execution requires an active cluster connection.[/red]")
                    self.console.print("[dim]Use 'connect' to connect to a cluster first.[/dim]")
                    return True

                return self._execute_action_run(args[1:], cluster_manager)

            else:
                self.console.print(f"[red]Unknown action subcommand: {subcommand}[/red]")
                self.console.print("[dim]Available subcommands: list, show, run[/dim]")
                return True

        except Exception as e:
            self.console.print(f"[red]Error in action command: {e}[/red]")
            return True

    def _execute_action_list(self) -> bool:
        """Execute action list command."""
        try:
            # Import and use ActionHandler
            from handlers.action_handler import ActionHandler

            # Use the existing argument parser to create proper args
            cmd_line = ['action', 'list']
            mock_args = None
            try:
                if self.argument_parser:
                    mock_args = self.argument_parser.parse_args(cmd_line)
            except (SystemExit, Exception) as e:
                self.console.print(f"[red]Error parsing action list arguments: {e}[/red]")
                return True

            if not mock_args:
                self.console.print(f"[red]Failed to parse action list arguments[/red]")
                return True

            action_handler = ActionHandler(None, mock_args, self.console, None, None)
            action_handler.handle_action()
            return True

        except Exception as e:
            self.console.print(f"[red]Error listing actions: {e}[/red]")
            return True

    def _execute_action_show(self, action_name: str) -> bool:
        """Execute action show command."""
        try:
            # Import and use ActionHandler
            from handlers.action_handler import ActionHandler

            # Use the existing argument parser to create proper args
            cmd_line = ['action', 'show', action_name]
            mock_args = None
            try:
                if self.argument_parser:
                    mock_args = self.argument_parser.parse_args(cmd_line)
            except (SystemExit, Exception) as e:
                self.console.print(f"[red]Error parsing action show arguments: {e}[/red]")
                return True

            if not mock_args:
                self.console.print(f"[red]Failed to parse action show arguments[/red]")
                return True

            action_handler = ActionHandler(None, mock_args, self.console, None, None)
            action_handler.handle_action()
            return True

        except Exception as e:
            self.console.print(f"[red]Error showing action '{action_name}': {e}[/red]")
            return True

    def _execute_action_run(self, args: List[str], cluster_manager) -> bool:
        """Execute action run command."""
        import os

        # Set environment variable to indicate esterm context
        original_esterm_session = os.environ.get('ESTERM_SESSION')
        os.environ['ESTERM_SESSION'] = '1'

        try:
            # Import ActionHandler
            from handlers.action_handler import ActionHandler

            # Parse action run arguments using the real argument parser
            action_name = args[0]
            action_args = args[1:] if len(args) > 1 else []

            # Construct command line as it would appear to escmd.py for action command
            cmd_line = ['action', 'run', action_name] + action_args

            # Use the existing argument parser to create proper args
            mock_args = None
            try:
                if self.argument_parser:
                    mock_args = self.argument_parser.parse_args(cmd_line)
            except SystemExit:
                # Argument parser error (probably invalid arguments)
                self.console.print(f"[red]Invalid arguments for action '{action_name}'[/red]")
                return True
            except Exception as e:
                self.console.print(f"[red]Error parsing action arguments: {e}[/red]")
                return True

            if not mock_args:
                self.console.print(f"[red]Failed to parse action arguments[/red]")
                return True

            # Get cluster configuration
            es_client = cluster_manager.get_current_client()
            location_config = cluster_manager.config_manager.get_server_config_by_location(
                cluster_manager.current_location
            )
            config_file = cluster_manager.config_manager.config_file_path

            # Create ActionHandler with proper context
            action_handler = ActionHandler(
                es_client,
                mock_args,
                self.console,
                config_file,
                location_config,
                cluster_manager.current_location
            )

            action_handler.handle_action()
            return True

        except Exception as e:
            self.console.print(f"[red]Error executing action '{args[0] if args else 'unknown'}': {e}[/red]")
            # Show some helpful debug info in esterm debug mode
            if os.environ.get('ESTERM_DEBUG'):
                import traceback
                self.console.print(f"[red]Traceback:[/red]\n{traceback.format_exc()}")
            return True

        finally:
            # Restore original environment variable
            if original_esterm_session is None:
                os.environ.pop('ESTERM_SESSION', None)
            else:
                os.environ['ESTERM_SESSION'] = original_esterm_session

    def execute_escmd_command(self, command: str, args: List[str], cluster_manager) -> bool:
        """
        Execute ESCMD command using the cluster client and handlers.

        Args:
            command: Command name
            args: Command arguments
            cluster_manager: ClusterManager instance

        Returns:
            bool: True if command executed successfully
        """
        try:
            # Handle special commands that need custom processing FIRST
            # (these don't require ES connection)
            if self._handle_special_commands(command, args, cluster_manager):
                return True

            # Check if we have an active cluster connection
            es_client = cluster_manager.get_current_client()
            if not es_client:
                self.console.print("[red]No active cluster connection. Use 'connect' to connect to a cluster.[/red]")
                return False

            # Clear performance cache before every command execution in esterm
            # This ensures all data is real-time and never cached
            try:
                from performance import default_cache
                default_cache.invalidate()  # Clear all cached data for real-time results
            except ImportError:
                # Performance module not available, continue without clearing cache
                pass

            # Create mock args object for CommandHandler
            # This simulates the argparse.Namespace object expected by CommandHandler
            mock_args = self._create_mock_args(command, args)

            if not mock_args:
                self.console.print(f"[red]Invalid command or arguments: {command} {' '.join(args)}[/red]")
                return False

            # Get cluster configuration for CommandHandler
            location_config = cluster_manager.config_manager.get_server_config_by_location(
                cluster_manager.current_location
            )
            config_file = cluster_manager.config_manager.config_file_path

            # Create and execute command handler
            command_handler = CommandHandler(
                es_client,
                mock_args,
                self.console,
                config_file,
                location_config,
                cluster_manager.current_location
            )

            command_handler.execute()

            # After command execution, check if indices cache should be refreshed
            # This ensures real-time data display in esterm
            if self._should_refresh_indices_cache(command, args):
                es_client.refresh_indices_cache()

            return True

        except Exception as e:
            self.console.print(f"[red]Command execution error: {e}[/red]")
            return False

    def _handle_special_commands(self, command: str, args: List[str], cluster_manager) -> bool:
        """
        Handle special commands that need custom processing.

        Args:
            command: Command name
            args: Command arguments
            cluster_manager: ClusterManager instance

        Returns:
            bool: True if command was handled
        """
        from configuration_manager import ConfigurationManager

        # Handle configuration commands that don't need active cluster
        if command in ['locations', 'get-default', 'set-default', 'show-settings', 'set-username', 'cluster-groups']:
            try:
                # Get the correct state file path (escmd.json in script directory)
                script_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                state_file = os.path.join(script_directory, 'escmd.json')
                temp_config = ConfigurationManager(state_file_path=state_file)
                mock_args = self._create_mock_args(command, args)

                if command == 'locations':
                    clusters = temp_config.get_clusters()
                    self._display_locations(clusters)
                elif command == 'get-default':
                    default = temp_config.get_default_cluster()
                    self.console.print(f"Default cluster: [cyan]{default}[/cyan]")
                elif command == 'set-default':
                    if not args:
                        self.console.print(
                            "[red]Usage: set-default <cluster-name>[/red]"
                        )
                    else:
                        if not cluster_manager.config_manager:
                            cluster_manager.load_cluster_configuration()
                        if not cluster_manager.config_manager:
                            self.console.print(
                                "[red]Could not load cluster configuration.[/red]"
                            )
                        else:
                            cm = cluster_manager.config_manager
                            location = args[0]
                            server_config = cm.get_server_config(location)
                            if not server_config:
                                self.console.print(
                                    f"[red]Error: Location '{location}' not found "
                                    f"in configuration.[/red]"
                                )
                                self.console.print("[yellow]Available locations:[/yellow]")
                                for loc in sorted(
                                    cm.servers_dict.keys(), key=str.lower
                                ):
                                    self.console.print(f"  • {loc}")
                            else:
                                resolved = None
                                for name, cfg in cm.servers_dict.items():
                                    if cfg == server_config:
                                        resolved = name
                                        break
                                if not resolved:
                                    resolved = location
                                cm.set_default_cluster(resolved)
                                if not cluster_manager.connect_to_cluster(resolved):
                                    self.console.print(
                                        f"[yellow]Default saved as '{resolved}' but "
                                        f"reconnect failed. When reachable, run: "
                                        f"[bold]connect {resolved}[/bold][/yellow]"
                                    )
                elif command == 'show-settings':
                    # Handle show-settings command
                    from cli.special_commands import handle_show_settings
                    format_output = args[0] if args and args[0] in ['table', 'json'] else 'table'
                    handle_show_settings(temp_config, format_output)
                elif command == 'set-username':
                    # Handle set-username command
                    from cli.special_commands import handle_set_username
                    # Create mock args object similar to argparse.Namespace
                    mock_args = type('MockArgs', (), {})()
                    if args:
                        mock_args.username = args[0]
                        mock_args.show_current = '--show-current' in args
                    else:
                        mock_args.username = None
                        mock_args.show_current = False
                    handle_set_username(mock_args, temp_config)
                elif command == 'cluster-groups':
                    # Handle cluster-groups command
                    from cli.special_commands import handle_cluster_groups
                    format_output = args[0] if args and args[0] in ['table', 'json'] else 'table'
                    handle_cluster_groups(temp_config, format_output)

                return True
            except Exception as e:
                self.console.print(f"[red]Configuration command error: {e}[/red]")
                return True

        # Handle watch-health as special case
        if command == 'watch-health':
            # This would be handled by health_monitor
            return False

        return False

    def _create_mock_args(self, command: str, args: List[str]) -> Optional[Any]:
        """
        Create a mock argparse.Namespace object for CommandHandler.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            Namespace-like object or None if parsing fails
        """
        try:
            if not self.argument_parser:
                return None
            # Construct command line as it would appear to escmd.py
            cmd_line = [command] + args

            # Parse using the actual argument parser
            parsed_args = self.argument_parser.parse_args(cmd_line)
            return parsed_args

        except SystemExit:
            # Argument parser calls sys.exit on --help or error
            # Check if this was a help request (valid) vs actual error
            if args and '--help' in args:
                # This is a valid help request, create a minimal args object
                class MockArgs:
                    def __init__(self, command):
                        self.command = command
                        self.help = True
                return MockArgs(command)
            # Otherwise it's a parsing error
            return None
        except Exception:
            return None

    def _show_command_help(self, command: str):
        """
        Show help for a specific command.

        Args:
            command: Command name to show help for
        """
        try:
            # Try to get help from argument parser
            help_args = [command, '--help']
            self.argument_parser.parse_args(help_args)
        except SystemExit:
            # This is expected when --help is used
            pass
        except Exception:
            self.console.print(f"[red]No help available for command: {command}[/red]")

    def _display_locations(self, clusters: Dict[str, Any]):
        """
        Display available cluster locations.

        Args:
            clusters: Dictionary of cluster configurations
        """
        if not clusters:
            self.console.print("[yellow]No clusters configured[/yellow]")
            return

        self.console.print("\n[bold blue]🌐 Configured Clusters:[/bold blue]")

        # Create table for cluster information
        from rich.table import Table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Name", style="white", width=20)
        table.add_column("Host", style="dim", width=25)
        table.add_column("Port", style="dim", width=8)
        table.add_column("SSL", style="dim", width=6)

        for name, config in clusters.items():
            host = config.get('elastic_host', 'unknown')
            port = str(config.get('elastic_port', 'unknown'))
            ssl = "✓" if config.get('use_ssl', False) else "✗"

            table.add_row(name, host, port, ssl)

        self.console.print(table)

    def _clear_performance_cache(self):
        """Clear the performance cache manually."""
        try:
            # Import here to avoid circular imports
            from performance import default_cache
            cleared_count = default_cache.invalidate()
            self.console.print(f"[green]✓ Performance cache cleared ({cleared_count} items)[/green]")
        except Exception as e:
            self.console.print(f"[red]Error clearing cache: {e}[/red]")

    def _refresh_indices_cache(self, cluster_manager):
        """Refresh the indices cache for the current cluster."""
        try:
            es_client = cluster_manager.get_current_client()
            if not es_client:
                self.console.print("[red]No active cluster connection.[/red]")
                return

            # Refresh the indices cache
            es_client.refresh_indices_cache()
            self.console.print("[green]✓ Indices cache refreshed[/green]")
        except Exception as e:
            self.console.print(f"[red]Error refreshing indices cache: {e}[/red]")

    def _should_refresh_indices_cache(self, command: str, args: List[str]) -> bool:
        """
        Determine if indices cache should be refreshed after a command.

        Args:
            command: Command that was executed
            args: Command arguments

        Returns:
            bool: True if cache should be refreshed
        """
        # Commands that should always refresh indices cache for real-time data
        cache_refresh_commands = {
            'indices',           # Always refresh for indices commands
            'shards',            # Show current shard state
            'nodes',             # Node information can change
            'health',            # Cluster health changes frequently
            'storage',           # Disk usage changes
            'recovery',          # Recovery status changes
            'masters',           # Master node can change
            'current-master',    # Current master can change
            'allocation',        # Allocation settings/status
            'cluster-settings',  # Cluster settings
            'cluster-check',     # Comprehensive cluster status
            'dangling',          # Dangling indices can appear/disappear
            'datastreams',       # Datastream status can change
            'snapshots',         # Snapshot operations and status
            'ilm',               # ILM status changes
            'freeze',            # Index state change
            'unfreeze',          # Index state change
            'set-replicas',      # Index settings change
            'set',               # Cluster settings change
            'create',            # Creates indices/snapshots
            'create-index',      # Creates new indices
            'delete',            # Deletes indices/snapshots
            'restore',           # Creates indices from snapshots
            'rollover',          # Creates new indices
            'auto-rollover',     # Creates new indices
        }

        # Check if command should trigger refresh
        if command in cache_refresh_commands:
            return True

        # Special case: any command with --delete flag
        if '--delete' in args or '-d' in args:
            return True

        return False

    def get_command_suggestions(self, partial_command: str) -> List[str]:
        """
        Get command suggestions using fuzzy matching for better user experience.

        Args:
            partial_command: Partial or mistyped command string

        Returns:
            List[str]: List of matching command suggestions, sorted by relevance
        """
        all_commands = []

        # Collect all available commands
        all_commands.extend(self.builtin_commands)

        # Get ESCMD commands from argument parser
        try:
            if self.argument_parser:
                # Find the _SubParsersAction in the parser's actions
                for action in self.argument_parser._actions:
                    if hasattr(action, 'choices') and action.choices:
                        all_commands.extend(action.choices.keys())
                        break  # We found the subparser action, no need to continue
        except Exception:
            pass

        # Remove duplicates
        unique_commands = list(set(all_commands))
        partial_lower = partial_command.lower()

        # Categorize matches by relevance
        exact_matches = []
        prefix_matches = []
        contains_matches = []
        fuzzy_matches = []

        for cmd in unique_commands:
            cmd_lower = cmd.lower()
            if cmd_lower == partial_lower:
                exact_matches.append(cmd)
            elif cmd_lower.startswith(partial_lower):
                prefix_matches.append(cmd)
            elif partial_lower in cmd_lower:
                contains_matches.append(cmd)

        # Get fuzzy matches with higher cutoff for better quality
        fuzzy_candidates = difflib.get_close_matches(
            partial_lower,
            unique_commands,
            n=10,  # Get more candidates to filter
            cutoff=0.5  # Higher cutoff for better quality
        )

        # Add fuzzy matches that aren't already categorized
        for cmd in fuzzy_candidates:
            cmd_lower = cmd.lower()
            if (cmd not in exact_matches and
                cmd not in prefix_matches and
                cmd not in contains_matches):
                fuzzy_matches.append(cmd)

        # Combine results with proper prioritization
        suggestions = []

        # Add in order of relevance
        for match_list in [exact_matches, prefix_matches, contains_matches, fuzzy_matches]:
            for cmd in sorted(match_list):
                if cmd not in suggestions and len(suggestions) < 5:
                    suggestions.append(cmd)

        return suggestions

    def _get_themed_style(self, category: str, style_type: str, default: str = "") -> str:
        """
        Get a style from the theme manager with fallback.

        Args:
            category: Theme category (e.g., 'messages')
            style_type: Style type (e.g., 'error_style')
            default: Default style if theme manager unavailable

        Returns:
            str: Rich style string
        """
        if self.theme_manager:
            return self.theme_manager.get_style(category, style_type, default)
        return default

    def _format_themed_error_message(self, command: str, suggestions: List[str]) -> str:
        """
        Format error message with themed styling.

        Args:
            command: The invalid command
            suggestions: List of suggested commands

        Returns:
            str: Formatted error message with theme styling
        """
        if not suggestions:
            error_style = self._get_themed_style('messages', 'error_style', 'red')
            command_style = self._get_themed_style('messages', 'warning_style', 'yellow')
            help_style = self._get_themed_style('messages', 'info_style', 'cyan')

            return (f"[{error_style}]Unknown command[/{error_style}] "
                   f"[{command_style}]'{command}'[/{command_style}]. "
                   f"Type [{help_style}]'help'[/{help_style}] for available commands.")

        # Get theme styles
        error_style = self._get_themed_style('messages', 'error_style', 'red')
        command_style = self._get_themed_style('messages', 'warning_style', 'yellow')
        info_style = self._get_themed_style('messages', 'info_style', 'blue')
        success_style = self._get_themed_style('messages', 'success_style', 'green')

        # Format the first line with inline suggestions
        suggestion_list = ', '.join([f"[{success_style}]{cmd}[/{success_style}]" for cmd in suggestions[:3]])
        error_msg = (f"[{error_style}]Unknown command[/{error_style}] "
                    f"[{command_style}]'{command}'[/{command_style}]. "
                    f"[{info_style}]Did you mean:[/{info_style}] {suggestion_list}?")

        # Add detailed list
        error_msg += f"\n[{info_style}]Did you mean one of these commands?[/{info_style}]"
        for suggestion in suggestions:
            error_msg += f"\n  [{success_style}]{suggestion}[/{success_style}]"

        return error_msg

    def validate_command(self, command: str, args: List[str]) -> Tuple[bool, str]:
        """
        Validate command and arguments before execution.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not command:
            return False, "Empty command"

        # Built-in commands are always valid
        if self.is_builtin_command(command):
            return True, ""

        # For ESCMD commands, try to parse with argument parser
        try:
            # First check if the command exists in the parser
            if not self._command_exists_in_parser(command):
                suggestions = self.get_command_suggestions(command)
                return False, self._format_themed_error_message(command, suggestions)

            # If command exists, try to validate arguments
            mock_args = self._create_mock_args(command, args)
            if mock_args is None:
                return False, f"[red]Invalid arguments for command[/red] [yellow]'{command}'[/yellow]. Try [cyan]'{command} --help'[/cyan] for usage."
            return True, ""
        except Exception as e:
            return False, f"[red]Command validation error:[/red] {str(e)}"

    def _command_exists_in_parser(self, command: str) -> bool:
        """
        Check if a command exists in the argument parser.

        Args:
            command: Command name to check

        Returns:
            bool: True if command exists in parser
        """
        try:
            if not self.argument_parser:
                return False
            # Get the subparsers action
            for action in self.argument_parser._actions:
                if hasattr(action, '_name_parser_map'):
                    return command in action._name_parser_map
                elif hasattr(action, 'choices') and action.choices:
                    return command in action.choices
            return False
        except Exception:
            return False
