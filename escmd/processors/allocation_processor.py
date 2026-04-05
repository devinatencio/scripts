"""
Allocation processing utilities for Elasticsearch command-line tool.

This module provides allocation-related data processing capabilities including
allocation analysis, explanation parsing, and decision processing.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime


class AllocationProcessor:
    """
    Handles allocation data processing and analysis.
    
    Provides methods for processing allocation explanations, analyzing
    allocation decisions, and managing allocation-related data structures.
    """
    
    def __init__(self):
        """Initialize the allocation processor."""
        pass
    
    def process_allocation_explanation(self, explain_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process allocation explanation data into a standardized format.
        
        Args:
            explain_result: Raw allocation explanation from Elasticsearch
            
        Returns:
            Processed allocation explanation data
        """
        processed = {
            'index': explain_result.get('index', 'unknown'),
            'shard': explain_result.get('shard', 'unknown'),
            'primary': explain_result.get('primary', False),
            'current_state': 'unknown',
            'can_allocate': False,
            'allocate_explanation': 'No explanation available',
            'current_node': None,
            'allocation_decisions': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract current allocation status
        if 'current_state' in explain_result:
            processed['current_state'] = explain_result['current_state']
        
        # Process allocation decisions
        if 'allocate_explanation' in explain_result:
            processed['allocate_explanation'] = explain_result['allocate_explanation']
        
        if 'can_allocate' in explain_result:
            processed['can_allocate'] = explain_result['can_allocate'] == 'yes'
        
        # Process node decisions
        if 'node_allocation_decisions' in explain_result:
            processed['allocation_decisions'] = self._process_node_decisions(
                explain_result['node_allocation_decisions']
            )
        
        return processed
    
    def _process_node_decisions(self, node_decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process node allocation decisions."""
        processed_decisions = []
        
        for decision in node_decisions:
            processed_decision = {
                'node_id': decision.get('node_id', 'unknown'),
                'node_name': decision.get('node_name', 'unknown'),
                'transport_address': decision.get('transport_address', 'unknown'),
                'node_attributes': decision.get('node_attributes', {}),
                'node_decision': decision.get('node_decision', 'unknown'),
                'weight_ranking': decision.get('weight_ranking', 0),
                'deciders': []
            }
            
            # Process deciders
            if 'deciders' in decision:
                processed_decision['deciders'] = self._process_deciders(decision['deciders'])
            
            processed_decisions.append(processed_decision)
        
        return processed_decisions
    
    def _process_deciders(self, deciders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process allocation deciders."""
        processed_deciders = []
        
        for decider in deciders:
            processed_decider = {
                'decider': decider.get('decider', 'unknown'),
                'decision': decider.get('decision', 'unknown'),
                'explanation': decider.get('explanation', 'No explanation')
            }
            processed_deciders.append(processed_decider)
        
        return processed_deciders
    
    def analyze_allocation_issues(self, allocations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze allocation data to identify common issues.
        
        Args:
            allocations: List of allocation objects
            
        Returns:
            Analysis of allocation issues
        """
        issues = {
            'unassigned_shards': [],
            'allocation_failures': [],
            'node_issues': {},
            'disk_issues': [],
            'summary': {
                'total_issues': 0,
                'critical_issues': 0,
                'warning_issues': 0
            }
        }
        
        for allocation in allocations:
            # Check for unassigned shards
            if allocation.get('current_state') == 'unassigned':
                issues['unassigned_shards'].append(allocation)
                issues['summary']['total_issues'] += 1
                
                # Categorize severity
                if allocation.get('primary', False):
                    issues['summary']['critical_issues'] += 1
                else:
                    issues['summary']['warning_issues'] += 1
            
            # Check for allocation failures
            if not allocation.get('can_allocate', True):
                issues['allocation_failures'].append(allocation)
        
        return issues
    
    def group_allocations_by_index(self, allocations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group allocations by index name.
        
        Args:
            allocations: List of allocation objects
            
        Returns:
            Dictionary mapping index names to allocation lists
        """
        grouped = {}
        for allocation in allocations:
            index = allocation.get('index', 'unknown')
            if index not in grouped:
                grouped[index] = []
            grouped[index].append(allocation)
        return grouped
    
    def group_allocations_by_node(self, allocations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group allocations by node.
        
        Args:
            allocations: List of allocation objects
            
        Returns:
            Dictionary mapping node names to allocation lists
        """
        grouped = {}
        for allocation in allocations:
            node = allocation.get('current_node', 'unassigned')
            if node not in grouped:
                grouped[node] = []
            grouped[node].append(allocation)
        return grouped
    
    def calculate_allocation_statistics(self, allocations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate allocation statistics.
        
        Args:
            allocations: List of allocation objects
            
        Returns:
            Dictionary with allocation statistics
        """
        if not allocations:
            return {
                'total_allocations': 0,
                'assigned_count': 0,
                'unassigned_count': 0,
                'primary_count': 0,
                'replica_count': 0,
                'allocation_success_rate': 0.0
            }
        
        assigned_count = 0
        unassigned_count = 0
        primary_count = 0
        replica_count = 0
        
        for allocation in allocations:
            if allocation.get('current_state') == 'assigned':
                assigned_count += 1
            else:
                unassigned_count += 1
            
            if allocation.get('primary', False):
                primary_count += 1
            else:
                replica_count += 1
        
        total = len(allocations)
        success_rate = (assigned_count / total * 100) if total > 0 else 0
        
        return {
            'total_allocations': total,
            'assigned_count': assigned_count,
            'unassigned_count': unassigned_count,
            'primary_count': primary_count,
            'replica_count': replica_count,
            'allocation_success_rate': round(success_rate, 2)
        }
    
    def extract_allocation_decisions_summary(self, allocation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract a summary of allocation decisions for a single allocation.
        
        Args:
            allocation: Single allocation object
            
        Returns:
            Summary of allocation decisions
        """
        decisions = allocation.get('allocation_decisions', [])
        
        summary = {
            'total_nodes_evaluated': len(decisions),
            'nodes_can_allocate': 0,
            'nodes_cannot_allocate': 0,
            'common_rejection_reasons': {},
            'best_candidate_node': None
        }
        
        for decision in decisions:
            node_decision = decision.get('node_decision', 'unknown')
            
            if node_decision == 'yes':
                summary['nodes_can_allocate'] += 1
                # Track best candidate (first one that can allocate)
                if summary['best_candidate_node'] is None:
                    summary['best_candidate_node'] = {
                        'node_name': decision.get('node_name'),
                        'node_id': decision.get('node_id'),
                        'weight_ranking': decision.get('weight_ranking')
                    }
            else:
                summary['nodes_cannot_allocate'] += 1
            
            # Track rejection reasons
            deciders = decision.get('deciders', [])
            for decider in deciders:
                if decider.get('decision') == 'NO':
                    reason = decider.get('decider', 'unknown')
                    summary['common_rejection_reasons'][reason] = \
                        summary['common_rejection_reasons'].get(reason, 0) + 1
        
        return summary
    
    def find_problematic_allocations(self, allocations: List[Dict[str, Any]], 
                                   threshold_failures: int = 3) -> List[Dict[str, Any]]:
        """
        Find allocations that are consistently failing.
        
        Args:
            allocations: List of allocation objects
            threshold_failures: Minimum number of node failures to consider problematic
            
        Returns:
            List of problematic allocations
        """
        problematic = []
        
        for allocation in allocations:
            if allocation.get('current_state') == 'unassigned':
                summary = self.extract_allocation_decisions_summary(allocation)
                
                if summary['nodes_cannot_allocate'] >= threshold_failures:
                    allocation_copy = allocation.copy()
                    allocation_copy['failure_summary'] = summary
                    problematic.append(allocation_copy)
        
        return problematic

    def get_enhanced_allocation_explain(self, es_client, index_name, shard_number, is_primary):
        """
        Get comprehensive allocation explanation with enhanced details.

        Args:
            es_client: Elasticsearch client instance  
            index_name (str): Name of the index
            shard_number (int): Shard number
            is_primary (bool): True for primary shard, False for replica

        Returns:
            dict: Enhanced allocation explanation with detailed information
        """
        try:
            # Get basic allocation explanation
            request_body = {
                "index": index_name,
                "shard": shard_number,
                "primary": is_primary
            }
            allocation_explain = es_client.cluster.allocation_explain(body=request_body)

            # Get additional context information
            try:
                # Get cluster nodes information
                nodes_info = es_client.nodes.info()
                nodes_stats = es_client.nodes.stats()

                # Get index information
                index_settings = es_client.indices.get_settings(index=index_name)
                index_stats = es_client.indices.stats(index=index_name)

                # Get cluster settings that might affect allocation
                cluster_settings = es_client.cluster.get_settings()

                # Get shard information for this index (assumes get_shards_as_dict exists)
                # We'll just use basic shard info for now
                index_shards = []

            except Exception as e:
                # If we can't get additional info, continue with basic explain
                nodes_info = None
                nodes_stats = None
                index_settings = None
                index_stats = None
                cluster_settings = None
                index_shards = []

            # Build enhanced response
            enhanced_result = {
                "basic_explanation": allocation_explain,
                "index_name": index_name,
                "shard_number": shard_number,
                "is_primary": is_primary,
                "shard_type": "primary" if is_primary else "replica",
                "enhancement_metadata": {
                    "nodes_available": len(nodes_info['nodes']) if nodes_info else 0,
                    "total_shards_for_index": len(index_shards),
                    "analysis_timestamp": self._get_current_timestamp()
                }
            }

            # Extract current allocation info
            current_node = allocation_explain.get('current_node')
            if current_node:
                enhanced_result['current_allocation'] = {
                    "allocated": True,
                    "node_id": current_node.get('id'),
                    "node_name": current_node.get('name'),
                    "weight_ranking": current_node.get('weight_ranking'),
                    "allocation_details": current_node
                }
            else:
                enhanced_result['current_allocation'] = {
                    "allocated": False,
                    "reason": "Shard is unassigned"
                }

                # Add unassigned info if available
                unassigned_info = allocation_explain.get('unassigned_info', {})
                enhanced_result['unassigned_details'] = {
                    "reason": unassigned_info.get('reason'),
                    "at": unassigned_info.get('at'),
                    "last_allocation_status": unassigned_info.get('last_allocation_status'),
                    "failed_attempts": unassigned_info.get('failed_allocation_attempts', 0)
                }

            # Process node allocation decisions
            node_allocation_decisions = allocation_explain.get('node_allocation_decisions', [])
            enhanced_result['node_decisions'] = []

            for decision in node_allocation_decisions:
                node_decision = {
                    "node_id": decision.get('node_id'),
                    "node_name": decision.get('node_name'),
                    "transport_address": decision.get('transport_address'),
                    "node_attributes": decision.get('node_attributes', {}),
                    "node_decision": decision.get('node_decision'),
                    "weight_ranking": decision.get('weight_ranking', 0),
                    "deciders": []
                }

                # Process allocation deciders
                for decider in decision.get('deciders', []):
                    decider_info = {
                        "decider": decider.get('decider'),
                        "decision": decider.get('decision'),
                        "explanation": decider.get('explanation')
                    }
                    node_decision['deciders'].append(decider_info)

                enhanced_result['node_decisions'].append(node_decision)

            # Add summary statistics
            enhanced_result['summary'] = self.generate_allocation_summary(enhanced_result)

            return enhanced_result

        except Exception as e:
            # Return basic error information if enhancement fails
            return {
                "error": f"Failed to get allocation explanation: {str(e)}",
                "index_name": index_name,
                "shard_number": shard_number,
                "is_primary": is_primary
            }
    
    def generate_allocation_summary(self, enhanced_result):
        """Generate summary statistics for allocation explanation."""
        summary = {
            "total_nodes_evaluated": len(enhanced_result.get('node_decisions', [])),
            "allocation_possible": False,
            "primary_barriers": [],
            "recommendation": ""
        }

        # Determine if allocation is possible
        if enhanced_result.get('current_allocation', {}).get('allocated'):
            summary['allocation_possible'] = True
            summary['recommendation'] = "Shard is successfully allocated"
        else:
            # Check if any node can accept the shard
            node_decisions = enhanced_result.get('node_decisions', [])
            can_allocate_nodes = [n for n in node_decisions if n.get('node_decision') in ['yes', 'throttle']]

            if can_allocate_nodes:
                summary['allocation_possible'] = True
                summary['recommendation'] = f"Allocation possible on {len(can_allocate_nodes)} node(s)"
            else:
                summary['allocation_possible'] = False

                # Identify primary barriers
                all_deciders = []
                for node in node_decisions:
                    for decider in node.get('deciders', []):
                        if decider.get('decision') == 'no':
                            all_deciders.append(decider.get('decider'))

                # Count barrier frequency
                from collections import Counter
                barrier_counts = Counter(all_deciders)
                summary['primary_barriers'] = [
                    {"barrier": barrier, "affected_nodes": count}
                    for barrier, count in barrier_counts.most_common(3)
                ]

                if summary['primary_barriers']:
                    top_barrier = summary['primary_barriers'][0]['barrier']
                    summary['recommendation'] = f"Address '{top_barrier}' issue to enable allocation"
                else:
                    summary['recommendation'] = "Check cluster allocation settings"

        return summary

    def _get_current_timestamp(self):
        """Get current timestamp for metadata."""
        from datetime import datetime
        return datetime.now().isoformat()


# Backward compatibility functions
def process_allocation_explanation(explain_result: Dict[str, Any]) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    processor = AllocationProcessor()
    return processor.process_allocation_explanation(explain_result)
