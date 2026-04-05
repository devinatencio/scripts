"""
Help content for ILM (Index Lifecycle Management) commands.
"""

from .base_help_content import BaseHelpContent


class ILMHelpContent(BaseHelpContent):
    """Help content for ILM commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for ILM help."""
        return "ilm"

    def get_topic_description(self) -> str:
        """Get the topic description for ILM help."""
        return "Index Lifecycle Management commands"

    def show_help(self) -> None:
        """Show detailed help for ILM commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table = self._create_usage_table()

        # Add commands (updated for current escmd)
        commands_table.add_row("ilm status", "Show comprehensive ILM status and statistics")
        commands_table.add_row("ilm policies", "List all ILM policies with phase configurations")
        commands_table.add_row("ilm policy <name>", "Show detailed configuration for specific policy")
        commands_table.add_row("ilm explain <index>", "Show ILM status for specific index")
        commands_table.add_row("ilm errors", "Show indices with ILM errors")
        commands_table.add_row("ilm create-policy <name> <json>", "Create new ILM policy from JSON definition or file")
        commands_table.add_row("ilm delete-policy <name>", "Delete an existing ILM policy")
        commands_table.add_row(
            "ilm set-policy <target> …",
            "Assign ILM policy (pattern, --file, or --from-policy <source>)",
        )
        commands_table.add_row("ilm remove-policy <pattern>", "Remove ILM policy from indices matching pattern")

        # Add examples (updated for current escmd)
        examples_table.add_row("ILM status:", "./escmd.py ilm status")
        examples_table.add_row("List policies:", "./escmd.py ilm policies")
        examples_table.add_row("Policy details:", "./escmd.py ilm policy my-policy")
        examples_table.add_row("Index status:", "./escmd.py ilm explain logs-2024-01")
        examples_table.add_row("Show errors:", "./escmd.py ilm errors")
        examples_table.add_row("Create policy:", "./escmd.py ilm create-policy retention-policy policy.json")
        examples_table.add_row("Inline policy:", "./escmd.py ilm create-policy test '{\"policy\":{\"phases\":{...}}}'")
        examples_table.add_row("Delete policy:", "./escmd.py ilm delete-policy old-policy")
        examples_table.add_row("Set policy:", "./escmd.py ilm set-policy 30-days 'logs-*'")
        examples_table.add_row(
            "Migrate policies:",
            "./escmd.py ilm set-policy new-ilm --from-policy old-ilm --dry-run",
        )
        examples_table.add_row("Remove policy:", "./escmd.py ilm remove-policy 'temp-*'")
        examples_table.add_row("JSON output:", "./escmd.py ilm policies --format json")

        # Add usage patterns (updated for current escmd)
        usage_table.add_row("🆕 Policy Creation:", "Create and customize lifecycle policies")
        usage_table.add_row("   From File:", "./escmd.py ilm create-policy retention-policy policy.json")
        usage_table.add_row("   Inline JSON:", "./escmd.py ilm create-policy test '{\"policy\":{\"phases\":{...}}}'")
        usage_table.add_row("   Delete Policy:", "./escmd.py ilm delete-policy old-policy")
        usage_table.add_row("   Purpose:", "Define custom data lifecycle management")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 Policy Management:", "Monitor and apply lifecycle policies")
        usage_table.add_row("   List All:", "./escmd.py ilm policies")
        usage_table.add_row("   Check Policy:", "./escmd.py ilm policy my-logs-policy")
        usage_table.add_row("   Apply Policy:", "./escmd.py ilm set-policy 30-days 'logs-*'")
        usage_table.add_row(
            "   From Policy:",
            "./escmd.py ilm set-policy target-ilm --from-policy source-ilm --dry-run",
        )
        usage_table.add_row("   Remove Policy:", "./escmd.py ilm remove-policy 'temp-*'")
        usage_table.add_row("", "")
        usage_table.add_row("🔍 Troubleshooting:", "Debug ILM issues and failed operations")
        usage_table.add_row("   Check Status:", "./escmd.py ilm status")
        usage_table.add_row("   Show Errors:", "./escmd.py ilm errors")
        usage_table.add_row("   Explain Index:", "./escmd.py ilm explain stuck-index")
        usage_table.add_row("   Purpose:", "Identify and resolve ILM problems")
        usage_table.add_row("", "")
        usage_table.add_row("⚡ Performance Tuning:", "Optimize lifecycle management")
        usage_table.add_row("   Monitor:", "./escmd.py ilm status")
        usage_table.add_row("   Analyze:", "Check for indices stuck in phases")
        usage_table.add_row("   Action:", "Adjust policies or force transitions")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Automation:", "Script ILM operations and monitoring")
        usage_table.add_row("   Export Policies:", "./escmd.py ilm policies --format json")
        usage_table.add_row("   Monitor Status:", "./escmd.py ilm status --format json")
        usage_table.add_row("   Create Policies:", "Use JSON templates for bulk policy creation")
        usage_table.add_row("   Integration:", "Integrate with CI/CD and monitoring systems")

        # Display help panels
        self._display_help_panels(
            commands_table, examples_table,
            "🔄 ILM Management Commands", "💡 ILM Examples",
            usage_table, "🎯 ILM Workflows & Best Practices"
        )
