"""
Replica processing operations for Elasticsearch indices.

This module handles the core business logic for replica count management,
including planning and executing replica updates.
"""

import json
import time
import fnmatch
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional, Any


class ReplicaProcessor:
    """Processor for Elasticsearch replica count operations."""

    def __init__(self, es_client):
        """
        Initialize replica processor with ES client reference.
        
        Args:
            es_client: ElasticsearchClient instance
        """
        self.es_client = es_client

    def plan_replica_updates(
        self, 
        target_count: int, 
        indices: Optional[List[str]] = None, 
        pattern: Optional[str] = None, 
        no_replicas_only: bool = False
    ) -> Dict[str, Any]:
        """
        Plan replica count updates without executing them.

        Args:
            target_count: Target replica count
            indices: Specific indices to update
            pattern: Pattern to match indices (e.g., "logs-*")
            no_replicas_only: Only update indices with 0 replicas

        Returns:
            dict: Plan results with indices to update and metadata
            
        Raises:
            Exception: If unable to plan replica updates
        """
        try:
            # Get current cluster state
            ES_URL = self.es_client.build_es_url()
            if ES_URL is None:
                raise Exception("Could not build Elasticsearch URL")

            # Get all indices and their settings
            settings_data = self._get_all_index_settings(ES_URL)

            # Build list of candidate indices
            candidate_indices = self._build_candidate_indices_list(
                settings_data, indices, pattern
            )

            # Filter indices that need updates
            indices_to_update, skipped_indices = self._filter_indices_for_updates(
                settings_data, candidate_indices, target_count, no_replicas_only
            )

            return {
                'indices_to_update': indices_to_update,
                'skipped_indices': skipped_indices,
                'target_count': target_count,
                'total_candidates': len(candidate_indices),
                'total_updates_needed': len(indices_to_update),
                'pattern': pattern,
                'no_replicas_only': no_replicas_only
            }

        except Exception as e:
            raise Exception(f"Failed to plan replica updates: {str(e)}")

    def execute_replica_updates(
        self, 
        indices_to_update: List[Dict[str, Any]], 
        target_count: int, 
        progress=None, 
        task_id=None
    ) -> Dict[str, Any]:
        """
        Execute the planned replica count updates.

        Args:
            indices_to_update: List of indices to update from plan_replica_updates
            target_count: Target replica count
            progress: Optional Rich progress bar
            task_id: Optional task ID for progress tracking

        Returns:
            dict: Execution results
            
        Raises:
            Exception: If unable to execute replica updates
        """
        try:
            ES_URL = self.es_client.build_es_url()
            if ES_URL is None:
                raise Exception("Could not build Elasticsearch URL")

            successful_updates = []
            failed_updates = []

            for index_info in indices_to_update:
                index_name = index_info['index']

                try:
                    # Update replica count for single index
                    self._update_single_index_replica_count(
                        ES_URL, index_name, target_count
                    )

                    successful_updates.append({
                        'index': index_name,
                        'previous_replicas': index_info['current_replicas'],
                        'new_replicas': target_count,
                        'timestamp': time.time()
                    })

                except Exception as e:
                    failed_updates.append({
                        'index': index_name,
                        'error': str(e),
                        'previous_replicas': index_info.get('current_replicas', 'unknown')
                    })

                # Update progress if provided
                if progress and task_id:
                    progress.advance(task_id)
                    time.sleep(0.1)  # Small delay to show progress

            return {
                'successful_updates': successful_updates,
                'failed_updates': failed_updates,
                'target_count': target_count,
                'total_attempted': len(indices_to_update),
                'success_count': len(successful_updates),
                'failure_count': len(failed_updates)
            }

        except Exception as e:
            raise Exception(f"Failed to execute replica updates: {str(e)}")

    def get_index_replica_settings(self, indices: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get current replica settings for specified indices or all indices.
        
        Args:
            indices: Optional list of specific indices to check
            
        Returns:
            dict: Index replica settings
            
        Raises:
            Exception: If unable to retrieve replica settings
        """
        try:
            ES_URL = self.es_client.build_es_url()
            if ES_URL is None:
                raise Exception("Could not build Elasticsearch URL")

            if indices:
                indices_path = ','.join(indices)
            else:
                indices_path = '_all'

            return self._get_all_index_settings(ES_URL, indices_path)

        except Exception as e:
            raise Exception(f"Failed to get index replica settings: {str(e)}")

    def _get_all_index_settings(self, es_url: str, indices_path: str = '_all') -> Dict[str, Any]:
        """
        Get index settings from Elasticsearch.
        
        Args:
            es_url: Elasticsearch URL
            indices_path: Index path (default: '_all')
            
        Returns:
            dict: Index settings data
            
        Raises:
            Exception: If request fails
        """
        settings_url = f'{es_url}/{indices_path}/_settings?filter_path=*.settings.index.number_of_replicas'

        if self.es_client.elastic_authentication:
            response = requests.get(
                settings_url,
                auth=HTTPBasicAuth(self.es_client.elastic_username, self.es_client.elastic_password),
                verify=False,
                timeout=self.es_client.timeout
            )
        else:
            response = requests.get(
                settings_url, 
                verify=False, 
                timeout=self.es_client.timeout
            )

        response.raise_for_status()
        return response.json()

    def _build_candidate_indices_list(
        self, 
        settings_data: Dict[str, Any], 
        indices: Optional[List[str]], 
        pattern: Optional[str]
    ) -> List[str]:
        """
        Build list of candidate indices based on input criteria.
        
        Args:
            settings_data: Index settings data from Elasticsearch
            indices: Specific indices list
            pattern: Pattern to match indices
            
        Returns:
            list: Candidate index names
        """
        candidate_indices = []

        if indices:
            # Use specific indices provided
            for index_name in indices:
                if index_name in settings_data:
                    candidate_indices.append(index_name)
                else:
                    print(f"Warning: Index '{index_name}' not found in cluster")
        elif pattern:
            # Use pattern matching
            for index_name in settings_data.keys():
                if fnmatch.fnmatch(index_name, pattern):
                    candidate_indices.append(index_name)
        else:
            # Use all indices
            candidate_indices = list(settings_data.keys())

        return candidate_indices

    def _filter_indices_for_updates(
        self, 
        settings_data: Dict[str, Any], 
        candidate_indices: List[str], 
        target_count: int, 
        no_replicas_only: bool
    ) -> tuple:
        """
        Filter candidate indices to determine which need updates.
        
        Args:
            settings_data: Index settings data
            candidate_indices: List of candidate indices
            target_count: Target replica count
            no_replicas_only: Only update indices with 0 replicas
            
        Returns:
            tuple: (indices_to_update, skipped_indices)
        """
        indices_to_update = []
        skipped_indices = []

        for index_name in candidate_indices:
            if index_name not in settings_data:
                continue

            current_replicas = settings_data[index_name].get('settings', {}).get('index', {}).get('number_of_replicas')

            if current_replicas is None:
                skipped_indices.append({
                    'index': index_name,
                    'reason': 'Could not determine current replica count'
                })
                continue

            current_replicas = int(current_replicas)

            # Apply no_replicas_only filter
            if no_replicas_only and current_replicas != 0:
                skipped_indices.append({
                    'index': index_name,
                    'reason': f'Has {current_replicas} replicas (--no-replicas-only specified)'
                })
                continue

            # Check if update is needed
            if current_replicas != target_count:
                indices_to_update.append({
                    'index': index_name,
                    'current_replicas': current_replicas,
                    'target_replicas': target_count
                })
            else:
                skipped_indices.append({
                    'index': index_name,
                    'reason': f'Already has {target_count} replicas'
                })

        return indices_to_update, skipped_indices

    def _update_single_index_replica_count(self, es_url: str, index_name: str, target_count: int):
        """
        Update replica count for a single index.
        
        Args:
            es_url: Elasticsearch URL
            index_name: Name of the index to update
            target_count: Target replica count
            
        Raises:
            Exception: If update fails
        """
        settings_url = f'{es_url}/{index_name}/_settings'
        update_payload = {
            "index": {
                "number_of_replicas": target_count
            }
        }

        if self.es_client.elastic_authentication:
            response = requests.put(
                settings_url,
                json=update_payload,
                auth=HTTPBasicAuth(self.es_client.elastic_username, self.es_client.elastic_password),
                verify=False,
                timeout=self.es_client.timeout
            )
        else:
            response = requests.put(
                settings_url, 
                json=update_payload, 
                verify=False, 
                timeout=self.es_client.timeout
            )

        response.raise_for_status()
