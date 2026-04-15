"""
Help content for freeze commands.
"""

from .base_help_content import BaseHelpContent


class FreezeHelpContent(BaseHelpContent):
    """Help content for freeze commands."""

    def get_topic_name(self) -> str:
        return "freeze"

    def get_topic_description(self) -> str:
        return "Freeze indices to prevent write operations"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("freeze <index>",              "Freeze a single index by exact name",                    "./escmd.py freeze myindex-2024-01")
        commands_table.add_row("freeze <pattern>",            "Auto-detects regex patterns and freezes matching indices","./escmd.py freeze 'logs-.*'")
        commands_table.add_row("freeze <pattern> --regex",    "Explicitly treat pattern as regex",                      "./escmd.py freeze 'logs-.*' --regex")
        commands_table.add_row("freeze <pattern> --exact",    "Force exact match (disable auto-detection)",             "./escmd.py freeze 'index.with.dots' --exact")
        commands_table.add_row("freeze <pattern> --yes",      "Skip confirmation prompt",                               "./escmd.py freeze 'old-.*' --yes")
        commands_table.add_row("freeze <pattern> -r",         "Short form of --regex flag",                             "")
        commands_table.add_row("freeze <pattern> -e",         "Short form of --exact flag",                             "")
        commands_table.add_row("freeze <pattern> -y",         "Short form of --yes flag",                               "./escmd.py freeze 'backup-.*' -y")

        usage_table.add_row("🧊 Understanding Freeze:", "Convert active indices to memory-optimized storage")
        usage_table.add_row("   Memory Savings:",       "Significantly reduced heap usage")
        usage_table.add_row("   Search Impact:",        "Slower searches due to disk-based operations")
        usage_table.add_row("   Write Status:",         "Read-only, no new documents accepted")
        usage_table.add_row("", "")
        usage_table.add_row("🧊 When to Freeze:", "Optimize storage for rarely accessed data")
        usage_table.add_row("   Old Indices:",    "Historical data accessed infrequently")
        usage_table.add_row("   Archive Storage:","Long-term retention with space savings")
        usage_table.add_row("   Memory Pressure:","Free up heap space in constrained clusters")
        usage_table.add_row("", "")
        usage_table.add_row("🤖 Auto-Detection:", "Automatically detects regex patterns for convenience")
        usage_table.add_row("   Smart Detection:","Patterns like 'logs-.*' auto-enable regex mode")
        usage_table.add_row("   Auto Patterns:",  ".* .+ [] {} ^ $ | + ? () and \\ sequences")
        usage_table.add_row("   Manual Override:","Use --regex to force or --exact to disable")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 Pattern Matching:", "Flexible pattern matching options")
        usage_table.add_row("   Exact Match:",     "./escmd.py freeze myindex-001")
        usage_table.add_row("   Auto Regex:",      "./escmd.py freeze 'logs-2023-.*'")
        usage_table.add_row("   Force Exact:",     "./escmd.py freeze 'index.with.dots' --exact")
        usage_table.add_row("   Explicit Regex:",  "./escmd.py freeze 'pattern' --regex")
        usage_table.add_row("", "")
        usage_table.add_row("🔶 Safety Features:", "Confirmation prompts prevent accidents")
        usage_table.add_row("   Single Index:",    "No confirmation required")
        usage_table.add_row("   Multiple Indices:","Interactive confirmation (y/yes/n/no)")
        usage_table.add_row("   Skip Confirmation:","Use --yes/-y for automation")
        usage_table.add_row("   Cancel Operation:","Press Ctrl+C or enter 'n/no'")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Common Workflows:", "Typical freeze scenarios")
        usage_table.add_row("   Archive Old Logs:", "1. Find: ./escmd.py indices | grep logs-2023")
        usage_table.add_row("   ",                  "2. Freeze: ./escmd.py freeze 'logs-2023-.*'")
        usage_table.add_row("   ",                  "3. Monitor memory usage improvement")
        usage_table.add_row("   Batch Freeze:",     "1. Pattern: ./escmd.py freeze 'old-.*'")
        usage_table.add_row("   ",                  "2. Review list, confirm with 'y'")
        usage_table.add_row("   ",                  "3. Verify: ./escmd.py indices | grep frozen")
        usage_table.add_row("   Automation:",       "./escmd.py freeze 'archive-.*' -y")
        usage_table.add_row("", "")
        usage_table.add_row("🔶 Common Issues:", "Troubleshooting freeze problems")
        usage_table.add_row("   No matching indices:", "Check pattern syntax and existing indices")
        usage_table.add_row("   Regex syntax error:",  "Validate pattern: 'logs-.*' not 'logs-*'")
        usage_table.add_row("   Wrong auto-detection:","Use --exact for literal matches with special chars")
        usage_table.add_row("   Permission denied:",   "Ensure cluster write permissions")
        usage_table.add_row("   Already frozen:",      "Command succeeds but no change needed")

        self._display_help_panels(
            commands_table, examples_table,
            "🧊 Freeze Index Commands", "",
            usage_table, "🎯 Freeze Workflows & Best Practices"
        )
