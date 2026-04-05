"""
Utility command processors extracted from ElasticsearchClient.

This module handles miscellaneous utility operations including:
- Data stream operations
- Lifecycle management utilities
- Storage operations
- General utility functions
"""

from typing import Dict, Any, Optional, List
from .base_command import BaseCommand


class UtilityCommands(BaseCommand):
    """
    Command processor for utility and miscellaneous operations.

    This class extracts utility methods from the main ElasticsearchClient,
    providing a focused interface for general-purpose operations.
    """

    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'utility'

    def get_datastreams(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get data stream information.

        Args:
            name: Specific data stream name (optional)

        Returns:
            dict: Data stream information
        """
        try:
            if name:
                datastreams = self.es_client.es.indices.get_data_stream(name=name)
            else:
                datastreams = self.es_client.es.indices.get_data_stream()

            # Handle response format differences
            if hasattr(datastreams, 'body'):
                return datastreams.body
            elif hasattr(datastreams, 'get'):
                return dict(datastreams)
            else:
                return datastreams

        except Exception as e:
            return {
                "error": f"Failed to get data streams: {str(e)}",
                "name": name
            }

    def create_datastream(self, name: str) -> Dict[str, Any]:
        """
        Create a data stream.

        Args:
            name: Name for the data stream

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.indices.create_data_stream(name=name)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to create data stream: {str(e)}",
                "name": name
            }

    def delete_datastream(self, name: str) -> Dict[str, Any]:
        """
        Delete a data stream.

        Args:
            name: Name of the data stream to delete

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.indices.delete_data_stream(name=name)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to delete data stream: {str(e)}",
                "name": name
            }

    def rollover_datastream(self, name: str, max_age: Optional[str] = None,
                           max_size: Optional[str] = None, max_docs: Optional[int] = None) -> Dict[str, Any]:
        """
        Rollover a data stream.

        Args:
            name: Name of the data stream
            max_age: Maximum age for rollover
            max_size: Maximum size for rollover
            max_docs: Maximum document count for rollover

        Returns:
            dict: Operation result
        """
        try:
            conditions = {}
            if max_age:
                conditions['max_age'] = max_age
            if max_size:
                conditions['max_size'] = max_size
            if max_docs:
                conditions['max_docs'] = max_docs

            params = {}
            if conditions:
                params['body'] = {'conditions': conditions}

            result = self.es_client.es.indices.rollover(alias=name, **params)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to rollover data stream: {str(e)}",
                "name": name
            }

    def get_lifecycle_status(self) -> Dict[str, Any]:
        """
        Get ILM operation status.

        Returns:
            dict: ILM operation status
        """
        try:
            status = self.es_client.es.ilm.get_status()

            # Handle response format differences
            if hasattr(status, 'body'):
                return status.body
            elif hasattr(status, 'get'):
                return dict(status)
            else:
                return status

        except Exception as e:
            return {"error": f"Failed to get lifecycle status: {str(e)}"}

    def start_lifecycle(self) -> Dict[str, Any]:
        """
        Start ILM operations.

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.ilm.start()

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {"error": f"Failed to start lifecycle: {str(e)}"}

    def stop_lifecycle(self) -> Dict[str, Any]:
        """
        Stop ILM operations.

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.ilm.stop()

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {"error": f"Failed to stop lifecycle: {str(e)}"}

    def explain_lifecycle(self, index_name: str) -> Dict[str, Any]:
        """
        Explain lifecycle status for an index.

        Args:
            index_name: Name of the index

        Returns:
            dict: Lifecycle explanation
        """
        try:
            explanation = self.es_client.es.ilm.explain_lifecycle(index=index_name)

            # Handle response format differences
            if hasattr(explanation, 'body'):
                return explanation.body
            elif hasattr(explanation, 'get'):
                return dict(explanation)
            else:
                return explanation

        except Exception as e:
            return {
                "error": f"Failed to explain lifecycle: {str(e)}",
                "index": index_name
            }

    def move_to_step(self, index_name: str, current_step: Dict[str, Any],
                    next_step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Move an index to a specific ILM step.

        Args:
            index_name: Name of the index
            current_step: Current step information
            next_step: Next step information

        Returns:
            dict: Operation result
        """
        try:
            body = {
                'current_step': current_step,
                'next_step': next_step
            }

            result = self.es_client.es.ilm.move_to_step(
                index=index_name,
                body=body
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
                "error": f"Failed to move to step: {str(e)}",
                "index": index_name
            }

    def retry_lifecycle(self, index_name: str) -> Dict[str, Any]:
        """
        Retry lifecycle step for an index.

        Args:
            index_name: Name of the index

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.ilm.retry(index=index_name)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to retry lifecycle: {str(e)}",
                "index": index_name
            }

    def remove_lifecycle_policy(self, index_name: str) -> Dict[str, Any]:
        """
        Remove lifecycle policy from an index.

        Args:
            index_name: Name of the index

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.ilm.remove_policy(index=index_name)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to remove lifecycle policy: {str(e)}",
                "index": index_name
            }

    def refresh_index(self, index_name: str) -> Dict[str, Any]:
        """
        Refresh an index to make recent changes searchable.

        Args:
            index_name: Name of the index to refresh

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.indices.refresh(index=index_name)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to refresh index: {str(e)}",
                "index": index_name
            }

    def get_flush_timeout(self) -> int:
        """
        HTTP request timeout for cluster-wide flush operations.

        Flush can run much longer than typical API calls on large clusters.
        Optional ``flush_timeout`` in escmd.yml ``settings`` overrides the
        computed default (max(5 * read_timeout, 300) seconds).
        """
        cm = getattr(self.es_client, "configuration_manager", None)
        if cm and getattr(cm, "main_config", None):
            settings = (cm.main_config or {}).get("settings", {})
            if settings.get("flush_timeout") is not None:
                return int(settings["flush_timeout"])
        base = int(getattr(self.es_client, "timeout", 60))
        return max(base * 5, 300)

    def flush_index(self, index_name: str, wait_if_ongoing: bool = True) -> Dict[str, Any]:
        """
        Flush an index to commit changes to disk.

        Args:
            index_name: Name of the index to flush
            wait_if_ongoing: Whether to wait if flush is ongoing

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.indices.flush(
                index=index_name,
                wait_if_ongoing=wait_if_ongoing
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
                "error": f"Failed to flush index: {str(e)}",
                "index": index_name
            }

    def flush_synced_elasticsearch(self, host=None, port=None, use_ssl=False, authentication=False, username=None, password=None) -> Dict[str, Any]:
        """
        Perform a synced flush across the entire Elasticsearch cluster.

        This method flushes all indices in the cluster to commit changes to disk.
        Synced flush is deprecated in newer Elasticsearch versions but still
        supported for compatibility.

        Args:
            host: Elasticsearch host (optional, uses existing connection if not provided)
            port: Elasticsearch port (optional, uses existing connection if not provided)
            use_ssl: Whether to use SSL (optional, uses existing connection if not provided)
            authentication: Whether to use authentication (optional)
            username: Username for authentication (optional)
            password: Password for authentication (optional)

        Returns:
            dict: Operation result including flush statistics
        """
        try:
            # Use the existing ES client connection - parameters are for compatibility
            # with the original method signature but we use the already configured client
            flush_timeout = self.get_flush_timeout()
            result = self.es_client.es.indices.flush(request_timeout=flush_timeout)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to perform synced flush: {str(e)}"
            }

    def clear_cache(self, index_name: Optional[str] = None, cache_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Clear various caches.

        Args:
            index_name: Specific index name (optional)
            cache_types: Types of caches to clear (optional)

        Returns:
            dict: Operation result
        """
        try:
            params = {}
            if index_name:
                params['index'] = index_name
            if cache_types:
                for cache_type in cache_types:
                    params[cache_type] = True

            result = self.es_client.es.indices.clear_cache(**params)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to clear cache: {str(e)}",
                "index": index_name
            }

    def analyze_text(self, text: str, analyzer: Optional[str] = None,
                    index: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze text using specified analyzer.

        Args:
            text: Text to analyze
            analyzer: Analyzer to use
            index: Index to use for analysis context

        Returns:
            dict: Analysis result
        """
        try:
            body = {'text': text}
            if analyzer:
                body['analyzer'] = analyzer

            params = {'body': body}
            if index:
                params['index'] = index

            result = self.es_client.es.indices.analyze(**params)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to analyze text: {str(e)}",
                "text": text
            }

    def show_cluster_groups(self, configuration_manager, format_type: str = 'table') -> Dict[str, Any]:
        """
        Display configured cluster groups with descriptions in a pretty table format.

        Args:
            configuration_manager: Configuration manager instance containing cluster groups
            format_type: Output format ('table' or 'json')

        Returns:
            dict: Cluster groups information and display result
        """
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from rich.text import Text
            from esclient import get_theme_styles

            console = Console()

            # Get enhanced cluster groups with descriptions
            cluster_groups = configuration_manager.get_cluster_groups_with_descriptions()

            if not cluster_groups:
                if format_type == 'json':
                    return {
                        "cluster_groups": {},
                        "total_groups": 0,
                        "message": "No cluster groups configured"
                    }
                else:
                    console.print("[yellow]ℹ️  No cluster groups configured[/yellow]")
                    console.print("[dim]Add 'cluster_groups' section to escmd.yml to create logical cluster groupings[/dim]")
                    return {
                        "cluster_groups": {},
                        "total_groups": 0,
                        "displayed": True
                    }

            if format_type == 'json':
                # Return JSON format with descriptions
                total_clusters = sum(group['cluster_count'] for group in cluster_groups.values())
                return {
                    "cluster_groups": {name: group['clusters'] for name, group in cluster_groups.items()},
                    "total_groups": len(cluster_groups),
                    "total_clusters_in_groups": total_clusters,
                    "group_details": [
                        {
                            "name": group_name,
                            "clusters": group_data['clusters'],
                            "description": group_data['description'],
                            "cluster_count": group_data['cluster_count']
                        }
                        for group_name, group_data in cluster_groups.items()
                    ]
                }

            # Get theme styles
            styles = get_theme_styles(configuration_manager)
            panel_styles = styles.get('panel_styles', {})

            # Create the main table
            groups_table = Table(show_header=True, header_style="bold white", box=None, expand=True)
            groups_table.add_column("📝 Description", style=panel_styles.get('description', 'dim white'), min_width=25, max_width=40)
            groups_table.add_column("🔖  Group Name", style=panel_styles.get('title', 'bold green'), no_wrap=True, min_width=12, max_width=18)
            groups_table.add_column("📊 Count", style=panel_styles.get('success', 'white'), justify="center", min_width=6, max_width=8)
            groups_table.add_column("📋 Clusters", style=panel_styles.get('info', 'cyan'), min_width=30)

            # Sort groups alphabetically
            sorted_groups = sorted(cluster_groups.items())
            total_clusters_in_groups = 0

            for group_name, group_data in sorted_groups:
                cluster_list = sorted(group_data['clusters'])
                cluster_count = group_data['cluster_count']
                description = group_data['description']
                total_clusters_in_groups += cluster_count

                # Handle long cluster lists - show first few clusters and indicate if more
                if len(cluster_list) > 8:
                    displayed_clusters = cluster_list[:8]
                    clusters_text = ", ".join(displayed_clusters) + f", ... (+{len(cluster_list) - 8} more)"
                else:
                    clusters_text = ", ".join(cluster_list)

                groups_table.add_row(
                    description,
                    group_name,
                    str(cluster_count),
                    clusters_text
                )

            # Create summary information
            summary_text = f"[bold white]🏗️  Cluster Groups Summary[/bold white] • {len(cluster_groups)} groups • {total_clusters_in_groups} total cluster assignments"

            # Wrap in a panel
            panel = Panel(
                groups_table,
                title=summary_text,
                title_align="left",
                border_style=styles.get('border_style', 'cyan'),
                padding=(1, 2)
            )

            console.print(panel)

            # Add usage information
            usage_info = Table.grid(padding=(0, 2))
            usage_info.add_column(style=panel_styles.get('description', 'dim white'))
            usage_info.add_row("💡 Use cluster groups with commands like: [bold]health --group <group_name>[/bold]")
            usage_info.add_row("📝 Configure groups in [bold]escmd.yml[/bold] under the 'cluster_groups' section")

            usage_panel = Panel(
                usage_info,
                title="[bold white]💡 Usage Tips[/bold white]",
                border_style=panel_styles.get('border', 'dim white'),
                padding=(0, 2)
            )

            console.print(usage_panel)

            return {
                "cluster_groups": {name: group['clusters'] for name, group in cluster_groups.items()},
                "total_groups": len(cluster_groups),
                "total_clusters_in_groups": total_clusters_in_groups,
                "displayed": True
            }

        except ImportError as e:
            # Fallback if rich is not available
            return {
                "error": f"Display libraries not available: {str(e)}",
                "cluster_groups": configuration_manager.get_cluster_groups() if configuration_manager else {}
            }
        except Exception as e:
            return {
                "error": f"Failed to display cluster groups: {str(e)}",
                "cluster_groups": {}
            }


# Backward compatibility functions
def get_datastreams(es_client, name: Optional[str] = None) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    utility_cmd = UtilityCommands(es_client)
    return utility_cmd.get_datastreams(name)

def get_lifecycle_status(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    utility_cmd = UtilityCommands(es_client)
    return utility_cmd.get_lifecycle_status()

def refresh_index(es_client, index_name: str) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    utility_cmd = UtilityCommands(es_client)
    return utility_cmd.refresh_index(index_name)

def clear_cache(es_client, index_name: Optional[str] = None,
               cache_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    utility_cmd = UtilityCommands(es_client)
    return utility_cmd.clear_cache(index_name, cache_types)

def analyze_text(es_client, text: str, analyzer: Optional[str] = None,
                index: Optional[str] = None) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    utility_cmd = UtilityCommands(es_client)
    return utility_cmd.analyze_text(text, analyzer, index)
