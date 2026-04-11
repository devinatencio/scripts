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
        """Show detailed help for template-backup command."""
        help_styles, border_style = self._get_theme_styles()

        from rich.panel import Panel
        from rich.table import Table

        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=42)
        commands_table.add_column(style=help_styles.get('description', 'white'))

        commands_table.add_row("template-backup <name>", "Backup a template (auto-detects type)")
        commands_table.add_row("template-backup <name> --type legacy", "Backup a legacy (_template) template")
        commands_table.add_row("template-backup <name> --type composable", "Backup a composable (_index_template) template")
        commands_table.add_row("template-backup <name> --type component", "Backup a component (_component_template) template")
        commands_table.add_row("template-backup <name> --backup-dir <path>", "Save backup to a custom directory")
        commands_table.add_row("template-backup <name> --cluster <name>", "Tag backup with cluster name metadata")

        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style=help_styles.get('example', 'bold green'), min_width=42)
        examples_table.add_column(style=help_styles.get('description', 'dim white'))

        examples_table.add_row("Basic backup:", "./escmd.py template-backup my-logs-template")
        examples_table.add_row("Backup legacy template:", "./escmd.py template-backup old-template --type legacy")
        examples_table.add_row("Backup composable:", "./escmd.py template-backup logs-template --type composable")
        examples_table.add_row("Custom backup dir:", "./escmd.py template-backup my-template --backup-dir /backups/es")
        examples_table.add_row("Tag with cluster:", "./escmd.py template-backup my-template --cluster production")
        examples_table.add_row("Full options:", "./escmd.py template-backup my-template --type composable --backup-dir /backups --cluster prod")
        examples_table.add_row("List backups after:", "./escmd.py list-backups")
        examples_table.add_row("Filter backups:", "./escmd.py list-backups --name my-template")

        # Workflows table
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style=help_styles.get('section_header', 'bold magenta'), min_width=42)
        usage_table.add_column(style=help_styles.get('description', 'dim white'))

        usage_table.add_row("💾 Backup File Format:", "JSON file with full template definition + metadata")
        usage_table.add_row("   Default Location:", "~/.escmd/template-backups/")
        usage_table.add_row("   Filename Pattern:", "<name>_<type>_<timestamp>.json")
        usage_table.add_row("   Metadata Included:", "cluster name, backup date, template type")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 Before Modifying:", "Always backup before making changes")
        usage_table.add_row("   Step 1:", "./escmd.py template-backup critical-template")
        usage_table.add_row("   Step 2:", "./escmd.py template-modify critical-template -f <field> -v <value>")
        usage_table.add_row("   Step 3 (if needed):", "./escmd.py template-restore --backup-file <path>")
        usage_table.add_row("", "")
        usage_table.add_row("📦 Bulk Backup Strategy:", "Backup all critical templates before cluster changes")
        usage_table.add_row("   List templates:", "./escmd.py templates --type composable")
        usage_table.add_row("   Backup each:", "./escmd.py template-backup <name> --cluster prod")
        usage_table.add_row("   Verify backups:", "./escmd.py list-backups")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 Type Auto-Detection:", "Searches legacy → composable → component")
        usage_table.add_row("   Use --type:", "Specify type explicitly to skip detection overhead")
        usage_table.add_row("   Auto order:", "legacy, then composable, then component")

        self.console.print()
        self.console.print(Panel(
            commands_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]💾 template-backup Commands[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
        self.console.print(Panel(
            examples_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🚀 template-backup Examples[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
        self.console.print(Panel(
            usage_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🎯 Backup Workflows & Details[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
