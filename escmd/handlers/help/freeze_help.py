"""
Help content for freeze commands.
"""

from .base_help_content import BaseHelpContent


class FreezeHelpContent(BaseHelpContent):
    """Help content for freeze commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for freeze help."""
        return "freeze"

    def get_topic_description(self) -> str:
        """Get the topic description for freeze help."""
        return "Freeze indices to prevent write operations"

    def show_help(self) -> None:
        """Show detailed help for freeze commands."""
        help_styles, border_style = self._get_theme_styles()

        from rich.panel import Panel
        from rich.table import Table

        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=32)
        commands_table.add_column(style=help_styles.get('description', 'white'))

        commands_table.add_row("freeze <index>", "Freeze a single index by exact name")
        commands_table.add_row("freeze <pattern>", "Auto-detects regex patterns and freezes matching indices")
        commands_table.add_row("freeze <pattern> --regex", "Explicitly treat pattern as regex")
        commands_table.add_row("freeze <pattern> --exact", "Force exact match (disable auto-detection)")
        commands_table.add_row("freeze <pattern> --yes", "Skip confirmation prompt")
        commands_table.add_row("freeze <pattern> -r", "Short form of --regex flag")
        commands_table.add_row("freeze <pattern> -e", "Short form of --exact flag")
        commands_table.add_row("freeze <pattern> -y", "Short form of --yes flag")

        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style=help_styles.get('example', 'bold green'), min_width=32)
        examples_table.add_column(style=help_styles.get('description', 'dim white'))

        examples_table.add_row("Freeze single index:", "./escmd.py freeze myindex-2024-01")
        examples_table.add_row("Auto-detected pattern:", "./escmd.py freeze 'logs-.*'")
        examples_table.add_row("Explicit regex:", "./escmd.py freeze 'logs-.*' --regex")
        examples_table.add_row("Force exact match:", "./escmd.py freeze 'index.with.dots' --exact")
        examples_table.add_row("Skip confirmation:", "./escmd.py freeze 'old-.*' --yes")
        examples_table.add_row("Automation friendly:", "./escmd.py freeze 'backup-.*' -y")

        # Usage table
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style=help_styles.get('section_header', 'bold magenta'), min_width=32)
        usage_table.add_column(style=help_styles.get('description', 'dim cyan'))

        usage_table.add_row("🧊 Understanding Freeze:", "Convert active indices to memory-optimized storage")
        usage_table.add_row("   Memory Savings:", "Significantly reduced heap usage")
        usage_table.add_row("   Search Impact:", "Slower searches due to disk-based operations")
        usage_table.add_row("   Write Status:", "Read-only, no new documents accepted")
        usage_table.add_row("", "")
        usage_table.add_row("🧊 When to Freeze:", "Optimize storage for rarely accessed data")
        usage_table.add_row("   Old Indices:", "Historical data accessed infrequently")
        usage_table.add_row("   Archive Storage:", "Long-term retention with space savings")
        usage_table.add_row("   Memory Pressure:", "Free up heap space in constrained clusters")
        usage_table.add_row("", "")
        usage_table.add_row("🤖 Auto-Detection:", "Automatically detects regex patterns for convenience")
        usage_table.add_row("   Smart Detection:", "Patterns like 'logs-.*' auto-enable regex mode")
        usage_table.add_row("   Auto Patterns:", ".* .+ [] {} ^ $ | + ? () and \\ sequences")
        usage_table.add_row("   Manual Override:", "Use --regex to force or --exact to disable")
        usage_table.add_row("   Example:", "./escmd.py freeze 'logs-.*' (auto-detects regex)")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 Pattern Matching:", "Flexible pattern matching options")
        usage_table.add_row("   Exact Match:", "./escmd.py freeze myindex-001")
        usage_table.add_row("   Auto Regex:", "./escmd.py freeze 'logs-2023-.*'")
        usage_table.add_row("   Force Exact:", "./escmd.py freeze 'index.with.dots' --exact")
        usage_table.add_row("   Explicit Regex:", "./escmd.py freeze 'pattern' --regex")
        usage_table.add_row("", "")
        usage_table.add_row("🔶 Safety Features:", "Confirmation prompts prevent accidents")
        usage_table.add_row("   Single Index:", "No confirmation required")
        usage_table.add_row("   Multiple Indices:", "Interactive confirmation (y/yes/n/no)")
        usage_table.add_row("   Skip Confirmation:", "Use --yes/-y for automation")
        usage_table.add_row("   Cancel Operation:", "Press Ctrl+C or enter 'n/no'")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Common Workflows:", "Typical freeze scenarios (now simpler!)")
        usage_table.add_row("   Archive Old Logs:", "1. Find: ./escmd.py indices | grep logs-2023")
        usage_table.add_row("   ", "2. Freeze: ./escmd.py freeze 'logs-2023-.*'")
        usage_table.add_row("   ", "3. Monitor memory usage improvement")
        usage_table.add_row("   Batch Freeze:", "1. Pattern: ./escmd.py freeze 'old-.*'")
        usage_table.add_row("   ", "2. Review list, confirm with 'y'")
        usage_table.add_row("   ", "3. Verify: ./escmd.py indices | grep frozen")
        usage_table.add_row("   Automation:", "./escmd.py freeze 'archive-.*' -y")

        # Error handling table
        error_table = Table.grid(padding=(0, 3))
        error_table.add_column(style=help_styles.get('command', 'bold red'), min_width=32)
        error_table.add_column(style=help_styles.get('description', 'dim white'))

        error_table.add_row("No matching indices:", "Check pattern syntax and existing indices")
        error_table.add_row("Regex syntax error:", "Validate pattern: 'logs-.*' not 'logs-*'")
        error_table.add_row("Wrong auto-detection:", "Use --exact for literal matches with special chars")
        error_table.add_row("Permission denied:", "Ensure cluster write permissions")
        error_table.add_row("Index already frozen:", "Command succeeds but no change needed")
        error_table.add_row("Connection issues:", "Check cluster connectivity first")

        # Display main panels
        self.console.print()
        self.console.print(Panel(
            commands_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🧊 Freeze Index Commands[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            examples_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🚀 Freeze Examples[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            usage_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🎯 Freeze Workflows & Best Practices[/{help_styles.get('section_header', 'bold cyan')}]",
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
