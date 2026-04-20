#!/usr/bin/env python3

from .base_handler import BaseHandler
from rich.table import Table


class TemplateHandler(BaseHandler):
    """Handler for Elasticsearch template operations."""

    def handle_templates(self):
        """Handle templates list command."""
        template_type = getattr(self.args, 'type', 'all')

        if self.args.format == 'json':
            templates_data = self.es_client.template_commands.list_all_templates(template_type)
            self.es_client.pretty_print_json(templates_data)
        else:
            self._print_templates_table(template_type)

    def handle_template(self):
        """Handle single template detail command."""
        template_name = getattr(self.args, 'name', None)

        if not template_name:
            self._show_template_help()
            return

        template_type = getattr(self.args, 'type', 'auto')

        if self.args.format == 'json':
            template_data = self.es_client.template_commands.get_template_detail(template_name, template_type)
            self.es_client.pretty_print_json(template_data)
        else:
            self._print_template_detail(template_name, template_type)

    def handle_template_usage(self):
        """Handle template usage analysis command."""
        if self.args.format == 'json':
            usage_data = self.es_client.template_commands.get_templates_usage()
            self.es_client.pretty_print_json(usage_data)
        else:
            self._print_template_usage()

    def _show_template_help(self):
        """Display help screen for template commands."""
        from rich.panel import Panel
        from rich.text import Text

        console = self.console
        ss = self.es_client.style_system
        tm = self.es_client.theme_manager

        primary_style = ss.get_semantic_style("primary")
        success_style = ss.get_semantic_style("success")
        muted_style = ss._get_style('semantic', 'muted', 'dim')
        border_style = ss._get_style('table_styles', 'border_style', 'white')
        header_style = tm.get_theme_styles().get('header_style', 'bold white') if tm else 'bold white'
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        box_style = ss.get_table_box()

        header_panel = Panel(
            Text("Run ./escmd.py template <name> [options]", style="bold white"),
            title=f"[{title_style}]📋 Elasticsearch Templates[/{title_style}]",
            subtitle=Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]on any command for full options[/dim]"),
            border_style=border_style,
            padding=(1, 2),
            expand=True,
        )

        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border_style,
            box=box_style,
            show_lines=False,
            expand=True,
        )
        table.add_column("Command / Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("templates", "List all templates (legacy, composable, component)", "templates"),
            ("templates --type composable", "List only composable templates", "templates --type composable"),
            ("template <name>", "Show detailed info for a specific template", "template my-template"),
            ("template <name> --type legacy", "Specify template type", "template my-template --type legacy"),
            ("template-usage", "Analyze template usage across indices", "template-usage"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Management ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        mgmt = [
            ("template-backup <name>", "Backup a template to JSON file", "template-backup my-template"),
            ("template-restore <file>", "Restore a template from backup", "template-restore backup.json"),
            ("template-modify <name>", "Modify template fields", "template-modify my-template --set field value"),
            ("template-create --file <f>", "Create template from JSON file", "template-create --file template.json"),
            ("list-backups", "List available template backups", "list-backups"),
        ]
        for i, (opt, desc, ex) in enumerate(mgmt):
            table.add_row(
                Text(opt, style=ss._get_style('semantic', 'secondary', 'magenta')),
                desc,
                Text(f"./escmd.py {ex}", style=muted_style),
                style=ss.get_zebra_style(i) if ss else None,
            )

        console.print()
        console.print(header_panel)
        console.print()
        console.print(table)
        console.print()

    def _print_templates_table(self, template_type='all'):
        """Print formatted table of templates using the template renderer."""
        try:
            templates_data = self.es_client.template_commands.list_all_templates(template_type)

            # Use template renderer for display
            if hasattr(self.es_client, 'template_renderer'):
                self.es_client.template_renderer.print_templates_table(templates_data, template_type)
            else:
                # Fallback to simple display if renderer not available
                self.console.print("[red]Template renderer not available[/red]")
                self.es_client.pretty_print_json(templates_data)

        except Exception as e:
            self.console.print(f"[red]Error listing templates: {str(e)}[/red]")

    def _print_template_detail(self, template_name, template_type='auto'):
        """Print detailed information about a specific template using the template renderer."""
        try:
            template_data = self.es_client.template_commands.get_template_detail(template_name, template_type)

            # Use template renderer for display
            if hasattr(self.es_client, 'template_renderer'):
                self.es_client.template_renderer.print_template_detail(template_data)
            else:
                # Fallback to simple display if renderer not available
                self.console.print("[red]Template renderer not available[/red]")
                self.es_client.pretty_print_json(template_data)

        except Exception as e:
            self.console.print(f"[red]Error getting template details: {str(e)}[/red]")

    def _print_template_usage(self):
        """Print template usage analysis using the template renderer."""
        try:
            usage_data = self.es_client.template_commands.get_templates_usage()

            # Use template renderer for display
            if hasattr(self.es_client, 'template_renderer'):
                self.es_client.template_renderer.print_template_usage(usage_data)
            else:
                # Fallback to simple display if renderer not available
                self.console.print("[red]Template renderer not available[/red]")
                self.es_client.pretty_print_json(usage_data)

        except Exception as e:
            self.console.print(f"[red]Error analyzing template usage: {str(e)}[/red]")

    def handle_template_modify(self):
        """Handle template modification command."""
        template_name = getattr(self.args, 'name', None)

        if not template_name:
            self._show_template_modify_help()
            return

        template_type = getattr(self.args, 'type', 'auto')
        field_path = getattr(self.args, 'field', None)
        operation = getattr(self.args, 'operation', 'set')
        value = getattr(self.args, 'value', '')
        backup = getattr(self.args, 'backup', True)
        backup_dir = getattr(self.args, 'backup_dir', None)
        dry_run = getattr(self.args, 'dry_run', False)

        if not field_path:
            self._show_template_modify_help()
            return

        if not value and operation != 'delete':
            self.console.print("[red]Error: Value is required for this operation[/red]")
            return

        try:
            if dry_run:
                self._handle_dry_run_modify(template_name, template_type, field_path, operation, value)
            else:
                self._handle_actual_modify(template_name, template_type, field_path, operation, value, backup, backup_dir)

        except Exception as e:
            self.console.print(f"[red]Template modification failed: {str(e)}[/red]")

    def _show_template_modify_help(self):
        """Display help screen for template-modify command."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = self.console
        ss = self.es_client.style_system
        tm = self.es_client.theme_manager

        primary_style = ss.get_semantic_style("primary")
        success_style = ss.get_semantic_style("success")
        muted_style = ss._get_style('semantic', 'muted', 'dim')
        border_style = ss._get_style('table_styles', 'border_style', 'white')
        header_style = tm.get_theme_styles().get('header_style', 'bold white') if tm else 'bold white'
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        box_style = ss.get_table_box()

        header_panel = Panel(
            Text("Run ./escmd.py template-modify <name> --field <path> [options]", style="bold white"),
            title=f"[{title_style}]🔧 Modify Template[/{title_style}]",
            subtitle=Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]for full options[/dim]"),
            border_style=border_style,
            padding=(1, 2),
            expand=True,
        )

        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border_style,
            box=box_style,
            show_lines=False,
            expand=True,
        )
        table.add_column("Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("--field <path>", "Dot-notation path to the field", "template-modify my-tpl --field template.settings.index.number_of_replicas --value 2"),
            ("--value <val>", "New value to set", "template-modify my-tpl --field some.field --value newval"),
            ("--operation set", "Set field value (default)", "template-modify my-tpl --field f --value v"),
            ("--operation append", "Append value to a list", "template-modify my-tpl --field some.list --operation append --value node1"),
            ("--operation delete", "Delete a field entirely", "template-modify my-tpl --field some.field --operation delete"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Safety ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        safety = [
            ("--dry-run", "Preview changes without applying", "template-modify my-tpl --field f --value v --dry-run"),
            ("--no-backup", "Skip automatic backup", "template-modify my-tpl --field f --value v --no-backup"),
        ]
        for i, (opt, desc, ex) in enumerate(safety):
            table.add_row(
                Text(opt, style=ss._get_style('semantic', 'secondary', 'magenta')),
                desc,
                Text(f"./escmd.py {ex}", style=muted_style),
                style=ss.get_zebra_style(i) if ss else None,
            )

        console.print()
        console.print(header_panel)
        console.print()
        console.print(table)
        console.print()

    def handle_template_backup(self):
        """Handle template backup command."""
        template_name = getattr(self.args, 'name', None)

        if not template_name:
            self._show_template_backup_help()
            return

        template_type = getattr(self.args, 'type', 'auto')
        backup_dir = getattr(self.args, 'backup_dir', None)
        cluster_name = getattr(self.args, 'cluster', None)

        try:
            result = self.es_client.template_commands.backup_template(
                template_name, template_type, backup_dir, cluster_name
            )

            if result['success']:
                self.console.print("[green]✓[/green] Template backup created successfully")
                self.console.print(f"  Template: {result['template_name']} ({result['template_type']})")
                self.console.print(f"  Backup file: {result['backup_file']}")
            else:
                self.console.print(f"[red]✗[/red] Backup failed: {result['error']}")

        except Exception as e:
            self.console.print(f"[red]Template backup failed: {str(e)}[/red]")

    def _show_template_backup_help(self):
        """Display help screen for template-backup command."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = self.console
        ss = self.es_client.style_system
        tm = self.es_client.theme_manager

        primary_style = ss.get_semantic_style("primary")
        success_style = ss.get_semantic_style("success")
        muted_style = ss._get_style('semantic', 'muted', 'dim')
        border_style = ss._get_style('table_styles', 'border_style', 'white')
        header_style = tm.get_theme_styles().get('header_style', 'bold white') if tm else 'bold white'
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        box_style = ss.get_table_box()

        header_panel = Panel(
            Text("Run ./escmd.py template-backup <name> [options]", style="bold white"),
            title=f"[{title_style}]💾 Backup Template[/{title_style}]",
            subtitle=Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]for full options[/dim]"),
            border_style=border_style,
            padding=(1, 2),
            expand=True,
        )

        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border_style,
            box=box_style,
            show_lines=False,
            expand=True,
        )
        table.add_column("Usage / Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("template-backup <name>", "Backup a template (auto-detect type)", "template-backup my-template"),
            ("--type <type>", "Specify template type", "template-backup my-tpl --type legacy"),
            ("--backup-dir <path>", "Custom backup directory", "template-backup my-tpl --backup-dir /tmp"),
            ("--cluster <name>", "Cluster name for metadata", "template-backup my-tpl --cluster prod"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Related ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        related = [
            ("template-restore", "Restore a template from backup", "template-restore --backup-file backup.json"),
            ("list-backups", "List available backup files", "list-backups"),
        ]
        for i, (opt, desc, ex) in enumerate(related):
            table.add_row(
                Text(opt, style=ss._get_style('semantic', 'secondary', 'magenta')),
                desc,
                Text(f"./escmd.py {ex}", style=muted_style),
                style=ss.get_zebra_style(i) if ss else None,
            )

        console.print()
        console.print(header_panel)
        console.print()
        console.print(table)
        console.print()

    def handle_template_restore(self):
        """Handle template restore command."""
        backup_file = getattr(self.args, 'backup_file', None)

        if not backup_file:
            self._show_template_restore_help()
            return

        try:
            result = self.es_client.template_commands.restore_template(backup_file)

            if result['success']:
                self.console.print("[green]✓[/green] Template restored successfully")
                self.console.print(f"  Template: {result['template_name']} ({result['template_type']})")
                self.console.print(f"  From backup: {result['backup_file']}")
            else:
                self.console.print(f"[red]✗[/red] Restore failed: {result['error']}")

        except Exception as e:
            self.console.print(f"[red]Template restore failed: {str(e)}[/red]")

    def _show_template_restore_help(self):
        """Display help screen for template-restore command."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = self.console
        ss = self.es_client.style_system
        tm = self.es_client.theme_manager

        primary_style = ss.get_semantic_style("primary")
        success_style = ss.get_semantic_style("success")
        muted_style = ss._get_style('semantic', 'muted', 'dim')
        border_style = ss._get_style('table_styles', 'border_style', 'white')
        header_style = tm.get_theme_styles().get('header_style', 'bold white') if tm else 'bold white'
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        box_style = ss.get_table_box()

        header_panel = Panel(
            Text("Run ./escmd.py template-restore --backup-file <path>", style="bold white"),
            title=f"[{title_style}]🔄 Restore Template[/{title_style}]",
            subtitle=Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]for full options[/dim]"),
            border_style=border_style,
            padding=(1, 2),
            expand=True,
        )

        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border_style,
            box=box_style,
            show_lines=False,
            expand=True,
        )
        table.add_column("Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("--backup-file <path>", "Path to backup JSON file", "template-restore --backup-file backup.json"),
            ("list-backups", "List available backup files", "list-backups"),
            ("list-backups --name <n>", "Filter backups by template name", "list-backups --name my-template"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        console.print()
        console.print(header_panel)
        console.print()
        console.print(table)
        console.print()

    def handle_list_backups(self):
        """Handle list backups command."""
        template_name = getattr(self.args, 'name', None)
        template_type = getattr(self.args, 'type', None)
        backup_dir = getattr(self.args, 'backup_dir', None)

        try:
            result = self.es_client.template_commands.list_backups(template_name, template_type, backup_dir)

            if result['success']:
                if self.args.format == 'json':
                    self.es_client.pretty_print_json(result['backups'])
                else:
                    self._print_backups_table(result['backups'])
            else:
                self.console.print(f"[red]Failed to list backups: {result['error']}[/red]")

        except Exception as e:
            self.console.print(f"[red]Error listing backups: {str(e)}[/red]")

    def _handle_dry_run_modify(self, template_name, template_type, field_path, operation, value):
        """Handle dry run template modification."""
        self.console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")
        self.console.print()

        # Get current template data
        template_data = self.es_client.template_commands.get_template_detail(template_name, template_type)

        if not template_data.get('found', False):
            self.console.print(f"[red]Template '{template_name}' not found[/red]")
            return

        actual_template_type = template_data.get('type', template_type)

        # Extract template definition
        if actual_template_type == 'component':
            template_def = template_data['template_data']['component_template']
        elif actual_template_type == 'composable':
            template_def = template_data['template_data']['index_template']
        elif actual_template_type == 'legacy':
            template_def = template_data['template_data']
        else:
            self.console.print(f"[red]Unknown template type: {actual_template_type}[/red]")
            return

        # Show what would change
        try:
            from template_utils.field_manipulation import TemplateModifier
        except ImportError:
            from ..template_utils.field_manipulation import TemplateModifier
        modifier = TemplateModifier()
        current_value, field_exists = modifier.get_field_value(template_def, field_path)

        self.console.print(f"[bold]Template:[/bold] {template_name} ({actual_template_type})")
        self.console.print(f"[bold]Field path:[/bold] {field_path}")
        self.console.print(f"[bold]Operation:[/bold] {operation}")
        self.console.print(f"[bold]Value:[/bold] {value}")
        self.console.print()

        if field_exists:
            self.console.print(f"[bold]Current value:[/bold] {current_value}")

            # Preview the change
            import copy
            preview_template = copy.deepcopy(template_def)
            modifier.modify_field(preview_template, field_path, operation, value)
            new_value, _ = modifier.get_field_value(preview_template, field_path)
            self.console.print(f"[bold]New value:[/bold] {new_value}")
        else:
            self.console.print("[yellow]Field does not currently exist[/yellow]")
            if operation == 'set':
                self.console.print(f"[bold]Would create field with value:[/bold] {value}")
            else:
                self.console.print(f"[yellow]Operation '{operation}' on non-existent field will be treated as 'set'[/yellow]")

    def _handle_actual_modify(self, template_name, template_type, field_path, operation, value, backup, backup_dir):
        """Handle actual template modification."""
        cluster_name = getattr(self.location_config, 'name', None) if self.location_config else None

        result = self.es_client.template_commands.modify_template(
            template_name, template_type, field_path, operation, value, backup, backup_dir, cluster_name
        )

        if result['success']:
            self.console.print("[green]✓[/green] Template modified successfully")
            self.console.print(f"  Template: {result['template_name']} ({result['template_type']})")
            self.console.print(f"  Field: {result['field_path']}")
            self.console.print(f"  Operation: {result['operation']}")

            if result['original_value'] is not None:
                self.console.print(f"  Original value: {result['original_value']}")
            if result['new_value'] is not None:
                self.console.print(f"  New value: {result['new_value']}")

            if result['backup_created']:
                self.console.print(f"  Backup created: {result['backup_file']}")
        else:
            self.console.print(f"[red]✗[/red] Template modification failed: {result['error']}")
            if result['backup_created']:
                self.console.print(f"  Backup was created: {result['backup_file']}")

    def _print_backups_table(self, backups):
        """Print formatted table of backups."""
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table as InnerTable

        ss = getattr(self.es_client, 'style_system', None)
        tm = getattr(self.es_client, 'theme_manager', None)
        border = tm.get_theme_styles().get('border_style', 'cyan') if tm else 'cyan'
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        warning_style = ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'
        muted_style = ss._get_style('semantic', 'muted', 'dim') if ss else 'dim'
        primary_style = ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan'

        if not backups:
            from rich.align import Align
            msg_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            msg_table.add_column("Icon", justify="center", width=3)
            msg_table.add_column("Text")
            msg_table.add_row("📭", Text("No backups found", style=warning_style))
            msg_table.add_row("", Text(""))
            msg_table.add_row("💡", Text("Create a backup with: ./escmd.py template-backup <name>", style=muted_style))
            self.console.print()
            self.console.print(Panel(
                msg_table,
                title=f"[{title_style}]Template Backups[/{title_style}]",
                border_style=warning_style,
                padding=(1, 2)
            ))
            self.console.print()
            return

        # Build colorized subtitle
        from rich.text import Text as SubText
        total = len(backups)
        subtitle_rich = SubText()
        subtitle_rich.append("Total: ", style="default")
        subtitle_rich.append(str(total), style=primary_style)
        types = {}
        for b in backups:
            t = b.get('template_type', 'unknown')
            types[t] = types.get(t, 0) + 1
        for t, count in sorted(types.items()):
            subtitle_rich.append(f" | {t.title()}: ", style="default")
            subtitle_rich.append(str(count), style=primary_style)

        header_panel = Panel(
            SubText(""),
            title=f"[{title_style}]Template Backups[/{title_style}]",
            subtitle=subtitle_rich,
            border_style=border,
            padding=(0, 2)
        )

        full_theme = tm.get_full_theme_data() if tm else {}
        table_styles = full_theme.get('table_styles', {})
        header_style = table_styles.get('header_style', 'bold white')

        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border,
            box=ss.get_table_box() if ss else None,
            expand=True
        )
        table.add_column("Template Name", style=primary_style)
        table.add_column("Type", style=ss._get_style('semantic', 'secondary', 'magenta') if ss else 'magenta')
        table.add_column("Cluster", style=ss._get_style('semantic', 'info', 'blue') if ss else 'blue')
        table.add_column("Backup Date", style=ss._get_style('semantic', 'success', 'green') if ss else 'green')
        table.add_column("File Size", style=ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow', justify="right")
        table.add_column("File Name", style=muted_style)

        for backup in backups:
            file_size = self._format_file_size(backup.get('file_size', 0))
            backup_date = backup.get('backup_timestamp', 'Unknown')
            if backup_date and backup_date != 'Unknown':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(backup_date.replace('Z', '+00:00'))
                    backup_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            table.add_row(
                backup.get('template_name', 'Unknown'),
                backup.get('template_type', 'Unknown'),
                backup.get('cluster_name', '-'),
                backup_date,
                file_size,
                backup.get('file_name', 'Unknown')
            )

        self.console.print()
        self.console.print(header_panel)
        self.console.print()
        self.console.print(table)
        self.console.print()

    def handle_template_create(self):
        """Handle template creation from JSON file or inline definition."""
        file_path = getattr(self.args, 'file', None)
        template_name = getattr(self.args, 'name', None)
        template_type = getattr(self.args, 'type', 'component')
        inline_definition = getattr(self.args, 'definition', None)
        dry_run = getattr(self.args, 'dry_run', False)

        try:
            if file_path:
                # Create templates from JSON file
                result = self.es_client.template_commands.create_templates_from_file(
                    file_path, dry_run
                )
            elif template_name and inline_definition:
                # Create single template from inline definition
                result = self.es_client.template_commands.create_template_inline(
                    template_name, template_type, inline_definition, dry_run
                )
            else:
                self._show_template_create_help()
                return

            # Display results
            if self.args.format == 'json':
                self.es_client.pretty_print_json(result)
            else:
                self._print_template_creation_result(result, dry_run)

        except Exception as e:
            self.console.print(f"[red]Template creation failed: {str(e)}[/red]")

    def _show_template_create_help(self):
        """Display help screen for template-create command."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = self.console
        ss = self.es_client.style_system
        tm = self.es_client.theme_manager

        primary_style = ss.get_semantic_style("primary")
        success_style = ss.get_semantic_style("success")
        muted_style = ss._get_style('semantic', 'muted', 'dim')
        border_style = ss._get_style('table_styles', 'border_style', 'white')
        header_style = tm.get_theme_styles().get('header_style', 'bold white') if tm else 'bold white'
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        box_style = ss.get_table_box()

        header_panel = Panel(
            Text("Run ./escmd.py template-create --file <path> or --name <n> --definition <json>", style="bold white"),
            title=f"[{title_style}]📝 Create Template[/{title_style}]",
            subtitle=Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]for full options[/dim]"),
            border_style=border_style,
            padding=(1, 2),
            expand=True,
        )

        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border_style,
            box=box_style,
            show_lines=False,
            expand=True,
        )
        table.add_column("Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("--file <path>", "Create template(s) from JSON file", "template-create --file my-template.json"),
            ("--name <n> --definition <json>", "Create single template inline", "template-create --name my-tpl --definition '{...}'"),
            ("--type <type>", "Template type (default: component)", "template-create --file t.json --type composable"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Options ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        options = [
            ("--dry-run", "Preview without creating", "template-create --file t.json --dry-run"),
            ("--format json", "JSON output", "template-create --file t.json --format json"),
        ]
        for i, (opt, desc, ex) in enumerate(options):
            table.add_row(
                Text(opt, style=ss._get_style('semantic', 'secondary', 'magenta')),
                desc,
                Text(f"./escmd.py {ex}", style=muted_style),
                style=ss.get_zebra_style(i) if ss else None,
            )

        console.print()
        console.print(header_panel)
        console.print()
        console.print(table)
        console.print()

    def _print_template_creation_result(self, result, dry_run=False):
        """Print formatted template creation results."""
        mode_text = "DRY RUN - " if dry_run else ""

        if result.get('success', False):
            created_count = result.get('created_count', 0)
            failed_count = result.get('failed_count', 0)

            if created_count > 0:
                self.console.print(f"[green]✓[/green] {mode_text}{created_count} template(s) {'would be ' if dry_run else ''}created successfully")

                # Show details of created templates
                for template_info in result.get('created_templates', []):
                    self.console.print(f"  • {template_info['name']} ({template_info['type']})")

            if failed_count > 0:
                self.console.print(f"[red]✗[/red] {failed_count} template(s) failed to create")

                # Show details of failed templates
                for error_info in result.get('failed_templates', []):
                    self.console.print(f"  • {error_info['name']}: {error_info['error']}")
        else:
            self.console.print(f"[red]✗[/red] {mode_text}Template creation failed: {result.get('error', 'Unknown error')}")

    def _format_file_size(self, size_bytes):
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
