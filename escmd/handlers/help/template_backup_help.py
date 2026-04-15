"""
Help content for template-backup command.
"""

from .base_help_content import BaseHelpContent


class TemplateBackupHelpContent(BaseHelpContent):
    """Help content for template-backup command."""

    def get_topic_name(self) -> str:
        return "template-backup"

    def get_topic_description(self) -> str:
        return "Create a backup of an Elasticsearch template to a JSON file"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("template-backup <name>",                    "Backup a template (auto-detects type)",                          "./escmd.py template-backup my-logs-template")
        commands_table.add_row("template-backup <name> --type legacy",      "Backup a legacy (_template) template",                          "")
        commands_table.add_row("template-backup <name> --type composable",  "Backup a composable (_index_template) template",                "")
        commands_table.add_row("template-backup <name> --type component",   "Backup a component (_component_template) template",             "")
        commands_table.add_row("template-backup <name> --backup-dir <path>","Save backup to a custom directory",                             "")
        commands_table.add_row("template-backup <name> --cluster <name>",   "Tag backup with cluster name metadata",                         "")

        usage_table.add_row("💾 Backup File Format:", "JSON file with full template definition + metadata")
        usage_table.add_row("   Default Location:", "~/.escmd/template-backups/")
        usage_table.add_row("   Filename Pattern:", "<name>_<type>_<timestamp>.json")
        usage_table.add_row("   Metadata Included:","cluster name, backup date, template type")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 Before Modifying:", "Always backup before making changes")
        usage_table.add_row("   Step 1:",           "./escmd.py template-backup critical-template")
        usage_table.add_row("   Step 2:",           "./escmd.py template-modify critical-template -f <field> -v <value>")
        usage_table.add_row("   Step 3 (if needed):","./escmd.py template-restore --backup-file <path>")
        usage_table.add_row("", "")
        usage_table.add_row("📦 Bulk Backup Strategy:", "Backup all critical templates before cluster changes")
        usage_table.add_row("   List templates:", "./escmd.py templates --type composable")
        usage_table.add_row("   Backup each:",    "./escmd.py template-backup <name> --cluster prod")
        usage_table.add_row("   Verify backups:", "./escmd.py list-backups")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 Type Auto-Detection:", "Searches legacy → composable → component")
        usage_table.add_row("   Use --type:",    "Specify type explicitly to skip detection overhead")
        usage_table.add_row("   Auto order:",    "legacy, then composable, then component")

        self._display_help_panels(
            commands_table, examples_table,
            "💾 template-backup Commands", "",
            usage_table, "🎯 Backup Workflows & Details"
        )
