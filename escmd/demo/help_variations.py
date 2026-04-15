#!/usr/bin/env python3
"""
Three variations of the --help zebra table.
Run: python3 demo/help_variations.py
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.rule import Rule

console = Console()
VERSION = "3.12.0"

COMMANDS = [
    ("🏥 Cluster & Health",  "green",        "health",                  "Cluster health status",                   "./escmd.py health"),
    ("🏥 Cluster & Health",  "green",        "health-detail",           "Full health dashboard",                   "./escmd.py health-detail"),
    ("🏥 Cluster & Health",  "green",        "cluster-check",           "Comprehensive cluster checks",            "./escmd.py cluster-check"),
    ("🏥 Cluster & Health",  "green",        "ping",                    "Test connectivity",                       "./escmd.py ping"),
    ("🏥 Cluster & Health",  "green",        "nodes",                   "List all nodes",                          "./escmd.py nodes"),
    ("🏥 Cluster & Health",  "green",        "masters",                 "Master-eligible nodes",                   "./escmd.py masters"),
    ("🏥 Cluster & Health",  "green",        "current-master",          "Show active master node",                 "./escmd.py current-master"),
    ("🏥 Cluster & Health",  "green",        "recovery",                "Monitor shard recovery jobs",             "./escmd.py recovery"),
    ("📑 Index Management",  "blue",         "indices",                 "List & manage indices",                   "./escmd.py indices"),
    ("📑 Index Management",  "blue",         "indice",                  "Single index detail",                     "./escmd.py indice <name>"),
    ("📑 Index Management",  "blue",         "create-index",            "Create a new index",                      "./escmd.py create-index <name>"),
    ("📑 Index Management",  "blue",         "freeze / unfreeze",       "Freeze or unfreeze an index",             "./escmd.py freeze <name>"),
    ("📑 Index Management",  "blue",         "flush",                   "Flush index",                             "./escmd.py flush <name>"),
    ("📑 Index Management",  "blue",         "set-replicas",            "Set replica count",                       "./escmd.py set-replicas <name> 1"),
    ("📑 Index Management",  "blue",         "dangling",                "List/manage dangling indices",            "./escmd.py dangling"),
    ("📋 Templates",         "cyan",         "templates",               "List all index templates",                "./escmd.py templates"),
    ("📋 Templates",         "cyan",         "template",                "Show template detail",                    "./escmd.py template <name>"),
    ("📋 Templates",         "cyan",         "template-create",         "Create template from JSON",               "./escmd.py template-create <file>"),
    ("📋 Templates",         "cyan",         "template-modify",         "Modify a template field",                 "./escmd.py template-modify <name>"),
    ("📋 Templates",         "cyan",         "template-backup",         "Backup a template",                       "./escmd.py template-backup <name>"),
    ("📋 Templates",         "cyan",         "template-restore",        "Restore template from backup",            "./escmd.py template-restore <name>"),
    ("💾 Storage & Shards",  "cyan",         "storage",                 "Disk usage per node",                     "./escmd.py storage"),
    ("💾 Storage & Shards",  "cyan",         "shards",                  "Shard distribution",                      "./escmd.py shards"),
    ("💾 Storage & Shards",  "cyan",         "shard-colocation",        "Primary/replica on same host",            "./escmd.py shard-colocation"),
    ("💾 Storage & Shards",  "cyan",         "allocation",              "Allocation settings & explain",           "./escmd.py allocation explain <index>"),
    ("💾 Storage & Shards",  "cyan",         "exclude / exclude-reset", "Exclude or reset index from host",        "./escmd.py exclude <index> <host>"),
    ("💾 Storage & Shards",  "cyan",         "snapshots",               "Manage snapshots",                        "./escmd.py snapshots"),
    ("💾 Storage & Shards",  "cyan",         "repositories",            "Snapshot repositories",                   "./escmd.py repositories"),
    ("📊 Analytics",         "yellow",       "indices-analyze",         "Rollover series outlier analysis",        "./escmd.py indices-analyze"),
    ("📊 Analytics",         "yellow",       "indices-s3-estimate",     "S3 monthly cost estimate",                "./escmd.py indices-s3-estimate"),
    ("📊 Analytics",         "yellow",       "indices-watch-collect",   "Sample index stats to JSON on interval",  "./escmd.py indices-watch-collect"),
    ("📊 Analytics",         "yellow",       "indices-watch-report",    "Summarize collected watch samples",       "./escmd.py indices-watch-report"),
    ("📊 Analytics",         "yellow",       "es-top",                  "Live auto-refreshing cluster dashboard",  "./escmd.py es-top"),
    ("🔄 ILM & Lifecycle",   "yellow",       "ilm",                     "ILM policies & status",                   "./escmd.py ilm"),
    ("🔄 ILM & Lifecycle",   "yellow",       "datastreams",             "Datastream list & detail",                "./escmd.py datastreams"),
    ("🔄 ILM & Lifecycle",   "yellow",       "rollover",                "Rollover a datastream",                   "./escmd.py rollover <name>"),
    ("🔄 ILM & Lifecycle",   "yellow",       "auto-rollover",           "Rollover the biggest shard",              "./escmd.py auto-rollover"),
    ("🔄 ILM & Lifecycle",   "yellow",       "action",                  "Run action sequences",                    "./escmd.py action run <name>"),
    ("🔩 Settings & Config", "white",        "cluster-settings",        "View/manage cluster settings",            "./escmd.py cluster-settings"),
    ("🔩 Settings & Config", "white",        "set",                     "Set a setting via dot notation",          "./escmd.py set cluster.routing.allocation.enable all"),
    ("🔩 Settings & Config", "white",        "show-settings",           "Show current tool config",                "./escmd.py show-settings"),
    ("🔩 Settings & Config", "white",        "locations",               "All configured clusters",                 "./escmd.py locations"),
    ("🔩 Settings & Config", "white",        "get-default / set-default","Show or change default cluster",         "./escmd.py set-default sjc01"),
    ("🔩 Settings & Config", "white",        "set-theme / themes",      "Change or browse colour themes",          "./escmd.py set-theme dark"),
    ("🛠  Utilities",        "bright_black", "version",                 "Version & system info",                   "./escmd.py version"),
    ("🛠  Utilities",        "bright_black", "help",                    "Detailed help for a command",             "./escmd.py help <command>"),
    ("🔐 Security",          "red",          "store-password",          "Store encrypted password",                "./escmd.py store-password"),
    ("🔐 Security",          "red",          "list-stored-passwords",   "List stored password environments",       "./escmd.py list-stored-passwords"),
    ("🔐 Security",          "red",          "remove-stored-password",  "Remove a stored password",                "./escmd.py remove-stored-password <env>"),
    ("🔐 Security",          "red",          "generate-master-key",     "Generate a new master key",               "./escmd.py generate-master-key"),
    ("🔐 Security",          "red",          "rotate-master-key",       "Rotate master key & re-encrypt",          "./escmd.py rotate-master-key"),
    ("🔐 Security",          "red",          "clear-session",           "Clear session cache",                     "./escmd.py clear-session"),
    ("🔐 Security",          "red",          "session-info",            "Show session cache info",                 "./escmd.py session-info"),
]

TOTAL = len(COMMANDS)

def footer():
    t = Text(justify="center")
    t.append("-l <cluster>", style="bold yellow")
    t.append("  target cluster  ·  ", style="dim")
    t.append("--format json", style="bold yellow")
    t.append("  machine output  ·  ", style="dim")
    t.append("--pager", style="bold yellow")
    t.append("  page output  ·  ", style="dim")
    t.append("./escmd.py help <cmd>", style="bold yellow")
    t.append("  per-command help", style="dim")
    console.print(Panel(Align.center(t), border_style="dim", padding=(0, 1)))
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# VARIATION A — section dividers between categories (bold coloured rule row)
# ─────────────────────────────────────────────────────────────────────────────

def variation_a():
    console.rule("[bold cyan] Variation A — Category divider rows [/bold cyan]")
    console.print()

    tbl = Table(
        expand=True,
        show_header=True,
        header_style="bold white on grey23",
        border_style="grey23",
        show_lines=False,
        pad_edge=True,
        padding=(0, 1),
    )
    tbl.add_column("Command",     style="bold",     no_wrap=True, min_width=26)
    tbl.add_column("Description", style="white")
    tbl.add_column("Example",     style="dim cyan", no_wrap=True)

    prev_cat = None
    for cat, colour, cmd, desc, example in COMMANDS:
        if cat != prev_cat:
            # Full-width category divider row
            cat_text = Text(f"  {cat}", style=f"bold {colour} on grey15")
            tbl.add_row(cat_text, Text("", style=f"on grey15"), Text("", style=f"on grey15"),
                        style=f"on grey15")
            prev_cat = cat
        tbl.add_row(cmd, desc, example)

    console.print(Panel(tbl,
        title=f"[bold white]📖 All Commands[/bold white]  [dim]({TOTAL} total)[/dim]",
        border_style="dim", padding=(0, 0),
    ))
    console.print()
    footer()


# ─────────────────────────────────────────────────────────────────────────────
# VARIATION B — zebra striping + category label only on first row of group
# ─────────────────────────────────────────────────────────────────────────────

def variation_b():
    console.rule("[bold cyan] Variation B — Zebra + category label on first row [/bold cyan]")
    console.print()

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
    tbl.add_column("Category",    style="dim",      no_wrap=True, min_width=22)
    tbl.add_column("Command",     style="bold",     no_wrap=True, min_width=26)
    tbl.add_column("Description", style="white")
    tbl.add_column("Example",     style="dim cyan", no_wrap=True)

    prev_cat = None
    for cat, colour, cmd, desc, example in COMMANDS:
        cat_cell = Text(cat, style=f"bold {colour}") if cat != prev_cat else Text("")
        cmd_cell = Text(cmd, style=f"bold {colour}")
        tbl.add_row(cat_cell, cmd_cell, desc, example)
        prev_cat = cat

    console.print(Panel(tbl,
        title=f"[bold white]📖 All Commands[/bold white]  [dim]({TOTAL} total)[/dim]",
        border_style="dim", padding=(0, 0),
    ))
    console.print()
    footer()


# ─────────────────────────────────────────────────────────────────────────────
# VARIATION C — category colour fills entire row background (grouped blocks)
# ─────────────────────────────────────────────────────────────────────────────

# Map each category to a subtle dark background tint
CAT_BG = {
    "🏥 Cluster & Health":  "on grey11",
    "📑 Index Management":  "",
    "📋 Templates":         "on grey11",
    "💾 Storage & Shards":  "",
    "📊 Analytics":         "on grey11",
    "🔄 ILM & Lifecycle":   "",
    "🔩 Settings & Config": "on grey11",
    "🛠  Utilities":        "",
    "🔐 Security":          "on grey11",
}

def variation_c():
    console.rule("[bold cyan] Variation C — Alternating category background blocks [/bold cyan]")
    console.print()

    tbl = Table(
        expand=True,
        show_header=True,
        header_style="bold white on grey23",
        border_style="grey23",
        show_lines=False,
        pad_edge=True,
        padding=(0, 1),
    )
    tbl.add_column("Category",    no_wrap=True, min_width=22)
    tbl.add_column("Command",     no_wrap=True, min_width=26)
    tbl.add_column("Description")
    tbl.add_column("Example",     no_wrap=True)

    prev_cat = None
    for cat, colour, cmd, desc, example in COMMANDS:
        bg = CAT_BG.get(cat, "")
        cat_cell = Text(cat,  style=f"bold {colour} {bg}") if cat != prev_cat else Text("", style=bg)
        cmd_cell = Text(cmd,  style=f"bold {colour} {bg}")
        dsc_cell = Text(desc, style=f"white {bg}")
        ex_cell  = Text(example, style=f"dim cyan {bg}")
        tbl.add_row(cat_cell, cmd_cell, dsc_cell, ex_cell)
        prev_cat = cat

    console.print(Panel(tbl,
        title=f"[bold white]📖 All Commands[/bold white]  [dim]({TOTAL} total)[/dim]",
        border_style="dim", padding=(0, 0),
    ))
    console.print()
    footer()


if __name__ == "__main__":
    console.print()
    variation_a()
    variation_b()
    variation_c()
