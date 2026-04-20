"""
Help system module for escmd.
Provides a full-width zebra table with alternating category background blocks.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.text import Text


# Alternating dark background tints — every other category gets a subtle shade
_CAT_BG = [
    "",          # cat 0 — default terminal bg
    "on grey7",  # cat 1 — very subtle dark
    "",
    "on grey7",
    "",
    "on grey7",
    "",
    "on grey7",
    "",
    "on grey7",
]

_COMMANDS = [
    # (category, colour, command, description, example)
    ("🏥 Cluster & Health",  "green",        "health",                  "Cluster health status",                          "./escmd.py health"),
    ("🏥 Cluster & Health",  "green",        "health-detail",           "Full health dashboard",                          "./escmd.py health-detail"),
    ("🏥 Cluster & Health",  "green",        "cluster-check",           "Comprehensive cluster checks",                   "./escmd.py cluster-check"),
    ("🏥 Cluster & Health",  "green",        "ping",                    "Test connectivity",                              "./escmd.py ping"),
    ("🏥 Cluster & Health",  "green",        "nodes",                   "List all nodes",                                 "./escmd.py nodes"),
    ("🏥 Cluster & Health",  "green",        "masters",                 "Master-eligible nodes",                          "./escmd.py masters"),
    ("🏥 Cluster & Health",  "green",        "current-master",          "Show active master node",                        "./escmd.py current-master"),
    ("🏥 Cluster & Health",  "green",        "recovery",                "Monitor shard recovery jobs",                    "./escmd.py recovery"),

    ("📑 Index Management",  "blue",         "indices",                 "List & manage indices",                          "./escmd.py indices"),
    ("📑 Index Management",  "blue",         "indice",                  "Single index detail",                            "./escmd.py indice <name>"),
    ("📑 Index Management",  "blue",         "create-index",            "Create a new index",                             "./escmd.py create-index <name>"),
    ("📑 Index Management",  "blue",         "freeze / unfreeze",       "Freeze or unfreeze an index",                    "./escmd.py freeze <name>"),
    ("📑 Index Management",  "blue",         "flush",                   "Flush index",                                    "./escmd.py flush <name>"),
    ("📑 Index Management",  "blue",         "set-replicas",            "Set replica count",                              "./escmd.py set-replicas <name> 1"),
    ("📑 Index Management",  "blue",         "dangling",                "List/manage dangling indices",                   "./escmd.py dangling"),
    ("📑 Index Management",  "blue",         "indice-add-metadata",     "Add metadata to an index",                       "./escmd.py indice-add-metadata <name>"),

    ("📋 Templates",         "cyan",         "templates",               "List all index templates",                       "./escmd.py templates"),
    ("📋 Templates",         "cyan",         "template",                "Show template detail",                           "./escmd.py template <name>"),
    ("📋 Templates",         "cyan",         "template-create",         "Create template from JSON",                      "./escmd.py template-create <file>"),
    ("📋 Templates",         "cyan",         "template-modify",         "Modify a template field",                        "./escmd.py template-modify <name>"),
    ("📋 Templates",         "cyan",         "template-backup",         "Backup a template",                              "./escmd.py template-backup <name>"),
    ("📋 Templates",         "cyan",         "template-restore",        "Restore template from backup",                   "./escmd.py template-restore <name>"),
    ("📋 Templates",         "cyan",         "template-usage",          "Analyse template usage across indices",          "./escmd.py template-usage"),
    ("📋 Templates",         "cyan",         "list-backups",            "List available template backups",                "./escmd.py list-backups"),

    ("💾 Storage & Shards",  "cyan",         "storage",                 "Disk usage per node",                            "./escmd.py storage"),
    ("💾 Storage & Shards",  "cyan",         "shards",                  "Shard distribution",                             "./escmd.py shards"),
    ("💾 Storage & Shards",  "cyan",         "shard-colocation",        "Primary/replica on same host",                   "./escmd.py shard-colocation"),
    ("💾 Storage & Shards",  "cyan",         "allocation",              "Allocation settings & explain",                  "./escmd.py allocation explain <index>"),
    ("💾 Storage & Shards",  "cyan",         "exclude / exclude-reset", "Exclude or reset index from host",               "./escmd.py exclude <index> <host>"),
    ("💾 Storage & Shards",  "cyan",         "snapshots",               "Manage snapshots",                               "./escmd.py snapshots"),
    ("💾 Storage & Shards",  "cyan",         "repositories",            "Snapshot repositories",                          "./escmd.py repositories"),

    ("📊 Analytics",         "yellow",       "indices-analyze",         "Rollover series outlier analysis",               "./escmd.py indices-analyze"),
    ("📊 Analytics",         "yellow",       "indices-s3-estimate",     "S3 monthly cost estimate",                       "./escmd.py indices-s3-estimate"),
    ("📊 Analytics",         "yellow",       "indices-watch-collect",   "Sample index stats to JSON on interval",         "./escmd.py indices-watch-collect"),
    ("📊 Analytics",         "yellow",       "indices-watch-report",    "Summarize collected watch samples",              "./escmd.py indices-watch-report"),
    ("📊 Analytics",         "yellow",       "indices-watch-sessions",  "Manage stored watch sessions",                   "./escmd.py indices-watch-sessions list"),
    ("📊 Analytics",         "yellow",       "es-top",                  "Live auto-refreshing cluster dashboard",         "./escmd.py es-top"),

    ("🔄 ILM & Lifecycle",   "yellow",       "ilm",                     "ILM policies & status",                          "./escmd.py ilm"),
    ("🔄 ILM & Lifecycle",   "yellow",       "datastreams",             "Datastream list & detail",                       "./escmd.py datastreams"),
    ("🔄 ILM & Lifecycle",   "yellow",       "rollover",                "Rollover a datastream",                          "./escmd.py rollover <name>"),
    ("🔄 ILM & Lifecycle",   "yellow",       "auto-rollover",           "Rollover the biggest shard",                     "./escmd.py auto-rollover"),
    ("🔄 ILM & Lifecycle",   "yellow",       "actions",                 "Run action sequences",                           "./escmd.py actions run <name>"),

    ("🔩 Settings & Config", "white",        "cluster-settings",        "View/manage cluster settings",                   "./escmd.py cluster-settings"),
    ("🔩 Settings & Config", "white",        "set",                     "Set a setting via dot notation",                 "./escmd.py set cluster.routing.allocation.enable all"),
    ("🔩 Settings & Config", "white",        "show-settings",           "Show current tool config",                       "./escmd.py show-settings"),
    ("🔩 Settings & Config", "white",        "locations",               "All configured clusters",                        "./escmd.py locations"),
    ("🔩 Settings & Config", "white",        "get-default / set-default","Show or change default cluster",                "./escmd.py set-default sjc01"),
    ("🔩 Settings & Config", "white",        "cluster-groups",          "Display cluster groups",                         "./escmd.py cluster-groups"),
    ("🔩 Settings & Config", "white",        "set-username",            "Set default username",                           "./escmd.py set-username admin"),
    ("🔩 Settings & Config", "white",        "set-theme / themes",      "Change or browse colour themes",                 "./escmd.py set-theme dark"),

    ("🛠  Utilities",        "bright_black", "version",                 "Version & system info",                          "./escmd.py version"),
    ("🛠  Utilities",        "bright_black", "help",                    "Detailed help for a command",                    "./escmd.py help <command>"),

    ("🔐 Security",          "red",          "store-password",          "Store encrypted password",                       "./escmd.py store-password"),
    ("🔐 Security",          "red",          "list-stored-passwords",   "List stored password environments",              "./escmd.py list-stored-passwords"),
    ("🔐 Security",          "red",          "remove-stored-password",  "Remove a stored password",                       "./escmd.py remove-stored-password <env>"),
    ("🔐 Security",          "red",          "generate-master-key",     "Generate a new master key",                      "./escmd.py generate-master-key"),
    ("🔐 Security",          "red",          "rotate-master-key",       "Rotate master key & re-encrypt",                 "./escmd.py rotate-master-key"),
    ("🔐 Security",          "red",          "migrate-to-env-key",      "Migrate to environment variable key",            "./escmd.py migrate-to-env-key"),
    ("🔐 Security",          "red",          "clear-session",           "Clear session cache",                            "./escmd.py clear-session"),
    ("🔐 Security",          "red",          "session-info",            "Show session cache info",                        "./escmd.py session-info"),
    ("🔐 Security",          "red",          "set-session-timeout",     "Set session timeout (minutes)",                  "./escmd.py set-session-timeout 30"),
]


def show_custom_help(config_manager=None):
    """Display full-width command reference table with alternating category blocks."""
    console = Console()
    total = len(_COMMANDS)

    # ── header ────────────────────────────────────────────────────────────────
    try:
        from version import VERSION
    except ImportError:
        VERSION = "3.12.0"

    header = Text(justify="center")
    header.append("ESCMD ", style="bold white")
    header.append(f"v{VERSION}", style="bold cyan")
    header.append("  ·  Elasticsearch Command Reference", style="dim")

    console.print()
    console.print(Panel(Align.center(header), border_style="dim", padding=(0, 2)))
    console.print()

    # ── build category index for background assignment ────────────────────────
    cat_order = []
    for cat, *_ in _COMMANDS:
        if cat not in cat_order:
            cat_order.append(cat)

    # ── table ─────────────────────────────────────────────────────────────────
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
    for cat, colour, cmd, desc, example in _COMMANDS:
        cat_idx = cat_order.index(cat)
        bg = _CAT_BG[cat_idx % len(_CAT_BG)]

        cat_cell = Text(cat,     style=f"bold {colour} {bg}") if cat != prev_cat else Text("", style=bg)
        cmd_cell = Text(cmd,     style=f"bold {colour} {bg}")
        dsc_cell = Text(desc,    style=f"white {bg}")
        ex_cell  = Text(example, style=f"dim cyan {bg}")

        tbl.add_row(cat_cell, cmd_cell, dsc_cell, ex_cell)
        prev_cat = cat

    console.print(Panel(
        tbl,
        title=f"[bold white]📖 All Commands[/bold white]  [dim]({total} total)[/dim]",
        border_style="dim",
        padding=(0, 0),
    ))
    console.print()

    # ── footer ────────────────────────────────────────────────────────────────
    footer = Text(justify="center")
    footer.append("-l <cluster>", style="bold yellow")
    footer.append("  target a specific cluster  ·  ", style="dim")
    footer.append("--format json", style="bold yellow")
    footer.append("  machine-readable output  ·  ", style="dim")
    footer.append("--pager", style="bold yellow")
    footer.append("  page long output  ·  ", style="dim")
    footer.append("./escmd.py help <cmd>", style="bold yellow")
    footer.append("  detailed per-command help", style="dim")

    console.print(Panel(Align.center(footer), border_style="dim", padding=(0, 1)))
    console.print()
