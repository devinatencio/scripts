"""
Refactored help handler for escmd using modular help system.

Provides detailed help and examples for major commands using a registry-based approach.
"""

from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    Console = None
    Table = None
    Panel = None

from .base_handler import BaseHandler
from .help import get_help_registry, get_help_for_topic


class HelpHandler(BaseHandler):
    """Handler for global help command using modular help system."""

    def __init__(self, *args, **kwargs):
        """Initialize help handler with registry support."""
        super().__init__(*args, **kwargs)
        self.help_registry = get_help_registry()

    def handle_help(self):
        """Handle help command for various topics."""
        if not hasattr(self.args, 'topic') or not self.args.topic:
            self._show_general_help()
        else:
            self._show_command_help(self.args.topic)

    def _show_general_help(self):
        """Show general help with all available help topics."""
        if Console is None:
            print("Rich library not available. Please install it with: pip install rich")
            return

        console = Console()

        # Get theme styles
        help_styles, border_style = self._get_theme_styles()

        # Create help topics table
        if Table is None:
            print("Rich library not available for table formatting")
            return

        topics_table = Table.grid(padding=(0, 3))
        topics_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=16)
        topics_table.add_column(style=help_styles.get('description', 'white'))

        # Get available topics from registry
        available_topics = self.help_registry.get_available_topics()

        # Add topics in a specific order for consistency
        ordered_topics = [
            'allocation', 'dangling', 'exclude', 'freeze', 'health', 'ilm',
            'indice-add-metadata', 'indices', 'indices-analyze', 'indices-s3-estimate',
            'indices-watch-collect', 'indices-watch-report', 'nodes', 'shards',
            'snapshots', 'security', 'templates', 'unfreeze'
        ]

        # Add ordered topics first
        for topic in ordered_topics:
            if topic in available_topics:
                topics_table.add_row(topic, available_topics[topic])

        # Add any additional topics that weren't in the ordered list
        for topic, description in available_topics.items():
            if topic not in ordered_topics:
                topics_table.add_row(topic, description)

        # Create main help panel
        if Panel is None:
            print("Rich library not available for panel formatting")
            return

        help_panel = Panel(
            topics_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]📚 Available Help Topics[/{help_styles.get('header', 'bold magenta')}]",
            subtitle=f"[{help_styles.get('usage', 'yellow')}]Use: ./escmd.py help <topic> for detailed information[/{help_styles.get('usage', 'yellow')}]",
            border_style=border_style,
            padding=(1, 2)
        )

        # Display help
        print()
        console.print(help_panel)
        print()

    def _show_command_help(self, command):
        """Show detailed help for a specific command."""
        # Handle aliases - map "action" to "actions"
        if command == "action":
            command = "actions"

        help_content = get_help_for_topic(command, self._get_theme_manager())

        if help_content:
            help_content.show_help()
        else:
            # Fallback for unknown topics
            if Console is None or Panel is None:
                print(f"Unknown help topic: {command}")
                print("Use './escmd.py help' to see all available topics.")
                return

            console = Console()
            help_styles, border_style = self._get_theme_styles()

            error_panel = Panel(
                f"[{help_styles.get('warning', 'bold red')}]Unknown help topic: {command}[/{help_styles.get('warning', 'bold red')}]\n\n"
                f"[{help_styles.get('description', 'white')}]Use './escmd.py help' to see all available topics.[/{help_styles.get('description', 'white')}]",
                title=f"[{help_styles.get('warning', 'bold red')}]❌ Help Topic Not Found[/{help_styles.get('warning', 'bold red')}]",
                border_style=border_style,
                padding=(1, 2)
            )

            print()
            console.print(error_panel)
            print()

    def _get_theme_styles(self):
        """Get theme styles for help display."""
        theme_manager = self._get_theme_manager()

        if theme_manager:
            # Get help-specific styles from theme
            help_styles = theme_manager.get_theme_section('help_styles', {
                'command': 'bold cyan',
                'description': 'white',
                'example': 'green',
                'usage': 'yellow',
                'header': 'bold magenta',
                'subheader': 'bold blue',
                'warning': 'bold red',
                'success': 'bold green'
            })
            border_style = theme_manager.get_theme_value('table_styles', 'border_style', 'white')
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

    def _get_theme_manager(self) -> Optional[object]:
        """Get theme manager instance if available."""
        # Try to get theme manager from parent class or configuration
        if hasattr(self, 'theme_manager'):
            return self.theme_manager
        elif hasattr(self, 'config_manager') and hasattr(self.config_manager, 'theme_manager'):
            return self.config_manager.theme_manager
        else:
            return None
