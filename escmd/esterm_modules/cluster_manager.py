#!/usr/bin/env python3
"""
Cluster Manager Module for ESterm

Handles all cluster connection logic including:
- Cluster discovery and selection
- Interactive cluster menus (both Rich and InquirerPy modes)
- Connection establishment and management
- Error handling for cluster operations
"""

import os
import sys
from typing import Optional, List, Dict, Any

# Optional advanced menu support
try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False

# Import Rich components
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.table import Table

# Import core ESCMD modules
from esclient import ElasticsearchClient
from configuration_manager import ConfigurationManager
from error_handling import ConnectionError


class ClusterManager:
    """
    Manages cluster connections and selection for ESterm.

    This class handles the discovery of available clusters, provides
    interactive menus for cluster selection, and manages the connection
    establishment process.
    """

    def __init__(self, console: Console):
        """
        Initialize the cluster manager.

        Args:
            console: Rich Console instance for output
        """
        self.console = console
        self.config_manager = None
        self.current_client = None
        self.current_location = None

    def load_cluster_configuration(self) -> bool:
        """
        Load cluster configuration from configuration files.

        Returns:
            bool: True if configuration loaded successfully
        """
        try:
            # Get the correct state file path (escmd.json in script directory)
            from utils import get_script_dir
            script_directory = get_script_dir()
            state_file = os.path.join(script_directory, 'escmd.json')
            self.config_manager = ConfigurationManager(state_file_path=state_file)
            return True
        except Exception as e:
            self.console.print(f"[red]Error loading cluster configuration: {e}[/red]")
            return False

    def get_available_clusters(self) -> List[str]:
        """
        Get list of available cluster names from configuration, sorted alphabetically.

        Returns:
            List[str]: List of available cluster names sorted alphabetically
        """
        if not self.config_manager:
            if not self.load_cluster_configuration():
                return []

        try:
            clusters = list(self.config_manager.servers_dict.keys())
            # Sort clusters alphabetically for better user experience
            return sorted(clusters, key=str.lower)
        except Exception:
            return []

    def get_clusters_with_environments(self) -> List[Dict[str, str]]:
        """
        Get list of available clusters with their environment information.

        Returns:
            List[Dict[str, str]]: List of dictionaries with 'name', 'env', and 'display_name' keys
        """
        if not self.config_manager:
            if not self.load_cluster_configuration():
                return []

        try:
            clusters = []
            for name, config in self.config_manager.servers_dict.items():
                env = config.get('env', 'unknown').upper()
                display_name = f"{name} [{env}]"
                clusters.append({
                    'name': name,
                    'env': env,
                    'display_name': display_name
                })

            # Sort clusters alphabetically by name for better user experience
            return sorted(clusters, key=lambda x: x['name'].lower())
        except Exception:
            return []

    def connect_to_cluster(self, location: Optional[str] = None) -> bool:
        """
        Connect to an Elasticsearch cluster.

        Args:
            location: Specific cluster location to connect to

        Returns:
            bool: True if connection successful
        """
        try:
            if not self.config_manager:
                if not self.load_cluster_configuration():
                    return False

            # Determine which cluster to connect to
            if not location:
                location = self.config_manager.get_default_cluster()

            if not location:
                self.console.print("[yellow]No cluster specified and no default cluster configured.[/yellow]")
                return False

            # Get cluster configuration
            location_config = self.config_manager.get_server_config_by_location(location)
            if not location_config:
                self.console.print(f"[red]Cluster configuration not found for: {location}[/red]")
                return False

            # Create client
            self.config_manager.server_config = location_config
            # Allow preprocessing in terminal mode to ensure commands work properly
            self.config_manager.preprocess_indices = True

            try:
                self.current_client = ElasticsearchClient(self.config_manager)
            except (ValueError, ConnectionError) as e:
                # Handle authentication/configuration/connection errors gracefully
                self.console.print(f"[red]Client initialization failed: {str(e)}[/red]")
                self.current_client = None
                self.current_location = None
                return False

            # Test the connection
            if self._test_connection():
                self.current_location = location
                self.console.print(f"[green]✓ Connected to cluster: [bold]{location}[/bold][/green]")
                return True
            else:
                self.current_client = None
                self.current_location = None
                return False

        except Exception as e:
            self.console.print(f"[red]Connection failed: {str(e)}[/red]")
            self.current_client = None
            self.current_location = None
            return False

    def _test_connection(self) -> bool:
        """
        Test the Elasticsearch connection.

        Returns:
            bool: True if connection is working
        """
        try:
            if not self.current_client:
                return False

            # Simple ping test
            health = self.current_client.es.cluster.health()
            if hasattr(health, 'body'):
                return health.body.get('status') is not None
            else:
                return health.get('status') is not None

        except Exception:
            return False

    def show_cluster_selection(self) -> bool:
        """
        Show cluster selection interface and handle user choice.

        Returns:
            bool: True if cluster was selected and connected
        """
        try:
            clusters_with_env = self.get_clusters_with_environments()

            if not clusters_with_env:
                self.console.print("[yellow]No clusters configured. Please configure a cluster first.[/yellow]")
                return False

            # Use interactive menu for better UX
            selected_cluster = self._show_interactive_menu(clusters_with_env)

            if selected_cluster:
                self.console.print(f"\n[blue]Connecting to {selected_cluster}...[/blue]")
                return self.connect_to_cluster(selected_cluster)
            else:
                self.console.print("[yellow]No cluster selected. Continuing without connection.[/yellow]")
                return False

        except Exception as e:
            self.console.print(f"[red]Error in cluster selection: {e}[/red]")
            return False

    def _show_interactive_menu(self, clusters: List[Dict[str, str]]) -> Optional[str]:
        """
        Display an enhanced interactive menu for cluster selection.
        Uses InquirerPy if available for arrow key navigation, otherwise falls back to Rich.

        Args:
            clusters: List of cluster dictionaries with 'name', 'env', and 'display_name' keys

        Returns:
            str or None: Selected cluster name or None if cancelled
        """
        if not clusters:
            return None

        # Use advanced InquirerPy menu if available
        if INQUIRER_AVAILABLE and len(clusters) > 1:
            return self._show_inquirer_menu(clusters)
        else:
            return self._show_rich_menu(clusters)

    def _show_inquirer_menu(self, clusters: List[Dict[str, str]]) -> Optional[str]:
        """Advanced interactive menu using InquirerPy with arrow key navigation."""
        try:
            choices = [
                Choice(cluster['name'], name=f"🌐 {cluster['display_name']}")
                for cluster in clusters
            ]
            choices.append(Choice(None, name="⏩ Skip cluster selection"))

            selected = inquirer.select(
                message="Select Elasticsearch Cluster:",
                choices=choices,
                default=clusters[0]['name'] if clusters else None,
                pointer="❯"
            ).execute()

            return selected

        except KeyboardInterrupt:
            return None
        except Exception:
            # Fallback to Rich menu if InquirerPy fails
            return self._show_rich_menu(clusters)

    def _show_rich_menu(self, clusters: List[Dict[str, str]]) -> Optional[str]:
        """Rich-based interactive menu (fallback method)."""
        # Enhanced Rich-based menu
        self.console.print("\n[bold blue]🌐 Available Elasticsearch Clusters:[/bold blue]")

        # Create a nicely formatted table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Number", style="bold cyan", width=4)
        table.add_column("Cluster", style="white")
        table.add_column("Environment", style="green", justify="center")

        for i, cluster in enumerate(clusters, 1):
            table.add_row(f"{i}.", cluster['name'], f"[{cluster['env']}]")

        self.console.print(table)

        self.console.print("\n[dim]Options:[/dim]")
        self.console.print(f"  • [cyan]Enter number[/cyan] (1-{len(clusters)}) to select cluster")
        self.console.print("  • [cyan]Enter cluster name[/cyan] directly")
        self.console.print("  • [cyan]Press Enter[/cyan] to skip cluster selection")
        self.console.print("  • [cyan]Type 'q'[/cyan] to quit")

        cluster_names = [cluster['name'] for cluster in clusters]

        while True:
            try:
                choice = Prompt.ask(
                    "\n[bold blue]Select cluster[/bold blue]",
                    default=""
                )

                if not choice.strip():
                    return None

                if choice.lower() == 'q':
                    return None

                # Check if it's a number
                if choice.isdigit():
                    cluster_index = int(choice) - 1
                    if 0 <= cluster_index < len(clusters):
                        return clusters[cluster_index]['name']
                    else:
                        self.console.print(f"[red]Invalid number. Please enter 1-{len(clusters)}[/red]")
                        continue

                # Check if it's a cluster name
                if choice in cluster_names:
                    return choice
                else:
                    self.console.print(f"[red]Cluster '{choice}' not found.[/red]")
                    continue

            except KeyboardInterrupt:
                return None

    def get_current_cluster(self) -> Optional[str]:
        """
        Get the currently connected cluster name.

        Returns:
            str or None: Current cluster name or None if not connected
        """
        return self.current_location

    def get_current_client(self) -> Optional[ElasticsearchClient]:
        """
        Get the current Elasticsearch client.

        Returns:
            ElasticsearchClient or None: Current client or None if not connected
        """
        return self.current_client

    def is_connected(self) -> bool:
        """
        Check if currently connected to a cluster.

        Returns:
            bool: True if connected and connection is healthy
        """
        return self.current_client is not None and self._test_connection()

    def disconnect(self):
        """Disconnect from current cluster."""
        if self.current_client:
            try:
                # Clean up any resources if needed
                pass
            except Exception:
                pass
            finally:
                self.current_client = None
                self.current_location = None

    def get_cluster_info(self) -> Optional[Dict[str, Any]]:
        """
        Get basic information about the current cluster.

        Returns:
            dict or None: Cluster information or None if not connected
        """
        if not self.current_client or not self.is_connected():
            return None

        try:
            # Get basic cluster health
            health = self.current_client.es.cluster.health()
            if hasattr(health, 'body'):
                health_data = health.body
            else:
                health_data = health

            return {
                'name': self.current_location,
                'status': health_data.get('status', 'unknown'),
                'nodes': health_data.get('number_of_nodes', 0),
                'data_nodes': health_data.get('number_of_data_nodes', 0),
                'active_shards': health_data.get('active_shards', 0),
                'cluster_name': health_data.get('cluster_name', 'unknown')
            }

        except Exception:
            return {
                'name': self.current_location,
                'status': 'error',
                'error': 'Unable to fetch cluster info'
            }

    def list_clusters_with_status(self) -> List[Dict[str, Any]]:
        """
        Get list of all configured clusters with basic status information.

        Returns:
            List[Dict]: List of cluster information dictionaries
        """
        clusters = []
        available_cluster_names = self.get_available_clusters()

        for cluster_name in available_cluster_names:
            cluster_info = {
                'name': cluster_name,
                'status': 'unknown',
                'current': cluster_name == self.current_location
            }

            # If this is the current cluster, we already have status
            if cluster_name == self.current_location and self.is_connected():
                info = self.get_cluster_info()
                if info:
                    cluster_info.update(info)

            clusters.append(cluster_info)

        return clusters
