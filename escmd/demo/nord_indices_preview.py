#!/usr/bin/env python3
"""
Nord Theme Preview — Indices Commands

Demonstrates how the Nord arctic palette transforms the indices list view
and the detailed index view compared to the current 'rich' (default) theme.

Run:  python3 demo/nord_indices_preview.py

Nord palette reference (Rich-compatible names):
  Polar Night : grey23, grey27, grey30, grey35
  Snow Storm  : light_steel_blue, grey82, white
  Frost       : pale_turquoise1, cornflower_blue, sky_blue1, steel_blue1
  Aurora      : indian_red (red), light_goldenrod2 (yellow),
                pale_turquoise1 (green), steel_blue1 (purple)
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box

console = Console()

# ── Nord palette constants ──────────────────────────────────────────
# Polar Night (backgrounds)
NORD0 = "grey23"       # darkest bg
NORD1 = "grey27"       # elevated bg
NORD2 = "grey30"       # selection / zebra
NORD3 = "grey35"       # comments / muted

# Snow Storm (foregrounds)
NORD4 = "light_steel_blue"   # default text
NORD5 = "grey82"             # brighter text
NORD6 = "white"              # brightest text

# Frost (blues / primary accents)
FROST_TEAL   = "pale_turquoise1"   # nord8  — also used for success/green
FROST_BLUE   = "cornflower_blue"   # nord10 — info
FROST_SKY    = "sky_blue1"         # nord7  — primary / titles
FROST_STEEL  = "steel_blue1"       # nord9  — secondary / borders

# Aurora (semantic accents)
AURORA_RED    = "indian_red"         # error
AURORA_YELLOW = "light_goldenrod2"   # warning
AURORA_GREEN  = "pale_turquoise1"    # success (same as frost teal)
AURORA_PURPLE = "steel_blue1"        # secondary


def separator(label: str):
    console.print()
    console.rule(f"[bold {FROST_SKY}]{label}[/bold {FROST_SKY}]", style=NORD3)
    console.print()


# ════════════════════════════════════════════════════════════════════
# 1. INDICES LIST VIEW  —  `indices` / `indices *`
# ════════════════════════════════════════════════════════════════════

def nord_indices_list():
    """Simulates the `indices` command output with full Nord theming."""

    separator("NORD — indices list view")

    # ── Title panel ──────────────────────────────────────────────
    subtitle = Text()
    subtitle.append("Total: ", style="default")
    subtitle.append("8", style=FROST_BLUE)
    subtitle.append(" | Green: ", style="default")
    subtitle.append("5", style=AURORA_GREEN)
    subtitle.append(" | Yellow: ", style="default")
    subtitle.append("2", style=AURORA_YELLOW)
    subtitle.append(" | Red: ", style="default")
    subtitle.append("1", style=AURORA_RED)
    subtitle.append(" | Hot: ", style="default")
    subtitle.append("1", style=FROST_SKY)
    subtitle.append(" | Frozen: ", style="default")
    subtitle.append("1", style=FROST_STEEL)

    cluster_sub = Text()
    cluster_sub.append("prod-cluster", style=FROST_SKY)
    cluster_sub.append("  ", style="default")
    cluster_sub.append("v8.17.0", style=f"dim {NORD4}")
    cluster_sub.append("   ", style="default")
    cluster_sub.append_text(subtitle)

    title_panel = Panel(
        Text("🟡 Warning — 2 Indices Yellow", style=f"bold {AURORA_YELLOW}", justify="center"),
        title=Text("📊 Elasticsearch Indices", style=f"bold {FROST_SKY}"),
        subtitle=cluster_sub,
        border_style=AURORA_YELLOW,
        padding=(1, 2),
    )
    console.print(title_panel)
    console.print()

    # ── Indices table ────────────────────────────────────────────
    table = Table(
        box=box.SIMPLE,
        expand=True,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD0}",
        border_style=FROST_STEEL,
    )
    table.add_column("Index Name", no_wrap=False, min_width=40)
    table.add_column("Health", justify="left", no_wrap=True)
    table.add_column("Status", justify="left", no_wrap=True)
    table.add_column("Docs", justify="right", width=12)
    table.add_column("Shards", justify="right", width=10)
    table.add_column("Primary", justify="right", width=10)
    table.add_column("Total", justify="right", width=10)

    # Helper: health cell
    def health_cell(level):
        g = Table.grid(padding=(0, 1))
        g.add_column(justify="center")
        g.add_column(justify="left")
        if level == "green":
            g.add_row(Text("◉", style=AURORA_GREEN), Text("Green", style=AURORA_GREEN))
        elif level == "yellow":
            g.add_row(Text("◐", style=AURORA_YELLOW), Text("Yellow", style=AURORA_YELLOW))
        else:
            g.add_row(Text("○", style=AURORA_RED), Text("Red", style=AURORA_RED))
        return g

    # Helper: status cell
    def status_cell(st):
        g = Table.grid(padding=(0, 1))
        g.add_column(justify="center")
        g.add_column(justify="left")
        if st == "open":
            g.add_row(Text("◆", style=AURORA_GREEN), Text("Open", style=AURORA_GREEN))
        else:
            g.add_row(Text("◇", style=AURORA_YELLOW), Text("Closed", style=AURORA_YELLOW))
        return g

    # Helper: zebra bg
    def zbg(i):
        return f"on {NORD2}" if i % 2 == 1 else ""

    # Sample data — 8 indices with mixed health
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
        # Determine foreground color
        if health == "red":
            fg = AURORA_RED
        elif health == "yellow":
            fg = AURORA_YELLOW
        elif special == "hot":
            fg = AURORA_RED
        elif special == "frozen":
            fg = FROST_BLUE
        else:
            fg = NORD4

        bg = zbg(i)
        row_style = f"{fg} {bg}" if bg else fg

        table.add_row(
            name,
            health_cell(health),
            status_cell(status),
            docs,
            shards,
            pri_size,
            tot_size,
            style=row_style,
        )

    console.print(table)
    console.print()


# ════════════════════════════════════════════════════════════════════
# 2. INDEX DETAIL VIEW  —  `indice <name>`  (yellow health)
# ════════════════════════════════════════════════════════════════════

def nord_indice_detail_yellow():
    """Simulates `indice audit-logs-2026-q1` with Nord theming."""

    separator("NORD — indice detail (yellow health)")

    # ── Title panel ──────────────────────────────────────────────
    subtitle = Text()
    subtitle.append("Docs: ", style="default")
    subtitle.append("1,234,567", style=FROST_BLUE)
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("1p", style=FROST_SKY)
    subtitle.append("/", style="default")
    subtitle.append("1r", style=FROST_STEEL)
    subtitle.append(" | Size: ", style="default")
    subtitle.append("4.2gb", style=FROST_BLUE)
    subtitle.append(" / ", style="default")
    subtitle.append("4.2gb", style=FROST_BLUE)
    subtitle.append(" | Status: ", style="default")
    subtitle.append("Open", style=AURORA_GREEN)
    subtitle.append(" | ILM: ", style="default")
    subtitle.append("audit-policy", style=FROST_SKY)
    subtitle.append(" (", style="default")
    subtitle.append("🟡 Warm", style=AURORA_YELLOW)
    subtitle.append(")", style="default")

    title_panel = Panel(
        Text("🟡 audit-logs-2026-q1 — 1 Unassigned Replica",
             style=f"bold {AURORA_YELLOW}", justify="center"),
        title=Text("📋 Index Details", style=f"bold {FROST_SKY}"),
        subtitle=subtitle,
        border_style=AURORA_YELLOW,
        padding=(1, 2),
    )

    # ── Settings panel (left) ────────────────────────────────────
    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column("Label", style=f"bold {NORD4}", no_wrap=True)
    info.add_column("Icon", justify="left", width=3)
    info.add_column("Value", style=NORD5, no_wrap=True)
    info.add_row("UUID:", "🆔", "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    info.add_row("Created:", "📅", "2026-01-15 09:30:00")
    info.add_row("Version:", "🔩", "8170099")
    info.add_row("ILM Policy:", "📋", Text("audit-policy", style=FROST_SKY))
    info.add_row("ILM Phase:", "🟡", Text("Warm", style=AURORA_YELLOW))
    info.add_row("Shards:", "🔢", "1 primary / 1 replica")

    info_panel = Panel(
        info,
        title=f"[bold {NORD6}]🔩 Settings[/bold {NORD6}]",
        border_style=FROST_STEEL,
        padding=(1, 2),
    )

    # ── Shard overview panel (right) ─────────────────────────────
    sh = Table(show_header=False, box=None, padding=(0, 1))
    sh.add_column("Label", style=f"bold {NORD4}", no_wrap=True)
    sh.add_column("Icon", justify="left", width=3)
    sh.add_column("Value", no_wrap=True)
    sh.add_row("Total Shards:", "📊", Text("2", style=NORD5))
    sh.add_row("Primary:", "🔑", Text("1 Started", style=AURORA_GREEN))
    sh.add_row("Replica:", "📋", Text("1 Unassigned", style=AURORA_RED))
    sh.add_row("", "", "")
    sh.add_row("node-1:", "💻", Text("1 shard", style=NORD5))
    sh.add_row("Unassigned:", "🔶", Text("1 shard", style=AURORA_RED))

    sh_panel = Panel(
        sh,
        title=f"[bold {NORD6}]📊 Shard Overview[/bold {NORD6}]",
        border_style=AURORA_YELLOW,
        padding=(1, 2),
    )

    console.print(title_panel)
    console.print()
    console.print(Columns([info_panel, sh_panel], expand=True))
    console.print()

    # ── Detailed shards table ────────────────────────────────────
    shard_table = Table(
        box=box.SIMPLE,
        expand=True,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD0}",
        border_style=FROST_STEEL,
    )
    shard_table.add_column("Shard", justify="center", width=6)
    shard_table.add_column("Type", justify="center", width=10)
    shard_table.add_column("State", justify="left", width=14)
    shard_table.add_column("Node", min_width=20)
    shard_table.add_column("Docs", justify="right", width=12)
    shard_table.add_column("Size", justify="right", width=10)

    shard_table.add_row(
        "0",
        Text("Primary", style=f"bold {FROST_SKY}"),
        Text("✅ STARTED", style=AURORA_GREEN),
        Text("node-1", style=NORD4),
        "1,234,567",
        "4.2gb",
        style=NORD4,
    )
    shard_table.add_row(
        "0",
        Text("Replica", style=f"bold {FROST_STEEL}"),
        Text("❌ UNASSIGNED", style=AURORA_RED),
        Text("—", style=NORD3),
        "—",
        "—",
        style=f"{NORD4} on {NORD2}",
    )

    console.print(shard_table)
    console.print()


# ════════════════════════════════════════════════════════════════════
# 3. INDEX DETAIL VIEW  —  `indice <name>`  (green / healthy)
# ════════════════════════════════════════════════════════════════════

def nord_indice_detail_green():
    """Simulates `indice .ds-logs-2026.04.14-000001` with Nord theming."""

    separator("NORD — indice detail (green / healthy)")

    subtitle = Text()
    subtitle.append("Docs: ", style="default")
    subtitle.append("12,345,678", style=FROST_BLUE)
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("5p", style=FROST_SKY)
    subtitle.append("/", style="default")
    subtitle.append("1r", style=FROST_STEEL)
    subtitle.append(" | Size: ", style="default")
    subtitle.append("8.5gb", style=FROST_BLUE)
    subtitle.append(" / ", style="default")
    subtitle.append("17.0gb", style=FROST_BLUE)
    subtitle.append(" | Status: ", style="default")
    subtitle.append("Open", style=AURORA_GREEN)
    subtitle.append(" | ILM: ", style="default")
    subtitle.append("logs-policy", style=FROST_SKY)
    subtitle.append(" (", style="default")
    subtitle.append("🔥 Hot", style=FROST_SKY)
    subtitle.append(")", style="default")

    title_panel = Panel(
        Text("🟢 .ds-logs-2026.04.14-000001 — Healthy (All Shards Assigned)",
             style=f"bold {AURORA_GREEN}", justify="center"),
        title=Text("📋 Index Details", style=f"bold {FROST_SKY}"),
        subtitle=subtitle,
        border_style=FROST_STEEL,
        padding=(1, 2),
    )

    # Settings
    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column("Label", style=f"bold {NORD4}", no_wrap=True)
    info.add_column("Icon", justify="left", width=3)
    info.add_column("Value", style=NORD5, no_wrap=True)
    info.add_row("UUID:", "🆔", "f7e8d9c0-b1a2-3456-7890-abcdef012345")
    info.add_row("Created:", "📅", "2026-04-14 00:00:01")
    info.add_row("Version:", "🔩", "8170099")
    info.add_row("ILM Policy:", "📋", Text("logs-policy", style=FROST_SKY))
    info.add_row("ILM Phase:", "🔥", Text("Hot", style=FROST_SKY))
    info.add_row("Shards:", "🔢", "5 primary / 1 replica")

    info_panel = Panel(
        info,
        title=f"[bold {NORD6}]🔩 Settings[/bold {NORD6}]",
        border_style=FROST_STEEL,
        padding=(1, 2),
    )

    # Shard overview
    sh = Table(show_header=False, box=None, padding=(0, 1))
    sh.add_column("Label", style=f"bold {NORD4}", no_wrap=True)
    sh.add_column("Icon", justify="left", width=3)
    sh.add_column("Value", no_wrap=True)
    sh.add_row("Total Shards:", "📊", Text("10", style=NORD5))
    sh.add_row("Primary:", "🔑", Text("5 Started", style=AURORA_GREEN))
    sh.add_row("Replica:", "📋", Text("5 Started", style=AURORA_GREEN))
    sh.add_row("", "", "")
    sh.add_row("node-1:", "💻", Text("4 shards", style=NORD5))
    sh.add_row("node-2:", "💻", Text("3 shards", style=NORD5))
    sh.add_row("node-3:", "💻", Text("3 shards", style=NORD5))

    sh_panel = Panel(
        sh,
        title=f"[bold {NORD6}]📊 Shard Overview[/bold {NORD6}]",
        border_style=AURORA_GREEN,
        padding=(1, 2),
    )

    console.print(title_panel)
    console.print()
    console.print(Columns([info_panel, sh_panel], expand=True))
    console.print()

    # Shards table
    shard_table = Table(
        box=box.SIMPLE,
        expand=True,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD0}",
        border_style=FROST_STEEL,
    )
    shard_table.add_column("Shard", justify="center", width=6)
    shard_table.add_column("Type", justify="center", width=10)
    shard_table.add_column("State", justify="left", width=14)
    shard_table.add_column("Node", min_width=20)
    shard_table.add_column("Docs", justify="right", width=12)
    shard_table.add_column("Size", justify="right", width=10)

    shard_rows = [
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

    for i, (shard, stype, node, docs, size) in enumerate(shard_rows):
        type_style = FROST_SKY if stype == "Primary" else FROST_STEEL
        bg = f"on {NORD2}" if i % 2 == 1 else ""
        base = f"{NORD4} {bg}" if bg else NORD4

        shard_table.add_row(
            shard,
            Text(stype, style=f"bold {type_style}"),
            Text("✅ STARTED", style=AURORA_GREEN),
            Text(node, style=NORD4),
            docs,
            size,
            style=base,
        )

    console.print(shard_table)
    console.print()


# ════════════════════════════════════════════════════════════════════
# 4. INDEX DETAIL VIEW  —  `indice <name>`  (red / critical)
# ════════════════════════════════════════════════════════════════════

def nord_indice_detail_red():
    """Simulates `indice temp-reindex-failed` with Nord theming."""

    separator("NORD — indice detail (red / critical)")

    subtitle = Text()
    subtitle.append("Docs: ", style="default")
    subtitle.append("0", style=FROST_BLUE)
    subtitle.append(" | Shards: ", style="default")
    subtitle.append("1p", style=FROST_SKY)
    subtitle.append("/", style="default")
    subtitle.append("1r", style=FROST_STEEL)
    subtitle.append(" | Size: ", style="default")
    subtitle.append("0b", style=FROST_BLUE)
    subtitle.append(" / ", style="default")
    subtitle.append("0b", style=FROST_BLUE)
    subtitle.append(" | Status: ", style="default")
    subtitle.append("Open", style=AURORA_GREEN)

    title_panel = Panel(
        Text("🔴 temp-reindex-failed — 2 Unassigned Shards",
             style=f"bold {AURORA_RED}", justify="center"),
        title=Text("📋 Index Details", style=f"bold {FROST_SKY}"),
        subtitle=subtitle,
        border_style=AURORA_RED,
        padding=(1, 2),
    )

    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column("Label", style=f"bold {NORD4}", no_wrap=True)
    info.add_column("Icon", justify="left", width=3)
    info.add_column("Value", style=NORD5, no_wrap=True)
    info.add_row("UUID:", "🆔", "dead0000-beef-0000-cafe-000000000000")
    info.add_row("Created:", "📅", "2026-04-14 22:15:00")
    info.add_row("Version:", "🔩", "8170099")
    info.add_row("ILM Policy:", "❌", Text("None", style=f"dim {NORD3}"))
    info.add_row("Shards:", "🔢", "1 primary / 1 replica")

    info_panel = Panel(
        info,
        title=f"[bold {NORD6}]🔩 Settings[/bold {NORD6}]",
        border_style=FROST_STEEL,
        padding=(1, 2),
    )

    sh = Table(show_header=False, box=None, padding=(0, 1))
    sh.add_column("Label", style=f"bold {NORD4}", no_wrap=True)
    sh.add_column("Icon", justify="left", width=3)
    sh.add_column("Value", no_wrap=True)
    sh.add_row("Total Shards:", "📊", Text("2", style=NORD5))
    sh.add_row("Primary:", "🔑", Text("1 Unassigned", style=AURORA_RED))
    sh.add_row("Replica:", "📋", Text("1 Unassigned", style=AURORA_RED))
    sh.add_row("", "", "")
    sh.add_row("Unassigned:", "🔶", Text("2 shards", style=AURORA_RED))

    sh_panel = Panel(
        sh,
        title=f"[bold {NORD6}]📊 Shard Overview[/bold {NORD6}]",
        border_style=AURORA_RED,
        padding=(1, 2),
    )

    console.print(title_panel)
    console.print()
    console.print(Columns([info_panel, sh_panel], expand=True))
    console.print()

    # Shards table
    shard_table = Table(
        box=box.SIMPLE,
        expand=True,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD0}",
        border_style=FROST_STEEL,
    )
    shard_table.add_column("Shard", justify="center", width=6)
    shard_table.add_column("Type", justify="center", width=10)
    shard_table.add_column("State", justify="left", width=14)
    shard_table.add_column("Node", min_width=20)
    shard_table.add_column("Docs", justify="right", width=12)
    shard_table.add_column("Size", justify="right", width=10)

    shard_table.add_row(
        "0",
        Text("Primary", style=f"bold {FROST_SKY}"),
        Text("❌ UNASSIGNED", style=AURORA_RED),
        Text("—", style=NORD3),
        "—", "—",
        style=NORD4,
    )
    shard_table.add_row(
        "0",
        Text("Replica", style=f"bold {FROST_STEEL}"),
        Text("❌ UNASSIGNED", style=AURORA_RED),
        Text("—", style=NORD3),
        "—", "—",
        style=f"{NORD4} on {NORD2}",
    )

    console.print(shard_table)
    console.print()


# ════════════════════════════════════════════════════════════════════
# 5. PALETTE REFERENCE CARD
# ════════════════════════════════════════════════════════════════════

def nord_palette_card():
    """Shows the Nord color mapping used throughout."""

    separator("NORD — palette reference")

    card = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style=f"bold {NORD6} on {NORD0}",
        border_style=FROST_STEEL,
        title=f"[bold {FROST_SKY}]🧊 Nord Palette Mapping[/bold {FROST_SKY}]",
        expand=True,
    )
    card.add_column("Role", style=f"bold {NORD4}", width=20)
    card.add_column("Rich Color", width=22)
    card.add_column("Nord Token", width=14)
    card.add_column("Preview", width=30)

    mappings = [
        ("Border / Secondary", FROST_STEEL, "nord9",  "━━━━━━━━━━━━━━━━━━━━"),
        ("Title / Primary",    FROST_SKY,   "nord7",  "📊 Elasticsearch Indices"),
        ("Info / Links",       FROST_BLUE,  "nord10", "cornflower_blue"),
        ("Success / Green",    AURORA_GREEN, "nord8",  "◉ Green  ✅ STARTED"),
        ("Warning / Yellow",   AURORA_YELLOW,"nord13", "◐ Yellow  🟡 Warm"),
        ("Error / Red",        AURORA_RED,   "nord11", "○ Red  ❌ UNASSIGNED"),
        ("Default Text",       NORD4,        "nord4",  "light_steel_blue body text"),
        ("Bright Text",        NORD5,        "nord5",  "grey82 values"),
        ("Muted / Dim",        NORD3,        "nord3",  "grey35 comments"),
        ("Zebra Row BG",       NORD2,        "nord2",  "grey30 alternating rows"),
        ("Header BG",          NORD0,        "nord0",  "grey23 table headers"),
    ]

    for role, color, token, preview in mappings:
        card.add_row(
            role,
            Text(color, style=f"bold {color}"),
            Text(token, style=f"dim {NORD4}"),
            Text(preview, style=color),
        )

    console.print(card)
    console.print()


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    console.print()
    console.print(
        Panel(
            Text("Nord Theme Preview — Indices Commands\n\n"
                 "This preview shows how the Nord arctic palette transforms\n"
                 "the indices list and detail views. All colors map to the\n"
                 "official Nord palette using Rich-compatible color names.",
                 style=NORD4, justify="center"),
            title=f"[bold {FROST_SKY}]🧊 NORD THEME PREVIEW[/bold {FROST_SKY}]",
            border_style=FROST_STEEL,
            padding=(1, 4),
        )
    )

    nord_palette_card()
    nord_indices_list()
    nord_indice_detail_yellow()
    nord_indice_detail_green()
    nord_indice_detail_red()

    console.print()
    console.rule(f"[dim {NORD3}]end of preview[/dim {NORD3}]", style=NORD3)
    console.print()
