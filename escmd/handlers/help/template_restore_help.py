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
        """Show detailed help for template-restore command."""
        help_styles, border_style = self._get_theme_styles()

        from rich.panel import Panel
        from rich.table import Table

        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=48)
        commands_table.add_column(style=help_styles.get('description', 'white'))

        commands_table.add_row("template-restore --backup-file <path>", "Restore template from a backup JSON file")
        commands_table.add_row("list-backups", "List all available backup files")
        commands_table.add_row("list-backups --name <template>", "Filter backups by template name")
        commands_table.add_row("list-backups --type <type>", "Filter backups by template type")
        commands_table.add_row("list-backups --backup-dir <path>", "List backups in a custom directory")

        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style=help_styles.get('example', 'bold green'), min_width=48)
        examples_table.add_column(style=help_styles.get('description', 'dim white'))

        examples_table.add_row("Find backup files:", "./escmd.py list-backups")
        examples_table.add_row("Filter by name:", "./escmd.py list-backups --name my-logs-template")
        examples_table.add_row("Restore from backup:", "./escmd.py template-restore --backup-file ~/.escmd/template-backups/my-logs-template_composable_20260101_120000.json")
        examples_table.add_row("Restore from custom dir:", "./escmd.py template-restore --backup-file /backups/es/my-template_legacy_20260101.json")
        examples_table.add_row("Verify after restore:", "./escmd.py template my-logs-template")

        # Workflow table
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style=help_styles.get('section_header', 'bold magenta'), min_width=48)
        usage_table.add_column(style=help_styles.get('description', 'dim white'))

        usage_table.add_row("🔄 Restore Workflow:", "Step-by-step recovery process")
        usage_table.add_row("   Step 1 - Find backup:", "./escmd.py list-backups --name my-template")
        usage_table.add_row("   Step 2 - Note the path:", "Copy the full path from list-backups output")
        usage_table.add_row("   Step 3 - Restore:", "./escmd.py template-restore --backup-file <path>")
        usage_table.add_row("   Step 4 - Verify:", "./escmd.py template my-template")
        usage_table.add_row("", "")
        usage_table.add_row("📁 Default Backup Location:", "~/.escmd/template-backups/")
        usage_table.add_row("   Filename format:", "<name>_<type>_<YYYYMMDD>_<HHMMSS>.json")
        usage_table.add_row("   Example:", "my-logs-template_composable_20260101_120000.json")
        usage_table.add_row("", "")
        usage_table.add_row("⚠️  What Gets Restored:", "The full template definition from the backup")
        usage_table.add_row("   Template body:", "All settings, mappings, aliases, patterns")
        usage_table.add_row("   Template type:", "Determined from backup metadata")
        usage_table.add_row("   Overwrites current:", "Existing template is replaced on restore")
        usage_table.add_row("", "")
        usage_table.add_row("💡 Pro Tips:", "")
        usage_table.add_row("   Before restoring:", "Backup the current state first if needed")
        usage_table.add_row("   Cross-cluster:", "Backup files are portable across clusters")
        usage_table.add_row("   Automation:", "Use --backup-file with absolute paths in scripts")

        self.console.print()
        self.console.print(Panel(
            commands_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🔄 template-restore Commands[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
        self.console.print(Panel(
            examples_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🚀 template-restore Examples[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
        self.console.print(Panel(
            usage_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🎯 Restore Workflows & Details[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
