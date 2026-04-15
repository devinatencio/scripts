#!/usr/bin/env python3
"""
Preview: Allocation explain with condensed shard overview.

Shows the proposed layout adding shard totals/states/distribution
to the allocation explain screen in a condensed format.

Run: python3 demo/allocation_explain_preview.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

console = Console()


def preview_current():
    """Current allocation explain layout (no shard info)."""
    console.rule("[bold white]CURRENT: allocation explain mylog[/bold white]", style="dim")
    print()

    # Title
    subtitle = Text()
    subtitle.append("Index: ", style="default")
    subtitle.append("mylog", style="cyan")
    subtitle.append(" | Shard: ", style="default")
    subtitle.append("0", style="bright_magenta")
    subtitle.append(" | Type: ", style="default")
    subtitle.append("Replica", style="magenta")
    subtitle.append(" | Status: ", style="default")
    subtitle.append("❌ Unassigned", style="red")
    subtitle.append(" | Nodes: ", style="default")
    subtitle.append("1", style="cyan")

    title_panel = Panel(
        Text("🔍 Allocation Explain: mylog [shard 0] (replica)", style="bold cyan", justify="center"),
        subtitle=subtitle,
        border_style="cyan",
        padding=(1, 2),
    )

    # Allocation Detail (left)
    alloc_table = Table(show_header=False, box=None, padding=(0, 1))
    alloc_table.add_column("Label", style="bold", no_wrap=True)
    alloc_table.add_column("Icon", justify="left", width=3)
    alloc_table.add_column("Value", no_wrap=True)
    alloc_table.add_row("Status:", "❌", "Unassigned")
    alloc_table.add_row("Can Allocate:", "🔀", "no")
    alloc_table.add_row("Explanation:", "📝", "cannot allocate because allocation is not permitted to any of the nodes")
    alloc_table.add_row("Reason:", "📋", "REPLICA_ADDED")
    alloc_table.add_row("Last Status:", "🔄", "no_attempt")
    alloc_table.add_row("Since:", "🕐", "2026-04-14T22:16:11.554Z")
    alloc_panel = Panel(alloc_table, title="📊 Allocation Detail", border_style="yellow", padding=(1, 2))

    # Summary (right)
    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Label", style="bold", no_wrap=True)
    summary_table.add_column("Icon", justify="left", width=3)
    summary_table.add_column("Value", no_wrap=True)
    summary_table.add_row("Nodes Evaluated:", "💻", "1")
    summary_table.add_row("Nodes Available:", "💾", "1")
    summary_table.add_row("Allocation Possible:", "❌", "No")
    summary_table.add_row("Recommendation:", "💡", "Check cluster allocation settings")
    summary_table.add_row("Analyzed At:", "🕐", "2026-04-14T19:39:32.17")
    summary_panel = Panel(summary_table, title="📋 Summary", border_style="yellow", padding=(1, 2))

    # Decisions
    dec_table = Table(show_header=True, box=None, padding=(0, 1), expand=True)
    dec_table.add_column("Node", style="bold", no_wrap=True)
    dec_table.add_column("Transport", style="dim", no_wrap=True)
    dec_table.add_column("Decision", no_wrap=True)
    dec_table.add_column("Weight", justify="right", no_wrap=True)
    dec_table.add_column("Deciders", ratio=1)
    dec_table.add_row("node-1", "192.168.12.202:9300", Text("No", style="red"), "0",
                       "NO  same_shard: a copy of this shard is already allocated to this node [[0], node, [P], s[STARTED], a]")
    dec_panel = Panel(dec_table, title="🔀 Node Allocation Decisions", border_style="blue", padding=(1, 2))

    console.print(title_panel)
    print()
    console.print(Columns([alloc_panel, summary_panel], expand=True))
    print()
    console.print(dec_panel)
    print()


def preview_proposed():
    """Proposed layout with condensed shard overview added."""
    console.rule("[bold white]PROPOSED: allocation explain mylog (with shard overview)[/bold white]", style="dim")
    print()

    # Title - now includes shard health summary in subtitle
    subtitle = Text()
    subtitle.append("Index: ", style="default")
    subtitle.append("mylog", style="cyan")
    subtitle.append(" | Health: ", style="default")
    subtitle.append("🟡 Yellow", style="yellow")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("1p", style="bright_magenta")
    subtitle.append("/", style="default")
    subtitle.append("1r", style="blue")
    subtitle.append(" | Started: ", style="default")
    subtitle.append("1", style="green")
    subtitle.append(" | Unassigned: ", style="default")
    subtitle.append("1", style="red")

    title_panel = Panel(
        Text("🔍 Allocation Explain: mylog [shard 0] (replica)", style="bold cyan", justify="center"),
        subtitle=subtitle,
        border_style="cyan",
        padding=(1, 2),
    )

    # Allocation Detail (left) - unchanged
    alloc_table = Table(show_header=False, box=None, padding=(0, 1))
    alloc_table.add_column("Label", style="bold", no_wrap=True)
    alloc_table.add_column("Icon", justify="left", width=3)
    alloc_table.add_column("Value", no_wrap=True)
    alloc_table.add_row("Status:", "❌", "Unassigned")
    alloc_table.add_row("Can Allocate:", "🔀", "no")
    alloc_table.add_row("Explanation:", "📝", "cannot allocate because allocation is not permitted to any of the nodes")
    alloc_table.add_row("Reason:", "📋", "REPLICA_ADDED")
    alloc_table.add_row("Last Status:", "🔄", "no_attempt")
    alloc_table.add_row("Since:", "🕐", "2026-04-14T22:16:11.554Z")
    alloc_panel = Panel(alloc_table, title="📊 Allocation Detail", border_style="yellow", padding=(1, 2))

    # Summary (right) - now includes shard breakdown
    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Label", style="bold", no_wrap=True)
    summary_table.add_column("Icon", justify="left", width=3)
    summary_table.add_column("Value", no_wrap=True)
    summary_table.add_row("Nodes Evaluated:", "💻", "1")
    summary_table.add_row("Nodes Available:", "💾", "1")
    summary_table.add_row("Allocation Possible:", "❌", "No")
    summary_table.add_row("Recommendation:", "💡", "Check cluster allocation settings")
    summary_table.add_row("", "", "")
    summary_table.add_row("Total Shards:", "📊", "2")
    summary_table.add_row("Primary:", "🔑", Text("1 Started", style="green"))
    summary_table.add_row("Replica:", "📋", Text("1 Unassigned", style="red"))
    summary_table.add_row("Node:", "💻", "node-1 (1 shard)")
    summary_panel = Panel(summary_table, title="📋 Summary & Shards", border_style="yellow", padding=(1, 2))

    # Decisions - unchanged
    dec_table = Table(show_header=True, box=None, padding=(0, 1), expand=True)
    dec_table.add_column("Node", style="bold", no_wrap=True)
    dec_table.add_column("Transport", style="dim", no_wrap=True)
    dec_table.add_column("Decision", no_wrap=True)
    dec_table.add_column("Weight", justify="right", no_wrap=True)
    dec_table.add_column("Deciders", ratio=1)
    dec_table.add_row("node-1", "192.168.12.202:9300", Text("No", style="red"), "0",
                       "NO  same_shard: a copy of this shard is already allocated to this node [[0], node, [P], s[STARTED], a]")
    dec_panel = Panel(dec_table, title="🔀 Node Allocation Decisions", border_style="blue", padding=(1, 2))

    console.print(title_panel)
    print()
    console.print(Columns([alloc_panel, summary_panel], expand=True))
    print()
    console.print(dec_panel)
    print()


def preview_proposed_green():
    """Proposed layout for a healthy green index."""
    console.rule("[bold white]PROPOSED: allocation explain greenlog (healthy index)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("Index: ", style="default")
    subtitle.append("greenlog", style="cyan")
    subtitle.append(" | Health: ", style="default")
    subtitle.append("🟢 Green", style="green")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("1p", style="bright_magenta")
    subtitle.append("/", style="default")
    subtitle.append("1r", style="blue")
    subtitle.append(" | Started: ", style="default")
    subtitle.append("2", style="green")

    title_panel = Panel(
        Text("🔍 Allocation Explain: greenlog [shard 0] (primary)", style="bold cyan", justify="center"),
        subtitle=subtitle,
        border_style="cyan",
        padding=(1, 2),
    )

    alloc_table = Table(show_header=False, box=None, padding=(0, 1))
    alloc_table.add_column("Label", style="bold", no_wrap=True)
    alloc_table.add_column("Icon", justify="left", width=3)
    alloc_table.add_column("Value", no_wrap=True)
    alloc_table.add_row("Status:", "✅", "Allocated")
    alloc_table.add_row("Node:", "💻", "node-1")
    alloc_table.add_row("Node ID:", "🔑", "bGJvsr-xQGOcPs_WxBsfxw")
    alloc_table.add_row("Weight Ranking:", "📈", "1")
    alloc_table.add_row("Can Remain:", "🔒", "yes")
    alloc_panel = Panel(alloc_table, title="📊 Allocation Detail", border_style="green", padding=(1, 2))

    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Label", style="bold", no_wrap=True)
    summary_table.add_column("Icon", justify="left", width=3)
    summary_table.add_column("Value", no_wrap=True)
    summary_table.add_row("Nodes Evaluated:", "💻", "1")
    summary_table.add_row("Nodes Available:", "💾", "1")
    summary_table.add_row("Allocation Possible:", "✅", "Yes")
    summary_table.add_row("Recommendation:", "💡", "Shard is successfully allocated")
    summary_table.add_row("", "", "")
    summary_table.add_row("Total Shards:", "📊", "2")
    summary_table.add_row("Primary:", "🔑", Text("1 Started", style="green"))
    summary_table.add_row("Replica:", "📋", Text("1 Started", style="green"))
    summary_table.add_row("Node:", "💻", "node-1 (2 shards)")
    summary_panel = Panel(summary_table, title="📋 Summary & Shards", border_style="green", padding=(1, 2))

    console.print(title_panel)
    print()
    console.print(Columns([alloc_panel, summary_panel], expand=True))
    print()


if __name__ == "__main__":
    preview_current()
    print()
    preview_proposed()
    print()
    preview_proposed_green()
