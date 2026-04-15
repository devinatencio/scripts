#!/usr/bin/env python3
"""
Preview of enhanced no-args welcome screen - uniform grid layout.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.align import Align
from rich.text import Text

console = Console()
VERSION = "3.12.0"

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
    colours = ["bold cyan","bold cyan","bold blue","bold blue","bold magenta","bold magenta"]
    banner = Text()
    for line, colour in zip(letters, colours):
        banner.append(line + "\n", style=colour)
    console.print(Align.center(banner))
    console.print(Align.center(Text(
        f"v{VERSION}  ·  Elasticsearch CLI Management & Monitoring", style="dim"
    )))
    console.print()


# ── status bar ────────────────────────────────────────────────────────────────

def render_status_bar():
    default_cluster = "sjc01-prod"
    bar = Text()
    if default_cluster:
        bar.append("  🟢 Active cluster: ", style="bold green")
        bar.append(default_cluster, style="bold white")
        bar.append("   change with ", style="dim")
        bar.append("./escmd.py set-default <name>", style="dim cyan")
    else:
        bar.append("  ⚠  No default cluster — run ", style="bold yellow")
        bar.append("./escmd.py set-default <name>", style="bold cyan")
    console.print(Panel(bar, border_style="dim", padding=(0, 1)))
    console.print()


# ── category data ─────────────────────────────────────────────────────────────
# Organized into 3 balanced rows of 3 — each row has similar total line counts

CATEGORIES = [
    # ── row 1 ──
    ("🏥 Cluster & Health", "green", [
        ("health",          "Cluster health"),
        ("health-detail",   "Full health dashboard"),
        ("cluster-check",   "Comprehensive checks"),
        ("ping",            "Test connectivity"),
        ("nodes",           "List nodes"),
        ("masters",         "Master nodes"),
        ("current-master",  "Active master"),
        ("recovery",        "Recovery jobs"),
    ]),
    ("📑 Index Management", "blue", [
        ("indices",         "List indices"),
        ("indice",          "Single index detail"),
        ("create-index",    "Create index"),
        ("freeze/unfreeze", "Freeze or unfreeze"),
        ("flush",           "Flush index"),
        ("set-replicas",    "Set replica count"),
        ("templates",       "List templates"),
        ("dangling",        "Dangling indices"),
    ]),
    ("💾 Storage & Shards", "cyan", [
        ("storage",          "Disk usage"),
        ("shards",           "Shard distribution"),
        ("shard-colocation", "Primary/replica on same host"),
        ("allocation",       "Allocation settings"),
        ("exclude",          "Exclude from host"),
        ("exclude-reset",    "Reset exclusion"),
        ("snapshots",        "Manage snapshots"),
        ("repositories",     "Snapshot repos"),
    ]),
    # ── row 2 ──
    ("🔄 ILM & Lifecycle", "yellow", [
        ("ilm",          "ILM policies"),
        ("datastreams",  "Datastream list"),
        ("rollover",     "Rollover datastream"),
        ("auto-rollover","Rollover biggest shard"),
        ("es-top",       "Live cluster dashboard"),
        ("action",       "Action sequences"),
    ]),
    ("🔩 Settings & Config", "white", [
        ("cluster-settings", "Cluster settings"),
        ("set",              "Set setting (dot notation)"),
        ("show-settings",    "Current config"),
        ("locations",        "Configured clusters"),
        ("get-default",      "Show default cluster"),
        ("set-default",      "Change default cluster"),
    ]),
    ("🛠  Utilities", "bright_black", [
        ("version",            "Version & system info"),
        ("themes / set-theme", "Browse or change theme"),
        ("help",               "Detailed help"),
        ("store-password",     "Store encrypted password"),
        ("list-stored-passwords", "List stored passwords"),
        ("show-settings",      "Current config"),
    ]),
]


# ── uniform grid ──────────────────────────────────────────────────────────────

def _make_table(commands, colour):
    t = Table.grid(padding=(0, 2))
    t.add_column(style=f"bold {colour}", no_wrap=True, min_width=22)
    t.add_column(style="dim", min_width=28)
    for cmd, desc in commands:
        t.add_row(cmd, desc)
    return t


def render_grid():
    # Two uniform 3-column rows, panels padded to equal height per row
    for row_cats in [CATEGORIES[0:3], CATEGORIES[3:6]]:
        max_cmds = max(len(c[2]) for c in row_cats)
        panels = []
        for title, colour, commands in row_cats:
            padded = commands + [("", "")] * (max_cmds - len(commands))
            panels.append(Panel(
                _make_table(padded, colour),
                title=f"[bold {colour}]{title}[/bold {colour}]",
                border_style=colour,
                padding=(0, 1),
            ))
        console.print(Columns(panels, equal=True, expand=True))
        console.print()


# ── footer ────────────────────────────────────────────────────────────────────

def render_footer():
    t = Text(justify="center")
    t.append("./escmd.py help <cmd>", style="bold cyan")
    t.append("  ·  ", style="dim")
    t.append("./escmd.py version", style="bold cyan")
    t.append("  ·  ", style="dim")
    t.append("-l <cluster>", style="bold cyan")
    t.append(" to target a cluster  ·  ", style="dim")
    t.append("--format json", style="bold cyan")
    t.append(" for machine output", style="dim")
    console.print(Panel(Align.center(t), border_style="dim", padding=(0, 1)))


# ── entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    console.print()
    render_banner()
    render_status_bar()
    render_grid()
    render_footer()
    console.print()
