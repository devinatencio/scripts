"""
Help content for indices-analyze.
"""

from .base_help_content import BaseHelpContent


class IndicesAnalyzeHelpContent(BaseHelpContent):
    """Help for rollover-series doc/size outlier analysis."""

    def get_topic_name(self) -> str:
        return "indices-analyze"

    def get_topic_description(self) -> str:
        return "Rollover backing indices whose doc count beats sibling medians"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("indices-analyze",                  "Analyze all rollover series for doc outliers",                    "./escmd.py indices-analyze")
        commands_table.add_row("indices-analyze <regex>",          "Optional index filter (same semantics as indices)",               "./escmd.py indices-analyze 'logs-*'")
        commands_table.add_row("--format json|table",              "Human table or JSON summary + rows",                             "")
        commands_table.add_row("--status green|yellow|red",        "Only indices with that cluster health",                          "")
        commands_table.add_row("--min-peers N",                    "Need at least N other backing indices in the series (default: 1)","")
        commands_table.add_row("--min-ratio R",                    "Only show when docs >= R times peer median docs (default: 5)",   "")
        commands_table.add_row("--min-docs N",                     "Outlier must have at least N documents (default: 1000000)",      "")
        commands_table.add_row("--top N",                          "Keep only top N rows by docs ratio after sort",                  "")
        commands_table.add_row("--within-days N",                  "Only outliers whose rollover date is within last N UTC days",    "")
        commands_table.add_row("--pager",                          "Force pager (also follows config paging rules)",                 "")

        usage_table.add_row("📋 Overview:", "Groups indices matching a dated rollover pattern")
        usage_table.add_row("   Pattern:",       "...YYYY.MM.DD-NNNNNN, including .ds- data stream backing indices")
        usage_table.add_row("   Comparison:",    "Compares docs.count to leave-one-out median of siblings")
        usage_table.add_row("   Outlier rule:",  "Rows shown when docs >= --min-ratio times that median (default 5)")
        usage_table.add_row("   Context:",       "Store size vs peer median shown for context")
        usage_table.add_row("   Sort:",          "Results sort by highest docs ratio first")
        usage_table.add_row("   Requires:",      "Live Elasticsearch connection (_cat/indices)")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Quick Examples:", "Common usage patterns")
        usage_table.add_row("   Default cluster:",  "./escmd.py indices-analyze")
        usage_table.add_row("   Regex + location:", "./escmd.py -l prod indices-analyze 'logs-*'")
        usage_table.add_row("   min-ratio 2:",      "./escmd.py indices-analyze k_fluent_bit --min-ratio 2")
        usage_table.add_row("   min-docs 0:",       "./escmd.py indices-analyze k_fluent_bit --min-docs 0")
        usage_table.add_row("   Last 7d by name:",  "./escmd.py indices-analyze k_fluent_bit --within-days 7")
        usage_table.add_row("   JSON output:",      "./escmd.py indices-analyze --format json")
        usage_table.add_row("   More index cmds:",  "./escmd.py help indices")

        self._display_help_panels(
            commands_table, examples_table,
            "📊 indices-analyze Flags", "",
            usage_table, "🎯 Overview & Examples"
        )
