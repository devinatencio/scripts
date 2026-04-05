"""
Location data collection module for ESCMD.

This module handles all business logic for collecting cluster location
and configuration information, separating data gathering from presentation logic.
"""

from collections import defaultdict


class LocationsDataCollector:
    """Handles collection of cluster location and configuration information."""

    def __init__(self):
        """Initialize the locations data collector."""
        pass

    def collect_locations_data(self, configuration_manager):
        """
        Collect all location-related data for display.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            Dictionary containing all location information
        """
        if not configuration_manager.servers_dict:
            return {
                'has_locations': False,
                'error': 'No cluster configurations found',
                'environments': {},
                'total_servers': 0,
                'total_environments': 0,
                'default_cluster': None
            }

        # Group servers by environment
        env_groups = defaultdict(list)
        for location, config in configuration_manager.servers_dict.items():
            env = config.get('env', 'unknown')
            env_groups[env].append((location, config))

        # Sort environments and servers within each environment
        sorted_envs = sorted(env_groups.keys())
        default_cluster = configuration_manager.get_default_cluster()

        # Process each environment
        processed_environments = {}
        total_servers = 0
        global_username = configuration_manager.default_settings.get('elastic_username', '')

        for env in sorted_envs:
            servers = sorted(env_groups[env], key=lambda x: x[0])  # Sort by server name
            processed_servers = []

            for location, config in servers:
                total_servers += 1

                # Determine username and source using proper resolution
                resolved_username = configuration_manager._resolve_username(config)
                server_username = config.get('elastic_username', '')
                json_username = configuration_manager.get_elastic_username_from_json()
                
                if server_username and resolved_username == server_username:
                    username_display = f"{server_username} (server)"
                    username = server_username
                elif json_username and resolved_username == json_username:
                    username_display = f"{json_username} (JSON)"
                    username = json_username
                elif global_username and resolved_username == global_username:
                    username_display = f"{global_username} (global)"
                    username = global_username
                else:
                    username_display = ""
                    username = ""

                processed_server = {
                    'location': location,
                    'hostname': config.get('hostname', ''),
                    'hostname2': config.get('hostname2', ''),
                    'port': config.get('port', ''),
                    'use_ssl': config.get('use_ssl', False),
                    'verify_certs': config.get('verify_certs', False),
                    'username': username_display,
                    'username_raw': username,
                    'is_default': location == default_cluster,
                    'raw_config': config
                }
                processed_servers.append(processed_server)

            processed_environments[env] = {
                'name': env,
                'servers': processed_servers,
                'server_count': len(processed_servers)
            }

        return {
            'has_locations': True,
            'environments': processed_environments,
            'environment_names': sorted_envs,
            'total_servers': total_servers,
            'total_environments': len(sorted_envs),
            'default_cluster': default_cluster,
            'configuration_manager': configuration_manager
        }

    def get_location_details(self, configuration_manager, location_name):
        """
        Get detailed information for a specific location.

        Args:
            configuration_manager: Configuration manager instance
            location_name: Name of the location to get details for

        Returns:
            Dictionary containing detailed location information
        """
        server_config = configuration_manager.get_server_config(location_name)

        if not server_config:
            return {
                'found': False,
                'location_name': location_name,
                'error': f'Location "{location_name}" not found'
            }

        return {
            'found': True,
            'location_name': location_name,
            'hostname': server_config.get('hostname', 'N/A'),
            'hostname2': server_config.get('hostname2', ''),
            'port': server_config.get('port', 9200),
            'environment': server_config.get('env', 'Unknown'),
            'use_ssl': server_config.get('use_ssl', False),
            'verify_certs': server_config.get('verify_certs', False),
            'username': server_config.get('elastic_username', configuration_manager.default_settings.get('elastic_username', '')),
            'is_default': location_name == configuration_manager.get_default_cluster(),
            'raw_config': server_config
        }

    def get_available_locations(self, configuration_manager):
        """
        Get a simple list of all available location names.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            List of location names
        """
        return list(configuration_manager.servers_dict.keys()) if configuration_manager.servers_dict else []

    def get_environment_summary(self, configuration_manager):
        """
        Get summary statistics about environments and clusters.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            Dictionary containing summary statistics
        """
        if not configuration_manager.servers_dict:
            return {
                'total_environments': 0,
                'total_clusters': 0,
                'environments': {},
                'default_cluster': None,
                'ssl_enabled_count': 0,
                'cert_verification_count': 0
            }

        env_groups = defaultdict(list)
        ssl_enabled = 0
        cert_verification = 0

        for location, config in configuration_manager.servers_dict.items():
            env = config.get('env', 'unknown')
            env_groups[env].append(location)

            if config.get('use_ssl', False):
                ssl_enabled += 1
            if config.get('verify_certs', False):
                cert_verification += 1

        environment_summary = {}
        for env, locations in env_groups.items():
            environment_summary[env] = {
                'name': env,
                'cluster_count': len(locations),
                'clusters': sorted(locations)
            }

        return {
            'total_environments': len(env_groups),
            'total_clusters': len(configuration_manager.servers_dict),
            'environments': environment_summary,
            'default_cluster': configuration_manager.get_default_cluster(),
            'ssl_enabled_count': ssl_enabled,
            'cert_verification_count': cert_verification
        }

    def search_locations(self, configuration_manager, search_term):
        """
        Search for locations matching a term.

        Args:
            configuration_manager: Configuration manager instance
            search_term: Term to search for in location names or hostnames

        Returns:
            List of matching location information
        """
        if not configuration_manager.servers_dict or not search_term:
            return []

        search_term = search_term.lower()
        matches = []

        for location, config in configuration_manager.servers_dict.items():
            # Search in location name, hostname, and environment
            searchable_fields = [
                location.lower(),
                config.get('hostname', '').lower(),
                config.get('hostname2', '').lower(),
                config.get('env', '').lower()
            ]

            if any(search_term in field for field in searchable_fields):
                matches.append({
                    'location': location,
                    'hostname': config.get('hostname', ''),
                    'hostname2': config.get('hostname2', ''),
                    'environment': config.get('env', 'unknown'),
                    'match_reason': self._get_match_reason(search_term, location, config)
                })

        return sorted(matches, key=lambda x: x['location'])

    def _get_match_reason(self, search_term, location, config):
        """
        Determine why a location matched the search term.

        Args:
            search_term: The search term used
            location: Location name
            config: Configuration dictionary

        Returns:
            String describing the match reason
        """
        if search_term in location.lower():
            return 'name'
        elif search_term in config.get('hostname', '').lower():
            return 'hostname'
        elif search_term in config.get('hostname2', '').lower():
            return 'hostname2'
        elif search_term in config.get('env', '').lower():
            return 'environment'
        return 'unknown'

    def validate_location_config(self, location_config):
        """
        Validate a location configuration for completeness.

        Args:
            location_config: Configuration dictionary for a location

        Returns:
            Dictionary with validation results
        """
        required_fields = ['hostname', 'port']
        recommended_fields = ['env', 'use_ssl', 'verify_certs']

        missing_required = [field for field in required_fields if not location_config.get(field)]
        missing_recommended = [field for field in recommended_fields if field not in location_config]

        warnings = []
        if location_config.get('use_ssl', False) and not location_config.get('verify_certs', False):
            warnings.append('SSL enabled but certificate verification disabled')

        if not location_config.get('elastic_username'):
            warnings.append('No username configured - may require authentication')

        return {
            'is_valid': len(missing_required) == 0,
            'missing_required': missing_required,
            'missing_recommended': missing_recommended,
            'warnings': warnings,
            'score': self._calculate_config_score(location_config, missing_required, missing_recommended, warnings)
        }

    def _calculate_config_score(self, config, missing_required, missing_recommended, warnings):
        """Calculate a configuration completeness score (0-100)."""
        score = 100

        # Deduct points for missing required fields
        score -= len(missing_required) * 30

        # Deduct points for missing recommended fields
        score -= len(missing_recommended) * 10

        # Deduct points for warnings
        score -= len(warnings) * 5

        return max(0, score)
