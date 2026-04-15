#!/usr/bin/env python3
"""
Preview of --help as a single full-width zebra-striped table.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text

console = Console()
VERSION = "3.12.0"

# ── all commands with category, description, example ─────────────────────────

COMMANDS = [
    # category, command, description, example
    ("🏥 Cluster & Health",      "health",                  "Cluster health status",                          "./escmd.py health"),
    ("🏥 Cluster & Health",      "health-detail",           "Full health dashboard",                          "./escmd.py health-detail"),
    ("🏥 Cluster & Health",      "cluster-check",           "Comprehensive cluster checks",                   "./escmd.py cluster-check"),
    ("🏥 Cluster & Health",      "ping",                    "Test connectivity",                              "./escmd.py ping"),
    ("🏥 Cluster & Health",      "nodes",                   "List all nodes",                                 "./escmd.py nodes"),
    ("🏥 Cluster & Health",      "masters",                 "Master-eligible nodes",                          "./escmd.py masters"),
    ("🏥 Cluster & Health",      "current-master",          "Show active master node",                        "./escmd.py current-master"),
    ("🏥 Cluster & Health",      "recovery",                "Monitor shard recovery jobs",                    "./escmd.py recovery"),

    ("📑 Index Management",      "indices",                 "List & manage indices",                          "./escmd.py indices"),
    ("📑 Index Management",      "indice",                  "Single index detail",                            "./escmd.py indice <name>"),
    ("📑 Index Management",      "create-index",            "Create a new index",                             "./escmd.py create-index <name>"),
    ("📑 Index Management",      "freeze",                  "Freeze an index",                                "./escmd.py freeze <name>"),
    ("📑 Index Management",      "unfreeze",                "Unfreeze an index",                              "./escmd.py unfreeze <name>"),
    ("📑 Index Management",      "flush",                   "Flush index",                                    "./escmd.py flush <name>"),
    ("📑 Index Management",      "set-replicas",            "Set replica count",                              "./escmd.py set-replicas <name> <n>"),
    ("📑 Index Management",      "dangling",                "List/manage dangling indices",                   "./escmd.py dangling"),
    ("📑 Index Management",      "indice-add-metadata",     "Add metadata to an index",                       "./escmd.py indice-add-metadata <name>"),

    ("📋 Templates",             "templates",               "List all index templates",                       "./escmd.py templates"),
    ("📋 Templates",             "template",                "Show template detail",                           "./escmd.py template <name>"),
    ("📋 Templates",             "template-create",         "Create template from JSON",                      "./escmd.py template-create <file>"),
    ("📋 Templates",             "template-modify",         "Modify a template field",                        "./escmd.py template-modify <name>"),
    ("📋 Templates",             "template-backup",         "Backup a template",                              "./escmd.py template-backup <name>"),
    ("📋 Templates",             "template-restore",        "Restore template from backup",                   "./escmd.py template-restore <name>"),
    ("📋 Templates",             "template-usage",          "Analyse template usage",                         "./escmd.py template-usage"),
    ("📋 Templates",             "list-backups",            "List available template backups",                "./escmd.py list-backups"),

    ("💾 Storage & Shards",      "storage",                 "Disk usage per node",                            "./escmd.py storage"),
    ("💾 Storage & Shards",      "shards",                  "Shard distribution",                             "./escmd.py shards"),
    ("💾 Storage & Shards",      "shard-colocation",        "Primary/replica on same host",                   "./escmd.py shard-colocation"),
    ("💾 Storage & Shards",      "allocation",              "Allocation settings & explain",                  "./escmd.py allocation explain <index>"),
    ("💾 Storage & Shards",      "exclude",                 "Exclude index from host",                        "./escmd.py exclude <index> <host>"),
    ("💾 Storage & Shards",      "exclude-reset",           "Reset exclusion settings",                       "./escmd.py exclude-reset <index>"),

    ("📸 Snapshots",             "snapshots",               "Manage snapshots",                               "./escmd.py snapshots"),
    ("📸 Snapshots",             "repositories",            "Snapshot repositories",                          "./escmd.py repositories"),

    ("📊 Analytics",             "indices-analyze",         "Rollover series outlier analysis",               "./escmd.py indices-analyze"),
    ("📊 Analytics",             "indices-s3-estimate",     "S3 monthly cost estimate",                       "./escmd.py indices-s3-estimate"),
    ("📊 Analytics",             "indices-watch-collect",   "Sample index stats to JSON on interval",         "./escmd.py indices-watch-collect"),
    ("📊 Analytics",             "indices-watch-report",    "Summarize collected watch samples",              "./escmd.py indices-watch-report"),
    ("📊 Analytics",             "es-top",                  "Live auto-refreshing cluster dashboard",         "./escmd.py es-top"),

    ("🔄 ILM & Lifecycle",       "ilm",                     "ILM policies & status",                          "./escmd.py ilm"),
    ("🔄 ILM & Lifecycle",       "datastreams",             "Datastream list & detail",                       "./escmd.py datastreams"),
    ("🔄 ILM & Lifecycle",       "rollover",                "Rollover a datastream",                          "./escmd.py rollover <name>"),
    ("🔄 ILM & Lifecycle",       "auto-rollover",           "Rollover the biggest shard",                     "./escmd.py auto-rollover"),
    ("🔄 ILM & Lifecycle",       "action",                  "Run action sequences",                           "./escmd.py action run <name>"),

    ("🔩 Settings & Config",     "cluster-settings",        "View/manage cluster settings",                   "./escmd.py cluster-settings"),
    ("🔩 Settings & Config",     "set",                     "Set a setting via dot notation",                 "./escmd.py set cluster.routing.allocation.enable all"),
    ("🔩 Settings & Config",     "show-settings",           "Show current tool config",                       "./escmd.py show-settings"),
    ("🔩 Settings & Config",     "locations",               "All configured clusters",                        "./escmd.py locations"),
    ("🔩 Settings & Config",     "get-default",             "Show default cluster",                           "./escmd.py get-default"),
    ("🔩 Settings & Config",     "set-default",             "Change default cluster",                         "./escmd.py set-default sjc01"),
    ("🔩 Settings & Config",     "cluster-groups",          "Display cluster groups",                         "./escmd.py cluster-groups"),
    ("🔩 Settings & Config",     "set-username",            "Set default username",                           "./escmd.py set-username admin"),
    ("🔩 Settings & Config",     "set-theme",               "Change colour theme",                            "./escmd.py set-theme dark"),
    ("🔩 Settings & Config",     "themes",                  "Browse available themes",                        "./escmd.py themes"),

    ("🛠  Utilities",            "version",                 "Version & system info",                          "./escmd.py version"),
    ("🛠  Utilities",            "help",                    "Detailed help for a command",                    "./escmd.py help <command>"),

    ("🔐 Security",              "store-password",          "Store encrypted password",                       "./escmd.py store-password"),
    ("🔐 Security",              "list-stored-passwords",   "List stored password environments",              "./escmd.py list-stored-passwords"),
    ("🔐 Security",              "remove-stored-password",  "Remove a stored password",                       "./escmd.py remove-stored-password <env>"),
    ("🔐 Security",              "generate-master-key",     "Generate a new master key",                      "./escmd.py generate-master-key"),
    ("🔐 Security",              "rotate-master-key",       "Rotate master key & re-encrypt",                 "./escmd.py rotate-master-key"),
    ("🔐 Security",              "migrate-to-env-key",      "Migrate to environment variable key",            "./escmd.py migrate-to-env-key"),
    ("🔐 Security",              "clear-session",           "Clear session cache",                            "./escmd.py clear-session"),
    ("🔐 Security",              "session-info",            "Show session cache info",                        "./escmd.py session-info"),
    ("🔐 Security",              "set-session-timeout",     "Set session timeout (minutes)",                  "./escmd.py set-session-timeout 30"),
]

# colour per category
CAT_COLOUR = {
    "🏥 Cluster & Health":  "green",
    "📑 Index Management":  "blue",
    "📋 Templates":         "cyan",
    "💾 Storage & Shards":  "cyan",
    "📸 Snapshots":         "magenta",
    "📊 Analytics":         "yellow",
    "🔄 ILM & Lifecycle":   "yellow",
    "🔩 Settings & Config": "white",
    "🛠  Utilities":        "bright_black",
    "🔐 Security":          "red",
}


def render_header():
    t = Text(justify="center")
    t.append("ESCMD ", style="bold white")
    t.append(f"v{VERSION}", style="bold cyan")
    t.append("  ·  Elasticsearch Command Reference", style="dim")
    console.print()
    console.print(Panel(Align.center(t), border_style="dim", padding=(0, 2)))
    console.print()


def render_table():
    tbl = Table(
        expand=True,
        show_header=True,
        header_style="bold white on grey23",
        border_style="grey23",
        row_styles=["", "on grey7"],   # zebra: normal / very subtle dark row
        show_lines=False,
        pad_edge=True,
        padding=(0, 1),
    )

    tbl.add_column("Category",    style="dim",         no_wrap=True, min_width=22)
    tbl.add_column("Command",     style="bold",        no_wrap=True, min_width=26)
    tbl.add_column("Description", style="white",       no_wrap=False)
    tbl.add_column("Example",     style="dim cyan",    no_wrap=True)

    prev_cat = None
    for cat, cmd, desc, example in COMMANDS:
        colour = CAT_COLOUR.get(cat, "white")

        # Print category label only on first row of each group
        cat_cell = Text(cat, style=f"bold {colour}") if cat != prev_cat else Text("")
        cmd_cell = Text(cmd, style=f"bold {colour}")

        tbl.add_row(cat_cell, cmd_cell, desc, example)
        prev_cat = cat

    console.print(Panel(tbl,
        title="[bold white]📖 All Commands[/bold white]",
        border_style="dim",
        padding=(0, 0),
    ))
    console.print()


def render_footer():
    t = Text(justify="center")
    t.append("-l <cluster>", style="bold yellow")
    t.append("  target a specific cluster  ·  ", style="dim")
    t.append("--format json", style="bold yellow")
    t.append("  machine-readable output  ·  ", style="dim")
    t.append("--pager", style="bold yellow")
    t.append("  page long output  ·  ", style="dim")
    t.append("./escmd.py help <cmd>", style="bold yellow")
    t.append("  detailed per-command help", style="dim")
    console.print(Panel(Align.center(t), border_style="dim", padding=(0, 1)))
    console.print()


if __name__ == "__main__":
    render_header()
    render_table()
    render_footer()
