"""
Health dashboard and panel rendering functionality.

This module handles the rendering of health-related displays including:
- Cluster health dashboard
- Cluster overview panels
- Node information panels
- Shard status panels
- Performance metrics panels
"""

from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from .style_system import StyleSystem


class HealthRenderer:
    """
    Renderer for health dashboard and panel displays.

    This class extracts health display methods from the main ElasticsearchClient,
    providing a focused interface for health visualization operations.
    """

    def __init__(self, theme_manager, es_client=None):
        """
        Initialize the HealthRenderer.

        Args:
            theme_manager: Theme manager instance for styling
            es_client: ElasticsearchClient instance (optional, for delegation)
        """
        self.theme_manager = theme_manager
        self.style_system = StyleSystem(theme_manager) if theme_manager else None
        self.es_client = es_client
        self.console = Console()

    def print_stylish_health_dashboard(self, health_data: Dict[str, Any],
                                     include_snapshots: bool = True,
                                     snapshot_repo: Optional[str] = None,
                                     recovery_status: Optional[Dict[str, Any]] = None) -> None:
        """
        Print a stylish health dashboard with multiple panels.

        Args:
            health_data: Cluster health data dictionary
            include_snapshots: Whether to include snapshots panel
            snapshot_repo: Snapshot repository name for snapshots panel
            recovery_status: Recovery status information for performance panel
        """
        from rich.table import Table
        from rich.text import Text

        # Get theme styles and style system
        styles = self.theme_manager.get_theme_styles()
        style_system = self.style_system

        # Get cluster status and set semantic styling
        status = health_data.get('status', health_data.get('cluster_status', 'unknown'))
        if status == 'green':
            status_style = "success"
            status_icon = "🟢"
        elif status == 'yellow':
            status_style = "warning"
            status_icon = "🟡"
        elif status == 'red':
            status_style = "error"
            status_icon = "🔴"
        else:
            status_style = "muted"
            status_icon = "⚪"

        # Use pre-gathered data (should always be available from _handle_health_dashboard)
        if recovery_status is None:
            recovery_status = health_data.get('_recovery_status', [])
        allocation_issues = health_data.get('_allocation_issues', [])

        # Create the main title with cluster name and status
        cluster_name = health_data.get('cluster_name', 'Unknown')
        cluster_version = health_data.get('cluster_version', 'Unknown')

        # Handle version formatting for header
        if isinstance(cluster_version, dict):
            version_display = cluster_version.get('number', 'Unknown')
        else:
            version_display = cluster_version

        # Create title text with semantic styling
        if style_system:
            title_text = Text()
            title_text.append("🔍 ", style=style_system.get_semantic_style("info"))
            title_text.append("Elasticsearch Cluster Health", style=style_system.get_semantic_style("primary"))
        else:
            title_text = Text()
            title_text.append("🔍 ", style="bold cyan")
            title_text.append("Elasticsearch Cluster Health", style="bold white")

        # Status header with semantic styling
        if style_system:
            status_header = Text()
            status_header.append(f"{status_icon} ", style=style_system.get_semantic_style(status_style))
            status_header.append(f"Cluster: ", style=style_system.get_semantic_style("primary"))
            status_header.append(f"{cluster_name}", style=style_system.get_semantic_style("primary"))

            # Add version information if available
            if version_display != 'Unknown':
                status_header.append(f" (v{version_display})", style=style_system.get_semantic_style("info"))
        else:
            # Fallback styling
            theme_color = styles.get('border_style', 'white')
            status_color = "bright_green" if status == 'green' else "bright_yellow" if status == 'yellow' else "bright_red" if status == 'red' else "dim"
            status_header = Text()
            status_header.append(f"{status_icon} ", style=f"bold {status_color}")
            status_header.append(f"Cluster: ", style="bold white")
            status_header.append(f"{cluster_name}", style=f"bold {theme_color}")

            # Add version information if available
            if version_display != 'Unknown':
                status_header.append(f" (v{version_display})", style=f"bold cyan")

        # Add status to header with semantic styling
        if style_system:
            status_header.append(f" • Status: ", style=style_system.get_semantic_style("primary"))
            status_header.append(f"{status.upper()}", style=style_system.get_semantic_style(status_style))
        else:
            status_color = "bright_green" if status == 'green' else "bright_yellow" if status == 'yellow' else "bright_red" if status == 'red' else "dim"
            status_header.append(f" • Status: ", style="bold white")
            status_header.append(f"{status.upper()}", style=f"bold {status_color}")

        # Determine panel border color based on cluster health status
        theme_color = styles.get('border_style', 'white')  # Fallback for unknown/error
        if status == 'green':
            panel_color = 'green'
        elif status == 'yellow':
            panel_color = 'yellow'
        elif status == 'red':
            panel_color = 'red'
        else:
            panel_color = theme_color  # Default to theme color if status unknown

        cluster_panel = self._create_cluster_overview_panel(health_data, panel_color)
        nodes_panel = self._create_nodes_panel(health_data, panel_color)
        shards_panel = self._create_shards_panel(health_data, panel_color)
        performance_panel = self._create_performance_panel(health_data, panel_color, recovery_status)

        # Create snapshot panel if configured and include_snapshots is True
        if include_snapshots:
            # Get snapshots data if we have access to the client
            snapshots_data = health_data.get('_snapshots', [])
            if not snapshot_repo and self.es_client:
                snapshot_repo = getattr(self.es_client, 'snapshot_repo', None)
            snapshots_panel = self._create_snapshots_panel(panel_color, snapshot_repo, snapshots_data)
        else:
            snapshots_panel = None

        # Create allocation issues panel if there are issues
        allocation_panel = None
        if allocation_issues:
            if self.es_client and hasattr(self.es_client, 'allocation_renderer'):
                allocation_panel = self.es_client.allocation_renderer.create_allocation_issues_panel(allocation_issues)

        # Create the panel grid first to measure its actual width
        grid = Table.grid(padding=0)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="left", ratio=1)

        # Add the panel rows
        grid.add_row(cluster_panel, nodes_panel)
        grid.add_row("", "")  # Minimal spacing
        grid.add_row(shards_panel, performance_panel)
        grid.add_row("", "")  # Minimal spacing

        # Add bottom row based on what panels we have
        if include_snapshots and snapshots_panel:
            if allocation_panel:
                grid.add_row(snapshots_panel, allocation_panel)
            else:
                grid.add_row(snapshots_panel, "")
        elif allocation_panel:
            grid.add_row(allocation_panel, "")

        # Calculate actual grid width for better centering
        actual_grid_width = 94

        # Create a header table that matches the actual grid width
        header_table = Table.grid()
        header_table.add_column(justify="center", width=actual_grid_width)
        header_table.add_row("")
        header_table.add_row(title_text)
        header_table.add_row(status_header)
        header_table.add_row("")

        # Print header then grid
        self.console.print(header_table)
        self.console.print(grid)
        self.console.print()

    def _create_cluster_overview_panel(self, health_data: Dict[str, Any], theme_color: str) -> Panel:
        """
        Create cluster overview panel.

        Args:
            health_data: Cluster health data dictionary
            theme_color: Theme color for panel styling

        Returns:
            Panel: Cluster overview panel
        """
        # Get theme styles
        styles = self.theme_manager.get_theme_styles()

        # Create inner table for clean label-value pairs
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column()

        # Basic cluster info
        cluster_name = health_data.get('cluster_name', 'Unknown')
        status = health_data.get('status', 'unknown').upper()

        # Get status color from theme
        if status == 'GREEN':
            status_style = styles.get('health_styles', {}).get('green', {}).get('text', 'bold green')
        elif status == 'YELLOW':
            status_style = styles.get('health_styles', {}).get('yellow', {}).get('text', 'bold yellow')
        else:
            status_style = styles.get('health_styles', {}).get('red', {}).get('text', 'bold red')

        table.add_row("🏥 Cluster:", cluster_name)
        table.add_row("📊 Status:", Text(status, style=status_style))

        # Version information
        cluster_version = health_data.get('version', {}).get('number', 'Unknown')
        build_hash = health_data.get('version', {}).get('build_hash', '')

        if cluster_version != 'Unknown':
            # Handle version if it's a dict (extract just the number)
            if isinstance(cluster_version, dict):
                version_text = f"v{cluster_version.get('number', 'Unknown')}"
                if build_hash or cluster_version.get('build_hash'):
                    build_hash = build_hash or cluster_version.get('build_hash', '')
                    version_text += f" (build: {build_hash[:8]}...)" if len(build_hash) > 8 else f" (build: {build_hash})"
            else:
                version_text = f"v{cluster_version}"
                if build_hash:
                    version_text += f" (build: {build_hash})"
            table.add_row("🔧 ES Version:", version_text)

            # Add mixed version warning if applicable
            if health_data.get('mixed_versions', False):
                table.add_row("🔶 Version:", "Mixed versions detected!")

        # Get current master node - use pre-gathered data
        master_node = health_data.get('_master_node', 'Unknown')
        if master_node != 'Unknown':
            # Remove "-master" suffix from the display name
            display_name = master_node[:-7] if master_node.endswith('-master') else master_node
            table.add_row("👑 Master Node:", display_name)
        else:
            table.add_row("👑 Master Node:", "Unknown")

        table.add_row("💻 Total Nodes:", str(health_data.get('number_of_nodes', 0)))
        table.add_row("💾 Data Nodes:", str(health_data.get('number_of_data_nodes', 0)))

        # Create progress bar for shard health
        active_percent = float(health_data.get('active_shards_percent', 100.0))
        # If active_shards_percent is not available, calculate it
        if active_percent == 0.0 or 'active_shards_percent' not in health_data:
            total_shards = health_data.get('active_shards', 0) + health_data.get('unassigned_shards', 0)
            active_shards = health_data.get('active_shards', 0)
            if total_shards > 0:
                active_percent = (active_shards / total_shards) * 100
            else:
                active_percent = 100.0

        width = 12
        filled = int((active_percent / 100) * width)
        empty = width - filled

        if active_percent >= 95:
            bar_char = "🟢"
        elif active_percent >= 80:
            bar_char = "🟡"
        else:
            bar_char = "🔴"

        progress_bar = bar_char * filled + "⚪" * empty
        shard_health = f"{progress_bar} {active_percent:.1f}%"

        table.add_row("📊 Shard Health:", shard_health)

        return Panel(
            table,
            title=f"[{styles.get('panel_styles', {}).get('title', 'bold cyan')}]📋 Cluster Overview[/{styles.get('panel_styles', {}).get('title', 'bold cyan')}]",
            border_style=styles.get('border_style', theme_color),
            padding=(1, 2)
        )

    def _create_nodes_panel(self, health_data: Dict[str, Any], theme_color: str) -> Panel:
        """
        Create nodes information panel.

        Args:
            health_data: Cluster health data dictionary
            theme_color: Theme color for panel styling

        Returns:
            Panel: Nodes information panel
        """
        # Get theme styles
        styles = self.theme_manager.get_theme_styles()

        # Create inner table for clean label-value pairs
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column()

        # Calculate node info
        total_nodes = health_data.get('number_of_nodes', 0)
        data_nodes = health_data.get('number_of_data_nodes', 0)

        # Get detailed node counts - use pre-gathered data if available
        nodes = health_data.get('_nodes')
        if nodes is not None:
            try:
                # Count different node types based on roles
                master_only_nodes = len([node for node in nodes if 'master' in node['roles'] and not any(role.startswith('data') for role in node['roles'])])
                # Client nodes are coordinating nodes (no data roles, no master role)
                client_nodes = len([node for node in nodes if 'master' not in node['roles'] and not any(role.startswith('data') for role in node['roles'])])
                # Other nodes are master-only nodes (since client nodes are shown separately)
                other_nodes = master_only_nodes
            except Exception:
                # Fallback if we can't process detailed node info
                client_nodes = 0
                other_nodes = total_nodes - data_nodes
        else:
            # Use simple calculation if detailed node data is not available
            client_nodes = 0
            other_nodes = total_nodes - data_nodes

        # Add node info rows
        table.add_row("💻 Total Nodes:", Text(str(total_nodes), style=styles.get('value_style', 'bold white')))
        table.add_row("📚 Data Nodes:", Text(str(data_nodes), style=styles.get('success_style', 'bold green')))
        if other_nodes > 0:
            table.add_row("🔩 Master Nodes:", Text(str(other_nodes), style=styles.get('warning_style', 'bold yellow')))
        if client_nodes > 0:
            table.add_row("🔗 Client Nodes:", Text(str(client_nodes), style=styles.get('info_style', 'bold cyan')))

        # Create data node ratio with progress bar
        if total_nodes > 0:
            data_ratio = (data_nodes / total_nodes) * 100
            width = 15
            filled = int((data_ratio / 100) * width)
            empty = width - filled

            # Create ratio text with progress bar using theme-aware colors
            ratio_text = Text()
            # Use theme-aware progress bar colors
            progress_style = styles.get('success_style', 'bold green')
            empty_style = styles.get('muted_style', 'dim')

            ratio_text.append("█" * filled, style=progress_style)
            ratio_text.append("░" * empty, style=empty_style)
            ratio_text.append(f" {data_ratio:.0f}%", style=progress_style)

            table.add_row("📈 Data Ratio:", ratio_text)

        return Panel(
            table,
            title=f"[{styles.get('panel_styles', {}).get('title', 'bold green')}]💻 Node Information[/{styles.get('panel_styles', {}).get('title', 'bold green')}]",
            border_style=styles.get('border_style', theme_color),
            padding=(1, 2)
        )

    def _create_shards_panel(self, health_data: Dict[str, Any], theme_color: str) -> Panel:
        """
        Create shards information panel.

        Args:
            health_data: Cluster health data dictionary
            theme_color: Theme color for panel styling

        Returns:
            Panel: Shards information panel
        """
        # Get theme styles
        styles = self.theme_manager.get_theme_styles()

        # Create inner table for clean label-value pairs
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column()

        # Shard metrics
        active_primary = health_data.get('active_primary_shards', 0)
        active_total = health_data.get('active_shards', 0)
        unassigned = health_data.get('unassigned_shards', 0)
        replicas = active_total - active_primary

        # Add shard info rows using semantic theme styles
        primary_style = styles.get('type_styles', {}).get('primary', {}).get('text', 'bright_white')
        replica_style = styles.get('type_styles', {}).get('replica', {}).get('text', 'bright_white')
        normal_style = styles.get('row_styles', {}).get('normal', 'bright_white')

        table.add_row("🟢 Primary:", Text(f"{active_primary:,}", style=primary_style))
        table.add_row("🔵 Total Active:", Text(f"{active_total:,}", style=normal_style))
        table.add_row("🔄 Replicas:", Text(f"{replicas:,}", style=replica_style))

        # Calculate shards per data node (only data nodes hold shards)
        data_nodes = health_data.get('number_of_data_nodes', 1)  # Avoid division by zero
        if data_nodes > 0:
            shards_per_node = active_total / data_nodes
            table.add_row("🔢 Shards/Node:", Text(f"{shards_per_node:.1f}", style=normal_style))

        # Unassigned shards status using health styles
        if unassigned > 0:
            unassigned_style = styles.get('health_styles', {}).get('red', {}).get('text', 'bold red')
            table.add_row("🔴 Unassigned:", Text(f"{unassigned:,}", style=unassigned_style))
        else:
            assigned_style = styles.get('health_styles', {}).get('green', {}).get('text', 'bold green')
            table.add_row("✅ Status:", Text("All assigned!", style=assigned_style))

        return Panel(
            table,
            title=f"[{styles.get('panel_styles', {}).get('title', 'bold blue')}]🔄 Shard Status[/{styles.get('panel_styles', {}).get('title', 'bold blue')}]",
            border_style=styles.get('border_style', theme_color),
            padding=(1, 2)
        )

    def _create_performance_panel(self, health_data: Dict[str, Any], theme_color: str,
                                recovery_status: Optional[Dict[str, Any]] = None) -> Panel:
        """
        Create performance metrics panel.

        Args:
            health_data: Cluster health data dictionary
            theme_color: Theme color for panel styling
            recovery_status: Recovery status information (optional)

        Returns:
            Panel: Performance metrics panel
        """
        # Get theme styles
        styles = self.theme_manager.get_theme_styles()

        # Create inner table with 3 columns: Label, Value, Status
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(style=styles.get('row_styles', {}).get('normal', 'bold white'), justify="right", width=16)
        table.add_column(style="", no_wrap=True)

        pending_tasks = health_data.get('number_of_pending_tasks', 0)
        in_flight = health_data.get('number_of_in_flight_fetch', 0)
        delayed_unassigned = health_data.get('delayed_unassigned_shards', 0)

        # Pending tasks
        if pending_tasks == 0:
            pending_status = Text("✅", style=styles.get('success_style', 'bold green'))
        else:
            pending_status = Text("🔶", style=styles.get('warning_style', 'bold yellow'))
        table.add_row("⏳ Pending Tasks:", str(pending_tasks), pending_status)

        # In-flight fetches
        if in_flight == 0:
            inflight_status = Text("✅", style=styles.get('success_style', 'bold green'))
        elif in_flight < 5:
            inflight_status = Text("📊", style=styles.get('info_style', 'bold blue'))
        else:
            inflight_status = Text("🔶", style=styles.get('warning_style', 'bold yellow'))
        table.add_row("🔄 In-Flight:", str(in_flight), inflight_status)

        # Recovery jobs
        if recovery_status:
            recovery_count = len(recovery_status)
            total_shards = sum(len(shards) for shards in recovery_status.values())
            recovery_value = f"{recovery_count}i, {total_shards}s"
            recovery_status_icon = Text("⚡", style=styles.get('warning_style', 'bold orange'))
        else:
            recovery_value = "0"
            recovery_status_icon = Text("✅", style=styles.get('success_style', 'bold green'))
        table.add_row("🔧 Recovery Jobs:", recovery_value, recovery_status_icon)

        # Delayed unassigned shards
        if delayed_unassigned == 0:
            delayed_status = Text("✅", style=styles.get('success_style', 'bold green'))
        else:
            delayed_status = Text("🔶", style=styles.get('warning_style', 'bold yellow'))
        table.add_row("🕐 Delayed:", str(delayed_unassigned), delayed_status)

        # Overall performance indicator
        has_recovery = recovery_status and len(recovery_status) > 0
        if pending_tasks == 0 and delayed_unassigned == 0 and not has_recovery:
            status_text = "OPTIMAL"
            status_icon = Text("✨", style=styles.get('success_style', 'bold green'))
        elif pending_tasks < 10 and delayed_unassigned < 5 and (not has_recovery or len(recovery_status) < 3):
            status_text = "GOOD"
            status_icon = Text("👍", style=styles.get('warning_style', 'bold yellow'))
        else:
            status_text = "NEEDS ATTENTION"
            status_icon = Text("🔶", style=styles.get('error_style', 'bold red'))

        # Add overall status
        table.add_row("🎯 Overall:", status_text, status_icon)

        return Panel(
            table,
            title=f"[{styles.get('panel_styles', {}).get('title', 'bold yellow')}]⚡ Performance[/{styles.get('panel_styles', {}).get('title', 'bold yellow')}]",
            border_style=styles.get('border_style', theme_color),
            padding=(1, 2),
            width=50
        )

    def _create_snapshots_panel(self, theme_color: str, snapshot_repo: Optional[str] = None,
                              snapshots: Optional[Dict[str, Any]] = None) -> Panel:
        """
        Create snapshots information panel (delegates to SnapshotRenderer if available).

        Args:
            theme_color: Theme color for panel styling
            snapshot_repo: Snapshot repository name
            snapshots: Snapshots data (optional)

        Returns:
            Panel: Snapshots information panel
        """
        # If we have access to the client's snapshot renderer, use it
        if self.es_client and hasattr(self.es_client, 'snapshot_renderer'):
            return self.es_client.snapshot_renderer.create_snapshots_panel(theme_color, snapshot_repo, snapshots)

        # Otherwise, create a simple placeholder panel
        styles = self.theme_manager.get_theme_styles()

        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column()

        if snapshot_repo:
            table.add_row("📦 Repository:", snapshot_repo)
        else:
            table.add_row("📦 Repository:", "Not configured")

        table.add_row("📸 Snapshots:", "N/A")
        table.add_row("📊 Status:", "Check configuration")

        return Panel(
            table,
            title=f"[{styles.get('panel_styles', {}).get('title', 'bold magenta')}]📸 Snapshots[/{styles.get('panel_styles', {}).get('title', 'bold magenta')}]",
            border_style=styles.get('border_style', theme_color),
            padding=(1, 2)
        )

    def print_enhanced_current_master(self, master_node_id: str, nodes_data: List[Dict[str, Any]],
                                    health_data: Dict[str, Any]) -> None:
        """
        Print enhanced current master information with Rich formatting.

        Args:
            master_node_id: ID of the master node
            nodes_data: List of node information
            health_data: Cluster health data
        """
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table as InnerTable

        try:
            master_node = None

            # Find the master node details
            for node in nodes_data:
                if node.get('name') == master_node_id:
                    master_node = node
                    break

            if not master_node:
                # Fallback if we can't find detailed info
                simple_panel = Panel(
                    Text(f"👑 {master_node_id}", style="bold yellow", justify="center"),
                    title="👑 Current Cluster Master",
                    border_style="cyan",
                    padding=(1, 2)
                )
                print()
                self.console.print(simple_panel)
                return

            # Create title panel
            title_panel = Panel(
                Text("👑 Current Cluster Master", style="bold cyan", justify="center"),
                subtitle=f"Active master node: {master_node_id}",
                border_style="cyan",
                padding=(1, 2)
            )

            # Master node details panel
            master_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            master_table.add_column("Label", style="bold", no_wrap=True)
            master_table.add_column("Icon", justify="left", width=3)
            master_table.add_column("Value", no_wrap=True)

            # Basic information
            name = master_node.get('name', 'Unknown')
            hostname = master_node.get('hostname', 'Unknown')
            node_id = master_node.get('node', 'Unknown')
            roles = master_node.get('roles', [])

            master_table.add_row("Node Name:", "📛", name)
            master_table.add_row("Hostname:", "🌐", hostname)
            if node_id != 'Unknown':
                master_table.add_row("Node ID:", "🆔", node_id[:16] + "..." if len(node_id) > 16 else node_id)

            # Role information
            master_table.add_row("Master Role:", "👑", "✅ Active Master")

            # Check if it has other roles
            other_roles = []
            if any(role.startswith('data') for role in roles):
                other_roles.append("💾 Data")
            if 'ingest' in roles:
                other_roles.append("🔄 Ingest")

            if other_roles:
                master_table.add_row("Additional Roles:", "🔩", " + ".join(other_roles))
            else:
                master_table.add_row("Node Type:", "🔧", "Dedicated Master")

            master_details_panel = Panel(
                master_table,
                title="📋 Master Node Details",
                border_style="cyan",
                padding=(1, 2)
            )

            # Cluster status panel
            try:
                status = health_data.get('status', 'unknown').upper()

                # Determine status styling
                if status == 'GREEN':
                    status_icon = "🟢"
                    status_color = "green"
                elif status == 'YELLOW':
                    status_icon = "🟡"
                    status_color = "yellow"
                elif status == 'RED':
                    status_icon = "🔴"
                    status_color = "red"
                else:
                    status_icon = "⚪"
                    status_color = "cyan"

                cluster_name = health_data.get('cluster_name', 'Unknown')
                total_nodes = health_data.get('number_of_nodes', 0)
                data_nodes = health_data.get('number_of_data_nodes', 0)

                status_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                status_table.add_column("Label", style="bold", no_wrap=True)
                status_table.add_column("Icon", justify="left", width=3)
                status_table.add_column("Value", no_wrap=True)

                status_table.add_row("Cluster Name:", "🏢", cluster_name)
                status_table.add_row("Cluster Status:", status_icon, status)
                status_table.add_row("Total Nodes:", "💻", str(total_nodes))
                status_table.add_row("Data Nodes:", "💾", str(data_nodes))

                cluster_status_panel = Panel(
                    status_table,
                    title="📊 Cluster Status",
                    border_style=status_color,
                    padding=(1, 2)
                )

                # Display everything
                print()
                self.console.print(title_panel)
                print()
                self.console.print(Columns([master_details_panel, cluster_status_panel], expand=True))

            except Exception:
                # If we can't get cluster status, just show master details
                print()
                self.console.print(title_panel)
                print()
                self.console.print(master_details_panel)

        except Exception as e:
            self.console.print(f"[red]❌ Error retrieving master node details: {str(e)}[/red]")
