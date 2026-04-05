"""
Help content for snapshots commands.
"""

from .base_help_content import BaseHelpContent


class SnapshotsHelpContent(BaseHelpContent):
    """Help content for snapshots commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for snapshots help."""
        return "snapshots"

    def get_topic_description(self) -> str:
        """Get the topic description for snapshots help."""
        return "Backup and snapshot operations"

    def show_help(self) -> None:
        """Show detailed help for snapshots commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table = self._create_usage_table()

        # Add commands (exact from original)
        commands_table.add_row(
            "repositories", "List all configured snapshot repositories"
        )
        commands_table.add_row(
            "repositories --format json", "List repositories in JSON format"
        )
        commands_table.add_row(
            "snapshots list", "List all available snapshots (fast mode by default)"
        )
        commands_table.add_row(
            "snapshots list <pattern>", "Filter snapshots by pattern"
        )
        commands_table.add_row("snapshots list --pager", "Use pager for large lists")
        commands_table.add_row(
            "snapshots list --slow", "Use slow listing mode (full metadata)"
        )
        commands_table.add_row(
            "snapshots info <name>", "Show detailed snapshot information"
        )
        commands_table.add_row("snapshots create <name>", "Create new snapshot")
        commands_table.add_row("snapshots delete <name>", "Delete existing snapshot")

        # Add examples (exact from original)
        examples_table.add_row("List repositories:", "./escmd.py repositories")
        examples_table.add_row(
            "Repositories JSON:", "./escmd.py repositories --format json"
        )
        examples_table.add_row("List snapshots:", "./escmd.py snapshots list")
        examples_table.add_row(
            "Filter by pattern:", "./escmd.py snapshots list 'logs-*'"
        )
        examples_table.add_row("With pager:", "./escmd.py snapshots list --pager")
        examples_table.add_row("Full metadata:", "./escmd.py snapshots list --slow")
        examples_table.add_row(
            "Snapshot details:", "./escmd.py snapshots info backup-001"
        )
        examples_table.add_row(
            "JSON output:", "./escmd.py snapshots list --format json"
        )

        # Add usage patterns (exact from original)
        usage_table.add_row(
            "🏗️ Repository Management:", "Configure and monitor snapshot repositories"
        )
        usage_table.add_row("   List Repos:", "./escmd.py repositories")
        usage_table.add_row("   Check Config:", "./escmd.py repositories --format json")
        usage_table.add_row(
            "   Purpose:", "Verify repository connectivity and settings"
        )
        usage_table.add_row("", "")
        usage_table.add_row(
            "💾 Backup Strategy:", "Regular data protection and recovery planning"
        )
        usage_table.add_row(
            "   Daily Backup:", "./escmd.py snapshots create daily-$(date +%Y%m%d)"
        )
        usage_table.add_row(
            "   Verify Status:", "./escmd.py snapshots info daily-20250828"
        )
        usage_table.add_row("   Monitor Space:", "./escmd.py snapshots list")
        usage_table.add_row("   Purpose:", "Track backup storage usage")
        usage_table.add_row("", "")
        usage_table.add_row(
            "🔄 Disaster Recovery:", "Restore operations during incidents"
        )
        usage_table.add_row(
            "   List Available:", "./escmd.py snapshots list --format json"
        )
        usage_table.add_row("   Filter:", "| filter latest")
        usage_table.add_row(
            "   Check Integrity:", "./escmd.py snapshots info <backup-name>"
        )
        usage_table.add_row("   Purpose:", "Verify backup health before restore")
        usage_table.add_row(
            "   Recovery Point:", "Use snapshot timestamp for recovery planning"
        )
        usage_table.add_row("", "")
        usage_table.add_row(
            "🧹 Backup Maintenance:", "Managing backup lifecycle and cleanup"
        )
        usage_table.add_row("   Find Old:", "./escmd.py snapshots list")
        usage_table.add_row("   Filter:", "| grep old-date-pattern")
        usage_table.add_row(
            "   Space Cleanup:", "./escmd.py snapshots delete <old-backup-name>"
        )
        usage_table.add_row(
            "   Retention Policy:", "Delete snapshots older than retention period"
        )
        usage_table.add_row("", "")
        usage_table.add_row(
            "📊 Backup Monitoring:", "Track backup health and performance"
        )
        usage_table.add_row("   Status Check:", "./escmd.py snapshots list --pager")
        usage_table.add_row("   Full Check:", "./escmd.py snapshots list --slow")
        usage_table.add_row("   Purpose:", "For large environments with many snapshots")
        usage_table.add_row(
            "   Success Rate:", "Monitor for failed snapshots and investigate"
        )
        usage_table.add_row(
            "   Storage Growth:", "Track backup storage consumption over time"
        )
        usage_table.add_row("", "")
        usage_table.add_row(
            "⚡ Emergency Procedures:", "Quick backup and restore operations"
        )
        usage_table.add_row(
            "   Quick Backup:", "./escmd.py snapshots create emergency-backup"
        )
        usage_table.add_row(
            "   Verify Quick:", "./escmd.py snapshots info emergency-backup"
        )
        usage_table.add_row("   List Recent:", "./escmd.py snapshots list")
        usage_table.add_row("   Filter:", "| head -10")

        # Display help panels
        self._display_help_panels(
            commands_table,
            examples_table,
            "📸 Snapshot Management Commands",
            "🚀 Snapshot Examples",
            usage_table,
            "🎯 Backup & Recovery Workflows",
        )
