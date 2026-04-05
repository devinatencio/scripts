"""
Health and monitoring command processors extracted from ElasticsearchClient.

This module handles health and monitoring operations including:
- Cluster health checks
- Node monitoring
- Shard health analysis
- Performance monitoring
- Status reporting
"""

import time
from typing import Dict, Any, Optional, List
from .base_command import BaseCommand

# Try to import performance modules
try:
    from performance import cache_5min, cache_1min, monitor_performance
except ImportError:
    # Fallback for when modules aren't available
    def cache_5min(func):
        return func
    def cache_1min(func):
        return func
    def monitor_performance(func):
        return func


class HealthCommands(BaseCommand):
    """
    Command processor for health and monitoring operations.

    This class extracts health monitoring methods from the main ElasticsearchClient,
    providing a focused interface for cluster monitoring operations.
    """

    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'health'

    @cache_1min
    @monitor_performance
    def check_cluster_health(self, level: str = 'cluster', wait_for_status: Optional[str] = None) -> Dict[str, Any]:
        """
        Check cluster health status.

        Args:
            level: Level of detail ('cluster', 'indices', 'shards')
            wait_for_status: Wait for specific status ('green', 'yellow', 'red')

        Returns:
            dict: Cluster health information
        """
        try:
            params = {'level': level}
            if wait_for_status:
                params['wait_for_status'] = wait_for_status
                params['timeout'] = '10s'  # Reasonable timeout

            health = self.es_client.es.cluster.health(**params)

            # Handle response format differences
            if hasattr(health, 'body'):
                return health.body
            elif hasattr(health, 'get'):
                return dict(health)
            else:
                return health

        except Exception as e:
            return {
                "error": f"Failed to get cluster health: {str(e)}",
                "level": level
            }

    @cache_5min
    @monitor_performance
    def get_node_stats(self, node_id: Optional[str] = None, metric: Optional[str] = None) -> Dict[str, Any]:
        """
        Get node statistics.

        Args:
            node_id: Specific node ID (optional)
            metric: Specific metric to retrieve (optional)

        Returns:
            dict: Node statistics
        """
        try:
            params = {}
            if node_id:
                params['node_id'] = node_id
            if metric:
                params['metric'] = metric

            stats = self.es_client.es.nodes.stats(**params)

            # Handle response format differences
            if hasattr(stats, 'body'):
                return stats.body
            elif hasattr(stats, 'get'):
                return dict(stats)
            else:
                return stats

        except Exception as e:
            return {
                "error": f"Failed to get node stats: {str(e)}",
                "node_id": node_id,
                "metric": metric
            }

    @cache_5min
    @monitor_performance
    def get_cluster_stats(self) -> Dict[str, Any]:
        """
        Get cluster statistics.

        Returns:
            dict: Cluster statistics
        """
        try:
            stats = self.es_client.es.cluster.stats()

            # Handle response format differences
            if hasattr(stats, 'body'):
                return stats.body
            elif hasattr(stats, 'get'):
                return dict(stats)
            else:
                return stats

        except Exception as e:
            return {"error": f"Failed to get cluster stats: {str(e)}"}

    def get_index_stats(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get index statistics.

        Args:
            index_name: Specific index name (optional)

        Returns:
            dict: Index statistics
        """
        try:
            if index_name:
                stats = self.es_client.es.indices.stats(index=index_name)
            else:
                stats = self.es_client.es.indices.stats()

            # Handle response format differences
            if hasattr(stats, 'body'):
                return stats.body
            elif hasattr(stats, 'get'):
                return dict(stats)
            else:
                return stats

        except Exception as e:
            return {
                "error": f"Failed to get index stats: {str(e)}",
                "index": index_name
            }

    def get_shard_recovery(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get shard recovery information.

        Args:
            index_name: Specific index name (optional)

        Returns:
            dict: Shard recovery information
        """
        try:
            if index_name:
                recovery = self.es_client.es.indices.recovery(index=index_name)
            else:
                recovery = self.es_client.es.indices.recovery()

            # Handle response format differences
            if hasattr(recovery, 'body'):
                return recovery.body
            elif hasattr(recovery, 'get'):
                return dict(recovery)
            else:
                return recovery

        except Exception as e:
            return {
                "error": f"Failed to get shard recovery: {str(e)}",
                "index": index_name
            }

    def print_enhanced_recovery_status(self, recovery_status: Dict[str, Any]) -> None:
        """
        Display recovery status in enhanced format.

        Args:
            recovery_status: Recovery status data from get_shard_recovery()
        """
        from display.recovery_renderer import RecoveryRenderer

        # Create renderer and display
        renderer = RecoveryRenderer(self.es_client.theme_manager)
        renderer.render_enhanced_recovery_status(recovery_status)

    def print_stylish_health_dashboard(self, health_data: Dict[str, Any],
                                     include_snapshots: bool = True,
                                     snapshot_repo: Optional[str] = None,
                                     recovery_status: Optional[Dict[str, Any]] = None) -> None:
        """
        Display health dashboard in enhanced format.

        Args:
            health_data: Cluster health data dictionary
            include_snapshots: Whether to include snapshots panel
            snapshot_repo: Snapshot repository name for snapshots panel
            recovery_status: Recovery status information for performance panel
        """
        from display.health_renderer import HealthRenderer

        # Create renderer and display
        renderer = HealthRenderer(self.es_client.theme_manager, self.es_client)
        renderer.print_stylish_health_dashboard(health_data, include_snapshots, snapshot_repo, recovery_status)

    def get_pending_tasks(self) -> Dict[str, Any]:
        """
        Get pending cluster tasks.

        Returns:
            dict: Pending tasks information
        """
        try:
            tasks = self.es_client.es.cluster.pending_tasks()

            # Handle response format differences
            if hasattr(tasks, 'body'):
                return tasks.body
            elif hasattr(tasks, 'get'):
                return dict(tasks)
            else:
                return tasks

        except Exception as e:
            return {"error": f"Failed to get pending tasks: {str(e)}"}

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of a specific task.

        Args:
            task_id: Task identifier

        Returns:
            dict: Task status information
        """
        try:
            task = self.es_client.es.tasks.get(task_id=task_id)

            # Handle response format differences
            if hasattr(task, 'body'):
                return task.body
            elif hasattr(task, 'get'):
                return dict(task)
            else:
                return task

        except Exception as e:
            return {
                "error": f"Failed to get task status: {str(e)}",
                "task_id": task_id
            }

    def get_running_tasks(self) -> Dict[str, Any]:
        """
        Get currently running tasks.

        Returns:
            dict: Running tasks information
        """
        try:
            tasks = self.es_client.es.tasks.list()

            # Handle response format differences
            if hasattr(tasks, 'body'):
                return tasks.body
            elif hasattr(tasks, 'get'):
                return dict(tasks)
            else:
                return tasks

        except Exception as e:
            return {"error": f"Failed to get running tasks: {str(e)}"}

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        Cancel a running task.

        Args:
            task_id: Task identifier to cancel

        Returns:
            dict: Cancellation result
        """
        try:
            result = self.es_client.es.tasks.cancel(task_id=task_id)

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {
                "error": f"Failed to cancel task: {str(e)}",
                "task_id": task_id
            }

    def get_hot_threads(self, node_id: Optional[str] = None, threads: int = 3,
                       interval: str = '500ms', snapshots: int = 10) -> Dict[str, Any]:
        """
        Get hot threads information for performance analysis.

        Args:
            node_id: Specific node ID (optional)
            threads: Number of threads to show
            interval: Sampling interval
            snapshots: Number of snapshots

        Returns:
            dict: Hot threads information
        """
        try:
            params = {
                'threads': threads,
                'interval': interval,
                'snapshots': snapshots
            }
            if node_id:
                params['node_id'] = node_id

            hot_threads = self.es_client.es.nodes.hot_threads(**params)

            # Handle response - hot_threads returns text, not JSON
            if hasattr(hot_threads, 'body'):
                return {"hot_threads": hot_threads.body}
            elif isinstance(hot_threads, str):
                return {"hot_threads": hot_threads}
            else:
                return {"hot_threads": str(hot_threads)}

        except Exception as e:
            return {
                "error": f"Failed to get hot threads: {str(e)}",
                "node_id": node_id
            }

    def get_thread_pool_stats(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get thread pool statistics.

        Args:
            node_id: Specific node ID (optional)

        Returns:
            dict: Thread pool statistics
        """
        try:
            params = {'metric': 'thread_pool'}
            if node_id:
                params['node_id'] = node_id

            stats = self.es_client.es.nodes.stats(**params)

            # Handle response format differences
            if hasattr(stats, 'body'):
                return stats.body
            elif hasattr(stats, 'get'):
                return dict(stats)
            else:
                return stats

        except Exception as e:
            return {
                "error": f"Failed to get thread pool stats: {str(e)}",
                "node_id": node_id
            }

    def check_shard_health(self, index_pattern: str = '*') -> Dict[str, Any]:
        """
        Analyze shard health across indices.

        Args:
            index_pattern: Pattern to match indices

        Returns:
            dict: Shard health analysis
        """
        try:
            # Get cluster health at shard level
            health = self.check_cluster_health(level='shards')

            # Get additional shard information
            shards = self.es_client.nodes_commands.get_shards(index_pattern)

            # Combine health and shard data
            result = {
                "health_overview": health,
                "shard_details": shards
            }

            return result

        except Exception as e:
            return {
                "error": f"Failed to check shard health: {str(e)}",
                "index_pattern": index_pattern
            }

    def get_disk_watermarks(self) -> Dict[str, Any]:
        """
        Get disk watermark information from cluster settings.

        Returns:
            dict: Disk watermark configuration
        """
        try:
            settings = self.es_client.settings_commands.get_cluster_settings()

            # Extract disk watermark settings
            watermarks = {}

            if 'persistent' in settings:
                for key, value in settings['persistent'].items():
                    if 'disk.watermark' in key:
                        watermarks[key] = value

            if 'transient' in settings:
                for key, value in settings['transient'].items():
                    if 'disk.watermark' in key:
                        watermarks[key] = value

            # Add default values if not set
            if not watermarks:
                watermarks = {
                    "cluster.routing.allocation.disk.watermark.low": "85%",
                    "cluster.routing.allocation.disk.watermark.high": "90%",
                    "cluster.routing.allocation.disk.watermark.flood_stage": "95%"
                }

            return {"disk_watermarks": watermarks}

        except Exception as e:
            return {"error": f"Failed to get disk watermarks: {str(e)}"}

    def check_no_replica_indices(self):
        """
        Check for indices that have no replicas (number_of_replicas = 0).
        Returns a list of indices with no replicas.
        """
        import requests
        from requests.auth import HTTPBasicAuth

        try:
            ES_URL = self.es_client.build_es_url()
            if ES_URL is None:
                return []

            # Get index settings for all indices
            settings_url = f'{ES_URL}/_all/_settings'

            if self.es_client.elastic_authentication == True:
                response = requests.get(
                    settings_url,
                    auth=HTTPBasicAuth(self.es_client.elastic_username, self.es_client.elastic_password),
                    verify=False,
                    timeout=self.es_client.timeout
                )
            else:
                response = requests.get(settings_url, verify=False, timeout=self.es_client.timeout)

            response.raise_for_status()

            data = response.json()
            no_replica_indices = []

            for index_name, index_data in data.items():
                if 'settings' in index_data:
                    settings = index_data['settings']
                    index_settings = settings.get('index', {})

                    # Check number_of_replicas
                    replicas = index_settings.get('number_of_replicas', '1')

                    # Convert to int for comparison
                    try:
                        replica_count = int(replicas)
                        if replica_count == 0:
                            no_replica_indices.append({
                                'index': index_name,
                                'replicas': replica_count,
                                'shards': index_settings.get('number_of_shards', 'Unknown'),
                                'creation_date': index_settings.get('creation_date', 'Unknown')
                            })
                    except (ValueError, TypeError):
                        # Skip if replica count cannot be determined
                        continue

            return no_replica_indices

        except Exception as e:
            print(f"Error checking replica settings: {str(e)}")
            return []

    def check_large_shards(self, max_size_gb=50):
        """
        Check for shards larger than the specified size in GB.
        Returns a list of large shards.
        """
        import requests
        from requests.auth import HTTPBasicAuth

        try:
            ES_URL = self.es_client.build_es_url()
            if ES_URL is None:
                return []

            # Get detailed shard information
            shards_url = f'{ES_URL}/_cat/shards?v&h=index,shard,prirep,store,node&bytes=b&s=store:desc'

            if self.es_client.elastic_authentication == True:
                response = requests.get(
                    shards_url,
                    auth=HTTPBasicAuth(self.es_client.elastic_username, self.es_client.elastic_password),
                    verify=False,
                    timeout=self.es_client.timeout
                )
            else:
                response = requests.get(shards_url, verify=False, timeout=self.es_client.timeout)

            response.raise_for_status()

            lines = response.text.strip().split('\n')
            large_shards = []
            max_size_bytes = max_size_gb * 1024 * 1024 * 1024  # Convert GB to bytes

            # Skip header line
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 5:
                    index_name = parts[0]
                    shard_id = parts[1]
                    shard_type = parts[2]  # 'p' for primary, 'r' for replica
                    store_size = parts[3]
                    node_name = parts[4] if len(parts) > 4 else 'unassigned'

                    try:
                        # Convert store size to bytes
                        if store_size and store_size != '-':
                            size_bytes = int(store_size)
                            if size_bytes > max_size_bytes:
                                size_gb = size_bytes / (1024 * 1024 * 1024)
                                large_shards.append({
                                    'index': index_name,
                                    'shard': shard_id,
                                    'type': 'Primary' if shard_type == 'p' else 'Replica',
                                    'size_bytes': size_bytes,
                                    'size_gb': round(size_gb, 2),
                                    'node': node_name
                                })
                    except (ValueError, TypeError):
                        # Skip if size cannot be determined
                        continue

            return large_shards

        except Exception as e:
            print(f"Error checking shard sizes: {str(e)}")
            return []

    def perform_cluster_health_checks(self, max_shard_size_gb=50, skip_ilm=False):
        """
        Perform comprehensive cluster health checks and return all results.
        This is a convenience method that aggregates all health checks.
        """
        results = {}

        try:
            # Step 1: ILM errors check (skip if requested)
            if not skip_ilm:
                results['ilm_errors'] = self.es_client.ilm_commands.check_ilm_errors()
            else:
                results['ilm_errors'] = {'skipped': True, 'reason': 'ILM checks skipped via --skip-ilm flag'}

            # Step 2: No replicas check
            results['no_replica_indices'] = self.check_no_replica_indices()

            # Step 3: Large shards check
            results['large_shards'] = self.check_large_shards(max_shard_size_gb)

            # Step 4: Additional metadata
            results['max_shard_size'] = max_shard_size_gb
            results['skip_ilm'] = skip_ilm
            results['timestamp'] = time.time()

            return results

        except Exception as e:
            return {
                'error': f"Failed to perform cluster health checks: {str(e)}",
                'max_shard_size': max_shard_size_gb,
                'skip_ilm': skip_ilm
            }

    def print_multi_cluster_health_comparison(self, config_file, group_name, output_format='table'):
        """
        Display health comparison for all clusters in a group.

        Args:
            config_file (str): Path to configuration file (can be None, will auto-detect)
            group_name (str): Name of cluster group to display
            output_format (str): Output format - 'table' or 'json'
        """
        try:
            from rich.console import Console
            from rich.table import Table
            import json
            import os

            console = Console()

            # Load configuration to get group members
            from configuration_manager import ConfigurationManager

            # Handle None config_file by using the es_client's config manager
            if config_file is None:
                # Use the existing config manager from es_client
                config_manager = self.es_client.configuration_manager
            else:
                # Use dual-file configuration mode for proper initialization
                script_directory = os.path.dirname(config_file)
                state_file = os.path.join(script_directory, 'escmd.json')
                main_config_file = os.path.join(script_directory, 'escmd.yml')
                servers_config_file = os.path.join(script_directory, 'elastic_servers.yml')

                config_manager = ConfigurationManager(
                    state_file_path=state_file,
                    main_config_path=main_config_file,
                    servers_config_path=servers_config_file
                )

            # Get cluster groups - handle both dual-file and single-file modes
            if hasattr(config_manager, 'cluster_groups'):
                cluster_groups = config_manager.cluster_groups
            else:
                # Fallback to config attribute for single-file mode
                all_config = getattr(config_manager, 'config', {})
                cluster_groups = all_config.get('cluster_groups', {})

            if group_name not in cluster_groups:
                print(f"ERROR: Group '{group_name}' not found in configuration.")
                available_groups = list(cluster_groups.keys())
                if available_groups:
                    print(f"Available groups: {', '.join(available_groups)}")
                return

            group_members = cluster_groups[group_name]
            if not group_members:
                print(f"ERROR: Group '{group_name}' has no members.")
                return

            # Collect health data for all clusters
            clusters_health_data = []

            if output_format == 'table':
                print(f"\nChecking health for {len(group_members)} clusters in group '{group_name}'...\n")

            for cluster_name in group_members:
                cluster_data = {
                    'cluster_name': cluster_name,
                    'status': 'ERROR',
                    'version': 'N/A',
                    'nodes': 0,
                    'data_nodes': 0,
                    'primary_shards': 0,
                    'active_shards': 0,
                    'unassigned_shards': 0,
                    'shard_health_percent': 0.0,
                    'error': None
                }

                try:
                    # Get cluster configuration directly
                    cluster_config = config_manager.get_server_config_by_location(cluster_name)

                    if not cluster_config:
                        cluster_data.update({
                            'status': 'NOT_FOUND',
                            'error': 'Configuration not found'
                        })
                        clusters_health_data.append(cluster_data)
                        continue

                    # Create ES client for this cluster using the current client
                    from esclient import ElasticsearchClient
                    from configuration_manager import ConfigurationManager

                    # Create a configuration manager for this cluster
                    temp_config_manager = ConfigurationManager()
                    temp_config_manager.server_config = cluster_config
                    temp_config_manager.preprocess_indices = False

                    temp_client = ElasticsearchClient(temp_config_manager)

                    # Test connection first
                    if not temp_client.ping():
                        cluster_data.update({
                            'status': 'OFFLINE',
                            'error': 'Connection failed'
                        })
                        clusters_health_data.append(cluster_data)
                        continue

                    # Get health data
                    health_data = temp_client.get_cluster_health()

                    # Extract and format the data
                    display_name = health_data.get('cluster_name', cluster_name)
                    status = health_data.get('status', 'unknown').upper()

                    # Format version
                    version = health_data.get('cluster_version', 'Unknown')
                    if isinstance(version, dict):
                        version = version.get('number', 'Unknown')

                    # Update cluster data with real values
                    cluster_data.update({
                        'cluster_name': display_name,
                        'status': status,
                        'version': version,
                        'nodes': health_data.get('number_of_nodes', 0),
                        'data_nodes': health_data.get('number_of_data_nodes', 0),
                        'primary_shards': health_data.get('active_primary_shards', 0),
                        'active_shards': health_data.get('active_shards', 0),
                        'unassigned_shards': health_data.get('unassigned_shards', 0),
                        'shard_health_percent': health_data.get('active_shards_percent', 100.0),
                        'error': None
                    })

                except Exception as e:
                    cluster_data.update({
                        'status': 'ERROR',
                        'error': str(e)
                    })

                clusters_health_data.append(cluster_data)

            # Output the data in the requested format
            if output_format == 'json':
                # JSON output
                json_output = {
                    'group_name': group_name,
                    'cluster_count': len(group_members),
                    'clusters': clusters_health_data
                }
                print(json.dumps(json_output, indent=2))
            else:
                # Table output using themed styling
                from display.style_system import StyleSystem
                from rich.text import Text

                # Get the theme manager and create style system
                theme_manager = self.es_client.theme_manager
                style_system = StyleSystem(theme_manager)

                # Get theme styles for table
                header_style = "bold white"
                border_style = "white"
                if style_system:
                    # Get header and border styles from theme
                    full_theme = theme_manager.get_full_theme_data() if theme_manager else {}
                    table_styles = full_theme.get('table_styles', {})
                    header_style = table_styles.get('header_style', 'bold white')
                    border_style = table_styles.get('border_style', 'white')

                # Create themed table with proper styling
                table = Table(
                    box=style_system.get_table_box() if style_system else None,
                    header_style=header_style,
                    border_style=border_style,
                    show_header=True,
                    expand=True
                )

                # Add title with themed styling
                if theme_manager:
                    title_text = style_system.create_semantic_text(f"Health Status for Group: {group_name.upper()}", "title")
                    table.title = title_text
                else:
                    table.title = f"Health Status for Group: {group_name.upper()}"

                # Add columns with themed styling (abbreviated for better fit)
                headers = [
                    ("Cluster", "primary"),
                    ("Status", "info"),
                    ("Version", "muted"),
                    ("Nodes", "metric"),
                    ("Data", "metric"),
                    ("Primary", "metric"),
                    ("Shards", "metric"),
                    ("Unassign", "warning"),
                    ("Health%", "success")
                ]

                for header_text, semantic_type in headers:
                    if style_system:
                        header_style = style_system.get_semantic_style(semantic_type)
                        # Set column widths and justification for better layout
                        if header_text == "Cluster":
                            table.add_column(header_text, style=header_style, justify="left", min_width=10, max_width=15)
                        elif header_text == "Status":
                            table.add_column(header_text, style=header_style, justify="center", min_width=8, max_width=10)
                        elif header_text == "Version":
                            table.add_column(header_text, style=header_style, justify="left", min_width=7, max_width=9)
                        elif header_text == "Health%":
                            table.add_column(header_text, style=header_style, justify="right", min_width=7, max_width=8)
                        elif header_text in ["Nodes", "Data", "Primary", "Shards", "Unassign"]:
                            table.add_column(header_text, style=header_style, justify="right", min_width=5, max_width=7)
                        else:
                            table.add_column(header_text, style=header_style, justify="left")
                    else:
                        # Fallback column setup without theming
                        if header_text == "Cluster":
                            table.add_column(header_text, justify="left", min_width=10, max_width=15)
                        elif header_text == "Status":
                            table.add_column(header_text, justify="center", min_width=8, max_width=10)
                        elif header_text == "Version":
                            table.add_column(header_text, justify="left", min_width=7, max_width=9)
                        elif header_text == "Health%":
                            table.add_column(header_text, justify="right", min_width=7, max_width=8)
                        elif header_text in ["Nodes", "Data", "Primary", "Shards", "Unassign"]:
                            table.add_column(header_text, justify="right", min_width=5, max_width=7)
                        else:
                            table.add_column(header_text, justify="left")

                # Add rows with themed styling
                for cluster_data in clusters_health_data:
                    if cluster_data['status'] in ['NOT_FOUND', 'OFFLINE', 'ERROR']:
                        # Error states with semantic styling
                        status_icons = {
                            'NOT_FOUND': "✗ NOT FOUND",
                            'OFFLINE': "● OFFLINE",
                            'ERROR': "✗ ERROR"
                        }
                        status_text = status_icons.get(cluster_data['status'], "✗ ERROR")

                        if style_system:
                            cluster_name = style_system.create_semantic_text(cluster_data['cluster_name'], "primary")
                            status_display = style_system.create_semantic_text(status_text, "error")
                            na_text = style_system.create_semantic_text("N/A", "muted")
                            table.add_row(cluster_name, status_display, na_text, na_text, na_text, na_text, na_text, na_text, na_text)
                        else:
                            table.add_row(cluster_data['cluster_name'], f"[red]{status_text}[/red]", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A")
                    else:
                        # Healthy states with semantic styling
                        status = cluster_data['status']
                        if status == 'GREEN':
                            status_text, status_type = "✓ GREEN", "success"
                        elif status == 'YELLOW':
                            status_text, status_type = "⚠ YELLOW", "warning"
                        elif status == 'RED':
                            status_text, status_type = "✗ RED", "error"
                        else:
                            status_text, status_type = f"? {status}", "muted"

                        version = cluster_data['version']
                        if version != 'Unknown' and not str(version).startswith('v'):
                            version = f"v{version}"

                        unassigned_count = cluster_data['unassigned_shards']
                        health_percent = cluster_data['shard_health_percent']

                        if style_system:
                            cluster_name = style_system.create_semantic_text(cluster_data['cluster_name'], "primary")
                            status_display = style_system.create_semantic_text(status_text, status_type)
                            version_display = style_system.create_semantic_text(version, "muted")
                            nodes_display = style_system.create_semantic_text(str(cluster_data['nodes']), "metric")
                            data_nodes_display = style_system.create_semantic_text(str(cluster_data['data_nodes']), "metric")
                            primary_display = style_system.create_semantic_text(f"{cluster_data['primary_shards']:,}", "metric")
                            total_display = style_system.create_semantic_text(f"{cluster_data['active_shards']:,}", "metric")
                            unassigned_display = style_system.create_semantic_text(str(unassigned_count), "error" if unassigned_count > 0 else "success")
                            health_display = style_system.create_semantic_text(f"{health_percent:.1f}%", "success" if health_percent == 100.0 else "warning")

                            table.add_row(cluster_name, status_display, version_display, nodes_display, data_nodes_display, primary_display, total_display, unassigned_display, health_display)
                        else:
                            # Fallback styling without theme system
                            status_color = "green" if status == 'GREEN' else "yellow" if status == 'YELLOW' else "red"
                            unassigned_color = "red" if unassigned_count > 0 else "green"
                            health_color = "green" if health_percent == 100.0 else "yellow"

                            table.add_row(
                                cluster_data['cluster_name'],
                                f"[{status_color}]{status_text}[/{status_color}]",
                                f"[dim]{version}[/dim]",
                                str(cluster_data['nodes']),
                                str(cluster_data['data_nodes']),
                                f"{cluster_data['primary_shards']:,}",
                                f"{cluster_data['active_shards']:,}",
                                f"[{unassigned_color}]{unassigned_count}[/{unassigned_color}]",
                                f"[{health_color}]{health_percent:.1f}%[/{health_color}]"
                            )

                console.print(table)
                print()

        except Exception as e:
            print(f"ERROR: Error displaying group health: {str(e)}")


# Backward compatibility functions
def check_cluster_health(es_client, level: str = 'cluster',
                        wait_for_status: Optional[str] = None) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    health_cmd = HealthCommands(es_client)
    return health_cmd.check_cluster_health(level, wait_for_status)

def get_node_stats(es_client, node_id: Optional[str] = None,
                  metric: Optional[str] = None) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    health_cmd = HealthCommands(es_client)
    return health_cmd.get_node_stats(node_id, metric)

def get_cluster_stats(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    health_cmd = HealthCommands(es_client)
    return health_cmd.get_cluster_stats()

def get_pending_tasks(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    health_cmd = HealthCommands(es_client)
    return health_cmd.get_pending_tasks()

def get_hot_threads(es_client, node_id: Optional[str] = None, threads: int = 3,
                   interval: str = '500ms', snapshots: int = 10) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    health_cmd = HealthCommands(es_client)
    return health_cmd.get_hot_threads(node_id, threads, interval, snapshots)
