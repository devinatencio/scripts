"""
Help content for allocation commands.
"""

from .base_help_content import BaseHelpContent


class AllocationHelpContent(BaseHelpContent):
    """Help content for allocation commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for allocation help."""
        return "allocation"

    def get_topic_description(self) -> str:
        """Get the topic description for allocation help."""
        return "Shard allocation management"

    def show_help(self) -> None:
        """Show detailed help for allocation commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table = self._create_usage_table()

        # Add commands (exact from original)
        commands_table.add_row("🔀 allocation enable", "Enable shard allocation")
        commands_table.add_row("🔀 allocation disable", "Disable shard allocation")
        commands_table.add_row("🔀 allocation explain <index>", "Explain shard allocation decisions")
        commands_table.add_row("🔀 allocation exclude add <host>", "Exclude node from allocation")
        commands_table.add_row("🔀 allocation exclude remove <host>", "Remove node exclusion")
        commands_table.add_row("🔀 allocation exclude reset", "Reset all exclusions")

        # Add examples (exact from original)
        examples_table.add_row("Show settings:", "./escmd.py allocation")
        examples_table.add_row("Enable allocation:", "./escmd.py allocation enable")
        examples_table.add_row("Disable allocation:", "./escmd.py allocation disable")
        examples_table.add_row("Explain allocation:", "./escmd.py allocation explain myindex-001")
        examples_table.add_row("Exclude node:", "./escmd.py allocation exclude add node-1")
        examples_table.add_row("Remove exclusion:", "./escmd.py allocation exclude remove node-1")
        examples_table.add_row("Reset exclusions:", "./escmd.py allocation exclude reset")

        # Add usage patterns (exact from original)
        usage_table.add_row("🔧 Allocation Control:", "Manage cluster-wide shard allocation")
        usage_table.add_row("   Enable:", "./escmd.py allocation enable")
        usage_table.add_row("   Purpose:", "Allow shards to move and allocate")
        usage_table.add_row("   Disable:", "./escmd.py allocation disable")
        usage_table.add_row("   Purpose:", "Prevent shard movement during maintenance")
        usage_table.add_row("", "")
        usage_table.add_row("🚫 Node Exclusions:", "Exclude specific nodes from allocation")
        usage_table.add_row("   Exclude Node:", "./escmd.py allocation exclude add node-1")
        usage_table.add_row("   Purpose:", "Prevent shards from being allocated to specific node")
        usage_table.add_row("   Remove Node:", "./escmd.py allocation exclude remove node-1")
        usage_table.add_row("   Purpose:", "Allow node to receive shards again")
        usage_table.add_row("", "")
        usage_table.add_row("🔶 DANGER: Reset All:", "Reset all node exclusions (CLUSTER-WIDE)")
        usage_table.add_row("   Safe Reset:", "./escmd.py allocation exclude reset")
        usage_table.add_row("   Safety:", "Requires typing 'RESET' to confirm")
        usage_table.add_row("   Bypass Safety:", "./escmd.py allocation exclude reset --yes-i-really-mean-it")
        usage_table.add_row("   Warning:", "Use bypass flag with EXTREME caution!")
        usage_table.add_row("", "")
        usage_table.add_row("🔍 Troubleshooting:", "Understand allocation decisions")
        usage_table.add_row("   Explain:", "./escmd.py allocation explain myindex-001")
        usage_table.add_row("   Purpose:", "See why shards are allocated where they are")
        usage_table.add_row("   Display Settings:", "./escmd.py allocation")
        usage_table.add_row("   Purpose:", "View current allocation configuration")

        # Display help panels
        self._display_help_panels(
            commands_table, examples_table,
            "🔀 Allocation Management Commands", "🚀 Allocation Examples",
            usage_table, "🎯 Allocation Workflows & Safety"
        )
