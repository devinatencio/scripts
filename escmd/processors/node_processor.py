"""
Node processing utilities for Elasticsearch command-line tool.

This module provides node-related data processing capabilities including
role filtering, hostname resolution, and node statistics parsing.
"""

from typing import List, Dict, Any, Optional, Union


class NodeProcessor:
    """
    Handles node data processing and manipulation.
    
    Provides methods for filtering nodes by role, resolving node IDs,
    and parsing node statistics without being tied to any specific 
    Elasticsearch client implementation.
    """
    
    def __init__(self):
        """Initialize the node processor."""
        pass
    
    def filter_nodes_by_role(self, nodes_list: List[Dict[str, Any]], role: str) -> List[Dict[str, Any]]:
        """
        Filter nodes by role.
        
        Args:
            nodes_list: List of node objects
            role: Role to filter by (e.g., 'master', 'data', 'ingest')
            
        Returns:
            List of nodes that have the specified role
        """
        filtered_nodes = []
        for node in nodes_list:
            if role in node.get('roles', []):
                filtered_nodes.append(node)
        return filtered_nodes
    
    def resolve_node_ids_to_hostnames(self, node_ids: List[str], 
                                    node_id_to_hostname_map: Optional[Dict[str, str]] = None,
                                    nodes_data: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Resolve a list of node IDs to their corresponding hostnames.
        
        Args:
            node_ids: List of node IDs to resolve
            node_id_to_hostname_map: Optional pre-built mapping to avoid processing nodes_data
            nodes_data: Optional nodes data to build mapping from
            
        Returns:
            List of resolved hostnames or error indicators
        """
        try:
            # Use provided mapping or build from nodes_data
            if node_id_to_hostname_map is None:
                if nodes_data is None:
                    # Cannot resolve without data
                    return [f"Unknown({node_id[:8]})" for node_id in node_ids]
                
                # Create mapping of node ID to hostname
                node_id_to_hostname_map = self.create_node_id_to_hostname_map(nodes_data)
            
            # Resolve node IDs to hostnames
            resolved_nodes = []
            for node_id in node_ids:
                hostname = node_id_to_hostname_map.get(node_id, f"Unknown({node_id[:8]})")
                resolved_nodes.append(hostname)
            
            return resolved_nodes
        
        except Exception:
            # If resolution fails, return node IDs with error indication
            return [f"Error({node_id[:8]})" for node_id in node_ids]
    
    def create_node_id_to_hostname_map(self, nodes_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Create a mapping of node IDs to hostnames from nodes data.
        
        Args:
            nodes_data: List of node objects
            
        Returns:
            Dictionary mapping node IDs to hostnames
        """
        node_id_to_hostname_map = {}
        for node in nodes_data:
            node_id = node.get('nodeid')
            hostname = node.get('hostname', node.get('name', 'Unknown'))
            if node_id:
                node_id_to_hostname_map[node_id] = hostname
        return node_id_to_hostname_map
    
    def parse_node_stats(self, node_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse node statistics into a standardized format.
        
        Args:
            node_stats: Raw node statistics from Elasticsearch
            
        Returns:
            List of parsed node objects
        """
        parsed_data = []
        
        for node_id, node_info in node_stats.get('nodes', {}).items():
            hostname = node_info.get('host', 'Unknown')
            name = node_info.get('name', 'Unknown')
            roles = node_info.get('roles', [])
            
            # Extract various statistics
            indices_info = node_info.get('indices', {})
            docs_info = indices_info.get('docs', {})
            shard_info = indices_info.get('shard_stats', {})
            
            # Create base node data
            node_data = {
                'nodeid': node_id,
                'name': name,
                'hostname': hostname,
                'host': hostname,  # Add host field for compatibility
                'roles': roles,
                'indices': docs_info.get('count', 0),
                'shards': shard_info.get('total_count', 0),
                'docs_count': docs_info.get('count', 0),
                'docs_deleted': docs_info.get('deleted', 0),
                'store_size': indices_info.get('store', {}).get('size_in_bytes', 0)
            }
            
            # Extract HTTP port information
            http_info = node_info.get('http', {})
            if http_info:
                # Try different field names for port
                port = (http_info.get('bound_address', [''])[0].split(':')[-1] if http_info.get('bound_address') 
                       else http_info.get('publish_address', '').split(':')[-1])
                try:
                    node_data['http_port'] = int(port) if port.isdigit() else 9200
                except (ValueError, AttributeError):
                    node_data['http_port'] = 9200
            else:
                node_data['http_port'] = 9200
            
            # Extract CPU performance metrics (prefer OS stats over process stats)
            os_stats = node_info.get('os', {})
            process_stats = node_info.get('process', {})
            
            # Try OS CPU first (more accurate system-wide metric)
            if os_stats and 'cpu' in os_stats:
                cpu_info = os_stats['cpu']
                if 'percent' in cpu_info:
                    node_data['cpu_percent'] = cpu_info['percent']
            # Fallback to process CPU if OS CPU not available
            elif process_stats and 'cpu' in process_stats:
                cpu_info = process_stats['cpu']
                if 'percent' in cpu_info:
                    node_data['cpu_percent'] = cpu_info['percent']
            
            # Extract memory performance metrics (JVM heap)
            jvm_stats = node_info.get('jvm', {})
            if jvm_stats and 'mem' in jvm_stats:
                mem_info = jvm_stats['mem']
                heap_max = mem_info.get('heap_max_in_bytes', 0)
                heap_used = mem_info.get('heap_used_in_bytes', 0)
                if heap_max > 0:
                    node_data['memory_total_bytes'] = heap_max
                    node_data['memory_used_bytes'] = heap_used
            
            # Extract disk/filesystem performance metrics
            fs_stats = node_info.get('fs', {})
            if fs_stats and 'total' in fs_stats:
                fs_info = fs_stats['total']
                total_bytes = fs_info.get('total_in_bytes', 0)
                available_bytes = fs_info.get('available_in_bytes', 0)
                if total_bytes > 0:
                    used_bytes = total_bytes - available_bytes
                    used_percent = int((used_bytes / total_bytes * 100)) if total_bytes > 0 else 0
                    node_data['disk'] = {
                        'total': total_bytes,
                        'used': used_bytes,
                        'available': available_bytes,
                        'used_percent': used_percent
                    }
            
            # Extract load average from OS stats
            if os_stats and 'load_average' in os_stats:
                load_avg = os_stats['load_average']
                if isinstance(load_avg, dict):
                    node_data['load_1m'] = load_avg.get('1m', 0)
                    node_data['load_5m'] = load_avg.get('5m', 0) 
                    node_data['load_15m'] = load_avg.get('15m', 0)
                elif isinstance(load_avg, list) and len(load_avg) >= 3:
                    node_data['load_1m'] = load_avg[0]
                    node_data['load_5m'] = load_avg[1]
                    node_data['load_15m'] = load_avg[2]
                elif isinstance(load_avg, (int, float)):
                    node_data['load_1m'] = load_avg
            
            # Network statistics (optional)
            transport_stats = node_info.get('transport', {})
            if transport_stats:
                node_data['network'] = {
                    'server_open': transport_stats.get('server_open', 0),
                    'rx_count': transport_stats.get('rx_count', 0),
                    'rx_size_in_bytes': transport_stats.get('rx_size_in_bytes', 0),
                    'tx_count': transport_stats.get('tx_count', 0),
                    'tx_size_in_bytes': transport_stats.get('tx_size_in_bytes', 0)
                }
            
            # HTTP statistics (optional)
            http_stats = node_info.get('http', {})
            if http_stats:
                node_data['http'] = {
                    'current_open': http_stats.get('current_open', 0),
                    'total_opened': http_stats.get('total_opened', 0)
                }
            
            parsed_data.append(node_data)
        
        return parsed_data
    
    def group_nodes_by_role(self, nodes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group nodes by their roles.
        
        Args:
            nodes: List of node objects
            
        Returns:
            Dictionary mapping roles to lists of nodes
        """
        grouped = {}
        
        for node in nodes:
            roles = node.get('roles', [])
            for role in roles:
                if role not in grouped:
                    grouped[role] = []
                grouped[role].append(node)
        
        return grouped
    
    def get_nodes_by_role(self, nodes: List[Dict[str, Any]], role: str) -> List[Dict[str, Any]]:
        """
        Get all nodes that have a specific role.
        
        Args:
            nodes: List of node objects
            role: Role to search for
            
        Returns:
            List of nodes with the specified role
        """
        return [node for node in nodes if role in node.get('roles', [])]
    
    def get_master_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all master-eligible nodes."""
        return self.get_nodes_by_role(nodes, 'master')
    
    def get_data_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all data nodes."""
        return self.get_nodes_by_role(nodes, 'data')
    
    def get_ingest_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all ingest nodes."""
        return self.get_nodes_by_role(nodes, 'ingest')
    
    def calculate_node_statistics(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics across all nodes.
        
        Args:
            nodes: List of node objects
            
        Returns:
            Dictionary with node statistics
        """
        if not nodes:
            return {
                'total_nodes': 0,
                'total_docs': 0,
                'total_shards': 0,
                'total_store_size': 0,
                'roles_distribution': {}
            }
        
        total_docs = sum(node.get('docs_count', 0) for node in nodes)
        total_shards = sum(node.get('shards', 0) for node in nodes)
        total_store_size = sum(node.get('store_size', 0) for node in nodes)
        
        # Calculate role distribution
        roles_distribution = {}
        for node in nodes:
            roles = node.get('roles', [])
            for role in roles:
                roles_distribution[role] = roles_distribution.get(role, 0) + 1
        
        return {
            'total_nodes': len(nodes),
            'total_docs': total_docs,
            'total_shards': total_shards,
            'total_store_size': total_store_size,
            'roles_distribution': roles_distribution
        }
    
    def find_node_by_id(self, nodes: List[Dict[str, Any]], node_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a node by its ID.
        
        Args:
            nodes: List of node objects
            node_id: Node ID to search for
            
        Returns:
            Node object if found, None otherwise
        """
        for node in nodes:
            if node.get('nodeid') == node_id:
                return node
        return None
    
    def find_node_by_name(self, nodes: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
        """
        Find a node by its name.
        
        Args:
            nodes: List of node objects
            name: Node name to search for
            
        Returns:
            Node object if found, None otherwise
        """
        for node in nodes:
            if node.get('name') == name:
                return node
        return None


# Backward compatibility functions
def filter_nodes_by_role(nodes_list: List[Dict[str, Any]], role: str) -> List[Dict[str, Any]]:
    """Backward compatibility function for existing code."""
    processor = NodeProcessor()
    return processor.filter_nodes_by_role(nodes_list, role)


def parse_node_stats(node_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Backward compatibility function for existing code."""
    processor = NodeProcessor()
    return processor.parse_node_stats(node_stats)
