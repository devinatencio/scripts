#!/usr/bin/env python3
"""
Preview: Indices and Nodes top panels — current vs proposed (matching shards/allocation standard).

The standard pattern (shards, allocation, ping, indices-analyze):
  - Title bar: command name with themed primary style
  - Body: status text centered with health-aware color
  - Subtitle bar: themed stats with semantic colors

Run: python3 demo/indices_nodes_header_preview.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


# ── INDICES ──────────────────────────────────────────────────────────

def indices_current():
    console.rule("[bold white]CURRENT: indices header[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("my-cluster", style="cyan")
    subtitle.append("  ", style="default")
    subtitle.append("v8.17.0", style="dim")
    subtitle.append("   ", style="default")
    subtitle.append("Total: ", style="default")
    subtitle.append("247", style="cyan")
    subtitle.append(" | Green: ", style="default")
    subtitle.append("245", style="green")
    subtitle.append(" | Yellow: ", style="default")
    subtitle.append("2", style="yellow")
    subtitle.append(" | Red: ", style="default")
    subtitle.append("0", style="red")
    subtitle.append(" | Hot: ", style="default")
    subtitle.append("12", style="bright_magenta")

    title_panel = Panel(
        "",
        title=Text("📊 Elasticsearch Indices", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(0, 2),
    )
    console.print(title_panel)
    print()


def indices_proposed():
    console.rule("[bold white]PROPOSED: indices header (matching standard)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("my-cluster", style="cyan")
    subtitle.append("  ", style="default")
    subtitle.append("v8.17.0", style="dim")
    subtitle.append("   ", style="default")
    subtitle.append("Total: ", style="default")
    subtitle.append("247", style="cyan")
    subtitle.append(" | Green: ", style="default")
    subtitle.append("245", style="green")
    subtitle.append(" | Yellow: ", style="default")
    subtitle.append("2", style="yellow")
    subtitle.append(" | Red: ", style="default")
    subtitle.append("0", style="red")
    subtitle.append(" | Hot: ", style="default")
    subtitle.append("12", style="bright_magenta")

    title_panel = Panel(
        Text("✅ Cluster Healthy - 245 of 247 Indices Green", style="bold green", justify="center"),
        title=Text("📊 Elasticsearch Indices", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(1, 2),
    )
    console.print(title_panel)
    print()


def indices_proposed_yellow():
    console.rule("[bold white]PROPOSED: indices header (yellow cluster)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("my-cluster", style="cyan")
    subtitle.append("  ", style="default")
    subtitle.append("v8.17.0", style="dim")
    subtitle.append("   ", style="default")
    subtitle.append("Total: ", style="default")
    subtitle.append("247", style="cyan")
    subtitle.append(" | Green: ", style="default")
    subtitle.append("230", style="green")
    subtitle.append(" | Yellow: ", style="default")
    subtitle.append("17", style="yellow")
    subtitle.append(" | Red: ", style="default")
    subtitle.append("0", style="red")

    title_panel = Panel(
        Text("🟡 Warning - 17 Indices Yellow", style="bold yellow", justify="center"),
        title=Text("📊 Elasticsearch Indices", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(title_panel)
    print()


# ── NODES ────────────────────────────────────────────────────────────

def nodes_current():
    console.rule("[bold white]CURRENT: nodes header[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("my-cluster", style="cyan")
    subtitle.append("  ", style="default")
    subtitle.append("v8.17.0", style="dim")
    subtitle.append("   ", style="default")
    subtitle.append("Total: ", style="default")
    subtitle.append("3", style="cyan")
    subtitle.append(" | Health: ", style="default")
    subtitle.append("GREEN ✅", style="green")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("494 active", style="green")
    subtitle.append(" | Master: ", style="default")
    subtitle.append("1", style="bright_magenta")
    subtitle.append(" | Data: ", style="default")
    subtitle.append("2", style="green")
    subtitle.append(" | Ingest: ", style="default")
    subtitle.append("3", style="cyan")

    title_panel = Panel(
        "",
        title=Text("💻 Elasticsearch Nodes", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(0, 2),
    )
    console.print(title_panel)
    print()


def nodes_proposed():
    console.rule("[bold white]PROPOSED: nodes header (matching standard)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("my-cluster", style="cyan")
    subtitle.append("  ", style="default")
    subtitle.append("v8.17.0", style="dim")
    subtitle.append("   ", style="default")
    subtitle.append("Total: ", style="default")
    subtitle.append("3", style="cyan")
    subtitle.append(" | Master: ", style="default")
    subtitle.append("1", style="bright_magenta")
    subtitle.append(" | Data: ", style="default")
    subtitle.append("2", style="green")
    subtitle.append(" | Ingest: ", style="default")
    subtitle.append("3", style="cyan")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("494", style="green")

    title_panel = Panel(
        Text("🟢 All Nodes Healthy - 3 Nodes Online", style="bold green", justify="center"),
        title=Text("💻 Elasticsearch Nodes", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(1, 2),
    )
    console.print(title_panel)
    print()


def nodes_proposed_yellow():
    console.rule("[bold white]PROPOSED: nodes header (yellow cluster)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("my-cluster", style="cyan")
    subtitle.append("  ", style="default")
    subtitle.append("v8.17.0", style="dim")
    subtitle.append("   ", style="default")
    subtitle.append("Total: ", style="default")
    subtitle.append("3", style="cyan")
    subtitle.append(" | Master: ", style="default")
    subtitle.append("1", style="bright_magenta")
    subtitle.append(" | Data: ", style="default")
    subtitle.append("2", style="green")
    subtitle.append(" | Ingest: ", style="default")
    subtitle.append("3", style="cyan")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("490 active", style="green")
    subtitle.append(" | ", style="default")
    subtitle.append("4 unassigned", style="red")

    title_panel = Panel(
        Text("🟡 Warning - 4 Unassigned Shards", style="bold yellow", justify="center"),
        title=Text("💻 Elasticsearch Nodes", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(title_panel)
    print()


if __name__ == "__main__":
    indices_current()
    indices_proposed()
    indices_proposed_yellow()
    print()
    nodes_current()
    nodes_proposed()
    nodes_proposed_yellow()
