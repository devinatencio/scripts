"""
Cluster command processors extracted from ElasticsearchClient.

This module handles cluster-level operations including:
- Cluster information and statistics
- Cluster health monitoring
- Cluster state management
"""

from typing import Dict, Any, Optional
from .base_command import BaseCommand

# Try to import performance and error handling modules
try:
    from performance import cache_5min, cache_1min, monitor_performance
    from error_handling import handle_es_errors
except ImportError:
    # Fallback for when modules aren't available
    def cache_5min(func):
        return func
    def cache_1min(func):
        return func
    def monitor_performance(func):
        return func
    def handle_es_errors(operation):
        def decorator(func):
            return func
        return decorator


class ClusterCommands(BaseCommand):
    """
    Command processor for cluster-related operations.

    This class extracts cluster management methods from the main ElasticsearchClient,
    providing a focused interface for cluster operations.
    """

    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'cluster'

    @handle_es_errors("get_cluster_info")
    @cache_5min
    @monitor_performance
    def get_cluster_info(self) -> Dict[str, Any]:
        """
        Get cluster information using the Elasticsearch cluster API.

        Returns:
            dict: Cluster information including name, version, etc.
        """
        try:
            return self.es_client.es.info()
        except Exception as e:
            return {"error": f"Failed to get cluster info: {str(e)}"}

    @handle_es_errors("get_cluster_health")
    @cache_1min
    @monitor_performance
    def get_cluster_health(self, include_version: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive cluster health information.

        Args:
            include_version: Whether to include version information

        Returns:
            dict: Cluster health data with optional version info
        """
        try:
            health = self.es_client.es.cluster.health(
                wait_for_status='yellow',
                timeout='10s'
            )

            # Convert response to dict if needed (ES client version compatibility)
            if hasattr(health, 'body'):
                health_data = health.body
            elif hasattr(health, 'get'):
                health_data = dict(health)
            else:
                health_data = health

            if include_version:
                try:
                    cluster_info = self.get_cluster_info()
                    if 'error' not in cluster_info:
                        health_data['cluster_version'] = cluster_info.get('version', {})
                        health_data['cluster_tagline'] = cluster_info.get('tagline', '')
                except Exception:
                    # If we can't get version info, continue without it
                    pass

            # Fetch index count from cluster stats (single aggregated number, no per-index payload)
            try:
                stats = self.es_client.es.cluster.stats()
                if hasattr(stats, 'body'):
                    stats = stats.body
                health_data['number_of_indices'] = stats.get('indices', {}).get('count', None)
            except Exception:
                pass

            return health_data

        except Exception as e:
            return {
                "error": f"Failed to get cluster health: {str(e)}",
                "cluster_name": "unknown",
                "status": "unknown"
            }

    def ping(self) -> bool:
        """
        Test connectivity to the Elasticsearch cluster.

        Returns:
            bool: True if cluster is reachable, False otherwise
        """
        try:
            return self.es_client.es.ping()
        except Exception:
            return False

    def get_cluster_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cluster statistics.

        Returns:
            dict: Cluster statistics including indices, nodes, shards
        """
        try:
            stats = self.es_client.es.cluster.stats()

            # Handle response format differences between ES client versions
            if hasattr(stats, 'body'):
                return stats.body
            elif hasattr(stats, 'get'):
                return dict(stats)
            else:
                return stats

        except Exception as e:
            return {"error": f"Failed to get cluster stats: {str(e)}"}

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

    def get_master_node(self) -> Dict[str, Any]:
        """
        Get information about the current master node.

        Returns:
            dict: Master node information
        """
        try:
            # Get cluster state to find master node
            state = self.es_client.es.cluster.state(metric='master_node')

            # Handle response format
            if hasattr(state, 'body'):
                state_data = state.body
            elif hasattr(state, 'get'):
                state_data = dict(state)
            else:
                state_data = state

            master_node_id = state_data.get('master_node')

            if master_node_id:
                # Get node details
                try:
                    nodes_info = self.es_client.es.nodes.info(node_id=master_node_id)
                    if hasattr(nodes_info, 'body'):
                        nodes_data = nodes_info.body
                    else:
                        nodes_data = nodes_info

                    node_info = nodes_data.get('nodes', {}).get(master_node_id, {})

                    return {
                        'node_id': master_node_id,
                        'name': node_info.get('name', 'unknown'),
                        'host': node_info.get('host', 'unknown'),
                        'ip': node_info.get('ip', 'unknown'),
                        'roles': node_info.get('roles', []),
                        'version': node_info.get('version', 'unknown')
                    }
                except Exception:
                    return {
                        'node_id': master_node_id,
                        'name': 'unknown',
                        'error': 'Could not get node details'
                    }
            else:
                return {'error': 'No master node found'}

        except Exception as e:
            return {'error': f'Failed to get master node: {str(e)}'}

    def wait_for_cluster_health(self, status: str = 'yellow', timeout: str = '30s') -> Dict[str, Any]:
        """
        Wait for cluster to reach a specific health status.

        Args:
            status: Health status to wait for ('green', 'yellow', 'red')
            timeout: Timeout duration

        Returns:
            dict: Final cluster health status
        """
        try:
            health = self.es_client.es.cluster.health(
                wait_for_status=status,
                timeout=timeout
            )

            # Handle response format
            if hasattr(health, 'body'):
                return health.body
            elif hasattr(health, 'get'):
                return dict(health)
            else:
                return health

        except Exception as e:
            return {
                'error': f'Failed to wait for cluster health: {str(e)}',
                'requested_status': status,
                'timeout': timeout
            }


# Backward compatibility functions
def get_cluster_health(es_client, include_version: bool = True) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    cluster_cmd = ClusterCommands(es_client)
    return cluster_cmd.get_cluster_health(include_version)

def get_cluster_info(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    cluster_cmd = ClusterCommands(es_client)
    return cluster_cmd.get_cluster_info()

def ping_cluster(es_client) -> bool:
    """Backward compatibility function for existing code."""
    cluster_cmd = ClusterCommands(es_client)
    return cluster_cmd.ping()
