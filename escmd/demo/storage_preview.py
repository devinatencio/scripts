#!/usr/bin/env python3
"""
Preview: ./escmd.py storage — current vs proposed with progress bars.

Run: python3 demo/storage_preview.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def current():
    console.rule("[bold white]CURRENT: storage top panel[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("Nodes: ", style="default")
    subtitle.append("2", style="cyan")
    subtitle.append(" | Indices: ", style="default")
    subtitle.append("247", style="bright_magenta")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("494", style="green")
    subtitle.append(" | Cluster Usage: ", style="default")
    subtitle.append("62.3%", style="green")

    body = Table(show_header=False, box=None, padding=(0, 1))
    body.add_column("Metric", style="bold", no_wrap=True)
    body.add_column("Icon", justify="center", width=4)
    body.add_column("Value", style="bright_cyan")
    body.add_row("Total Nodes:", "💻", "2")
    body.add_row("Total Indices:", "📑", "247")
    body.add_row("Total Shards:", "🔄", "494")
    body.add_row("Cluster Used:", "💾", "1.2 TB")
    body.add_row("Cluster Available:", "🆓", "726.8 GB")
    body.add_row("Cluster Total:", "📦", "1.9 TB")
    body.add_row("Average Usage:", "📊", "62.3%")

    panel = Panel(
        body,
        title="[bold bright_cyan]💾 Elasticsearch Storage Overview[/bold bright_cyan]",
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(1, 2),
    )
    console.print(panel)
    print()


def proposed():
    console.rule("[bold white]PROPOSED: storage top panel (with progress bars)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("Nodes: ", style="default")
    subtitle.append("2", style="cyan")
    subtitle.append(" | Indices: ", style="default")
    subtitle.append("247", style="bright_magenta")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("494", style="green")

    body = Table(show_header=False, box=None, padding=(0, 1))
    body.add_column("Metric", style="bold", no_wrap=True)
    body.add_column("Icon", justify="center", width=3)
    body.add_column("Value")

    # Cluster usage with big progress bar
    usage_pct = 62.3
    bar_width = 20
    filled = int((usage_pct / 100) * bar_width)
    empty = bar_width - filled
    usage_bar = Text()
    usage_bar.append("█" * filled, style="green")
    usage_bar.append("░" * empty, style="dim")
    usage_bar.append(f"  {usage_pct:.1f}%", style="bold green")

    body.add_row("Cluster Usage:", "💾", usage_bar)
    body.add_row("Used:", "📊", Text("1.2 TB", style="green"))
    body.add_row("Available:", "🆓", Text("726.8 GB", style="cyan"))
    body.add_row("Total:", "📦", Text("1.9 TB", style="white"))

    panel = Panel(
        body,
        title=Text("💾 Elasticsearch Storage Overview", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(1, 2),
    )
    console.print(panel)
    print()


def proposed_high():
    console.rule("[bold white]PROPOSED: storage (high usage 85%)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("Nodes: ", style="default")
    subtitle.append("3", style="cyan")
    subtitle.append(" | Indices: ", style="default")
    subtitle.append("512", style="bright_magenta")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("1,024", style="green")
    subtitle.append(" | High: ", style="default")
    subtitle.append("1", style="yellow")

    body = Table(show_header=False, box=None, padding=(0, 1))
    body.add_column("Metric", style="bold", no_wrap=True)
    body.add_column("Icon", justify="center", width=3)
    body.add_column("Value")

    usage_pct = 85.2
    bar_width = 20
    filled = int((usage_pct / 100) * bar_width)
    empty = bar_width - filled
    usage_bar = Text()
    usage_bar.append("█" * filled, style="red")
    usage_bar.append("░" * empty, style="dim")
    usage_bar.append(f"  {usage_pct:.1f}%", style="bold red")

    body.add_row("Cluster Usage:", "💾", usage_bar)
    body.add_row("Used:", "📊", Text("5.1 TB", style="red"))
    body.add_row("Available:", "🆓", Text("892.4 GB", style="yellow"))
    body.add_row("Total:", "📦", Text("5.9 TB", style="white"))

    panel = Panel(
        body,
        title=Text("💾 Elasticsearch Storage Overview", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(panel)
    print()


def proposed_critical():
    console.rule("[bold white]PROPOSED: storage (critical 94%)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("Nodes: ", style="default")
    subtitle.append("3", style="cyan")
    subtitle.append(" | Indices: ", style="default")
    subtitle.append("800", style="bright_magenta")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("1,600", style="green")
    subtitle.append(" | Critical: ", style="default")
    subtitle.append("2", style="red")

    body = Table(show_header=False, box=None, padding=(0, 1))
    body.add_column("Metric", style="bold", no_wrap=True)
    body.add_column("Icon", justify="center", width=3)
    body.add_column("Value")

    usage_pct = 94.1
    bar_width = 20
    filled = int((usage_pct / 100) * bar_width)
    empty = bar_width - filled
    usage_bar = Text()
    usage_bar.append("█" * filled, style="bold red")
    usage_bar.append("░" * empty, style="dim")
    usage_bar.append(f"  {usage_pct:.1f}%", style="bold red")

    body.add_row("Cluster Usage:", "💾", usage_bar)
    body.add_row("Used:", "📊", Text("8.8 TB", style="bold red"))
    body.add_row("Available:", "🆓", Text("551.2 GB", style="red"))
    body.add_row("Total:", "📦", Text("9.4 TB", style="white"))

    panel = Panel(
        body,
        title=Text("💾 Elasticsearch Storage Overview", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="red",
        padding=(1, 2),
    )
    console.print(panel)
    print()


if __name__ == "__main__":
    current()
    proposed()
    proposed_high()
    proposed_critical()
