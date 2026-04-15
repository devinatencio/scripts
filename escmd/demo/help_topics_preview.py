#!/usr/bin/env python3
"""
Preview: Variation B table + C-style coloured pill on the topic name.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text

console = Console()

TOPICS = [
    ("🏥 Cluster & Health",  "green",        "health",                "Cluster health monitoring options",                          True),
    ("🏥 Cluster & Health",  "green",        "nodes",                 "Node management and information",                            False),
    ("🏥 Cluster & Health",  "green",        "shards",                "Shard distribution and analysis",                            True),
    ("🏥 Cluster & Health",  "green",        "allocation",            "Shard allocation management",                                True),
    ("📑 Index Management",  "blue",         "indices",               "Index management operations and examples",                   True),
    ("📑 Index Management",  "blue",         "freeze",                "Freeze indices to prevent write operations",                 False),
    ("📑 Index Management",  "blue",         "unfreeze",              "Unfreeze indices to restore write operations",               False),
    ("📑 Index Management",  "blue",         "dangling",              "Dangling index management",                                  False),
    ("📑 Index Management",  "blue",         "exclude",               "Index exclusion from specific hosts",                        False),
    ("📑 Index Management",  "blue",         "indice-add-metadata",   "Add custom metadata to indices",                             False),
    ("📋 Templates",         "cyan",         "templates",             "Index template management operations",                       True),
    ("📋 Templates",         "cyan",         "template-backup",       "Backup an Elasticsearch template to JSON",                   False),
    ("📋 Templates",         "cyan",         "template-modify",       "Modify template fields (set/append/remove/delete)",          False),
    ("📋 Templates",         "cyan",         "template-restore",      "Restore a template from a backup file",                      False),
    ("📊 Analytics",         "yellow",       "indices-analyze",       "Rollover backing indices outlier analysis",                  True),
    ("📊 Analytics",         "yellow",       "indices-s3-estimate",   "Rough monthly S3 cost from primary store sizes",             True),
    ("📊 Analytics",         "yellow",       "indices-watch-collect", "Sample index stats on an interval to JSON",                  True),
    ("📊 Analytics",         "yellow",       "indices-watch-report",  "Summarize watch JSON samples without Elasticsearch",         True),
    ("📊 Analytics",         "yellow",       "es-top",                "Live auto-refreshing cluster dashboard",                     True),
    ("🔄 ILM & Lifecycle",   "yellow",       "ilm",                   "Index Lifecycle Management commands",                        True),
    ("📸 Snapshots",         "magenta",      "snapshots",             "Backup and snapshot operations",                             True),
    ("📸 Snapshots",         "magenta",      "repositories",          "Snapshot repository configuration and management",           False),
    ("🔐 Security",          "red",          "security",              "Password management and security features",                  True),
    ("🔐 Security",          "red",          "store-password",        "Store an encrypted password for an environment",             False),
    ("🛠  Utilities",        "bright_black", "actions",               "Action sequence management and execution",                   True),
]

_CAT_BG = ["", "on grey7", "", "on grey7", "", "on grey7", "", "on grey7"]

from collections import OrderedDict
cat_order = list(OrderedDict.fromkeys(t[0] for t in TOPICS))

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
tbl.add_column("Topic",       no_wrap=True, min_width=28)
tbl.add_column("Description")
tbl.add_column("",            no_wrap=True, width=10)  # badge

prev_cat = None
for cat, colour, topic, desc, detailed in TOPICS:
    cat_idx = cat_order.index(cat)
    bg = _CAT_BG[cat_idx % len(_CAT_BG)]

    # Category cell — label only on first row of group
    cat_cell = Text(cat, style=f"bold {colour} {bg}") if cat != prev_cat else Text("", style=bg)

    # Topic cell — C-style coloured pill: " topic " on coloured bg
    topic_cell = Text()
    topic_cell.append(f" {topic} ", style=f"bold black on {colour}")

    # Description
    desc_cell = Text(desc, style=f"white {bg}")

    # Badge — ● detailed or blank
    if detailed:
        badge = Text()
        badge.append(" detailed ", style=f"dim {colour} {bg}")
    else:
        badge = Text("", style=bg)

    tbl.add_row(cat_cell, topic_cell, desc_cell, badge)
    prev_cat = cat

console.print()
console.print(Panel(
    tbl,
    title=f"[bold white]📚 Help Topics[/bold white]  [dim]({len(TOPICS)} topics)[/dim]",
    border_style="dim",
    padding=(0, 0),
))
console.print()

hint = Text(justify="center")
hint.append("./escmd.py help <topic>", style="bold cyan")
hint.append("  ·  ", style="dim")
hint.append("detailed", style="dim cyan")
hint.append(" = rich subcommand docs available", style="dim")
console.print(Panel(Align.center(hint), border_style="dim", padding=(0, 1)))
console.print()
