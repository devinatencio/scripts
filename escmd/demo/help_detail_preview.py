#!/usr/bin/env python3
"""
Preview of enhanced ./escmd.py help health detailed screen.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.align import Align
from rich.text import Text
from rich.rule import Rule

console = Console()

# ── 1. topic header ───────────────────────────────────────────────────────────

def render_header():
    t = Text()
    t.append(" health ", style="bold black on green")
    t.append("  Cluster health monitoring options", style="white")
    t.append("   ", style="")
    t.append("./escmd.py help health", style="dim cyan")

    console.print()
    console.print(Panel(t, border_style="green", padding=(0, 2)))
    console.print()


# ── 2. merged commands + examples table ──────────────────────────────────────

def render_commands():
    tbl = Table(
        expand=True,
        show_header=True,
        header_style="bold white on grey23",
        border_style="grey23",
        row_styles=["", "on grey7"],
        show_lines=False,
        pad_edge=True,
        padding=(0, 1),
    )
    tbl.add_column("Command",     style="bold cyan",  no_wrap=True, min_width=36)
    tbl.add_column("Description", style="white")
    tbl.add_column("Example",     style="dim cyan",   no_wrap=True)

    rows = [
        ("health",                          "Quick cluster health check",          "./escmd.py health"),
        ("health --compare <cluster>",      "Compare with another cluster",        "./escmd.py health --compare prod"),
        ("health --group <prefix>",         "Group clusters by prefix",            "./escmd.py health --group us"),
        ("health --format json",            "Machine-readable JSON output",        "./escmd.py health --format json"),
        ("health-detail",                   "Full health dashboard",               "./escmd.py health-detail"),
        ("health-detail --style dashboard", "Modern dashboard view",               "./escmd.py health-detail --style dashboard"),
        ("health-detail --style classic",   "Traditional table format",            "./escmd.py health-detail --style classic"),
    ]
    for cmd, desc, example in rows:
        tbl.add_row(cmd, desc, example)

    console.print(Panel(
        tbl,
        title="[bold white]📋 Commands & Examples[/bold white]",
        border_style="dim",
        padding=(0, 0),
    ))
    console.print()


# ── 3. workflow scenario cards ────────────────────────────────────────────────

SCENARIOS = [
    (
        "🚨 Incident Response",
        "green",
        "Quick cluster status during an outage",
        [
            ("Check status",   "./escmd.py health"),
            ("Full detail",    "./escmd.py health-detail"),
            ("JSON for alert", "./escmd.py health --format json"),
        ],
    ),
    (
        "📊 Daily Monitoring",
        "blue",
        "Regular health checks and automation",
        [
            ("Morning check",  "./escmd.py health-detail"),
            ("Cron / CI",      "./escmd.py health --format json | monitor.py"),
            ("Group view",     "./escmd.py health --group prod"),
        ],
    ),
    (
        "🔄 Multi-Cluster Ops",
        "yellow",
        "Managing and comparing multiple environments",
        [
            ("Compare two",    "./escmd.py health --compare staging"),
            ("Group by region","./escmd.py health --group us"),
            ("All clusters",   "./escmd.py locations && ./escmd.py health"),
        ],
    ),
]

def render_workflows():
    # Build scenario panels stacked full-width
    for title, colour, subtitle, steps in SCENARIOS:
        t = Table.grid(padding=(0, 2))
        t.add_column(style="dim",       no_wrap=True, min_width=18)
        t.add_column(style="bold cyan", no_wrap=True)

        t.add_row(Text(subtitle, style="dim italic"), Text(""))
        t.add_row(Text(""), Text(""))
        for label, cmd in steps:
            t.add_row(Text(label, style="dim"), Text(cmd, style=f"bold {colour}"))

        console.print(Panel(t,
            title=f"[bold {colour}]{title}[/bold {colour}]",
            border_style=colour, padding=(0, 2),
        ))


# ── 4. slim footer ────────────────────────────────────────────────────────────

def render_footer():
    t = Text(justify="center")
    t.append("./escmd.py help", style="bold cyan")
    t.append("  back to topic list  ·  ", style="dim")
    t.append("-l <cluster>", style="bold cyan")
    t.append("  target a specific cluster  ·  ", style="dim")
    t.append("--format json", style="bold cyan")
    t.append("  machine output", style="dim")
    console.print(Panel(Align.center(t), border_style="dim", padding=(0, 1)))
    console.print()


if __name__ == "__main__":
    render_header()
    render_commands()
    render_workflows()
    render_footer()
