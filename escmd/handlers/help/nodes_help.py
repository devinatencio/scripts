"""
Help content for nodes commands.
"""

from .base_help_content import BaseHelpContent


class NodesHelpContent(BaseHelpContent):
    """Help content for nodes commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for nodes help."""
        return "nodes"

    def get_topic_description(self) -> str:
        """Get the topic description for nodes help."""
        return "Node management and information"

    def show_help(self) -> None:
        """Show detailed help for nodes commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table = self._create_usage_table()

        # Add commands (from original)
        commands_table.add_row("nodes", "List all cluster nodes with details")
        commands_table.add_row("masters", "Show master-eligible nodes")
        commands_table.add_row("current-master", "Show current active master node")
        commands_table.add_row("storage", "View node disk usage statistics")
        commands_table.add_row("recovery", "Monitor node recovery operations")

        # Add examples (from original)
        examples_table.add_row("All nodes:", "./escmd.py nodes")
        examples_table.add_row("Master nodes:", "./escmd.py masters")
        examples_table.add_row("Current master:", "./escmd.py current-master")
        examples_table.add_row("Disk usage:", "./escmd.py storage")
        examples_table.add_row("Recovery status:", "./escmd.py recovery")
        examples_table.add_row("JSON output:", "./escmd.py nodes --format json")

        # Add usage patterns (from original)
        usage_table.add_row("🔍 Cluster Monitoring:", "Regular node health and status checks")
        usage_table.add_row("   Overview:", "./escmd.py nodes")
        usage_table.add_row("   Purpose:", "Check all nodes status, roles, and resources")
        usage_table.add_row("   Master Check:", "./escmd.py current-master")
        usage_table.add_row("   Purpose:", "Verify master node stability")
        usage_table.add_row("", "")
        usage_table.add_row("💾 Storage Management:", "Monitor disk usage and capacity")
        usage_table.add_row("   Command:", "./escmd.py storage")
        usage_table.add_row("   Purpose:", "Track disk usage across all nodes")
        usage_table.add_row("   Action:", "Identify nodes approaching capacity limits")
        usage_table.add_row("", "")
        usage_table.add_row("🔧 Troubleshooting:", "Diagnose node-specific issues")
        usage_table.add_row("   Step 1:", "./escmd.py nodes")
        usage_table.add_row("   Purpose:", "Identify disconnected or problematic nodes")
        usage_table.add_row("   Step 2:", "./escmd.py recovery")
        usage_table.add_row("   Purpose:", "Check ongoing recovery operations")
        usage_table.add_row("", "")
        usage_table.add_row("⚡ Performance Analysis:", "Identify resource bottlenecks")
        usage_table.add_row("   Node Resources:", "./escmd.py nodes")
        usage_table.add_row("   Storage Load:", "./escmd.py storage")
        usage_table.add_row("   Recovery Impact:", "./escmd.py recovery")
        usage_table.add_row("   Benefit:", "Comprehensive view of node performance")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Automation:", "Script node monitoring and alerts")
        usage_table.add_row("   Export Data:", "./escmd.py nodes --format json")
        usage_table.add_row("   Parse Results:", "| jq '.[] | select(.status == \"disconnected\")'")
        usage_table.add_row("   Integration:", "Use with monitoring systems and alerting")

        # Display help panels
        self._display_help_panels(
            commands_table, examples_table,
            "💻 Node Management Commands", "🚀 Node Examples",
            usage_table, "🎯 Node Operations & Monitoring"
        )
