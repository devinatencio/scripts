"""
Help content for health commands.
"""

from .base_help_content import BaseHelpContent


class HealthHelpContent(BaseHelpContent):
    """Help content for health commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for health help."""
        return "health"

    def get_topic_description(self) -> str:
        """Get the topic description for health help."""
        return "Cluster health monitoring options"

    def show_help(self) -> None:
        """Show detailed help for health commands."""
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        # 3-col merged: command | description | example
        commands_table.add_row("health",                          "Quick cluster health check",       "./escmd.py health")
        commands_table.add_row("health --compare <cluster>",      "Compare with another cluster",     "./escmd.py health --compare prod")
        commands_table.add_row("health --group <prefix>",         "Group clusters by prefix",         "./escmd.py health --group us")
        commands_table.add_row("health --format json",            "Machine-readable JSON output",     "./escmd.py health --format json")
        commands_table.add_row("health-detail",                   "Full health dashboard",            "./escmd.py health-detail")
        commands_table.add_row("health-detail --style dashboard", "Modern dashboard view",            "./escmd.py health-detail --style dashboard")
        commands_table.add_row("health-detail --style classic",   "Traditional table format",         "./escmd.py health-detail --style classic")

        # Workflow scenarios
        usage_table.add_row("🚨 Incident Response:", "Quick cluster status during an outage")
        usage_table.add_row("   Check status:",      "./escmd.py health")
        usage_table.add_row("   Full detail:",       "./escmd.py health-detail")
        usage_table.add_row("   JSON for alert:",    "./escmd.py health --format json")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Daily Monitoring:", "Regular health checks and automation")
        usage_table.add_row("   Morning check:",    "./escmd.py health-detail")
        usage_table.add_row("   Cron / CI:",        "./escmd.py health --format json | monitor.py")
        usage_table.add_row("   Group view:",       "./escmd.py health --group prod")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 Multi-Cluster Ops:", "Managing and comparing multiple environments")
        usage_table.add_row("   Compare two:",       "./escmd.py health --compare staging")
        usage_table.add_row("   Group by region:",   "./escmd.py health --group us")
        usage_table.add_row("   All clusters:",      "./escmd.py locations && ./escmd.py health")

        self._display_help_panels(
            commands_table, examples_table,
            "❤️  Cluster Health Commands", "🚀 Health Examples",
            usage_table, "🎯 Monitoring & Troubleshooting Workflows"
        )
