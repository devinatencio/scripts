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
        template_name = self.args.name
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
        template_name = self.args.name
        template_type = getattr(self.args, 'type', 'auto')
        field_path = getattr(self.args, 'field', None)
        operation = getattr(self.args, 'operation', 'set')
        value = getattr(self.args, 'value', '')
        backup = getattr(self.args, 'backup', True)
        backup_dir = getattr(self.args, 'backup_dir', None)
        dry_run = getattr(self.args, 'dry_run', False)

        if not field_path:
            self.console.print("[red]Error: Field path is required for template modification[/red]")
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

    def handle_template_backup(self):
        """Handle template backup command."""
        template_name = self.args.name
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

    def handle_template_restore(self):
        """Handle template restore command."""
        backup_file = getattr(self.args, 'backup_file', None)

        if not backup_file:
            self.console.print("[red]Error: Backup file path is required[/red]")
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
        from ..template_utils import TemplateModifier
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
        if not backups:
            self.console.print("[yellow]No backups found[/yellow]")
            return

        table = Table(title="Template Backups")
        table.add_column("Template Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Cluster", style="blue")
        table.add_column("Backup Date", style="green")
        table.add_column("File Size", style="yellow")
        table.add_column("File Name", style="white")

        for backup in backups:
            file_size = self._format_file_size(backup.get('file_size', 0))
            backup_date = backup.get('backup_timestamp', 'Unknown')
            if backup_date and backup_date != 'Unknown':
                # Format the timestamp for display
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

        self.console.print(table)

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
                self.console.print("[red]Error: Either --file or both --name and --definition must be provided[/red]")
                return

            # Display results
            if self.args.format == 'json':
                self.es_client.pretty_print_json(result)
            else:
                self._print_template_creation_result(result, dry_run)

        except Exception as e:
            self.console.print(f"[red]Template creation failed: {str(e)}[/red]")

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
