"""
Shard processing utilities for Elasticsearch command-line tool.

This module provides shard-related data processing capabilities including
colocation analysis, shard statistics, and shard state management.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


class ShardProcessor:
    """
    Handles shard data processing and analysis.
    
    Provides methods for analyzing shard distribution, colocation,
    and statistics without being tied to any specific Elasticsearch
    client implementation.
    """
    
    def __init__(self):
        """Initialize the shard processor."""
        pass
    
    def analyze_shard_distribution(self, shards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze shard distribution across nodes and indices.
        
        Args:
            shards: List of shard objects
            
        Returns:
            Dictionary with shard distribution analysis
        """
        if not shards:
            return {
                'total_shards': 0,
                'primary_shards': 0,
                'replica_shards': 0,
                'unassigned_shards': 0,
                'indices_count': 0,
                'nodes_count': 0,
                'shards_per_node': {},
                'shards_per_index': {}
            }
        
        primary_shards = 0
        replica_shards = 0
        unassigned_shards = 0
        shards_per_node = defaultdict(int)
        shards_per_index = defaultdict(int)
        indices = set()
        nodes = set()
        
        for shard in shards:
            shard_type = shard.get('prirep', 'unknown')
            state = shard.get('state', 'unknown')
            index = shard.get('index', 'unknown')
            node = shard.get('node', None)
            
            # Count shard types
            if shard_type == 'p':
                primary_shards += 1
            elif shard_type == 'r':
                replica_shards += 1
            
            # Count unassigned shards
            if state == 'UNASSIGNED':
                unassigned_shards += 1
            
            # Track indices and nodes
            indices.add(index)
            if node:
                nodes.add(node)
                shards_per_node[node] += 1
            
            shards_per_index[index] += 1
        
        return {
            'total_shards': len(shards),
            'primary_shards': primary_shards,
            'replica_shards': replica_shards,
            'unassigned_shards': unassigned_shards,
            'indices_count': len(indices),
            'nodes_count': len(nodes),
            'shards_per_node': dict(shards_per_node),
            'shards_per_index': dict(shards_per_index)
        }
    
    def group_shards_by_index(self, shards: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group shards by their index name.
        
        Args:
            shards: List of shard objects
            
        Returns:
            Dictionary mapping index names to lists of shards
        """
        grouped = defaultdict(list)
        for shard in shards:
            index = shard.get('index', 'unknown')
            grouped[index].append(shard)
        return dict(grouped)
    
    def group_shards_by_node(self, shards: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group shards by their node.
        
        Args:
            shards: List of shard objects
            
        Returns:
            Dictionary mapping node names to lists of shards
        """
        grouped = defaultdict(list)
        for shard in shards:
            node = shard.get('node', 'unassigned')
            grouped[node].append(shard)
        return dict(grouped)
    
    def group_shards_by_state(self, shards: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group shards by their state.
        
        Args:
            shards: List of shard objects
            
        Returns:
            Dictionary mapping states to lists of shards
        """
        grouped = defaultdict(list)
        for shard in shards:
            state = shard.get('state', 'unknown')
            grouped[state].append(shard)
        return dict(grouped)
    
    def filter_shards_by_state(self, shards: List[Dict[str, Any]], state: str) -> List[Dict[str, Any]]:
        """
        Filter shards by their state.
        
        Args:
            shards: List of shard objects
            state: State to filter by (e.g., 'STARTED', 'UNASSIGNED', 'RELOCATING')
            
        Returns:
            List of shards in the specified state
        """
        return [shard for shard in shards if shard.get('state', '').upper() == state.upper()]
    
    def filter_shards_by_type(self, shards: List[Dict[str, Any]], shard_type: str) -> List[Dict[str, Any]]:
        """
        Filter shards by their type (primary or replica).
        
        Args:
            shards: List of shard objects
            shard_type: Type to filter by ('p' for primary, 'r' for replica)
            
        Returns:
            List of shards of the specified type
        """
        return [shard for shard in shards if shard.get('prirep', '') == shard_type]
    
    def get_primary_shards(self, shards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all primary shards."""
        return self.filter_shards_by_type(shards, 'p')
    
    def get_replica_shards(self, shards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all replica shards."""
        return self.filter_shards_by_type(shards, 'r')
    
    def get_unassigned_shards(self, shards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all unassigned shards."""
        return self.filter_shards_by_state(shards, 'UNASSIGNED')
    
    def get_started_shards(self, shards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all started shards."""
        return self.filter_shards_by_state(shards, 'STARTED')
    
    def calculate_shard_statistics(self, shards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comprehensive shard statistics.
        
        Args:
            shards: List of shard objects
            
        Returns:
            Dictionary with detailed shard statistics
        """
        distribution = self.analyze_shard_distribution(shards)
        states = self.group_shards_by_state(shards)
        
        # Calculate additional metrics
        state_counts = {state: len(shard_list) for state, shard_list in states.items()}
        
        # Calculate balance metrics
        shards_per_node = distribution['shards_per_node']
        if shards_per_node:
            node_shard_counts = list(shards_per_node.values())
            max_shards_per_node = max(node_shard_counts)
            min_shards_per_node = min(node_shard_counts)
            avg_shards_per_node = sum(node_shard_counts) / len(node_shard_counts)
        else:
            max_shards_per_node = 0
            min_shards_per_node = 0
            avg_shards_per_node = 0
        
        return {
            **distribution,
            'state_breakdown': state_counts,
            'balance_metrics': {
                'max_shards_per_node': max_shards_per_node,
                'min_shards_per_node': min_shards_per_node,
                'avg_shards_per_node': avg_shards_per_node,
                'balance_ratio': max_shards_per_node / max(min_shards_per_node, 1)
            }
        }
    
    def find_colocation_issues(self, shards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find potential colocation issues (primary and replica on same node).
        
        Args:
            shards: List of shard objects
            
        Returns:
            List of colocation issues found
        """
        issues = []
        index_shards = self.group_shards_by_index(shards)
        
        for index, index_shard_list in index_shards.items():
            # Group by shard number
            shard_groups = defaultdict(list)
            for shard in index_shard_list:
                shard_num = shard.get('shard', 'unknown')
                shard_groups[shard_num].append(shard)
            
            # Check for colocation within each shard group
            for shard_num, shard_group in shard_groups.items():
                nodes_used = set()
                primary_node = None
                replica_nodes = []
                
                for shard in shard_group:
                    node = shard.get('node')
                    shard_type = shard.get('prirep')
                    
                    if node:
                        if node in nodes_used and shard_type in ['p', 'r']:
                            issues.append({
                                'index': index,
                                'shard': shard_num,
                                'node': node,
                                'type': 'colocation',
                                'description': f"Primary and replica on same node: {node}"
                            })
                        
                        nodes_used.add(node)
                        
                        if shard_type == 'p':
                            primary_node = node
                        elif shard_type == 'r':
                            replica_nodes.append(node)
        
        return issues

    def analyze_shard_colocation(self, shards: List[Dict[str, Any]], pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze shard distribution to find indices where primary and replica shards
        are located on the same host, which poses availability risks.

        Args:
            shards: List of shard objects
            pattern: Optional regex pattern to filter indices

        Returns:
            dict: Colocation analysis results
        """
        import re
        
        all_shards = shards
        
        # Filter by pattern if provided
        if pattern:
            try:
                regex = re.compile(f".*{re.escape(pattern)}.*", re.IGNORECASE)
                all_shards = [shard for shard in all_shards if regex.search(shard.get("index", ""))]
            except re.error:
                # If regex fails, use simple substring match
                all_shards = [shard for shard in all_shards if pattern.lower() in shard.get("index", "").lower()]

        # Group shards by index and shard number
        index_shards = defaultdict(lambda: defaultdict(list))

        for shard in all_shards:
            if shard.get("state") == "STARTED":  # Only consider started shards
                index_name = shard.get("index", "")
                shard_number = shard.get("shard", "")
                index_shards[index_name][shard_number].append(shard)

        # Analyze colocation
        colocated_indices = []
        total_indices = len(index_shards)
        total_shard_groups = 0
        problematic_shard_groups = 0

        for index_name, shards_by_number in index_shards.items():
            index_issues = []

            for shard_number, shard_list in shards_by_number.items():
                total_shard_groups += 1

                # Group by node
                nodes_for_shard = defaultdict(list)
                for shard in shard_list:
                    nodes_for_shard[shard.get("node")].append(shard)

                # Check if any node has both primary and replica
                for node, node_shards in nodes_for_shard.items():
                    if len(node_shards) > 1:  # More than one shard (primary + replica(s))
                        has_primary = any(s.get("prirep") == "p" for s in node_shards)
                        has_replica = any(s.get("prirep") == "r" for s in node_shards)

                        if has_primary and has_replica:
                            problematic_shard_groups += 1
                            issue = {
                                "shard_number": shard_number,
                                "node": node,
                                "shards": node_shards,
                                "total_shards_on_node": len(node_shards),
                                "primary_count": sum(1 for s in node_shards if s.get("prirep") == "p"),
                                "replica_count": sum(1 for s in node_shards if s.get("prirep") == "r")
                            }
                            index_issues.append(issue)

            if index_issues:
                colocated_indices.append({
                    "index": index_name,
                    "issues": index_issues,
                    "affected_shard_groups": len(index_issues)
                })

        # Calculate summary statistics
        affected_indices = len(colocated_indices)
        risk_percentage = (affected_indices / total_indices * 100) if total_indices > 0 else 0

        return {
            "summary": {
                "total_indices_analyzed": total_indices,
                "affected_indices": affected_indices,
                "total_shard_groups": total_shard_groups,
                "problematic_shard_groups": problematic_shard_groups,
                "risk_percentage": round(risk_percentage, 2),
                "pattern_applied": pattern is not None,
                "filter_pattern": pattern
            },
            "colocated_indices": colocated_indices,
            "risk_level": "high" if risk_percentage > 50 else "medium" if risk_percentage > 20 else "low"
        }

    def print_shard_colocation_results(self, colocation_results: Dict[str, Any], use_pager: bool = False, console=None, theme_manager=None) -> None:
        """
        Print shard colocation analysis results with Rich formatting.
        
        Args:
            colocation_results: Results from analyze_shard_colocation
            use_pager: Whether to use pager for long output
            console: Rich console instance
            theme_manager: Theme manager for styling
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        
        if console is None:
            console = Console()
            
        summary = colocation_results.get("summary", {})
        colocated_indices = colocation_results.get("colocated_indices", [])
        risk_level = colocation_results.get("risk_level", "low")
        
        # Risk level styling
        if risk_level == "high":
            risk_color = "red"
            risk_icon = "🔴"
        elif risk_level == "medium":
            risk_color = "yellow" 
            risk_icon = "🟡"
        else:
            risk_color = "green"
            risk_icon = "🟢"
        
        # Create title panel
        total_analyzed = summary.get("total_indices_analyzed", 0)
        affected = summary.get("affected_indices", 0)
        risk_pct = summary.get("risk_percentage", 0)
        
        if affected == 0:
            title_text = f"✅ No Shard Colocation Issues Found"
            console.print()
            console.print(Panel(
                Text(f"✅ All {total_analyzed} indices have proper shard distribution!\n\nNo primary and replica shards are colocated on the same host.", 
                     style="bold green", justify="center"),
                title="🔍 Shard Colocation Analysis",
                border_style="green",
                padding=(2, 4)
            ))
            console.print()
            return
            
        title_text = f"{risk_icon} Shard Colocation Issues Detected"
        subtitle_text = f"Analyzed: {total_analyzed} | Affected: {affected} | Risk: {risk_pct:.1f}%"
        
        title_panel = Panel(
            Text(title_text, style=f"bold {risk_color}", justify="center"),
            subtitle=subtitle_text,
            border_style=risk_color,
            padding=(1, 2)
        )
        
        # Create detailed issues table
        table = Table(
            show_header=True, 
            header_style="bold white", 
            title="🔶  Colocation Issues", 
            expand=True
        )
        table.add_column("📋 Index Name", style="yellow", no_wrap=True)
        table.add_column("🔢 Shard", justify="center", width=8)
        table.add_column("💻 Problem Node", style="red", no_wrap=True)
        table.add_column("🔑 Primary", justify="center", width=10)
        table.add_column("📋 Replicas", justify="center", width=10)
        table.add_column("📦 Total", justify="center", width=8)
        
        for index_data in colocated_indices:
            index_name = index_data["index"]
            for issue in index_data["issues"]:
                shard_number = issue["shard_number"]
                node = issue["node"]
                primary_count = issue["primary_count"]
                replica_count = issue["replica_count"]
                total_shards = issue["total_shards_on_node"]
                
                table.add_row(
                    index_name,
                    str(shard_number),
                    node,
                    str(primary_count),
                    str(replica_count),
                    str(total_shards),
                    style="red" if primary_count > 0 and replica_count > 0 else "yellow"
                )
        
        # Display results
        console.print()
        console.print(title_panel)
        console.print()
        console.print(table)
        console.print()


# Backward compatibility functions
def analyze_shard_distribution(shards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    processor = ShardProcessor()
    return processor.analyze_shard_distribution(shards)
