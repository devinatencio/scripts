"""
Help content for template-restore command.
"""

from .base_help_content import BaseHelpContent


class TemplateRestoreHelpContent(BaseHelpContent):
    """Help content for template-restore command."""

    def get_topic_name(self) -> str:
        return "template-restore"

    def get_topic_description(self) -> str:
        return "Restore an Elasticsearch template from a backup file"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("template-restore --backup-file <path>",  "Restore template from a backup JSON file",    "./escmd.py template-restore --backup-file ~/.escmd/template-backups/my-template.json")
        commands_table.add_row("list-backups",                           "List all available backup files",             "./escmd.py list-backups")
        commands_table.add_row("list-backups --name <template>",         "Filter backups by template name",             "")
        commands_table.add_row("list-backups --type <type>",             "Filter backups by template type",             "")
        commands_table.add_row("list-backups --backup-dir <path>",       "List backups in a custom directory",          "")

        usage_table.add_row("🔄 Restore Workflow:", "Step-by-step recovery process")
        usage_table.add_row("   Step 1 - Find backup:", "./escmd.py list-backups --name my-template")
        usage_table.add_row("   Step 2 - Note the path:","Copy the full path from list-backups output")
        usage_table.add_row("   Step 3 - Restore:",     "./escmd.py template-restore --backup-file <path>")
        usage_table.add_row("   Step 4 - Verify:",      "./escmd.py template my-template")
        usage_table.add_row("", "")
        usage_table.add_row("📁 Default Backup Location:", "~/.escmd/template-backups/")
        usage_table.add_row("   Filename format:", "<name>_<type>_<YYYYMMDD>_<HHMMSS>.json")
        usage_table.add_row("   Example:",         "my-logs-template_composable_20260101_120000.json")
        usage_table.add_row("", "")
        usage_table.add_row("⚠️  What Gets Restored:", "The full template definition from the backup")
        usage_table.add_row("   Template body:",    "All settings, mappings, aliases, patterns")
        usage_table.add_row("   Template type:",    "Determined from backup metadata")
        usage_table.add_row("   Overwrites current:","Existing template is replaced on restore")
        usage_table.add_row("", "")
        usage_table.add_row("💡 Pro Tips:", "")
        usage_table.add_row("   Before restoring:", "Backup the current state first if needed")
        usage_table.add_row("   Cross-cluster:",    "Backup files are portable across clusters")
        usage_table.add_row("   Automation:",       "Use --backup-file with absolute paths in scripts")

        self._display_help_panels(
            commands_table, examples_table,
            "🔄 template-restore Commands", "",
            usage_table, "🎯 Restore Workflows & Details"
        )
