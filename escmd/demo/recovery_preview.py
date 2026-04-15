#!/usr/bin/env python3
"""
Preview: Recovery command — current vs proposed layout.

Run: python3 demo/recovery_preview.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

console = Console()


# ── NO ACTIVE RECOVERIES ────────────────────────────────────────────

def no_recovery_current():
    console.rule("[bold white]CURRENT: recovery (no active)[/bold white]", style="dim")
    print()
    panel = Panel(
        Text("🎉 No active recovery operations", style="bold green", justify="center"),
        title="[bold white]🔄 Cluster Recovery Status[/bold white]",
        border_style="cyan",
        padding=(2, 4)
    )
    console.print(panel)
    print()


def no_recovery_proposed():
    console.rule("[bold white]PROPOSED: recovery (no active)[/bold white]", style="dim")
    print()
    panel = Panel(
        Text("✅ No Active Recovery Operations", style="bold green", justify="center"),
        title=Text("🔄 Cluster Recovery Status", style="bold bright_magenta"),
        border_style="bright_magenta",
        padding=(1, 2)
    )
    console.print(panel)
    print()


# ── ACTIVE RECOVERIES ───────────────────────────────────────────────

def active_recovery_current():
    console.rule("[bold white]CURRENT: recovery (3 active)[/bold white]", style="dim")
    print()

    # Title panel
    title_panel = Panel(
        Text("🔄 Cluster Recovery Status", style="bold white", justify="center"),
        subtitle="Active recovery operations: 3",
        border_style="cyan",
        padding=(1, 2)
    )

    # Summary panel
    summary_table = Table(show_header=False, box=None, padding=(0, 1))
    summary_table.add_column("Label", style="bold", no_wrap=True)
    summary_table.add_column("Icon", justify="left", width=3)
    summary_table.add_column("Value", no_wrap=True)
    summary_table.add_row("Total Shards:", "📊", "5")
    summary_table.add_row("Active Recoveries:", "🔄", "3")
    summary_table.add_row("Completion Rate:", "✅", "40.0%")
    summary_table.add_row("Recovery Types:", "🔧", "2 peer, 1 existing_store")
    summary_panel = Panel(summary_table, title="[bold white]📈 Recovery Summary[/bold white]", border_style="cyan", padding=(1, 2))

    # Stages panel
    stage_table = Table(show_header=False, box=None, padding=(0, 1))
    stage_table.add_column("Stage", style="bold", no_wrap=True)
    stage_table.add_column("Icon", justify="left", width=3)
    stage_table.add_column("Count", no_wrap=True)
    stage_table.add_row("Translog", "📝", "2")
    stage_table.add_row("Index", "📚", "1")
    stage_panel = Panel(stage_table, title="[bold white]🎯 Recovery Stages[/bold white]", border_style="cyan", padding=(1, 2))

    # Recovery table
    rec_table = Table(show_header=True, header_style="bold white", expand=True, box=None)
    rec_table.add_column("📚 Index", no_wrap=True)
    rec_table.add_column("📋 Shard", justify="center", width=8)
    rec_table.add_column("🎯 Stage", justify="center", width=12)
    rec_table.add_column("📤 Source", no_wrap=True)
    rec_table.add_column("📥 Target", no_wrap=True)
    rec_table.add_column("🔧 Type", justify="center", width=10)
    rec_table.add_column("📊 Progress", justify="center", width=15)
    rec_table.add_row("logs-2026.04.14", "0", "📝 Translog", "node-1", "node-2", "peer", "📊 ██████░░ 75.2%", style="yellow")
    rec_table.add_row("logs-2026.04.14", "1", "📚 Index", "node-2", "node-3", "peer", "📊 ██░░░░░░ 25.0%", style="cyan")
    rec_table.add_row("metrics-001", "0", "📝 Translog", "n/a", "node-1", "existing_store", "📊 █████░░░ 62.5%", style="cyan")
    rec_panel = Panel(rec_table, title="[bold white]🔄 Active Recovery Operations[/bold white]", border_style="cyan", padding=(1, 2))

    console.print(title_panel)
    print()
    console.print(Columns([summary_panel, stage_panel], expand=True))
    print()
    console.print(rec_panel)
    print()


def active_recovery_proposed():
    console.rule("[bold white]PROPOSED: recovery (3 active)[/bold white]", style="dim")
    print()

    # Title panel with status body + stats subtitle
    subtitle = Text()
    subtitle.append("Active: ", style="default")
    subtitle.append("3", style="yellow")
    subtitle.append(" | Total Shards: ", style="default")
    subtitle.append("5", style="cyan")
    subtitle.append(" | Completion: ", style="default")
    subtitle.append("40.0%", style="yellow")
    subtitle.append(" | Types: ", style="default")
    subtitle.append("2 peer", style="bright_magenta")
    subtitle.append(", ", style="default")
    subtitle.append("1 existing_store", style="cyan")

    title_panel = Panel(
        Text("🔶 3 Recovery Operations In Progress", style="bold yellow", justify="center"),
        title=Text("🔄 Cluster Recovery Status", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="yellow",
        padding=(1, 2),
    )

    # Stages + detail side by side
    stage_table = Table(show_header=False, box=None, padding=(0, 1))
    stage_table.add_column("Label", style="bold", no_wrap=True)
    stage_table.add_column("Icon", justify="left", width=3)
    stage_table.add_column("Value", no_wrap=True)
    stage_table.add_row("Translog:", "📝", "2")
    stage_table.add_row("Index:", "📚", "1")
    stage_table.add_row("", "", "")
    stage_table.add_row("Peer Recovery:", "🔄", "2")
    stage_table.add_row("Existing Store:", "💾", "1")
    stage_panel = Panel(stage_table, title="[bold white]🎯 Stages & Types[/bold white]", border_style="bright_magenta", padding=(1, 2))

    # Progress panel
    progress_table = Table(show_header=False, box=None, padding=(0, 1))
    progress_table.add_column("Label", style="bold", no_wrap=True)
    progress_table.add_column("Icon", justify="left", width=3)
    progress_table.add_column("Value", no_wrap=True)
    progress_table.add_row("Fastest:", "🚀", Text("logs-2026.04.14[0] 75.2%", style="green"))
    progress_table.add_row("Slowest:", "🐢", Text("logs-2026.04.14[1] 25.0%", style="yellow"))
    progress_table.add_row("Average:", "📊", Text("54.2%", style="cyan"))
    progress_panel = Panel(progress_table, title="[bold white]📈 Progress[/bold white]", border_style="bright_magenta", padding=(1, 2))

    # Recovery table
    rec_table = Table(show_header=True, header_style="bold white", expand=True, box=None)
    rec_table.add_column("Index", no_wrap=True)
    rec_table.add_column("Shard", justify="center", width=6)
    rec_table.add_column("Stage", justify="center", width=12)
    rec_table.add_column("Source", no_wrap=True)
    rec_table.add_column("Target", no_wrap=True)
    rec_table.add_column("Type", justify="center", width=14)
    rec_table.add_column("Progress", justify="center", width=15)
    rec_table.add_row("logs-2026.04.14", "0", "📝 Translog", "node-1", "node-2", "peer", "██████░░ 75.2%", style="yellow")
    rec_table.add_row("logs-2026.04.14", "1", "📚 Index", "node-2", "node-3", "peer", "██░░░░░░ 25.0%", style="cyan")
    rec_table.add_row("metrics-001", "0", "📝 Translog", "n/a", "node-1", "existing_store", "█████░░░ 62.5%", style="cyan")
    rec_panel = Panel(rec_table, title="[bold white]🔄 Active Recovery Operations[/bold white]", border_style="bright_magenta", padding=(1, 2))

    console.print(title_panel)
    print()
    console.print(Columns([stage_panel, progress_panel], expand=True))
    print()
    console.print(rec_panel)
    print()


if __name__ == "__main__":
    no_recovery_current()
    no_recovery_proposed()
    print()
    active_recovery_current()
    active_recovery_proposed()
