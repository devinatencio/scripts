"""
Help content for template-modify command.
"""

from .base_help_content import BaseHelpContent


class TemplateModifyHelpContent(BaseHelpContent):
    """Help content for template-modify command."""

    def get_topic_name(self) -> str:
        return "template-modify"

    def get_topic_description(self) -> str:
        return "Modify template fields with set/append/remove/delete operations"

    def show_help(self) -> None:
        """Show detailed help for template-modify command."""
        help_styles, border_style = self._get_theme_styles()

        from rich.panel import Panel
        from rich.table import Table

        # Commands / flags table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=48)
        commands_table.add_column(style=help_styles.get('description', 'white'))

        commands_table.add_row("template-modify <name> -f <field> -v <value>", "Set a field value (default operation)")
        commands_table.add_row("template-modify <name> -f <field> -o set -v <value>", "Explicitly replace field value")
        commands_table.add_row("template-modify <name> -f <field> -o append -v <value>", "Append value(s) to a comma-separated list")
        commands_table.add_row("template-modify <name> -f <field> -o remove -v <value>", "Remove value(s) from a comma-separated list")
        commands_table.add_row("template-modify <name> -f <field> -o delete", "Delete the field entirely")
        commands_table.add_row("template-modify <name> ... --dry-run", "Preview changes without applying them")
        commands_table.add_row("template-modify <name> ... --no-backup", "Skip automatic backup before modifying")
        commands_table.add_row("template-modify <name> ... --backup-dir <path>", "Save backup to a custom directory")
        commands_table.add_row("template-modify <name> ... --type <type>", "Specify template type (auto/legacy/composable/component)")

        # Operations table
        ops_table = Table.grid(padding=(0, 3))
        ops_table.add_column(style=help_styles.get('command', 'bold yellow'), min_width=12)
        ops_table.add_column(style=help_styles.get('description', 'white'))

        ops_table.add_row("set", "Replace the field value entirely (default). Works for strings, numbers, and lists.")
        ops_table.add_row("append", "Add one or more values to a comma-separated list field. Skips duplicates.")
        ops_table.add_row("remove", "Remove one or more values from a comma-separated list field.")
        ops_table.add_row("delete", "Remove the field key entirely from the template definition.")

        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style=help_styles.get('example', 'bold green'), min_width=48)
        examples_table.add_column(style=help_styles.get('description', 'dim white'))

        examples_table.add_row("Set replica count:", "./escmd.py template-modify my-template -f template.settings.index.number_of_replicas -v 2")
        examples_table.add_row("Dry run first:", "./escmd.py template-modify my-template -f template.settings.index.number_of_replicas -v 2 --dry-run")
        examples_table.add_row("Append host exclusion:", "./escmd.py template-modify my-template -f template.settings.index.routing.allocation.exclude._name -o append -v 'ess01-*'")
        examples_table.add_row("Append multiple hosts:", "./escmd.py template-modify my-template -f template.settings.index.routing.allocation.exclude._name -o append -v 'ess01-*,ess02-*'")
        examples_table.add_row("Remove host exclusion:", "./escmd.py template-modify my-template -f template.settings.index.routing.allocation.exclude._name -o remove -v 'ess01-*'")
        examples_table.add_row("Replace exclusion list:", "./escmd.py template-modify my-template -f template.settings.index.routing.allocation.exclude._name -o set -v 'ess03-*,ess04-*'")
        examples_table.add_row("Delete a field:", "./escmd.py template-modify my-template -f template.settings.index.routing -o delete")
        examples_table.add_row("No backup:", "./escmd.py template-modify my-template -f settings.index.refresh_interval -v '30s' --no-backup")
        examples_table.add_row("Custom backup dir:", "./escmd.py template-modify my-template -f settings.index.replicas -v 1 --backup-dir /backups")
        examples_table.add_row("Legacy template:", "./escmd.py template-modify old-template --type legacy -f settings.index.replicas -v 1")

        # Field path guide
        field_table = Table.grid(padding=(0, 3))
        field_table.add_column(style=help_styles.get('section_header', 'bold magenta'), min_width=48)
        field_table.add_column(style=help_styles.get('description', 'dim white'))

        field_table.add_row("📍 Field Path Notation:", "Use dot notation to navigate the template JSON")
        field_table.add_row("   Composable replicas:", "template.settings.index.number_of_replicas")
        field_table.add_row("   Composable shards:", "template.settings.index.number_of_shards")
        field_table.add_row("   Allocation exclude:", "template.settings.index.routing.allocation.exclude._name")
        field_table.add_row("   Refresh interval:", "template.settings.index.refresh_interval")
        field_table.add_row("   Legacy replicas:", "settings.index.number_of_replicas")
        field_table.add_row("   Priority (composable):", "priority")
        field_table.add_row("   Index patterns:", "index_patterns")
        field_table.add_row("", "")
        field_table.add_row("🔒 Safety Features:", "Built-in safeguards for safe modifications")
        field_table.add_row("   Auto-backup:", "Backup created before every change (default)")
        field_table.add_row("   Dry run:", "Use --dry-run to preview without applying")
        field_table.add_row("   Restore path:", "./escmd.py template-restore --backup-file <path>")
        field_table.add_row("", "")
        field_table.add_row("💡 Append/Remove Tips:", "For comma-separated list fields")
        field_table.add_row("   Multiple values:", "Separate with commas: -v 'host1-*,host2-*'")
        field_table.add_row("   No duplicates:", "append skips values already in the list")
        field_table.add_row("   Partial remove:", "remove only removes the specified values")

        self.console.print()
        self.console.print(Panel(
            commands_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🔧 template-modify Commands & Flags[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
        self.console.print(Panel(
            ops_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🔩 Available Operations[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
        self.console.print(Panel(
            examples_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🚀 template-modify Examples[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
        self.console.print(Panel(
            field_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🎯 Field Paths & Safety Guide[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
