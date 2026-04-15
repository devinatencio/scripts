#!/usr/bin/env python3
"""
Preview: Condensed allocation settings layout.

Current layout (5 panels):
  1. Title panel (full width)
  2. Allocation Status (left) + Quick Actions (right)
  3. Configuration Details (full width)
  4. Excluded Nodes (full width)

Proposed layout (3 panels):
  1. Title panel with richer subtitle (full width)
  2. Status & Config merged (left) + Quick Actions (right)
  3. Excluded Nodes only shown if exclusions exist (full width)

Run: python3 demo/allocation_settings_preview.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

console = Console()

# ── Simulated data ──────────────────────────────────────────────────
allocation_enabled = False
total_nodes = 3
data_nodes = 2
excluded_nodes = ["aex10-c01-ess01-3"]
excluded_count = len(excluded_nodes)
active_nodes = data_nodes - excluded_count
enable_setting = "primaries"


def preview_current():
    """Show the CURRENT 5-panel layout."""
    console.rule("[bold white]CURRENT LAYOUT (5 panels)[/bold white]", style="dim")
    print()

    # Title panel
    subtitle = Text()
    subtitle.append("Status: ", style="default")
    subtitle.append("🔶 Disabled", style="yellow")
    subtitle.append(" | Total: ", style="default")
    subtitle.append(str(total_nodes), style="cyan")
    subtitle.append(" | Data: ", style="default")
    subtitle.append(str(data_nodes), style="bright_magenta")
    subtitle.append(" | Excluded: ", style="default")
    subtitle.append(str(excluded_count), style="red")
    subtitle.append(" | Active: ", style="default")
    subtitle.append(str(active_nodes), style="green")

    title_panel = Panel(
        Text("🔀 Elasticsearch Allocation Settings Overview", style="bold cyan", justify="center"),
        subtitle=subtitle,
        border_style="cyan",
        padding=(1, 2),
    )

    # Status panel
    status_table = Table(show_header=False, box=None, padding=(0, 1))
    status_table.add_column("Label", style="bold", no_wrap=True)
    status_table.add_column("Icon", justify="left", width=3)
    status_table.add_column("Value", no_wrap=True)
    status_table.add_row("Allocation Status:", "🔶", "Disabled (Primaries Only)")
    status_table.add_row("Shard Movement:", "🔒", "Primaries Only")
    status_table.add_row("Total Nodes:", "💻", str(total_nodes))
    status_table.add_row("Data Nodes:", "💾", str(data_nodes))
    status_table.add_row("Excluded Nodes:", "❌", str(excluded_count))
    status_table.add_row("Active Nodes:", "✅", str(active_nodes))
    status_panel = Panel(status_table, title="📊 Allocation Status", border_style="yellow", padding=(1, 2))

    # Quick Actions panel
    actions_table = Table(show_header=False, box=None, padding=(0, 1))
    actions_table.add_column("Action", style="bold magenta", no_wrap=True)
    actions_table.add_column("Command", style="dim white")
    actions_table.add_row("Enable allocation:", "./escmd.py allocation enable")
    actions_table.add_row("Disable allocation:", "./escmd.py allocation disable")
    actions_table.add_row("Exclude node:", "./escmd.py allocation exclude add <hostname>")
    actions_table.add_row("Remove exclusion:", "./escmd.py allocation exclude remove <hostname>")
    actions_table.add_row("Reset exclusions:", "./escmd.py allocation exclude reset")
    actions_panel = Panel(actions_table, title="🚀 Quick Actions", border_style="magenta", padding=(1, 2))

    # Config panel
    config_table = Table(show_header=False, box=None, padding=(0, 1))
    config_table.add_column("Setting", style="bold", no_wrap=True)
    config_table.add_column("Icon", justify="left", width=3)
    config_table.add_column("Value", no_wrap=True)
    config_table.add_row("Enable Setting:", "🔶", "Primaries Only")
    config_panel = Panel(config_table, title="🔩 Configuration Details", border_style="blue", padding=(1, 2))

    # Excluded panel
    excl_content = ""
    for i, node in enumerate(excluded_nodes, 1):
        excl_content += f"[bold red]{i}.[/bold red] [red]{node}[/red]\n"
    excl_panel = Panel(excl_content.rstrip(), title="❌ Excluded Nodes", border_style="red", padding=(1, 2))

    console.print(title_panel)
    print()
    console.print(Columns([status_panel, actions_panel], expand=True))
    print()
    console.print(config_panel)
    print()
    console.print(excl_panel)
    print()


def preview_proposed():
    """Show the PROPOSED condensed 3-panel layout."""
    console.rule("[bold white]PROPOSED LAYOUT (condensed)[/bold white]", style="dim")
    print()

    # ── Title panel (same but subtitle has config info folded in) ──
    subtitle = Text()
    subtitle.append("Status: ", style="default")
    subtitle.append("🔶 Disabled (Primaries Only)", style="yellow")
    subtitle.append(" | Total: ", style="default")
    subtitle.append(str(total_nodes), style="cyan")
    subtitle.append(" | Data: ", style="default")
    subtitle.append(str(data_nodes), style="bright_magenta")
    if excluded_count > 0:
        subtitle.append(" | Excluded: ", style="default")
        subtitle.append(str(excluded_count), style="red")
    subtitle.append(" | Active: ", style="default")
    subtitle.append(str(active_nodes), style="green")

    title_panel = Panel(
        Text("🔀 Elasticsearch Allocation Settings Overview", style="bold cyan", justify="center"),
        subtitle=subtitle,
        border_style="cyan",
        padding=(1, 2),
    )

    # ── Left panel: Status + Config + Exclusions merged ──
    left_table = Table(show_header=False, box=None, padding=(0, 1))
    left_table.add_column("Label", style="bold", no_wrap=True)
    left_table.add_column("Icon", justify="left", width=3)
    left_table.add_column("Value", no_wrap=True)

    left_table.add_row("Allocation Status:", "🔶", "Disabled (Primaries Only)")
    left_table.add_row("Shard Movement:", "🔒", "Primaries Only")
    left_table.add_row("Total Nodes:", "💻", str(total_nodes))
    left_table.add_row("Data Nodes:", "💾", str(data_nodes))
    left_table.add_row("Active Nodes:", "✅", str(active_nodes))
    left_table.add_row("", "", "")  # spacer

    # Fold exclusions inline
    if excluded_nodes:
        left_table.add_row("Excluded Nodes:", "❌", str(excluded_count))
        for node in excluded_nodes:
            left_table.add_row("", "🔴", node)
    else:
        left_table.add_row("Excluded Nodes:", "✅", "None")

    left_panel = Panel(
        left_table,
        title="📊 Allocation Status",
        border_style="yellow",
        padding=(1, 2),
    )

    # ── Right panel: Quick Actions (unchanged) ──
    actions_table = Table(show_header=False, box=None, padding=(0, 1))
    actions_table.add_column("Action", style="bold magenta", no_wrap=True)
    actions_table.add_column("Command", style="dim white")
    actions_table.add_row("Enable allocation:", "./escmd.py allocation enable")
    actions_table.add_row("Disable allocation:", "./escmd.py allocation disable")
    actions_table.add_row("Exclude node:", "./escmd.py allocation exclude add <hostname>")
    actions_table.add_row("Remove exclusion:", "./escmd.py allocation exclude remove <hostname>")
    actions_table.add_row("Reset exclusions:", "./escmd.py allocation exclude reset")
    actions_table.add_row("Explain allocation:", "./escmd.py allocation explain <index>")

    actions_panel = Panel(
        actions_table,
        title="🚀 Quick Actions",
        border_style="magenta",
        padding=(1, 2),
    )

    console.print(title_panel)
    print()
    console.print(Columns([left_panel, actions_panel], expand=True))
    print()


def preview_proposed_no_exclusions():
    """Show proposed layout when there are NO exclusions (cleanest case)."""
    console.rule("[bold white]PROPOSED LAYOUT (no exclusions)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("Status: ", style="default")
    subtitle.append("✅ Enabled (All Shards)", style="green")
    subtitle.append(" | Total: ", style="default")
    subtitle.append(str(total_nodes), style="cyan")
    subtitle.append(" | Data: ", style="default")
    subtitle.append(str(data_nodes), style="bright_magenta")
    subtitle.append(" | Active: ", style="default")
    subtitle.append(str(data_nodes), style="green")

    title_panel = Panel(
        Text("🔀 Elasticsearch Allocation Settings Overview", style="bold cyan", justify="center"),
        subtitle=subtitle,
        border_style="cyan",
        padding=(1, 2),
    )

    left_table = Table(show_header=False, box=None, padding=(0, 1))
    left_table.add_column("Label", style="bold", no_wrap=True)
    left_table.add_column("Icon", justify="left", width=3)
    left_table.add_column("Value", no_wrap=True)

    left_table.add_row("Allocation Status:", "✅", "Enabled (All Shards)")
    left_table.add_row("Shard Movement:", "🔄", "Primary & Replica")
    left_table.add_row("Total Nodes:", "💻", str(total_nodes))
    left_table.add_row("Data Nodes:", "💾", str(data_nodes))
    left_table.add_row("Active Nodes:", "✅", str(data_nodes))
    left_table.add_row("Excluded Nodes:", "✅", "None")

    left_panel = Panel(
        left_table,
        title="📊 Allocation Status",
        border_style="green",
        padding=(1, 2),
    )

    actions_table = Table(show_header=False, box=None, padding=(0, 1))
    actions_table.add_column("Action", style="bold magenta", no_wrap=True)
    actions_table.add_column("Command", style="dim white")
    actions_table.add_row("Enable allocation:", "./escmd.py allocation enable")
    actions_table.add_row("Disable allocation:", "./escmd.py allocation disable")
    actions_table.add_row("Exclude node:", "./escmd.py allocation exclude add <hostname>")
    actions_table.add_row("Remove exclusion:", "./escmd.py allocation exclude remove <hostname>")
    actions_table.add_row("Reset exclusions:", "./escmd.py allocation exclude reset")
    actions_table.add_row("Explain allocation:", "./escmd.py allocation explain <index>")

    actions_panel = Panel(
        actions_table,
        title="🚀 Quick Actions",
        border_style="magenta",
        padding=(1, 2),
    )

    console.print(title_panel)
    print()
    console.print(Columns([left_panel, actions_panel], expand=True))
    print()


if __name__ == "__main__":
    preview_current()
    print()
    preview_proposed()
    print()
    preview_proposed_no_exclusions()
