"""
Settings data collection module for ESCMD.

This module handles all business logic for collecting configuration settings
and cluster information, separating data gathering from presentation logic.
"""

import os
from collections import defaultdict


class SettingsDataCollector:
    """Handles collection of configuration settings and cluster information."""

    def __init__(self):
        """Initialize the settings data collector."""
        pass

    def collect_settings_data(self, configuration_manager):
        """
        Collect all settings-related data for display.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            Dictionary containing all settings information
        """
        settings = configuration_manager.default_settings
        default_cluster = configuration_manager.get_default_cluster()

        return {
            'default_cluster': default_cluster,
            'settings': settings,
            'clusters': self._collect_cluster_data(configuration_manager),
            'authentication': self._collect_authentication_data(configuration_manager),
            'username_configuration': self._collect_username_configuration(configuration_manager),
            'configuration_files': self._collect_file_info(configuration_manager),
            'environment_overrides': self._collect_environment_overrides(),
            'has_clusters': bool(configuration_manager.servers_dict),
            'total_clusters': len(configuration_manager.servers_dict) if configuration_manager.servers_dict else 0
        }

    def _collect_cluster_data(self, configuration_manager):
        """
        Collect cluster configuration data.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            List of cluster information dictionaries
        """
        if not configuration_manager.servers_dict:
            return []

        clusters = []
        default_cluster = configuration_manager.get_default_cluster()

        # Sort clusters by name
        sorted_servers = sorted(configuration_manager.servers_dict.items())

        for location, config in sorted_servers:
            # Determine if this is the default cluster
            is_default = (location == default_cluster or
                         location == default_cluster.lower() if default_cluster else False)

            cluster_info = {
                'name': location,
                'is_default': is_default,
                'environment': config.get('env', ''),
                'hostname': config.get('hostname', 'N/A'),
                'hostname2': config.get('hostname2', ''),
                'port': config.get('port', 9200),
                'use_ssl': config.get('use_ssl', False),
                'verify_certs': config.get('verify_certs', False),
                'has_authentication': config.get('elastic_authentication', False),
                'username': config.get('elastic_username', ''),
                'raw_config': config
            }
            clusters.append(cluster_info)

        return clusters

    def _collect_authentication_data(self, configuration_manager):
        """
        Collect authentication configuration data.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            List of authentication information dictionaries
        """
        if not configuration_manager.servers_dict:
            return []

        auth_data = []
        global_username = configuration_manager.default_settings.get('elastic_username', 'Not set')
        sorted_servers = sorted(configuration_manager.servers_dict.items())
        default_cluster = configuration_manager.get_default_cluster()

        for location, config in sorted_servers:
            # Skip clusters that don't use authentication
            if not config.get('elastic_authentication'):
                continue

            # Determine if this is the default cluster
            is_default = (location == default_cluster or
                         location == default_cluster.lower() if default_cluster else False)

            # Determine username source and value using the proper resolution method
            resolved_username = configuration_manager._resolve_username(config)
            cluster_username = config.get('elastic_username')
            env_username = config.get('env', {}).get('elastic_username') if isinstance(config.get('env'), dict) else None
            json_username = configuration_manager.get_elastic_username_from_json()

            if cluster_username and resolved_username == cluster_username:
                username_source = "Cluster Config"
                username = cluster_username
            elif env_username and resolved_username == env_username:
                username_source = "Environment Config"
                username = env_username
            elif json_username and resolved_username == json_username:
                username_source = "JSON Config"
                username = json_username
            elif global_username != 'Not set' and resolved_username == global_username:
                username_source = "Global Config"
                username = global_username
            else:
                username_source = "None"
                username = "❌ Not configured"

            # Determine password source
            cluster_password = config.get('elastic_password')
            if cluster_password:
                password_source = "Cluster Config (plaintext)"
                password_status = "🔶 Plaintext"
                password_secure = False
            else:
                password_source = "Encrypted Storage"
                password_status = "🔒 Encrypted"
                password_secure = True

            auth_info = {
                'cluster_name': location,
                'is_default': is_default,
                'username_source': username_source,
                'username': username,
                'password_source': password_source,
                'password_status': password_status,
                'password_secure': password_secure,
                'has_auth': True
            }
            auth_data.append(auth_info)

        return auth_data

    def _collect_username_configuration(self, configuration_manager):
        """
        Collect username configuration data showing current settings and resolution order.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            Dictionary containing username configuration information
        """
        # Get different username sources
        json_username = configuration_manager.get_elastic_username_from_json()
        global_username = configuration_manager.default_settings.get('elastic_username')
        resolved_username = configuration_manager._resolve_username({})  # Empty server config for default resolution

        # Check if there are any environment variable overrides
        env_username = None
        if hasattr(configuration_manager, 'config_manager'):
            # Check if there are any environment-specific username settings
            for location, config in (configuration_manager.servers_dict or {}).items():
                env_config = config.get('env')
                if isinstance(env_config, dict) and env_config.get('elastic_username'):
                    env_username = env_config.get('elastic_username')
                    break

        # Determine the active source
        active_source = "Not configured"
        if resolved_username:
            if json_username and resolved_username == json_username:
                active_source = "JSON Config"
            elif global_username and resolved_username == global_username:
                active_source = "Global Config"
            elif env_username and resolved_username == env_username:
                active_source = "Environment Config"
            else:
                # Check if it's from a server-level config
                active_source = "Server Config"

        return {
            'json_username': json_username,
            'global_username': global_username,
            'environment_username': env_username,
            'resolved_username': resolved_username,
            'active_source': active_source,
            'has_json_config': bool(json_username),
            'has_global_config': bool(global_username),
            'has_environment_config': bool(env_username),
            'is_configured': bool(resolved_username),
            'priority_order': [
                {
                    'level': 1,
                    'source': 'Server-level Config',
                    'description': 'Username defined in individual cluster configuration',
                    'active': active_source == 'Server Config'
                },
                {
                    'level': 2,
                    'source': 'Environment Config',
                    'description': 'Username from environment-specific settings',
                    'active': active_source == 'Environment Config',
                    'configured': bool(env_username)
                },
                {
                    'level': 3,
                    'source': 'JSON Config',
                    'description': f'Username from {configuration_manager.state_file_path}',
                    'active': active_source == 'JSON Config',
                    'configured': bool(json_username),
                    'value': json_username
                },
                {
                    'level': 4,
                    'source': 'Global Config',
                    'description': 'Username from YAML configuration file',
                    'active': active_source == 'Global Config',
                    'configured': bool(global_username),
                    'value': global_username
                }
            ]
        }

    def _collect_file_info(self, configuration_manager):
        """
        Collect configuration file information.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            Dictionary containing file information
        """
        file_info = {
            'is_dual_file_mode': configuration_manager.is_dual_file_mode,
            'files': []
        }

        if configuration_manager.is_dual_file_mode:
            # Dual-file mode: check both config files
            main_exists = os.path.exists(configuration_manager.main_config_path)
            servers_exists = os.path.exists(configuration_manager.servers_config_path)

            file_info['files'].extend([
                {
                    'type': 'Main Config',
                    'path': configuration_manager.main_config_path,
                    'exists': main_exists,
                    'status': "✅ Found" if main_exists else "❌ Missing",
                    'description': 'Main configuration settings'
                },
                {
                    'type': 'Servers Config',
                    'path': configuration_manager.servers_config_path,
                    'exists': servers_exists,
                    'status': "✅ Found" if servers_exists else "❌ Missing",
                    'description': 'Cluster server definitions'
                }
            ])
        else:
            # Single-file mode: check single config file
            config_exists = os.path.exists(configuration_manager.config_file_path)
            file_info['files'].append({
                'type': 'Configuration',
                'path': configuration_manager.config_file_path,
                'exists': config_exists,
                'status': "✅ Found" if config_exists else "❌ Missing",
                'description': 'Combined configuration file'
            })

        return file_info

    def _collect_environment_overrides(self):
        """
        Collect environment variable overrides.

        Returns:
            Dictionary containing environment override information
        """
        overrides = {}

        # Check for ASCII mode override
        env_ascii = os.environ.get('ESCMD_ASCII_MODE', '').lower() in ('true', '1', 'yes')
        if env_ascii:
            overrides['ascii_mode'] = {
                'variable': 'ESCMD_ASCII_MODE',
                'value': 'True',
                'description': 'Forces ASCII mode output'
            }

        # Check for other common environment overrides
        env_vars_to_check = {
            'ESCMD_THEME': 'Theme override',
            'ESCMD_TIMEOUT': 'Connection timeout override',
            'ESCMD_DEBUG': 'Debug mode override',
            'ESCMD_NO_COLOR': 'Disable color output'
        }

        for env_var, description in env_vars_to_check.items():
            value = os.environ.get(env_var)
            if value:
                overrides[env_var.lower().replace('escmd_', '')] = {
                    'variable': env_var,
                    'value': value,
                    'description': description
                }

        return overrides

    def get_setting_descriptions(self):
        """
        Get descriptions for configuration settings.

        Returns:
            Dictionary mapping setting names to descriptions
        """
        return {
            'box_style': 'Rich table border style',
            'health_style': 'Health command display mode',
            'classic_style': 'Classic health display format',
            'enable_paging': 'Auto-enable pager for long output',
            'paging_threshold': 'Line count threshold for paging',
            'ilm_display_limit': 'Max ILM unmanaged indices to show before truncating',
            'show_legend_panels': 'Show legend panels in output',
            'ascii_mode': 'Use plain text instead of Unicode',
            'display_theme': 'Color theme (rich/plain) for universal compatibility',
            'connection_timeout': 'ES connection timeout (seconds)',
            'read_timeout': 'ES read timeout (seconds)',
            'flush_timeout': 'ES flush command HTTP timeout (seconds)',
            'dangling_cleanup.max_retries': 'Max retries for dangling operations',
            'dangling_cleanup.retry_delay': 'Delay between retries (seconds)',
            'dangling_cleanup.timeout': 'Operation timeout (seconds)',
            'dangling_cleanup.default_log_level': 'Default logging level',
            'dangling_cleanup.enable_progress_bar': 'Show progress bars',
            'dangling_cleanup.confirmation_required': 'Require user confirmation'
        }

    def analyze_security_posture(self, settings_data):
        """
        Analyze the security posture of the configuration.

        Args:
            settings_data: Settings data dictionary

        Returns:
            Dictionary containing security analysis
        """
        analysis = {
            'total_clusters': settings_data['total_clusters'],
            'ssl_enabled': 0,
            'ssl_verified': 0,
            'auth_enabled': 0,
            'plaintext_passwords': 0,
            'secure_passwords': 0,
            'security_score': 0,
            'recommendations': []
        }

        if not settings_data['clusters']:
            return analysis

        for cluster in settings_data['clusters']:
            if cluster['use_ssl']:
                analysis['ssl_enabled'] += 1
            if cluster['verify_certs']:
                analysis['ssl_verified'] += 1
            if cluster['has_authentication']:
                analysis['auth_enabled'] += 1

        for auth in settings_data['authentication']:
            if not auth['password_secure']:
                analysis['plaintext_passwords'] += 1
            else:
                analysis['secure_passwords'] += 1

        # Calculate security score (0-100)
        total = settings_data['total_clusters']
        if total > 0:
            ssl_score = (analysis['ssl_enabled'] / total) * 30
            cert_score = (analysis['ssl_verified'] / total) * 25
            auth_score = (analysis['auth_enabled'] / total) * 25
            password_score = 0
            if analysis['auth_enabled'] > 0:
                password_score = (analysis['secure_passwords'] / analysis['auth_enabled']) * 20
            analysis['security_score'] = int(ssl_score + cert_score + auth_score + password_score)

        # Generate recommendations
        if analysis['ssl_enabled'] < total:
            analysis['recommendations'].append('Enable SSL for all clusters')
        if analysis['ssl_verified'] < analysis['ssl_enabled']:
            analysis['recommendations'].append('Enable certificate verification for SSL connections')
        if analysis['auth_enabled'] < total:
            analysis['recommendations'].append('Enable authentication for all clusters')
        if analysis['plaintext_passwords'] > 0:
            analysis['recommendations'].append('Avoid storing passwords in plaintext')

        return analysis

    def validate_configuration(self, configuration_manager):
        """
        Validate the overall configuration for completeness and issues.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            Dictionary containing validation results
        """
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'info': [],
            'score': 100
        }

        # Check for default cluster
        if not configuration_manager.get_default_cluster():
            validation['warnings'].append('No default cluster configured')
            validation['score'] -= 10

        # Check configuration files
        file_info = self._collect_file_info(configuration_manager)
        missing_files = [f for f in file_info['files'] if not f['exists']]
        if missing_files:
            validation['errors'].extend([f"Missing file: {f['path']}" for f in missing_files])
            validation['is_valid'] = False
            validation['score'] -= 30

        # Check clusters
        if not configuration_manager.servers_dict:
            validation['errors'].append('No clusters configured')
            validation['is_valid'] = False
            validation['score'] -= 50
        else:
            # Check each cluster
            for location, config in configuration_manager.servers_dict.items():
                if not config.get('hostname'):
                    validation['errors'].append(f"Cluster '{location}' missing hostname")
                    validation['score'] -= 15

                if config.get('use_ssl') and not config.get('verify_certs'):
                    validation['warnings'].append(f"Cluster '{location}' has SSL but no cert verification")
                    validation['score'] -= 5

        # Environment checks
        overrides = self._collect_environment_overrides()
        if overrides:
            validation['info'].append(f"Environment overrides active: {', '.join(overrides.keys())}")

        validation['score'] = max(0, validation['score'])
        return validation

    def export_for_backup(self, configuration_manager):
        """
        Export configuration data suitable for backup/restore operations.

        Args:
            configuration_manager: Configuration manager instance

        Returns:
            Dictionary containing exportable configuration
        """
        return {
            'export_timestamp': os.path.getmtime(configuration_manager.config_file_path) if hasattr(configuration_manager, 'config_file_path') and os.path.exists(configuration_manager.config_file_path) else None,
            'default_cluster': configuration_manager.get_default_cluster(),
            'settings': configuration_manager.default_settings,
            'servers': configuration_manager.servers_dict,
            'file_mode': 'dual' if configuration_manager.is_dual_file_mode else 'single',
            'version': '1.0',
            'cluster_count': len(configuration_manager.servers_dict) if configuration_manager.servers_dict else 0
        }
