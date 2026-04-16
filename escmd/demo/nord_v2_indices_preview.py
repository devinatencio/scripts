#!/usr/bin/env python3
"""
Nord v2 Theme Preview — True Nord Hex Colors

Uses the actual Nord palette hex values instead of approximate Rich color names.
Rich supports "#rrggbb" style strings natively, so we get pixel-perfect Nord.

Nord palette: https://www.nordtheme.com/docs/colors-and-palettes

Run:  python3 demo/nord_v2_indices_preview.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box

console = Console()

# ── True Nord Hex Palette ───────────────────────────────────────────
# Polar Night — backgrounds & surfaces
NORD0  = "#2e3440"   # darkest bg
NORD1  = "#3b4252"   # elevated surfaces
NORD2  = "#434c5e"   # selection / zebra
NORD3  = "#4c566a"   # comments, muted, inactive

# Snow Storm — foreground text
NORD4  = "#d8dee9"   # default body text
NORD5  = "#e5e9f0"   # brighter text
NORD6  = "#eceff4"   # brightest / headers

# Frost — blues (the soul of Nord)
NORD7  = "#8fbcbb"   # teal — success/green health
NORD8  = "#88c0d0"   # light blue — primary, titles
NORD9  = "#81a1c1"   # muted blue — secondary, borders
NORD10 = "#5e81ac"   # deep blue — info, links

# Aurora — semantic accents (used sparingly)
NORD11 = "#bf616a"   # red — error, critical
NORD12 = "#d08770"   # orange — hot indices, warm phase
NORD13 = "#ebcb8b"   # yellow — warning
NORD14 = "#a3be8c"   # green — success (actual green, not teal)
NORD15 = "#b48ead"   # purple — frozen, secondary accent


def sep(label: str):
    console.print()
    console.rule(f"[bold {NORD8}]{label}[/bold {NORD8}]", style=NORD3)
    console.print()


# ════════════════════════════════════════════════════════════════════
# PALETTE REFERENCE
# ════════════════════════════════════════════════════════════════════

def palette_card():
    """Show the true Nord hex mapping and semantic roles."""

    sep("palette reference")

    card = Table(
        box=box.ROUNDED,
        expand=True,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD1}",
        border_style=NORD9,
        title=f"[bold {NORD8}]🧊 True Nord Palette — Hex Values[/bold {NORD8}]",
        padding=(0, 1),
    )
    card.add_column("Semantic Role", style=f"bold {NORD4}", width=22)
    card.add_column("Token", width=8)
    card.add_column("Hex", width=9)
    card.add_column("Preview", min_width=30)

    rows = [
        ("Polar Night",    "",      "",      "── Backgrounds & Surfaces ──"),
        ("Darkest BG",     "nord0", NORD0,   "████████ table header bg"),
        ("Elevated BG",    "nord1", NORD1,   "████████ panel surfaces"),
        ("Zebra / Select", "nord2", NORD2,   "████████ alternating rows"),
        ("Muted / Dim",    "nord3", NORD3,   "████████ comments, inactive"),
        ("Snow Storm",     "",      "",      "── Foreground Text ──"),
        ("Body Text",      "nord4", NORD4,   "Default body text style"),
        ("Bright Text",    "nord5", NORD5,   "Values and emphasis"),
        ("Headers",        "nord6", NORD6,   "Column headers, titles"),
        ("Frost",          "",      "",      "── Primary Blues ──"),
        ("Teal Accent",    "nord7", NORD7,   "◉ Green health indicator"),
        ("Primary / Title","nord8", NORD8,   "📊 Elasticsearch Indices"),
        ("Border / Sec.",  "nord9", NORD9,   "━━━ panel borders ━━━"),
        ("Info / Deep",    "nord10",NORD10,  "Links, doc counts, info"),
        ("Aurora",         "",      "",      "── Semantic Accents ──"),
        ("Error / Red",    "nord11",NORD11,  "○ Red  ❌ UNASSIGNED"),
        ("Orange / Hot",   "nord12",NORD12,  "🔥 Hot index, warm phase"),
        ("Warning",        "nord13",NORD13,  "◐ Yellow  ⚠ Warning"),
        ("Success",        "nord14",NORD14,  "✅ STARTED  ◆ Open"),
        ("Purple / Frozen","nord15",NORD15,  "🧊 Frozen  secondary"),
    ]

    for role, token, hex_val, preview in rows:
        if not hex_val:
            # Section header row
            card.add_row(
                Text(role, style=f"bold {NORD8}"),
                "", "",
                Text(preview, style=f"dim {NORD3}"),
            )
        else:
            card.add_row(
                role,
                Text(token, style=f"dim {NORD4}"),
                Text(hex_val, style=f"bold {hex_val}"),
                Text(preview, style=hex_val),
            )

    console.print(card)
    console.print()
    console.print(
        f"  [{NORD3}]Key difference from v1: nord14 ({NORD14}) is actual green for success,[/{NORD3}]"
    )
    console.print(
        f"  [{NORD3}]nord7 ({NORD7}) teal for green-health, nord12 ({NORD12}) orange for hot/warm,[/{NORD3}]"
    )
    console.print(
        f"  [{NORD3}]and nord15 ({NORD15}) purple for frozen indices — each Aurora color has a job.[/{NORD3}]"
    )
    console.print()


# ════════════════════════════════════════════════════════════════════
# INDICES LIST VIEW
# ════════════════════════════════════════════════════════════════════

def health_cell(level):
    g = Table.grid(padding=(0, 1))
    g.add_column(justify="center")
    g.add_column(justify="left")
    if level == "green":
        g.add_row(Text("◉", style=NORD7), Text("Green", style=NORD7))
    elif level == "yellow":
        g.add_row(Text("◐", style=NORD13), Text("Yellow", style=NORD13))
    else:
        g.add_row(Text("○", style=NORD11), Text("Red", style=NORD11))
    return g


def status_cell(st):
    g = Table.grid(padding=(0, 1))
    g.add_column(justify="center")
    g.add_column(justify="left")
    if st == "open":
        g.add_row(Text("◆", style=NORD14), Text("Open", style=NORD14))
    else:
        g.add_row(Text("◇", style=NORD13), Text("Closed", style=NORD13))
    return g


def indices_list():
    """Full indices list with true Nord colors."""

    sep("indices list view")

    # Title panel
    subtitle = Text()
    subtitle.append("Total: ", style=NORD4)
    subtitle.append("8", style=NORD10)
    subtitle.append("  Green: ", style=NORD4)
    subtitle.append("5", style=NORD7)
    subtitle.append("  Yellow: ", style=NORD4)
    subtitle.append("2", style=NORD13)
    subtitle.append("  Red: ", style=NORD4)
    subtitle.append("1", style=NORD11)
    subtitle.append("  Hot: ", style=NORD4)
    subtitle.append("1", style=NORD12)
    subtitle.append("  Frozen: ", style=NORD4)
    subtitle.append("1", style=NORD15)

    cluster_sub = Text()
    cluster_sub.append("prod-cluster", style=f"bold {NORD8}")
    cluster_sub.append("  ", style="default")
    cluster_sub.append("v8.17.0", style=NORD3)
    cluster_sub.append("   ", style="default")
    cluster_sub.append_text(subtitle)

    title_panel = Panel(
        Text("🟡 Warning — 2 Indices Yellow", style=f"bold {NORD13}", justify="center"),
        title=Text("📊 Elasticsearch Indices", style=f"bold {NORD8}"),
        subtitle=cluster_sub,
        border_style=NORD13,
        padding=(1, 2),
    )
    console.print(title_panel)
    console.print()

    # Table
    table = Table(
        box=box.ROUNDED,
        expand=True,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD1}",
        border_style=NORD9,
    )
    table.add_column("Index Name", no_wrap=False, min_width=40)
    table.add_column("Health", justify="left", no_wrap=True)
    table.add_column("Status", justify="left", no_wrap=True)
    table.add_column("Docs", justify="right", width=12)
    table.add_column("Shards", justify="right", width=10)
    table.add_column("Primary", justify="right", width=10)
    table.add_column("Total", justify="right", width=10)

    rows = [
        (".ds-logs-2026.04.14-000001",  "green",  "open",   "12,345,678", "5|1", "8.5gb",  "17.0gb",  ""),
        (".ds-logs-2026.04.13-000002",  "green",  "open",   "9,876,543",  "5|1", "6.2gb",  "12.4gb",  ""),
        (".ds-metrics-2026.04.14",      "green",  "open",   "2,345,678",  "3|1", "1.8gb",  "3.6gb",   ""),
        ("app-events-hot 🔥",           "green",  "open",   "456,789",    "2|1", "890mb",  "1.7gb",   "hot"),
        ("audit-logs-2026-q1",          "yellow", "open",   "1,234,567",  "1|1", "4.2gb",  "4.2gb",   ""),
        ("legacy-orders-2024",          "yellow", "closed", "567,890",    "1|1", "2.1gb",  "2.1gb",   ""),
        ("search-cache-v2 🧊",          "green",  "open",   "89,012",     "1|0", "156mb",  "156mb",   "frozen"),
        ("temp-reindex-failed",         "red",    "open",   "0",          "1|1", "0b",     "0b",      ""),
    ]

    for i, (name, health, status, docs, shards, pri_size, tot_size, special) in enumerate(rows):
        # Foreground: health drives color, special states override
        if special == "hot":
            fg = NORD12       # orange for hot
        elif special == "frozen":
            fg = NORD15       # purple for frozen
        elif health == "red":
            fg = NORD11
        elif health == "yellow":
            fg = NORD13
        else:
            fg = NORD4        # default snow storm text

        # Zebra striping
        bg = f" on {NORD2}" if i % 2 == 1 else ""
        row_style = f"{fg}{bg}"

        table.add_row(
            name,
            health_cell(health),
            status_cell(status),
            docs, shards, pri_size, tot_size,
            style=row_style,
        )

    console.print(table)
    console.print()


# ════════════════════════════════════════════════════════════════════
# INDEX DETAIL — YELLOW HEALTH
# ════════════════════════════════════════════════════════════════════

def detail_yellow():
    """indice audit-logs-2026-q1 — yellow health, unassigned replica."""

    sep("indice detail — yellow health")

    # Subtitle bar
    sub = Text()
    sub.append("Docs: ", style=NORD4)
    sub.append("1,234,567", style=NORD10)
    sub.append("  Shards: ", style=NORD4)
    sub.append("1p", style=NORD8)
    sub.append("/", style=NORD3)
    sub.append("1r", style=NORD9)
    sub.append("  Size: ", style=NORD4)
    sub.append("4.2gb", style=NORD10)
    sub.append(" / ", style=NORD3)
    sub.append("4.2gb", style=NORD10)
    sub.append("  Status: ", style=NORD4)
    sub.append("Open", style=NORD14)
    sub.append("  ILM: ", style=NORD4)
    sub.append("audit-policy", style=NORD8)
    sub.append(" (", style=NORD3)
    sub.append("Warm", style=NORD12)
    sub.append(")", style=NORD3)

    title_panel = Panel(
        Text("🟡 audit-logs-2026-q1 — 1 Unassigned Replica",
             style=f"bold {NORD13}", justify="center"),
        title=Text("📋 Index Details", style=f"bold {NORD8}"),
        subtitle=sub,
        border_style=NORD13,
        padding=(1, 2),
    )

    # Settings panel
    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column("Label", style=f"bold {NORD9}", no_wrap=True)
    info.add_column("Icon", justify="left", width=3)
    info.add_column("Value", style=NORD5, no_wrap=True)
    info.add_row("UUID:", "🆔", "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    info.add_row("Created:", "📅", "2026-01-15 09:30:00")
    info.add_row("Version:", "🔩", "8170099")
    info.add_row("ILM Policy:", "📋", Text("audit-policy", style=NORD8))
    info.add_row("ILM Phase:", "🟡", Text("Warm", style=NORD12))
    info.add_row("Shards:", "🔢", "1 primary / 1 replica")

    info_panel = Panel(
        info,
        title=f"[bold {NORD6}]🔩 Settings[/bold {NORD6}]",
        border_style=NORD9,
        padding=(1, 2),
    )

    # Shard overview
    sh = Table(show_header=False, box=None, padding=(0, 1))
    sh.add_column("Label", style=f"bold {NORD9}", no_wrap=True)
    sh.add_column("Icon", justify="left", width=3)
    sh.add_column("Value", no_wrap=True)
    sh.add_row("Total Shards:", "📊", Text("2", style=NORD5))
    sh.add_row("Primary:", "🔑", Text("1 Started", style=NORD14))
    sh.add_row("Replica:", "📋", Text("1 Unassigned", style=NORD11))
    sh.add_row("", "", "")
    sh.add_row("node-1:", "💻", Text("1 shard", style=NORD5))
    sh.add_row("Unassigned:", "🔶", Text("1 shard", style=NORD11))

    sh_panel = Panel(
        sh,
        title=f"[bold {NORD6}]📊 Shard Overview[/bold {NORD6}]",
        border_style=NORD13,
        padding=(1, 2),
    )

    console.print(title_panel)
    console.print()
    console.print(Columns([info_panel, sh_panel], expand=True))
    console.print()

    # Shards table
    st = Table(
        box=box.ROUNDED,
        expand=True,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD1}",
        border_style=NORD9,
    )
    st.add_column("Shard", justify="center", width=6)
    st.add_column("Type", justify="center", width=10)
    st.add_column("State", justify="left", width=16)
    st.add_column("Node", min_width=20)
    st.add_column("Docs", justify="right", width=12)
    st.add_column("Size", justify="right", width=10)

    st.add_row(
        "0",
        Text("Primary", style=f"bold {NORD8}"),
        Text("✅ STARTED", style=NORD14),
        Text("node-1", style=NORD4),
        "1,234,567", "4.2gb",
        style=NORD4,
    )
    st.add_row(
        "0",
        Text("Replica", style=f"bold {NORD9}"),
        Text("❌ UNASSIGNED", style=NORD11),
        Text("—", style=NORD3),
        "—", "—",
        style=f"{NORD4} on {NORD2}",
    )

    console.print(st)
    console.print()


# ════════════════════════════════════════════════════════════════════
# INDEX DETAIL — GREEN / HEALTHY
# ════════════════════════════════════════════════════════════════════

def detail_green():
    """indice .ds-logs — healthy, 10 shards across 3 nodes."""

    sep("indice detail — green / healthy")

    sub = Text()
    sub.append("Docs: ", style=NORD4)
    sub.append("12,345,678", style=NORD10)
    sub.append("  Shards: ", style=NORD4)
    sub.append("5p", style=NORD8)
    sub.append("/", style=NORD3)
    sub.append("1r", style=NORD9)
    sub.append("  Size: ", style=NORD4)
    sub.append("8.5gb", style=NORD10)
    sub.append(" / ", style=NORD3)
    sub.append("17.0gb", style=NORD10)
    sub.append("  Status: ", style=NORD4)
    sub.append("Open", style=NORD14)
    sub.append("  ILM: ", style=NORD4)
    sub.append("logs-policy", style=NORD8)
    sub.append(" (", style=NORD3)
    sub.append("🔥 Hot", style=NORD12)
    sub.append(")", style=NORD3)

    title_panel = Panel(
        Text("🟢 .ds-logs-2026.04.14-000001 — Healthy (All Shards Assigned)",
             style=f"bold {NORD14}", justify="center"),
        title=Text("📋 Index Details", style=f"bold {NORD8}"),
        subtitle=sub,
        border_style=NORD9,
        padding=(1, 2),
    )

    # Settings
    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column("Label", style=f"bold {NORD9}", no_wrap=True)
    info.add_column("Icon", justify="left", width=3)
    info.add_column("Value", style=NORD5, no_wrap=True)
    info.add_row("UUID:", "🆔", "f7e8d9c0-b1a2-3456-7890-abcdef012345")
    info.add_row("Created:", "📅", "2026-04-14 00:00:01")
    info.add_row("Version:", "🔩", "8170099")
    info.add_row("ILM Policy:", "📋", Text("logs-policy", style=NORD8))
    info.add_row("ILM Phase:", "🔥", Text("Hot", style=NORD12))
    info.add_row("Shards:", "🔢", "5 primary / 1 replica")

    info_panel = Panel(
        info,
        title=f"[bold {NORD6}]🔩 Settings[/bold {NORD6}]",
        border_style=NORD9,
        padding=(1, 2),
    )

    # Shard overview
    sh = Table(show_header=False, box=None, padding=(0, 1))
    sh.add_column("Label", style=f"bold {NORD9}", no_wrap=True)
    sh.add_column("Icon", justify="left", width=3)
    sh.add_column("Value", no_wrap=True)
    sh.add_row("Total Shards:", "📊", Text("10", style=NORD5))
    sh.add_row("Primary:", "🔑", Text("5 Started", style=NORD14))
    sh.add_row("Replica:", "📋", Text("5 Started", style=NORD14))
    sh.add_row("", "", "")
    sh.add_row("node-1:", "💻", Text("4 shards", style=NORD5))
    sh.add_row("node-2:", "💻", Text("3 shards", style=NORD5))
    sh.add_row("node-3:", "💻", Text("3 shards", style=NORD5))

    sh_panel = Panel(
        sh,
        title=f"[bold {NORD6}]📊 Shard Overview[/bold {NORD6}]",
        border_style=NORD14,
        padding=(1, 2),
    )

    console.print(title_panel)
    console.print()
    console.print(Columns([info_panel, sh_panel], expand=True))
    console.print()

    # Shards table
    st = Table(
        box=box.ROUNDED,
        expand=True,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD1}",
        border_style=NORD9,
    )
    st.add_column("Shard", justify="center", width=6)
    st.add_column("Type", justify="center", width=10)
    st.add_column("State", justify="left", width=16)
    st.add_column("Node", min_width=20)
    st.add_column("Docs", justify="right", width=12)
    st.add_column("Size", justify="right", width=10)

    shard_data = [
        ("0", "Primary", "node-1", "2,469,135", "1.7gb"),
        ("0", "Replica", "node-2", "2,469,135", "1.7gb"),
        ("1", "Primary", "node-2", "2,469,136", "1.7gb"),
        ("1", "Replica", "node-3", "2,469,136", "1.7gb"),
        ("2", "Primary", "node-3", "2,469,136", "1.7gb"),
        ("2", "Replica", "node-1", "2,469,136", "1.7gb"),
        ("3", "Primary", "node-1", "2,469,136", "1.7gb"),
        ("3", "Replica", "node-3", "2,469,136", "1.7gb"),
        ("4", "Primary", "node-2", "2,469,135", "1.7gb"),
        ("4", "Replica", "node-1", "2,469,135", "1.7gb"),
    ]

    for i, (shard, stype, node, docs, size) in enumerate(shard_data):
        type_style = NORD8 if stype == "Primary" else NORD9
        bg = f" on {NORD2}" if i % 2 == 1 else ""
        base = f"{NORD4}{bg}"

        st.add_row(
            shard,
            Text(stype, style=f"bold {type_style}"),
            Text("✅ STARTED", style=NORD14),
            Text(node, style=NORD4),
            docs, size,
            style=base,
        )

    console.print(st)
    console.print()


# ════════════════════════════════════════════════════════════════════
# INDEX DETAIL — RED / CRITICAL
# ════════════════════════════════════════════════════════════════════

def detail_red():
    """indice temp-reindex-failed — red health, all unassigned."""

    sep("indice detail — red / critical")

    sub = Text()
    sub.append("Docs: ", style=NORD4)
    sub.append("0", style=NORD10)
    sub.append("  Shards: ", style=NORD4)
    sub.append("1p", style=NORD8)
    sub.append("/", style=NORD3)
    sub.append("1r", style=NORD9)
    sub.append("  Size: ", style=NORD4)
    sub.append("0b", style=NORD10)
    sub.append(" / ", style=NORD3)
    sub.append("0b", style=NORD10)
    sub.append("  Status: ", style=NORD4)
    sub.append("Open", style=NORD14)

    title_panel = Panel(
        Text("🔴 temp-reindex-failed — 2 Unassigned Shards",
             style=f"bold {NORD11}", justify="center"),
        title=Text("📋 Index Details", style=f"bold {NORD8}"),
        subtitle=sub,
        border_style=NORD11,
        padding=(1, 2),
    )

    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column("Label", style=f"bold {NORD9}", no_wrap=True)
    info.add_column("Icon", justify="left", width=3)
    info.add_column("Value", style=NORD5, no_wrap=True)
    info.add_row("UUID:", "🆔", "dead0000-beef-0000-cafe-000000000000")
    info.add_row("Created:", "📅", "2026-04-14 22:15:00")
    info.add_row("Version:", "🔩", "8170099")
    info.add_row("ILM Policy:", "❌", Text("None", style=NORD3))
    info.add_row("Shards:", "🔢", "1 primary / 1 replica")

    info_panel = Panel(
        info,
        title=f"[bold {NORD6}]🔩 Settings[/bold {NORD6}]",
        border_style=NORD9,
        padding=(1, 2),
    )

    sh = Table(show_header=False, box=None, padding=(0, 1))
    sh.add_column("Label", style=f"bold {NORD9}", no_wrap=True)
    sh.add_column("Icon", justify="left", width=3)
    sh.add_column("Value", no_wrap=True)
    sh.add_row("Total Shards:", "📊", Text("2", style=NORD5))
    sh.add_row("Primary:", "🔑", Text("1 Unassigned", style=NORD11))
    sh.add_row("Replica:", "📋", Text("1 Unassigned", style=NORD11))
    sh.add_row("", "", "")
    sh.add_row("Unassigned:", "🔶", Text("2 shards", style=NORD11))

    sh_panel = Panel(
        sh,
        title=f"[bold {NORD6}]📊 Shard Overview[/bold {NORD6}]",
        border_style=NORD11,
        padding=(1, 2),
    )

    console.print(title_panel)
    console.print()
    console.print(Columns([info_panel, sh_panel], expand=True))
    console.print()

    st = Table(
        box=box.ROUNDED,
        expand=True,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD1}",
        border_style=NORD9,
    )
    st.add_column("Shard", justify="center", width=6)
    st.add_column("Type", justify="center", width=10)
    st.add_column("State", justify="left", width=16)
    st.add_column("Node", min_width=20)
    st.add_column("Docs", justify="right", width=12)
    st.add_column("Size", justify="right", width=10)

    st.add_row(
        "0",
        Text("Primary", style=f"bold {NORD8}"),
        Text("❌ UNASSIGNED", style=NORD11),
        Text("—", style=NORD3),
        "—", "—",
        style=NORD4,
    )
    st.add_row(
        "0",
        Text("Replica", style=f"bold {NORD9}"),
        Text("❌ UNASSIGNED", style=NORD11),
        Text("—", style=NORD3),
        "—", "—",
        style=f"{NORD4} on {NORD2}",
    )

    console.print(st)
    console.print()


# ════════════════════════════════════════════════════════════════════
# SIDE-BY-SIDE: CURRENT RICH vs NORD v2
# ════════════════════════════════════════════════════════════════════

def side_by_side_mini():
    """Compact comparison of the same 4 rows in rich vs nord."""

    sep("side-by-side — rich (current) vs nord v2")

    # ── Current "rich" theme ─────────────────────────────────────
    rich_table = Table(
        box=box.HEAVY,
        show_header=True,
        header_style="bold white on dark_blue",
        border_style="white",
        title="[bold cyan]Current: rich theme[/bold cyan]",
        expand=True,
    )
    rich_table.add_column("Index Name", min_width=28)
    rich_table.add_column("Health", width=12)
    rich_table.add_column("Docs", justify="right", width=12)
    rich_table.add_column("Size", justify="right", width=8)

    rich_rows = [
        (".ds-logs-2026.04.14",  "green",  "12,345,678", "8.5gb",  "white"),
        ("audit-logs-2026-q1",   "yellow", "1,234,567",  "4.2gb",  "yellow"),
        ("app-events-hot 🔥",    "green",  "456,789",    "890mb",  "bright_red"),
        ("temp-reindex-failed",  "red",    "0",          "0b",     "red"),
    ]

    for i, (name, health, docs, size, fg) in enumerate(rich_rows):
        h_color = {"green": "green bold", "yellow": "yellow bold", "red": "red bold"}[health]
        zbg = " on grey11" if i % 2 == 1 else ""
        rich_table.add_row(
            name,
            Text(health.title(), style=h_color),
            docs, size,
            style=f"{fg}{zbg}",
        )

    # ── Nord v2 ──────────────────────────────────────────────────
    nord_table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD1}",
        border_style=NORD9,
        title=f"[bold {NORD8}]Nord v2: true hex[/bold {NORD8}]",
        expand=True,
    )
    nord_table.add_column("Index Name", min_width=28)
    nord_table.add_column("Health", width=12)
    nord_table.add_column("Docs", justify="right", width=12)
    nord_table.add_column("Size", justify="right", width=8)

    nord_rows = [
        (".ds-logs-2026.04.14",  "green",  "12,345,678", "8.5gb",  NORD4),
        ("audit-logs-2026-q1",   "yellow", "1,234,567",  "4.2gb",  NORD13),
        ("app-events-hot 🔥",    "green",  "456,789",    "890mb",  NORD12),
        ("temp-reindex-failed",  "red",    "0",          "0b",     NORD11),
    ]

    h_map = {"green": (NORD7, "Green"), "yellow": (NORD13, "Yellow"), "red": (NORD11, "Red")}

    for i, (name, health, docs, size, fg) in enumerate(nord_rows):
        hc, hl = h_map[health]
        zbg = f" on {NORD2}" if i % 2 == 1 else ""
        nord_table.add_row(
            name,
            Text(hl, style=f"bold {hc}"),
            docs, size,
            style=f"{fg}{zbg}",
        )

    console.print(Columns([rich_table, nord_table], expand=True))
    console.print()


# ════════════════════════════════════════════════════════════════════
# PROPOSED themes.yml SNIPPET
# ════════════════════════════════════════════════════════════════════

def proposed_yml():
    """Print the proposed themes.yml nord section."""

    sep("proposed themes.yml — nord v2 (true hex)")

    yml = Text()
    yml.append("  # 🧊 Nord v2 — True hex values from nordtheme.com\n", style=NORD3)
    yml.append("  nord:\n", style=f"bold {NORD8}")
    yml.append("    table_styles:\n", style=NORD9)
    yml.append(f'      border_style: "{NORD9}"\n', style=NORD4)
    yml.append(f'      header_style: "bold {NORD6} on {NORD1}"\n', style=NORD4)
    yml.append( '      table_box: rounded\n', style=NORD4)
    yml.append( '      health_styles:\n', style=NORD9)
    yml.append(f'        green:  {{ icon: "{NORD7} bold",  text: "{NORD7} bold"  }}\n', style=NORD4)
    yml.append(f'        yellow: {{ icon: "{NORD13} bold", text: "{NORD13} bold" }}\n', style=NORD4)
    yml.append(f'        red:    {{ icon: "{NORD11} bold", text: "{NORD11} bold" }}\n', style=NORD4)
    yml.append( '      status_styles:\n', style=NORD9)
    yml.append(f'        open:  {{ icon: "{NORD14} bold", text: "{NORD14} bold" }}\n', style=NORD4)
    yml.append(f'        close: {{ icon: "{NORD11} bold", text: "{NORD11} bold" }}\n', style=NORD4)
    yml.append( '      state_styles:\n', style=NORD9)
    yml.append(f'        STARTED:      {{ icon: "{NORD14} bold", text: "{NORD14} bold" }}\n', style=NORD4)
    yml.append(f'        INITIALIZING: {{ icon: "{NORD13} bold", text: "{NORD13} bold" }}\n', style=NORD4)
    yml.append(f'        RELOCATING:   {{ icon: "{NORD10} bold", text: "{NORD10} bold" }}\n', style=NORD4)
    yml.append(f'        UNASSIGNED:   {{ icon: "{NORD11} bold", text: "{NORD11} bold" }}\n', style=NORD4)
    yml.append( '      type_styles:\n', style=NORD9)
    yml.append(f'        primary: {{ icon: "{NORD8} bold", text: "{NORD8} bold" }}\n', style=NORD4)
    yml.append(f'        replica: {{ icon: "{NORD9} bold", text: "{NORD9} bold" }}\n', style=NORD4)
    yml.append( '      row_styles:\n', style=NORD9)
    yml.append(f'        normal: "{NORD4}"\n', style=NORD4)
    yml.append(f'        zebra: "{NORD2}"\n', style=NORD4)
    yml.append(f'        hot: "{NORD12}"\n', style=NORD4)
    yml.append(f'        frozen: "{NORD15}"\n', style=NORD4)
    yml.append(f'        critical_health: "{NORD11}"\n', style=NORD4)
    yml.append(f'        warning_health: "{NORD13}"\n', style=NORD4)
    yml.append(f'        healthy: "{NORD4}"\n', style=NORD4)
    yml.append( '    panel_styles:\n', style=NORD9)
    yml.append(f'      title: "bold {NORD8}"\n', style=NORD4)
    yml.append(f'      subtitle: "dim {NORD4}"\n', style=NORD4)
    yml.append(f'      success: "{NORD14}"\n', style=NORD4)
    yml.append(f'      warning: "{NORD13}"\n', style=NORD4)
    yml.append(f'      error: "{NORD11}"\n', style=NORD4)
    yml.append(f'      info: "{NORD10}"\n', style=NORD4)
    yml.append(f'      secondary: "{NORD15}"\n', style=NORD4)
    yml.append( '    help_styles:\n', style=NORD9)
    yml.append(f'      title: "bold {NORD8}"\n', style=NORD4)
    yml.append(f'      section_header: "bold {NORD9}"\n', style=NORD4)
    yml.append(f'      command: "{NORD13} bold"\n', style=NORD4)
    yml.append(f'      description: "{NORD4}"\n', style=NORD4)
    yml.append(f'      example: "{NORD7}"\n', style=NORD4)
    yml.append(f'      footer: "dim {NORD3}"\n', style=NORD4)
    yml.append( '    semantic_styles:\n', style=NORD9)
    yml.append(f'      primary: "{NORD8}"\n', style=NORD4)
    yml.append(f'      secondary: "{NORD15}"\n', style=NORD4)
    yml.append(f'      success: "{NORD14}"\n', style=NORD4)
    yml.append(f'      warning: "{NORD13}"\n', style=NORD4)
    yml.append(f'      error: "{NORD11}"\n', style=NORD4)
    yml.append(f'      info: "{NORD10}"\n', style=NORD4)

    console.print(Panel(
        yml,
        title=f"[bold {NORD8}]themes.yml — nord v2[/bold {NORD8}]",
        border_style=NORD9,
        padding=(1, 2),
    ))
    console.print()


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    console.print()
    console.print(Panel(
        Text(
            "Nord v2 Theme Preview — True Hex Colors\n\n"
            "This version uses the actual Nord hex palette (#2e3440 … #b48ead)\n"
            "instead of approximate Rich color names. Every Aurora color has\n"
            "a distinct semantic job:\n\n"
            "  nord11 #bf616a  red    → error, critical health\n"
            "  nord12 #d08770  orange → hot indices, warm ILM phase\n"
            "  nord13 #ebcb8b  yellow → warnings, yellow health\n"
            "  nord14 #a3be8c  green  → success, started, open\n"
            "  nord15 #b48ead  purple → frozen indices, secondary\n",
            style=NORD4, justify="center",
        ),
        title=f"[bold {NORD8}]🧊 NORD v2 PREVIEW[/bold {NORD8}]",
        border_style=NORD9,
        padding=(1, 3),
    ))

    palette_card()
    side_by_side_mini()
    indices_list()
    detail_yellow()
    detail_green()
    detail_red()
    proposed_yml()

    console.print()
    console.rule(f"[{NORD3}]end of preview[/{NORD3}]", style=NORD3)
    console.print()
