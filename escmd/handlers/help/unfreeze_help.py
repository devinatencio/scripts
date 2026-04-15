"""
Help content for unfreeze commands.
"""

from .base_help_content import BaseHelpContent


class UnfreezeHelpContent(BaseHelpContent):
    """Help content for unfreeze commands."""

    def get_topic_name(self) -> str:
        return "unfreeze"

    def get_topic_description(self) -> str:
        return "Unfreeze indices to restore write operations"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("unfreeze <index>",           "Unfreeze a single index by exact name",  "./escmd.py unfreeze myindex-2024-01")
        commands_table.add_row("unfreeze <pattern> --regex", "Unfreeze indices matching regex pattern", "./escmd.py unfreeze 'logs-.*' --regex")
        commands_table.add_row("unfreeze <pattern> -r",      "Short form of --regex flag",              "./escmd.py unfreeze 'temp-.*' -r")
        commands_table.add_row("unfreeze <pattern> --yes",   "Skip confirmation prompt",                "./escmd.py unfreeze 'old-.*' -r --yes")
        commands_table.add_row("unfreeze <pattern> -y",      "Short form of --yes flag",                "./escmd.py unfreeze 'backup-.*' -r -y")

        usage_table.add_row("🧊 Understanding Frozen Indices:", "Frozen indices are memory-optimized for long-term storage")
        usage_table.add_row("   Memory Usage:",               "Minimal heap usage for metadata only")
        usage_table.add_row("   Search Speed:",               "Slower searches due to disk-based operations")
        usage_table.add_row("   Write Status:",               "Read-only, no new documents accepted")
        usage_table.add_row("", "")
        usage_table.add_row("🔥 When to Unfreeze:", "Restore full functionality for active use")
        usage_table.add_row("   Resume Writing:",  "Need to index new documents")
        usage_table.add_row("   Performance:",     "Require normal search performance")
        usage_table.add_row("   Temporary Access:","Short-term intensive operations")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 Pattern Matching:", "Use regex for bulk operations")
        usage_table.add_row("   Exact Match:",      "./escmd.py unfreeze myindex-001")
        usage_table.add_row("   Regex Pattern:",    "./escmd.py unfreeze 'logs-2024-.*' --regex")
        usage_table.add_row("", "")
        usage_table.add_row("🔶 Safety Features:", "Confirmation prompts prevent accidents")
        usage_table.add_row("   Single Index:",    "No confirmation required")
        usage_table.add_row("   Multiple Indices:","Interactive confirmation (y/yes/n/no)")
        usage_table.add_row("   Skip Confirmation:","Use --yes/-y for automation")
        usage_table.add_row("   Cancel Operation:","Press Ctrl+C or enter 'n/no'")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Common Workflows:", "Typical unfreeze scenarios")
        usage_table.add_row("   Restore Old Data:", "1. Find: ./escmd.py indices | grep frozen")
        usage_table.add_row("   ",                  "2. Unfreeze: ./escmd.py unfreeze old-index")
        usage_table.add_row("   ",                  "3. Use normally, then re-freeze if needed")
        usage_table.add_row("   Batch Unfreeze:",   "1. Pattern: ./escmd.py unfreeze 'temp-.*' -r")
        usage_table.add_row("   ",                  "2. Review list, confirm with 'y'")
        usage_table.add_row("   ",                  "3. Monitor: ./escmd.py indices | grep temp")
        usage_table.add_row("   Automation:",       "./escmd.py unfreeze 'backup-.*' -r -y")
        usage_table.add_row("", "")
        usage_table.add_row("🔶 Common Issues:", "Troubleshooting unfreeze problems")
        usage_table.add_row("   No matching indices:", "Check pattern syntax and existing indices")
        usage_table.add_row("   Regex syntax error:",  "Validate pattern: 'logs-.*' not 'logs-*'")
        usage_table.add_row("   Permission denied:",   "Ensure cluster write permissions")
        usage_table.add_row("   Index not frozen:",    "Command succeeds but no change needed")
        usage_table.add_row("   Connection issues:",   "Check cluster connectivity first")

        self._display_help_panels(
            commands_table, examples_table,
            "🔥 Unfreeze Index Commands", "",
            usage_table, "🎯 Unfreeze Workflows & Best Practices"
        )
