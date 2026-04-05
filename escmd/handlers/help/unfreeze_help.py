"""
Help content for unfreeze commands.
"""

from .base_help_content import BaseHelpContent


class UnfreezeHelpContent(BaseHelpContent):
    """Help content for unfreeze commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for unfreeze help."""
        return "unfreeze"

    def get_topic_description(self) -> str:
        """Get the topic description for unfreeze help."""
        return "Unfreeze indices to restore write operations"

    def show_help(self) -> None:
        """Show detailed help for unfreeze commands."""
        help_styles, border_style = self._get_theme_styles()

        from rich.panel import Panel
        from rich.table import Table

        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=32)
        commands_table.add_column(style=help_styles.get('description', 'white'))

        commands_table.add_row("unfreeze <index>", "Unfreeze a single index by exact name")
        commands_table.add_row("unfreeze <pattern> --regex", "Unfreeze indices matching regex pattern")
        commands_table.add_row("unfreeze <pattern> -r", "Short form of --regex flag")
        commands_table.add_row("unfreeze <pattern> --yes", "Skip confirmation prompt")
        commands_table.add_row("unfreeze <pattern> -y", "Short form of --yes flag")

        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style=help_styles.get('example', 'bold green'), min_width=32)
        examples_table.add_column(style=help_styles.get('description', 'dim white'))

        examples_table.add_row("Unfreeze single index:", "./escmd.py unfreeze myindex-2024-01")
        examples_table.add_row("Unfreeze by pattern:", "./escmd.py unfreeze 'logs-.*' --regex")
        examples_table.add_row("Short regex form:", "./escmd.py unfreeze 'temp-.*' -r")
        examples_table.add_row("Skip confirmation:", "./escmd.py unfreeze 'old-.*' -r --yes")
        examples_table.add_row("Automation friendly:", "./escmd.py unfreeze 'backup-.*' -r -y")

        # Usage table
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style=help_styles.get('section_header', 'bold magenta'), min_width=32)
        usage_table.add_column(style=help_styles.get('description', 'dim cyan'))

        usage_table.add_row("🧊 Understanding Frozen Indices:", "Frozen indices are memory-optimized for long-term storage")
        usage_table.add_row("   Memory Usage:", "Minimal heap usage for metadata only")
        usage_table.add_row("   Search Speed:", "Slower searches due to disk-based operations")
        usage_table.add_row("   Write Status:", "Read-only, no new documents accepted")
        usage_table.add_row("", "")
        usage_table.add_row("🔥 When to Unfreeze:", "Restore full functionality for active use")
        usage_table.add_row("   Resume Writing:", "Need to index new documents")
        usage_table.add_row("   Performance:", "Require normal search performance")
        usage_table.add_row("   Temporary Access:", "Short-term intensive operations")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 Pattern Matching:", "Use regex for bulk operations")
        usage_table.add_row("   Exact Match:", "./escmd.py unfreeze myindex-001")
        usage_table.add_row("   Purpose:", "Single index, no --regex needed")
        usage_table.add_row("   Regex Pattern:", "./escmd.py unfreeze 'logs-2024-.*' --regex")
        usage_table.add_row("   Purpose:", "Multiple indices matching pattern")
        usage_table.add_row("", "")
        usage_table.add_row("🔶 Safety Features:", "Confirmation prompts prevent accidents")
        usage_table.add_row("   Single Index:", "No confirmation required")
        usage_table.add_row("   Multiple Indices:", "Interactive confirmation (y/yes/n/no)")
        usage_table.add_row("   Skip Confirmation:", "Use --yes/-y for automation")
        usage_table.add_row("   Cancel Operation:", "Press Ctrl+C or enter 'n/no'")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Common Workflows:", "Typical unfreeze scenarios")
        usage_table.add_row("   Restore Old Data:", "1. Find: ./escmd.py indices | grep frozen")
        usage_table.add_row("   ", "2. Unfreeze: ./escmd.py unfreeze old-index")
        usage_table.add_row("   ", "3. Use normally, then re-freeze if needed")
        usage_table.add_row("   Batch Unfreeze:", "1. Pattern: ./escmd.py unfreeze 'temp-.*' -r")
        usage_table.add_row("   ", "2. Review list, confirm with 'y'")
        usage_table.add_row("   ", "3. Monitor: ./escmd.py indices | grep temp")
        usage_table.add_row("   Automation:", "./escmd.py unfreeze 'backup-.*' -r -y")

        # Error handling table
        error_table = Table.grid(padding=(0, 3))
        error_table.add_column(style=help_styles.get('command', 'bold red'), min_width=32)
        error_table.add_column(style=help_styles.get('description', 'dim white'))

        error_table.add_row("No matching indices:", "Check pattern syntax and existing indices")
        error_table.add_row("Regex syntax error:", "Validate pattern: 'logs-.*' not 'logs-*'")
        error_table.add_row("Permission denied:", "Ensure cluster write permissions")
        error_table.add_row("Index not frozen:", "Command succeeds but no change needed")
        error_table.add_row("Connection issues:", "Check cluster connectivity first")

        # Display main panels
        self.console.print()
        self.console.print(Panel(
            commands_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🔥 Unfreeze Index Commands[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            examples_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🚀 Unfreeze Examples[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            usage_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🎯 Unfreeze Workflows & Best Practices[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            error_table,
            title=f"[{help_styles.get('section_header', 'bold red')}]🔶 Common Issues & Troubleshooting[/{help_styles.get('section_header', 'bold red')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
