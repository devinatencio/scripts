"""
Help content for indices-watch-sessions.
"""

from .base_help_content import BaseHelpContent


class IndicesWatchSessionsHelpContent(BaseHelpContent):
    """Help for watch session management."""

    def get_topic_name(self) -> str:
        return "indices-watch-sessions"

    def get_topic_description(self) -> str:
        return "List, inspect, and delete stored watch sessions"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("indices-watch-sessions list",        "List all sessions across all dates for the cluster",            "./escmd.py indices-watch-sessions list")
        commands_table.add_row("indices-watch-sessions detail <id>", "Show full metadata and sample info for a session",              "./escmd.py indices-watch-sessions detail 1430")
        commands_table.add_row("indices-watch-sessions delete <id>", "Delete a specific session (prompts for confirmation)",          "./escmd.py indices-watch-sessions delete 1430")
        commands_table.add_row("indices-watch-sessions delete-day",  "Delete all sessions for a date (default: today)",               "./escmd.py indices-watch-sessions delete-day --date 2025-01-15")
        commands_table.add_row("indices-watch-sessions clusters",    "List all clusters that have stored watch data",                 "./escmd.py indices-watch-sessions clusters")
        commands_table.add_row("--cluster NAME",                     "Target a specific cluster slug",                                "")
        commands_table.add_row("--date YYYY-MM-DD",                  "Narrow to a specific date (list, delete-day)",                  "")
        commands_table.add_row("--format json",                      "Machine-readable JSON output (list, detail, clusters)",          "")
        commands_table.add_row("--force",                            "Skip confirmation prompt (delete, delete-day)",                  "")

        usage_table.add_row("📋 Overview:", "Manage sessions created by indices-watch-collect")
        usage_table.add_row("   Storage:",     "~/.escmd/index-watch/<cluster>/<date>/<session>/")
        usage_table.add_row("   Session IDs:", "HHMM or HHMM-<label> (e.g. 1430, 1430-load-test)")
        usage_table.add_row("   Lookup:",      "detail and delete search all dates automatically")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Quick Examples:", "Common usage patterns")
        usage_table.add_row("   See everything:",    "./escmd.py indices-watch-sessions list")
        usage_table.add_row("   One date only:",     "./escmd.py indices-watch-sessions list --date 2025-01-15")
        usage_table.add_row("   Inspect a session:", "./escmd.py indices-watch-sessions detail 1430")
        usage_table.add_row("   Clean up old day:",  "./escmd.py indices-watch-sessions delete-day --date 2025-01-10 --force")
        usage_table.add_row("   JSON for scripts:",  "./escmd.py indices-watch-sessions list --format json")

        self._display_help_panels(
            commands_table, examples_table,
            "📂 indices-watch-sessions Commands", "",
            usage_table, "🎯 Overview & Examples"
        )
