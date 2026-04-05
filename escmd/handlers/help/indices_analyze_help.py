"""
Help content for indices-analyze.
"""

from rich.panel import Panel
from rich.table import Table

from .base_help_content import BaseHelpContent


class IndicesAnalyzeHelpContent(BaseHelpContent):
    """Help for rollover-series doc/size outlier analysis."""

    def get_topic_name(self) -> str:
        return "indices-analyze"

    def get_topic_description(self) -> str:
        return "Rollover backing indices whose doc count beats sibling medians"

    def show_help(self) -> None:
        help_styles, border_style = self._get_theme_styles()

        overview = Table.grid(padding=(0, 2))
        overview.add_column(style=help_styles.get("description", "white"))
        overview.add_row(
            "Groups indices whose names match a dated rollover pattern "
            "(...-YYYY.MM.DD-NNNNNN, including .ds- data stream backing indices). "
            "For each index, compares docs.count to the leave-one-out median of its siblings "
            "in the same base pattern. Rows are outliers when docs are at least --min-ratio "
            "times that median (default 5). Store size vs peer median is shown for context. "
            "Results sort by highest docs ratio first. Requires a live Elasticsearch connection "
            "(_cat/indices via the same path as ./escmd.py indices)."
        )

        flags = Table.grid(padding=(0, 3))
        flags.add_column(style=help_styles.get("command", "bold cyan"), min_width=26)
        flags.add_column(style=help_styles.get("description", "white"))
        flags.add_row("regex (positional)", "Optional index filter (same semantics as indices)")
        flags.add_row("--format json|table", "Human table or JSON summary + rows")
        flags.add_row("--status green|yellow|red", "Only indices with that cluster health")
        flags.add_row(
            "--min-peers N",
            "Need at least N other backing indices in the series (default: 1)",
        )
        flags.add_row(
            "--min-ratio R",
            "Only show when docs >= R times peer median docs (default: 5)",
        )
        flags.add_row(
            "--min-docs N",
            "Outlier must have at least N documents (default: 1000000; 0 disables)",
        )
        flags.add_row("--top N", "Keep only top N rows by docs ratio after sort")
        flags.add_row(
            "--within-days N",
            "Only outliers whose rollover date in the name is within last N UTC calendar days",
        )
        flags.add_row("--pager", "Force pager (also follows config paging rules)")

        examples = Table.grid(padding=(0, 3))
        examples.add_column(style=help_styles.get("example", "green"), min_width=52)
        examples.add_column(style=help_styles.get("description", "dim white"))
        examples.add_row(
            "./escmd.py indices-analyze",
            "Default cluster",
        )
        examples.add_row(
            "./escmd.py -l prod indices-analyze 'logs-*'",
            "Regex + location",
        )
        examples.add_row(
            "./escmd.py indices-analyze k_fluent_bit --min-ratio 2",
            "min-ratio 2",
        )
        examples.add_row(
            "./escmd.py indices-analyze k_fluent_bit --min-docs 0",
            "min-docs 0",
        )
        examples.add_row(
            "./escmd.py indices-analyze k_fluent_bit --within-days 7",
            "Last 7d by name",
        )
        examples.add_row(
            "./escmd.py indices-analyze --format json",
            "JSON output",
        )
        examples.add_row(
            "./escmd.py help indices",
            "More index commands",
        )

        self.console.print()
        self.console.print(
            Panel(
                overview,
                title=f"[{help_styles.get('header', 'bold magenta')}]indices-analyze[/{help_styles.get('header', 'bold magenta')}]",
                subtitle="Live cluster; pairs with indices-watch-* for time-sampled ingest",
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
