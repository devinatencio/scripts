"""
Nodes command processors extracted from ElasticsearchClient.

This module handles node-related operations including:
- Node information retrieval  
- Node statistics and performance metrics
- Node role management
- Node mapping and identification
"""

from typing import Dict, Any, Optional, List
from .base_command import BaseCommand


class NodesCommands(BaseCommand):
    """
    Command processor for node-related operations.
    
    This class extracts node management methods from the main ElasticsearchClient,
    providing a focused interface for node operations.
    """
    
    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'nodes'
    
    def get_nodes_fast(self) -> List[Dict[str, Any]]:
        """
        Get basic node information quickly for dashboard (minimal API calls).
        
        Returns:
            list: Basic node information without expensive details
        """
        try:
            # Only get basic node stats - skip detailed info and shard allocation
            stats = self.es_client.es.nodes.stats()
            node_stats = self.es_client.node_processor.parse_node_stats(stats)
            
            # Skip version info and shard allocation for speed
            # Just add minimal defaults
            for node in node_stats:
                node.update({
                    'version': 'N/A',  # Skip version lookup for speed
                    'build_hash': None,
                    'build_date': '',
                    'indices_count': 0  # Skip shard allocation lookup for speed
                })
            
            return sorted(node_stats, key=lambda x: x['name'])
            
        except Exception:
            return []
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """
        Get comprehensive node information with statistics and version details.
        
        Returns:
            list: Complete node information including performance metrics
        """
        try:
            # Get node statistics
            stats = self.es_client.es.nodes.stats()
            node_stats = self.es_client.node_processor.parse_node_stats(stats)
            
            # Get node info for versions
            try:
                info = self.es_client.es.nodes.info()
                node_info = {}
                
                # Handle response format differences
                if hasattr(info, 'body'):
                    nodes_data = info.body.get('nodes', {})
                elif hasattr(info, 'get'):
                    nodes_data = info.get('nodes', {})
                else:
                    nodes_data = info.get('nodes', {})
                
                for node_id, node_data in nodes_data.items():
                    # Extract port information from HTTP settings
                    http_info = node_data.get('http', {})
                    port = 9200  # Default port
                    
                    if http_info:
                        # Try to extract port from bound_address or publish_address
                        if 'bound_address' in http_info and http_info['bound_address']:
                            try:
                                address = http_info['bound_address'][0] if isinstance(http_info['bound_address'], list) else http_info['bound_address']
                                port = int(address.split(':')[-1])
                            except (ValueError, IndexError, AttributeError):
                                pass
                        elif 'publish_address' in http_info:
                            try:
                                port = int(http_info['publish_address'].split(':')[-1])
                            except (ValueError, IndexError, AttributeError):
                                pass
                    
                    node_info[node_id] = {
                        'version': node_data.get('version', 'unknown'),
                        'build_hash': node_data.get('build_hash'),
                        'build_date': node_data.get('build_date', ''),
                        'http_port': port
                    }
            except Exception:
                node_info = {}
            
            # Get actual indices per node by checking shard allocation
            try:
                # Get shard allocation information
                allocation_data = self.es_client.get_allocation_as_dict()
                node_indices_count = {}
                
                for allocation in allocation_data.values():
                    node_name = allocation.get('node')
                    if node_name and node_name != 'UNASSIGNED':
                        node_indices_count[node_name] = node_indices_count.get(node_name, 0) + 1
                        
            except Exception:
                node_indices_count = {}
            
            # Merge the data
            for node in node_stats:
                node_id = node.get('nodeid')
                node_name = node.get('name')
                
                # Add version and port info
                version_info = node_info.get(node_id, {})
                node.update({
                    'version': version_info.get('version', 'unknown'),
                    'build_hash': version_info.get('build_hash'),
                    'build_date': version_info.get('build_date', ''),
                    'http_port': version_info.get('http_port', 9200)
                })
                
                # Add actual indices count from shard allocation
                node['indices_count'] = node_indices_count.get(node_name, 0)
            
            return sorted(node_stats, key=lambda x: x['name'])
            
        except Exception as e:
            return []
    
    def get_all_nodes_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for all nodes.
        
        Returns:
            dict: All node statistics
        """
        try:
            stats = self.es_client.es.nodes.stats()
            
            # Handle response format differences
            if hasattr(stats, 'body'):
                return stats.body
            elif hasattr(stats, 'get'):
                return dict(stats)
            else:
                return stats
                
        except Exception as e:
            return {"error": f"Failed to get node stats: {str(e)}"}
    
    def get_nodes_info(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about nodes.
        
        Args:
            node_id: Specific node ID to get info for (optional)
            
        Returns:
            dict: Node information
        """
        try:
            if node_id:
                info = self.es_client.es.nodes.info(node_id=node_id)
            else:
                info = self.es_client.es.nodes.info()
            
            # Handle response format differences
            if hasattr(info, 'body'):
                return info.body
            elif hasattr(info, 'get'):
                return dict(info)
            else:
                return info
                
        except Exception as e:
            return {"error": f"Failed to get nodes info: {str(e)}"}
    
    def get_node_id_to_hostname_map(self) -> Dict[str, str]:
        """
        Create a mapping from node IDs to hostnames.
        
        Returns:
            dict: Mapping of node_id -> hostname
        """
        try:
            nodes_data = self.get_nodes()
            
            node_map = {}
            for node in nodes_data:
                node_id = node.get('nodeid')
                hostname = node.get('hostname', node.get('name', 'unknown'))
                if node_id:
                    node_map[node_id] = hostname
            
            return node_map
            
        except Exception:
            return {}
    
    def get_master_eligible_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all nodes that are eligible to be master.
        
        Returns:
            list: Master-eligible nodes
        """
        try:
            nodes_data = self.get_nodes()
            return self.es_client.node_processor.filter_nodes_by_role(nodes_data, 'master')
        except Exception:
            return []
    
    def get_data_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all data nodes.
        
        Returns:
            list: Data nodes
        """
        try:
            nodes_data = self.get_nodes()
            return self.es_client.node_processor.filter_nodes_by_role(nodes_data, 'data')
        except Exception:
            return []
    
    def get_ingest_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all ingest nodes.
        
        Returns:
            list: Ingest nodes
        """
        try:
            nodes_data = self.get_nodes()
            return self.es_client.node_processor.filter_nodes_by_role(nodes_data, 'ingest')
        except Exception:
            return []
    
    def get_node_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific node by name.
        
        Args:
            name: Node name to search for
            
        Returns:
            dict: Node information or None if not found
        """
        try:
            nodes_data = self.get_nodes()
            for node in nodes_data:
                if node.get('name') == name:
                    return node
            return None
        except Exception:
            return None
    
    def get_node_utilization_stats(self) -> Dict[str, Any]:
        """
        Get node utilization statistics including CPU, memory, disk.
        
        Returns:
            dict: Node utilization statistics
        """
        try:
            stats = self.get_all_nodes_stats()
            
            utilization_stats = {
                'total_nodes': 0,
                'nodes_details': [],
                'cluster_totals': {
                    'total_memory': 0,
                    'used_memory': 0,
                    'total_disk': 0,
                    'used_disk': 0
                }
            }
            
            nodes_data = stats.get('nodes', {})
            utilization_stats['total_nodes'] = len(nodes_data)
            
            for node_id, node_stats in nodes_data.items():
                node_detail = {
                    'node_id': node_id,
                    'name': node_stats.get('name', 'unknown'),
                    'host': node_stats.get('host', 'unknown')
                }
                
                # Memory stats
                jvm_mem = node_stats.get('jvm', {}).get('mem', {})
                if jvm_mem:
                    heap_max = jvm_mem.get('heap_max_in_bytes', 0)
                    heap_used = jvm_mem.get('heap_used_in_bytes', 0)
                    node_detail['memory'] = {
                        'heap_max': heap_max,
                        'heap_used': heap_used,
                        'heap_percent': int((heap_used / heap_max * 100)) if heap_max > 0 else 0
                    }
                    utilization_stats['cluster_totals']['total_memory'] += heap_max
                    utilization_stats['cluster_totals']['used_memory'] += heap_used
                
                # File system stats
                fs_stats = node_stats.get('fs', {}).get('total', {})
                if fs_stats:
                    total_bytes = fs_stats.get('total_in_bytes', 0)
                    available_bytes = fs_stats.get('available_in_bytes', 0)
                    used_bytes = total_bytes - available_bytes
                    node_detail['disk'] = {
                        'total': total_bytes,
                        'used': used_bytes,
                        'available': available_bytes,
                        'used_percent': int((used_bytes / total_bytes * 100)) if total_bytes > 0 else 0
                    }
                    utilization_stats['cluster_totals']['total_disk'] += total_bytes
                    utilization_stats['cluster_totals']['used_disk'] += used_bytes
                
                utilization_stats['nodes_details'].append(node_detail)
            
            return utilization_stats
            
        except Exception as e:
            return {"error": f"Failed to get node utilization stats: {str(e)}"}

    def print_enhanced_nodes_table(self, nodes, show_data_only=False):
        """Print enhanced nodes table with Rich formatting and statistics - ORIGINAL DESIGN"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table
        from rich.console import Console
        from rich import box

        console = Console()

        # Get theme styles with enhanced semantic styling
        # Use the theme manager from the es_client to get proper configuration
        theme_manager = self.es_client.theme_manager
        styles = theme_manager.get_theme_styles()
        
        # Use semantic style system from es_client
        style_system = self.es_client.style_system

        if not nodes:
            # Use semantic error styling
            if style_system:
                error_text = style_system.create_semantic_text("❌ No nodes data available", 'error')
                console.print(error_text)
            else:
                console.print("[red]❌ No nodes data available[/red]")
            return

        # Calculate statistics
        total_nodes = len(nodes)
        node_roles = {}
        master_eligible = 0
        data_nodes = 0
        client_nodes = 0
        ingest_nodes = 0

        # Get current master node
        try:
            current_master = self.get_master_node()
        except:
            current_master = "Unknown"

        # Analyze node roles
        for node in nodes:
            roles = node.get('roles', [])

            # Count by primary roles
            if 'master' in roles:
                master_eligible += 1
            if any(role.startswith('data') for role in roles):
                data_nodes += 1
            if 'ingest' in roles:
                ingest_nodes += 1
            if not any(role.startswith('data') for role in roles) and 'master' not in roles:
                client_nodes += 1

            # Track role combinations
            role_key = ', '.join(sorted(roles)) if roles else 'none'
            node_roles[role_key] = node_roles.get(role_key, 0) + 1

        # Create title panel with version information
        filter_text = " (Data Nodes Only)" if show_data_only else ""
        
        # Get cluster version and health info
        try:
            cluster_info = self.es_client.cluster_commands.get_cluster_info()
            cluster_name = cluster_info.get('cluster_name', 'Unknown')
            cluster_version = cluster_info.get('version', {}).get('number', 'Unknown')
            mixed_versions = False  # TODO: implement mixed version detection
        except Exception:
            cluster_name = 'Unknown'
            cluster_version = 'Unknown'
            mixed_versions = False

        # Get cluster health info
        try:
            health_info = self.es_client.cluster_commands.get_cluster_health(include_version=False)
            cluster_status = health_info.get('status', 'unknown').upper()
            active_shards = health_info.get('active_shards', 0)
            relocating_shards = health_info.get('relocating_shards', 0)
            unassigned_shards = health_info.get('unassigned_shards', 0)
            
            # Create health indicator
            if cluster_status == 'GREEN':
                health_indicator = "🟢"
            elif cluster_status == 'YELLOW':
                health_indicator = "🟡"
            elif cluster_status == 'RED':
                health_indicator = "🔴"
            else:
                health_indicator = "⚪"
        except Exception:
            cluster_status = 'UNKNOWN'
            health_indicator = "⚪"
            active_shards = relocating_shards = unassigned_shards = 0

        # Build enhanced title with version info - matching indices format
        if cluster_version != 'Unknown':
            nodes_title = f"💻  Elasticsearch Nodes: {cluster_name} (v{cluster_version})"
        else:
            nodes_title = f"💻  Elasticsearch Nodes: {cluster_name}"

        # Create colorized subtitle with theme-based styling for statistics
        from rich.text import Text
        subtitle_rich = Text()
        subtitle_rich.append("Total: ", style="default")
        subtitle_rich.append(str(total_nodes), style=style_system._get_style('semantic', 'info', 'cyan'))

        # Node breakdown
        subtitle_rich.append(" | Master: ", style="default")
        subtitle_rich.append(str(master_eligible), style=style_system._get_style('semantic', 'primary', 'bright_magenta'))
        subtitle_rich.append(" | Data: ", style="default")
        subtitle_rich.append(str(data_nodes), style=style_system._get_style('semantic', 'success', 'green'))
        subtitle_rich.append(" | Ingest: ", style="default")
        subtitle_rich.append(str(ingest_nodes), style=style_system._get_style('semantic', 'info', 'cyan'))
        if client_nodes > 0:
            subtitle_rich.append(" | Client: ", style="default")
            subtitle_rich.append(str(client_nodes), style=style_system._get_style('semantic', 'secondary', 'bright_blue'))

        # Shard counts
        if cluster_status != 'UNKNOWN' and active_shards > 0:
            subtitle_rich.append(" | Shards: ", style="default")
            subtitle_rich.append(str(active_shards), style=style_system._get_style('semantic', 'success', 'green'))
            if unassigned_shards > 0:
                subtitle_rich.append(" | ", style="default")
                subtitle_rich.append(f"{unassigned_shards} unassigned", style=style_system._get_style('semantic', 'error', 'red'))
            if relocating_shards > 0:
                subtitle_rich.append(" | ", style="default")
                subtitle_rich.append(f"{relocating_shards} relocating", style=style_system._get_style('semantic', 'warning', 'yellow'))

        # Status body text
        if cluster_status == 'RED':
            status_text = f"🔴 Critical - {unassigned_shards} Unassigned Shards"
            body_style = "bold red"
            border = "red"
        elif cluster_status == 'YELLOW':
            status_text = f"🟡 Warning - {unassigned_shards} Unassigned Shard{'s' if unassigned_shards != 1 else ''}"
            body_style = "bold yellow"
            border = "yellow"
        else:
            status_text = f"🟢 All Nodes Healthy - {total_nodes} Node{'s' if total_nodes != 1 else ''} Online"
            body_style = "bold green"
            border = style_system._get_style('table_styles', 'border_style', 'bright_magenta')

        # Build cluster subtitle matching indices format
        cluster_subtitle = Text()
        cluster_subtitle.append(cluster_name, style=style_system._get_style('semantic', 'primary', 'cyan'))
        cluster_subtitle.append("  ", style="default")
        if cluster_version != 'Unknown':
            cluster_subtitle.append(f"v{cluster_version}", style=style_system._get_style('semantic', 'muted', 'dim'))
            cluster_subtitle.append("   ", style="default")
        cluster_subtitle.append_text(subtitle_rich)

        title_panel = Panel(
            Text(status_text, style=body_style, justify="center"),
            title=style_system.create_semantic_text(f"💻 Elasticsearch Nodes{filter_text}", "primary"),
            subtitle=cluster_subtitle,
            border_style=border,
            padding=(1, 2)
        )

        # Check if we have meaningful node IDs
        has_node_ids = any(node.get('nodeid', 'Unknown') != 'Unknown' for node in nodes)

        # Create enhanced nodes table with semantic styling
        if style_system:
            table = style_system.create_standard_table(None, style_variant='dashboard')
        else:
            # Fallback to original styling
            table = Table(show_header=True, header_style=styles.get('header_style', 'bold magenta'), expand=True, box=self.es_client.style_system.get_table_box())
        
        # Add columns with semantic column types
        if style_system:
            style_system.add_themed_column(table, "📛 Node Name", column_type='name', no_wrap=True, width=25)
            if has_node_ids:
                style_system.add_themed_column(table, "🆔 Node ID", column_type='default', width=12, justify="center")
            style_system.add_themed_column(table, "📦 ES Version", column_type='default', width=12, justify="center", no_wrap=True)
            style_system.add_themed_column(table, "📊 Indices", column_type='count', justify="center", width=8)
            style_system.add_themed_column(table, "👑 Master", column_type='status', justify="center", width=8)
            style_system.add_themed_column(table, "💾 Data", column_type='status', justify="center", width=6)
            style_system.add_themed_column(table, "🔄 Ingest", column_type='status', justify="center", width=8)
            style_system.add_themed_column(table, "🔗 Client", column_type='status', justify="center", width=8)
            style_system.add_themed_column(table, "🎯 Status", column_type='status', justify="center", width=10)
        else:
            # Fallback to original column definitions
            table.add_column("📛 Node Name", no_wrap=True, width=25)
            if has_node_ids:
                table.add_column("🆔 Node ID", width=12, justify="center")
            table.add_column("📦 ES Version", width=12, justify="center", no_wrap=True)
            table.add_column("📊 Indices", justify="center", width=8)
            table.add_column("👑 Master", justify="center", width=8)
            table.add_column("💾 Data", justify="center", width=6)
            table.add_column("🔄 Ingest", justify="center", width=8)
            table.add_column("🔗 Client", justify="center", width=8)
            table.add_column("🎯 Status", justify="center", width=10)

        # Sort nodes: master first, then data nodes, then others - ORIGINAL SORTING
        def node_sort_key(node):
            roles = node.get('roles', [])
            name = node.get('name', '')
            # Current master gets priority
            if name == current_master:
                return (0, name)
            # Master-eligible nodes next
            elif 'master' in roles:
                return (1, name)
            # Data nodes next
            elif any(role.startswith('data') for role in roles):
                return (2, name)
            # Others last
            else:
                return (3, name)

        sorted_nodes = sorted(nodes, key=node_sort_key)

        for node in sorted_nodes:
            name = node.get('name', 'Unknown')
            hostname = node.get('hostname', 'Unknown')
            node_id = node.get('nodeid', 'Unknown')[:12]  # Truncate for display
            roles = node.get('roles', [])
            
            # Get version information
            version = node.get('version', 'Unknown')
            build_hash = node.get('build_hash')
            indices_count = node.get('indices_count', 0)  # Get actual indices count
            
            # Format version display
            if version != 'Unknown':
                if build_hash:
                    version_display = f"v{version}"
                else:
                    version_display = f"v{version}"
            else:
                version_display = "Unknown"
            
            # Format node name with hostname in parentheses - ORIGINAL FORMAT
            node_display_name = f"{name} ({hostname})"

            # Determine node type indicators - ORIGINAL LOGIC
            is_master_eligible = 'master' in roles
            is_data = any(role.startswith('data') for role in roles)
            is_ingest = 'ingest' in roles
            is_client = not is_data and not is_master_eligible
            is_current_master = name == current_master

            # Set status and styling with semantic colors
            row_style = 'white'  # Default row style for fallback
            if is_current_master:
                if style_system:
                    status_icon = "👑"
                    status_text = style_system.create_semantic_text("Master", 'primary')
                else:
                    row_style = 'yellow'
                    status_icon = "👑"
                    status_text = "Master"
            elif is_master_eligible and is_data:
                if style_system:
                    status_icon = "🔩"
                    status_text = style_system.create_semantic_text("Master+Data", 'success')
                else:
                    row_style = 'green'
                    status_icon = "🔩"
                    status_text = "Master+Data"
            elif is_master_eligible:
                if style_system:
                    status_icon = "🔩"
                    status_text = style_system.create_semantic_text("Master-only", 'info')
                else:
                    row_style = 'white'
                    status_icon = "🔩"
                    status_text = " Master-only"
            elif is_data:
                if style_system:
                    status_icon = "💾"
                    status_text = style_system.create_semantic_text("Data", 'neutral')
                else:
                    row_style = 'white'
                    status_icon = "💾"
                    status_text = "Data"
            elif is_client:
                if style_system:
                    status_icon = "🔗"
                    status_text = style_system.create_semantic_text("Client", 'secondary')
                else:
                    row_style = 'white'
                    status_icon = "🔗"
                    status_text = "Client"
            else:
                if style_system:
                    status_icon = "❓"
                    status_text = style_system.create_semantic_text("Other", 'muted')
                else:
                    row_style = 'white'
                    status_icon = "❓"
                    status_text = "Other"

            # Role indicators with semantic styling
            if style_system:
                master_indicator = style_system.create_semantic_text(" ★ ", 'primary') if is_current_master else \
                                 style_system.create_semantic_text(" ○ ", 'info') if is_master_eligible else \
                                 style_system.create_semantic_text(" - ", 'muted')
                data_indicator = style_system.create_semantic_text(" ● ", 'success') if is_data else \
                               style_system.create_semantic_text(" - ", 'muted')
                ingest_indicator = style_system.create_semantic_text(" ● ", 'info') if is_ingest else \
                                 style_system.create_semantic_text(" - ", 'muted')
                client_indicator = style_system.create_semantic_text(" ● ", 'secondary') if is_client else \
                                 style_system.create_semantic_text(" - ", 'muted')
            else:
                # Original indicators for fallback
                master_indicator = " ★ " if is_current_master else " ○ " if is_master_eligible else " - "
                data_indicator = " ● " if is_data else " - "
                ingest_indicator = " ● " if is_ingest else " - "
                client_indicator = " ● " if is_client else " - "

            # Build row data conditionally with semantic styling
            row_data = [node_display_name]  # Use the formatted name with hostname
            if has_node_ids:
                row_data.append(node_id)
            row_data.append(version_display)  # Add version column
            row_data.append(f"{indices_count:,}")  # Add indices count with comma formatting
            row_data.extend([
                master_indicator,
                data_indicator,
                ingest_indicator,
                client_indicator,
                f"{status_icon} {status_text}" if not style_system else f"{status_icon} {status_text}"
            ])

            table.add_row(*row_data, style=row_style)

        # Display everything
        console.print()
        console.print(title_panel)
        console.print()
        console.print(table)
        console.print()

    def get_master_node(self):
        """Get the current master node name"""
        try:
            master_info = self.es_client.es.cat.master(format='json', h='node')
            if master_info and len(master_info) > 0:
                return master_info[0].get('node', 'Unknown')
            return 'Unknown'
        except Exception:
            return 'Unknown'

    def print_enhanced_masters_info(self, master_nodes):
        """Print enhanced master nodes information with Rich formatting"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table
        from rich.console import Console

        console = Console()

        # Get theme styles with enhanced semantic styling
        # Use the theme manager from the es_client to get proper configuration
        theme_manager = self.es_client.theme_manager
        styles = theme_manager.get_theme_styles()
        
        # Initialize semantic style system if available
        style_system = None
        try:
            from display.style_system import StyleSystem
            style_system = StyleSystem(theme_manager)
        except ImportError:
            # Fallback to old styling methods
            pass

        if not master_nodes:
            if style_system:
                no_masters_panel = style_system.create_warning_panel(
                    style_system.create_semantic_text("🔶 No master-eligible nodes found", 'warning', justify="center"),
                    "Master Nodes"
                )
            else:
                no_masters_panel = Panel(
                    Text("🔶 No master-eligible nodes found", style=styles.get('panel_styles', {}).get('error', 'bold red'), justify="center"),
                    title="👑 Master Nodes",
                    border_style=styles.get('panel_styles', {}).get('error', 'red'),
                    padding=(2, 4)
                )
            print()
            console.print(no_masters_panel)
            return

        # Get current master for identification
        try:
            current_master = self.get_master_node()
        except:
            current_master = None

        # Calculate master statistics
        total_masters = len(master_nodes)
        active_master_count = 1 if current_master else 0
        standby_masters = total_masters - active_master_count

        # Create masters table with semantic styling
        if style_system:
            table = style_system.create_standard_table(title=None, style_variant='dashboard')
            style_system.add_themed_column(table, "Status", column_type='status', width=15, justify="center")
            style_system.add_themed_column(table, "Node Name", column_type='name', no_wrap=True, width=45)  # Increased width for combined display
            style_system.add_themed_column(table, "Port", column_type='default', width=10, justify="center")
            style_system.add_themed_column(table, "Roles", column_type='default', width=40)
            style_system.add_themed_column(table, "Memory", column_type='metric', width=12, justify="right")
            style_system.add_themed_column(table, "Disk", column_type='metric', width=12, justify="right")
        else:
            table = Table(show_header=True, header_style=styles.get('header_style', 'bold magenta'), expand=True, box=self.es_client.style_system.get_table_box())
            table.add_column("Status", width=18, justify="left")  # Changed width and alignment
            table.add_column("Node Name", no_wrap=True, width=45)  # Increased width for combined display
            table.add_column("Port", width=10, justify="center")
            table.add_column("Roles", width=40)
            table.add_column("Memory", width=12, justify="right")
            table.add_column("Disk", width=12, justify="right")

        # Add master nodes to table
        for node in sorted(master_nodes, key=lambda x: x.get('name', '')):
            name = node.get('name', 'Unknown')
            roles = ', '.join(node.get('roles', [])) or 'none'
            host = node.get('host', node.get('hostname', 'Unknown'))
            port = str(node.get('http_port', node.get('port', 'N/A')))
            
            # Combine name and host in a single column
            node_display = f"{name} ([dim]{host}[/dim])"
            
            # Master status
            if name == current_master:
                status = "🟢  [bold]ACTIVE[/bold]"  # Use consistent spacing and bold for better alignment
                name_style = styles.get('success_style', 'bold green')
            else:
                status = "⚪  [bold]STANDBY[/bold]"  # Use consistent spacing and bold for better alignment
                name_style = styles.get('info_style', 'bold blue')
            
            # Resource usage - Memory
            memory_used = node.get('memory_used_bytes', 0)
            memory_total = node.get('memory_total_bytes', 0)
            if memory_total > 0 and memory_used > 0:
                memory_percent = int((memory_used / memory_total) * 100)
                # Color code based on memory usage
                if memory_percent >= 90:
                    memory_text = f"[red]{memory_percent}%[/red]"
                elif memory_percent >= 75:
                    memory_text = f"[yellow]{memory_percent}%[/yellow]"
                else:
                    memory_text = f"{memory_percent}%"
            else:
                memory_text = "[dim]N/A[/dim]"

            # Resource usage - Disk
            disk_info = node.get('disk', {})
            if disk_info and disk_info.get('total', 0) > 0:
                disk_percent = disk_info.get('used_percent', 0)
                # Color code based on disk usage
                if disk_percent >= 95:
                    disk_text = f"[red]{disk_percent}%[/red]"
                elif disk_percent >= 85:
                    disk_text = f"[yellow]{disk_percent}%[/yellow]"
                else:
                    disk_text = f"{disk_percent}%"
            else:
                disk_text = "[dim]N/A[/dim]"

            table.add_row(
                status,
                f"[{name_style}]{node_display}[/{name_style}]",
                port,
                roles,
                memory_text,
                disk_text
            )

        # Create a panel that contains the table
        subtitle_text = f"Total: {total_masters} | Active: {active_master_count} | Standby: {standby_masters}"
        
        if style_system:
            main_panel = style_system.create_dashboard_panel(
                table,  # Put the table inside the panel
                "Master Nodes",
                "👑"
            )
        else:
            main_panel = Panel(
                table,  # Put the table inside the panel
                title="👑 Master Nodes",
                subtitle=subtitle_text,
                border_style=styles.get('border_style', 'bright_magenta'),
                padding=(1, 2)
            )

        # Display everything
        console.print()
        console.print(main_panel)
        console.print()


# Backward compatibility functions
def get_nodes(es_client) -> List[Dict[str, Any]]:
    """Backward compatibility function for existing code."""
    nodes_cmd = NodesCommands(es_client)
    return nodes_cmd.get_nodes()

def get_nodes_fast(es_client) -> List[Dict[str, Any]]:
    """Backward compatibility function for existing code."""
    nodes_cmd = NodesCommands(es_client)
    return nodes_cmd.get_nodes_fast()

def get_all_nodes_stats(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    nodes_cmd = NodesCommands(es_client)
    return nodes_cmd.get_all_nodes_stats()

def get_node_id_to_hostname_map(es_client) -> Dict[str, str]:
    """Backward compatibility function for existing code."""
    nodes_cmd = NodesCommands(es_client)
    return nodes_cmd.get_node_id_to_hostname_map()
