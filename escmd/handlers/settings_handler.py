#!/usr/bin/env python3

from .base_handler import BaseHandler
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm
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
        setting_type = self.args.setting_type
        setting_key = self.args.setting_key
        setting_value = self.args.setting_value
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
            self.console.print("[yellow]Dry run mode - no changes will be applied[/yellow]")
            return

        # Confirm the operation unless --yes flag is used
        if not skip_confirm:
            action = "reset" if setting_value is None else "set"
            if not Confirm.ask(f"Do you want to {action} this {setting_type} cluster setting?"):
                self.console.print("[yellow]Operation cancelled[/yellow]")
                return

        # Apply the setting
        self._apply_cluster_setting(setting_type, nested_settings)

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
        # Create the preview content
        if value is None:
            action_text = f"[red]RESET[/red] {setting_type} setting"
            value_display = "[dim]null (will remove the setting)[/dim]"
        else:
            action_text = f"[green]SET[/green] {setting_type} setting"
            value_display = f"[cyan]{value}[/cyan]"

        preview_content = Text()
        preview_content.append("Setting Key: ", style="bold")
        preview_content.append(f"{key}\n", style="yellow")
        preview_content.append("Setting Value: ", style="bold")
        preview_content.append(f"{value_display}\n\n", style="")
        preview_content.append("JSON Structure:\n", style="bold")

        # Format the nested structure for display
        json_str = json.dumps({setting_type: nested_settings}, indent=2)
        preview_content.append(json_str, style="dim")

        # Create panel
        panel = Panel(
            preview_content,
            title=action_text,
            border_style="blue" if value is not None else "red",
            padding=(1, 2)
        )

        self.console.print(panel)

    def _apply_cluster_setting(self, setting_type, nested_settings):
        """Apply the cluster setting using the Elasticsearch API."""
        try:
            # Prepare the settings payload
            if setting_type == 'persistent':
                result = self.es_client.settings_commands.update_cluster_settings(
                    persistent=nested_settings
                )
            else:  # transient
                result = self.es_client.settings_commands.update_cluster_settings(
                    transient=nested_settings
                )

            # Check for errors in the response
            if 'error' in result:
                self.console.print(f"[red]Error updating cluster settings: {result['error']}[/red]")
                return

            # Display success message
            if self.args.format == 'json':
                self.es_client.pretty_print_json(result)
            else:
                self._display_success_message(setting_type, result)

        except Exception as e:
            self.console.print(f"[red]Failed to update cluster settings: {str(e)}[/red]")

    def _display_success_message(self, setting_type, result):
        """Display a formatted success message."""
        success_text = Text()
        success_text.append("✓ ", style="green bold")
        success_text.append(f"Successfully updated {setting_type} cluster setting", style="green")

        # Show the response in a nice format
        response_content = Text()
        response_content.append("Elasticsearch Response:\n", style="bold")

        if 'acknowledged' in result and result['acknowledged']:
            response_content.append("✓ Acknowledged: ", style="green")
            response_content.append("true\n", style="bold green")

        # Show the updated settings
        for key in ['persistent', 'transient']:
            if key in result and result[key]:
                response_content.append(f"{key.title()} Settings:\n", style="bold")
                settings_str = json.dumps(result[key], indent=2)
                response_content.append(settings_str, style="dim")
                response_content.append("\n")

        panel = Panel(
            response_content,
            title=success_text,
            border_style="green",
            padding=(1, 2)
        )

        self.console.print(panel)
