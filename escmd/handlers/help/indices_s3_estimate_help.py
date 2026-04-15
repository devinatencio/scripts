"""
Help content for indices-s3-estimate.
"""

from .base_help_content import BaseHelpContent


class IndicesS3EstimateHelpContent(BaseHelpContent):
    """Help for primary-size S3 monthly cost estimate."""

    def get_topic_name(self) -> str:
        return "indices-s3-estimate"

    def get_topic_description(self) -> str:
        return "Rough monthly S3 cost from primary store sizes in a rollover date window"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("indices-s3-estimate",                "Estimate S3 cost for last 30d dated indices",                    "./escmd.py indices-s3-estimate --price-per-gib-month 0.023")
        commands_table.add_row("indices-s3-estimate <regex>",        "Optional index filter (same semantics as indices)",              "")
        commands_table.add_row("--format json|table",                "Human table or JSON",                                           "")
        commands_table.add_row("--status green|yellow|red",          "Only indices with that cluster health",                         "")
        commands_table.add_row("--within-days N",                    "Rollover date within last N UTC calendar days (default: 30)",   "")
        commands_table.add_row("--buffer-percent P",                 "Scale bytes by (1 + P/100) before pricing (default: 0)",        "")
        commands_table.add_row("--price-per-gib-month USD",          "Required. Price per GiB-month (1024^3 bytes)",                  "")
        commands_table.add_row("--include-undated",                  "Add indices without YYYY.MM.DD in the name (use carefully)",    "")

        usage_table.add_row("📋 Overview:", "Sums pri.store.size for dated rollover indices")
        usage_table.add_row("   Pattern:",       "Same dated rollover pattern as indices-analyze")
        usage_table.add_row("   Replicas:",      "Excluded — single-copy basis only")
        usage_table.add_row("   Buffer:",        "Optional buffer percent scales bytes before pricing")
        usage_table.add_row("   Projections:",   "Shows cumulative cost for months 2 and 3 (2× and 3× GiB × price)")
        usage_table.add_row("   Note:",          "Planning estimate only — snapshot size may differ from AWS bill")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Quick Examples:", "Common usage patterns")
        usage_table.add_row("   S3 Standard rate:",   "./escmd.py indices-s3-estimate --price-per-gib-month 0.023")
        usage_table.add_row("   Pattern + buffer:",   "./escmd.py indices-s3-estimate 'logs-*' --price-per-gib-month 0.023 --buffer-percent 10")
        usage_table.add_row("   Last 7d JSON:",       "./escmd.py indices-s3-estimate --within-days 7 --price-per-gib-month 0.023 --format json")
        usage_table.add_row("   Related command:",    "./escmd.py help indices-analyze")

        self._display_help_panels(
            commands_table, examples_table,
            "💰 indices-s3-estimate Flags", "",
            usage_table, "🎯 Overview & Examples"
        )
