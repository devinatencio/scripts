#!/usr/bin/env python3
"""
Health (short) facelift preview.

Run:  python3 demo/health_facelift_preview.py

Shows BEFORE (current) and AFTER (proposed) for the quick `health` command
using the active theme from escmd.json / themes.yml.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.rule import Rule
from rich import box

from display.theme_manager import ThemeManager
from display.style_system import StyleSystem


# ── bootstrap theme ───────────────────────────────────────────────────────────

class _Cfg:
    def __init__(self, theme):
        self._t = theme
        self.default_settings = {}
    def get_display_theme(self):
        return self._t

def _theme():
    try:
        with open("escmd.json") as f:
            return json.load(f).get("display_theme", "rich")
    except Exception:
        return "rich"

cfg = _Cfg(_theme())
tm = ThemeManager(configuration_manager=cfg)
ss = StyleSystem(theme_manager=tm)
console = Console()
styles = tm.get_theme_styles()

def sem(k, fb="white"):
    return ss.get_semantic_style(k)

def border():
    return tm.get_themed_style("table_styles", "border_style", "white")

def title_s():
    return tm.get_themed_style("panel_styles", "title", "bold cyan")

def muted():
    return sem("muted")


# ── fake data ─────────────────────────────────────────────────────────────────

HEALTH = {
    "cluster_name": "sjc01-prod",
    "status": "green",
    "cluster_version": {"number": "8.17.4"},
    "number_of_nodes": 24,
    "number_of_data_nodes": 18,
    "active_primary_shards": 1842,
    "active_shards": 3684,
    "unassigned_shards": 0,
    "relocating_shards": 0,
    "initializing_shards": 0,
    "number_of_indices": 312,
    "number_of_pending_tasks": 0,
    "number_of_in_flight_fetch": 2,
    "delayed_unassigned_shards": 0,
    "timed_out": False,
}


# ══════════════════════════════════════════════════════════════════════════════
#  BEFORE  – exact reproduction of handle_health() rendering
# ══════════════════════════════════════════════════════════════════════════════

def render_before():
    primary       = sem("primary")
    success       = sem("success")
    warning       = sem("warning")
    error         = sem("error")
    info          = sem("info")
    _muted        = muted()
    _border       = border()
    label_style   = "bold white"
    health_styles = styles.get("health_styles", {})
    type_styles   = styles.get("type_styles", {})
    row_styles    = styles.get("row_styles", {})
    normal        = row_styles.get("normal", "bright_white")
    primary_shard = type_styles.get("primary", {}).get("text", "bright_cyan")
    replica_shard = type_styles.get("replica", {}).get("text", "bright_blue")

    status       = HEALTH["status"]
    cluster_name = HEALTH["cluster_name"]
    version_str  = HEALTH["cluster_version"]["number"]
    total_nodes  = HEALTH["number_of_nodes"]
    data_nodes   = HEALTH["number_of_data_nodes"]
    primary_s    = HEALTH["active_primary_shards"]
    total_shards = HEALTH["active_shards"]
    replicas     = total_shards - primary_s
    unassigned   = HEALTH["unassigned_shards"]
    relocating   = HEALTH["relocating_shards"]
    initializing = HEALTH["initializing_shards"]
    index_count  = HEALTH["number_of_indices"]

    status_icon  = "🟢"
    status_style = health_styles.get("green", {}).get("text", success)

    def make_section():
        t = Table.grid(padding=(0, 2))
        t.add_column(justify="left", no_wrap=True, width=4)
        t.add_column(justify="left", no_wrap=True, width=16)
        t.add_column(justify="left")
        return t

    def add_row(t, icon, label, value_text):
        t.add_row(icon, Text(label, style=label_style), value_text)

    outer = Table.grid(padding=(0, 0))
    outer.add_column(ratio=1)

    # Section 1: Cluster + Nodes
    s1 = make_section()
    cluster_val = Text()
    cluster_val.append(cluster_name, style=primary)
    cluster_val.append(f"  v{version_str}", style=_muted)
    add_row(s1, "🏢", "Cluster", cluster_val)

    status_val = Text()
    status_val.append(f"{status_icon} {status.upper()}", style=status_style)
    add_row(s1, "📊", "Status", status_val)

    nodes_val = Text()
    nodes_val.append(str(total_nodes), style=normal)
    nodes_val.append("  data: ", style=_muted)
    nodes_val.append(str(data_nodes), style=success)
    other = total_nodes - data_nodes
    if other > 0:
        nodes_val.append("  master: ", style=_muted)
        nodes_val.append(str(other), style=warning)
    add_row(s1, "💻", "Nodes", nodes_val)
    outer.add_row(s1)

    # Section 2: Indices + Shards
    outer.add_row(Rule(style=_muted))
    s2 = make_section()
    add_row(s2, "📂", "Indices", Text(f"{index_count:,}", style=normal))

    shards_val = Text()
    shards_val.append(str(total_shards), style=normal)
    shards_val.append("  primary: ", style=_muted)
    shards_val.append(str(primary_s), style=primary_shard)
    shards_val.append("  replicas: ", style=_muted)
    shards_val.append(str(replicas), style=replica_shard)
    add_row(s2, "🔵", "Shards", shards_val)

    add_row(s2, "✅", "Unassigned", Text("0  all assigned", style=success))
    outer.add_row(s2)

    title_style_v = styles.get("panel_styles", {}).get("title", "bold white")
    panel = Panel(
        outer,
        title=f"[{title_style_v}]⚡ Cluster Health[/{title_style_v}]",
        border_style="green",
        padding=(1, 3),
    )
    console.print()
    console.print(panel)
    console.print()


# ══════════════════════════════════════════════════════════════════════════════
#  AFTER  – proposed changes for the short health panel
# ══════════════════════════════════════════════════════════════════════════════
#
#  1. Inline status bar in the panel title (cluster + status at a glance)
#  2. Consistent label column using semantic primary (not hardcoded bold white)
#  3. Compact shard bar showing primary/replica ratio visually
#  4. Subtle footer hint for health-detail
#  5. All styles fully semantic — no styles.get() chains
# ──────────────────────────────────────────────────────────────────────────────

def _bar(filled: int, total: int, width: int = 20) -> Text:
    """Compact themed progress bar."""
    pct = (filled / total * 100) if total else 0
    f = int(pct / 100 * width)
    e = width - f
    if pct >= 95:
        c = f"bold {sem('success')}"
    elif pct >= 70:
        c = f"bold {sem('warning')}"
    else:
        c = f"bold {sem('error')}"
    b = Text()
    b.append("█" * f, style=c)
    b.append("░" * e, style=muted())
    b.append(f" {pct:.0f}%", style=c)
    return b


def render_after():
    _primary   = sem("primary")
    _success   = sem("success")
    _warning   = sem("warning")
    _info      = sem("info")
    _muted     = muted()
    _secondary = sem("secondary")

    status       = HEALTH["status"]
    cluster_name = HEALTH["cluster_name"]
    version_str  = HEALTH["cluster_version"]["number"]
    total_nodes  = HEALTH["number_of_nodes"]
    data_nodes   = HEALTH["number_of_data_nodes"]
    primary_s    = HEALTH["active_primary_shards"]
    total_shards = HEALTH["active_shards"]
    replicas     = total_shards - primary_s
    unassigned   = HEALTH["unassigned_shards"]
    index_count  = HEALTH["number_of_indices"]

    status_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(status, "⚪")
    sem_key     = {"green": "success", "yellow": "warning", "red": "error"}.get(status, "muted")

    # ── Build the panel title with inline status ──
    t_style = title_s()
    panel_title = Text()
    panel_title.append("⚡ ", style=t_style)
    panel_title.append(cluster_name, style=f"bold {_primary}")
    panel_title.append(f"  {status_icon} {status.upper()}", style=f"bold {sem(sem_key)}")

    # ── Label + value grid ──
    label_s = f"bold {_primary}"

    def section():
        t = Table.grid(padding=(0, 2))
        t.add_column(justify="left", no_wrap=True, min_width=4)   # icon
        t.add_column(justify="left", no_wrap=True, min_width=16, style=label_s)  # label
        t.add_column(justify="left")                               # value
        return t

    outer = Table.grid(padding=(0, 0))
    outer.add_column(ratio=1)

    # ── Cluster ──
    s1 = section()

    ver_val = Text()
    ver_val.append(f"v{version_str}", style=_info)
    s1.add_row("🔧", "Version", ver_val)

    nodes_val = Text.assemble(
        (str(total_nodes), f"bold {sem('neutral')}"),
        (" total  ", _muted),
        (str(data_nodes), f"bold {_success}"),
        (" data  ", _muted),
        (str(total_nodes - data_nodes), f"bold {_warning}"),
        (" master/coord", _muted),
    )
    s1.add_row("💻", "Nodes", nodes_val)
    outer.add_row(s1)

    # ── Indices + Shards ──
    outer.add_row(Rule(style=_muted))
    s2 = section()

    s2.add_row("📂", "Indices", Text(f"{index_count:,}", style=f"bold {sem('neutral')}"))

    shards_val = Text.assemble(
        (f"{total_shards:,}", f"bold {sem('neutral')}"),
        ("  pri ", _muted),
        (f"{primary_s:,}", f"bold {_secondary}"),
        ("  rep ", _muted),
        (f"{replicas:,}", f"bold {_info}"),
    )
    s2.add_row("🔵", "Shards", shards_val)

    # Shard assignment bar
    assigned = total_shards - unassigned
    if unassigned > 0:
        assign_text = Text.assemble(
            _bar(assigned, total_shards, 16),
            ("  ", ""),
            (f"  {unassigned:,} unassigned", f"bold {sem('error')}"),
        )
        s2.add_row("🔴", "Assignment", assign_text)
    else:
        assign_text = Text.assemble(
            _bar(assigned, total_shards, 16),
            ("  ", ""),
            ("all assigned", _success),
        )
        s2.add_row("✅", "Assignment", assign_text)

    outer.add_row(s2)

    # ── Footer hint ──
    outer.add_row(Rule(style=_muted))
    footer = Text()
    footer.append("💡 ", style=f"bold {sem('warning')}")
    footer.append("Run ", style=_muted)
    footer.append("health-detail", style=f"bold {_info}")
    footer.append(" for full dashboard with snapshots, recovery & performance", style=_muted)
    ft = Table.grid()
    ft.add_column(ratio=1)
    ft.add_row(footer)
    outer.add_row(ft)

    panel = Panel(
        outer,
        title=panel_title,
        border_style=sem(sem_key),
        padding=(1, 3),
    )
    console.print()
    console.print(panel)
    console.print()


# ══════════════════════════════════════════════════════════════════════════════
#  YELLOW cluster — shows how warnings render
# ══════════════════════════════════════════════════════════════════════════════

def render_after_yellow():
    """Same layout but with a yellow cluster to show warning styling."""
    _primary   = sem("primary")
    _success   = sem("success")
    _warning   = sem("warning")
    _info      = sem("info")
    _muted     = muted()
    _secondary = sem("secondary")

    status       = "yellow"
    cluster_name = "ewr02-staging"
    version_str  = "8.15.2"
    total_nodes  = 12
    data_nodes   = 9
    primary_s    = 924
    total_shards = 1848
    replicas     = total_shards - primary_s
    unassigned   = 14
    index_count  = 187

    status_icon = "🟡"
    sem_key     = "warning"

    t_style = title_s()
    panel_title = Text()
    panel_title.append("⚡ ", style=t_style)
    panel_title.append(cluster_name, style=f"bold {_primary}")
    panel_title.append(f"  {status_icon} {status.upper()}", style=f"bold {sem(sem_key)}")

    label_s = f"bold {_primary}"

    def section():
        t = Table.grid(padding=(0, 2))
        t.add_column(justify="left", no_wrap=True, min_width=4)
        t.add_column(justify="left", no_wrap=True, min_width=16, style=label_s)
        t.add_column(justify="left")
        return t

    outer = Table.grid(padding=(0, 0))
    outer.add_column(ratio=1)

    s1 = section()
    s1.add_row("🔧", "Version", Text(f"v{version_str}", style=_info))

    nodes_val = Text.assemble(
        (str(total_nodes), f"bold {sem('neutral')}"),
        (" total  ", _muted),
        (str(data_nodes), f"bold {_success}"),
        (" data  ", _muted),
        (str(total_nodes - data_nodes), f"bold {_warning}"),
        (" master/coord", _muted),
    )
    s1.add_row("💻", "Nodes", nodes_val)
    outer.add_row(s1)

    outer.add_row(Rule(style=_muted))
    s2 = section()
    s2.add_row("📂", "Indices", Text(f"{index_count:,}", style=f"bold {sem('neutral')}"))

    shards_val = Text.assemble(
        (f"{total_shards:,}", f"bold {sem('neutral')}"),
        ("  pri ", _muted),
        (f"{primary_s:,}", f"bold {_secondary}"),
        ("  rep ", _muted),
        (f"{replicas:,}", f"bold {_info}"),
    )
    s2.add_row("🔵", "Shards", shards_val)

    assigned = total_shards - unassigned
    assign_text = Text.assemble(
        _bar(assigned, total_shards, 16),
        ("  ", ""),
        (f"  {unassigned:,} unassigned", f"bold {sem('error')}"),
    )
    s2.add_row("🔴", "Assignment", assign_text)

    # Unassigned reasons
    reason_text = Text()
    reason_text.append("└─ ", style=_muted)
    reason_text.append("NODE_LEFT: 8", style=_warning)
    reason_text.append(", ", style=_muted)
    reason_text.append("ALLOCATION_FAILED: 6", style=_warning)
    s2.add_row("", "", reason_text)

    outer.add_row(s2)

    outer.add_row(Rule(style=_muted))
    footer = Text()
    footer.append("💡 ", style=f"bold {sem('warning')}")
    footer.append("Run ", style=_muted)
    footer.append("health-detail", style=f"bold {_info}")
    footer.append(" for full dashboard with snapshots, recovery & performance", style=_muted)
    ft = Table.grid()
    ft.add_column(ratio=1)
    ft.add_row(footer)
    outer.add_row(ft)

    panel = Panel(
        outer,
        title=panel_title,
        border_style=sem(sem_key),
        padding=(1, 3),
    )
    console.print()
    console.print(panel)
    console.print()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY
# ══════════════════════════════════════════════════════════════════════════════

def _divider(label, style_key):
    console.print(Align.center(Text("━" * 70, style=muted())))
    console.print(Align.center(Text(label, style=f"bold {sem(style_key)}")))
    console.print(Align.center(Text("━" * 70, style=muted())))


if __name__ == "__main__":
    console.print()
    _divider("BEFORE  —  current ./escmd.py health", "warning")
    render_before()

    _divider("AFTER  —  proposed ./escmd.py health  (green cluster)", "success")
    render_after()

    _divider("AFTER  —  proposed ./escmd.py health  (yellow cluster)", "warning")
    render_after_yellow()
