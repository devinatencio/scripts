"""
Help content for indices-watch-collect.
"""

from rich.panel import Panel
from rich.table import Table

from .base_help_content import BaseHelpContent


class IndicesWatchCollectHelpContent(BaseHelpContent):
    """Help for periodic index stats sampling."""

    def get_topic_name(self) -> str:
        return "indices-watch-collect"

    def get_topic_description(self) -> str:
        return "Sample index stats on an interval (JSON) for ingest analysis"

    def show_help(self) -> None:
        help_styles, border_style = self._get_theme_styles()

        overview = Table.grid(padding=(0, 2))
        overview.add_column(style=help_styles.get("description", "white"))
        overview.add_row(
            "Polls _cat/indices on a fixed interval and writes one JSON file per sample. "
            "Default directory is ~/.escmd/index-watch/<location>/<UTC-date>/ so multiple "
            "clusters and days stay separated. Use hostname3 in YAML for a third coordinator "
            "when nodes time out; each sample retries across elastic_host, elastic_host2, "
            "elastic_host3."
        )

        flags = Table.grid(padding=(0, 3))
        flags.add_column(style=help_styles.get("command", "bold cyan"), min_width=28)
        flags.add_column(style=help_styles.get("description", "white"))
        flags.add_row("--interval SEC", "Seconds between samples (default: 60)")
        flags.add_row("--duration SEC", "Stop after N seconds (omit = run until Ctrl+C)")
        flags.add_row("--output-dir PATH", "Override directory (else ESCMD_INDEX_WATCH_DIR or default tree)")
        flags.add_row("regex (positional)", "Optional index filter (same semantics as indices command)")
        flags.add_row("--status green|yellow|red", "Restrict to indices with that health")
        flags.add_row("--retries N", "Attempts per host per sample (default: 3)")
        flags.add_row("--retry-delay SEC", "Pause between retries (default: 2)")

        examples = Table.grid(padding=(0, 3))
        examples.add_column(style=help_styles.get("example", "green"), min_width=42)
        examples.add_column(style=help_styles.get("description", "dim white"))
        examples.add_row(
            "./escmd.py -l iad41-c03 indices-watch-collect --interval 30 --duration 300",
            "5 minutes of samples every 30s for that cluster (default path)",
        )
        examples.add_row(
            "./escmd.py -l prod indices-watch-collect 'logs-.*' --status green",
            "Only matching index names and green health",
        )
        examples.add_row(
            "./escmd.py -l prod indices-watch-collect --output-dir /tmp/watch-run",
            "Write snapshots under a fixed folder",
        )
        examples.add_row(
            "./escmd.py help indices-watch-report",
            "How to summarize the files this command creates",
        )

        self.console.print()
        self.console.print(
            Panel(
                overview,
                title=f"[{help_styles.get('header', 'bold magenta')}]indices-watch-collect[/{help_styles.get('header', 'bold magenta')}]",
                subtitle="Requires Elasticsearch; skips heavy index cache at startup",
                border_style=border_style,
                padding=(1, 2),
            )
        )
        self.console.print()
        self.console.print(
            Panel(
                flags,
                title=f"[{help_styles.get('subheader', 'bold blue')}]Flags[/{help_styles.get('subheader', 'bold blue')}]",
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
