#!/usr/bin/env python3
"""
Preview: ./escmd.py indice mylog — current vs proposed layout.

Run: python3 demo/indice_detail_preview.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

console = Console()


# ── CURRENT LAYOUT ──────────────────────────────────────────────────

def current_layout():
    console.rule("[bold white]CURRENT: indice mylog (7 panels)[/bold white]", style="dim")
    print()

    # 1. Title panel
    title_panel = Panel(
        Text("Index Details: mylog", style="bold bright_cyan", justify="center"),
        subtitle="📋 Standard Index",
        border_style="bright_cyan",
        padding=(1, 2),
    )

    # 2. Overview panel
    ov = Table(show_header=False, box=None, padding=(0, 1))
    ov.add_column("Label", style="bold", no_wrap=True)
    ov.add_column("Icon", justify="left", width=2)
    ov.add_column("Value", no_wrap=True)
    ov.add_row("Health:", "🟡", "Yellow")
    ov.add_row("Status:", "📂", "Open")
    ov.add_row("Documents:", "📊", "1,234")
    ov.add_row("Primary Shards:", "🔢", "1")
    ov.add_row("Replica Shards:", "📋", "1")
    ov.add_row("Primary Size:", "💾", "4.2kb")
    ov.add_row("Total Size:", "📦", "4.2kb")
    ov_panel = Panel(ov, title="Overview", border_style="magenta", padding=(1, 2))

    # 3. Settings panel
    st = Table(show_header=False, box=None, padding=(0, 1))
    st.add_column("Label", style="bold", no_wrap=True)
    st.add_column("Icon", justify="left", width=2)
    st.add_column("Value", no_wrap=True)
    st.add_row("UUID:", "🆔", "abc123-def456-ghi789")
    st.add_row("Created:", "📅", "2026-04-14 10:30:00")
    st.add_row("Version:", "🔩", "8170099")
    st.add_row("ILM Policy:", "📋", "my-ilm-policy")
    st.add_row("ILM Phase:", "🔥", "Hot")
    st.add_row("Configured Shards:", "🔢", "1")
    st.add_row("Configured Replicas:", "📋", "1")
    st_panel = Panel(st, title="Settings", border_style="blue", padding=(1, 2))

    # 4-6. Three shard panels
    tot = Table.grid(padding=(0, 3))
    tot.add_column(style="bold cyan", min_width=16)
    tot.add_column(style="white")
    tot.add_row("Total Shards:", "📊 2")
    tot.add_row("Primary:", "🔑 1")
    tot.add_row("Replica:", "📋 1")
    tot_panel = Panel(tot, title="Shard Totals", border_style="green", padding=(1, 1))

    sta = Table.grid(padding=(0, 3))
    sta.add_column(style="bold cyan", min_width=16)
    sta.add_column(style="white")
    sta.add_row("STARTED:", "✅ 1")
    sta.add_row("UNASSIGNED:", "❌ 1")
    sta_panel = Panel(sta, title="🔄 Shard States", border_style="yellow", padding=(1, 1))

    nd = Table.grid(padding=(0, 3))
    nd.add_column(style="bold cyan", min_width=16)
    nd.add_column(style="white")
    nd.add_row("node-1:", "💻 1")
    nd.add_row("None:", "🔶 1")
    nd_panel = Panel(nd, title="💻 Node Distribution", border_style="magenta", padding=(1, 1))

    console.print(title_panel)
    print()
    console.print(Columns([ov_panel, st_panel], expand=True))
    print()
    console.print(Columns([tot_panel, sta_panel, nd_panel], expand=True))
    print()
    console.print("[dim]  ... Detailed Shards Information table below ...[/dim]")
    print()


# ── PROPOSED LAYOUT ─────────────────────────────────────────────────

def proposed_yellow():
    console.rule("[bold white]PROPOSED: indice mylog (yellow index, 3 panels)[/bold white]", style="dim")
    print()

    # 1. Title panel — standard pattern
    subtitle = Text()
    subtitle.append("Docs: ", style="default")
    subtitle.append("1,234", style="cyan")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("1p", style="bright_magenta")
    subtitle.append("/", style="default")
    subtitle.append("1r", style="blue")
    subtitle.append(" | Size: ", style="default")
    subtitle.append("4.2kb", style="cyan")
    subtitle.append(" / ", style="default")
    subtitle.append("4.2kb", style="cyan")
    subtitle.append(" | Status: ", style="default")
    subtitle.append("Open", style="green")
    subtitle.append(" | ILM: ", style="default")
    subtitle.append("my-ilm-policy", style="bright_magenta")
    subtitle.append(" (", style="default")
    subtitle.append("🔥 Hot", style="bright_magenta")
    subtitle.append(")", style="default")

    title_panel = Panel(
        Text("🟡 mylog - 1 Unassigned Replica", style="bold yellow", justify="center"),
        title=Text("📋 Index Details", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="yellow",
        padding=(1, 2),
    )

    # 2. Settings & Info panel (left) — merged overview + settings
    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column("Label", style="bold", no_wrap=True)
    info.add_column("Icon", justify="left", width=3)
    info.add_column("Value", no_wrap=True)
    info.add_row("UUID:", "🆔", "abc123-def456-ghi789")
    info.add_row("Created:", "📅", "2026-04-14 10:30:00")
    info.add_row("Version:", "🔩", "8170099")
    info.add_row("ILM Policy:", "📋", "my-ilm-policy")
    info.add_row("ILM Phase:", "🔥", "Hot")
    info.add_row("Shards:", "🔢", "1 primary / 1 replica")
    info_panel = Panel(info, title="[bold white]🔩 Settings[/bold white]", border_style="bright_magenta", padding=(1, 2))

    # 3. Shard Overview panel (right) — condensed from 3 panels
    sh = Table(show_header=False, box=None, padding=(0, 1))
    sh.add_column("Label", style="bold", no_wrap=True)
    sh.add_column("Icon", justify="left", width=3)
    sh.add_column("Value", no_wrap=True)
    sh.add_row("Total Shards:", "📊", "2")
    sh.add_row("Primary:", "🔑", Text("1 Started", style="green"))
    sh.add_row("Replica:", "📋", Text("1 Unassigned", style="red"))
    sh.add_row("", "", "")
    sh.add_row("node-1:", "💻", "1 shard")
    sh.add_row("Unassigned:", "🔶", "1 shard")
    sh_panel = Panel(sh, title="[bold white]📊 Shard Overview[/bold white]", border_style="yellow", padding=(1, 2))

    console.print(title_panel)
    print()
    console.print(Columns([info_panel, sh_panel], expand=True))
    print()
    console.print("[dim]  ... Detailed Shards Information table below (unchanged) ...[/dim]")
    print()


def proposed_green():
    console.rule("[bold white]PROPOSED: indice greenlog (healthy index)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("Docs: ", style="default")
    subtitle.append("5,678,901", style="cyan")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("3p", style="bright_magenta")
    subtitle.append("/", style="default")
    subtitle.append("1r", style="blue")
    subtitle.append(" | Size: ", style="default")
    subtitle.append("2.1gb", style="cyan")
    subtitle.append(" / ", style="default")
    subtitle.append("4.2gb", style="cyan")
    subtitle.append(" | Status: ", style="default")
    subtitle.append("Open", style="green")
    subtitle.append(" | ILM: ", style="default")
    subtitle.append("logs-policy", style="bright_magenta")
    subtitle.append(" (", style="default")
    subtitle.append("🟡 Warm", style="yellow")
    subtitle.append(")", style="default")

    title_panel = Panel(
        Text("🟢 greenlog - Healthy (All Shards Assigned)", style="bold green", justify="center"),
        title=Text("📋 Index Details", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(1, 2),
    )

    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column("Label", style="bold", no_wrap=True)
    info.add_column("Icon", justify="left", width=3)
    info.add_column("Value", no_wrap=True)
    info.add_row("UUID:", "🆔", "xyz789-abc123-def456")
    info.add_row("Created:", "📅", "2026-03-01 08:15:00")
    info.add_row("Version:", "🔩", "8170099")
    info.add_row("ILM Policy:", "📋", "logs-policy")
    info.add_row("ILM Phase:", "🟡", "Warm")
    info.add_row("Shards:", "🔢", "3 primary / 1 replica")
    info_panel = Panel(info, title="[bold white]🔩 Settings[/bold white]", border_style="bright_magenta", padding=(1, 2))

    sh = Table(show_header=False, box=None, padding=(0, 1))
    sh.add_column("Label", style="bold", no_wrap=True)
    sh.add_column("Icon", justify="left", width=3)
    sh.add_column("Value", no_wrap=True)
    sh.add_row("Total Shards:", "📊", "6")
    sh.add_row("Primary:", "🔑", Text("3 Started", style="green"))
    sh.add_row("Replica:", "📋", Text("3 Started", style="green"))
    sh.add_row("", "", "")
    sh.add_row("node-1:", "💻", "3 shards")
    sh.add_row("node-2:", "💻", "3 shards")
    sh_panel = Panel(sh, title="[bold white]📊 Shard Overview[/bold white]", border_style="green", padding=(1, 2))

    console.print(title_panel)
    print()
    console.print(Columns([info_panel, sh_panel], expand=True))
    print()
    console.print("[dim]  ... Detailed Shards Information table below (unchanged) ...[/dim]")
    print()


def proposed_hot():
    console.rule("[bold white]PROPOSED: indice hotlog (hot index)[/bold white]", style="dim")
    print()

    subtitle = Text()
    subtitle.append("Docs: ", style="default")
    subtitle.append("12,345,678", style="cyan")
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("5p", style="bright_magenta")
    subtitle.append("/", style="default")
    subtitle.append("1r", style="blue")
    subtitle.append(" | Size: ", style="default")
    subtitle.append("8.5gb", style="cyan")
    subtitle.append(" / ", style="default")
    subtitle.append("17.0gb", style="cyan")
    subtitle.append(" | Status: ", style="default")
    subtitle.append("Open", style="green")
    subtitle.append(" | 🔥 Hot Index", style="bright_red")

    title_panel = Panel(
        Text("🟢 hotlog - Healthy (All Shards Assigned)", style="bold green", justify="center"),
        title=Text("📋 Index Details", style="bold bright_magenta"),
        subtitle=subtitle,
        border_style="bright_magenta",
        padding=(1, 2),
    )

    console.print(title_panel)
    print()
    console.print("[dim]  ... Settings + Shard Overview panels + Detailed Shards table below ...[/dim]")
    print()


if __name__ == "__main__":
    current_layout()
    print()
    proposed_yellow()
    proposed_green()
    proposed_hot()
