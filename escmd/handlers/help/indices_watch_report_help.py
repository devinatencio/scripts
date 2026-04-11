"""
Help content for indices-watch-report.
"""

from rich.panel import Panel
from rich.table import Table

from .base_help_content import BaseHelpContent


class IndicesWatchReportHelpContent(BaseHelpContent):
    """Help for summarizing collected watch samples."""

    def get_topic_name(self) -> str:
        return "indices-watch-report"

    def get_topic_description(self) -> str:
        return "Summarize watch JSON samples (docs/s, HOT) without Elasticsearch"

    def show_help(self) -> None:
        help_styles, border_style = self._get_theme_styles()

        overview = Table.grid(padding=(0, 2))
        overview.add_column(style=help_styles.get("description", "white"))
        overview.add_row(
            "Reads JSON snapshots produced by indices-watch-collect, compares the first and "
            "last sample for Δ docs and full-window span docs/s, and (with ≥3 samples, "
            "default --rate-stats auto) summarizes per-interval docs/s as median, p90, and max "
            "between adjacent snapshots. Shows last-sample doc count vs leave-one-out median "
            "sibling doc count (docs/med, like indices-analyze) plus ingest rate vs peers "
            "(rate/med; still based on span docs/s). ⚠ marks indices whose doc count is ≥ "
            "--docs-peer-ratio times the peer median (default 5). No Elasticsearch connection."
        )

        flags = Table.grid(padding=(0, 3))
        flags.add_column(style=help_styles.get("command", "bold cyan"), min_width=26)
        flags.add_column(style=help_styles.get("description", "white"))
        flags.add_row("--dir PATH", "Explicit sample directory")
        flags.add_row("--cluster NAME", "Slug for default path if -l is not used")
        flags.add_row("--date YYYY-MM-DD", "UTC date folder (default: today UTC)")
        flags.add_row("--format json|table", "Machine or human output")
        flags.add_row("--min-docs-delta N", "Minimum doc increase (Δ docs = 0 always hidden)")
        flags.add_row("--hot-ratio R", "HOT when docs/s ≥ R × peer median (default: 2)")
        flags.add_row("--min-peers N", "Minimum siblings for rate/med, docs/med, HOT/⚠ (default: 1)")
        flags.add_row(
            "--docs-peer-ratio R",
            "⚠ when doc count ≥ R × median peer docs (last sample); 0 disables ⚠ (default: 5)",
        )
        flags.add_row(
            "--top N",
            "Limit to top N rows by sort key (median interval docs/s or span docs/s)",
        )
        flags.add_row(
            "--rate-stats auto|span|intervals",
            "auto: interval med/p90/max when ≥3 samples (default); span: full-window only; "
            "intervals: always interval distribution (+ span column in table)",
        )

        examples = Table.grid(padding=(0, 3))
        examples.add_column(style=help_styles.get("example", "green"), min_width=46)
        examples.add_column(style=help_styles.get("description", "dim white"))
        examples.add_row(
            "./escmd.py -l iad41-c03 indices-watch-report",
            "Today’s UTC folder for that location’s default path",
        )
        examples.add_row(
            "./escmd.py indices-watch-report --cluster iad41-c03 --date 2026-03-29",
            "No -l: use slug + date (offline-friendly)",
        )
        examples.add_row(
            "./escmd.py indices-watch-report --dir /path/to/samples --format json",
            "Arbitrary directory, JSON for scripts",
        )
        examples.add_row(
            "./escmd.py help indices-watch-collect",
            "How to record samples first",
        )

        self.console.print()
        self.console.print(
            Panel(
                overview,
                title=f"[{help_styles.get('header', 'bold magenta')}]indices-watch-report[/{help_styles.get('header', 'bold magenta')}]",
                subtitle="No ES connection; pair with indices-watch-collect",
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
