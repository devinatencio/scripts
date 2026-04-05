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


def show_welcome_screen(console, version=None, date=None):
    """Display a beautiful welcome screen when no command is provided."""

    # Use provided version/date or fallback defaults
    display_version = version or "3.7.4"
    display_date = date or "02/26/2026"

    # Create title panel
    title_table = Table.grid(padding=(0, 2))
    title_table.add_column(style="bold cyan", justify="center")
    title_table.add_row("🔍 ESCMD - Elasticsearch Command Line Tool")
    title_table.add_row(
        f"[dim]Advanced Elasticsearch CLI Management Tool v{display_version}[/dim]"
    )

    title_panel = Panel(
        Align.center(title_table),
        title="[bold green]Welcome to ESCMD[/bold green]",
        border_style="green",
        padding=(1, 2),
    )

    # Dynamically get all available commands
    command_info = _get_dynamic_command_info()

    # Quick start commands (still curated for best UX)
    quick_start_table = Table(expand=True)
    quick_start_table.add_column("Command", style="bold yellow", no_wrap=True)
    quick_start_table.add_column("Description", style="white")

    # Keep curated quick commands for best user experience
    quick_commands = [
        ("./escmd.py health", "Show cluster health status"),
        ("./escmd.py indices", "List all indices"),
        ("./escmd.py nodes", "Show cluster nodes"),
        ("./escmd.py version", "Show detailed version & statistics"),
        ("./escmd.py locations", "Show configured clusters"),
        ("./escmd.py help", "Show detailed help system"),
    ]

    for cmd, desc in quick_commands:
        quick_start_table.add_row(cmd, desc)

    quick_panel = Panel(
        quick_start_table,
        title="[bold blue]🚀 Quick Start Commands[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    )

    # Dynamic command categories (compact version)
    categories_table = Table(expand=True)
    categories_table.add_column("Category", style="bold magenta", no_wrap=True)
    categories_table.add_column("Count", justify="right", style="cyan")
    categories_table.add_column("Examples", style="white")

    # Use dynamic data for categories
    for category, data in command_info["categories"].items():
        count = data["count"]

        # Select better representative examples for each category
        if category == "Utilities":
            # For utilities, prioritize commonly used commands
            priority_commands = [
                "locations",
                "show-settings",
                "version",
                "help",
                "get-default",
                "set-default",
                "themes",
                "cluster-groups",
            ]
            available_commands = data["examples"]
            selected_examples = []

            # First, add priority commands that exist
            for cmd in priority_commands:
                if cmd in available_commands and len(selected_examples) < 3:
                    selected_examples.append(cmd)

            # Fill remaining slots with other commands if needed
            for cmd in sorted(available_commands):
                if cmd not in selected_examples and len(selected_examples) < 3:
                    selected_examples.append(cmd)

            examples = ", ".join(selected_examples)
        else:
            # For other categories, show first 3 as before
            examples = ", ".join(data["examples"][:3])

        categories_table.add_row(category, str(count), examples)

    # Add totals row
    categories_table.add_section()
    total_commands = command_info["total_commands"]
    total_subcommands = command_info["total_subcommands"]
    categories_table.add_row(
        "[bold white]TOTAL[/bold white]",
        f"[bold white]{total_commands + total_subcommands}[/bold white]",
        f"[dim]{total_commands} main + {total_subcommands} sub[/dim]",
    )

    categories_panel = Panel(
        categories_table,
        title="[bold magenta]📋 Categories Summary[/bold magenta]",
        border_style="magenta",
        padding=(1, 2),
    )

    # Complete command list with descriptions
    commands_table = _generate_complete_commands_table()

    commands_panel = Panel(
        commands_table,
        title="[bold cyan]📖 All Available Commands[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )

    # Usage tips
    tips_table = Table.grid(padding=(0, 1))
    tips_table.add_column(style="bold green", no_wrap=True)
    tips_table.add_column(style="white")

    tips_table.add_row(
        "💡", "Use [bold]--format json[/bold] for machine-readable output"
    )
    tips_table.add_row(
        "🎯", "Use [bold]-l <cluster>[/bold] to target specific clusters"
    )
    tips_table.add_row(
        "📊", "Use [bold]--group <name>[/bold] for multi-cluster operations"
    )
    tips_table.add_row(
        "🔍", "Use [bold]./escmd.py help <topic>[/bold] for detailed help"
    )
    tips_table.add_row(
        "⚡", "Most commands support [bold]--pager[/bold] for large outputs"
    )

    tips_panel = Panel(
        tips_table,
        title="[bold yellow]💡 Pro Tips[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    )

    # Display all panels
    console.print()
    console.print(title_panel)
    console.print()

    # Display quick start and categories side by side if terminal is wide enough
    if console.size.width >= 120:
        console.print(Columns([quick_panel, categories_panel], equal=True))
    else:
        console.print(quick_panel)
        console.print()
        console.print(categories_panel)

    console.print()
    console.print(commands_panel)
    console.print()
    console.print(tips_panel)
    console.print()

    # Footer with dynamic count
    footer_text = f"[dim]Run [bold]./escmd.py version[/bold] for complete command statistics ({total_commands + total_subcommands} total commands) or [bold]./escmd.py help <topic>[/bold] for detailed help[/dim]"
    console.print(Align.center(footer_text))
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

    # Get theme styles
    from esclient import get_theme_styles

    styles = get_theme_styles(configuration_manager)

    current_cluster = configuration_manager.get_default_cluster()
    if not current_cluster:
        console.print("[yellow]No default cluster configured.[/yellow]")
        return

    # Try both the original case and lowercase version
    server_config = configuration_manager.servers_dict.get(current_cluster.lower())
    if not server_config:
        server_config = configuration_manager.servers_dict.get(current_cluster)

    if not server_config:
        console.print(
            f"[red]Default server '{current_cluster}' not found in configuration.[/red]"
        )
        console.print("[yellow]Available clusters:[/yellow]")
        for cluster_name in sorted(configuration_manager.servers_dict.keys()):
            console.print(f"  • {cluster_name}")
        return

    # Create a table for the default configuration with better spacing
    config_table = Table.grid(padding=(0, 3))  # Add padding between columns
    config_table.add_column(
        style=styles.get("panel_styles", {}).get("secondary", "cyan"),
        no_wrap=True,
        min_width=15,
    )
    config_table.add_column(style="white")

    config_table.add_row("Location:", current_cluster.lower())
    config_table.add_row("Environment:", server_config.get("env", "Unknown"))
    config_table.add_row("Host:", server_config.get("hostname", "N/A"))
    config_table.add_row("Port:", str(server_config.get("port", 9200)))
    config_table.add_row("Username:", server_config.get("elastic_username", "N/A"))
    config_table.add_row("SSL Verify:", str(server_config.get("verify_certs", True)))

    panel = Panel(
        config_table,
        title=f"🎯 Current Default Cluster",
        title_align="left",
        border_style=styles["border_style"],
        padding=(1, 2),
    )

    console.print(panel)


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

    # Print state file info if available
    if hasattr(configuration_manager, "state_file_path"):
        info_style = styles.get("panel_styles", {}).get("subtitle", "dim white")
        console.print(
            f"[{info_style}]💾 State file: {configuration_manager.state_file_path}[/{info_style}]"
        )


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
