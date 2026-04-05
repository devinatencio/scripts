#!/usr/bin/env python3
"""
Themed Terminal UI Module for ESterm

Enhanced version of terminal_ui.py that uses the ESterm theme system.
This replaces the original terminal_ui.py with themed styling capabilities
while maintaining the same interface and functionality.
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

# Import ESterm theme manager
from .theme_manager import EstermThemeManager


class ThemedTerminalUI:
    """
    Manages all user interface elements for ESterm with theme support.

    This class handles the visual presentation layer with theming, including banners,
    status displays, prompts, and user interaction elements.
    """

    def __init__(self, console: Console):
        """
        Initialize the themed terminal UI.

        Args:
            console: Rich Console instance for output
        """
        self.console = console
        self.theme_manager = EstermThemeManager(console)
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
            self.console.print(f"[{self.theme_manager.get_style('messages', 'warning_style')}]Warning: Could not setup command history: {e}[/{self.theme_manager.get_style('messages', 'warning_style')}]")

    def show_banner(self, version: str, date: str):
        """
        Display the welcome banner with theme styling.

        Args:
            version: ESterm version string
            date: Version date string
        """
        # Check if banner should be shown
        if not self.theme_manager.should_show_banner():
            return
        banner_text = Text()

        # Get themed styles
        title_style = self.theme_manager.get_style('banner', 'title_style')
        subtitle_style = self.theme_manager.get_style('banner', 'subtitle_style')
        version_style = self.theme_manager.get_style('banner', 'version_style')
        welcome_style = self.theme_manager.get_style('banner', 'welcome_style')
        border_style = self.theme_manager.get_style('banner', 'border_style')

        banner_text.append("ESterm - Interactive Elasticsearch Terminal\n", style=title_style)
        banner_text.append(f"Version {version} ({date})\n\n", style=subtitle_style)
        banner_text.append("Enhanced with Rich formatting and interactive cluster selection\n", style=welcome_style)
        banner_text.append("Type 'help' for commands or 'connect' to select a cluster\n", style=subtitle_style)

        # Show theme info if configured to do so
        if self.theme_manager.should_show_theme_in_banner():
            theme_info = self.theme_manager.get_theme_info()
            banner_text.append(f"[Current theme: {theme_info['name']} ({self.theme_manager.get_current_theme()})]", style=version_style)

        panel = Panel.fit(
            banner_text,
            title="🔍 Welcome to ESterm",
            border_style=border_style,
            padding=(1, 2)
        )

        self.console.print(panel)

    def show_help(self):
        """Show comprehensive help information with theme styling."""
        help_text = Text()

        # Get themed styles
        title_style = self.theme_manager.get_style('help', 'title_style')
        section_style = self.theme_manager.get_style('help', 'section_header_style')
        command_style = self.theme_manager.get_style('help', 'command_style')
        desc_style = self.theme_manager.get_style('help', 'description_style')
        example_style = self.theme_manager.get_style('help', 'example_style')

        help_text.append("ESterm Interactive Help\n\n", style=title_style)

        # Built-in terminal commands
        help_text.append("Built-in Terminal Commands:\n", style=section_style)
        help_text.append("  help [command]     ", style=command_style)
        help_text.append("Show help (optionally for specific command)\n", style=desc_style)
        help_text.append("  status             ", style=command_style)
        help_text.append("Show connection and cluster status\n", style=desc_style)
        help_text.append("  connect [cluster]  ", style=command_style)
        help_text.append("Connect to cluster (shows menu if no cluster specified)\n", style=desc_style)
        help_text.append("  switch             ", style=command_style)
        help_text.append("Show cluster selection menu\n", style=desc_style)
        help_text.append("  disconnect         ", style=command_style)
        help_text.append("Disconnect from current cluster\n", style=desc_style)
        help_text.append("  theme [name]       ", style=command_style)
        help_text.append("Change ESterm theme (list themes if no name given)\n", style=desc_style)
        help_text.append("  clear              ", style=command_style)
        help_text.append("Clear the screen\n", style=desc_style)
        help_text.append("  cache-clear        ", style=command_style)
        help_text.append("Clear performance cache\n", style=desc_style)
        help_text.append("  exit, quit, q      ", style=command_style)
        help_text.append("Exit ESterm\n\n", style=desc_style)

        # ESCMD commands
        help_text.append("Elasticsearch Commands:\n", style=section_style)
        help_text.append("  health             ", style=command_style)
        help_text.append("Show cluster health\n", style=desc_style)
        help_text.append("  nodes              ", style=command_style)
        help_text.append("List cluster nodes\n", style=desc_style)
        help_text.append("  indices [pattern]  ", style=command_style)
        help_text.append("List indices (optionally filtered)\n", style=desc_style)
        help_text.append("  cluster-settings   ", style=command_style)
        help_text.append("Show cluster settings\n", style=desc_style)
        help_text.append("  set                ", style=command_style)
        help_text.append("Set cluster settings with dot notation\n", style=desc_style)
        help_text.append("  allocation         ", style=command_style)
        help_text.append("Manage shard allocation\n", style=desc_style)
        help_text.append("  recovery           ", style=command_style)
        help_text.append("Show recovery operations\n", style=desc_style)
        help_text.append("  snapshots          ", style=command_style)
        help_text.append("Manage snapshots\n", style=desc_style)
        help_text.append("  ilm                ", style=command_style)
        help_text.append("Index Lifecycle Management\n", style=desc_style)
        help_text.append("  ... and many more!\n\n", style=desc_style)

        help_text.append("Theme Commands:\n", style=section_style)
        help_text.append("  theme              ", style=command_style)
        help_text.append("List available themes\n", style=desc_style)
        help_text.append("  theme <name>       ", style=command_style)
        help_text.append("Switch to specified theme\n", style=desc_style)
        help_text.append("  theme preview <name> ", style=command_style)
        help_text.append("Preview a theme without switching\n\n", style=desc_style)

        help_text.append("Usage Tips:\n", style=section_style)
        help_text.append("• Use 'help <command>' for detailed command help\n", style=example_style)
        help_text.append("• Commands support --help flag for argument details\n", style=example_style)
        help_text.append("• Use TAB for command history navigation\n", style=example_style)
        help_text.append("• All ESCMD commands work in interactive mode\n", style=example_style)
        help_text.append("• Theme changes only affect ESterm, not ESCMD output\n", style=example_style)

        panel = Panel(
            help_text,
            title="📖 ESterm Help",
            border_style=self.theme_manager.get_style('panels', 'border_style'),
            padding=(1, 2)
        )

        self.console.print(panel)

    def show_status(self, cluster_manager):
        """
        Show current connection status and cluster information with theme styling.

        Args:
            cluster_manager: ClusterManager instance
        """
        status_text = Text()

        # Get themed styles
        title_style = self.theme_manager.get_style('status', 'title_style')
        label_style = self.theme_manager.get_style('status', 'label_style')
        value_style = self.theme_manager.get_style('status', 'value_style')
        success_style = self.theme_manager.get_style('status', 'success_style')
        warning_style = self.theme_manager.get_style('status', 'warning_style')
        error_style = self.theme_manager.get_style('status', 'error_style')
        info_style = self.theme_manager.get_style('status', 'info_style')

        status_text.append("ESterm Status\n\n", style=title_style)

        # Connection status
        if cluster_manager.is_connected():
            cluster_info = cluster_manager.get_cluster_info()
            if cluster_info:
                status_text.append("Connection: ", style=label_style)
                status_text.append("Connected ✓\n", style=success_style)

                status_text.append("Cluster: ", style=label_style)
                status_text.append(f"{cluster_info['name']}\n", style=value_style)

                status_text.append("Status: ", style=label_style)
                status_color = self._get_themed_status_color(cluster_info['status'])
                status_text.append(f"{cluster_info['status'].upper()}\n", style=status_color)

                status_text.append("Nodes: ", style=label_style)
                status_text.append(f"{cluster_info['nodes']} total, {cluster_info['data_nodes']} data\n", style=value_style)

                status_text.append("Shards: ", style=label_style)
                status_text.append(f"{cluster_info['active_shards']} active\n", style=value_style)

                if 'cluster_name' in cluster_info:
                    status_text.append("Cluster Name: ", style=label_style)
                    status_text.append(f"{cluster_info['cluster_name']}\n", style=info_style)
            else:
                status_text.append("Connection: ", style=label_style)
                status_text.append("Connected but unable to fetch info\n", style=warning_style)
        else:
            status_text.append("Connection: ", style=label_style)
            status_text.append("Not connected ✗\n", style=error_style)
            status_text.append("\nUse 'connect' to connect to a cluster\n", style=info_style)

        # Theme information
        status_text.append("\nESterm Theme: ", style=label_style)
        current_theme = self.theme_manager.get_current_theme()
        theme_info = self.theme_manager.get_theme_info(current_theme)
        status_text.append(f"{theme_info['name']} ({current_theme})\n", style=value_style)

        # Available clusters
        clusters = cluster_manager.get_available_clusters()
        if clusters:
            status_text.append(f"\nAvailable Clusters: {len(clusters)}\n", style=label_style)
            for i, cluster in enumerate(clusters[:5], 1):  # Show first 5
                is_current = cluster == cluster_manager.get_current_cluster()
                prefix = "→ " if is_current else "  "
                style = success_style if is_current else info_style
                status_text.append(f"{prefix}{cluster}\n", style=style)

            if len(clusters) > 5:
                status_text.append(f"  ... and {len(clusters) - 5} more\n", style=info_style)

        panel = Panel(
            status_text,
            title="📊 Status Information",
            border_style=self.theme_manager.get_style('status', 'border_style'),
            padding=(1, 2)
        )

        self.console.print(panel)

    def get_prompt(self, cluster_manager) -> str:
        """
        Get the command prompt string with theme styling.

        Args:
            cluster_manager: ClusterManager instance

        Returns:
            str: Formatted prompt string
        """
        prompt_symbol_style = self.theme_manager.get_style('prompt', 'prompt_symbol_style')
        prompt_format = self.theme_manager.get_config_value('ui.prompt.format', 'esterm')
        show_icons = self.theme_manager.get_config_value('ui.prompt.show_icons', True)
        show_node_count = self.theme_manager.get_config_value('ui.prompt.show_node_count', False)
        show_time = self.theme_manager.get_config_value('ui.prompt.show_time', False)
        current_theme = self.theme_manager.get_current_theme()

        if cluster_manager and cluster_manager.is_connected():
            cluster_name = cluster_manager.get_current_cluster()
            cluster_info = cluster_manager.get_cluster_info()

            # Get contextual cluster indicator and enhanced cluster display
            cluster_indicator = self._get_cluster_indicator(cluster_name, cluster_info, show_icons)
            enhanced_cluster_display = self._get_enhanced_cluster_display(
                cluster_name, cluster_info, show_node_count
            )

            # Get time display if enabled
            time_display = self._get_time_display(show_time, current_theme)

            if prompt_format == 'simple':
                return f"{cluster_indicator}{cluster_name}> "
            elif prompt_format == 'minimal':
                return "> "
            elif prompt_format == 'cyberpunk' and current_theme == 'cyberpunk':
                return self._get_cyberpunk_prompt(enhanced_cluster_display, time_display, cluster_indicator)
            elif prompt_format == 'matrix' and current_theme == 'matrix':
                return self._get_matrix_prompt(enhanced_cluster_display, cluster_indicator)
            else:  # esterm format
                time_part = f" {time_display}" if time_display else ""
                return f"<[{prompt_symbol_style}]esterm[/{prompt_symbol_style}]({enhanced_cluster_display}){time_part}>"
        else:
            # Disconnected state
            disconnect_indicator = " " if show_icons else ""
            time_display = self._get_time_display(show_time, current_theme)

            if prompt_format == 'simple':
                return f"{disconnect_indicator}disconnected> "
            elif prompt_format == 'minimal':
                return "> "
            elif prompt_format == 'cyberpunk' and current_theme == 'cyberpunk':
                return self._get_cyberpunk_disconnected_prompt(disconnect_indicator, time_display)
            elif prompt_format == 'matrix' and current_theme == 'matrix':
                return self._get_matrix_disconnected_prompt(disconnect_indicator)
            else:  # esterm format
                disconnected_style = self.theme_manager.get_style('prompt', 'disconnected_style')
                time_part = f" {time_display}" if time_display else ""
                return f"<[{prompt_symbol_style}]esterm[/{prompt_symbol_style}]([{disconnected_style}]disconnected[/{disconnected_style}]){time_part}>"

    def get_user_input_with_history(self, prompt_text: str) -> Optional[str]:
        """
        Get user input with proper readline history support and colored prompts.

        Uses a two-line approach: colored prompt on first line, plain input on second line.

        Args:
            prompt_text: Prompt text to display

        Returns:
            str or None: User input or None if interrupted
        """
        try:
            # Print the colored prompt on its own line
            from rich.text import Text
            prompt_obj = Text.from_markup(prompt_text)
            self.console.print(prompt_obj)

            # Use a simple plain prompt on the next line for input
            # This completely avoids readline ANSI issues while preserving colors
            # Get prompt symbol from theme configuration
            prompt_symbol = self.theme_manager.get_style('prompt', 'prompt_symbol', '➤')
            user_input = input(f"{prompt_symbol} ")

            return user_input

        except (KeyboardInterrupt, EOFError):
            return None
        except Exception:
            raise

    def show_error(self, message: str, title: str = "Error"):
        """
        Display an error message in a themed panel.

        Args:
            message: Error message to display
            title: Panel title
        """
        error_style = self.theme_manager.get_style('messages', 'error_style')
        border_style = self.theme_manager.get_style('messages', 'error_style')

        # Check if panels should be used
        use_panels = self.theme_manager.get_config_value('ui.messages.use_panels', True)
        show_icons = self.theme_manager.get_config_value('ui.messages.show_icons', True)

        icon = "🔶  " if show_icons else ""

        if use_panels:
            error_panel = Panel.fit(
                f"[{error_style}]{message}[/{error_style}]",
                title=f"{icon}{title}",
                border_style=border_style,
                padding=(1, 2)
            )
            self.console.print(error_panel)
        else:
            self.console.print(f"[{error_style}]{icon}{title}: {message}[/{error_style}]")

    def show_success(self, message: str, title: str = "Success"):
        """
        Display a success message in a themed panel.

        Args:
            message: Success message to display
            title: Panel title
        """
        success_style = self.theme_manager.get_style('messages', 'success_style')
        border_style = self.theme_manager.get_style('messages', 'success_style')

        # Check if panels should be used
        use_panels = self.theme_manager.get_config_value('ui.messages.use_panels', True)
        show_icons = self.theme_manager.get_config_value('ui.messages.show_icons', True)

        icon = "✓ " if show_icons else ""

        if use_panels:
            success_panel = Panel.fit(
                f"[{success_style}]{message}[/{success_style}]",
                title=f"{icon}{title}",
                border_style=border_style,
                padding=(1, 2)
            )
            self.console.print(success_panel)
        else:
            self.console.print(f"[{success_style}]{icon}{title}: {message}[/{success_style}]")

    def show_warning(self, message: str, title: str = "Warning"):
        """
        Display a warning message in a themed panel.

        Args:
            message: Warning message to display
            title: Panel title
        """
        warning_style = self.theme_manager.get_style('messages', 'warning_style')
        border_style = self.theme_manager.get_style('messages', 'warning_style')

        # Check if panels should be used
        use_panels = self.theme_manager.get_config_value('ui.messages.use_panels', True)
        show_icons = self.theme_manager.get_config_value('ui.messages.show_icons', True)

        icon = "🔶  " if show_icons else ""

        if use_panels:
            warning_panel = Panel.fit(
                f"[{warning_style}]{message}[/{warning_style}]",
                title=f"{icon}{title}",
                border_style=border_style,
                padding=(1, 2)
            )
            self.console.print(warning_panel)
        else:
            self.console.print(f"[{warning_style}]{icon}{title}: {message}[/{warning_style}]")

    def show_info(self, message: str, title: str = "Information"):
        """
        Display an informational message in a themed panel.

        Args:
            message: Info message to display
            title: Panel title
        """
        info_style = self.theme_manager.get_style('messages', 'info_style')
        border_style = self.theme_manager.get_style('messages', 'info_style')

        # Check if panels should be used
        use_panels = self.theme_manager.get_config_value('ui.messages.use_panels', True)
        show_icons = self.theme_manager.get_config_value('ui.messages.show_icons', True)

        icon = "ℹ️  " if show_icons else ""

        if use_panels:
            info_panel = Panel.fit(
                f"[{info_style}]{message}[/{info_style}]",
                title=f"{icon}{title}",
                border_style=border_style,
                padding=(1, 2)
            )
            self.console.print(info_panel)
        else:
            self.console.print(f"[{info_style}]{icon}{title}: {message}[/{info_style}]")

    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Show a themed confirmation prompt to the user.

        Args:
            message: Confirmation message
            default: Default response if user just presses Enter

        Returns:
            bool: True if user confirmed, False otherwise
        """
        try:
            warning_style = self.theme_manager.get_style('messages', 'warning_style')
            default_text = "Y/n" if default else "y/N"
            response = Prompt.ask(f"[{warning_style}]{message}[/{warning_style}] [{default_text}]", default="")

            if not response:
                return default

            return response.lower() in ('y', 'yes', 'true', '1')
        except KeyboardInterrupt:
            return False

    def show_progress(self, message: str):
        """
        Show a themed progress/working message.

        Args:
            message: Progress message to display
        """
        progress_style = self.theme_manager.get_style('messages', 'progress_style')
        self.console.print(f"[{progress_style}]⏳ {message}...[/{progress_style}]")

    def clear_screen(self):
        """Clear the terminal screen."""
        self.console.clear()

    def print_separator(self, char: str = "─", width: Optional[int] = None):
        """
        Print a themed separator line.

        Args:
            char: Character to use for separator
            width: Width of separator (None for full width)
        """
        if width is None:
            width = self.console.size.width

        border_style = self.theme_manager.get_style('panels', 'border_style')
        self.console.print(char * width, style=border_style)

    def format_table(self, data: List[Dict[str, Any]], columns: List[str],
                    title: Optional[str] = None) -> Table:
        """
        Create a themed Rich table from data.

        Args:
            data: List of dictionaries containing row data
            columns: List of column names
            title: Optional table title

        Returns:
            Table: Formatted Rich table
        """
        header_style = self.theme_manager.get_style('status', 'title_style')
        content_style = self.theme_manager.get_style('status', 'value_style')

        table = Table(show_header=True, header_style=header_style, title=title)

        # Add columns
        for col in columns:
            table.add_column(col, style=content_style)

        # Add rows
        for row in data:
            values = [str(row.get(col, '')) for col in columns]
            table.add_row(*values)

        return table

    def show_spinner(self, message: str = "Working"):
        """
        Context manager for showing a themed spinner during operations.

        Args:
            message: Message to show with spinner

        Returns:
            Context manager for spinner
        """
        from rich.spinner import Spinner
        from rich.live import Live

        progress_style = self.theme_manager.get_style('messages', 'progress_style')
        spinner = Spinner("dots", text=f"[{progress_style}]{message}...[/{progress_style}]")
        return Live(spinner, console=self.console, refresh_per_second=12.5)

    def set_theme(self, theme_name: str) -> bool:
        """
        Set the ESterm theme.

        Args:
            theme_name: Name of the theme to set

        Returns:
            bool: True if theme was successfully set
        """
        return self.theme_manager.set_theme(theme_name)

    def get_current_theme(self) -> str:
        """Get the current theme name."""
        return self.theme_manager.get_current_theme()

    def list_themes(self):
        """Display available themes."""
        self.theme_manager.list_themes()

    def preview_theme(self, theme_name: str):
        """Preview a theme."""
        self.theme_manager.preview_theme(theme_name)

    def _get_themed_status_color(self, status: str) -> str:
        """
        Get appropriate themed color for cluster status.

        Args:
            status: Cluster status string

        Returns:
            str: Rich color string
        """
        status_map = {
            'green': self.theme_manager.get_style('status', 'success_style'),
            'yellow': self.theme_manager.get_style('status', 'warning_style'),
            'red': self.theme_manager.get_style('status', 'error_style'),
            'unknown': self.theme_manager.get_style('status', 'info_style'),
            'error': self.theme_manager.get_style('status', 'error_style')
        }
        return status_map.get(status.lower(), self.theme_manager.get_style('status', 'value_style'))

    def _get_themed_prompt_status_color(self, status: str) -> str:
        """
        Get appropriate themed color for prompt status.

        Args:
            status: Cluster status string

        Returns:
            str: Rich color string
        """
        status_map = {
            'green': self.theme_manager.get_style('prompt', 'connected_cluster_style'),
            'yellow': self.theme_manager.get_style('prompt', 'warning_cluster_style'),
            'red': self.theme_manager.get_style('prompt', 'disconnected_style'),
            'unknown': self.theme_manager.get_style('prompt', 'warning_cluster_style')
        }
        return status_map.get(status.lower(), self.theme_manager.get_style('prompt', 'connected_cluster_style'))









    def _get_cluster_indicator(self, cluster_name: str, cluster_info: dict, show_icons: bool) -> str:
        """Get contextual cluster indicator inspired by Starship's approach."""
        if not show_icons:
            return ""

        # Determine cluster type based on name patterns
        cluster_lower = cluster_name.lower()

        # Production-like environments
        if any(keyword in cluster_lower for keyword in ['prod', 'production', 'live', 'master']):
            return " "  # Database/server icon for production

        # Development environments
        elif any(keyword in cluster_lower for keyword in ['dev', 'develop', 'test', 'sandbox']):
            return " "  # Terminal icon for development

        # Staging environments
        elif any(keyword in cluster_lower for keyword in ['stage', 'staging', 'qa', 'uat']):
            return " "  # Beaker/test icon for staging

        # Local environments
        elif any(keyword in cluster_lower for keyword in ['local', 'localhost', '127.0.0.1']):
            return " "  # Home icon for local

        # Cloud providers (AWS, GCP, Azure, etc.)
        elif any(keyword in cluster_lower for keyword in ['aws', 'ec2', 'amazon']):
            return " "  # AWS icon
        elif any(keyword in cluster_lower for keyword in ['gcp', 'google', 'cloud']):
            return " "  # Google Cloud icon
        elif any(keyword in cluster_lower for keyword in ['azure', 'microsoft']):
            return " "  # Azure icon

        # Default elasticsearch icon for unknown clusters
        else:
            return " "  # Elasticsearch/search icon

    def _get_environment_context(self, cluster_name: str) -> str:
        """Get environment context indicator like Starship modules."""
        cluster_lower = cluster_name.lower()

        # Add subtle environment indicators
        if 'prod' in cluster_lower:
            return "[dim red]![/dim red]"  # Warning for production
        elif 'stage' in cluster_lower:
            return "[dim yellow]~[/dim yellow]"  # Staging indicator
        elif 'dev' in cluster_lower:
            return "[dim green]◦[/dim green]"  # Dev indicator

        return ""

    def _should_show_node_count(self, cluster_info, show_node_count: bool) -> bool:
        """Conditionally show node count like Starship's context-aware modules."""
        if not show_node_count or not cluster_info:
            return False

        node_count = cluster_info.get('number_of_nodes', 0)
        # Only show if we have meaningful node count (> 1)
        return node_count > 1

    def _get_prompt_status_indicator(self, cluster_info) -> str:
        """Get git-style status indicator for cluster state."""
        if not cluster_info:
            return ""

        indicators = []

        # Simulate git-style indicators for cluster state
        node_count = cluster_info.get('number_of_nodes', 0)
        if node_count > 3:
            indicators.append("[bright_green]+[/bright_green]")  # Many nodes
        elif node_count == 1:
            indicators.append("[dim yellow]•[/dim yellow]")  # Single node

        return "".join(indicators)

    def _get_enhanced_cluster_display(self, cluster_name: str, cluster_info, show_node_count: bool) -> str:
        """Get enhanced cluster display with additional information (no health status)."""
        # Use connected cluster style for consistent appearance
        connected_style = self.theme_manager.get_style('prompt', 'connected_cluster_style')
        base_display = f"[{connected_style}]{cluster_name}[/{connected_style}]"

        # Add environment context
        env_context = self._get_environment_context(cluster_name)
        if env_context:
            base_display = f"{env_context}{base_display}"

        # Add node count if conditionally appropriate
        if self._should_show_node_count(cluster_info, show_node_count):
            node_count = cluster_info.get('number_of_nodes', 0)
            base_display += f"[dim]:{node_count}[/dim]"

        # Add status indicators
        status_indicator = self._get_prompt_status_indicator(cluster_info)
        if status_indicator:
            base_display += f" {status_indicator}"

        return base_display

    def _get_time_display(self, show_time: bool, theme: str) -> str:
        """Get time display for prompt."""
        if not show_time:
            return ""

        import datetime
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M:%S")

        # Theme-specific time styling
        if theme == 'cyberpunk':
            return f"[bright_cyan]:: {time_str}[/bright_cyan]"
        elif theme == 'matrix':
            return f"[bright_green][{time_str}][/bright_green]"
        else:
            return f"[dim]{time_str}[/dim]"

    def _get_starship_style_fill(self, current_theme: str) -> str:
        """Get fill character for right-aligned elements like Starship."""
        if current_theme == 'cyberpunk':
            return " [dim bright_cyan]•[/dim bright_cyan] "
        elif current_theme == 'matrix':
            return " [dim green]·[/dim green] "
        else:
            return " [dim]•[/dim] "

    def _get_cyberpunk_prompt(self, cluster_display: str, time_display: str, cluster_indicator: str) -> str:
        """Get cyberpunk-themed prompt."""
        prompt_base = f"{cluster_indicator}[bold bright_magenta]esterm[/bold bright_magenta] [bright_cyan]>>[/bright_cyan] [{cluster_display}]"

        if time_display:
            prompt_base += f" {time_display}"

        return f"{prompt_base} [bright_cyan]>>[/bright_cyan] "

    def _get_matrix_prompt(self, cluster_display: str, cluster_indicator: str) -> str:
        """Get matrix-themed prompt."""
        return f"{cluster_indicator}[bold bright_green]esterm[/bold bright_green][green]@[/green][{cluster_display}] [bright_green]$[/bright_green] "

    def _get_cyberpunk_disconnected_prompt(self, disconnect_indicator: str, time_display: str) -> str:
        """Get cyberpunk-themed disconnected prompt."""
        prompt_base = f"{disconnect_indicator}[bold bright_magenta]esterm[/bold bright_magenta] [bright_red]>>[/bright_red] [bright_red]<OFFLINE>[/bright_red]"

        if time_display:
            prompt_base += f" {time_display}"

        return f"{prompt_base} [bright_red]>>[/bright_red] "

    def _get_matrix_disconnected_prompt(self, disconnect_indicator: str) -> str:
        """Get matrix-themed disconnected prompt."""
        return f"{disconnect_indicator}[bold bright_green]esterm[/bold bright_green][red]@[/red][bright_red]OFFLINE[/bright_red] [bright_red]$[/bright_red] "
