#!/usr/bin/env python3
"""
Help System Module for ESterm

Handles help display and command extraction logic including:
- Dynamic help generation from argument parser
- Command usage extraction
- Help formatting and display
- Command information management
"""

import os
import subprocess
import sys
from typing import Dict, Any, Optional

# Import Rich components
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class HelpSystem:
    """
    Manages help system functionality for ESterm.

    This class handles the extraction of command information from the
    argument parser and provides formatted help displays to users.
    """

    def __init__(self, console: Console, builtin_commands=None):
        """
        Initialize the help system.

        Args:
            console: Rich Console instance for output
            builtin_commands: Set of built-in command names (optional)
        """
        self.console = console
        self.parser = None
        self.commands_cache = {}  # Cache for parsed command information
        self._builtin_commands = builtin_commands

    def load_parser(self):
        """Load the argument parser for command extraction."""
        try:
            from cli.argument_parser import create_argument_parser

            self.parser = create_argument_parser()
            return True
        except ImportError:
            return False

    def show_help(self, command: Optional[str] = None):
        """
        Show help information.

        Args:
            command: Optional specific command to show help for
        """
        if command:
            # Check for special flags
            if command in ["--advanced", "-a"]:
                self.show_advanced_help_index()
            elif command in [
                "connect",
                "status",
                "watch",
                "help",
                "clear",
                "cache-clear",
                "cache-refresh",
                "exit",
                "quit",
                "disconnect",
                "switch",
                "actions",
            ]:
                # Built-in esterm commands - show basic help
                self.show_builtin_command_help(command)
            else:
                # Try advanced help first for elasticsearch commands
                if not self.show_advanced_command_help(command):
                    # Fallback to basic help
                    self.show_command_help(command)
        else:
            self.show_general_help()

    def show_general_help(self):
        """Show comprehensive help information extracted from argument parser."""
        help_text = Text()

        # Built-in terminal commands - dynamically generated
        help_text.append("Built-in Commands:\n", style="bold white")

        # Define command descriptions for built-in commands
        builtin_descriptions = {
            "help": "Show this help",
            "?": "Show this help (alias)",
            "connect": "Connect to a cluster",
            "status": "Show connection status",
            "info": "Show connection status (alias)",
            "watch": 'Monitor cluster health (e.g., "watch health [interval]")',
            "cache-clear": "Clear performance cache",
            "cache-refresh": "Refresh indices cache",
            "disconnect": "Disconnect from current cluster",
            "switch": "Show cluster selection menu",
            "theme": "Change terminal theme or show theme menu",
            "actions": "Execute predefined action sequences (list/show/run)",
            "clear": "Clear screen",
            "cls": "Clear screen (alias)",
            "exit": "Exit terminal",
            "quit": "Exit terminal (alias)",
            "q": "Exit terminal (alias)",
        }

        # Get built-in commands from the passed parameter or use fallback
        builtin_commands = self._builtin_commands
        if not builtin_commands:
            # Fallback to a reasonable set if not available
            builtin_commands = {
                "help",
                "?",
                "connect",
                "status",
                "info",
                "watch",
                "actions",
                "cache-clear",
                "cache-refresh",
                "disconnect",
                "switch",
                "theme",
                "clear",
                "cls",
                "exit",
                "quit",
                "q",
            }

        # Sort and display built-in commands
        primary_commands = [
            "help",
            "connect",
            "status",
            "watch",
            "actions",
            "theme",
            "switch",
            "cache-clear",
            "cache-refresh",
            "disconnect",
            "clear",
            "exit",
        ]

        for cmd in primary_commands:
            if cmd in builtin_commands:
                desc = builtin_descriptions.get(cmd, f"{cmd.title()} command")
                if cmd == "connect":
                    help_text.append(f"  {cmd:<15} - {desc} (<name>)\n", style="white")
                elif cmd == "watch":
                    help_text.append(f"  {cmd:<15} - {desc}\n", style="white")
                elif cmd in ["clear", "exit"]:
                    # Show aliases for these commands
                    aliases = []
                    if cmd == "clear" and "cls" in builtin_commands:
                        aliases.append("cls")
                    elif cmd == "exit":
                        if "quit" in builtin_commands:
                            aliases.append("quit")
                        if "q" in builtin_commands:
                            aliases.append("q")

                    if aliases:
                        help_text.append(
                            f"  {cmd}/{'/'.join(aliases):<15} - {desc}\n", style="white"
                        )
                    else:
                        help_text.append(f"  {cmd:<15} - {desc}\n", style="white")
                else:
                    help_text.append(f"  {cmd:<15} - {desc}\n", style="white")

        help_text.append("  \n", style="white")
        help_text.append(
            "Note: ESterm shows real-time data with intelligent caching\n",
            style="dim green",
        )

        # Dynamic ESCMD commands
        help_text.append("\nESCMD Commands:\n", style="bold white")

        if not self.parser and not self.load_parser():
            # Fallback if parser can't be loaded
            help_text.append("  [Unable to load dynamic command list]\n", style="red")
            help_text.append(
                "  Try: indices, shards, nodes, health, cluster\n", style="white"
            )
        else:
            # Extract all subcommands and their help text
            commands_info = self.extract_commands_from_parser()

            # Sort commands alphabetically for better presentation
            for command_name in sorted(commands_info.keys()):
                command_info = commands_info[command_name]
                help_desc = command_info.get("help", "No description available")

                # Format command with basic syntax
                command_line = f"  {command_name:<15} - {help_desc}\n"
                help_text.append(command_line, style="white")

                # Show usage if available
                usage = command_info.get("usage", "")
                if usage:
                    help_text.append(
                        f"    Usage: {command_name} {usage}\n", style="dim white"
                    )

        # Common options
        help_text.append("\nCommon Options:\n", style="bold white")
        help_text.append(
            "  --format FORMAT - Output format (json, table, data)\n", style="white"
        )
        help_text.append(
            "  --limit N       - Limit results to N items\n", style="white"
        )
        help_text.append(
            "  --regex PATTERN - Filter with regex pattern\n", style="white"
        )
        help_text.append("  --size          - Sort by size\n", style="white")
        help_text.append("  --server HOST   - Filter by server/host\n", style="white")

        # Examples
        help_text.append("\nAdvanced Help:\n", style="bold cyan")
        help_text.append(
            "  help <command>             # Get detailed help for any command\n",
            style="dim white",
        )
        help_text.append(
            "  help --advanced            # Show advanced help index\n",
            style="dim white",
        )
        help_text.append(
            "  help indices               # Show comprehensive indices help\n",
            style="dim white",
        )
        help_text.append(
            "  help health                # Show health command examples\n",
            style="dim white",
        )
        help_text.append("\nExamples:\n", style="bold white")
        help_text.append(
            "  indices                    # Show all indices\n", style="dim white"
        )
        help_text.append(
            "  watch health               # Monitor health every 10s\n",
            style="dim white",
        )
        help_text.append(
            "  watch health 5             # Monitor health every 5s\n",
            style="dim white",
        )
        help_text.append(
            "  indices log-*              # Show indices matching pattern\n",
            style="dim white",
        )
        help_text.append(
            "  shards geoip               # Show shards matching 'geoip'\n",
            style="dim white",
        )
        help_text.append(
            "  nodes --format json        # Show nodes in JSON format\n",
            style="dim white",
        )
        help_text.append(
            "  health --format json       # Cluster health in JSON\n", style="dim white"
        )
        help_text.append(
            "  allocation                 # Show allocation settings\n",
            style="dim white",
        )

        panel = Panel(
            help_text,
            title="[bold blue]ESterm Help[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_advanced_help_index(self):
        """Show the advanced help index from escmd.py."""
        try:
            # Get the script directory (where escmd.py is located)
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            escmd_path = os.path.join(script_dir, "escmd.py")

            if not os.path.exists(escmd_path):
                self.console.print(
                    "[red]Advanced help not available: escmd.py not found[/red]"
                )
                return

            # Run escmd.py --help to get the advanced help index
            result = subprocess.run(
                [sys.executable, escmd_path, "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=script_dir,
            )

            if result.returncode == 0:
                self.console.print("[bold blue]Advanced Help Index[/bold blue]")
                self.console.print()
                self.console.print(result.stdout)
                self.console.print()
                self.console.print(
                    "[dim]💡 Use 'help <command>' for detailed help on specific commands[/dim]"
                )
            else:
                self.console.print("[red]Error accessing advanced help[/red]")

        except Exception as e:
            self.console.print(f"[red]Error showing advanced help: {e}[/red]")

    def show_advanced_command_help(self, command: str) -> bool:
        """
        Show advanced help for a command using escmd.py.

        Args:
            command: Command to show help for

        Returns:
            bool: True if advanced help was shown, False if not available
        """
        try:
            # Get the script directory (where escmd.py is located)
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            escmd_path = os.path.join(script_dir, "escmd.py")

            if not os.path.exists(escmd_path):
                return False

            # Try to get advanced help for the command
            result = subprocess.run(
                [sys.executable, escmd_path, "help", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=script_dir,
            )

            if result.returncode == 0 and result.stdout.strip():
                # Success - show the advanced help
                self.console.print(result.stdout)
                self.console.print()
                self.console.print(
                    "[dim]💡 This is advanced help from escmd.py. Use 'help --advanced' for the full command index.[/dim]"
                )
                return True
            else:
                # Command not found in advanced help
                return False

        except Exception:
            return False

    def show_builtin_command_help(self, command: str):
        """
        Show help for built-in esterm commands.

        Args:
            command: Built-in command to show help for
        """
        builtin_help = {
            "connect": {
                "description": "Connect to an Elasticsearch cluster",
                "usage": "connect [cluster-name]",
                "examples": [
                    "connect                # Show cluster selection menu",
                    "connect production     # Connect to production cluster",
                    "connect dev            # Connect to dev cluster",
                ],
            },
            "status": {
                "description": "Show current connection and cluster status",
                "usage": "status",
                "examples": ["status                  # Show connection status"],
            },
            "watch": {
                "description": "Monitor cluster health in real-time",
                "usage": "watch health [interval]",
                "examples": [
                    "watch health           # Monitor every 10 seconds",
                    "watch health 5         # Monitor every 5 seconds",
                ],
            },
            "disconnect": {
                "description": "Disconnect from current cluster",
                "usage": "disconnect",
                "examples": ["disconnect             # Disconnect from cluster"],
            },
            "switch": {
                "description": "Show cluster selection menu",
                "usage": "switch",
                "examples": ["switch                 # Show cluster menu"],
            },
            "clear": {
                "description": "Clear the terminal screen",
                "usage": "clear",
                "examples": ["clear                  # Clear screen"],
            },
            "cache-clear": {
                "description": "Clear performance cache",
                "usage": "cache-clear",
                "examples": ["cache-clear            # Clear cache"],
            },
            "cache-refresh": {
                "description": "Refresh indices cache",
                "usage": "cache-refresh",
                "examples": ["cache-refresh          # Refresh indices cache"],
            },
            "help": {
                "description": "Show help information",
                "usage": "help [command|--advanced]",
                "examples": [
                    "help                   # Show general help",
                    "help indices           # Show help for indices command",
                    "help --advanced        # Show advanced help index",
                ],
            },
            "exit": {
                "description": "Exit esterm",
                "usage": "exit",
                "examples": ["exit                   # Exit esterm"],
            },
            "quit": {
                "description": "Exit esterm",
                "usage": "quit",
                "examples": ["quit                   # Exit esterm"],
            },
            "action": {
                "description": "Execute predefined action sequences",
                "usage": "action <list|show|run> [arguments]",
                "examples": [
                    "actions list            # List all available actions",
                    "actions show add-host   # Show details for add-host action",
                    "actions run add-host --param-host server01 # Execute action",
                    "actions run add-host --param-host server01 --dry-run # Test action",
                    "actions run add-host --param-host server01 --quiet # Quiet execution",
                ],
            },
        }

        if command in builtin_help:
            cmd_info = builtin_help[command]
            help_text = Text()
            help_text.append(f"{cmd_info['description']}\n\n", style="bold white")
            help_text.append("Usage:\n", style="bold yellow")
            help_text.append(f"  {cmd_info['usage']}\n\n", style="white")
            help_text.append("Examples:\n", style="bold green")
            for example in cmd_info["examples"]:
                help_text.append(f"  {example}\n", style="dim white")

            panel = Panel(
                help_text,
                title=f"📖 Help: {command}",
                border_style="blue",
                padding=(1, 2),
            )
            self.console.print(panel)
        else:
            self.console.print(
                f"[red]No help available for built-in command: {command}[/red]"
            )

    def show_command_help(self, command: str):
        """
        Show help for a specific command.

        Args:
            command: Command name to show help for
        """
        try:
            if not self.parser:
                if not self.load_parser():
                    self.console.print(
                        f"[red]Unable to load help for command: {command}[/red]"
                    )
                    return

            # Try to get help from argument parser
            help_args = [command, "--help"]
            self.parser.parse_args(help_args)
        except SystemExit:
            # This is expected when --help is used - the parser prints help and exits
            pass
        except Exception:
            self.console.print(f"[red]No help available for command: {command}[/red]")

    def extract_commands_from_parser(self) -> Dict[str, Any]:
        """Extract command information from argument parser using built-in help."""
        if not self.parser:
            return {}

        # Return cached results if available
        if self.commands_cache:
            return self.commands_cache

        commands_info = {}

        try:
            # Get the subparsers action
            subparsers_action = None
            for action in self.parser._actions:
                if hasattr(action, "choices") and hasattr(action, "_choices_actions"):
                    subparsers_action = action
                    break

            if subparsers_action:
                # Create mapping from command names to help text using _choices_actions
                help_mapping = {}
                for choice_action in subparsers_action._choices_actions:
                    if hasattr(choice_action, "dest") and hasattr(
                        choice_action, "help"
                    ):
                        help_mapping[choice_action.dest] = choice_action.help

                # Get commands and their help text
                for command_name, subparser in subparsers_action.choices.items():
                    if command_name == "help":  # Skip the help command itself
                        continue

                    # Get help text from the mapping
                    help_text = help_mapping.get(
                        command_name,
                        f"{command_name.replace('-', ' ').title()} command",
                    )

                    commands_info[command_name] = {
                        "help": help_text,
                        "usage": self.get_command_usage(subparser),
                    }

                    # Handle subcommands (like allocation subcommands)
                    for sub_action in subparser._actions:
                        if hasattr(sub_action, "choices") and hasattr(
                            sub_action, "_choices_actions"
                        ):
                            sub_help_mapping = {}
                            for sub_choice_action in sub_action._choices_actions:
                                if hasattr(sub_choice_action, "dest") and hasattr(
                                    sub_choice_action, "help"
                                ):
                                    sub_help_mapping[sub_choice_action.dest] = (
                                        sub_choice_action.help
                                    )

                            for sub_command_name in sub_action.choices.keys():
                                full_command = f"{command_name} {sub_command_name}"
                                sub_help = sub_help_mapping.get(
                                    sub_command_name,
                                    f"{sub_command_name.title()} {command_name}",
                                )
                                commands_info[full_command] = {
                                    "help": sub_help,
                                    "usage": "",
                                }

            # Cache the results
            self.commands_cache = commands_info

        except Exception:
            # If extraction fails, return empty dict - fallback will handle it
            pass

        return commands_info

    def get_command_usage(self, subparser) -> str:
        """
        Get simplified usage string for a command.

        Args:
            subparser: Argument subparser for the command

        Returns:
            str: Usage string for the command
        """
        try:
            # Get positional arguments
            positional = []
            optional = []

            for action in subparser._actions:
                if action.dest in ["help"]:
                    continue

                if action.option_strings:
                    # Optional argument
                    if action.dest in ["format", "limit", "regex", "server", "size"]:
                        optional.append(f"[--{action.dest}]")
                else:
                    # Positional argument
                    if action.nargs == "?":
                        positional.append(f"[{action.dest}]")
                    else:
                        positional.append(f"<{action.dest}>")

            usage_parts = positional + optional[:3]  # Show max 3 optional args
            if len(optional) > 3:
                usage_parts.append("...")

            return " ".join(usage_parts)
        except:
            return ""

    def get_command_list(self) -> list:
        """
        Get list of all available commands.

        Returns:
            list: List of command names
        """
        if not self.parser and not self.load_parser():
            return []

        commands_info = self.extract_commands_from_parser()
        return list(commands_info.keys())

    def get_command_info(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific command.

        Args:
            command: Command name

        Returns:
            dict or None: Command information or None if not found
        """
        commands_info = self.extract_commands_from_parser()
        return commands_info.get(command)

    def search_commands(self, query: str) -> list:
        """
        Search for commands matching a query.

        Args:
            query: Search query

        Returns:
            list: List of matching command names
        """
        commands_info = self.extract_commands_from_parser()
        matching_commands = []

        query_lower = query.lower()
        for command_name, command_info in commands_info.items():
            # Search in command name
            if query_lower in command_name.lower():
                matching_commands.append(command_name)
            # Search in help text
            elif query_lower in command_info.get("help", "").lower():
                matching_commands.append(command_name)

        return sorted(matching_commands)

    def clear_cache(self):
        """Clear the commands cache to force re-extraction."""
        self.commands_cache = {}

    def show_command_summary(self):
        """Show a brief summary of available commands by category."""
        help_text = Text()
        help_text.append("ESterm Command Categories:\n\n", style="bold blue")

        # Define command categories
        categories = {
            "Cluster Information": ["health", "nodes", "cluster", "cluster-settings"],
            "Index Management": [
                "indices",
                "index",
                "index-settings",
                "mappings",
                "templates",
            ],
            "Data Operations": ["search", "count", "cat", "shards"],
            "Administration": ["allocation", "recovery", "snapshots", "tasks"],
            "Lifecycle": ["ilm", "slm"],
            "Configuration": [
                "locations",
                "get-default",
                "set-default",
                "cluster-groups",
            ],
        }

        commands_info = self.extract_commands_from_parser()

        for category, commands in categories.items():
            help_text.append(f"{category}:\n", style="bold yellow")
            for command in commands:
                if command in commands_info:
                    help_desc = commands_info[command].get("help", "No description")
                    # Truncate long descriptions
                    if len(help_desc) > 50:
                        help_desc = help_desc[:47] + "..."
                    help_text.append(f"  {command:<15} - {help_desc}\n", style="white")
            help_text.append("\n")

        help_text.append("Use 'help <command>' for detailed information\n", style="dim")

        panel = Panel(
            help_text,
            title="[bold blue]Command Summary[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
        self.console.print(panel)
