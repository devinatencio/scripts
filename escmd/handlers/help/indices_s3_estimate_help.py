"""
Help content for indices-s3-estimate.
"""

from rich.panel import Panel
from rich.table import Table

from .base_help_content import BaseHelpContent


class IndicesS3EstimateHelpContent(BaseHelpContent):
    """Help for primary-size S3 monthly cost estimate."""

    def get_topic_name(self) -> str:
        return "indices-s3-estimate"

    def get_topic_description(self) -> str:
        return "Rough monthly S3 cost from primary store sizes in a rollover date window"

    def show_help(self) -> None:
        help_styles, border_style = self._get_theme_styles()

        overview = Table.grid(padding=(0, 2))
        overview.add_column(style=help_styles.get("description", "white"))
        overview.add_row(
            "Sums pri.store.size (bytes from _cat/indices) for indices whose names match the "
            "same dated rollover pattern as indices-analyze (...-YYYY.MM.DD-NNNNNN, including "
            ".ds- data stream backing indices). Only indices with rollover date on or after "
            "(UTC today - --within-days) are included. Replicas are excluded (single-copy basis). "
            "Applies an optional buffer percent, then multiplies by your USD/GiB-month price. "
            "Also shows cumulative buffered size and cost for months 2 and 3 assuming the same "
            "monthly slice accrues each month (2× and 3× GiB × price). "
            "This is a planning estimate, not an AWS bill; snapshot size may differ."
        )

        flags = Table.grid(padding=(0, 3))
        flags.add_column(style=help_styles.get("command", "bold cyan"), min_width=26)
        flags.add_column(style=help_styles.get("description", "white"))
        flags.add_row("regex (positional)", "Optional index filter (same semantics as indices)")
        flags.add_row("--format json|table", "Human table or JSON")
        flags.add_row("--status green|yellow|red", "Only indices with that cluster health")
        flags.add_row(
            "--within-days N",
            "Rollover date in name must be within last N UTC calendar days (default: 30)",
        )
        flags.add_row(
            "--buffer-percent P",
            "Scale bytes by (1 + P/100) before pricing (default: 0; try 10 for headroom)",
        )
        flags.add_row(
            "--price-per-gib-month USD",
            "Required. Price per gibibyte-month (1024^3 bytes), e.g. S3 Standard",
        )
        flags.add_row(
            "--include-undated",
            "Add indices without YYYY.MM.DD in the name (risk of double-count; use carefully)",
        )

        examples = Table.grid(padding=(0, 3))
        examples.add_column(style=help_styles.get("example", "green"), min_width=56)
        examples.add_column(style=help_styles.get("description", "dim white"))
        examples.add_row(
            "./escmd.py indices-s3-estimate --price-per-gib-month 0.023",
            "Last 30d dated indices, S3 Standard example rate",
        )
        examples.add_row(
            "./escmd.py indices-s3-estimate 'logs-*' --price-per-gib-month 0.023 --buffer-percent 10",
            "Pattern + 10% buffer",
        )
        examples.add_row(
            "./escmd.py indices-s3-estimate --within-days 7 --price-per-gib-month 0.023 --format json",
            "JSON for scripts",
        )
        examples.add_row(
            "./escmd.py help indices-analyze",
            "Same rollover date rules as analyze",
        )

        self.console.print()
        self.console.print(
            Panel(
                overview,
                title=f"[{help_styles.get('header', 'bold magenta')}]indices-s3-estimate[/{help_styles.get('header', 'bold magenta')}]",
                subtitle="Live cluster; uses current primary sizes only",
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
