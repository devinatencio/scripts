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
        """
        try:
            settings = self.get_cluster_settings()

            from rich.table import Table
            from rich.panel import Panel
            from rich.console import Console, Group
            from rich.text import Text

            console = Console()
            ss = self.es_client.style_system
            tm = self.es_client.theme_manager
            ts = ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'
            border = ss._get_style('table_styles', 'border_style', 'cyan') if ss else 'cyan'
            _title = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'

            persistent = settings.get('persistent') or {}
            transient = settings.get('transient') or {}

            # Count settings
            flat_persistent = self._flatten_settings_to_dot_notation(persistent) if persistent else {}
            flat_transient = self._flatten_settings_to_dot_notation(transient) if transient else {}
            total_settings = len(flat_persistent) + len(flat_transient)

            # --- Title panel ---
            subtitle_rich = Text()
            subtitle_rich.append("Persistent: ", style="default")
            subtitle_rich.append(str(len(flat_persistent)), style=ss._get_style('semantic', 'success', 'green') if ss else "green")
            subtitle_rich.append(" | Transient: ", style="default")
            subtitle_rich.append(str(len(flat_transient)), style=ss._get_style('semantic', 'info', 'blue') if ss else "blue")

            if total_settings == 0:
                status_text = "✅ All Settings at Default Values"
                body_style = "bold green"
            else:
                status_text = f"🔧 {total_settings} Custom Setting{'s' if total_settings != 1 else ''} Configured"
                body_style = "bold white"

            title_panel = Panel(
                Text(status_text, style=body_style, justify="center"),
                title=f"[{ts}]🔧 Cluster Settings[/{ts}]",
                subtitle=subtitle_rich,
                border_style=border,
                padding=(1, 2)
            )

            print()
            console.print(title_panel)
            print()

            if total_settings == 0:
                return

            # --- Settings tables ---
            full_theme = tm.get_full_theme_data() if tm else {}
            table_styles = full_theme.get('table_styles', {})
            header_style = table_styles.get('header_style', 'bold white')
            tbl_border = table_styles.get('border_style', 'bright_magenta')
            box_style = ss.get_table_box() if ss else None

            for settings_type, flat_settings, icon, type_style in [
                ('persistent', flat_persistent, '📌', 'green'),
                ('transient', flat_transient, '⚡', 'blue'),
            ]:
                if not flat_settings:
                    continue

                table = Table(
                    show_header=True,
                    header_style=header_style,
                    border_style=tbl_border,
                    box=box_style,
                    expand=True,
                )
                table.add_column("Setting", style=ss.get_semantic_style("primary") if ss else "bold", no_wrap=False)
                table.add_column("Value", style="white", no_wrap=False)

                for i, (key, value) in enumerate(sorted(flat_settings.items())):
                    if value is None:
                        display_value = Text("null", style="dim italic")
                    elif isinstance(value, bool):
                        display_value = Text(str(value).lower(), style="green")
                    elif isinstance(value, (int, float)):
                        display_value = Text(str(value), style="cyan")
                    else:
                        display_value = Text(str(value))

                    table.add_row(key, display_value, style=ss.get_zebra_style(i) if ss else None)

                settings_panel = Panel(
                    table,
                    title=f"[{_title}]{icon} {settings_type.capitalize()} Settings[/{_title}]",
                    border_style=type_style,
                    padding=(1, 2)
                )
                console.print(settings_panel)
                print()

        except Exception as e:
            from rich.console import Console
            from rich.panel import Panel
            from rich.text import Text
            console = Console()
            console.print(Panel(
                Text(f"❌ Error displaying cluster settings: {str(e)}", style="bold red", justify="center"),
                title="[bold red]Error[/bold red]",
                border_style="red",
                padding=(1, 2)
            ))

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
