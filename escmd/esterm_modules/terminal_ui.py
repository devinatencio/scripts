#!/usr/bin/env python3
"""
Terminal UI Module for ESterm

Handles all user interface and display logic including:
- Banner and welcome messages
- Status displays and prompts
- Help system integration
- User input handling with history
- Visual feedback and formatting
- Error and success message display
"""

import os
import readline
import atexit
from typing import Optional, Dict, Any, List

# Import Rich components
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt


class TerminalUI:
    """
    Manages all user interface elements for ESterm.

    This class handles the visual presentation layer, including banners,
    status displays, prompts, and user interaction elements.
    """

    def __init__(self, console: Console):
        """
        Initialize the terminal UI.

        Args:
            console: Rich Console instance for output
        """
        self.console = console
        self.history_file = os.path.expanduser("~/.esterm_history")
        self.setup_readline()

    def setup_readline(self):
        """Setup readline for command history and completion."""
        try:
            readline.read_history_file(self.history_file)
            readline.set_history_length(1000)
            atexit.register(readline.write_history_file, self.history_file)
        except FileNotFoundError:
            # History file doesn't exist yet, will be created on exit
            pass
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not setup command history: {e}[/yellow]")

    def show_banner(self, version: str, date: str):
        """
        Display the welcome banner.

        Args:
            version: ESterm version string
            date: Version date string
        """
        banner_text = Text()
        banner_text.append("ESterm - Interactive Elasticsearch Terminal\n", style="bold blue")
        banner_text.append(f"Version {version} ({date})\n\n", style="dim")
        banner_text.append("Enhanced with Rich formatting and interactive cluster selection\n", style="green")
        banner_text.append("Type 'help' for commands or 'connect' to select a cluster\n", style="dim")
        banner_text.append("[Real-time mode: Intelligent caching with auto-refresh]", style="dim green")

        panel = Panel.fit(
            banner_text,
            title="🔍 Welcome to ESterm",
            border_style="blue",
            padding=(1, 2)
        )

        self.console.print(panel)

    def show_help(self):
        """Show comprehensive help information extracted from argument parser."""
        help_text = Text()
        help_text.append("ESterm Interactive Help\n\n", style="bold blue")

        # Built-in terminal commands
        help_text.append("Built-in Terminal Commands:\n", style="bold yellow")
        help_text.append("  help [command]     Show help (optionally for specific command)\n", style="cyan")
        help_text.append("  status             Show connection and cluster status\n", style="cyan")
        help_text.append("  connect [cluster]  Connect to cluster (shows menu if no cluster specified)\n", style="cyan")
        help_text.append("  switch             Show cluster selection menu\n", style="cyan")
        help_text.append("  disconnect         Disconnect from current cluster\n", style="cyan")
        help_text.append("  clear              Clear the screen\n", style="cyan")
        help_text.append("  cache-clear        Clear performance cache\n", style="cyan")
        help_text.append("  exit, quit, q      Exit ESterm\n\n", style="cyan")

        # ESCMD commands
        help_text.append("Elasticsearch Commands:\n", style="bold green")
        help_text.append("  health             Show cluster health\n", style="dim")
        help_text.append("  nodes              List cluster nodes\n", style="dim")
        help_text.append("  indices [pattern]  List indices (optionally filtered)\n", style="dim")
        help_text.append("  cluster-settings   Show cluster settings\n", style="dim")
        help_text.append("  set                Set cluster settings with dot notation\n", style="dim")
        help_text.append("  allocation         Manage shard allocation\n", style="dim")
        help_text.append("  recovery           Show recovery operations\n", style="dim")
        help_text.append("  repositories       List snapshot repositories\n", style="dim")
        help_text.append("  snapshots          Manage snapshots\n", style="dim")
        help_text.append("  ilm                Index Lifecycle Management\n", style="dim")
        help_text.append("  ... and many more!\n\n", style="dim")

        help_text.append("Usage Tips:\n", style="bold magenta")
        help_text.append("• Use 'help <command>' for detailed command help\n", style="dim")
        help_text.append("• Commands support --help flag for argument details\n", style="dim")
        help_text.append("• Use TAB for command history navigation\n", style="dim")
        help_text.append("• All ESCMD commands work in interactive mode\n", style="dim")

        panel = Panel(
            help_text,
            title="📖 ESterm Help",
            border_style="blue",
            padding=(1, 2)
        )

        self.console.print(panel)

    def show_status(self, cluster_manager):
        """
        Show current connection status and cluster information.

        Args:
            cluster_manager: ClusterManager instance
        """
        status_text = Text()
        status_text.append("ESterm Status\n\n", style="bold blue")

        # Connection status
        if cluster_manager.is_connected():
            cluster_info = cluster_manager.get_cluster_info()
            if cluster_info:
                status_text.append("Connection: ", style="bold")
                status_text.append("Connected ✓\n", style="green")

                status_text.append("Cluster: ", style="bold")
                status_text.append(f"{cluster_info['name']}\n", style="cyan")

                status_text.append("Status: ", style="bold")
                status_color = self._get_status_color(cluster_info['status'])
                status_text.append(f"{cluster_info['status'].upper()}\n", style=status_color)

                status_text.append("Nodes: ", style="bold")
                status_text.append(f"{cluster_info['nodes']} total, {cluster_info['data_nodes']} data\n", style="white")

                status_text.append("Shards: ", style="bold")
                status_text.append(f"{cluster_info['active_shards']} active\n", style="white")

                if 'cluster_name' in cluster_info:
                    status_text.append("Cluster Name: ", style="bold")
                    status_text.append(f"{cluster_info['cluster_name']}\n", style="dim")
            else:
                status_text.append("Connection: ", style="bold")
                status_text.append("Connected but unable to fetch info\n", style="yellow")
        else:
            status_text.append("Connection: ", style="bold")
            status_text.append("Not connected ✗\n", style="red")
            status_text.append("\nUse 'connect' to connect to a cluster\n", style="dim")

        # Available clusters
        clusters = cluster_manager.get_available_clusters()
        if clusters:
            status_text.append(f"\nAvailable Clusters: {len(clusters)}\n", style="bold")
            for i, cluster in enumerate(clusters[:5], 1):  # Show first 5
                is_current = cluster == cluster_manager.get_current_cluster()
                prefix = "→ " if is_current else "  "
                style = "green" if is_current else "dim"
                status_text.append(f"{prefix}{cluster}\n", style=style)

            if len(clusters) > 5:
                status_text.append(f"  ... and {len(clusters) - 5} more\n", style="dim")

        panel = Panel(
            status_text,
            title="📊 Status Information",
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print(panel)

    def get_prompt(self, cluster_manager) -> str:
        """
        Get the command prompt string.

        Args:
            cluster_manager: ClusterManager instance

        Returns:
            str: Formatted prompt string
        """
        if cluster_manager and cluster_manager.is_connected():
            cluster_name = cluster_manager.get_current_cluster()
            cluster_info = cluster_manager.get_cluster_info()

            if cluster_info:
                status = cluster_info.get('status', 'unknown')
                status_color = self._get_status_color(status)
                return f"[bold blue]esterm[/bold blue]([{status_color}]{cluster_name}[/{status_color}])> "
            else:
                return f"[bold blue]esterm[/bold blue]([yellow]{cluster_name}[/yellow])> "
        else:
            return "[bold blue]esterm[/bold blue]([red]disconnected[/red])> "

    def get_user_input_with_history(self, prompt_text: str) -> Optional[str]:
        """
        Get user input with proper readline history support.

        Args:
            prompt_text: Prompt text to display

        Returns:
            str or None: User input or None if interrupted
        """
        try:
            # Convert Rich markup to plain text for input prompt
            plain_prompt = self._strip_rich_markup(prompt_text)
            return input(plain_prompt)
        except (KeyboardInterrupt, EOFError):
            return None
        except Exception:
            raise

    def show_error(self, message: str, title: str = "Error"):
        """
        Display an error message in a formatted panel.

        Args:
            message: Error message to display
            title: Panel title
        """
        error_panel = Panel.fit(
            f"[red]{message}[/red]",
            title=f"🔶  {title}",
            border_style="red",
            padding=(1, 2)
        )
        self.console.print(error_panel)

    def show_success(self, message: str, title: str = "Success"):
        """
        Display a success message in a formatted panel.

        Args:
            message: Success message to display
            title: Panel title
        """
        success_panel = Panel.fit(
            f"[green]{message}[/green]",
            title=f"✓ {title}",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(success_panel)

    def show_warning(self, message: str, title: str = "Warning"):
        """
        Display a warning message in a formatted panel.

        Args:
            message: Warning message to display
            title: Panel title
        """
        warning_panel = Panel.fit(
            f"[yellow]{message}[/yellow]",
            title=f"🔶  {title}",
            border_style="yellow",
            padding=(1, 2)
        )
        self.console.print(warning_panel)

    def show_info(self, message: str, title: str = "Information"):
        """
        Display an informational message in a formatted panel.

        Args:
            message: Info message to display
            title: Panel title
        """
        info_panel = Panel.fit(
            f"[blue]{message}[/blue]",
            title=f"🔵  {title}",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(info_panel)

    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Show a confirmation prompt to the user.

        Args:
            message: Confirmation message
            default: Default response if user just presses Enter

        Returns:
            bool: True if user confirmed, False otherwise
        """
        try:
            default_text = "Y/n" if default else "y/N"
            response = Prompt.ask(f"[yellow]{message}[/yellow] [{default_text}]", default="")

            if not response:
                return default

            return response.lower() in ('y', 'yes', 'true', '1')
        except KeyboardInterrupt:
            return False

    def show_progress(self, message: str):
        """
        Show a progress/working message.

        Args:
            message: Progress message to display
        """
        self.console.print(f"[blue]⏳ {message}...[/blue]")

    def clear_screen(self):
        """Clear the terminal screen."""
        self.console.clear()

    def print_separator(self, char: str = "─", width: Optional[int] = None):
        """
        Print a separator line.

        Args:
            char: Character to use for separator
            width: Width of separator (None for full width)
        """
        if width is None:
            width = self.console.size.width

        self.console.print(char * width, style="dim")

    def _get_status_color(self, status: str) -> str:
        """
        Get appropriate color for cluster status.

        Args:
            status: Cluster status string

        Returns:
            str: Rich color string
        """
        status_colors = {
            'green': 'green',
            'yellow': 'yellow',
            'red': 'red',
            'unknown': 'dim',
            'error': 'red'
        }
        return status_colors.get(status.lower(), 'white')

    def _strip_rich_markup(self, text: str) -> str:
        """
        Strip Rich markup from text for plain display.

        Args:
            text: Text with Rich markup

        Returns:
            str: Plain text without markup
        """
        # Simple regex-based removal of Rich markup
        import re
        # Remove [style] and [/style] tags
        clean_text = re.sub(r'\[/?[^\]]*\]', '', text)
        return clean_text

    def format_table(self, data: List[Dict[str, Any]], columns: List[str],
                    title: Optional[str] = None) -> Table:
        """
        Create a formatted Rich table from data.

        Args:
            data: List of dictionaries containing row data
            columns: List of column names
            title: Optional table title

        Returns:
            Table: Formatted Rich table
        """
        table = Table(show_header=True, header_style="bold cyan", title=title)

        # Add columns
        for col in columns:
            table.add_column(col, style="white")

        # Add rows
        for row in data:
            values = [str(row.get(col, '')) for col in columns]
            table.add_row(*values)

        return table

    def show_spinner(self, message: str = "Working"):
        """
        Context manager for showing a spinner during operations.

        Args:
            message: Message to show with spinner

        Returns:
            Context manager for spinner
        """
        from rich.spinner import Spinner
        from rich.live import Live

        spinner = Spinner("dots", text=f"[blue]{message}...[/blue]")
        return Live(spinner, console=self.console, refresh_per_second=12.5)
