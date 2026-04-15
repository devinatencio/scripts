#!/usr/bin/env python3
"""
Preview: ./escmd.py repositories — current vs proposed layout.

Run: python3 demo/repositories_preview.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


# ── CURRENT LAYOUT ──────────────────────────────────────────────────

def current_with_repos():
    console.rule("[bold white]CURRENT: repositories (2 repos)[/bold white]", style="dim")
    print()

    # Title panel
    subtitle = Text()
    subtitle.append("Total Repositories: ", style="default")
    subtitle.append("2", style="cyan")
    subtitle.append(" | Types: ", style="default")
    subtitle.append("S3: 1 • FS: 1", style="bright_magenta")
    subtitle.append(" | Status: ", style="default")
    subtitle.append("Good backup coverage", style="green")

    title_panel = Panel(
        Text("📦 Elasticsearch Snapshot Repositories", style="bold bright_cyan", justify="center"),
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(1, 2),
    )

    # Table with redundant title
    table = Table(show_header=True, header_style="bold white", expand=True, title="📦 Repository Details", title_style="bold bright_cyan")
    table.add_column("📦 Repository Name", width=20)
    table.add_column("🔧 Type", justify="center", width=12)
    table.add_column("📍 Location/Bucket", width=30)
    table.add_column("🔩 Settings", width=35)
    table.add_column("🎯 Status", justify="center", width=12)
    table.add_row("prod-backups", "S3", "s3://my-es-backups/prod", "compress: true, chunk: 1gb", "✅ Active")
    table.add_row("local-snapshots", "FS", "/mnt/snapshots/es-data", "compress: true", "✅ Active")

    # Summary panel (redundant)
    summary = Table(show_header=False, box=None, padding=(0, 1))
    summary.add_column("Metric", style="bold", no_wrap=True)
    summary.add_column("Icon", justify="center", width=4)
    summary.add_column("Value", style="bright_cyan")
    summary.add_row("Total Repositories:", "📦", "2")
    summary.add_row("S3 Repositories:", "☁️", "1")
    summary.add_row("FS Repositories:", "💾", "1")
    summary_panel = Panel(summary, title="📈 Repository Summary", border_style="magenta", padding=(1, 2))

    console.print(title_panel)
    print()
    console.print(table)
    print()
    console.print(summary_panel)
    print()


def current_empty():
    console.rule("[bold white]CURRENT: repositories (empty)[/bold white]", style="dim")
    print()

    panel = Panel(
        Text.from_markup(
            "💡 No snapshot repositories are currently configured.\n\n"
            "Repositories are required for creating backups of your Elasticsearch data.\n"
            "Common repository types include:\n"
            "• [cyan]S3[/cyan] - Amazon S3 storage\n"
            "• [cyan]GCS[/cyan] - Google Cloud Storage\n"
            "• [cyan]Azure[/cyan] - Azure Blob Storage\n"
            "• [cyan]FS[/cyan] - Local filesystem\n\n"
            "[bold green]💡 Quick Start:[/bold green]\n"
            "Create a repository using: [cyan]./escmd.py repositories create <name> --type <type>[/cyan]\n",
            justify="left"
        ),
        title="📦 Snapshot Repositories",
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(panel)
    print()


# ── PROPOSED LAYOUT ─────────────────────────────────────────────────

def proposed_with_repos():
    console.rule("[bold white]PROPOSED: repositories (2 repos)[/bold white]", style="dim")
    print()

    # Title panel — standard pattern
    subtitle = Text()
    subtitle.append("Total: ", style="default")
    subtitle.append("2", style="cyan")
    subtitle.append(" | S3: ", style="default")
    subtitle.append("1", style="bright_magenta")
    subtitle.append(" | FS: ", style="default")
    subtitle.append("1", style="bright_magenta")

    title_panel = Panel(
        Text("✅ Good Backup Coverage - 2 Repositories Configured", style="bold green", justify="center"),
        title=Text("📦 Snapshot Repositories", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(1, 2),
    )

    # Table — no redundant title
    table = Table(show_header=True, header_style="bold white", expand=True)
    table.add_column("Repository Name", width=20)
    table.add_column("Type", justify="center", width=12)
    table.add_column("Location/Bucket", width=30)
    table.add_column("Settings", width=35)
    table.add_column("Status", justify="center", width=12)
    table.add_row("prod-backups", "S3", "s3://my-es-backups/prod", "compress: true, chunk: 1gb", "✅ Active")
    table.add_row("local-snapshots", "FS", "/mnt/snapshots/es-data", "compress: true", "✅ Active")

    console.print(title_panel)
    print()
    console.print(table)
    print()


def proposed_single_repo():
    console.rule("[bold white]PROPOSED: repositories (1 repo — limited)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("Total: ", style="default")
    subtitle.append("1", style="cyan")
    subtitle.append(" | S3: ", style="default")
    subtitle.append("1", style="bright_magenta")

    title_panel = Panel(
        Text("🔶 Limited Redundancy - 1 Repository Configured", style="bold yellow", justify="center"),
        title=Text("📦 Snapshot Repositories", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="yellow",
        padding=(1, 2),
    )

    table = Table(show_header=True, header_style="bold white", expand=True)
    table.add_column("Repository Name", width=20)
    table.add_column("Type", justify="center", width=12)
    table.add_column("Location/Bucket", width=30)
    table.add_column("Settings", width=35)
    table.add_column("Status", justify="center", width=12)
    table.add_row("prod-backups", "S3", "s3://my-es-backups/prod", "compress: true, chunk: 1gb", "✅ Active")

    console.print(title_panel)
    print()
    console.print(table)
    print()


def proposed_empty():
    console.rule("[bold white]PROPOSED: repositories (empty)[/bold white]", style="dim")
    print()

    panel = Panel(
        Text.from_markup(
            "No snapshot repositories are currently configured.\n\n"
            "[bold]Common repository types:[/bold]\n"
            "  • [cyan]S3[/cyan] - Amazon S3    • [cyan]GCS[/cyan] - Google Cloud    • [cyan]Azure[/cyan] - Azure Blob    • [cyan]FS[/cyan] - Local filesystem\n\n"
            "[bold]Quick Start:[/bold]\n"
            "  [cyan]./escmd.py repositories create my-repo --type s3 --bucket my-backups[/cyan]",
            justify="left"
        ),
        title=Text("📦 Snapshot Repositories", style="bold bright_magenta"),
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(panel)
    print()


if __name__ == "__main__":
    current_with_repos()
    current_empty()
    print()
    proposed_with_repos()
    proposed_single_repo()
    proposed_empty()
