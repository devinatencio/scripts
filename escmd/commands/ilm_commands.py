"""
ILM (Index Lifecycle Management) commands for escmd.

This module contains the core ILM operations that interact directly with Elasticsearch.
"""

from .base_command import BaseCommand


class ILMCommands(BaseCommand):
    """Commands for ILM (Index Lifecycle Management) operations."""

    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'ilm'

    def get_ilm_status(self):
        """Get ILM status and basic statistics."""
        try:
            # Get ILM status
            ilm_status = self.es_client.es.ilm.get_status()

            # Get ILM policies
            policies = self.es_client.es.ilm.get_lifecycle()

            # Get ILM explain for all indices to understand phase distribution
            ilm_explain = self.es_client.es.ilm.explain_lifecycle(index="_all")

            # Process phase distribution
            phase_counts = {'hot': 0, 'warm': 0, 'cold': 0, 'frozen': 0, 'delete': 0, 'unmanaged': 0, 'error': 0}

            for index_name, index_info in ilm_explain.get('indices', {}).items():
                if 'managed' in index_info and index_info['managed']:
                    phase = index_info.get('phase', 'unknown')
                    if phase in phase_counts:
                        phase_counts[phase] += 1

                    # Check for errors
                    if 'step_info' in index_info and 'error' in index_info.get('step_info', {}):
                        phase_counts['error'] += 1
                else:
                    phase_counts['unmanaged'] += 1

            return {
                'operation_mode': ilm_status.get('operation_mode', 'UNKNOWN'),
                'policy_count': len(policies),
                'phase_counts': phase_counts,
                'total_managed': sum(phase_counts[p] for p in ['hot', 'warm', 'cold', 'frozen', 'delete']),
                'has_errors': phase_counts['error'] > 0
            }

        except Exception as e:
            return {
                'operation_mode': 'ERROR',
                'error': str(e),
                'policy_count': 0,
                'phase_counts': {'hot': 0, 'warm': 0, 'cold': 0, 'frozen': 0, 'delete': 0, 'unmanaged': 0, 'error': 0},
                'total_managed': 0,
                'has_errors': False
            }

    def get_ilm_policies(self):
        """Get all ILM policies."""
        try:
            return self.es_client.es.ilm.get_lifecycle()
        except Exception as e:
            return {"error": str(e)}

    def get_ilm_policy_detail(self, policy_name):
        """Get detailed information for a specific ILM policy."""
        try:
            # Get the specific policy
            policy_data = self.es_client.es.ilm.get_lifecycle(policy=policy_name)

            if policy_name not in policy_data:
                return {"error": f"Policy '{policy_name}' not found"}

            policy_info = policy_data[policy_name]

            # Get indices using this policy
            try:
                all_explain = self.es_client.es.ilm.explain_lifecycle(index="_all")
                using_indices = []

                for index_name, index_info in all_explain.get('indices', {}).items():
                    if index_info.get('policy') == policy_name:
                        using_indices.append({
                            'name': index_name,
                            'phase': index_info.get('phase', 'N/A'),
                            'action': index_info.get('action', 'N/A'),
                            'managed': index_info.get('managed', False)
                        })

                policy_info['using_indices'] = using_indices
            except:
                policy_info['using_indices'] = []

            return {policy_name: policy_info}

        except Exception as e:
            return {"error": str(e)}

    def get_ilm_explain(self, index_name):
        """Get ILM explain for specific index."""
        try:
            return self.es_client.es.ilm.explain_lifecycle(index=index_name)
        except Exception as e:
            error_msg = str(e)
            # Check if this might be a policy name instead of index name
            if "index_not_found_exception" in error_msg:
                # Get list of policies to check if the user provided a policy name
                try:
                    policies = self.get_ilm_policies()
                    if not isinstance(policies, dict) or 'error' in policies:
                        return {"error": f"Index not found: {error_msg}"}

                    if index_name in policies:
                        return {"error": f"'{index_name}' is an ILM policy name, not an index name. Use 'ilm explain <index-name>' with an actual index name, not a policy name."}
                except:
                    pass

                return {"error": f"Index '{index_name}' not found. Make sure you're using an index name (not a policy name). Use './escmd.py indices' to see available indices."}

            return {"error": error_msg}

    def get_ilm_policy_index_patterns(self, policy_name):
        """Get unique index patterns (date/sequence stripped) for a specific ILM policy."""
        import re

        try:
            policy_detail = self.get_ilm_policy_detail(policy_name)

            if 'error' in policy_detail:
                return {'error': policy_detail['error']}

            policy_info = policy_detail.get(policy_name, {})
            using_indices = policy_info.get('using_indices', [])

            patterns = {}
            for index_info in using_indices:
                index_name = index_info['name']
                pattern = self._extract_index_pattern(index_name)

                if pattern not in patterns:
                    patterns[pattern] = {
                        'pattern': pattern,
                        'count': 0,
                        'phases': set(),
                        'indices': [],
                    }
                patterns[pattern]['count'] += 1
                phase = index_info.get('phase', 'N/A')
                if phase and phase != 'N/A':
                    patterns[pattern]['phases'].add(phase)
                patterns[pattern]['indices'].append(index_name)

            result_patterns = []
            for _p, data in sorted(patterns.items()):
                result_patterns.append({
                    'pattern': data['pattern'],
                    'count': data['count'],
                    'phases': sorted(list(data['phases'])),
                    'indices': sorted(data['indices']),
                })

            return {
                'policy_name': policy_name,
                'total_indices': len(using_indices),
                'unique_patterns': len(result_patterns),
                'patterns': result_patterns,
            }

        except Exception as e:
            return {'error': str(e)}

    def _extract_index_pattern(self, index_name):
        """Strip date and sequence suffixes from an index name to derive its base pattern."""
        import re
        # .ds-<base>-YYYY.MM.DD-NNNNNN  (datastream backing indices)
        result = re.sub(r'-\d{4}\.\d{2}\.\d{2}-\d+$', '', index_name)
        if result != index_name:
            return result
        # <base>-YYYY.MM.DD
        result = re.sub(r'-\d{4}\.\d{2}\.\d{2}$', '', index_name)
        if result != index_name:
            return result
        # <base>-YYYYMMDD
        result = re.sub(r'-\d{8}$', '', index_name)
        if result != index_name:
            return result
        return index_name

    def get_ilm_errors(self):
        """Get indices with ILM errors."""
        try:
            ilm_explain = self.es_client.es.ilm.explain_lifecycle(index="_all")
            errors = {}

            for index_name, index_info in ilm_explain.get('indices', {}).items():
                if 'step_info' in index_info and 'error' in index_info.get('step_info', {}):
                    errors[index_name] = index_info

            return errors
        except Exception as e:
            return {"error": str(e)}

    def remove_ilm_policy(self, indices_pattern, dry_run=False):
        """Remove ILM policy from indices matching a pattern."""
        try:
            # Get indices that match the pattern
            all_indices = self.es_client.es.cat.indices(format="json")
            matching_indices = []

            import re
            pattern_regex = re.compile(indices_pattern.replace('*', '.*'))

            for index_info in all_indices:
                index_name = index_info['index']
                if pattern_regex.match(index_name):
                    matching_indices.append(index_name)

            if not matching_indices:
                return {"error": f"No indices found matching pattern: {indices_pattern}"}

            results = []
            for index_name in matching_indices:
                try:
                    if dry_run:
                        # Just report what would be done
                        results.append({
                            'index': index_name,
                            'action': 'would_remove_policy',
                            'status': 'dry_run'
                        })
                    else:
                        # Actually remove the policy
                        self.es_client.es.ilm.remove_policy(index=index_name)
                        results.append({
                            'index': index_name,
                            'action': 'removed_policy',
                            'status': 'success'
                        })
                except Exception as e:
                    results.append({
                        'index': index_name,
                        'action': 'remove_policy',
                        'status': 'error',
                        'error': str(e)
                    })

            return {
                'pattern': indices_pattern,
                'matched_indices': len(matching_indices),
                'results': results,
                'dry_run': dry_run
            }

        except Exception as e:
            return {"error": str(e)}

    def set_ilm_policy(self, indices_pattern, policy_name, dry_run=False):
        """Set ILM policy for indices matching a pattern."""
        try:
            # First verify the policy exists
            try:
                policy_data = self.es_client.es.ilm.get_lifecycle(policy=policy_name)
                if policy_name not in policy_data:
                    return {"error": f"ILM policy '{policy_name}' not found"}
            except Exception as e:
                return {"error": f"Error checking policy '{policy_name}': {str(e)}"}

            # Get indices that match the pattern
            all_indices = self.es_client.es.cat.indices(format="json")
            matching_indices = []

            import re
            pattern_regex = re.compile(indices_pattern.replace('*', '.*'))

            for index_info in all_indices:
                index_name = index_info['index']
                if pattern_regex.match(index_name):
                    matching_indices.append(index_name)

            if not matching_indices:
                return {"error": f"No indices found matching pattern: {indices_pattern}"}

            results = []
            for index_name in matching_indices:
                try:
                    if dry_run:
                        # Just report what would be done
                        results.append({
                            'index': index_name,
                            'action': f'would_set_policy_{policy_name}',
                            'status': 'dry_run'
                        })
                    else:
                        # Actually set the policy
                        self.es_client.es.ilm.explain_lifecycle(index=index_name)  # Check if manageable first

                        # Set the policy
                        body = {
                            "policy": policy_name
                        }
                        self.es_client.es.transport.perform_request(
                            'PUT',
                            f'/{index_name}/_settings',
                            body={
                                "index": {
                                    "lifecycle": body
                                }
                            }
                        )

                        results.append({
                            'index': index_name,
                            'action': f'set_policy_{policy_name}',
                            'status': 'success'
                        })
                except Exception as e:
                    results.append({
                        'index': index_name,
                        'action': f'set_policy_{policy_name}',
                        'status': 'error',
                        'error': str(e)
                    })

            return {
                'pattern': indices_pattern,
                'policy': policy_name,
                'matched_indices': len(matching_indices),
                'results': results,
                'dry_run': dry_run
            }

        except Exception as e:
            return {"error": str(e)}

    def _clear_rc_snapshots_cache(self):
        """Clear the rc_snapshots indices cache."""
        if hasattr(self, '_rc_snapshots_cache'):
            delattr(self, '_rc_snapshots_cache')

    def _get_rc_snapshots_indices_cache(self):
        """
        Get all indices from rc_snapshots index and cache them in a set for efficient lookup.
        Returns a set of index names managed by the S3-Snapshot utility.
        """
        # Check if we already have a cached version for this ILM check
        if hasattr(self, '_rc_snapshots_cache'):
            return self._rc_snapshots_cache

        # Initialize cache as empty set
        self._rc_snapshots_cache = set()

        try:
            # Get rc_snapshots index name from configuration
            rc_snapshots_index = 'rc_snapshots'  # Default

            if hasattr(self.es_client, 'configuration_manager') and self.es_client.configuration_manager:
                config = self.es_client.configuration_manager.main_config or {}
                settings = config.get('settings', {})
                rc_snapshots_index = settings.get('restored_snapshots_index', 'rc_snapshots')

            # Check if rc_snapshots index exists
            try:
                index_exists = self.es_client.es.indices.exists(index=rc_snapshots_index)
                if not index_exists:
                    return self._rc_snapshots_cache
            except Exception:
                # If we can't check index existence, return empty cache
                return self._rc_snapshots_cache

            # Get all documents from rc_snapshots index
            query = {
                "query": {
                    "match_all": {}
                },
                "size": 10000,  # Reasonable limit for restored snapshots
                "_source": ["index_name"]
            }

            try:
                result = self.es_client.es.search(index=rc_snapshots_index, body=query)
                hits = result.get("hits", {}).get("hits", [])

                for hit in hits:
                    source = hit.get("_source", {})
                    index_name = source.get("index_name")
                    if index_name:
                        self._rc_snapshots_cache.add(index_name)

            except Exception:
                # If query fails, cache remains empty
                pass

        except Exception:
            # If any error occurs, cache remains empty
            pass

        return self._rc_snapshots_cache

    def _is_index_managed_by_s3(self, index_name):
        """
        Check if an index is managed by the S3-Snapshot utility.
        This includes indices in rc_snapshots AND the rc_snapshots system indices.
        Returns True if the index is managed by the custom ILM utility.
        """
        # Define system indices that are part of the S3-Snapshot utility
        rc_system_indices = {
            'rc_snapshots',
            'rc_snapshots_ilm',
            'rc_snapshots_ilm_failed',
            'rc_snapshots_history'
        }

        # Check if it's a system index
        if index_name in rc_system_indices:
            return True

        # Check if it's in the rc_snapshots cache
        rc_indices_cache = self._get_rc_snapshots_indices_cache()
        return index_name in rc_indices_cache

    def check_ilm_errors(self):
        """
        Check for ILM errors by calling the ILM explain API and looking for STEP = error.
        Returns a list of indices with ILM errors.
        """
        import requests
        from requests.auth import HTTPBasicAuth

        try:
            ES_URL = self.es_client.build_es_url()
            if ES_URL is None:
                return []

            # Call ILM explain API with filter to get detailed error information
            explain_url = f'{ES_URL}/_all/_ilm/explain?pretty&filter_path=indices.*,indices.*.policy,indices.*.step,indices.*.step_info,indices.*.failed_step,indices.*.phase,indices.*.action,indices.*.step_time,indices.*.is_auto_retryable_error,indices.*.failed_step_retry_count'

            if self.es_client.elastic_authentication == True:
                response = requests.get(
                    explain_url,
                    auth=HTTPBasicAuth(self.es_client.elastic_username, self.es_client.elastic_password),
                    verify=False,
                    timeout=self.es_client.timeout
                )
            else:
                response = requests.get(explain_url, verify=False, timeout=self.es_client.timeout)

            response.raise_for_status()

            data = response.json()
            error_indices = []
            no_policy_indices = []
            managed_indices_count = 0

            if 'indices' in data:
                for index_name, index_data in data['indices'].items():
                    # Check if index has any ILM policy
                    if not index_data.get('policy') or index_data.get('policy') == '':
                        # Check if this index is managed by the S3-Snapshot utility
                        if self._is_index_managed_by_s3(index_name):
                            no_policy_indices.append({
                                'index': index_name,
                                'reason': 'S3-Snapshot managed'
                            })
                        else:
                            no_policy_indices.append({
                                'index': index_name,
                                'reason': 'No ILM policy attached'
                            })
                    elif 'step' in index_data and index_data['step'] == 'ERROR':
                        # Index has policy but is in error state
                        error_info = {
                            'index': index_name,
                            'policy': index_data.get('policy', 'Unknown'),
                            'step': index_data.get('step'),
                            'phase': index_data.get('phase', 'Unknown'),
                            'action': index_data.get('action', 'Unknown'),
                            'step_time': index_data.get('step_time', 'Unknown'),
                            'failed_step': index_data.get('failed_step', 'Unknown'),
                            'step_info': index_data.get('step_info', {}),
                            'phase_time': index_data.get('phase_time', 'Unknown'),
                            'action_time': index_data.get('action_time', 'Unknown'),
                            'step_time_millis': index_data.get('step_time_millis', 'Unknown'),
                            'is_auto_retryable_error': index_data.get('is_auto_retryable_error', False),
                            'failed_step_retry_count': index_data.get('failed_step_retry_count', 0)
                        }
                        error_indices.append(error_info)
                    else:
                        # Index has policy and is working correctly
                        managed_indices_count += 1

            # Clear cache before returning results
            self._clear_rc_snapshots_cache()

            # Return comprehensive ILM status
            return {
                'errors': error_indices,
                'no_policy': no_policy_indices,
                'managed_count': managed_indices_count,
                'total_indices': len(data.get('indices', {}))
            }

        except requests.exceptions.HTTPError as e:
            # Clear cache on error
            self._clear_rc_snapshots_cache()
            if e.response.status_code == 405:
                # ILM not supported on this cluster
                return {'not_supported': True, 'reason': 'ILM API not available on this cluster (older ES version or ILM disabled)'}
            else:
                print(f"Error checking ILM status: {str(e)}")
                return []
        except Exception as e:
            # Clear cache on error
            self._clear_rc_snapshots_cache()
            print(f"Error checking ILM status: {str(e)}")
            return []
