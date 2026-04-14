"""
Help content for es-top — live Elasticsearch cluster dashboard.
"""

from rich.panel import Panel
from rich.table import Table

from .base_help_content import BaseHelpContent


class EsTopHelpContent(BaseHelpContent):
    """Help for the es-top live terminal dashboard."""

    def get_topic_name(self) -> str:
        return "es-top"

    def get_topic_description(self) -> str:
        return "Live auto-refreshing Elasticsearch cluster dashboard (like Unix top)  [alias: top]"

    def show_help(self) -> None:
        help_styles, border_style = self._get_theme_styles()

        overview = Table.grid(padding=(0, 2))
        overview.add_column(style=help_styles.get("description", "white"))
        overview.add_row(
            "Launches a full-screen, auto-refreshing terminal dashboard modelled after "
            "the Unix top command. Polls the cluster at a configurable interval and "
            "displays three live panels: cluster health header, top nodes by JVM heap "
            "pressure, and an index hot list showing docs/sec, searches/sec, and "
            "cumulative session totals since es-top started. Exit cleanly with Ctrl+C."
        )
        overview.add_row("")
        overview.add_row("Available as both [bold cyan]es-top[/bold cyan] and [bold cyan]top[/bold cyan] — both commands are identical.")
        overview.add_row("")
        overview.add_row(
            "Pass [bold cyan]--collect[/bold cyan] to write a JSON snapshot to disk on every poll cycle "
            "(same format as [bold cyan]indices-watch-collect[/bold cyan]). When you exit, run "
            "[bold cyan]indices-watch-report[/bold cyan] against the saved directory to analyze ingest "
            "rates, HOT indices, and peer comparisons — no Elasticsearch connection required."
        )

        flags = Table.grid(padding=(0, 3))
        flags.add_column(style=help_styles.get("command", "bold cyan"), min_width=22)
        flags.add_column(style=help_styles.get("description", "white"))
        flags.add_row("--interval SEC", "Refresh interval in seconds (default: 30, minimum: 10)")
        flags.add_row("--top-nodes N",  "Number of nodes to show ranked by heap % (default: 5)")
        flags.add_row("--top-indices N", "Number of active indices to show ranked by docs/sec (default: 10)")
        flags.add_row("--collect",       "Write index stats snapshots to disk each poll cycle (same format as indices-watch-collect). Use indices-watch-report to analyze afterward.")
        flags.add_row("--collect-dir PATH", "Directory for --collect snapshots (default: ~/.escmd/index-watch/<cluster>/<UTC-date>/)")

        config = Table.grid(padding=(0, 3))
        config.add_column(style=help_styles.get("command", "bold cyan"), min_width=24)
        config.add_column(style=help_styles.get("description", "white"))
        config.add_row("es_top.interval",       "Default refresh interval (seconds)")
        config.add_row("es_top.top_nodes",      "Default node panel row count")
        config.add_row("es_top.top_indices",    "Default index hot list row count")
        config.add_row("es_top.hot_indicator",  "How to flag the hottest index — emoji | color | both | none")

        config_example = Table.grid(padding=(0, 2))
        config_example.add_column(style=help_styles.get("example", "green"))
        config_example.add_row("# escmd.yml")
        config_example.add_row("es_top:")
        config_example.add_row("  interval: 30")
        config_example.add_row("  top_nodes: 5")
        config_example.add_row("  top_indices: 20")
        config_example.add_row("  hot_indicator: emoji   # emoji | color | both | none")

        panels_table = Table.grid(padding=(0, 3))
        panels_table.add_column(style=help_styles.get("command", "bold cyan"), min_width=22)
        panels_table.add_column(style=help_styles.get("description", "white"))
        panels_table.add_row("Cluster Header",  "Status pill (● GREEN/YELLOW/RED), cluster name, node counts, shard breakdown. Unassigned shards flash red.")
        panels_table.add_row("Top Nodes",       "JVM heap, CPU, and disk shown as progress bars. Heap ≥70% → yellow, ≥85% → red. Disk ≥85% → yellow, ≥90% → red.")
        panels_table.add_row("Index Hot List",  "Docs/sec and searches/sec (delta between polls). Session totals accumulate across all cycles.")
        panels_table.add_row("Hot Indicator",   "Flags the busiest index after its name. 🔥 = #1 by docs/sec, 🌡 = #2. Controlled by hot_indicator in escmd.yml.")

        examples = Table.grid(padding=(0, 3))
        examples.add_column(style=help_styles.get("example", "green"), min_width=52)
        examples.add_column(style=help_styles.get("description", "dim white"))
        examples.add_row("./escmd.py es-top",                                        "Default cluster, 30s refresh")
        examples.add_row("./escmd.py top",                                           "Same — short alias")
        examples.add_row("./escmd.py -l prod es-top",                                "Specific cluster")
        examples.add_row("./escmd.py -l prod top",                                   "Same with alias")
        examples.add_row("./escmd.py es-top --interval 15",                          "15s refresh")
        examples.add_row("./escmd.py es-top --top-nodes 10",                         "Show top 10 nodes")
        examples.add_row("./escmd.py es-top --top-indices 20",                       "Show top 20 indices")
        examples.add_row("./escmd.py -l prod es-top --interval 10 --top-indices 5",  "Combined flags")
        examples.add_row("./escmd.py -l prod top --collect",                         "Collect snapshots to default path while watching")
        examples.add_row("./escmd.py -l prod top --collect --collect-dir /tmp/run",  "Collect to a custom directory")
        examples.add_row("./escmd.py -l prod indices-watch-report",                  "Analyze collected snapshots after exiting top")

        self.console.print()
        self.console.print(
            Panel(
                overview,
                title=f"[{help_styles.get('header', 'bold magenta')}]es-top — Live Cluster Dashboard[/{help_styles.get('header', 'bold magenta')}]",
                subtitle="Full-screen monitor · exit with Ctrl+C",
                border_style=border_style,
                padding=(1, 2),
            )
        )
        self.console.print()
        self.console.print(
            Panel(
                flags,
                title=f"[{help_styles.get('subheader', 'bold blue')}]CLI Flags[/{help_styles.get('subheader', 'bold blue')}]",
                border_style=border_style,
                padding=(1, 2),
            )
        )
        self.console.print()
        self.console.print(
            Panel(
                panels_table,
                title=f"[{help_styles.get('subheader', 'bold blue')}]Dashboard Panels[/{help_styles.get('subheader', 'bold blue')}]",
                border_style=border_style,
                padding=(1, 2),
            )
        )
        self.console.print()
        self.console.print(
            Panel(
                config_example,
                title=f"[{help_styles.get('subheader', 'bold blue')}]escmd.yml Configuration[/{help_styles.get('subheader', 'bold blue')}]",
                subtitle="CLI flags override config values; config values override built-in defaults",
                border_style=border_style,
                padding=(1, 2),
            )
        )
        self.console.print()
        self.console.print(
            Panel(
                examples,
                title=f"[{help_styles.get('subheader', 'bold blue')}]Examples[/{help_styles.get('subheader', 'bold blue')}]",
                border_style=border_style,
                padding=(1, 2),
            )
        )
        self.console.print()
