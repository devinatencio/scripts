import json
import os
import re
import yaml
from rich.console import Console
from rich.table import Table
from rich import box
from utils import load_json_tolerant as _load_json_tolerant


class ConfigurationManager:
    def __init__(
        self,
        config_file_path=None,
        state_file_path=None,
        main_config_path=None,
        servers_config_path=None,
    ):
        """
        Initialize ConfigurationManager with support for dual-file configuration.

        Args:
            config_file_path: Legacy single-file configuration path (for backward compatibility)
            state_file_path: State file path
            main_config_path: Path to main configuration file (escmd.yml)
            servers_config_path: Path to servers configuration file (elastic_servers.yml)
        """
        self.state_file_path = state_file_path or "test_state.json"

        # Determine configuration mode: dual-file or legacy single-file
        if main_config_path or servers_config_path:
            # Dual-file mode (new approach)
            self.main_config_path = main_config_path or "escmd.yml"
            self.servers_config_path = servers_config_path or "elastic_servers.yml"
            self.config_file_path = None  # Not used in dual-file mode
            self.is_dual_file_mode = True
            self._load_dual_file_config()
        elif config_file_path:
            # Legacy single-file mode (backward compatibility)
            self.config_file_path = config_file_path
            self.main_config_path = None
            self.servers_config_path = None
            self.is_dual_file_mode = False
            self._load_single_file_config()
        else:
            # Auto-detect mode: try dual-file first, fallback to single-file
            # Resolve config files relative to the state file's directory
            # so they work regardless of cwd (important for Nuitka onefile builds).
            _base = os.path.dirname(os.path.abspath(self.state_file_path))
            _main_candidate = os.path.join(_base, "escmd.yml")
            _servers_candidate = os.path.join(_base, "elastic_servers.yml")
            if os.path.exists(_main_candidate) or os.path.exists(_servers_candidate):
                self.main_config_path = _main_candidate
                self.servers_config_path = _servers_candidate
                self.config_file_path = None
                self.is_dual_file_mode = True
                self._load_dual_file_config()
            else:
                # Fallback to single-file mode with default path
                self.config_file_path = os.path.join(_base, "elastic_servers.yml")
                self.main_config_path = None
                self.servers_config_path = None
                self.is_dual_file_mode = False
                self._load_single_file_config()

        self.box_style = self._get_box_style()

    def _load_dual_file_config(self):
        """
        Load configuration from separate main and servers files.
        """
        # Load main configuration (settings, cluster_groups, passwords)
        self.main_config = self._read_yaml_file(self.main_config_path)
        self.default_settings = (
            self.main_config.get("settings", {}) if self.main_config else {}
        )
        self.cluster_groups_raw = (
            self.main_config.get("cluster_groups", {}) if self.main_config else {}
        )
        self.cluster_groups = self._normalize_cluster_groups(self.cluster_groups_raw)
        self.passwords = (
            self.main_config.get("passwords", {}) if self.main_config else {}
        )
        self.auth_profiles = self._normalize_auth_profiles(
            (self.main_config or {}).get("auth_profiles")
        )

        # Load servers configuration
        self.servers_config = self._read_yaml_file(self.servers_config_path)
        self.servers_settings = (
            self.servers_config.get(
                "servers",
                [
                    {
                        "name": "DEFAULT",
                        "hostname": "localhost",
                        "port": 9200,
                        "use_ssl": False,
                    }
                ],
            )
            if self.servers_config
            else [
                {
                    "name": "DEFAULT",
                    "hostname": "localhost",
                    "port": 9200,
                    "use_ssl": False,
                }
            ]
        )
        self.servers_dict = self._convert_dict_list_to_dict(self.servers_settings)

        # Combined config for compatibility with existing methods
        self.config = {**self.main_config, "servers": self.servers_settings}

    def _load_single_file_config(self):
        """
        Load configuration from single legacy file (backward compatibility).
        """
        self.config = self._read_yaml_file(self.config_file_path)
        self.default_settings = self.config.get("settings", {}) if self.config else {}
        self.servers_settings = (
            self.config.get(
                "servers",
                [
                    {
                        "name": "DEFAULT",
                        "hostname": "localhost",
                        "port": 9200,
                        "use_ssl": False,
                    }
                ],
            )
            if self.config
            else [
                {
                    "name": "DEFAULT",
                    "hostname": "localhost",
                    "port": 9200,
                    "use_ssl": False,
                }
            ]
        )
        self.servers_dict = self._convert_dict_list_to_dict(self.servers_settings)
        self.cluster_groups_raw = (
            self.config.get("cluster_groups", {}) if self.config else {}
        )
        self.cluster_groups = self._normalize_cluster_groups(self.cluster_groups_raw)
        self.passwords = self.config.get("passwords", {}) if self.config else {}
        self.auth_profiles = self._normalize_auth_profiles(
            (self.config or {}).get("auth_profiles")
        )

    def _normalize_auth_profiles(self, raw):
        """
        Normalize auth_profiles from YAML to a dict of profile_name -> settings dict.

        Invalid or non-dict entries are skipped.
        """
        if not raw or not isinstance(raw, dict):
            return {}
        out = {}
        for name, body in raw.items():
            if not name or not isinstance(name, str):
                continue
            key = name.strip()
            if not key:
                continue
            if isinstance(body, dict):
                out[key] = body
        return out

    def _read_yaml_file(self, file_path=None):
        """
        Read and parse a YAML configuration file.

        Args:
            file_path (str, optional): Path to the YAML file. If None, uses self.config_file_path

        Returns:
            dict: The parsed YAML configuration
        """
        path_to_read = file_path if file_path is not None else self.config_file_path
        if not path_to_read:
            return {}

        try:
            if os.path.exists(path_to_read):
                with open(path_to_read, "r") as file:
                    return yaml.safe_load(file)
        except (yaml.YAMLError, PermissionError, OSError) as e:
            print(f"Warning: Could not read configuration file {path_to_read}: {e}")
            # Return empty dict on any file reading or YAML parsing errors
            pass
        return {}

    def _normalize_cluster_groups(self, raw_cluster_groups):
        """
        Convert cluster groups to normalized format for backward compatibility.

        Args:
            raw_cluster_groups: Raw cluster groups from configuration

        Returns:
            dict: Normalized cluster groups {group_name: [cluster_list]}
        """
        normalized_groups = {}
        for group_name, group_data in raw_cluster_groups.items():
            if isinstance(group_data, dict) and "clusters" in group_data:
                # New format with description and clusters
                normalized_groups[group_name] = group_data["clusters"]
            elif isinstance(group_data, list):
                # Old format - just a list of clusters
                normalized_groups[group_name] = group_data
            else:
                # Handle unexpected format
                normalized_groups[group_name] = []
        return normalized_groups

    def _convert_dict_list_to_dict(self, servers_list):
        """
        Convert a list of dictionaries into a single dictionary using the 'name' key.

        Args:
            servers_list (list): List of dictionaries, each containing a 'name' key.

        Returns:
            dict: Dictionary with 'name' values as keys and remaining data as values.
        """
        result_dict = {}
        for item in servers_list:
            name = item.pop("name").lower()
            result_dict[name] = item
        return result_dict

    def _get_box_style(self):
        """
        Get the box style from configuration or return default.

        Returns:
            box: The box style to use for tables
        """
        box_style_string = self.default_settings.get("box_style", "SQUARE_DOUBLE_HEAD")
        box_styles = {
            "SIMPLE": box.SIMPLE,
            "ASCII": box.ASCII,
            "SQUARE": box.SQUARE,
            "ROUNDED": box.ROUNDED,
            "SQUARE_DOUBLE_HEAD": box.SQUARE_DOUBLE_HEAD,
        }
        return box_styles.get(box_style_string)

    def get_paging_enabled(self):
        """
        Get whether paging is enabled from configuration.

        Returns:
            bool: True if paging is enabled, False otherwise (defaults to False)
        """
        return self.default_settings.get("enable_paging", False)

    def get_paging_threshold(self):
        """
        Get the paging threshold from configuration.

        Returns:
            int: Number of items that triggers automatic paging
        """
        return self.default_settings.get("paging_threshold", 50)

    def get_show_legend_panels(self):
        """
        Get whether legend and quick actions panels should be shown.

        Returns:
            bool: True if legend panels should be shown, False otherwise (defaults to False)
        """
        return self.default_settings.get("show_legend_panels", False)

    def get_ascii_mode(self):
        """
        Get whether ASCII mode is enabled from configuration.

        Returns:
            bool: True if ASCII mode is enabled, False otherwise (defaults to False)
        """
        return self.default_settings.get("ascii_mode", False)

    def get_show_hidden_datastreams(self):
        """
        Get whether hidden/system datastreams should be shown.

        Returns:
            bool: True if hidden datastreams should be shown, False otherwise (defaults to False)
        """
        return self.default_settings.get("show_hidden_datastreams", False)

    def get_ilm_display_limit(self):
        """
        Get the ILM display limit from configuration.

        Returns:
            int: Number of ILM unmanaged indices to show before truncating (defaults to 10)
        """
        return self.default_settings.get("ilm_display_limit", 10)

    def get_estop_top_indices(self):
        """
        Get the es-top index hot list display limit from configuration.

        Returns:
            int: Number of top active indices to show in es-top (defaults to 10)
        """
        estop_config = (self.main_config or {}).get("es_top", {})
        return estop_config.get("top_indices", 10)

    def get_estop_top_nodes(self):
        """
        Get the es-top node panel display limit from configuration.

        Returns:
            int: Number of top nodes to show in es-top (defaults to 5)
        """
        estop_config = (self.main_config or {}).get("es_top", {})
        return estop_config.get("top_nodes", 5)

    def get_estop_interval(self):
        """
        Get the es-top default refresh interval from configuration.

        Returns:
            int: Refresh interval in seconds (defaults to 30, minimum 10)
        """
        estop_config = (self.main_config or {}).get("es_top", {})
        return max(10, estop_config.get("interval", 30))

    def get_estop_hot_indicator(self):
        """
        Get the es-top hot indicator display mode from configuration.

        Valid values: 'emoji', 'color', 'both', 'none'.
        Invalid or missing values fall back to 'emoji'.

        Returns:
            str: One of 'emoji', 'color', 'both', 'none' (defaults to 'emoji')
        """
        _valid = {"emoji", "color", "both", "none"}
        estop_config = (self.main_config or {}).get("es_top", {})
        value = estop_config.get("hot_indicator", "emoji")
        return value if value in _valid else "emoji"

    def get_display_theme(self):
        """
        Get the display theme from state file first, then configuration file.

        Returns:
            str: Display theme - 'rich' (colorful for dark backgrounds), 'plain' (universal compatibility), or 'auto' (defaults to 'rich')
        """
        # Check state file first (for runtime theme switching)
        try:
            state_data = _load_json_tolerant(self.state_file_path)
            if "display_theme" in state_data:
                return state_data["display_theme"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

        # Fall back to configuration file
        return self.default_settings.get("display_theme", "rich")

    def get_connection_timeout(self):
        """
        Get the connection timeout from configuration.

        Returns:
            int: Connection timeout in seconds (defaults to 30)
        """
        return self.default_settings.get("connection_timeout", 30)

    def get_read_timeout(self):
        """
        Get the read timeout from configuration.

        Returns:
            int: Read timeout in seconds (defaults to 60)
        """
        return self.default_settings.get("read_timeout", 60)

    def get_dangling_cleanup_config(self):
        """
        Get dangling cleanup configuration settings.

        Returns:
            dict: Dictionary containing dangling cleanup configuration options
        """
        dangling_config = self.default_settings.get("dangling_cleanup", {})

        return {
            "max_retries": dangling_config.get("max_retries", 3),
            "retry_delay": dangling_config.get("retry_delay", 5),
            "timeout": dangling_config.get("timeout", 60),
            "default_log_level": dangling_config.get("default_log_level", "INFO"),
            "enable_progress_bar": dangling_config.get("enable_progress_bar", True),
            "confirmation_required": dangling_config.get("confirmation_required", True),
        }

    def _resolve_password(self, server_config):
        """
        Resolve password using the new environment-based password scheme.

        Priority order:
        1. Direct password reference (elastic_password_ref)
        2. Encrypted stored password (new secure method)
        3. Environment-based password (use_env_password=True with config_password field)
        4. Traditional explicit password (elastic_password)
        5. Default password from settings

        Args:
            server_config (dict): Server configuration dictionary

        Returns:
            str: Resolved password or None if not found
        """
        # Option 1: Direct password reference (e.g., "prod.kibana_system")
        if "elastic_password_ref" in server_config:
            password_ref = server_config["elastic_password_ref"]
            try:
                env, username = password_ref.split(".", 1)
                return self.passwords.get(env, {}).get(username)
            except (ValueError, AttributeError):
                print(f"Warning: Invalid password reference format: {password_ref}")

        # Option 2: Encrypted stored password (new secure method)
        try:
            from security.password_manager import password_manager

            # Strategy for multi-user environment support:
            # 1. Try environment.username combination (e.g., "prod.kibana_system")
            # 2. Try environment-only password (e.g., "prod")
            # 3. Try global.username combination (e.g., "global.devin.acosta")
            # 4. Try global password (for single-user setups)
            # 5. Try default password (backward compatibility)

            env = server_config.get("config_password", server_config.get("env"))
            username = self._resolve_username(server_config)

            # Try environment-specific password with username
            if env and username:
                encrypted_password = password_manager.get_password(env, username)
                if encrypted_password:
                    return encrypted_password

            # Try environment-only password (no username specified)
            if env:
                encrypted_password = password_manager.get_password(env)
                if encrypted_password:
                    return encrypted_password

            # Try global password with username (e.g., global.devin.acosta)
            if username:
                global_encrypted = password_manager.get_password("global", username)
                if global_encrypted:
                    return global_encrypted

            # Try global password (no username - single-user setup)
            global_encrypted = password_manager.get_password("global")
            if global_encrypted:
                return global_encrypted

            # Try default password (backward compatibility)
            default_encrypted = password_manager.get_password("default")
            if default_encrypted:
                return default_encrypted

        except ImportError:
            # Password manager not available, continue with other methods
            pass
        except Exception as e:
            # Don't let password manager errors break the entire system
            print(f"Warning: Error accessing encrypted passwords: {e}")

        # Option 3: Environment-based password resolution
        if server_config.get("use_env_password", False):
            env = server_config.get("config_password", server_config.get("env"))
            username = self._resolve_username(server_config)
            if env and username and env in self.passwords:
                password = self.passwords[env].get(username)
                if password:
                    return password
                else:
                    print(
                        f"Warning: No password found for {username} in environment '{env}'"
                    )

        # Option 3.5: Automatic environment-based password resolution (fallback)
        # Try to resolve password from environment even without explicit use_env_password flag
        # This makes the system more user-friendly for auto-generated configurations
        env = server_config.get("config_password", server_config.get("env"))
        username = self._resolve_username(server_config)
        if env and username and env in self.passwords:
            password = self.passwords[env].get(username)
            if password:
                return password

        # Option 4: Traditional explicit password (backwards compatibility)
        explicit_password = server_config.get("elastic_password")
        if explicit_password:
            return explicit_password

        # Option 5: Default password from settings
        return self.default_settings.get("elastic_password", None)

    def _resolve_username(self, server_config):
        """
        Resolve username using the new priority order.

        Priority order:
        1. Server-level username (elastic_username in server config)
        2. Auth profile username (auth_profile on server -> auth_profiles in config)
        3. Environment-based username (from environment config)
        4. JSON state file username (elastic_username in escmd.json)
        5. Default username from settings (elastic_username in escmd.yml)

        Args:
            server_config (dict): Server configuration dictionary

        Returns:
            str: Resolved username or None if not found
        """
        # Option 1: Server-level username (highest priority)
        server_username = server_config.get("elastic_username")
        if server_username:
            return server_username

        # Option 2: Auth profile (portable cluster label -> username map in escmd.yml)
        profile_key = server_config.get("auth_profile")
        if isinstance(profile_key, str):
            profile_key = profile_key.strip()
        if profile_key:
            prof = self.auth_profiles.get(profile_key)
            if prof is None:
                print(
                    f"Warning: Unknown auth_profile '{profile_key}' (not defined under auth_profiles:)."
                )
            elif isinstance(prof, dict):
                u = prof.get("elastic_username")
                if u is not None:
                    u = u.strip() if isinstance(u, str) else u
                    if u:
                        return u

        # Option 3: Environment-based username
        env = server_config.get("config_password", server_config.get("env"))
        if env and env in self.passwords:
            # Check if environment has usernames defined
            env_passwords = self.passwords[env]
            if isinstance(env_passwords, dict) and len(env_passwords) == 1:
                # If there's only one user in the environment, use that username
                username = list(env_passwords.keys())[0]
                return username

        # Option 4: JSON state file username
        try:
            if os.path.exists(self.state_file_path):
                state_data = _load_json_tolerant(self.state_file_path)
                json_username = state_data.get("elastic_username")
                if json_username:
                    return json_username
        except (json.JSONDecodeError, IOError, KeyError):
            # Ignore errors reading state file
            pass

        # Option 5: Default username from settings (lowest priority)
        return self.default_settings.get("elastic_username", None)

    def get_server_config(self, location):
        """
        Get the server configuration for a specific location with intelligent fallback.

        This method implements smart location resolution:
        1. First tries the exact location name (e.g., "aex20")
        2. If not found, tries with "-c01" suffix (e.g., "aex20-c01")
        3. If still not found, searches for any cluster name starting with the short name
        4. If exactly one match is found, returns it (e.g., "aex20-glip" for "aex20")
        5. If multiple matches exist, returns None (ambiguous)

        Args:
            location (str): The location name to get configuration for.

        Returns:
            dict: The server configuration or None if not found/ambiguous.
        """
        location_lower = location.lower()

        # First, try the exact location name
        server_config = self.servers_dict.get(location_lower)
        if server_config:
            return server_config

        # If not found, try with "-c01" suffix for auto-generated cluster names
        fallback_location = f"{location_lower}-c01"
        server_config = self.servers_dict.get(fallback_location)
        if server_config:
            return server_config

        # If still not found, search for any cluster names that start with the short name
        matching_servers = [
            (name, config)
            for name, config in self.servers_dict.items()
            if name.startswith(location_lower + "-") and name != fallback_location
        ]

        # If exactly one match found, return it
        if len(matching_servers) == 1:
            return matching_servers[0][1]

        # If multiple matches or no matches found, return None
        return None

    def canonical_cluster_name_for_location(self, location):
        """
        Return the servers_dict key for a location after alias / short-name resolution.

        This matches how set-default stores the default: the first key in servers_dict
        whose server entry equals get_server_config(location). Use for stable paths
        (e.g. index-watch) regardless of whether the user passed a short name or the
        full cluster key.
        """
        if location is None:
            return None
        loc = str(location).strip()
        if not loc:
            return None
        server_config = self.get_server_config(loc)
        if not server_config:
            return None
        for name, config in self.servers_dict.items():
            if config == server_config:
                return name
        return None

    def get_default_cluster(self):
        """
        Get the current default cluster from the state file.

        Returns:
            str: The name of the default cluster.
        """
        try:
            return _load_json_tolerant(self.state_file_path)["current_cluster"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return "default"

    def set_default_cluster(self, value):
        """
        Set the default cluster in the state file.

        Args:
            value (str): The name of the cluster to set as default.
        """
        try:
            settings = _load_json_tolerant(self.state_file_path)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {"current_cluster": "default"}

        settings["current_cluster"] = value
        with open(self.state_file_path, "w") as file:
            json.dump(settings, file, indent=4)
        print(f"Current cluster set to: {value}")

    def set_display_theme(self, theme_name):
        """
        Set the display theme in the state file.

        Args:
            theme_name (str): The name of the theme to set as active.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            try:
                settings = _load_json_tolerant(self.state_file_path)
            except (FileNotFoundError, json.JSONDecodeError):
                settings = {"current_cluster": "default"}

            settings["display_theme"] = theme_name
            with open(self.state_file_path, "w") as file:
                json.dump(settings, file, indent=4)
            return True
        except Exception as e:
            print(f"Error setting theme: {e}")
            return False

    def set_elastic_username(self, username):
        """
        Set the elastic username in the state file.

        Args:
            username (str): The username to set as default.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            try:
                settings = _load_json_tolerant(self.state_file_path)
            except (FileNotFoundError, json.JSONDecodeError):
                settings = {"current_cluster": "default"}

            if username:
                settings["elastic_username"] = username
            else:
                # Remove username if None or empty string is provided
                settings.pop("elastic_username", None)

            with open(self.state_file_path, "w") as file:
                json.dump(settings, file, indent=4)
            return True
        except Exception as e:
            print(f"Error setting username: {e}")
            return False

    def get_elastic_username_from_json(self):
        """
        Get the elastic username from the JSON state file.

        Returns:
            str: The username from JSON file, or None if not found
        """
        try:
            if os.path.exists(self.state_file_path):
                state_data = _load_json_tolerant(self.state_file_path)
                return state_data.get("elastic_username")
        except (json.JSONDecodeError, IOError, KeyError):
            pass
        return None

    def get_server_config_by_location(self, location):
        """
        Get server configuration for a specific location with defaults.

        Args:
            location (str): The location name to get configuration for.

        Returns:
            dict: The server configuration with defaults applied.
        """
        server_config = self.get_server_config(location)
        if not server_config:
            return None

        return {
            "elastic_host": server_config.get(
                "hostname", self.default_settings.get("hostname", "localhost")
            ),
            "elastic_host2": server_config.get(
                "hostname2", self.default_settings.get("hostname2", "localhost")
            ),
            "elastic_host3": server_config.get(
                "hostname3", self.default_settings.get("hostname3")
            ),
            "elastic_port": server_config.get(
                "port", self.default_settings.get("port", 9200)
            ),
            "use_ssl": server_config.get(
                "use_ssl", self.default_settings.get("use_ssl", False)
            ),
            "verify_certs": server_config.get(
                "verify_certs", self.default_settings.get("verify_certs", False)
            ),
            "elastic_authentication": server_config.get(
                "elastic_authentication",
                self.default_settings.get("elastic_authentication", False),
            ),
            "elastic_username": self._resolve_username(server_config),
            "elastic_password": self._resolve_password(server_config),
            "repository": server_config.get(
                "repository", self.default_settings.get("repository", "default-repo")
            ),
            "elastic_s3snapshot_repo": server_config.get(
                "elastic_s3snapshot_repo",
                self.default_settings.get("elastic_s3snapshot_repo", None),
            ),
            "health_style": server_config.get(
                "health_style", self.default_settings.get("health_style", "dashboard")
            ),
            "classic_style": server_config.get(
                "classic_style", self.default_settings.get("classic_style", "panel")
            ),
            "ascii_mode": server_config.get(
                "ascii_mode", self.default_settings.get("ascii_mode", False)
            ),
            "read_timeout": server_config.get(
                "read_timeout", self.get_read_timeout()
            ),
            # Preserve critical fields needed for password resolution
            "config_password": server_config.get("config_password"),
            "env": server_config.get("env"),
        }

    def get_cluster_groups(self):
        """
        Get all available cluster groups in normalized format.

        Returns:
            dict: Dictionary of cluster group names and their members (backward compatible)
        """
        return self.cluster_groups

    def get_cluster_group_members(self, group_name):
        """
        Get the list of clusters in a specific group.

        Args:
            group_name (str): The name of the cluster group

        Returns:
            list: List of cluster names in the group, or None if group doesn't exist
        """
        return self.cluster_groups.get(group_name)

    def get_environment_members(self, env_name):
        """
        Get the list of clusters in a specific environment.

        Args:
            env_name (str): The name of the environment

        Returns:
            list: List of cluster names in the environment, or None if environment doesn't exist
        """
        env_members = []
        for server_name, server_config in self.servers_dict.items():
            if server_config.get("env", "unknown") == env_name:
                env_members.append(server_name)
        return env_members if env_members else None

    def is_environment(self, env_name):
        """
        Check if the given name is a valid environment.

        Args:
            env_name (str): The name to check

        Returns:
            bool: True if environment exists, False otherwise
        """
        for server_config in self.servers_dict.values():
            if server_config.get("env", "unknown") == env_name:
                return True
        return False

    def get_environments(self):
        """
        Get all available environments.

        Returns:
            dict: Dictionary mapping environment names to lists of server names
        """
        environments = {}
        for server_name, server_config in self.servers_dict.items():
            env = server_config.get("env", "unknown")
            if env not in environments:
                environments[env] = []
            environments[env].append(server_name)
        return environments

    def get_cluster_groups_with_descriptions(self):
        """
        Get all available cluster groups with their descriptions and metadata.

        Returns:
            dict: Dictionary with group details including descriptions
                Format: {
                    'group_name': {
                        'clusters': ['cluster1', 'cluster2'],
                        'description': 'Group description',
                        'cluster_count': 2
                    }
                }
        """
        enhanced_groups = {}
        for group_name, group_data in self.cluster_groups_raw.items():
            if isinstance(group_data, dict) and "clusters" in group_data:
                # New format with description and clusters
                clusters = group_data.get("clusters", [])
                description = group_data.get("description", "No description provided")
            elif isinstance(group_data, list):
                # Old format - just a list of clusters
                clusters = group_data
                description = "No description provided"
            else:
                # Handle unexpected format
                clusters = []
                description = "Invalid group configuration"

            enhanced_groups[group_name] = {
                "clusters": clusters,
                "description": description,
                "cluster_count": len(clusters),
            }

        return enhanced_groups

    def get_configuration_info(self):
        """
        Get information about the current configuration mode and file paths.

        Returns:
            dict: Configuration information including mode, file paths, and statistics
        """
        info = {
            "mode": "dual-file" if self.is_dual_file_mode else "single-file",
            "total_servers": len(self.servers_dict),
            "cluster_groups": len(self.cluster_groups),
            "password_environments": len(self.passwords),
        }

        if self.is_dual_file_mode:
            info.update(
                {
                    "main_config_file": self.main_config_path,
                    "servers_config_file": self.servers_config_path,
                    "main_config_exists": os.path.exists(self.main_config_path)
                    if self.main_config_path
                    else False,
                    "servers_config_exists": os.path.exists(self.servers_config_path)
                    if self.servers_config_path
                    else False,
                }
            )
        else:
            info.update(
                {
                    "config_file": self.config_file_path,
                    "config_exists": os.path.exists(self.config_file_path)
                    if self.config_file_path
                    else False,
                }
            )

        return info

    def get_metrics_config(self, environment=None):
        """
        Get metrics configuration for InfluxDB/VictoriaMetrics integration.

        Args:
            environment: Optional environment name to get environment-specific config

        Returns:
            dict: Metrics configuration or None if not configured
        """
        metrics_config = None

        # In dual-file mode, check root level of main config first
        if self.is_dual_file_mode and hasattr(self, "main_config") and self.main_config:
            metrics_config = self.main_config.get("metrics")

        # Fall back to settings section (for backward compatibility)
        if not metrics_config and self.default_settings:
            metrics_config = self.default_settings.get("metrics")

        if not metrics_config:
            return None

        # If environment is specified, check for environment-specific configuration
        if environment and isinstance(metrics_config, dict):
            env_configs = metrics_config.get("environments", {})
            if environment.lower() in env_configs:
                env_config = env_configs[environment.lower()]
                # Merge environment-specific config with base config
                # Environment-specific settings override base settings
                merged_config = metrics_config.copy()
                merged_config.update(env_config)
                # Remove the environments section from the final config
                merged_config.pop("environments", None)
                metrics_config = merged_config

        # Validate that at least endpoint is configured
        if not metrics_config.get("endpoint"):
            return None

        return metrics_config

    def is_cluster_group(self, name):
        """
        Check if a given name is a cluster group.

        Args:
            name (str): The name to check

        Returns:
            bool: True if it's a cluster group, False otherwise
        """
        return name in self.cluster_groups

    def get_display_theme(self):
        """
        Get the display theme setting, checking escmd.json first, then escmd.yml.

        Returns:
            str: The theme name, defaults to 'rich' if not found
        """
        # First try to get from state file (escmd.json)
        try:
            if os.path.exists(self.state_file_path):
                state_data = _load_json_tolerant(self.state_file_path)
                if "display_theme" in state_data:
                    return state_data["display_theme"]
        except (json.JSONDecodeError, IOError):
            # Ignore errors reading state file
            pass

        # Then try to get from main config file (escmd.yml)
        if self.is_dual_file_mode and self.main_config:
            settings = self.main_config.get("settings", {})
            if "display_theme" in settings:
                return settings["display_theme"]
        elif not self.is_dual_file_mode and self.config:
            settings = self.config.get("settings", {})
            if "display_theme" in settings:
                return settings["display_theme"]

        # Default to 'rich' theme
        return "rich"
