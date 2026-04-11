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
        return "Live auto-refreshing Elasticsearch cluster dashboard (like Unix top)"

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

        flags = Table.grid(padding=(0, 3))
        flags.add_column(style=help_styles.get("command", "bold cyan"), min_width=22)
        flags.add_column(style=help_styles.get("description", "white"))
        flags.add_row("--interval SEC", "Refresh interval in seconds (default: 30, minimum: 10)")
        flags.add_row("--top-nodes N",  "Number of nodes to show ranked by heap % (default: 5)")
        flags.add_row("--top-indices N", "Number of active indices to show ranked by docs/sec (default: 10)")

        config = Table.grid(padding=(0, 3))
        config.add_column(style=help_styles.get("command", "bold cyan"), min_width=22)
        config.add_column(style=help_styles.get("description", "white"))
        config.add_row("es_top.interval",     "Default refresh interval (seconds)")
        config.add_row("es_top.top_nodes",    "Default node panel row count")
        config.add_row("es_top.top_indices",  "Default index hot list row count")

        config_example = Table.grid(padding=(0, 2))
        config_example.add_column(style=help_styles.get("example", "green"))
        config_example.add_row("# escmd.yml — settings block")
        config_example.add_row("settings:")
        config_example.add_row("  es_top:")
        config_example.add_row("    interval: 30")
        config_example.add_row("    top_nodes: 5")
        config_example.add_row("    top_indices: 20")

        panels_table = Table.grid(padding=(0, 3))
        panels_table.add_column(style=help_styles.get("command", "bold cyan"), min_width=22)
        panels_table.add_column(style=help_styles.get("description", "white"))
        panels_table.add_row("Cluster Header",  "Status (green/yellow/red), node counts, shard counts. Unassigned shards flash red.")
        panels_table.add_row("Top Nodes",       "JVM heap %, CPU %, load avg, disk used %, disk free. Heap ≥85% → red. Disk ≥85% → yellow, ≥90% → red.")
        panels_table.add_row("Index Hot List",  "Docs/sec and searches/sec (delta between polls). Session totals accumulate across all cycles. Only indices with activity are shown.")

        examples = Table.grid(padding=(0, 3))
        examples.add_column(style=help_styles.get("example", "green"), min_width=46)
        examples.add_column(style=help_styles.get("description", "dim white"))
        examples.add_row("./escmd.py es-top",                              "Default cluster, 30s refresh")
        examples.add_row("./escmd.py -l prod es-top",                      "Specific cluster")
        examples.add_row("./escmd.py es-top --interval 15",                "15s refresh")
        examples.add_row("./escmd.py es-top --top-nodes 10",               "Show top 10 nodes")
        examples.add_row("./escmd.py es-top --top-indices 20",             "Show top 20 indices")
        examples.add_row("./escmd.py -l prod es-top --interval 10 --top-indices 5", "Combined flags")

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
