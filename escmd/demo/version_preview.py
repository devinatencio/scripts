#!/usr/bin/env python3
"""
Preview of enhanced version display with:
- Color-coded system metrics (green/yellow/red thresholds)
- Progress bars for CPU / Memory / Disk
- Gradient ASCII banner
"""

import sys
import platform
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich import box

console = Console()

VERSION = "3.11.1"
DATE = "04/14/2026"

# ── helpers ──────────────────────────────────────────────────────────────────

def _bar(percent: float, width: int = 20) -> Text:
    """Render a compact inline progress bar with threshold colouring."""
    filled = int(percent / 100 * width)
    empty  = width - filled

    if percent < 60:
        colour = "bold green"
    elif percent < 85:
        colour = "bold yellow"
    else:
        colour = "bold red"

    bar = Text()
    bar.append("█" * filled, style=colour)
    bar.append("░" * empty,  style="dim")
    bar.append(f"  {percent:.1f}%", style=colour)
    return bar


def _metric_colour(percent: float) -> str:
    if percent < 60:
        return "bold green"
    elif percent < 85:
        return "bold yellow"
    return "bold red"


# ── banner ────────────────────────────────────────────────────────────────────

def render_banner():
    letters = [
        " ███████╗███████╗████████╗███████╗██████╗ ███╗   ███╗",
        " ██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║",
        " █████╗  ███████╗   ██║   █████╗  ██████╔╝██╔████╔██║",
        " ██╔══╝  ╚════██║   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║",
        " ███████╗███████║   ██║   ███████╗██║  ██║██║ ╚═╝ ██║",
        " ╚══════╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝",
    ]
    colours = ["bold cyan", "bold cyan", "bold blue", "bold blue", "bold magenta", "bold magenta"]
    banner = Text()
    for line, colour in zip(letters, colours):
        banner.append(line + "\n", style=colour)
    console.print(Align.center(banner))
    console.print(
        Align.center(
            Text("⚡  Elasticsearch Terminal  ⚡", style="bold white on dark_blue")
        )
    )
    console.print()


# ── main info panel ───────────────────────────────────────────────────────────

def render_info_panel():
    left = Table.grid(padding=(0, 2))
    left.add_column(style="bold cyan",  no_wrap=True, min_width=14)
    left.add_column(style="white")

    left.add_row("🚀 Tool",     "[bold white]Elasticsearch Terminal (ESTERM)[/bold white]")
    left.add_row("📦 Version",  f"[bold green]{VERSION}[/bold green]")
    left.add_row("📅 Released", f"[bold cyan]{DATE}[/bold cyan]")
    left.add_row("🎯 Purpose",  "Advanced ES CLI Management & Monitoring")
    left.add_row("👥 Team",     "Monitoring Team US")
    left.add_row("🐍 Python",   f"[dim]{sys.version.split()[0]}[/dim]")
    left.add_row("💻 Platform", f"[dim]{platform.system()} {platform.machine()}[/dim]")

    right = Table.grid(padding=(0, 2))
    right.add_column(style="bold magenta", no_wrap=True, min_width=12)
    right.add_column()

    right.add_row("📑 Indices",   "[bold green]✔[/bold green] manage, freeze, reindex")
    right.add_row("🔄 ILM",       "[bold green]✔[/bold green] policies, rollover, phases")
    right.add_row("📸 Snapshots", "[bold green]✔[/bold green] create, restore, repos")
    right.add_row("🏥 Health",    "[bold green]✔[/bold green] cluster, nodes, shards")
    right.add_row("🔩 Settings",  "[bold green]✔[/bold green] cluster & index settings")
    right.add_row("🎨 Themes",    "[bold green]✔[/bold green] rich UI, colour schemes")
    right.add_row("📋 Export",    "[bold green]✔[/bold green] JSON, table, CSV")

    cols = Columns([
        Panel(left,  title="[bold white]ℹ  Info[/bold white]",        border_style="cyan",    padding=(1,2)),
        Panel(right, title="[bold white]🧰  Capabilities[/bold white]", border_style="magenta", padding=(1,2)),
    ], equal=True, expand=True)

    console.print(
        Panel(cols,
              title=f"[bold yellow]⚡ ESCMD v{VERSION}[/bold yellow]",
              subtitle="[dim]Interactive Elasticsearch Command Line Interface[/dim]",
              border_style="yellow",
              padding=(0, 1))
    )


# ── system metrics panel ──────────────────────────────────────────────────────

def render_metrics_panel():
    try:
        import psutil
        cpu  = psutil.cpu_percent(interval=0.1)
        mem  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        rows = [
            ("💻 CPU",    cpu,       None,                    None),
            ("🧠 Memory", mem.percent,
             f"[dim]{mem.available//(1024**3)} GB free[/dim]", None),
            ("💾 Disk",   disk.percent,
             f"[dim]{disk.free//(1024**3)} GB free[/dim]",    None),
        ]

        t = Table.grid(padding=(0, 2))
        t.add_column(style="bold white",  no_wrap=True, min_width=12)
        t.add_column(min_width=28)
        t.add_column(style="dim")

        for label, pct, extra, _ in rows:
            bar  = _bar(pct)
            note = extra or ""
            t.add_row(label, bar, note)

        t.add_row("", "", "")
        t.add_row(
            "🕐 Time",
            Text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style="bold white"),
            ""
        )

    except ImportError:
        t = Text("Install [bold]psutil[/bold] for live metrics", style="dim")

    console.print(
        Panel(Align.center(t),
              title="[bold white]⚡ Performance & System[/bold white]",
              border_style="green",
              padding=(1, 2))
    )


# ── footer ────────────────────────────────────────────────────────────────────

def render_footer():
    t = Text(justify="center")
    t.append("💡 ", style="bold yellow")
    t.append("Quick Start: ", style="bold white")
    t.append("./esterm", style="bold cyan")
    t.append("  for interactive mode  │  ", style="dim")
    t.append("./escmd.py help", style="bold cyan")
    t.append("  for command reference", style="dim")

    console.print(Panel(Align.center(t), border_style="dim", padding=(0, 2)))


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    console.print()
    render_banner()
    render_info_panel()
    console.print()
    render_metrics_panel()
    console.print()
    render_footer()
    console.print()
