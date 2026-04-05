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
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table = self._create_usage_table()

        # Add commands (exact from original)
        commands_table.add_row("health", "Quick health check")
        commands_table.add_row("health --compare <cluster>", "Compare with another cluster")
        commands_table.add_row("health --group <prefix>", "Group clusters by prefix")
        commands_table.add_row("health-detail", "Show comprehensive cluster health")
        commands_table.add_row("health-detail --style dashboard", "Modern dashboard view")
        commands_table.add_row("health-detail --style classic", "Traditional table format")

        # Add examples (exact from original)
        examples_table.add_row("Basic health:", "./escmd.py health")
        examples_table.add_row("Dashboard style:", "./escmd.py health-detail")
        examples_table.add_row("Compare clusters:", "./escmd.py health --compare prod")
        examples_table.add_row("Group by prefix:", "./escmd.py health --group us")
        examples_table.add_row("JSON format:", "./escmd.py health --format json")

        # Add usage patterns (exact from original)
        usage_table.add_row("🚨 Incident Response:", "Quick cluster status during outages")
        usage_table.add_row("   Command:", "./escmd.py health")
        usage_table.add_row("   Purpose:", "Immediate status for emergency situations")
        usage_table.add_row("   Follow-up:", "./escmd.py health-detail")
        usage_table.add_row("   Purpose:", "Detailed view for thorough analysis")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Daily Monitoring:", "Regular cluster health checks")
        usage_table.add_row("   Morning Check:", "./escmd.py health-detail")
        usage_table.add_row("   Automation:", "./escmd.py health --format json")
        usage_table.add_row("   Pipeline:", "| monitor_script.py")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 Multi-Cluster Ops:", "Managing multiple environments")
        usage_table.add_row("   Compare:", "./escmd.py health --compare production")
        usage_table.add_row("   Group View:", "./escmd.py health --group us")
        usage_table.add_row("   Note:", "Works with clusters like us-east, us-west")

        # Display help panels
        self._display_help_panels(
            commands_table, examples_table,
            "❤️ Cluster Health Commands", "🚀 Health Examples",
            usage_table, "🎯 Monitoring & Troubleshooting Workflows"
        )
