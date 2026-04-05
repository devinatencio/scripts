"""
Help content for shards commands.
"""

from .base_help_content import BaseHelpContent


class ShardsHelpContent(BaseHelpContent):
    """Help content for shards commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for shards help."""
        return "shards"

    def get_topic_description(self) -> str:
        """Get the topic description for shards help."""
        return "Shard distribution and analysis"

    def show_help(self) -> None:
        """Show detailed help for shards commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()

        # Add commands (exact from original)
        commands_table.add_row("🔄 shards", "Show shard distribution across nodes")
        commands_table.add_row("🔗 shard-colocation", "Find primary/replica shards on same host")
        commands_table.add_row("🔢 set-replicas", "Manage replica count for indices")

        # Add examples (exact from original)
        examples_table.add_row("View shards:", "./escmd.py shards")
        examples_table.add_row("Check colocation:", "./escmd.py shard-colocation")
        examples_table.add_row("Set replicas:", "./escmd.py set-replicas --count 1 --indices myindex")
        examples_table.add_row("Set by pattern:", "./escmd.py set-replicas --count 0 --pattern 'temp-*'")
        examples_table.add_row("JSON output:", "./escmd.py shards --format json")

        # Display help panels
        self._display_help_panels(
            commands_table, examples_table,
            "🔄 Shard Management Commands", "🚀 Shard Examples"
        )
