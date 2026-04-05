"""
Settings command processors extracted from ElasticsearchClient.

This module handles settings-related operations including:
- Cluster settings management
- Index settings operations
- Template management
- Configuration updates
"""

from typing import Dict, Any, Optional, List
from .base_command import BaseCommand


class SettingsCommands(BaseCommand):
    """
    Command processor for settings-related operations.

    This class extracts settings management methods from the main ElasticsearchClient,
    providing a focused interface for configuration operations.
    """

    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'settings'

    def get_cluster_settings(self, include_defaults: bool = False) -> Dict[str, Any]:
        """
        Get cluster settings.

        Args:
            include_defaults: Whether to include default settings

        Returns:
            dict: Cluster settings
        """
        try:
            settings = self.es_client.es.cluster.get_settings(
                include_defaults=include_defaults
            )

            # Handle response format differences
            if hasattr(settings, 'body'):
                return settings.body
            elif hasattr(settings, 'get'):
                return dict(settings)
            else:
                return settings

        except Exception as e:
            return {"error": f"Failed to get cluster settings: {str(e)}"}

    def print_enhanced_cluster_settings(self):
        """
        Print enhanced cluster settings display with dot notation table format.

        This method provides a formatted table display of cluster settings
        in dot notation format for better readability.
        """
        try:
            settings = self.get_cluster_settings()

            from rich.table import Table
            from rich.panel import Panel
            from rich.console import Console
            from rich.text import Text

            console = Console()

            # Check if settings contain data
            if not settings or ('persistent' not in settings and 'transient' not in settings):
                # Show default message when no custom settings are configured
                no_settings_text = Text()
                no_settings_text.append("No custom cluster settings are currently configured.\n\n", style="dim italic")
                no_settings_text.append("All cluster settings are using their default values.\n", style="dim")
                no_settings_text.append("Use ", style="dim")
                no_settings_text.append("set transient|persistent <setting> <value>", style="bold cyan")
                no_settings_text.append(" to configure cluster settings.", style="dim")

                no_settings_panel = Panel(
                    no_settings_text,
                    title="🔧 Cluster Settings",
                    border_style="yellow",
                    padding=(1, 2)
                )
                console.print(no_settings_panel)
                return

            # Build content for the main configuration panel
            panel_content = Text()
            panel_content.append("🔧 ", style="bold cyan")
            panel_content.append("Cluster Settings Overview", style="bold white")
            panel_content.append("\n\nDisplaying custom cluster settings in dot notation format.\n\n", style="dim")

            # Create tables for persistent and transient settings
            has_settings = False

            for settings_type in ['persistent', 'transient']:
                if settings_type in settings and settings[settings_type]:
                    # Flatten the nested settings to dot notation
                    flat_settings = self._flatten_settings_to_dot_notation(settings[settings_type])

                    if flat_settings:
                        has_settings = True

                        # Add section header
                        title_style = "green" if settings_type == "persistent" else "blue"
                        icon = "📌" if settings_type == "persistent" else "⚡"

                        panel_content.append(f"{icon} ", style=f"bold {title_style}")
                        panel_content.append(f"{settings_type.capitalize()} Settings", style=f"bold {title_style}")
                        panel_content.append("\n")

                        # Create table for this settings type
                        table = Table(show_header=True, header_style="bold cyan", expand=True, box=None)
                        table.add_column("Setting", style="yellow", no_wrap=False)
                        table.add_column("Value", style="white", no_wrap=False)

                        # Add rows to table
                        for setting_key, setting_value in sorted(flat_settings.items()):
                            # Format the value for display
                            if setting_value is None:
                                display_value = "[dim italic]null[/dim italic]"
                            elif isinstance(setting_value, bool):
                                display_value = f"[green]{str(setting_value).lower()}[/green]"
                            elif isinstance(setting_value, (int, float)):
                                display_value = f"[cyan]{setting_value}[/cyan]"
                            else:
                                display_value = str(setting_value)

                            table.add_row(
                                setting_key,
                                display_value
                            )

                        # Add the table to panel content (we'll need to render it separately)
                        console.print(table)
                        panel_content.append("\n\n")

            # Only show the panel if we have settings
            if has_settings:
                # Create the main configuration panel with embedded content
                main_panel = Panel(
                    panel_content,
                    title="[bold cyan]🔧 Configuration Status[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2)
                )

                # We need to restructure this to properly embed tables
                # Let's use a different approach with Group to combine elements
                from rich.console import Group

                # Create header
                header = Text()
                header.append("Displaying custom cluster settings in dot notation format.", style="dim")

                # Create all table elements
                elements = [header]

                for settings_type in ['persistent', 'transient']:
                    if settings_type in settings and settings[settings_type]:
                        flat_settings = self._flatten_settings_to_dot_notation(settings[settings_type])

                        if flat_settings:
                            # Add spacing
                            elements.append(Text())

                            # Add section title
                            title_style = "green" if settings_type == "persistent" else "blue"
                            icon = "📌" if settings_type == "persistent" else "⚡"
                            section_title = Text()
                            section_title.append(f"{icon} ", style=f"bold {title_style}")
                            section_title.append(f"{settings_type.capitalize()} Settings", style=f"bold {title_style}")
                            elements.append(section_title)

                            # Create and add table
                            table = Table(show_header=True, header_style="bold cyan", expand=True)
                            table.add_column("Setting", style="yellow", no_wrap=False)
                            table.add_column("Value", style="white", no_wrap=False)

                            for setting_key, setting_value in sorted(flat_settings.items()):
                                if setting_value is None:
                                    display_value = "[dim italic]null[/dim italic]"
                                elif isinstance(setting_value, bool):
                                    display_value = f"[green]{str(setting_value).lower()}[/green]"
                                elif isinstance(setting_value, (int, float)):
                                    display_value = f"[cyan]{setting_value}[/cyan]"
                                else:
                                    display_value = str(setting_value)

                                table.add_row(setting_key, display_value)

                            elements.append(table)

                # Create the main panel with all elements grouped
                content_group = Group(*elements)
                main_panel = Panel(
                    content_group,
                    title="[bold cyan]🔧 Configuration Status[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2)
                )
                console.print(main_panel)
                console.print()

                # Add footer with helpful information
                footer_text = Text()
                footer_text.append("💡 ", style="bold yellow")
                footer_text.append("Tips:", style="bold yellow")
                footer_text.append("\n• Persistent settings survive cluster restarts", style="dim")
                footer_text.append("\n• Transient settings are reset on cluster restart", style="dim")
                footer_text.append("\n• Use ", style="dim")
                footer_text.append("cluster-settings --format json", style="bold cyan")
                footer_text.append(" for full JSON output", style="dim")

                footer_panel = Panel(
                    footer_text,
                    border_style="dim",
                    padding=(1, 2)
                )
                console.print(footer_panel)

        except Exception as e:
            console = Console()
            error_text = Text()
            error_text.append("❌ Error displaying cluster settings:\n", style="bold red")
            error_text.append(str(e), style="red")

            error_panel = Panel(
                error_text,
                title="[bold red]Error[/bold red]",
                border_style="red",
                padding=(1, 2)
            )
            console.print(error_panel)

    def _flatten_settings_to_dot_notation(self, settings_dict, prefix=""):
        """
        Flatten nested settings dictionary to dot notation.

        Args:
            settings_dict: Nested dictionary of settings
            prefix: Current prefix for recursion

        Returns:
            dict: Flattened settings with dot notation keys
        """
        flattened = {}

        for key, value in settings_dict.items():
            new_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                flattened.update(self._flatten_settings_to_dot_notation(value, new_key))
            else:
                # Add leaf value
                flattened[new_key] = value

        return flattened


    def update_cluster_settings(self, persistent: Optional[Dict[str, Any]] = None,
                               transient: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update cluster settings.

        Args:
            persistent: Persistent settings to update
            transient: Transient settings to update

        Returns:
            dict: Operation result
        """
        try:
            body = {}
            if persistent:
                body['persistent'] = persistent
            if transient:
                body['transient'] = transient

            if not body:
                return {"error": "No settings provided to update"}

            result = self.es_client.es.cluster.put_settings(body=body)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to update cluster settings: {str(e)}",
                "persistent": persistent,
                "transient": transient
            }

    def get_index_settings(self, index_name: str) -> Dict[str, Any]:
        """
        Get settings for a specific index.

        Args:
            index_name: Name of the index

        Returns:
            dict: Index settings
        """
        try:
            settings = self.es_client.es.indices.get_settings(index=index_name)

            # Handle response format differences
            if hasattr(settings, 'body'):
                return settings.body
            elif hasattr(settings, 'get'):
                return dict(settings)
            else:
                return settings

        except Exception as e:
            return {
                "error": f"Failed to get settings for index '{index_name}': {str(e)}",
                "index": index_name
            }

    def update_index_settings(self, index_name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update settings for a specific index.

        Args:
            index_name: Name of the index
            settings: Settings to update

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.indices.put_settings(
                index=index_name,
                body=settings
            )

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to update settings for index '{index_name}': {str(e)}",
                "index": index_name,
                "settings": settings
            }

    def get_all_index_settings(self) -> Dict[str, Any]:
        """
        Get settings for all indices (delegates to IndicesCommands).

        Returns:
            dict: All index settings
        """
        return self.es_client.indices_commands.get_all_index_settings()

    def get_templates(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get index templates.

        Args:
            name: Specific template name (optional)

        Returns:
            dict: Template information
        """
        try:
            if name:
                templates = self.es_client.es.indices.get_template(name=name)
            else:
                templates = self.es_client.es.indices.get_template()

            # Handle response format differences
            if hasattr(templates, 'body'):
                return templates.body
            elif hasattr(templates, 'get'):
                return dict(templates)
            else:
                return templates

        except Exception as e:
            return {
                "error": f"Failed to get templates: {str(e)}",
                "template": name
            }

    def create_template(self, template_name: str, template_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an index template.

        Args:
            template_name: Name for the template
            template_body: Template configuration

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.indices.put_template(
                name=template_name,
                body=template_body
            )

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to create template: {str(e)}",
                "template": template_name
            }

    def delete_template(self, template_name: str) -> Dict[str, Any]:
        """
        Delete an index template.

        Args:
            template_name: Name of the template to delete

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.indices.delete_template(name=template_name)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to delete template: {str(e)}",
                "template": template_name
            }

    def get_ilm_policies(self) -> Dict[str, Any]:
        """
        Get Index Lifecycle Management policies.

        Returns:
            dict: ILM policies
        """
        try:
            policies = self.es_client.es.ilm.get_lifecycle()

            # Handle response format differences
            if hasattr(policies, 'body'):
                return policies.body
            elif hasattr(policies, 'get'):
                return dict(policies)
            else:
                return policies

        except Exception as e:
            return {"error": f"Failed to get ILM policies: {str(e)}"}

    def get_ilm_policy(self, policy_name: str) -> Dict[str, Any]:
        """
        Get a specific ILM policy.

        Args:
            policy_name: Name of the policy

        Returns:
            dict: ILM policy details
        """
        try:
            policy = self.es_client.es.ilm.get_lifecycle(policy=policy_name)

            # Handle response format differences
            if hasattr(policy, 'body'):
                return policy.body
            elif hasattr(policy, 'get'):
                return dict(policy)
            else:
                return policy

        except Exception as e:
            return {
                "error": f"Failed to get ILM policy: {str(e)}",
                "policy": policy_name
            }

    def create_ilm_policy(self, policy_name: str, policy_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an ILM policy.

        Args:
            policy_name: Name for the policy
            policy_body: Policy configuration

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.ilm.put_lifecycle(
                policy=policy_name,
                body=policy_body
            )

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to create ILM policy: {str(e)}",
                "policy": policy_name
            }

    def delete_ilm_policy(self, policy_name: str) -> Dict[str, Any]:
        """
        Delete an ILM policy.

        Args:
            policy_name: Name of the policy to delete

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.ilm.delete_lifecycle(policy=policy_name)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to delete ILM policy: {str(e)}",
                "policy": policy_name
            }

    def get_index_ilms(self, short: bool = False) -> Dict[str, Any]:
        """
        Get ILM information for indices.

        Args:
            short: Whether to return abbreviated information

        Returns:
            dict: Index ILM information
        """
        try:
            if short:
                # Get basic ILM explain for all indices
                ilm_data = self.es_client.es.ilm.explain_lifecycle(index='*')
            else:
                # Get detailed ILM information
                ilm_data = self.es_client.es.ilm.explain_lifecycle(
                    index='*',
                    only_managed=False,
                    only_errors=False
                )

            # Handle response format differences
            if hasattr(ilm_data, 'body'):
                return ilm_data.body
            elif hasattr(ilm_data, 'get'):
                return dict(ilm_data)
            else:
                return ilm_data

        except Exception as e:
            return {"error": f"Failed to get index ILM information: {str(e)}"}


# Backward compatibility functions
def get_cluster_settings(es_client, include_defaults: bool = False) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    settings_cmd = SettingsCommands(es_client)
    return settings_cmd.get_cluster_settings(include_defaults)

def update_cluster_settings(es_client, persistent: Optional[Dict[str, Any]] = None,
                           transient: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    settings_cmd = SettingsCommands(es_client)
    return settings_cmd.update_cluster_settings(persistent, transient)

def get_templates(es_client, name: Optional[str] = None) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    settings_cmd = SettingsCommands(es_client)
    return settings_cmd.get_templates(name)

def get_ilm_policies(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    settings_cmd = SettingsCommands(es_client)
    return settings_cmd.get_ilm_policies()

def get_index_ilms(es_client, short: bool = False) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    settings_cmd = SettingsCommands(es_client)
    return settings_cmd.get_index_ilms(short)
