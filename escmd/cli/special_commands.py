"""
Special command handlers for escmd.
Handles commands that don't require ES connection.
"""

import sys
import os
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.align import Align
from rich.text import Text


def show_welcome_screen(console, version=None, date=None):
    """Display welcome screen when no command is provided."""

    display_version = version or "3.12.0"

    # ── banner ────────────────────────────────────────────────────────────────
    letters = [
        " ███████╗███████╗████████╗███████╗██████╗ ███╗   ███╗",
        " ██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║",
        " █████╗  ███████╗   ██║   █████╗  ██████╔╝██╔████╔██║",
        " ██╔══╝  ╚════██║   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║",
        " ███████╗███████║   ██║   ███████╗██║  ██║██║ ╚═╝ ██║",
        " ╚══════╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝",
    ]
    colours = ["bold cyan","bold cyan","bold blue","bold blue","bold magenta","bold magenta"]
    banner = Text()
    for line, colour in zip(letters, colours):
        banner.append(line + "\n", style=colour)

    console.print()
    console.print(Align.center(banner))
    console.print(Align.center(Text(
        f"v{display_version}  ·  Elasticsearch CLI Management & Monitoring", style="dim"
    )))
    console.print()

    # ── status bar ────────────────────────────────────────────────────────────
    try:
        from configuration_manager import ConfigurationManager
        _cm = ConfigurationManager()
        default_cluster = _cm.get_default_cluster()
    except Exception:
        default_cluster = None

    bar = Text()
    if default_cluster:
        bar.append("  🟢 Active cluster: ", style="bold green")
        bar.append(default_cluster, style="bold white")
        bar.append("   change with ", style="dim")
        bar.append("./escmd.py set-default <name>", style="dim cyan")
    else:
        bar.append("  ⚠  No default cluster set — run ", style="bold yellow")
        bar.append("./escmd.py set-default <name>", style="bold cyan")
        bar.append(" to configure one", style="bold yellow")
    console.print(Panel(bar, border_style="dim", padding=(0, 1)))
    console.print()

    # ── category data ─────────────────────────────────────────────────────────
    categories = [
        # row 1
        ("🏥 Cluster & Health", "green", [
            ("health",          "Cluster health"),
            ("health-detail",   "Full health dashboard"),
            ("cluster-check",   "Comprehensive checks"),
            ("ping",            "Test connectivity"),
            ("nodes",           "List nodes"),
            ("masters",         "Master nodes"),
            ("current-master",  "Active master"),
            ("recovery",        "Recovery jobs"),
        ]),
        ("📑 Index Management", "blue", [
            ("indices",               "List indices"),
            ("indice",                "Single index detail"),
            ("create-index",          "Create index"),
            ("freeze/unfreeze",       "Freeze or unfreeze"),
            ("flush",                 "Flush index"),
            ("set-replicas",          "Set replica count"),
            ("templates",             "List templates"),
            ("template",              "Template detail"),
            ("template-usage",        "Template usage analysis"),
            ("template-create",       "Create template"),
            ("template-modify",       "Modify template field"),
            ("template-backup",       "Backup template"),
            ("template-restore",      "Restore template backup"),
            ("indice-add-metadata",   "Add metadata to index"),
        ]),
        ("💾 Storage & Shards", "cyan", [
            ("storage",               "Disk usage"),
            ("shards",                "Shard distribution"),
            ("shard-colocation",      "Primary/replica on same host"),
            ("allocation",            "Allocation settings"),
            ("exclude",               "Exclude from host"),
            ("exclude-reset",         "Reset exclusion"),
            ("snapshots",             "Manage snapshots"),
            ("repositories",          "Snapshot repos"),
            ("dangling",              "Dangling indices"),
            ("indices-analyze",       "Rollover series outlier analysis"),
            ("indices-s3-estimate",   "S3 cost estimate"),
            ("indices-watch-collect", "Sample index stats to JSON"),
            ("indices-watch-report",  "Summarize watch samples"),
            ("list-backups",          "List template backups"),
        ]),
        # row 2
        ("🔄 ILM & Lifecycle", "yellow", [
            ("ilm",           "ILM policies"),
            ("datastreams",   "Datastream list"),
            ("rollover",      "Rollover datastream"),
            ("auto-rollover", "Rollover biggest shard"),
            ("es-top / top",  "Live cluster dashboard"),
            ("action",        "Action sequences"),
            ("cluster-groups","Display cluster groups"),
        ]),
        ("🔩 Settings & Config", "white", [
            ("cluster-settings",  "Cluster settings"),
            ("set",               "Set setting (dot notation)"),
            ("show-settings",     "Current config"),
            ("locations",         "Configured clusters"),
            ("get-default",       "Show default cluster"),
            ("set-default",       "Change default cluster"),
            ("set-username",      "Set default username"),
            ("set-theme",         "Change colour theme"),
            ("themes",            "Browse colour themes"),
        ]),
        ("🛠  Utilities", "bright_black", [
            ("version",               "Version & system info"),
            ("help",                  "Detailed help"),
            ("store-password",        "Store encrypted password"),
            ("list-stored-passwords", "List stored passwords"),
            ("remove-stored-password","Remove stored password"),
            ("generate-master-key",   "Generate master key"),
            ("rotate-master-key",     "Rotate master key"),
            ("migrate-to-env-key",    "Migrate to env key"),
            ("clear-session",         "Clear session cache"),
            ("session-info",          "Show session info"),
            ("set-session-timeout",   "Set session timeout"),
        ]),
    ]

    # ── grid renderer ─────────────────────────────────────────────────────────
    # Fixed column widths ensure all panels render identically regardless of
    # content length, so borders align perfectly across both rows.
    CMD_COL_WIDTH  = 24
    DESC_COL_WIDTH = 30

    def _make_table(commands, colour):
        t = Table.grid(padding=(0, 1))
        t.add_column(style=f"bold {colour}", no_wrap=True, width=CMD_COL_WIDTH)
        t.add_column(style="dim", width=DESC_COL_WIDTH)
        for cmd, desc in commands:
            t.add_row(cmd, desc)
        return t

    for row_cats in [categories[0:3], categories[3:6]]:
        max_cmds = max(len(c[2]) for c in row_cats)
        panels = []
        for title, colour, commands in row_cats:
            padded = commands + [("", "")] * (max_cmds - len(commands))
            panels.append(Panel(
                _make_table(padded, colour),
                title=f"[bold {colour}]{title}[/bold {colour}]",
                border_style=colour,
                padding=(0, 1),
            ))
        console.print(Columns(panels, equal=True, expand=True))
        console.print()

    # ── footer ────────────────────────────────────────────────────────────────
    footer = Text(justify="center")
    footer.append("./escmd.py help <cmd>", style="bold cyan")
    footer.append("  ·  ", style="dim")
    footer.append("./escmd.py version", style="bold cyan")
    footer.append("  ·  ", style="dim")
    footer.append("-l <cluster>", style="bold cyan")
    footer.append(" to target a cluster  ·  ", style="dim")
    footer.append("--format json", style="bold cyan")
    footer.append(" for machine output", style="dim")
    console.print(Panel(Align.center(footer), border_style="dim", padding=(0, 1)))
    console.print()


def _generate_complete_commands_table():
    """Generate a comprehensive table of all commands with descriptions."""
    # Get both static descriptions and dynamically discovered commands
    static_descriptions = _get_static_command_descriptions()

    # Get dynamically discovered commands
    try:
        from cli.argument_parser import create_argument_parser

        parser = create_argument_parser()
        discovered_commands = set()
        for action in parser._actions:
            if hasattr(action, "choices") and action.choices:
                discovered_commands.update(action.choices.keys())
                break
    except Exception:
        discovered_commands = set(static_descriptions.keys())

    # Combine static descriptions with any new commands
    commands_info = {}
    for cmd in discovered_commands:
        if cmd in static_descriptions:
            commands_info[cmd] = static_descriptions[cmd]
        else:
            # For new commands not in static list, provide a generic description
            commands_info[cmd] = f"Command: {cmd}"

    # Create the commands table with full width
    commands_table = Table(expand=True)  # This makes the table expand to full width
    commands_table.add_column("Command", style="bold yellow", no_wrap=True, width=22)
    commands_table.add_column("Description", style="white")

    # Sort commands alphabetically and add to table
    for cmd_name in sorted(commands_info.keys()):
        commands_table.add_row(cmd_name, commands_info[cmd_name])

    return commands_table


def _get_static_command_descriptions():
    """Static command descriptions as fallback."""
    return {
        "action": "Manage and execute action sequences for workflow automation",
        "allocation": "Manage cluster allocation settings",
        "auto-rollover": "Rollover biggest shard",
        "clear-session": "Clear the current session cache",
        "cluster-check": "Perform comprehensive cluster health checks",
        "cluster-groups": "Display configured cluster groups",
        "cluster-settings": "Show Elasticsearch Cluster Settings",
        "create-index": "Create a new empty index with custom settings",
        "current-master": "List Current Master",
        "dangling": "List, analyze, and manage dangling indices",
        "datastreams": "List datastreams or show datastream details",
        "exclude": "Exclude Indice from Host",
        "exclude-reset": "Remove Settings from Indice",
        "flush": "Perform Elasticsearch Flush",
        "freeze": "Freeze an Elasticsearch index",
        "generate-master-key": "Generate a master key for ESCMD_MASTER_KEY environment variable",
        "get-default": "Show Default Cluster configured",
        "health": "Show Cluster Health",
        "health-detail": "Show Detailed Cluster Health Dashboard",
        "help": "Show detailed help for specific commands",
        "ilm": "Manage Index Lifecycle Management (ILM)",
        "indice": "Indice - Single One",
        "indice-add-metadata": "Add metadata to an index",
        "indices": "Indices",
        "indices-analyze": "Compare backing index docs/size to sibling medians in each rollover series",
        "indices-s3-estimate": "Estimate monthly S3 cost from primary sizes in a rollover-date UTC window",
        "indices-watch-collect": "Sample index stats on an interval to JSON files (per cluster/date directory)",
        "indices-watch-report": "Summarize watch samples (docs/s, HOT vs peer median) without Elasticsearch",
        "list-backups": "List available template backups",
        "list-stored-passwords": "List all stored password environments",
        "locations": "Display All Configured Locations",
        "masters": "List ES Master nodes",
        "migrate-to-env-key": "Migrate from file-based master key to environment variable",
        "rotate-master-key": "Back up state file, new master key, re-encrypt stored passwords",
        "nodes": "List Elasticsearch nodes",
        "ping": "Check ES Connection",
        "recovery": "List Recovery Jobs",
        "remove-stored-password": "Remove stored password for an environment",
        "repositories": "Manage Elasticsearch Repositories",
        "rollover": "Rollover Single Datastream",
        "session-info": "Show current session cache information",
        "set": "Set Elasticsearch cluster settings using dot notation",
        "set-default": "Set Default Cluster to use for commands",
        "set-replicas": "Manage replica count for indices",
        "set-session-timeout": "Set session cache timeout in minutes",
        "set-theme": "Change the active theme",
        "set-username": "Set default Elasticsearch username in JSON config",
        "shard-colocation": "Find indices with primary and replica shards on the same host",
        "shards": "Show Shards",
        "show-settings": "Show current configuration settings",
        "snapshots": "Manage Elasticsearch snapshots",
        "storage": "List ES Disk Usage",
        "store-password": "Store encrypted password for an environment and optionally a specific username",
        "template": "Show detailed information about a specific template",
        "template-backup": "Create a backup of a template",
        "template-create": "Create templates from JSON file or inline definition",
        "template-modify": "Modify a template field",
        "template-restore": "Restore a template from backup",
        "template-usage": "Analyze template usage across indices",
        "templates": "List all Elasticsearch templates",
        "themes": "Display available themes with previews",
        "unfreeze": "Unfreeze an Elasticsearch index",
        "version": "Show version information",
    }


def _get_dynamic_command_info():
    """Dynamically discover all available commands and categorize them."""
    try:
        # Import the argument parser to discover commands
        from cli.argument_parser import create_argument_parser

        parser = create_argument_parser()

        # Extract all commands from subparsers
        discovered_commands = set()

        # More robust subparser discovery
        for action in parser._actions:
            if hasattr(action, "choices") and action.choices:
                discovered_commands.update(action.choices.keys())
                break

        # Categorize the discovered commands
        categorized_commands = _categorize_discovered_commands(discovered_commands)

        # Get subcommand counts
        subcommand_counts = _get_subcommand_counts()

        # Calculate totals and create category info
        command_info = {"categories": {}, "total_commands": 0, "total_subcommands": 0}

        for category, commands in categorized_commands.items():
            if not commands:  # Skip empty categories
                continue

            # Calculate subcounts for this category
            category_subcommands = sum(
                subcommand_counts.get(cmd, 0) for cmd in commands
            )

            command_info["categories"][category] = {
                "count": len(commands) + category_subcommands,
                "examples": sorted(commands),  # Will be truncated in display
            }

            command_info["total_commands"] += len(commands)
            command_info["total_subcommands"] += category_subcommands

        return command_info

    except Exception:
        # Fallback to static data if dynamic discovery fails
        return _get_static_command_info()


def _categorize_discovered_commands(commands):
    """Categorize discovered commands into logical groups."""
    command_categories = {
        "Cluster & Health": [],
        "Index Management": [],
        "Storage & Shards": [],
        "Allocation": [],
        "ILM & Lifecycle": [],
        "Snapshots": [],
        "Maintenance": [],
        "Utilities": [],
    }

    # Command category mappings
    category_mapping = {
        "Cluster & Health": [
            "ping",
            "health",
            "current-master",
            "masters",
            "nodes",
            "recovery",
            "cluster-check",
        ],
        "Index Management": [
            "indices",
            "indices-analyze",
            "indices-s3-estimate",
            "indices-watch-collect",
            "indice",
            "freeze",
            "unfreeze",
            "flush",
            "exclude",
            "exclude-reset",
            "set-replicas",
            "templates",
            "template",
            "template-usage",
        ],
        "Storage & Shards": ["storage", "shards", "shard-colocation"],
        "Allocation": ["allocation"],
        "ILM & Lifecycle": ["ilm", "rollover", "auto-rollover", "datastreams"],
        "Snapshots": ["snapshots"],
        "Maintenance": ["dangling", "cluster-settings"],
        "Utilities": [
            "help",
            "version",
            "locations",
            "get-default",
            "set-default",
            "show-settings",
            "themes",
            "cluster-groups",
            "indices-watch-report",
        ],
    }

    # Assign discovered commands to categories
    for category, expected_commands in category_mapping.items():
        for cmd in expected_commands:
            if cmd in commands:
                command_categories[category].append(cmd)

    # Add any uncategorized commands to Utilities
    all_categorized = set()
    for cmds in command_categories.values():
        all_categorized.update(cmds)

    uncategorized = commands - all_categorized
    if uncategorized:
        command_categories["Utilities"].extend(sorted(uncategorized))

    # Only return non-empty categories
    return {k: v for k, v in command_categories.items() if v}


def _get_static_command_info():
    """Fallback static command information."""
    return {
        "categories": {
            "Cluster & Health": {"count": 7, "examples": ["health", "nodes", "ping"]},
            "Index Management": {
                "count": 11,
                "examples": ["indices", "freeze", "set-replicas", "templates"],
            },
            "Storage & Shards": {"count": 3, "examples": ["storage", "shards"]},
            "ILM & Lifecycle": {
                "count": 12,
                "examples": ["ilm", "rollover", "datastreams"],
            },
            "Snapshots": {"count": 3, "examples": ["snapshots"]},
            "Allocation": {"count": 8, "examples": ["allocation"]},
            "Maintenance": {"count": 2, "examples": ["dangling", "cluster-settings"]},
            "Utilities": {"count": 14, "examples": ["locations", "help", "version"]},
        },
        "total_commands": 32,
        "total_subcommands": 25,
    }


def handle_version(version=None, date=None):
    """Display enhanced version information using the VersionRenderer."""
    from display.version_renderer import VersionRenderer
    from display.version_data import VersionDataCollector

    console = Console()

    # Collect version data
    data_collector = VersionDataCollector()
    version_data = data_collector.collect_version_data(version, date)

    # Render version information
    renderer = VersionRenderer(console)
    renderer.render_version_info(version_data)
    console.print()


def _read_version_from_esterm():
    """Read version and date from main esterm.py file."""
    import os
    import re

    # Try to find esterm.py in the current directory structure
    possible_paths = [
        "esterm.py",
        "../esterm.py",
        "../../esterm.py",
        os.path.join(os.path.dirname(__file__), "..", "esterm.py"),
    ]

    for path in possible_paths:
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    content = f.read()

                    # Extract VERSION
                    version_match = re.search(
                        r"VERSION\s*=\s*['\"]([^'\"]+)['\"]", content
                    )
                    date_match = re.search(r"DATE\s*=\s*['\"]([^'\"]+)['\"]", content)

                    if version_match and date_match:
                        return version_match.group(1), date_match.group(1)
        except:
            continue

    # If we can't find the file, raise an exception to use fallback
    raise Exception("Could not read version from esterm.py")


def _generate_feature_info_table():
    """Generate a table showing script features and capabilities."""
    from rich.table import Table
    import sys
    import platform
    import os
    from pathlib import Path

    feature_table = Table.grid(padding=(0, 3))
    feature_table.add_column(style="bold yellow", no_wrap=True, min_width=18)
    feature_table.add_column(style="white")

    # Python and system info
    feature_table.add_row("Python Version:", f"{sys.version.split()[0]}")
    feature_table.add_row("Python Executable:", sys.executable)
    feature_table.add_row("Platform:", f"{platform.system()} {platform.release()}")

    # Script location
    script_path = Path(__file__).parent.parent.resolve()
    feature_table.add_row("Script Location:", str(script_path))

    # Feature capabilities
    feature_table.add_row("", "")  # Separator
    feature_table.add_row("Output Formats:", "JSON, Table, Rich Dashboard")
    feature_table.add_row("Multi-Cluster:", "✓ Supported")
    feature_table.add_row("Configuration:", "YAML-based cluster configs")
    feature_table.add_row("Authentication:", "Basic Auth, SSL/TLS")
    feature_table.add_row("Paging Support:", "✓ Auto/Manual")
    feature_table.add_row("Color Output:", "✓ Rich Terminal UI")
    feature_table.add_row("Error Handling:", "✓ Retry Logic & Timeouts")
    feature_table.add_row("Dry Run Mode:", "✓ Safe Preview Mode")

    return feature_table


def _generate_command_stats_table():
    """Generate a table showing command statistics by category."""
    from rich.table import Table

    # Dynamically discover commands by importing the argument parser
    try:
        from cli.argument_parser import create_argument_parser

        parser = create_argument_parser()

        # Extract all commands from subparsers
        discovered_commands = set()
        if hasattr(parser, "_subparsers"):
            for action in parser._subparsers._actions:
                if hasattr(action, "choices"):
                    discovered_commands.update(action.choices.keys())

        # Map discovered commands to categories
        command_categories = _categorize_commands(discovered_commands)

    except Exception:
        # Fallback to static command list if discovery fails
        command_categories = _get_static_command_categories()

    # Count subcommands for complex commands
    subcommand_counts = _get_subcommand_counts()

    # Create statistics table
    stats_table = Table()
    stats_table.add_column("Category", style="bold yellow", no_wrap=True)
    stats_table.add_column("Commands", justify="right", style="cyan")
    stats_table.add_column("Subcommands", justify="right", style="magenta")
    stats_table.add_column("Total", justify="right", style="bold green")

    total_commands = 0
    total_subcommands = 0

    for category, commands in command_categories.items():
        command_count = len(commands)
        subcommand_count = sum(subcommand_counts.get(cmd, 0) for cmd in commands)
        category_total = command_count + subcommand_count

        total_commands += command_count
        total_subcommands += subcommand_count

        stats_table.add_row(
            category,
            str(command_count),
            str(subcommand_count) if subcommand_count > 0 else "-",
            str(category_total),
        )

    # Add separator and totals
    stats_table.add_section()
    stats_table.add_row(
        "[bold white]TOTAL[/bold white]",
        f"[bold white]{total_commands}[/bold white]",
        f"[bold white]{total_subcommands}[/bold white]",
        f"[bold white]{total_commands + total_subcommands}[/bold white]",
    )

    return stats_table


def _categorize_commands(commands):
    """Categorize discovered commands."""
    command_categories = {
        "Cluster & Health": [],
        "Index Management": [],
        "Storage & Shards": [],
        "Allocation": [],
        "ILM & Lifecycle": [],
        "Snapshots": [],
        "Maintenance": [],
        "Utility": [],
    }

    # Command category mappings
    category_mapping = {
        "Cluster & Health": [
            "ping",
            "health",
            "current-master",
            "masters",
            "nodes",
            "recovery",
            "cluster-check",
        ],
        "Index Management": [
            "indices",
            "indices-analyze",
            "indices-s3-estimate",
            "indices-watch-collect",
            "indice",
            "freeze",
            "unfreeze",
            "flush",
            "exclude",
            "exclude-reset",
            "set-replicas",
            "templates",
            "template",
            "template-usage",
        ],
        "Storage & Shards": ["storage", "shards", "shard-colocation"],
        "Allocation": ["allocation"],
        "ILM & Lifecycle": ["ilm", "rollover", "auto-rollover", "datastreams"],
        "Snapshots": ["snapshots"],
        "Maintenance": ["dangling", "cluster-settings"],
        "Utility": [
            "help",
            "version",
            "locations",
            "get-default",
            "set-default",
            "show-settings",
            "themes",
            "cluster-groups",
            "indices-watch-report",
        ],
    }

    # Assign discovered commands to categories
    for category, expected_commands in category_mapping.items():
        for cmd in expected_commands:
            if cmd in commands:
                command_categories[category].append(cmd)

    # Add any uncategorized commands to Utility
    all_categorized = set()
    for cmds in command_categories.values():
        all_categorized.update(cmds)

    uncategorized = commands - all_categorized
    command_categories["Utility"].extend(sorted(uncategorized))

    return {
        k: v for k, v in command_categories.items() if v
    }  # Only return non-empty categories


def _get_static_command_categories():
    """Fallback static command categories."""
    return {
        "Cluster & Health": [
            "ping",
            "health",
            "current-master",
            "masters",
            "nodes",
            "recovery",
            "cluster-check",
        ],
        "Index Management": [
            "indices",
            "indices-analyze",
            "indices-s3-estimate",
            "indices-watch-collect",
            "indice",
            "freeze",
            "unfreeze",
            "flush",
            "exclude",
            "exclude-reset",
            "set-replicas",
            "templates",
            "template",
            "template-usage",
        ],
        "Storage & Shards": ["storage", "shards", "shard-colocation"],
        "Allocation": ["allocation"],
        "ILM & Lifecycle": ["ilm", "rollover", "auto-rollover", "datastreams"],
        "Snapshots": ["snapshots"],
        "Maintenance": ["dangling", "cluster-settings"],
        "Utility": [
            "help",
            "version",
            "locations",
            "get-default",
            "set-default",
            "show-settings",
            "themes",
            "cluster-groups",
            "indices-watch-report",
        ],
    }


def _get_subcommand_counts():
    """Return subcommand counts for commands with subcommands."""
    return {
        "allocation": 6,  # enable, disable, exclude (add, remove, reset), explain
        "ilm": 9,  # status, policies, errors, policy, explain, remove-policy, set-policy, create-policy, delete-policy
        "snapshots": 2,  # list, status
        "help": 8,  # indices, ilm, health, nodes, allocation, snapshots, dangling, shards
    }


def handle_locations(configuration_manager):
    """Display all configured cluster locations using the LocationsRenderer."""
    from display.locations_renderer import LocationsRenderer
    from display.locations_data import LocationsDataCollector

    console = Console()

    # Get theme styles
    from esclient import get_theme_styles

    styles = get_theme_styles(configuration_manager)

    # Collect locations data
    data_collector = LocationsDataCollector()
    locations_data = data_collector.collect_locations_data(configuration_manager)

    # Render locations information
    renderer = LocationsRenderer(console)
    renderer.render_locations_table(locations_data, styles)


def handle_get_default(configuration_manager):
    """Display the current default cluster configuration."""
    console = Console()

    try:
        from display.theme_manager import ThemeManager
        from display.style_system import StyleSystem
        tm = ThemeManager(configuration_manager)
        ss = StyleSystem(tm)
        full_theme    = tm.get_full_theme_data()
        table_styles  = full_theme.get('table_styles', {})
        border        = table_styles.get('border_style', 'bright_blue')
        header_style  = table_styles.get('header_style', 'bold white on blue')
        title_style   = tm.get_themed_style('panel_styles', 'title', 'bold white')
        primary_style = ss._get_style('semantic', 'primary',  'cyan')
        warning_style = ss._get_style('semantic', 'warning',  'yellow')
        success_style = ss._get_style('semantic', 'success',  'green')
        muted_style   = ss._get_style('semantic', 'muted',    'dim')
        box_style     = ss.get_table_box()
    except Exception:
        from esclient import get_theme_styles
        styles        = get_theme_styles(configuration_manager)
        border        = styles.get('border_style', 'bright_blue')
        header_style  = 'bold white on blue'
        title_style   = 'bold white'
        primary_style = 'cyan'
        warning_style = 'yellow'
        success_style = 'green'
        muted_style   = 'dim'
        box_style     = None

    current_cluster = configuration_manager.get_default_cluster()
    if not current_cluster:
        console.print(Panel(
            f"[{warning_style}]No default cluster configured.[/{warning_style}]\n\n"
            f"[{muted_style}]Use [/{muted_style}][{primary_style}]./escmd.py set-default <cluster>[/{primary_style}] "
            f"[{muted_style}]to set one.[/{muted_style}]",
            title=f"[{title_style}]🎯 Default Cluster[/{title_style}]",
            border_style=warning_style,
            padding=(1, 2),
        ))
        return

    server_config = (
        configuration_manager.servers_dict.get(current_cluster.lower())
        or configuration_manager.servers_dict.get(current_cluster)
    )

    if not server_config:
        available = "\n".join(
            f"  [{success_style}]•[/{success_style}] {n}"
            for n in sorted(configuration_manager.servers_dict.keys())
        )
        console.print(Panel(
            f"[red]Default server '[bold]{current_cluster}[/bold]' not found in configuration.[/red]\n\n"
            f"[{warning_style}]Available clusters:[/{warning_style}]\n{available}",
            title=f"[{title_style}]🎯 Default Cluster[/{title_style}]",
            border_style="red",
            padding=(1, 2),
        ))
        return

    # Build details grid
    grid = Table(show_header=False, box=None, padding=(0, 3), expand=False)
    grid.add_column(style=f"bold {warning_style}", no_wrap=True, min_width=14)
    grid.add_column(style="white")

    auth     = server_config.get("elastic_authentication", False)
    username = server_config.get("elastic_username", "N/A")
    ssl      = server_config.get("verify_certs", True)

    grid.add_row("Location",    current_cluster.lower())
    grid.add_row("Environment", server_config.get("env", "Unknown"))
    grid.add_row("Host",        server_config.get("hostname", "N/A"))
    grid.add_row("Port",        str(server_config.get("port", 9200)))
    grid.add_row("Username",    username if auth else f"[{muted_style}]N/A (no auth)[/{muted_style}]")
    grid.add_row(
        "SSL Verify",
        f"[{success_style}]✔ Enabled[/{success_style}]" if ssl else f"[{warning_style}]✘ Disabled[/{warning_style}]",
    )

    console.print()
    console.print(Panel(
        grid,
        title=f"[{title_style}]🎯 Current Default Cluster[/{title_style}]",
        border_style=border,
        padding=(1, 2),
    ))


def handle_set_default(location, configuration_manager):
    """Set a new default cluster with intelligent cluster name resolution."""
    console = Console()

    # Get theme styles
    from esclient import get_theme_styles

    styles = get_theme_styles(configuration_manager)

    if not location:
        console.print(
            "[red]Error: Location parameter is required for set-default command.[/red]"
        )
        console.print("[yellow]Usage: ./escmd.py set-default <location>[/yellow]")
        return

    # Use the enhanced cluster resolution logic
    server_config = configuration_manager.get_server_config(location)

    if not server_config:
        console.print(
            f"[red]Error: Location '{location}' not found in configuration.[/red]"
        )
        console.print("[yellow]Available locations:[/yellow]")
        for loc in configuration_manager.servers_dict.keys():
            console.print(f"  • {loc}")
        return

    # Find the actual cluster name that was resolved
    resolved_cluster_name = None
    for name, config in configuration_manager.servers_dict.items():
        if config == server_config:
            resolved_cluster_name = name
            break

    # Update the default with the resolved cluster name
    old_default = configuration_manager.get_default_cluster()
    configuration_manager.set_default_cluster(resolved_cluster_name)

    # Success message showing both input and resolved names
    success_table = Table.grid(padding=(0, 3))  # Add padding for better spacing
    success_table.add_column(
        style=styles.get("panel_styles", {}).get("secondary", "cyan"),
        no_wrap=True,
        min_width=15,
    )
    success_table.add_column(style="white")

    if old_default:
        success_table.add_row("Previous Default:", old_default)

    # Show both the input name and resolved name if they differ
    if location.lower() != resolved_cluster_name:
        success_table.add_row("Input Name:", location)
        success_table.add_row("Resolved To:", resolved_cluster_name)
    else:
        success_table.add_row("New Default:", resolved_cluster_name)

    success_table.add_row("Environment:", server_config.get("env", "Unknown"))
    success_table.add_row("Host:", server_config.get("hostname", "N/A"))
    success_table.add_row("Port:", str(server_config.get("port", 9200)))

    panel = Panel(
        success_table,
        title="✅ Default Cluster Updated",
        title_align="left",
        border_style=styles.get("panel_styles", {}).get("success", "green"),
        padding=(1, 2),
    )

    console.print(panel)


def handle_show_settings(configuration_manager, format_output=None):
    """Display current configuration settings using the SettingsRenderer."""
    from display.settings_renderer import SettingsRenderer
    from display.settings_data import SettingsDataCollector

    console = Console()

    # Get theme styles
    from esclient import get_theme_styles

    styles = get_theme_styles(configuration_manager)

    # Collect settings data
    data_collector = SettingsDataCollector()
    settings_data = data_collector.collect_settings_data(configuration_manager)

    # Render settings information
    renderer = SettingsRenderer(console)

    if format_output == "json":
        renderer.render_json_settings(settings_data)
    else:
        renderer.render_settings_overview(settings_data, styles)


def handle_set_username(args, configuration_manager):
    """Handle set-username command to set elastic username in JSON config."""
    console = Console()

    # Get theme styles
    from esclient import get_theme_styles

    styles = get_theme_styles(configuration_manager)

    username = getattr(args, "username", None)
    show_current = getattr(args, "show_current", False)

    if show_current:
        current_json = configuration_manager.get_elastic_username_from_json()
        current_resolved = configuration_manager._resolve_username(
            {}
        )  # Empty server config to get default resolution

        info_table = Table.grid(padding=(0, 3))
        info_table.add_column(
            style=styles.get("panel_styles", {}).get("secondary", "cyan"),
            no_wrap=True,
            min_width=20,
        )
        info_table.add_column(style="white")

        info_table.add_row(
            "JSON Username:", current_json if current_json else "[dim]Not set[/dim]"
        )
        info_table.add_row(
            "Resolved Username:",
            current_resolved if current_resolved else "[dim]Not configured[/dim]",
        )

        panel = Panel(
            info_table,
            title="[bold white]🔑 Current Username Configuration[/bold white]",
            border_style=styles.get("border_style", "cyan"),
            padding=(1, 2),
        )
        console.print(panel)
        return

    if not username:
        console.print("[red]Error: Username parameter is required.[/red]")
        console.print(
            "[yellow]Usage: ./escmd.py set-username <username> or 'clear' to remove[/yellow]"
        )
        return

    # Handle clearing the username
    if username.lower() == "clear":
        success = configuration_manager.set_elastic_username(None)
        if success:
            console.print("[green]✓ Username cleared from JSON configuration.[/green]")
        else:
            console.print(
                "[red]Error: Failed to clear username from JSON configuration.[/red]"
            )
        return

    # Set the username
    success = configuration_manager.set_elastic_username(username)

    if success:
        # Show success message with priority information
        success_table = Table.grid(padding=(0, 3))
        success_table.add_column(
            style=styles.get("panel_styles", {}).get("secondary", "cyan"),
            no_wrap=True,
            min_width=20,
        )
        success_table.add_column(style="white")

        success_table.add_row("Username Set:", username)
        success_table.add_row("Priority Level:", "JSON Config (3rd priority)")
        success_table.add_row("Saved To:", configuration_manager.state_file_path)

        # Show priority order
        success_table.add_row("", "")  # Spacer
        success_table.add_row("Priority Order:", "1. Server-level config")
        success_table.add_row("", "2. Environment config")
        success_table.add_row("", "3. JSON config (you)")
        success_table.add_row("", "4. YAML global config")

        panel = Panel(
            success_table,
            title="[bold green]✓ Username Configuration Updated[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
        console.print(panel)
    else:
        console.print("[red]Error: Failed to set username in JSON configuration.[/red]")


def handle_cluster_groups(configuration_manager, format_output="table"):
    """Display configured cluster groups in a pretty table format."""
    from commands.utility_commands import UtilityCommands

    console = Console()

    # Create a utility command instance (doesn't need ES client for this operation)
    utility_cmd = UtilityCommands(
        None
    )  # ES client not needed for cluster groups display

    # Display cluster groups using the utility command method
    result = utility_cmd.show_cluster_groups(configuration_manager, format_output)

    if format_output == "json":
        console.print_json(data=result)

    return result
