"""
Help content for repositories commands.
"""

from .base_help_content import BaseHelpContent


class RepositoriesHelpContent(BaseHelpContent):
    """Help content for repositories commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for repositories help."""
        return "repositories"

    def get_topic_description(self) -> str:
        """Get the topic description for repositories help."""
        return "Snapshot repository configuration and management"

    def show_help(self) -> None:
        """Show detailed help for repositories commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table = self._create_usage_table()

        # Add commands
        commands_table.add_row(
            "repositories", "List all configured snapshot repositories"
        )
        commands_table.add_row(
            "repositories list", "List all configured snapshot repositories"
        )
        commands_table.add_row(
            "repositories create", "Create a new snapshot repository"
        )
        commands_table.add_row(
            "repositories verify", "Verify repository works from all nodes"
        )
        commands_table.add_row(
            "repositories --format json", "List repositories in JSON format"
        )
        commands_table.add_row(
            "repositories --format table", "List repositories in table format (default)"
        )

        # Add examples
        examples_table.add_row("List all repositories:", "./escmd.py repositories")
        examples_table.add_row(
            "Verify repository:", "./escmd.py repositories verify s3_repo"
        )
        examples_table.add_row(
            "Create S3 repository:",
            "./escmd.py repositories create my-s3-repo --type s3 --bucket my-backups",
        )
        examples_table.add_row(
            "Create filesystem repo:",
            "./escmd.py repositories create local-repo --type fs --location /mnt/backups",
        )
        examples_table.add_row(
            "Dry run creation:",
            "./escmd.py repositories create test-repo --type s3 --bucket test --dry-run",
        )
        examples_table.add_row(
            "Verify with JSON:", "./escmd.py repositories verify s3_repo --format json"
        )
        examples_table.add_row("JSON format:", "./escmd.py repositories --format json")
        examples_table.add_row("ESterm usage:", "repositories")

        # Add usage patterns
        usage_table.add_row(
            "🏗️ Repository Creation:", "Create and configure new snapshot repositories"
        )
        usage_table.add_row(
            "   S3 Repository:",
            "./escmd.py repositories create prod-s3 --type s3 --bucket prod-backups --region us-west-2",
        )
        usage_table.add_row(
            "   Filesystem Repo:",
            "./escmd.py repositories create local --type fs --location /mnt/snapshots",
        )
        usage_table.add_row(
            "   Test Configuration:",
            "./escmd.py repositories create test --type s3 --bucket test --dry-run",
        )
        usage_table.add_row(
            "   Purpose:", "Set up backup storage before creating snapshots"
        )
        usage_table.add_row("", "")
        usage_table.add_row(
            "📋 Repository Management:", "Monitor and verify snapshot repositories"
        )
        usage_table.add_row("   List Configs:", "./escmd.py repositories")
        usage_table.add_row(
            "   Verify Connectivity:", "./escmd.py repositories verify repo_name"
        )
        usage_table.add_row(
            "   Check Settings:", "./escmd.py repositories --format json"
        )
        usage_table.add_row(
            "   Check Types:", "Identify S3, filesystem, and other repo types"
        )
        usage_table.add_row(
            "   Purpose:", "Ensure repositories are properly configured and accessible"
        )
        usage_table.add_row("", "")
        usage_table.add_row(
            "🔧 Troubleshooting:", "Diagnose repository connectivity issues"
        )
        usage_table.add_row(
            "   Test Connectivity:", "./escmd.py repositories verify repo_name"
        )
        usage_table.add_row("   Check Config:", "./escmd.py repositories --format json")
        usage_table.add_row(
            "   Verify All Nodes:", "Ensure all cluster nodes can access repository"
        )
        usage_table.add_row(
            "   Monitor Status:", "Regular verification prevents backup failures"
        )
        usage_table.add_row(
            "   Purpose:", "Identify configuration problems before backup failures"
        )
        usage_table.add_row("", "")
        usage_table.add_row(
            "🚀 Repository Types:", "Understanding different repository configurations"
        )
        usage_table.add_row(
            "   S3 Repositories:", "AWS S3 bucket storage with encryption options"
        )
        usage_table.add_row(
            "   Filesystem:", "Local or network filesystem repositories"
        )
        usage_table.add_row(
            "   Azure Blob:", "Microsoft Azure blob storage repositories"
        )
        usage_table.add_row(
            "   Google Cloud:", "GCS bucket repositories with service accounts"
        )
        usage_table.add_row("   HDFS:", "Hadoop distributed filesystem repositories")
        usage_table.add_row("", "")
        usage_table.add_row(
            "⚡ Quick Reference:", "Common repository management workflows"
        )
        usage_table.add_row(
            "   New Cluster Setup:",
            "1. Create repository 2. Verify connectivity 3. Test snapshot",
        )
        usage_table.add_row(
            "   Before Backup:", "Always verify repository connectivity first"
        )
        usage_table.add_row(
            "   After Changes:", "Verify repository after configuration updates"
        )
        usage_table.add_row(
            "   Regular Audit:", "Monthly verification of repository accessibility"
        )

        # Display help panels
        self._display_help_panels(
            commands_table,
            examples_table,
            "📦 Repository Management Commands",
            "🚀 Repository Examples",
            usage_table,
            "🎯 Repository Management Workflows",
        )
