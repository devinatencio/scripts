"""
Help content for dangling commands.
"""

from .base_help_content import BaseHelpContent


class DanglingHelpContent(BaseHelpContent):
    """Help content for dangling commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for dangling help."""
        return "dangling"

    def get_topic_description(self) -> str:
        """Get the topic description for dangling help."""
        return "Dangling index management"

    def show_help(self) -> None:
        """Show detailed help for dangling commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()

        # Add commands (exact from original)
        commands_table.add_row("dangling", "List all dangling indices")
        commands_table.add_row(
            "dangling <uuid>", "Show details for specific dangling index"
        )
        commands_table.add_row(
            "dangling <uuid> --delete", "Delete specific dangling index"
        )
        commands_table.add_row(
            "dangling --cleanup-all", "Interactive cleanup of all dangling indices"
        )
        commands_table.add_row(
            "dangling --group <name>", "Generate dangling report for cluster group"
        )
        commands_table.add_row(
            "dangling --env <name>", "Generate dangling report for environment"
        )
        commands_table.add_row(
            "dangling --env <name> --cleanup-all",
            "Cleanup dangling indices across environment",
        )
        commands_table.add_row(
            "dangling --group <name> --cleanup-all",
            "Cleanup dangling indices across cluster group",
        )

        # Add examples (exact from original)
        examples_table.add_row("List dangling:", "./escmd.py dangling")
        examples_table.add_row("Show details:", "./escmd.py dangling abc123-def456")
        examples_table.add_row(
            "Delete specific:", "./escmd.py dangling abc123-def456 --delete"
        )
        examples_table.add_row("Cleanup all:", "./escmd.py dangling --cleanup-all")
        examples_table.add_row("JSON output:", "./escmd.py dangling --format json")
        examples_table.add_row("Group report:", "./escmd.py dangling --group test")
        examples_table.add_row(
            "Group report JSON:", "./escmd.py dangling --group test --format json"
        )
        examples_table.add_row("Environment report:", "./escmd.py dangling --env prod")
        examples_table.add_row(
            "Environment JSON:", "./escmd.py dangling --env prod --format json"
        )
        examples_table.add_row(
            "Environment cleanup:",
            "./escmd.py dangling --env prod --cleanup-all --dry-run",
        )
        examples_table.add_row(
            "Group cleanup:", "./escmd.py dangling --group test --cleanup-all --dry-run"
        )

        # Display help panels
        self._display_help_panels(
            commands_table,
            examples_table,
            "❌ Dangling Index Commands",
            "🚀 Dangling Examples",
        )
