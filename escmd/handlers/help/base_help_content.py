"""
Base help content class for modular help system.

Provides common functionality and structure for individual help content modules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


class BaseHelpContent(ABC):
    """Base class for help content modules."""

    def __init__(self, theme_manager=None):
        """Initialize base help content with optional theme manager."""
        self.theme_manager = theme_manager
        self.console = Console()

    def _get_theme_styles(self) -> Tuple[Dict[str, str], str]:
        """Get theme styles for help display."""
        if self.theme_manager:
            # Get help-specific styles from theme
            help_styles = self.theme_manager.get_theme_section('help_styles', {
                'command': 'bold cyan',
                'description': 'white',
                'example': 'green',
                'usage': 'yellow',
                'header': 'bold magenta',
                'subheader': 'bold blue',
                'warning': 'bold red',
                'success': 'bold green'
            })
            border_style = self.theme_manager.get_theme_value('table_styles', 'border_style', 'white')
        else:
            # Default styles
            help_styles = {
                'command': 'bold cyan',
                'description': 'white',
                'example': 'green',
                'usage': 'yellow',
                'header': 'bold magenta',
                'subheader': 'bold blue',
                'warning': 'bold red',
                'success': 'bold green'
            }
            border_style = 'white'

        return help_styles, border_style

    def _create_commands_table(self) -> Table:
        """Create a standardized commands table."""
        help_styles, _ = self._get_theme_styles()

        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=25)
        commands_table.add_column(style=help_styles.get('description', 'white'))

        return commands_table

    def _create_examples_table(self) -> Table:
        """Create a standardized examples table."""
        help_styles, _ = self._get_theme_styles()

        examples_table = Table.grid(padding=(0, 2))
        examples_table.add_column(style=help_styles.get('example', 'green'), min_width=35)
        examples_table.add_column(style=help_styles.get('description', 'white'))

        return examples_table

    def _create_usage_table(self) -> Table:
        """Create a standardized usage/workflows table."""
        help_styles, _ = self._get_theme_styles()

        usage_table = Table.grid(padding=(0, 2))
        usage_table.add_column(style=help_styles.get('usage', 'yellow'), min_width=30)
        usage_table.add_column(style=help_styles.get('description', 'white'))

        return usage_table

    def _display_help_panels(self, commands_table: Table, examples_table: Table,
                           commands_title: str, examples_title: str,
                           usage_table: Table = None, usage_title: str = None) -> None:
        """Display help panels in a consistent format."""
        help_styles, border_style = self._get_theme_styles()

        # Commands panel
        commands_panel = Panel(
            commands_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]{commands_title}[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        )

        # Examples panel
        examples_panel = Panel(
            examples_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]{examples_title}[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        )

        # Usage panel (optional)
        usage_panel = None
        if usage_table and usage_title:
            usage_panel = Panel(
                usage_table,
                title=f"[{help_styles.get('header', 'bold magenta')}]{usage_title}[/{help_styles.get('header', 'bold magenta')}]",
                border_style=border_style,
                padding=(1, 2)
            )

        # Display panels
        print()
        self.console.print(commands_panel)
        print()
        self.console.print(examples_panel)

        if usage_panel:
            print()
            self.console.print(usage_panel)

        print()

    @abstractmethod
    def show_help(self) -> None:
        """Show help content for this module. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def get_topic_name(self) -> str:
        """Get the topic name for this help module. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def get_topic_description(self) -> str:
        """Get the topic description for this help module. Must be implemented by subclasses."""
        pass
