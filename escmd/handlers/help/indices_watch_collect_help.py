"""
Help content for indices-watch-collect.
"""

from .base_help_content import BaseHelpContent


class IndicesWatchCollectHelpContent(BaseHelpContent):
    """Help for periodic index stats sampling."""

    def get_topic_name(self) -> str:
        return "indices-watch-collect"

    def get_topic_description(self) -> str:
        return "Sample index stats on an interval (JSON) for ingest analysis"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("indices-watch-collect",              "Poll _cat/indices and write one JSON file per sample",           "./escmd.py -l iad41-c03 indices-watch-collect")
        commands_table.add_row("--interval SEC",                     "Seconds between samples (default: 60)",                         "")
        commands_table.add_row("--duration SEC",                     "Stop after N seconds (omit = run until Ctrl+C)",                "")
        commands_table.add_row("--output-dir PATH",                  "Override directory (else ESCMD_INDEX_WATCH_DIR or default tree)","")
        commands_table.add_row("<regex> (positional)",               "Optional index filter (same semantics as indices command)",      "")
        commands_table.add_row("--status green|yellow|red",          "Restrict to indices with that health",                          "")
        commands_table.add_row("--retries N",                        "Attempts per host per sample (default: 3)",                     "")
        commands_table.add_row("--retry-delay SEC",                  "Pause between retries (default: 2)",                            "")

        usage_table.add_row("📋 Overview:", "Polls _cat/indices on a fixed interval")
        usage_table.add_row("   Default path:",  "~/.escmd/index-watch/<location>/<UTC-date>/")
        usage_table.add_row("   Multi-cluster:", "Multiple clusters and days stay separated automatically")
        usage_table.add_row("   Failover:",      "Use hostname3 in YAML for a third coordinator on timeout")
        usage_table.add_row("   Retry order:",   "Each sample retries across elastic_host, elastic_host2, elastic_host3")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Quick Examples:", "Common usage patterns")
        usage_table.add_row("   5 min every 30s:",   "./escmd.py -l iad41-c03 indices-watch-collect --interval 30 --duration 300")
        usage_table.add_row("   Filter + health:",   "./escmd.py -l prod indices-watch-collect 'logs-.*' --status green")
        usage_table.add_row("   Fixed folder:",      "./escmd.py -l prod indices-watch-collect --output-dir /tmp/watch-run")
        usage_table.add_row("   Analyze results:",   "./escmd.py help indices-watch-report")

        self._display_help_panels(
            commands_table, examples_table,
            "📡 indices-watch-collect Flags", "",
            usage_table, "🎯 Overview & Examples"
        )
