"""
Help content for indices-watch-report.
"""

from .base_help_content import BaseHelpContent


class IndicesWatchReportHelpContent(BaseHelpContent):
    """Help for summarizing collected watch samples."""

    def get_topic_name(self) -> str:
        return "indices-watch-report"

    def get_topic_description(self) -> str:
        return "Summarize watch JSON samples (docs/s, HOT) without Elasticsearch"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        # Flags as the commands table (flag | description | example)
        commands_table.add_row("--dir PATH",                    "Explicit sample directory",                                          "")
        commands_table.add_row("--cluster NAME",                "Slug for default path if -l is not used",                           "")
        commands_table.add_row("--date YYYY-MM-DD",             "UTC date folder (default: today UTC)",                              "")
        commands_table.add_row("--format json|table",           "Machine or human output",                                           "")
        commands_table.add_row("--min-docs-delta N",            "Minimum doc increase (Δ docs = 0 always hidden)",                   "")
        commands_table.add_row("--hot-ratio R",                 "HOT when docs/s ≥ R × peer median (default: 2)",                   "")
        commands_table.add_row("--min-peers N",                 "Minimum siblings for rate/med, docs/med, HOT/⚠ (default: 1)",      "")
        commands_table.add_row("--docs-peer-ratio R",           "⚠ when doc count ≥ R × median peer docs; 0 disables (default: 5)", "")
        commands_table.add_row("--top N",                       "Limit to top N rows by sort key",                                   "")
        commands_table.add_row("--rate-stats auto|span|intervals",
                               "auto: interval med/p90/max when ≥3 samples (default); span: full-window only",                      "")

        # Workflow scenarios
        usage_table.add_row("📋 Overview:", "Reads JSON snapshots from indices-watch-collect")
        usage_table.add_row("   What it does:",  "Compares first/last sample for Δ docs and span docs/s")
        usage_table.add_row("   Rate stats:",    "With ≥3 samples: median, p90, max between adjacent snapshots")
        usage_table.add_row("   Peer compare:",  "docs/med and rate/med vs leave-one-out sibling median")
        usage_table.add_row("   ⚠ flag:",        "Marks indices whose doc count ≥ --docs-peer-ratio × peer median")
        usage_table.add_row("   No ES needed:",  "Runs entirely offline from collected JSON files")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Quick Start:", "Typical usage workflow")
        usage_table.add_row("   Step 1 — collect:", "./escmd.py -l iad41-c03 indices-watch-collect")
        usage_table.add_row("   Step 2 — report:",  "./escmd.py -l iad41-c03 indices-watch-report")
        usage_table.add_row("   Offline:",           "./escmd.py indices-watch-report --cluster iad41-c03 --date 2026-03-29")
        usage_table.add_row("   Custom dir:",        "./escmd.py indices-watch-report --dir /path/to/samples --format json")

        self._display_help_panels(
            commands_table, examples_table,
            "📊 indices-watch-report  Flags", "Examples",
            usage_table, "Workflows",
        )
