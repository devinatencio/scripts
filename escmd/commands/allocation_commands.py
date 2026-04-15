"""
Allocation command processors extracted from ElasticsearchClient.

This module handles allocation-related operations including:
- Shard allocation management
- Allocation explanation and debugging
- Node allocation controls
- Cluster allocation settings
"""

from typing import Dict, Any, Optional, List
from .base_command import BaseCommand


class AllocationCommands(BaseCommand):
    """
    Command processor for allocation-related operations.

    This class extracts allocation management methods from the main ElasticsearchClient,
    providing a focused interface for shard allocation operations.
    """

    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'allocation'

    def get_allocation_as_dict(self) -> Dict[str, Any]:
        """
        Get allocation information as a dictionary.

        Returns:
            dict: Node allocation data with disk and shard information
        """
        try:
            allocation = self.es_client.es.cat.allocation(format='json', bytes='b')

            allocation_dict = {}
            for entry in allocation:
                node = entry['node']
                allocation_dict[node] = {
                    'shards': int(entry['shards']),
                    'disk.percent': float(entry['disk.percent']) if entry['disk.percent'] is not None else 0,
                    'disk.used': int(entry['disk.used']) if entry['disk.used'] is not None else 0,
                    'disk.avail': int(entry['disk.avail']) if entry['disk.avail'] is not None else 0,
                    'disk.total': int(entry['disk.total']) if entry['disk.total'] is not None else 0
                }

            return allocation_dict

        except Exception as e:
            return {"error": f"Failed to get allocation data: {str(e)}"}

    def get_index_allocation_explain(self, index_name: str, shard_number: int, is_primary: bool) -> Dict[str, Any]:
        """
        Get allocation explanation for a specific shard.

        Args:
            index_name: Name of the index
            shard_number: Shard number
            is_primary: True for primary shard, False for replica

        Returns:
            dict: Allocation explanation
        """
        try:
            request_body = {
                "index": index_name,
                "shard": shard_number,
                "primary": is_primary
            }

            explanation = self.es_client.es.cluster.allocation_explain(body=request_body)

            # Handle response format differences
            if hasattr(explanation, 'body'):
                return explanation.body
            elif hasattr(explanation, 'get'):
                return dict(explanation)
            else:
                return explanation

        except Exception as e:
            return {
                "error": f"Failed to get allocation explanation: {str(e)}",
                "index": index_name,
                "shard": shard_number,
                "primary": is_primary
            }

    def get_enhanced_allocation_explain(self, index_name: str, shard_number: int, is_primary: bool) -> Dict[str, Any]:
        """
        Get enhanced allocation explanation with additional context (delegates to AllocationProcessor).

        Args:
            index_name: Name of the index
            shard_number: Shard number
            is_primary: True for primary shard, False for replica

        Returns:
            dict: Enhanced allocation explanation with detailed information
        """
        return self.es_client.allocation_processor.get_enhanced_allocation_explain(
            self.es_client.es, index_name, shard_number, is_primary
        )

    def check_allocation_issues(self) -> Dict[str, Any]:
        """
        Check for allocation issues in the cluster.

        Returns:
            dict: Allocation issues summary
        """
        try:
            issues = {
                'unassigned_shards': [],
                'delayed_shards': [],
                'failed_allocations': [],
                'summary': {
                    'total_issues': 0,
                    'critical_issues': 0,
                    'warning_issues': 0
                }
            }

            # Get cluster health for basic shard info
            health = self.es_client.cluster_commands.get_cluster_health(include_version=False)

            if health.get('unassigned_shards', 0) > 0:
                issues['summary']['total_issues'] += health['unassigned_shards']
                issues['summary']['critical_issues'] += health['unassigned_shards']

            if health.get('delayed_unassigned_shards', 0) > 0:
                issues['summary']['total_issues'] += health['delayed_unassigned_shards']
                issues['summary']['warning_issues'] += health['delayed_unassigned_shards']

            # Get detailed shard information for unassigned shards
            try:
                shards_data = self.get_shards_as_dict()

                for shard in shards_data:
                    if shard.get('state') == 'UNASSIGNED':
                        # Get allocation explanation for unassigned shard
                        explain = self.get_index_allocation_explain(
                            shard.get('index'),
                            int(shard.get('shard', 0)),
                            shard.get('prirep') == 'p'
                        )

                        issues['unassigned_shards'].append({
                            'index': shard.get('index'),
                            'shard': shard.get('shard'),
                            'type': shard.get('prirep'),
                            'explanation': explain
                        })

            except Exception as shard_error:
                issues['shard_analysis_error'] = str(shard_error)

            return issues

        except Exception as e:
            return {"error": f"Failed to check allocation issues: {str(e)}"}

    def get_shards_as_dict(self) -> List[Dict[str, Any]]:
        """
        Get all shards as a list of dictionaries.

        Returns:
            list: Shard information
        """
        try:
            # Explicitly request the fields we need to ensure they're included
            shards = self.es_client.es.cat.shards(
                format='json',
                h="index,shard,prirep,state,docs,store,node"
            )

            # Handle response format differences
            if hasattr(shards, 'body'):
                return shards.body
            elif hasattr(shards, '__iter__'):
                return list(shards)
            else:
                return [shards] if shards else []

        except Exception as e:
            return [{"error": f"Failed to get shards: {str(e)}"}]

    def change_shard_allocation(self, option: str) -> Dict[str, Any]:
        """
        Change cluster shard allocation settings.

        Args:
            option: Allocation option ('all', 'primaries', 'new_primaries', 'none')

        Returns:
            dict: Operation result
        """
        try:
            valid_options = ['all', 'primaries', 'new_primaries', 'none']
            if option not in valid_options:
                return {
                    "error": f"Invalid option '{option}'. Valid options: {valid_options}"
                }

            # For allocation enable/disable, use transient settings
            # When enabling (option='all'), remove the transient setting to return to default
            # When disabling, set the transient setting to restrict allocation
            if option == 'all':
                # Remove transient setting to return to default behavior
                setting_value = None
            else:
                # Set specific restriction (primaries, new_primaries, none)
                setting_value = option

            result = self.es_client.es.cluster.put_settings(
                body={
                    "transient": {
                        "cluster.routing.allocation.enable": setting_value
                    }
                }
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
                "error": f"Failed to change shard allocation: {str(e)}",
                "option": option
            }

    def exclude_node_from_allocation(self, hostname: Optional[str] = None) -> Dict[str, Any]:
        """
        Exclude a node from shard allocation.

        WARNING: This method OVERWRITES existing exclusions. For proper add/remove
        operations that append to existing exclusions, use the allocation exclude
        add/remove commands handled by AllocationHandler.

        Args:
            hostname: Hostname to exclude (optional, prompts if not provided)

        Returns:
            dict: Operation result
        """
        try:
            if not hostname:
                return {"error": "hostname parameter is required"}

            result = self.es_client.es.cluster.put_settings(
                body={
                    "transient": {
                        "cluster.routing.allocation.exclude._name": hostname
                    }
                }
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
                "error": f"Failed to exclude node from allocation: {str(e)}",
                "hostname": hostname
            }

    def reset_node_allocation_exclusion(self) -> Dict[str, Any]:
        """
        Reset node allocation exclusions.

        Returns:
            dict: Operation result
        """
        try:
            result = self.es_client.es.cluster.put_settings(
                body={
                    "persistent": {
                        "cluster.routing.allocation.exclude._name": None,
                        "cluster.routing.allocation.exclude._ip": None,
                        "cluster.routing.allocation.exclude._host": None
                    },
                    "transient": {
                        "cluster.routing.allocation.exclude._name": None,
                        "cluster.routing.allocation.exclude._ip": None,
                        "cluster.routing.allocation.exclude._host": None
                    }
                }
            )

            # Handle response format differences
            if hasattr(result, 'body'):
                return result.body
            elif hasattr(result, 'get'):
                return dict(result)
            else:
                return result

        except Exception as e:
            return {"error": f"Failed to reset node allocation exclusion: {str(e)}"}

    def get_allocation_settings(self) -> Dict[str, Any]:
        """
        Get current allocation settings.

        Returns:
            dict: Current allocation settings
        """
        try:
            settings = self.es_client.es.cluster.get_settings(
                include_defaults=True
            )

            # Handle response format differences
            if hasattr(settings, 'body'):
                settings_data = settings.body
            elif hasattr(settings, 'get'):
                settings_data = dict(settings)
            else:
                settings_data = settings

            # Extract allocation-related settings
            allocation_settings = {}

            for section in ['persistent', 'transient', 'defaults']:
                section_data = settings_data.get(section, {})

                # Look for cluster.routing.allocation settings
                cluster_settings = section_data.get('cluster', {})
                routing_settings = cluster_settings.get('routing', {})
                allocation_data = routing_settings.get('allocation', {})

                if allocation_data:
                    allocation_settings[section] = allocation_data

            return allocation_settings

        except Exception as e:
            return {"error": f"Failed to get allocation settings: {str(e)}"}

    def reroute_cluster(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Manually reroute cluster shards.

        Args:
            dry_run: Whether to perform a dry run (default: True)

        Returns:
            dict: Reroute operation result
        """
        try:
            result = self.es_client.es.cluster.reroute(
                dry_run=dry_run,
                explain=True
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
                "error": f"Failed to reroute cluster: {str(e)}",
                "dry_run": dry_run
            }

    def print_enhanced_allocation_settings(self) -> str:
        """
        Display allocation settings in enhanced multi-panel format.

        Returns:
            JSON string representation of settings for reference
        """
        from display.allocation_renderer import AllocationRenderer

        # Get cluster settings and health data
        settings = self.es_client.es.cluster.get_settings(include_defaults=False)
        health_data = self.es_client.get_cluster_health()

        # Create renderer and display
        renderer = AllocationRenderer(self.es_client.theme_manager)
        return renderer.render_enhanced_allocation_settings(settings, health_data)

    def print_allocation_explain_results(self, explain_result: Dict[str, Any]) -> None:
        """
        Display allocation explain results in themed multi-panel format.

        Args:
            explain_result: Enhanced allocation explanation data
        """
        from display.allocation_renderer import AllocationRenderer

        renderer = AllocationRenderer(self.es_client.theme_manager)
        renderer.render_allocation_explain_results(explain_result)


# ================================
# Backward Compatibility Functions
# ================================

def get_allocation_as_dict(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    allocation_cmd = AllocationCommands(es_client)
    return allocation_cmd.get_allocation_as_dict()

def get_index_allocation_explain(es_client, index_name: str, shard_number: int, is_primary: bool) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    allocation_cmd = AllocationCommands(es_client)
    return allocation_cmd.get_index_allocation_explain(index_name, shard_number, is_primary)

def check_allocation_issues(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    allocation_cmd = AllocationCommands(es_client)
    return allocation_cmd.check_allocation_issues()

def change_shard_allocation(es_client, option: str) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    allocation_cmd = AllocationCommands(es_client)
    return allocation_cmd.change_shard_allocation(option)
