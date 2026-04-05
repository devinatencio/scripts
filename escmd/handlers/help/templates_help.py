"""
Help content for template commands.
"""

from .base_help_content import BaseHelpContent


class TemplatesHelpContent(BaseHelpContent):
    """Help content for template commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for templates help."""
        return "templates"

    def get_topic_description(self) -> str:
        """Get the topic description for templates help."""
        return "Index template management operations"

    def show_help(self) -> None:
        """Show detailed help for template commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table = self._create_usage_table()

        # Add commands
        commands_table.add_row("templates", "List all templates with type filtering and statistics")
        commands_table.add_row("template <name>", "Show detailed information for a specific template")
        commands_table.add_row("template-usage", "Analyze template usage and pattern matching across indices")
        commands_table.add_row("template-modify <name>", "Modify template fields (set, append, remove, delete) with backup and dry-run options")
        commands_table.add_row("template-backup <name>", "Create a backup of a template")
        commands_table.add_row("template-restore", "Restore a template from backup file")
        commands_table.add_row("template-create", "Create templates from JSON file or inline definition")
        commands_table.add_row("list-backups", "List available template backups with filtering")

        # Add examples
        examples_table.add_row("List all templates:", "./escmd.py templates")
        examples_table.add_row("List composable only:", "./escmd.py templates --type composable")
        examples_table.add_row("Template details:", "./escmd.py template my-logs-template")
        examples_table.add_row("Auto-detect type:", "./escmd.py template my-template --type auto")
        examples_table.add_row("Template usage analysis:", "./escmd.py template-usage")
        examples_table.add_row("Set template field:", "./escmd.py template-modify my-template -f settings.index.replicas -v 2")
        examples_table.add_row("Append to list field:", "./escmd.py template-modify my-template -f settings.index.routing.allocation.exclude._name -o append -v 'host1-*'")
        examples_table.add_row("Remove from list field:", "./escmd.py template-modify my-template -f settings.index.routing.allocation.exclude._name -o remove -v 'old-host-*'")
        examples_table.add_row("Delete field:", "./escmd.py template-modify my-template -f settings.index.routing -o delete")
        examples_table.add_row("Dry run modification:", "./escmd.py template-modify my-template -f settings.index.shards --dry-run")
        examples_table.add_row("Backup template:", "./escmd.py template-backup my-template")
        examples_table.add_row("Custom backup location:", "./escmd.py template-backup my-template --backup-dir /path/to/backups")
        examples_table.add_row("Restore from backup:", "./escmd.py template-restore --backup-file /path/to/backup.json")
        examples_table.add_row("Create from JSON file:", "./escmd.py template-create --file templates.json")
        examples_table.add_row("Create inline component:", "./escmd.py template-create --name my-template --definition '{...}'")
        examples_table.add_row("Dry run creation:", "./escmd.py template-create --file templates.json --dry-run")
        examples_table.add_row("List all backups:", "./escmd.py list-backups")
        examples_table.add_row("Filter backups by name:", "./escmd.py list-backups --name my-template")
        examples_table.add_row("JSON output:", "./escmd.py templates --format json")

        # Add usage patterns
        usage_table.add_row("📋 Template Inventory:", "Audit and monitor template configurations")
        usage_table.add_row("   List All Types:", "./escmd.py templates")
        usage_table.add_row("   Check Legacy:", "./escmd.py templates --type legacy")
        usage_table.add_row("   Check Composable:", "./escmd.py templates --type composable")
        usage_table.add_row("   Component Templates:", "./escmd.py templates --type component")
        usage_table.add_row("   Purpose:", "Monitor template types and migration status")
        usage_table.add_row("", "")
        usage_table.add_row("🔍 Template Analysis:", "Deep dive into template configuration and usage")
        usage_table.add_row("   Template Detail:", "./escmd.py template critical-logs-template")
        usage_table.add_row("   Usage Patterns:", "./escmd.py template-usage")
        usage_table.add_row("   Pattern Matching:", "See which indices match template patterns")
        usage_table.add_row("   Unused Templates:", "Identify templates not matching any indices")
        usage_table.add_row("", "")
        usage_table.add_row("🧰 Template Modifications:", "Safe template updates with backup and verification")
        usage_table.add_row("   Preview Changes:", "./escmd.py template-modify my-template -f settings.index.replicas -v 2 --dry-run")
        usage_table.add_row("   Set Field Value:", "./escmd.py template-modify my-template -f settings.index.replicas -v 2")
        usage_table.add_row("   Append to List:", "./escmd.py template-modify manual_template -f template.settings.index.routing.allocation.exclude._name -o append -v 'host1-*,host2-*'")
        usage_table.add_row("   Remove from List:", "./escmd.py template-modify manual_template -f template.settings.index.routing.allocation.exclude._name -o remove -v 'old-host-*'")
        usage_table.add_row("   Replace Entire List:", "./escmd.py template-modify manual_template -f template.settings.index.routing.allocation.exclude._name -o set -v 'new-host1-*,new-host2-*'")
        usage_table.add_row("   Delete Field:", "./escmd.py template-modify my-template -f settings.index.routing -o delete")
        usage_table.add_row("   No Backup:", "./escmd.py template-modify my-template -f settings.test -v value --no-backup")
        usage_table.add_row("   Custom Backup Dir:", "./escmd.py template-modify my-template -f field -v value --backup-dir /custom/path")
        usage_table.add_row("", "")
        usage_table.add_row("💾 Backup Management:", "Template backup and restore operations")
        usage_table.add_row("   Create Backup:", "./escmd.py template-backup critical-template")
        usage_table.add_row("   With Metadata:", "./escmd.py template-backup my-template --cluster production")
        usage_table.add_row("   List Backups:", "./escmd.py list-backups")
        usage_table.add_row("   Filter by Type:", "./escmd.py list-backups --type composable")
        usage_table.add_row("   Restore Template:", "./escmd.py template-restore --backup-file /path/to/backup.json")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 Migration Workflows:", "Legacy to composable template migration")
        usage_table.add_row("   Audit Legacy:", "./escmd.py templates --type legacy")
        usage_table.add_row("   Backup Legacy:", "./escmd.py template-backup old-template --type legacy")
        usage_table.add_row("   Check Usage:", "./escmd.py template-usage")
        usage_table.add_row("   Plan Migration:", "Use template details to plan composable equivalents")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Automation & Monitoring:", "JSON output for scripts and monitoring")
        usage_table.add_row("   JSON Templates:", "./escmd.py templates --format json")
        usage_table.add_row("   JSON Template Detail:", "./escmd.py template my-template --format json")
        usage_table.add_row("   JSON Usage Data:", "./escmd.py template-usage --format json")
        usage_table.add_row("   JSON Backups:", "./escmd.py list-backups --format json")
        usage_table.add_row("   Scripting:", "Parse JSON output for automated template management")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 Template Types Guide:", "Understanding different template types")
        usage_table.add_row("   Legacy Templates:", "Traditional _template API (all ES versions)")
        usage_table.add_row("   • Precedence:", "Uses 'order' field (higher wins)")
        usage_table.add_row("   • Structure:", "Single template definition")
        usage_table.add_row("   Composable Templates:", "Modern _index_template API (ES 7.8+)")
        usage_table.add_row("   • Precedence:", "Uses 'priority' field (higher wins)")
        usage_table.add_row("   • Composition:", "Can include multiple component templates")
        usage_table.add_row("   • Data Streams:", "Support for data stream configuration")
        usage_table.add_row("   Component Templates:", "Reusable _component_template building blocks")
        usage_table.add_row("   • Content:", "Settings, mappings, or aliases only")
        usage_table.add_row("   • Usage:", "Referenced by composable templates")
        usage_table.add_row("", "")
        usage_table.add_row("🔧 Modification Operations:", "Available operations for template-modify command")
        usage_table.add_row("   • set:", "Replace field value completely (default operation)")
        usage_table.add_row("   • append:", "Add values to comma-separated lists (avoids duplicates)")
        usage_table.add_row("   • remove:", "Remove specific values from comma-separated lists")
        usage_table.add_row("   • delete:", "Remove field entirely from template")
        usage_table.add_row("   Common Use Case:", "Host exclusion lists for cluster maintenance")
        usage_table.add_row("   List Field Example:", "template.settings.index.routing.allocation.exclude._name")

        # Display help panels
        self._display_help_panels(
            commands_table, examples_table,
            "📝 Template Management Commands", "🚀 Template Examples",
            usage_table, "🎯 Template Workflows & Use Cases"
        )
