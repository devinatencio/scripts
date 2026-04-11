"""
Help system module for escmd.
Provides beautiful Rich-formatted help display with theme support.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text


def show_custom_help(config_manager=None):
    """Display the beautiful custom help interface with theme support."""
    console = Console()

    # Get theme styles
    theme_styles = {}
    if config_manager:
        try:
            from esclient import get_theme_styles
            theme_styles = get_theme_styles(config_manager)
        except:
            # Fallback to default if theme loading fails
            theme_styles = {
                'help_styles': {
                    'title': 'bold cyan',
                    'section_header': 'bold yellow',
                    'command': 'bold yellow',
                    'description': 'white',
                    'example': 'cyan',
                    'footer': 'dim white'
                },
                'border_style': 'white'
            }
    else:
        # Default theme if no config manager
        theme_styles = {
            'help_styles': {
                'title': 'bold cyan',
                'section_header': 'bold yellow',
                'command': 'bold yellow',
                'description': 'white',
                'example': 'cyan',
                'footer': 'dim white'
            },
            'border_style': 'white'
        }

    help_styles = theme_styles.get('help_styles', {})
    border_style = theme_styles.get('border_style', 'white')

    # Create title panel with theme
    title_panel = Panel(
        Text("🧰 Elasticsearch Command-Line Tool",
             style=help_styles.get('title', 'bold cyan'),
             justify="center"),
        subtitle="Advanced cluster management and monitoring",
        border_style=border_style,
        padding=(1, 2)
    )

    # Create command categories with theme colors
    cluster_table = Table.grid(padding=(0, 3))
    cluster_table.add_column(style=help_styles.get('command', 'bold yellow'), no_wrap=True)
    cluster_table.add_column(style=help_styles.get('description', 'white'))
    cluster_table.add_row("🎯 get-default", "Show current default cluster configuration")
    cluster_table.add_row("🔍 health", "Cluster health monitoring (dashboard/classic/comparison/groups)")
    cluster_table.add_row("📍 locations", "List all configured clusters")
    cluster_table.add_row("🏓 ping", "Test connectivity with cluster details and health overview")
    cluster_table.add_row("📌 set-default", "Set default cluster for commands")
    cluster_table.add_row("🔩 cluster-settings", "View and manage cluster settings")
    cluster_table.add_row("🔧 show-settings", "Show current configuration settings")
    cluster_table.add_row("🎨 themes", "Display available color themes with previews")

    node_table = Table.grid(padding=(0, 3))
    node_table.add_column(style=help_styles.get('command', 'bold green'), no_wrap=True)
    node_table.add_column(style=help_styles.get('description', 'white'))
    node_table.add_row("🎯 current-master", "Show current master node")
    node_table.add_row("👑 masters", "List master-eligible nodes")
    node_table.add_row("💻 nodes", "List all cluster nodes")

    index_table = Table.grid(padding=(0, 3))
    index_table.add_column(style=help_styles.get('command', 'bold blue'), no_wrap=True)
    index_table.add_column(style=help_styles.get('description', 'white'))
    index_table.add_row("❌ dangling", "Manage dangling indices")
    index_table.add_row("📂 datastreams", "Manage datastreams")
    index_table.add_row("💧 flush", "Flush indices")
    index_table.add_row("🧊 freeze", "Freeze indices")
    index_table.add_row("📄 indice", "Show single index details")
    index_table.add_row("📊 indices", "List and manage indices")
    index_table.add_row("📈 indices-analyze", "Rollover-series doc/size outliers vs peers")
    index_table.add_row("💰 indices-s3-estimate", "Rough S3 $/mo from primary sizes in a date window")
    index_table.add_row("📡 indices-watch-collect", "Sample _cat stats on an interval → JSON")
    index_table.add_row("📉 indices-watch-report", "Summarize samples (no ES); docs/s & HOT")
    index_table.add_row("🔗 shard-colocation", "Find primary/replica shards on same host")
    index_table.add_row("🔄 shards", "View shard distribution")
    index_table.add_row("📋 template", "Show detailed template information")
    index_table.add_row("📝 templates", "List all index templates")
    index_table.add_row("🔥 unfreeze", "Unfreeze indices")

    ops_table = Table.grid(padding=(0, 3))
    ops_table.add_column(style=help_styles.get('command', 'bold magenta'), no_wrap=True)
    ops_table.add_column(style=help_styles.get('description', 'white'))
    ops_table.add_row("🔀 allocation", "Manage shard allocation and explain allocation decisions")
    ops_table.add_row("🏥 cluster-check", "Comprehensive cluster health checks (ILM errors, replicas, shard sizes)")
    ops_table.add_row("📊 es-top", "Live auto-refreshing cluster dashboard (nodes, indices, health)")
    ops_table.add_row("📆 ilm", "Index Lifecycle Management")
    ops_table.add_row("🔄 recovery", "Monitor recovery operations")
    ops_table.add_row("📦 repositories", "List snapshot repositories")
    ops_table.add_row("🔄 rollover", "Rollover operations")
    ops_table.add_row("🔢 set-replicas", "Set replica count for indices")
    ops_table.add_row("📸 snapshots", "Manage snapshots")
    ops_table.add_row("💾 storage", "View disk usage")
    ops_table.add_row("📊 version", "Show version information")

    # Create panels for each category with theme colors
    cluster_panel = Panel(cluster_table,
                         title=f"[{help_styles.get('section_header', 'bold yellow')}]🏢 Cluster & Config[/{help_styles.get('section_header', 'bold yellow')}]",
                         border_style=border_style, padding=(1, 1))
    node_panel = Panel(node_table,
                      title=f"[{help_styles.get('section_header', 'bold green')}]💻 Nodes & Masters[/{help_styles.get('section_header', 'bold green')}]",
                      border_style=border_style, padding=(1, 1))
    index_panel = Panel(index_table,
                       title=f"[{help_styles.get('section_header', 'bold blue')}]📊 Indices & Data[/{help_styles.get('section_header', 'bold blue')}]",
                       border_style=border_style, padding=(1, 1))
    ops_panel = Panel(ops_table,
                     title=f"[{help_styles.get('section_header', 'bold magenta')}]⚡ Operations[/{help_styles.get('section_header', 'bold magenta')}]",
                     border_style=border_style, padding=(1, 1))

    # Usage examples with theme colors
    usage_content = Text()
    usage_content.append("Quick Health Check:        ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py health\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Detailed Health Dashboard: ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py health-detail\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Compare Clusters:          ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py health-detail --compare iad41\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Group Health:              ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py health-detail --group att\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Allocation Explain:        ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py allocation explain my-index\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Cluster with Location:     ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py -l sjc01 health\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("JSON Output:               ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py indices --format json\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Topic help (indices):      ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py help indices\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Topic help (analyze):      ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py help indices-analyze\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Topic help (S3 estimate):  ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py help indices-s3-estimate\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Topic help (watch collect): ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py help indices-watch-collect\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Topic help (watch report): ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py help indices-watch-report\n", style=help_styles.get('example', 'cyan'))
    usage_content.append("Topic help (es-top):       ", style=help_styles.get('description', 'bold white'))
    usage_content.append("./escmd.py help es-top\n", style=help_styles.get('example', 'cyan'))

    usage_panel = Panel(usage_content,
                       title=f"[{help_styles.get('section_header', 'bold cyan')}]🚀 Quick Start Examples[/{help_styles.get('section_header', 'bold cyan')}]",
                       border_style=border_style, padding=(1, 2))

    # Create layout
    print()
    console.print(title_panel)
    print()

    # Create a grid for perfect alignment
    grid_table = Table.grid()
    grid_table.add_column(style="", ratio=1)  # Column 1 - 50% width
    grid_table.add_column(style="", ratio=1)  # Column 2 - 50% width

    # Add rows with panels
    grid_table.add_row(cluster_panel, node_panel)   # Row 1
    grid_table.add_row(index_panel, ops_panel)      # Row 2

    # Display the perfect grid
    console.print(grid_table)
    print()
    console.print(usage_panel)
    print()

    # Footer with global options using theme colors
    footer_text = Text("Global Options: ", style=help_styles.get('description', 'bold white'))
    footer_text.append("-l <cluster>", style=help_styles.get('command', 'bold yellow'))
    footer_text.append(" (specify cluster)  ", style=help_styles.get('description', 'white'))
    footer_text.append("--help", style=help_styles.get('command', 'bold yellow'))
    footer_text.append(" (this screen)  ", style=help_styles.get('description', 'white'))
    footer_text.append("help <topic>", style=help_styles.get('command', 'bold yellow'))
    footer_text.append(
        " (e.g. ./escmd.py help indices-analyze)",
        style=help_styles.get('description', 'white'),
    )

    footer_panel = Panel(footer_text, border_style=help_styles.get('footer', border_style))
    console.print(footer_panel)
    print()
