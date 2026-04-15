#!/usr/bin/env python3

from .base_handler import BaseHandler
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm
from rich.markup import escape
import json


class SettingsHandler(BaseHandler):
    """Handler for Elasticsearch cluster settings operations."""

    def handle_settings(self):
        """Handle cluster settings display command."""
        if self.args.format == 'json':
            cluster_settings = self.es_client.get_settings()
            # Use Rich JSON formatting for better display (auto-detects pipe vs terminal)
            self.es_client.pretty_print_json(cluster_settings)
        else:
            self.es_client.print_enhanced_cluster_settings()

    def handle_set(self):
        """Handle cluster setting update command."""
        setting_type = getattr(self.args, 'setting_type', None)
        setting_key = getattr(self.args, 'setting_key', None)
        setting_value = getattr(self.args, 'setting_value', None)

        if not setting_type or not setting_key or setting_value is None:
            self._show_set_help()
            return

        dry_run = getattr(self.args, 'dry_run', False)
        skip_confirm = getattr(self.args, 'yes', False)

        # Convert "null" string to actual None for resetting settings
        if setting_value.lower() == "null":
            setting_value = None

        # Convert dot notation to nested dictionary
        nested_settings = self._dot_notation_to_dict(setting_key, setting_value)

        # Display what will be set
        self._display_setting_preview(setting_type, setting_key, setting_value, nested_settings)

        if dry_run:
            self.console.print(Panel(
                "[yellow]No changes were applied.[/yellow]",
                title="[bold yellow]🔍 Dry Run[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            ))
            return

        # Confirm the operation unless --yes flag is used
        if not skip_confirm:
            action = "reset" if setting_value is None else "set"
            self.console.print()
            if not Confirm.ask(f"  Do you want to {action} this [bold cyan]{setting_type}[/bold cyan] cluster setting?"):
                self.console.print(Panel(
                    "[yellow]No changes were made.[/yellow]",
                    title="[bold yellow]⚙️  Cancelled[/bold yellow]",
                    border_style="yellow",
                    padding=(1, 2),
                ))
                return

        # Apply the setting
        self._apply_cluster_setting(setting_type, nested_settings)

    def _show_set_help(self):
        """Display help screen for set command."""
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
            Text("Run ./escmd.py set <persistent|transient> <key> <value>", style="bold white"),
            title=f"[{title_style}]🔧 Set Cluster Settings[/{title_style}]",
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
            ("set persistent <key> <val>", "Set a persistent setting (survives restart)", "set persistent cluster.routing.allocation.node_concurrent_recoveries 5"),
            ("set transient <key> <val>", "Set a transient setting (resets on restart)", "set transient indices.recovery.max_bytes_per_sec 100mb"),
            ("set persistent <key> null", "Reset a setting to default", "set persistent cluster.routing.allocation.enable null"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Options ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        options = [
            ("--dry-run", "Preview without applying", "set persistent cluster.routing.allocation.enable all --dry-run"),
            ("--yes", "Skip confirmation prompt", "set persistent cluster.routing.allocation.enable all --yes"),
            ("--format json", "JSON output", "set persistent cluster.routing.allocation.enable all --format json"),
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

    def _dot_notation_to_dict(self, key, value):
        """
        Convert dot notation key to nested dictionary structure.

        Args:
            key (str): Dot notation key like 'cluster.routing.allocation.node_concurrent_recoveries'
            value: The value to set

        Returns:
            dict: Nested dictionary structure
        """
        keys = key.split('.')
        result = {}
        current = result

        for i, k in enumerate(keys[:-1]):
            current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        return result

    def _display_setting_preview(self, setting_type, key, value, nested_settings):
        """Display a preview of the setting that will be applied."""
        is_reset = value is None
        action_label = "RESET" if is_reset else "SET"
        action_style = "red" if is_reset else "green"
        value_display = "[dim]null (will remove the setting)[/dim]" if is_reset else f"[cyan]{escape(str(value))}[/cyan]"

        content = (
            f"[bold]Setting Type:[/bold]  [magenta]{escape(setting_type)}[/magenta]\n"
            f"[bold]Setting Key:[/bold]   [yellow]{escape(key)}[/yellow]\n"
            f"[bold]Value:[/bold]         {value_display}\n\n"
            f"[bold]JSON Payload:[/bold]\n"
            f"[dim]{escape(json.dumps({setting_type: nested_settings}, indent=2))}[/dim]"
        )

        self.console.print(Panel(
            content,
            title=f"[bold {action_style}]⚙️  {action_label} Cluster Setting[/bold {action_style}]",
            border_style=action_style,
            padding=(1, 2),
        ))

    def _apply_cluster_setting(self, setting_type, nested_settings):
        """Apply the cluster setting using the Elasticsearch API."""
        try:
            if setting_type == 'persistent':
                result = self.es_client.settings_commands.update_cluster_settings(
                    persistent=nested_settings
                )
            else:  # transient
                result = self.es_client.settings_commands.update_cluster_settings(
                    transient=nested_settings
                )

            if 'error' in result:
                self.console.print(Panel(
                    f"[red]{escape(str(result['error']))}[/red]",
                    title="[bold red]❌ Failed to Update Setting[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                ))
                return

            if self.args.format == 'json':
                self.es_client.pretty_print_json(result)
            else:
                self._display_success_message(setting_type, result)

        except Exception as e:
            self.console.print(Panel(
                f"[red]{escape(str(e))}[/red]",
                title="[bold red]❌ Failed to Update Setting[/bold red]",
                border_style="red",
                padding=(1, 2),
            ))

    def _display_success_message(self, setting_type, result):
        """Display a formatted success message."""
        lines = [f"[green]Successfully updated [bold]{escape(setting_type)}[/bold] cluster setting.[/green]\n"]

        if result.get('acknowledged'):
            lines.append("[bold]Acknowledged:[/bold] [bold green]✓ true[/bold green]")

        for key in ('persistent', 'transient'):
            if result.get(key):
                lines.append(f"\n[bold]{key.title()} Settings:[/bold]")
                lines.append(f"[dim]{escape(json.dumps(result[key], indent=2))}[/dim]")

        self.console.print(Panel(
            "\n".join(lines),
            title="[bold green]✓ Setting Updated[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))
