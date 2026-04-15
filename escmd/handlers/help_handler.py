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
        """Show general help — zebra table with coloured topic pills, sorted alphabetically within groups."""
        if Console is None or Table is None or Panel is None:
            print("Rich library not available. Please install it with: pip install rich")
            return

        from collections import OrderedDict
        from rich.text import Text
        from rich.align import Align

        console = Console()

        # ── topic catalogue: (category, colour, topic, description) ──
        # All registered topics have detailed docs — badge shown on all
        _TOPICS = [
            ("🏥 Cluster & Health",  "green",        "allocation",            "Shard allocation management"),
            ("🏥 Cluster & Health",  "green",        "health",                "Cluster health monitoring options"),
            ("🏥 Cluster & Health",  "green",        "nodes",                 "Node management and information"),
            ("🏥 Cluster & Health",  "green",        "shards",                "Shard distribution and analysis"),

            ("📑 Index Management",  "blue",         "dangling",              "Dangling index management"),
            ("📑 Index Management",  "blue",         "exclude",               "Index exclusion from specific hosts"),
            ("📑 Index Management",  "blue",         "freeze",                "Freeze indices to prevent write operations"),
            ("📑 Index Management",  "blue",         "indice-add-metadata",   "Add custom metadata to indices"),
            ("📑 Index Management",  "blue",         "indices",               "Index management operations and examples"),
            ("📑 Index Management",  "blue",         "unfreeze",              "Unfreeze indices to restore write operations"),

            ("📋 Templates",         "cyan",         "template-backup",       "Backup an Elasticsearch template to JSON"),
            ("📋 Templates",         "cyan",         "template-modify",       "Modify template fields (set/append/remove/delete)"),
            ("📋 Templates",         "cyan",         "template-restore",      "Restore a template from a backup file"),
            ("📋 Templates",         "cyan",         "templates",             "Index template management operations"),

            ("📊 Analytics",         "yellow",       "es-top",                "Live auto-refreshing cluster dashboard"),
            ("📊 Analytics",         "yellow",       "indices-analyze",       "Rollover backing indices outlier analysis"),
            ("📊 Analytics",         "yellow",       "indices-s3-estimate",   "Rough monthly S3 cost from primary store sizes"),
            ("📊 Analytics",         "yellow",       "indices-watch-collect", "Sample index stats on an interval to JSON"),
            ("📊 Analytics",         "yellow",       "indices-watch-report",  "Summarize watch JSON samples without Elasticsearch"),

            ("🔄 ILM & Lifecycle",   "yellow",       "ilm",                   "Index Lifecycle Management commands"),

            ("📸 Snapshots",         "magenta",      "repositories",          "Snapshot repository configuration and management"),
            ("📸 Snapshots",         "magenta",      "snapshots",             "Backup and snapshot operations"),

            ("🔐 Security",          "red",          "security",              "Password management and security features"),
            ("🔐 Security",          "red",          "store-password",        "Store an encrypted password for an environment"),

            ("🛠  Utilities",        "bright_black", "actions",               "Action sequence management and execution"),
        ]

        # Pull any registry topics not already listed (future-proof)
        available = self.help_registry.get_available_topics()
        listed = {t[2] for t in _TOPICS}
        for topic, desc in sorted(available.items()):
            if topic not in listed:
                _TOPICS.append(("🛠  Utilities", "bright_black", topic, desc))

        # Get theme styles for the table
        from handlers.help.base_help_content import BaseHelpContent
        class _TmpContent(BaseHelpContent):
            def show_help(self): pass
            def get_topic_name(self): return ""
            def get_topic_description(self): return ""
        _tmp = _TmpContent(self._get_theme_manager())
        _styles, _border = _tmp._get_theme_styles()
        _hdr   = _styles['header_style']
        _zebra = _styles['zebra']
        _desc  = _styles['description']

        _CAT_BG = ["", "on grey7", "", "on grey7", "", "on grey7", "", "on grey7"]
        cat_order = list(OrderedDict.fromkeys(t[0] for t in _TOPICS))

        from rich import box as rich_box
        _box_map = {
            'heavy': rich_box.HEAVY, 'double': rich_box.DOUBLE,
            'rounded': rich_box.ROUNDED, 'simple': rich_box.SIMPLE,
            'minimal': rich_box.MINIMAL, 'horizontals': rich_box.HORIZONTALS,
            'none': None,
        }
        _table_box = _box_map.get(_styles.get('table_box', 'heavy').lower(), rich_box.HEAVY)

        tbl = Table(
            expand=True,
            show_header=True,
            header_style=_hdr,
            border_style=_border,
            box=_table_box,
            show_lines=False,
            pad_edge=True,
            padding=(0, 1),
        )
        tbl.add_column("Category",    no_wrap=True, min_width=22)
        tbl.add_column("Topic",       no_wrap=True, min_width=28)
        tbl.add_column("Description")
        tbl.add_column("",            no_wrap=True, width=10)

        prev_cat = None
        for row in _TOPICS:
            cat, colour, topic, desc = row[0], row[1], row[2], row[3]
            cat_idx = cat_order.index(cat)
            bg = _CAT_BG[cat_idx % len(_CAT_BG)]

            cat_cell   = Text(cat, style=f"bold {colour} {bg}") if cat != prev_cat else Text("", style=bg)
            topic_cell = Text(f" {topic} ", style=f"bold black on {colour}")
            desc_cell  = Text(desc, style=f"{_desc} {bg}")
            badge_cell = Text(" detailed ", style=f"dim {colour} {bg}")

            tbl.add_row(cat_cell, topic_cell, desc_cell, badge_cell)
            prev_cat = cat

        console.print()
        console.print(Panel(
            tbl,
            title=f"[bold white]📚 Help Topics[/bold white]  [dim]({len(_TOPICS)} topics)[/dim]",
            border_style="dim",
            padding=(0, 0),
        ))
        console.print()

        hint = Text(justify="center")
        hint.append("./escmd.py help <topic>", style="bold cyan")
        hint.append("  ·  ", style="dim")
        hint.append("detailed", style="dim cyan")
        hint.append(" = rich subcommand docs available", style="dim")
        console.print(Panel(Align.center(hint), border_style="dim", padding=(0, 1)))
        console.print()

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
        # Check direct attribute first
        if hasattr(self, 'theme_manager') and self.theme_manager:
            return self.theme_manager
        # Check es_client (MockESClient or real client both carry theme_manager)
        if self.es_client and hasattr(self.es_client, 'theme_manager') and self.es_client.theme_manager:
            return self.es_client.theme_manager
        # Check config_manager
        if hasattr(self, 'config_manager') and hasattr(self.config_manager, 'theme_manager'):
            return self.config_manager.theme_manager
        return None
