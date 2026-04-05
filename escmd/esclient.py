#!/usr/bin/python3
from elasticsearch import Elasticsearch, ElasticsearchWarning, exceptions
from elasticsearch.exceptions import NotFoundError, RequestError
from requests.auth import HTTPBasicAuth

from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box

import json
import os
import requests
import urllib3
import warnings
import sys

# Import new display components
from display import (
    ThemeManager,
    TableRenderer,
    PanelRenderer,
    JSONFormatter,
    ProgressDisplay,
    StorageRenderer,
    IndexRenderer,
    AllocationRenderer,
    RecoveryRenderer,
    RepositoriesRenderer,
)
from display.ilm_renderer import ILMRenderer
from display.snapshot_renderer import SnapshotRenderer
from display.health_renderer import HealthRenderer
from display.shard_renderer import ShardRenderer
from display.template_renderer import TemplateRenderer
from display.style_system import StyleSystem

# Import new processing components
from processors import (
    IndexProcessor,
    NodeProcessor,
    ShardProcessor,
    AllocationProcessor,
    StatisticsProcessor,
)
from processors.snapshot_processor import SnapshotProcessor

# Import new command components
from commands import (
    CommandRegistry,
    ClusterCommands,
    IndicesCommands,
    NodesCommands,
    SnapshotCommands,
    AllocationCommands,
    SettingsCommands,
    HealthCommands,
    UtilityCommands,
    ILMCommands,
    ReplicaCommands,
    DatastreamCommands,
    TemplateCommands,
)

# Import error handling
from error_handling import ConnectionError

# Suppress only the InsecureRequestWarning from urllib3 needed for Elasticsearch
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(DeprecationWarning)

# Suppress the UserWarning and SecurityWarning
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")
warnings.filterwarnings("ignore", category=ElasticsearchWarning)
warnings.filterwarnings("ignore", message=".*verify_certs=False.*", category=Warning)

# Check Elasticsearch client version for compatibility
try:
    from elasticsearch import __version__ as es_version

    if isinstance(es_version, tuple):
        ES_VERSION_MAJOR = es_version[0]
    elif isinstance(es_version, str):
        ES_VERSION_MAJOR = int(es_version.split(".")[0])
    else:
        ES_VERSION_MAJOR = 7  # Default fallback
except (ImportError, AttributeError, ValueError, IndexError):
    # Default to assume version 7.x if we can't detect
    ES_VERSION_MAJOR = 7


def get_theme_styles(configuration_manager):
    """
    Backward compatibility function that uses the new ThemeManager.

    Returns:
        dict: Style configuration with 'header_style', 'health_styles', 'status_styles', etc.
    """
    theme_manager = ThemeManager(configuration_manager)
    return theme_manager.get_theme_styles()


def get_full_theme_data(configuration_manager):
    """
    Backward compatibility function that uses the new ThemeManager.

    Returns:
        dict: Complete theme configuration with all categories
    """
    theme_manager = ThemeManager(configuration_manager)
    return theme_manager.get_full_theme_data()


class ElasticsearchClient:
    def __init__(self, configuration_manager, console=None, skip_connection_test=False):
        """
        Initialize Elasticsearch Client with modular architecture.

        Args:
            configuration_manager: ConfigurationManager instance
            console: Rich console instance (optional, creates one if not provided)
            skip_connection_test: If True, skip connection validation (for env/group commands)
        """
        # Store configuration
        self.configuration_manager = configuration_manager
        self.console = console if console else Console()

        # Load connection configuration - get from server_config if available
        server_config = getattr(configuration_manager, "server_config", {})

        self.host1 = server_config.get("elastic_host", "localhost")
        self.host2 = server_config.get("elastic_host2")
        self.host3 = server_config.get("elastic_host3")
        self.port = server_config.get("elastic_port", 9200)
        # Support both naming conventions for SSL settings
        self.use_ssl = server_config.get("use_ssl") or server_config.get(
            "elastic_use_ssl", False
        )
        self.verify_certs = server_config.get("verify_certs") or server_config.get(
            "elastic_verify_certs", False
        )
        # Support both naming conventions for timeout; align with ConfigurationManager default
        _rt = server_config.get("read_timeout")
        if _rt is None:
            _rt = server_config.get("elastic_read_timeout")
        if _rt is None:
            _rt = self.configuration_manager.get_read_timeout()
        self.timeout = int(_rt)
        self.elastic_authentication = server_config.get("elastic_authentication", False)
        self.elastic_username = server_config.get("elastic_username")
        self.elastic_password = server_config.get("elastic_password")
        self.preprocess_indices = getattr(
            configuration_manager, "preprocess_indices", True
        )

        # Initialize display components
        self.theme_manager = ThemeManager(configuration_manager)
        self.style_system = StyleSystem(self.theme_manager)
        self.table_renderer = TableRenderer(self.theme_manager)
        self.panel_renderer = PanelRenderer(self.theme_manager)
        self.json_formatter = JSONFormatter(self.theme_manager)
        self.progress_display = ProgressDisplay(self.theme_manager)
        self.storage_renderer = StorageRenderer(
            self.theme_manager, None, self.style_system
        )
        self.allocation_renderer = AllocationRenderer(self.theme_manager)
        self.recovery_renderer = RecoveryRenderer(self.theme_manager)
        self.health_renderer = HealthRenderer(self.theme_manager)

        # ILM display renderer will be initialized after ES connection
        self.ilm_renderer = None

        # Initialize processing components
        self.index_processor = IndexProcessor()
        self.node_processor = NodeProcessor()
        self.shard_processor = ShardProcessor()
        self.allocation_processor = AllocationProcessor()
        self.statistics_processor = StatisticsProcessor()

        # Initialize command registry and commands
        # We'll initialize them after ES connection is established since they need self
        self.command_registry = None

        # Initialize command handlers - they need the ES client instance
        # We'll initialize them after ES connection is established
        self.cluster_commands = None
        self.indices_commands = None
        self.nodes_commands = None
        self.snapshot_commands = None
        self.allocation_commands = None
        self.settings_commands = None
        self.health_commands = None
        self.utility_commands = None
        self.ilm_commands = None

        # Create ES connection trying with host1
        self.es = self.create_es_client(self.host1)

        # Skip connection testing in test mode or when explicitly requested
        test_mode = os.environ.get("ESCMD_TEST_MODE", "false").lower() in (
            "true",
            "1",
            "yes",
        )

        if not test_mode and not skip_connection_test:
            if not self.es.ping() and self.host2:
                import sys

                print(
                    f"Connection to {self.host1} failed. Attempting to connect to {self.host2}...",
                    file=sys.stderr,
                )
                self.es = self.create_es_client(self.host2)

                if not self.es.ping():
                    attempted_settings1 = f"host:{self.host1}, port:{self.port}, ssl:{self.use_ssl}, verify_certs:{self.verify_certs}"
                    attempted_settings2 = f"host:{self.host2}, port:{self.port}, ssl:{self.use_ssl}, verify_certs:{self.verify_certs}"

                    # Build error message with authentication details if enabled
                    error_msg = f"ERROR: There was a 'Connection Error' trying to connect to ES.\nSettings: {attempted_settings1}\nSettings: {attempted_settings2}"

                    if self.elastic_authentication and self.elastic_username:
                        error_msg += (
                            f"\nAuthentication: username '{self.elastic_username}'"
                        )
                        error_msg += "\n\n💡 Please verify that the password is correct for this environment."

                    self.show_message_box(
                        "Connection Error",
                        error_msg,
                        message_style="bold white",
                        panel_style="red",
                    )
                    raise ConnectionError(
                        f"Failed to connect to both {self.host1} and {self.host2}",
                        self.host1,
                        self.port,
                    )
            elif not test_mode and not self.es.ping():
                attempted_settings = f"host:{self.host1}, port:{self.port}, ssl:{self.use_ssl}, verify_certs:{self.verify_certs}"

                # Build error message with authentication details if enabled
                error_msg = f"ERROR: There was a 'Connection Error' trying to connect to ES.\nSettings: {attempted_settings}"

                if self.elastic_authentication and self.elastic_username:
                    error_msg += f"\nAuthentication: username '{self.elastic_username}'"
                    error_msg += "\n\n💡 Please verify that the password is correct for this environment."

                self.show_message_box(
                    "Connection Error",
                    error_msg,
                    message_style="bold white",
                    panel_style="red",
                )
                raise ConnectionError(
                    f"Failed to connect to {self.host1}", self.host1, self.port
                )

        # Now that ES is connected, initialize command handlers and registry
        self.command_registry = CommandRegistry(self)
        self.cluster_commands = ClusterCommands(self)
        self.indices_commands = IndicesCommands(self)
        self.nodes_commands = NodesCommands(self)
        self.snapshot_commands = SnapshotCommands(
            self, self.theme_manager
        )  # Pass theme_manager
        self.allocation_commands = AllocationCommands(self)
        self.settings_commands = SettingsCommands(self)
        self.health_commands = HealthCommands(self)
        self.utility_commands = UtilityCommands(self)
        self.ilm_commands = ILMCommands(self)
        self.replica_commands = ReplicaCommands(self)
        self.datastream_commands = DatastreamCommands(self)
        self.template_commands = TemplateCommands(self)

        # Initialize ILM display renderer and pass statistics processor to storage renderer
        self.ilm_renderer = ILMRenderer(self)
        self.storage_renderer = StorageRenderer(
            self.theme_manager, self.statistics_processor, self.style_system
        )
        self.index_renderer = IndexRenderer(self.theme_manager, self)
        self.snapshot_renderer = SnapshotRenderer(self)
        self.repositories_renderer = RepositoriesRenderer(
            self.theme_manager, self.statistics_processor, self.style_system
        )
        self.shard_renderer = ShardRenderer(self.theme_manager)
        self.template_renderer = TemplateRenderer(
            self.theme_manager, self.table_renderer, self.panel_renderer
        )
        self.snapshot_processor = SnapshotProcessor(self)

        # Register all command handlers
        self.command_registry.register_command(self.cluster_commands)
        self.command_registry.register_command(self.indices_commands)
        self.command_registry.register_command(self.nodes_commands)
        self.command_registry.register_command(self.snapshot_commands)
        self.command_registry.register_command(self.allocation_commands)
        self.command_registry.register_command(self.settings_commands)
        self.command_registry.register_command(self.health_commands)
        self.command_registry.register_command(self.utility_commands)
        self.command_registry.register_command(self.datastream_commands)

        if self.preprocess_indices:
            # Get all indices, check for unique patterns, and get latest datastream for each indice
            self.cluster_indices = self.list_indices_stats()
            self.cluster_indices_patterns = self.extract_unique_patterns(
                self.cluster_indices
            )
            self.cluster_indices_hot_indexes = self.find_latest_indices(
                self.cluster_indices
            )

    # ================================
    # Display Methods (Delegation)
    # ================================

    def get_themed_style(self, category, style_type, default="white"):
        """Get themed style for various UI elements (delegates to theme_manager)."""
        return self.theme_manager.get_themed_style(category, style_type, default)

    def create_themed_panel(
        self,
        content,
        title=None,
        subtitle=None,
        title_style="title",
        border_style=None,
        **kwargs,
    ):
        """Create a themed panel with consistent styling (delegates to panel_renderer)."""
        return self.panel_renderer.create_themed_panel(
            content, title, subtitle, title_style, border_style, **kwargs
        )

    def pretty_print_json(self, data, indent=2):
        """Pretty print JSON data (delegates to json_formatter)."""
        self.json_formatter.format_json(data, indent)

    def show_message_box(
        self,
        title,
        message,
        message_style="white",
        panel_style="blue",
        border_style=None,
        width=None,
        theme_style=None,
    ):
        """Show a styled message box (delegates to panel_renderer)."""
        self.panel_renderer.show_message_box(
            title, message, message_style, panel_style, border_style, width, theme_style
        )

    # ================================
    # Core Elasticsearch Methods
    # ================================

    def create_es_client(self, host):
        """Create Elasticsearch client with authentication if configured."""
        if self.elastic_authentication:
            # Validate authentication credentials before creating client
            if self.elastic_username is None or self.elastic_password is None:
                error_msg = "Authentication is enabled but credentials are not properly configured.\n"
                if self.elastic_username is None:
                    error_msg += (
                        "Missing or invalid 'elastic_username' in configuration.\n"
                    )
                if self.elastic_password is None:
                    error_msg += (
                        "Missing or invalid 'elastic_password' in configuration.\n"
                    )
                error_msg += (
                    "Please check your configuration file or use password prompting."
                )

                # Use theme-aware error styling if available
                try:
                    from display.style_system import StyleSystem

                    style_system = StyleSystem(self.theme_manager)
                    error_panel = Panel.fit(
                        style_system.create_semantic_text(error_msg, "white"),
                        title=style_system.create_semantic_text(
                            "🔶  Authentication Error", "error"
                        ),
                        border_style=style_system.get_semantic_style("error"),
                        padding=(1, 2),
                    )
                    self.console.print(error_panel)
                except:
                    # Fallback to basic error display
                    print(f"ERROR: {error_msg}")

                # Raise exception instead of sys.exit(1) to allow graceful handling
                raise ValueError(error_msg)

            return Elasticsearch(
                [{"host": host, "port": self.port, "use_ssl": self.use_ssl}],
                timeout=self.timeout,
                verify_certs=self.verify_certs,
                http_auth=(self.elastic_username, self.elastic_password),
            )
        else:
            return Elasticsearch(
                [{"host": host, "port": self.port, "use_ssl": self.use_ssl}],
                timeout=self.timeout,
                verify_certs=self.verify_certs,
            )

    def _call_with_version_compatibility(self, method, primary_kwargs, fallback_kwargs):
        """Call an Elasticsearch method with version compatibility fallback."""
        try:
            return method(**primary_kwargs)
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                return method(**fallback_kwargs)
            else:
                raise e

    def build_es_url(self):
        """Build Elasticsearch URL for external access."""
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host1}:{self.port}"

    # ================================
    # Index Methods (Delegation)
    # ================================

    def list_dangling_indices(self):
        """Return dangling indices from the cluster (delegates to IndicesCommands)."""
        return self.indices_commands.list_dangling_indices()

    def delete_dangling_index(self, uuid):
        """Delete a dangling index by its UUID (delegates to IndicesCommands)."""
        return self.indices_commands.delete_dangling_index(uuid)

    def delete_indices(self, indice_data):
        """Delete multiple indices (delegates to IndicesCommands)."""
        if (
            isinstance(indice_data, list)
            and indice_data
            and isinstance(indice_data[0], dict)
        ):
            index_names = [
                indice.get("index") for indice in indice_data if indice.get("index")
            ]
        else:
            index_names = indice_data
        result = self.indices_commands.delete_indices(index_names)

        # Refresh indices cache after deletion to prevent stale data
        self.refresh_indices_cache()

        return result

    def create_index(self, index_name: str, settings=None, mappings=None):
        """Create a new empty index (delegates to IndicesCommands)."""
        result = self.indices_commands.create_index(index_name, settings, mappings)

        # Refresh indices cache after creation to show new index
        if result.get("success"):
            self.refresh_indices_cache()

        return result

    def filter_indices(self, pattern=None, status=None):
        """Filter indices by pattern and status (delegates to IndexProcessor)."""
        return self.index_processor.filter_indices(
            self.cluster_indices, pattern, status
        )

    def extract_unique_patterns(self, data):
        """Extract unique patterns from index data (delegates to IndexProcessor)."""
        return self.index_processor.extract_unique_patterns(data)

    def refresh_indices_cache(self):
        """Refresh the cached indices data."""
        if self.preprocess_indices:
            try:
                # Clear performance cache to ensure fresh data
                from performance import default_cache

                default_cache.invalidate()
            except ImportError:
                # Performance module not available, continue without clearing cache
                pass

            # Refresh all indices-related cached data
            self.cluster_indices = self.list_indices_stats()
            self.cluster_indices_patterns = self.extract_unique_patterns(
                self.cluster_indices
            )
            self.cluster_indices_hot_indexes = self.find_latest_indices(
                self.cluster_indices
            )

    def find_latest_indices(self, data):
        """Find latest indices based on date patterns (delegates to IndexProcessor)."""
        return self.index_processor.find_latest_indices(data)

    def get_indices_stats(self, pattern=None, status=None):
        """Get indices statistics (delegates to IndicesCommands)."""
        return self.indices_commands.get_indices_stats(pattern, status)

    def list_indices_stats(self, pattern=None, status=None):
        """List indices with statistics (delegates to IndicesCommands)."""
        return self.indices_commands.list_indices_stats(pattern, status)

    def filter_indices_by_status(self, indices, status):
        """Filter indices by status (delegates to IndexProcessor)."""
        return self.index_processor.filter_indices_by_status(indices, status)

    def get_index_info(self, index_name):
        """Get detailed information about an index (delegates to IndicesCommands)."""
        return self.indices_commands.get_index_info(index_name)

    def print_index_info(self, index_info):
        """Print formatted index information (delegates to IndicesCommands)."""
        return self.indices_commands.print_index_info(index_info)

    def get_index_ilm_short(self, data):
        """Get short ILM information for indices."""
        result = {}

        if not data or "indices" not in data:
            return result

        indices_data = data["indices"]

        for index_name, metadata in indices_data.items():
            phase = metadata.get("phase", None)
            age = metadata.get("age", 0)
            policy = metadata.get("policy", None)

            # Store in result dictionary with index_name as key
            result[index_name] = {"phase": phase, "age": age, "policy": policy}

        return result

    def get_index_ilms(self, short=False):
        """Get ILM information for all indices (delegates to SettingsCommands)."""
        return self.settings_commands.get_index_ilms(short)

    def get_all_index_settings(self):
        """Get settings for all indices (delegates to IndicesCommands)."""
        return self.indices_commands.get_all_index_settings()

    def print_table_indices(self, data_dict, use_pager=False):
        """Print enhanced indices table (delegates to IndicesCommands)."""
        return self.indices_commands.print_table_indices(data_dict, use_pager)

    # ================================
    # Node Methods (Delegation)
    # ================================

    def resolve_node_ids_to_hostnames(self, node_ids, node_id_to_hostname_map=None):
        """Resolve node IDs to hostnames (delegates to NodeProcessor)."""
        if node_id_to_hostname_map is None:
            node_id_to_hostname_map = self.get_node_id_to_hostname_map()
        return self.node_processor.resolve_node_ids_to_hostnames(
            node_ids, node_id_to_hostname_map
        )

    def get_node_id_to_hostname_map(self):
        """Get mapping of node IDs to hostnames (delegates to NodesCommands)."""
        return self.nodes_commands.get_node_id_to_hostname_map()

    def filter_nodes_by_role(self, nodes_list, role):
        """Filter nodes by their role (delegates to NodeProcessor)."""
        return self.node_processor.filter_nodes_by_role(nodes_list, role)

    def get_nodes(self):
        """Get all nodes information (delegates to NodesCommands)."""
        return self.nodes_commands.get_nodes()

    def get_nodes_fast(self):
        """Get nodes information quickly (delegates to NodesCommands)."""
        return self.nodes_commands.get_nodes_fast()

    def get_all_nodes_stats(self):
        """Get statistics for all nodes (delegates to NodesCommands)."""
        return self.nodes_commands.get_all_nodes_stats()

    def print_enhanced_nodes_table(self, nodes, show_data_only=False):
        """Print enhanced nodes table (delegates to NodesCommands)."""
        return self.nodes_commands.print_enhanced_nodes_table(nodes, show_data_only)

    def print_enhanced_masters_info(self, master_nodes):
        """Print enhanced masters information (delegates to NodesCommands)."""
        return self.nodes_commands.print_enhanced_masters_info(master_nodes)

    def get_master_node(self):
        """Get master node information."""
        return self.es.cat.master(h="node").strip()

    def get_snapshot_stats_fast(self, repository_name):
        """Get basic snapshot statistics (fast version for dashboard) (delegates to SnapshotProcessor)."""
        return self.snapshot_processor.get_snapshot_stats_fast(repository_name)

    def print_stylish_health_dashboard(
        self,
        health_data,
        include_snapshots=True,
        snapshot_repo=None,
        recovery_status=None,
    ):
        """Display cluster health dashboard (delegates to HealthCommands)."""
        return self.health_commands.print_stylish_health_dashboard(
            health_data, include_snapshots, snapshot_repo, recovery_status
        )

    def _create_cluster_overview_panel(self, health_data, theme_color):
        """Create cluster overview panel (delegates to HealthRenderer)."""
        from display.health_renderer import HealthRenderer

        renderer = HealthRenderer(self.theme_manager, self)
        return renderer._create_cluster_overview_panel(health_data, theme_color)

    def _create_nodes_panel(self, health_data, theme_color):
        """Create nodes information panel (delegates to HealthRenderer)."""
        from display.health_renderer import HealthRenderer

        renderer = HealthRenderer(self.theme_manager, self)
        return renderer._create_nodes_panel(health_data, theme_color)

    def _create_shards_panel(self, health_data, theme_color):
        """Create shards information panel (delegates to HealthRenderer)."""
        from display.health_renderer import HealthRenderer

        renderer = HealthRenderer(self.theme_manager, self)
        return renderer._create_shards_panel(health_data, theme_color)

    def _create_performance_panel(self, health_data, theme_color, recovery_status=None):
        """Create performance metrics panel (delegates to HealthRenderer)."""
        from display.health_renderer import HealthRenderer

        renderer = HealthRenderer(self.theme_manager, self)
        return renderer._create_performance_panel(
            health_data, theme_color, recovery_status
        )

    def _create_snapshots_panel(self, theme_color, snapshot_repo=None, snapshots=None):
        """Create snapshots information panel (delegates to SnapshotRenderer)."""
        return self.snapshot_renderer.create_snapshots_panel(
            theme_color, snapshot_repo, snapshots
        )

    def _create_allocation_issues_panel(self, allocation_issues):
        """Create allocation issues panel."""
        return self.allocation_renderer.create_allocation_issues_panel(
            allocation_issues
        )

    def parse_node_stats(self, node_stats):
        """Parse node statistics (delegates to NodeProcessor)."""
        return self.node_processor.parse_node_stats(node_stats)

    # ================================
    # Cluster Methods (Delegation)
    # ================================

    def get_cluster_info(self):
        """Get cluster information (delegates to ClusterCommands)."""
        return self.cluster_commands.get_cluster_info()

    def get_cluster_health(self, include_version=True):
        """Get cluster health (delegates to ClusterCommands)."""
        return self.cluster_commands.get_cluster_health(include_version)

    def get_state_color(self, state):
        """Get color for cluster state (delegates to ClusterCommands)."""
        return self.cluster_commands.get_state_color(state)

    def ping(self):
        """Test connectivity to the Elasticsearch cluster (delegates to ClusterCommands)."""
        return self.cluster_commands.ping()

    def get_settings(self):
        """Get cluster settings (delegates to SettingsCommands)."""
        return self.settings_commands.get_cluster_settings()

    def print_enhanced_cluster_settings(self):
        """Print enhanced cluster settings display (delegates to SettingsCommands)."""
        return self.settings_commands.print_enhanced_cluster_settings()

    # ================================
    # Allocation Methods (Delegation)
    # ================================

    def get_allocation_as_dict(self):
        """Get allocation information as dictionary (delegates to AllocationCommands)."""
        return self.allocation_commands.get_allocation_as_dict()

    def get_index_allocation_explain(self, index_name, shard_number, is_primary):
        """Get allocation explanation for an index shard (delegates to AllocationCommands)."""
        return self.allocation_commands.get_index_allocation_explain(
            index_name, shard_number, is_primary
        )

    def get_enhanced_allocation_explain(self, index_name, shard_number, is_primary):
        """Get enhanced allocation explanation (delegates to AllocationCommands)."""
        return self.allocation_commands.get_enhanced_allocation_explain(
            index_name, shard_number, is_primary
        )

    def print_allocation_explain_results(self, explain_result):
        """Print allocation explanation results (delegates to AllocationCommands)."""
        return self.allocation_commands.print_allocation_explain_results(explain_result)

    def check_allocation_issues(self):
        """Check for allocation issues (delegates to AllocationCommands)."""
        return self.allocation_commands.check_allocation_issues()

    def exclude_index_from_host(self, index_name=None, host_to_exclude=None):
        """Exclude an index from allocation on a host (delegates to AllocationCommands)."""
        return self.allocation_commands.exclude_index_from_host(
            index_name, host_to_exclude
        )

    def exclude_index_reset(self, index_name=None):
        """Reset index exclusion settings (delegates to AllocationCommands)."""
        return self.allocation_commands.exclude_index_reset(index_name)

    def change_shard_allocation(self, option):
        """Change cluster shard allocation settings (delegates to AllocationCommands)."""
        result = self.allocation_commands.change_shard_allocation(option)
        return result.get("acknowledged", True) if "error" not in result else False

    def exclude_node_from_allocation(self, hostname=None):
        """Exclude a node from shard allocation (delegates to AllocationCommands)."""
        result = self.allocation_commands.exclude_node_from_allocation(hostname)
        return result.get("acknowledged", True) if "error" not in result else False

    def reset_node_allocation_exclusion(self):
        """Reset node allocation exclusions (delegates to AllocationCommands)."""
        result = self.allocation_commands.reset_node_allocation_exclusion()
        return result.get("acknowledged", True) if "error" not in result else False

    def print_enhanced_allocation_settings(self):
        """
        Display allocation settings in enhanced multi-panel format following the 2.0+ style.
        """
        return self.allocation_commands.print_enhanced_allocation_settings()

    # ================================
    # Shard Methods (Delegation)
    # ================================

    def get_shards_stats(self, pattern=None):
        """Get shard statistics (uses consistent data source)."""
        shards_data = self.get_shards_as_dict()

        # Filter by pattern if provided
        if pattern and pattern != "*":
            import re

            filtered_shards = []
            for shard in shards_data:
                if "index" in shard and re.search(pattern, shard["index"]):
                    filtered_shards.append(shard)
            return filtered_shards
        return shards_data

    def get_shards_stats_direct(self, pattern=None):
        """
        Get shard statistics using direct index query for better data accuracy.

        Uses direct index query when pattern is provided for more complete data,
        falls back to general query and filtering for broader searches.
        """
        if pattern and pattern != "*":
            try:
                # First, try direct index query which returns complete data
                shards = self.es.cat.shards(index=pattern, format="json")

                # Handle response format differences
                if hasattr(shards, "body"):
                    return shards.body
                elif hasattr(shards, "__iter__"):
                    return list(shards)
                else:
                    return [shards] if shards else []

            except Exception:
                # Fallback to regex filtering if direct query fails
                # (e.g., if pattern is actually a regex, not an exact index name)
                return self.get_shards_stats(pattern=pattern)
        else:
            # For no pattern or wildcard, use the general method
            return self.get_shards_as_dict()

    def get_shards_as_dict(self):
        """Get shards information as dictionary."""
        try:
            # Explicitly request the fields we need to ensure they're included
            shards = self.es.cat.shards(
                format="json", h="index,shard,prirep,state,docs,store,node"
            )

            # Handle response format differences (same logic as allocation_commands)
            if hasattr(shards, "body"):
                return shards.body
            elif hasattr(shards, "__iter__"):
                return list(shards)
            else:
                return [shards] if shards else []

        except Exception as e:
            return [{"error": f"Failed to get shards: {str(e)}"}]

    def analyze_shard_colocation(self, pattern=None):
        """Analyze shard colocation (delegates to ShardProcessor)."""
        shards_data = self.get_shards_as_dict()
        return self.shard_processor.analyze_shard_colocation(shards_data, pattern)

    def print_shard_colocation_results(self, colocation_results, use_pager=False):
        """Print shard colocation analysis results (delegates to ShardRenderer)."""
        return self.shard_renderer.print_shard_colocation_results(
            colocation_results, use_pager, self.console, self.theme_manager
        )

    # ================================
    # Recovery Methods (Delegation)
    # ================================

    def get_recovery_status(self, index_name=None):
        """Get recovery status (delegates to HealthCommands)."""
        return self.health_commands.get_shard_recovery(index_name)

    def print_enhanced_recovery_status(self, recovery_status):
        """Print enhanced recovery status with Rich formatting."""
        return self.health_commands.print_enhanced_recovery_status(recovery_status)

    # ================================
    # Template Methods (Delegation)
    # ================================

    def get_template(self, name=None):
        """Get index templates (delegates to SettingsCommands)."""
        return self.settings_commands.get_template(name)

    # ================================
    # Utility Methods (Delegation)
    # ================================

    def format_bytes(self, size_in_bytes):
        """Format bytes to human-readable format (delegates to StatisticsProcessor)."""
        return self.statistics_processor.format_bytes(size_in_bytes)

    def size_to_bytes(self, size_str):
        """Convert size string to bytes (delegates to StatisticsProcessor)."""
        return self.statistics_processor.size_to_bytes(size_str)

    def obtain_keys_values(self, data):
        """Obtain keys and values from data structure (delegates to UtilityCommands)."""
        return self.utility_commands.obtain_keys_values(data)

    def flatten_json(self, json_obj, parent_key="", sep="."):
        """Flatten JSON object (delegates to UtilityCommands)."""
        return self.utility_commands.flatten_json(json_obj, parent_key, sep)

    def flush_synced_elasticsearch(
        self,
        host,
        port,
        use_ssl=False,
        authentication=False,
        username=None,
        password=None,
    ):
        """Issue a flush/synced request to Elasticsearch (delegates to UtilityCommands)."""
        return self.utility_commands.flush_synced_elasticsearch(
            host, port, use_ssl, authentication, username, password
        )

    # ================================
    # Snapshot Methods (Delegation)
    # ================================

    def list_snapshots(self, repository_name, progress_callback=None):
        """
        List snapshots in a repository, returns formatted list (delegates to SnapshotCommands).

        Args:
            repository_name: Name of the repository
            progress_callback: Optional callback function to update progress display

        Returns:
            list: Formatted snapshot information for display
        """
        return self.snapshot_commands.list_snapshots_formatted(
            repository_name, progress_callback
        )

    def list_snapshots_fast(self, repository_name, progress_callback=None):
        """
        List snapshots in a repository using fast mode (minimal metadata), returns formatted list (delegates to SnapshotCommands).

        Args:
            repository_name: Name of the repository
            progress_callback: Optional callback function to update progress display

        Returns:
            list: Formatted snapshot information for display (minimal metadata)
        """
        return self.snapshot_commands.list_snapshots_fast(
            repository_name, progress_callback
        )

    def get_snapshot_status(self, repository_name=None, snapshot_name=None):
        """Get snapshot status (delegates to SnapshotCommands) and format for display."""
        return self.snapshot_commands.get_snapshot_status_enhanced(
            repository_name, snapshot_name
        )

    def create_snapshot(
        self,
        repository_name=None,
        snapshot_name=None,
        indices=None,
        datastreams=None,
        wait_for_completion=False,
    ):
        """Create a snapshot (delegates to SnapshotCommands)."""
        return self.snapshot_commands.create_snapshot(
            repository=repository_name,
            snapshot_name=snapshot_name,
            indices=indices,
            datastreams=datastreams,
            wait_for_completion=wait_for_completion,
            default_repository=getattr(self, "_default_repository", "s3-repo"),
        )

    def delete_snapshot(self, repository, snapshot_name):
        """Delete a snapshot (delegates to SnapshotCommands)."""
        return self.snapshot_commands.delete_snapshot(repository, snapshot_name)

    def get_repositories(self):
        """Get snapshot repositories (delegates to SnapshotCommands)."""
        return self.snapshot_commands.get_repositories()

    def print_enhanced_repositories_table(self, repositories_data):
        """Print enhanced repositories table with Rich formatting and statistics (delegates to RepositoriesRenderer)."""
        return self.repositories_renderer.print_enhanced_repositories_table(
            repositories_data, self.console
        )

    def create_repository(self, repository_name, repo_type, settings):
        """Create a snapshot repository (delegates to SnapshotCommands)."""
        return self.snapshot_commands.create_repository(
            repository_name, repo_type, settings
        )

    def delete_repository(self, repository_name):
        """Delete a snapshot repository (delegates to SnapshotCommands)."""
        return self.snapshot_commands.delete_repository(repository_name)

    def verify_repository(self, repository_name):
        """Verify a snapshot repository (delegates to SnapshotCommands)."""
        return self.snapshot_commands.verify_repository(repository_name)

    def get_snapshot_info(self, repository_name, snapshot_name):
        """Get comprehensive snapshot information (delegates to SnapshotCommands)."""
        return self.snapshot_commands.get_snapshot_info_comprehensive(
            repository_name, snapshot_name
        )

    def list_datastreams(self):
        """List datastreams (delegates to UtilityCommands)."""
        return self.utility_commands.get_datastreams()

    def get_datastream_details(self, datastream_name):
        """Get detailed information about a specific datastream (delegates to UtilityCommands)."""
        return self.utility_commands.get_datastreams(datastream_name)

    def display_snapshot_status(self, status_info, repository_name):
        """Display snapshot status with Rich formatting (delegates to SnapshotRenderer)."""
        return self.snapshot_renderer.display_snapshot_status(
            status_info, repository_name
        )

    def print_table_shards(self, shards_info, use_pager=False):
        """Print table of shards (delegates to ShardRenderer)."""
        cluster_all_settings = self.get_all_index_settings()
        return self.shard_renderer.print_table_shards(
            shards_info=shards_info,
            cluster_all_settings=cluster_all_settings,
            cluster_indices_hot_indexes=self.cluster_indices_hot_indexes,
            use_pager=use_pager,
        )

    def print_enhanced_current_master(self, master_node_id):
        """Print enhanced current master information with Rich formatting (delegates to HealthRenderer)."""
        nodes_data = self.get_nodes()
        health_data = self.get_cluster_health()
        return self.health_renderer.print_enhanced_current_master(
            master_node_id, nodes_data, health_data
        )

    # ================================
    # Command Registry Methods
    # ================================

    def execute_command(self, command_type, method_name, *args, **kwargs):
        """Execute a command through the registry."""
        return self.command_registry.delegate_method(
            command_type, method_name, *args, **kwargs
        )

    def get_available_commands(self):
        """Get list of available commands."""
        return list(self.command_registry.commands.keys())

    # ================================
    # Index Management Methods
    # ================================

    def find_matching_index(self, indices_data, indice):
        """
        Check if a given index exists in the provided indices data (delegates to IndexProcessor).

        Args:
            indices_data (list or str): List of dictionaries or JSON string containing index data
            indice (str): The index name to search for

        Returns:
            bool: True if the index is found, False otherwise
        """
        return self.index_processor.find_matching_index(indices_data, indice)

    def freeze_index(self, index_name):
        """
        Freeze an index to make it read-only (delegates to IndicesCommands).

        Args:
            index_name (str): The name of the index to freeze.

        Returns:
            bool: True if successful, False otherwise.
        """
        return self.indices_commands.freeze_index(index_name)

    def unfreeze_index(self, index_name):
        """
        Unfreeze an index to make it writable again (delegates to IndicesCommands).

        Args:
            index_name (str): The name of the index to unfreeze.

        Returns:
            bool: True if successful, False otherwise.
        """
        return self.indices_commands.unfreeze_index(index_name)

    def rollover_datastream(self, datastream_name):
        """
        Rollover a datastream to create a new index (delegates to DatastreamCommands).

        Args:
            datastream_name (str): Name of the datastream to rollover

        Returns:
            dict: Rollover response data
        """
        return self.datastream_commands.rollover_datastream(datastream_name)

    def print_json_as_table(self, json_data):
        """
        Prints a JSON object as a pretty table using the rich module (delegates to JSONFormatter).

        Args:
            json_data (dict): Dictionary representing JSON key-value pairs.
        """
        return self.json_formatter.print_json_as_table(json_data, self.console)

    def print_detailed_indice_info(self, indice_name):
        """Print detailed information about a specific index with Rich formatting (delegates to IndexRenderer)."""
        return self.index_renderer.print_detailed_indice_info(indice_name, self.console)

    def print_enhanced_storage_table(self, data_dict, indices_count=None):
        """Print enhanced storage allocation table with Rich formatting and statistics (delegates to StorageRenderer)."""
        return self.storage_renderer.print_enhanced_storage_table(
            data_dict, self.console, indices_count
        )

    def check_ilm_errors(self):
        """Check for ILM errors (delegates to ILMCommands)."""
        return self.ilm_commands.check_ilm_errors()

    # ILM Delegation Methods
    def _get_ilm_status(self):
        """Get ILM status (delegates to ILMCommands)."""
        return self.ilm_commands.get_ilm_status()

    def get_ilm_policies(self):
        """Get all ILM policies (delegates to ILMCommands)."""
        return self.ilm_commands.get_ilm_policies()

    def get_ilm_policy_detail(self, policy_name):
        """Get detailed information for a specific ILM policy (delegates to ILMCommands)."""
        return self.ilm_commands.get_ilm_policy_detail(policy_name)

    def get_ilm_explain(self, index_name):
        """Get ILM explain for specific index (delegates to ILMCommands)."""
        return self.ilm_commands.get_ilm_explain(index_name)

    def get_ilm_errors(self):
        """Get indices with ILM errors (delegates to ILMCommands)."""
        return self.ilm_commands.get_ilm_errors()

    def get_ilm_policy_index_patterns(self, policy_name):
        """Get unique index patterns for a specific ILM policy (delegates to ILMCommands)."""
        return self.ilm_commands.get_ilm_policy_index_patterns(policy_name)

    def print_enhanced_ilm_status(self):
        """Display comprehensive ILM status in multi-panel format (delegates to ILMRenderer)."""
        return self.ilm_renderer.print_enhanced_ilm_status()

    def print_enhanced_ilm_policies(self):
        """Display ILM policies in enhanced format (delegates to ILMRenderer)."""
        return self.ilm_renderer.print_enhanced_ilm_policies()

    def print_enhanced_ilm_policy_detail(self, policy_name, show_all_indices=False):
        """Display detailed information for a specific ILM policy (delegates to ILMRenderer)."""
        return self.ilm_renderer.print_enhanced_ilm_policy_detail(
            policy_name, show_all_indices
        )

    def print_enhanced_ilm_explain(self, index_name):
        """Display ILM explain for specific index (delegates to ILMRenderer)."""
        return self.ilm_renderer.print_enhanced_ilm_explain(index_name)

    def print_enhanced_ilm_errors(self):
        """Display indices with ILM errors (delegates to ILMRenderer)."""
        return self.ilm_renderer.print_enhanced_ilm_errors()

    def print_ilm_policy_index_patterns(self, policy_name, show_all=False):
        """Display unique index patterns for a specific ILM policy (delegates to ILMRenderer)."""
        return self.ilm_renderer.print_ilm_policy_index_patterns(policy_name, show_all)

    def _get_phase_icon(self, phase):
        """Get icon for ILM phase (delegates to ILMRenderer)."""
        return self.ilm_renderer._get_phase_icon(phase)

    def create_ilm_policy(self, policy_name, policy_body):
        """Create an ILM policy (delegates to SettingsCommands)."""
        return self.settings_commands.create_ilm_policy(policy_name, policy_body)

    def delete_ilm_policy(self, policy_name):
        """Delete an ILM policy (delegates to SettingsCommands)."""
        return self.settings_commands.delete_ilm_policy(policy_name)

    def validate_ilm_policy_exists(self, policy_name):
        """
        Validate that an ILM policy exists.

        Args:
            policy_name (str): Name of the ILM policy to validate

        Returns:
            bool: True if policy exists, False otherwise
        """
        try:
            self.es.ilm.get_lifecycle(policy=policy_name)
            return True
        except Exception:
            return False

    def get_matching_indices(self, pattern):
        """
        Get all indices matching regex pattern with their current ILM status.

        Args:
            pattern (str): Regex pattern to match index names

        Returns:
            list: List of matching index dictionaries with current ILM status
        """
        import re
        from elasticsearch.exceptions import NotFoundError

        try:
            # Get all indices
            indices_response = self.es.cat.indices(
                format="json", h="index,health,status"
            )

            # Compile regex pattern
            compiled_pattern = re.compile(pattern, re.IGNORECASE)

            matching_indices = []
            for index_info in indices_response:
                index_name = index_info["index"]
                if compiled_pattern.search(index_name):
                    # Get current ILM status for this index
                    current_policy = None
                    try:
                        ilm_response = self.es.ilm.explain_lifecycle(index=index_name)
                        if (
                            "indices" in ilm_response
                            and index_name in ilm_response["indices"]
                        ):
                            current_policy = ilm_response["indices"][index_name].get(
                                "policy"
                            )
                    except (NotFoundError, Exception):
                        # Index might not have ILM or API might not be available
                        current_policy = None

                    matching_indices.append(
                        {
                            "name": index_name,
                            "current_policy": current_policy,
                            "health": index_info.get("health", "unknown"),
                            "status": index_info.get("status", "unknown"),
                        }
                    )

            return matching_indices

        except Exception as e:
            print(f"Error getting matching indices for pattern '{pattern}': {str(e)}")
            return []

    def get_indices_for_ilm_policy(self, policy_name):
        """
        Return indices currently assigned the given ILM policy, shaped for
        set_ilm_policy_for_indices (name + current_policy).

        Returns:
            tuple: (list of index dicts, error_message or None)
        """
        detail = self.get_ilm_policy_detail(policy_name)
        if not isinstance(detail, dict):
            return [], "Invalid policy detail response from cluster"
        if "error" in detail:
            return [], detail["error"]
        if policy_name not in detail:
            return [], f"Policy '{policy_name}' not found"
        using = detail[policy_name].get("using_indices", [])
        out = [
            {"name": u["name"], "current_policy": policy_name} for u in using
        ]
        return out, None

    def set_ilm_policy_for_indices(
        self,
        indices,
        policy_name,
        dry_run=False,
        max_concurrent=5,
        continue_on_error=False,
    ):
        """
        Set ILM policy for multiple indices with concurrent processing.

        Args:
            indices (list): List of index dictionaries
            policy_name (str): Name of the ILM policy to set
            dry_run (bool): If True, only simulate the operation
            max_concurrent (int): Maximum number of concurrent operations
            continue_on_error (bool): Whether to continue on individual failures

        Returns:
            dict: Results with successful, failed, and skipped operations
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from rich.progress import Progress, TaskID
        import time

        results = {
            "successful": [],
            "failed": [],
            "skipped": [],
            "total_processed": 0,
            "start_time": time.time(),
        }

        def set_policy_single(index_info):
            index_name = index_info["name"]
            current_policy = index_info["current_policy"]

            if current_policy == policy_name:
                return {
                    "index": index_name,
                    "status": "skipped",
                    "reason": f"Already has policy {policy_name}",
                }

            if dry_run:
                return {
                    "index": index_name,
                    "status": "would_set",
                    "new_policy": policy_name,
                    "current_policy": current_policy,
                }

            try:
                # Set ILM policy using index settings API
                self.es.indices.put_settings(
                    index=index_name, body={"index.lifecycle.name": policy_name}
                )
                return {
                    "index": index_name,
                    "status": "success",
                    "new_policy": policy_name,
                    "previous_policy": current_policy,
                }
            except Exception as e:
                return {
                    "index": index_name,
                    "status": "failed",
                    "error": str(e),
                    "target_policy": policy_name,
                    "current_policy": current_policy,
                }

        # Process with progress tracking
        with Progress() as progress:
            operation_name = (
                f"Simulating policy assignment ({policy_name})..."
                if dry_run
                else f"Setting ILM policy ({policy_name})..."
            )
            task = progress.add_task(operation_name, total=len(indices))

            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {
                    executor.submit(set_policy_single, idx): idx for idx in indices
                }

                for future in as_completed(futures):
                    result = future.result()
                    results["total_processed"] += 1

                    if result["status"] in ["success", "would_set"]:
                        results["successful"].append(result)
                    elif result["status"] == "failed":
                        results["failed"].append(result)
                        if not continue_on_error and not dry_run:
                            # Cancel remaining operations
                            for remaining_future in futures:
                                remaining_future.cancel()
                            break
                    else:
                        results["skipped"].append(result)

                    progress.advance(task)

        results["end_time"] = time.time()
        results["duration"] = results["end_time"] - results["start_time"]
        return results

    def remove_ilm_policy_from_indices(
        self,
        indices,
        dry_run=False,
        max_concurrent=5,
        continue_on_error=True,
    ):
        """
        Remove ILM policy from multiple indices with concurrent processing.

        Args:
            indices (list): List of index names (strings) or index dictionaries
            dry_run (bool): If True, only simulate the operation
            max_concurrent (int): Maximum number of concurrent operations
            continue_on_error (bool): Whether to continue on individual failures

        Returns:
            dict: Results with successful, failed, and skipped operations
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from rich.progress import Progress, TaskID
        import time

        results = {
            "successful": [],
            "failed": [],
            "skipped": [],
            "total_processed": 0,
            "start_time": time.time(),
        }

        def remove_policy_single(index_name):
            # Handle both string index names and dict objects
            if isinstance(index_name, dict):
                index_name = index_name.get("name", index_name.get("index", str(index_name)))

            try:
                # First check if index has an ILM policy
                explain_result = self.es.ilm.explain_lifecycle(index=index_name)
                index_info = explain_result.get("indices", {}).get(index_name, {})

                # Check if index is managed by ILM
                is_managed = index_info.get("managed", False)
                current_policy = index_info.get("policy", None)

                if not is_managed or not current_policy:
                    return {
                        "index": index_name,
                        "status": "skipped",
                        "reason": "No ILM policy attached",
                        "action": "remove_policy",
                    }

                if dry_run:
                    return {
                        "index": index_name,
                        "status": "would_remove",
                        "action": "remove_policy",
                        "current_policy": current_policy,
                    }

                # Remove ILM policy - use settings API which works for all index types
                # including data stream backing indices
                try:
                    # Try using ilm.remove_policy first (preferred method)
                    self.es.ilm.remove_policy(index=index_name)
                except Exception as ilm_error:
                    # If that fails (e.g., for data stream indices), use settings API
                    if "index_not_found_exception" in str(ilm_error):
                        # Remove ILM policy via settings API - works for data stream indices
                        self.es.indices.put_settings(
                            index=index_name,
                            body={
                                "index": {
                                    "lifecycle": {
                                        "name": None
                                    }
                                }
                            }
                        )
                    else:
                        raise

                return {
                    "index": index_name,
                    "status": "success",
                    "action": "removed_policy",
                    "removed_policy": current_policy,
                }
            except Exception as e:
                error_msg = str(e)
                return {
                    "index": index_name,
                    "status": "failed",
                    "error": error_msg,
                    "action": "remove_policy",
                }

        # Process with progress tracking
        with Progress() as progress:
            operation_name = (
                "Simulating policy removal..."
                if dry_run
                else "Removing ILM policies..."
            )
            task = progress.add_task(operation_name, total=len(indices))

            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {
                    executor.submit(remove_policy_single, idx): idx for idx in indices
                }

                for future in as_completed(futures):
                    result = future.result()
                    results["total_processed"] += 1

                    if result["status"] in ["success", "would_remove"]:
                        results["successful"].append(result)
                    elif result["status"] == "failed":
                        results["failed"].append(result)
                        if not continue_on_error and not dry_run:
                            # Cancel remaining operations
                            for remaining_future in futures:
                                remaining_future.cancel()
                            break
                    else:
                        results["skipped"].append(result)

                    progress.advance(task)

        results["end_time"] = time.time()
        results["duration"] = results["end_time"] - results["start_time"]
        return results

    def display_ilm_bulk_operation_results(self, results, operation_type):
        """
        Display results of bulk ILM operations in formatted panels.

        Args:
            results (dict): Results from bulk ILM operation
            operation_type (str): Type of operation performed
        """
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich.columns import Columns

        # Determine if this was a dry run
        is_dry_run = any(
            item.get("status", "").startswith("would_")
            for item in results["successful"]
        )

        # Create summary statistics
        total = results["total_processed"]
        successful = len(results["successful"])
        failed = len(results["failed"])
        skipped = len(results["skipped"])
        duration = results.get("duration", 0)

        # Create summary table
        summary_table = Table.grid(padding=(0, 1))
        summary_table.add_column(style="bold white", no_wrap=True)
        summary_table.add_column(style="bold cyan")

        operation_display = (
            f"🔍 {operation_type} (DRY RUN)" if is_dry_run else f"✅ {operation_type}"
        )
        summary_table.add_row("🚀 Operation:", operation_display)
        summary_table.add_row("📊 Total Processed:", str(total))
        summary_table.add_row("✅ Successful:", str(successful))
        summary_table.add_row("❌ Failed:", str(failed))
        summary_table.add_row("💤 Skipped:", str(skipped))
        summary_table.add_row("🕐 Duration:", f"{duration:.2f}s")

        # Create results details table if there are results to show
        details_table = Table(show_header=True, header_style="bold magenta")
        details_table.add_column("Index", style="cyan", no_wrap=True)
        details_table.add_column("Status", style="green")
        details_table.add_column("Details", style="yellow")

        # Add successful operations (all)
        for item in results["successful"]:
            status_icon = "🔍" if item["status"].startswith("would_") else "✅"
            status_text = f"{status_icon} {item['status'].replace('_', ' ').title()}"

            details = ""
            if "removed_policy" in item:
                details = f"Removed: {item['removed_policy']}"
            elif "new_policy" in item:
                details = f"Set: {item['new_policy']}"
                if item.get("previous_policy"):
                    details += f" (was: {item['previous_policy']})"
            elif "policy" in item:
                details = f"Would remove: {item['policy']}"

            details_table.add_row(item["index"], status_text, details)

        # Add failed operations
        for item in results["failed"]:
            details_table.add_row(
                item["index"],
                "❌ Failed",
                item.get("error", "Unknown error")[:50] + "..."
                if len(item.get("error", "")) > 50
                else item.get("error", "Unknown error"),
            )

        # Add skipped operations (all)
        for item in results["skipped"]:
            details_table.add_row(
                item["index"], "💤 Skipped", item.get("reason", "Unknown reason")
            )

        # All results are now shown, no truncation needed

        # Create panels
        summary_panel = Panel(
            summary_table,
            title="[bold cyan]📊 Operation Summary[/bold cyan]",
            border_style="green"
            if failed == 0
            else "yellow"
            if failed < successful
            else "red",
            padding=(1, 2),
        )

        details_panel = Panel(
            details_table,
            title="[bold cyan]📋 Operation Details[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )

        # Display results
        print()
        print(summary_panel)

        total_available = (
            len(results["successful"])
            + len(results["failed"])
            + len(results["skipped"])
        )
        if total_available > 0:
            print(details_panel)

        # Show warnings or errors
        if failed > 0 and not is_dry_run:
            warning_text = Text()
            warning_text.append("🔶  Some operations failed. ", style="bold yellow")
            warning_text.append(
                "Use --continue-on-error to process all indices even when some fail.",
                style="dim",
            )

            warning_panel = Panel(
                warning_text,
                title="[bold yellow]🔶  Warning[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
            print(warning_panel)

        print()

    def check_no_replica_indices(self):
        """Check for indices with no replicas (delegates to HealthCommands)."""
        return self.health_commands.check_no_replica_indices()

    def check_large_shards(self, max_size_gb=50):
        """Check for large shards (delegates to HealthCommands)."""
        return self.health_commands.check_large_shards(max_size_gb)

    def perform_cluster_health_checks(self, max_shard_size_gb=50, skip_ilm=False):
        """Perform comprehensive cluster health checks (delegates to HealthCommands)."""
        return self.health_commands.perform_cluster_health_checks(
            max_shard_size_gb, skip_ilm
        )

    def print_multi_cluster_health_comparison(
        self, config_file, group_name, output_format="table"
    ):
        """Display health comparison for all clusters in a group (delegates to HealthCommands)."""
        return self.health_commands.print_multi_cluster_health_comparison(
            config_file, group_name, output_format
        )

    def display_cluster_health_report(self, check_results):
        """Display comprehensive cluster health report (delegates to HealthHandler)."""
        # Import health handler here to avoid circular imports
        from handlers.health_handler import HealthHandler

        health_handler = HealthHandler(self, None, self.console, None, None, None)
        return health_handler.display_cluster_health_report(check_results)


# ---- End of Class Library above.
