#!/usr/bin/env python3
"""
Elasticsearch Servers Configuration Generator

This script reads crosscluster YAML configuration files and generates
a new elastic_servers.yml configuration by connecting to each cluster,
discovering nodes, and selecting 2 data nodes per cluster.

Usage:
    python generate_elastic_servers.py [--output OUTPUT_FILE] [--dry-run]
    python generate_elastic_servers.py --username USER [--password-env-file map.yml]
    (Per-env: ESCMD_GEN_PASSWORD_PROD, ESCMD_GEN_PASSWORD_IN, ESCMD_GEN_PASSWORD_EU, ...)

Author: Automated Script Generator
"""

import argparse
import getpass
import hashlib
import json
import os
import subprocess
import sys
import warnings
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3
import yaml
from elasticsearch import Elasticsearch, exceptions
from elasticsearch.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ConnectionError,
    NotFoundError,
)
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", message=".*verify_certs=False.*", category=Warning)

# Suppress Elasticsearch warnings
from elasticsearch import ElasticsearchWarning

warnings.filterwarnings("ignore", category=ElasticsearchWarning)
warnings.filterwarnings(
    "ignore",
    message=".*unable to verify that the server is Elasticsearch.*",
    category=Warning,
)


# Configure YAML to handle OrderedDict properly
def represent_ordereddict(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


yaml.add_representer(OrderedDict, represent_ordereddict)


class ElasticsearchServerGenerator:
    """
    Elasticsearch Servers Configuration Generator

    This class manages two types of environments:
    1. env: Source environment from crosscluster files (us, stress, att, eu, etc.)
            - Used for tracking which environment file a server came from
            - Used for merge logic to avoid cross-environment deletions
    2. config_password: Password environment (prod, eu, lab, ops, etc.)
                       - Used for credential mapping based on location
                       - Multiple envs can map to the same password env

    This separation prevents accidental deletion of servers from different
    crosscluster files that happen to use the same password environment.
    """

    def __init__(
        self,
        yml_directory: str = "/etc/git/ELK_scripts/ol9/kcs/maintenance/crosscluster",
        output_file: str = "elastic_servers.yml",
        environment: str = "all",
        update_mode: bool = False,
        escmd_json_path: Optional[str] = None,
        cli_username: Optional[str] = None,
        cli_password: Optional[str] = None,
        cli_password_by_env: Optional[Dict[str, str]] = None,
        es_timeout: int = 30,
    ):
        self.yml_directory = yml_directory
        self.output_file = output_file
        self.environment = environment
        self.update_mode = update_mode
        self.clusters_config = {}
        self.generated_servers = []
        self.passwords = {}
        self.existing_config = None
        self.console = Console()
        self.s3snapshot_repo_mapping = {}
        self.cli_username = cli_username.strip() if cli_username else None
        self.cli_password = cli_password
        self.cli_password_by_env = {
            k.lower(): v for k, v in (cli_password_by_env or {}).items() if v
        }
        script_dir = Path(__file__).resolve().parent
        self.escmd_json_path = escmd_json_path or str(script_dir / "escmd.json")
        self.state_elastic_username: Optional[str] = None
        self._password_manager = None
        self._password_manager_loaded = False
        self.es_timeout = max(5, int(es_timeout))

        # Check if the yml_directory exists and show helpful message if not
        if not Path(self.yml_directory).exists():
            self._show_path_notice()
            sys.exit(1)

        # Environment to crosscluster file mapping
        self.env_file_mapping = {
            "biz": "crosscluster.nodes_att.yml",
            "eu": "crosscluster.nodes_eu.yml",
            "in": "crosscluster.nodes_in.yml",
            "lab": "crosscluster.nodes_lab.yml",
            "ops": "crosscluster.nodes_ops.yml",
            "stress": "crosscluster.nodes_stress.yml",
            "us": "crosscluster.nodes_us.yml",
        }

        # Location to environment mapping
        self.location_env_mapping = {
            "lab": "lab",
            "ops": "ops",
            "stress": "stress",
            "na_sa": "prod",  # US/APAC prod
            "apac": "prod",  # US/APAC prod
            "eu": "eu",  # EU prod
            "india": "in",  # India prod
            "biz": "biz",  # Biz prod
        }

        # Environment-specific password fallback chains
        # Some environments like ATT might have clusters using different password environments
        self.env_password_chains = {
            "biz": ["biz", "prod"],  # ATT/BIZ environment: try BIZ first, then PROD
            "att": ["att", "prod"],  # ATT alternative: try ATT, then PROD
            "eu": ["eu"],  # EU uses only EU passwords
            "lab": ["lab"],  # LAB uses only LAB passwords
            "ops": ["ops"],  # OPS uses only OPS passwords
            "stress": ["stress"],  # STRESS uses only STRESS passwords
            "us": ["prod"],  # US uses only PROD passwords
            "in": ["in"],  # India uses only India passwords
        }

        # Generate password hashes first
        self._generate_password_hashes()

        self._load_state_elastic_username()

        # Load S3 snapshot repository mapping
        self._load_s3snapshot_repo_mapping()

        # Load existing configuration if in update mode
        if self.update_mode:
            self._load_existing_config()

        if self.cli_username and self.cli_password_by_env:
            self.console.print(
                f"📇 Per-env CLI passwords loaded for: [cyan]{', '.join(sorted(self.cli_password_by_env))}[/cyan]",
                style="dim",
            )

    def _resolve_cli_password_for_env(self, pwd_env: str) -> Optional[str]:
        """
        Password for --username for this config_password env.

        Order: --password-env-file entry, ESCMD_GEN_PASSWORD_<ENV>, then global
        cli_password / ESCMD_GEN_PASSWORD.
        """
        key = pwd_env.lower()
        if key in self.cli_password_by_env:
            v = self.cli_password_by_env[key]
            if v:
                return v
        env_pw = os.environ.get(f"ESCMD_GEN_PASSWORD_{key.upper()}")
        if env_pw:
            return env_pw
        return self.cli_password

    def _load_s3snapshot_repo_mapping(self):
        """Load S3 snapshot repository mapping from configuration file"""
        mapping_file = Path("s3snapshot_repo_mapping.yml")
        if mapping_file.exists():
            try:
                with open(mapping_file, "r") as f:
                    content = yaml.safe_load(f)
                    if content:
                        self.s3snapshot_repo_mapping = content
                        self.console.print(
                            f"📦 Loaded S3 snapshot repository mappings for {len(self.s3snapshot_repo_mapping)} clusters",
                            style="green",
                        )
                    else:
                        self.s3snapshot_repo_mapping = {}
            except Exception as e:
                self.console.print(
                    f"🔶  Warning: Could not load S3 snapshot repository mapping: {e}",
                    style="yellow",
                )
                self.s3snapshot_repo_mapping = {}
        else:
            self.s3snapshot_repo_mapping = {}

    def _show_path_notice(self):
        """Show a notice when the default yml directory doesn't exist"""
        notice_panel = Panel(
            Text.from_markup(
                f"[bold yellow]🔶  Default crosscluster directory not found![/bold yellow]\n\n"
                f"[white]The script is looking for crosscluster.nodes_*.yml files in:[/white]\n"
                f"[cyan]{self.yml_directory}[/cyan]\n\n"
                f"[white]This directory doesn't exist. You have two options:[/white]\n\n"
                f"[green]1. Use --yml-dir to specify the correct path:[/green]\n"
                f"   [dim]python generate_elastic_servers.py --yml-dir /path/to/your/crosscluster/files[/dim]\n\n"
                f"[green]2. Create the expected directory structure and place your crosscluster.nodes_*.yml files there[/green]\n\n"
                f"[white]The crosscluster files should be named like:[/white]\n"
                f"[dim]• crosscluster.nodes_us.yml\n"
                f"• crosscluster.nodes_eu.yml\n"
                f"• crosscluster.nodes_stress.yml\n"
                f"• etc.[/dim]"
            ),
            title="[bold red]Configuration Directory Missing[/bold red]",
            style="yellow",
            border_style="yellow",
        )
        self.console.print(notice_panel)
        self.console.print()  # Add spacing

    def _generate_password_hashes(self):
        """Generate SHA512 password hashes for different environments"""
        password_seeds = {
            "lab": "kibana_lab",
            "ops": "kibana_ops",
            "stress": "kibana_stress",
            "prod": "kibana_us",  # US/APAC
            "eu": "kibana_eu",
            "in": "kibana_in",
            "biz": "kibana_biz",
        }

        for env, seed in password_seeds.items():
            # Generate SHA512 hash
            hash_result = hashlib.sha512(seed.encode()).hexdigest()
            self.passwords[env] = {"kibana_system": hash_result}

        # Add Default password for old systems
        self.passwords["default"] = {"kibana": "kibana"}

        self.console.print(
            f"✅ Generated password hashes for environments: {list(self.passwords.keys())}",
            style="green",
        )

    def _load_state_elastic_username(self):
        """Load default elastic_username from escmd.json if present."""
        path = Path(self.escmd_json_path)
        if not path.is_file():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            u = data.get("elastic_username")
            if isinstance(u, str) and u.strip():
                self.state_elastic_username = u.strip()
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    def _get_password_manager(self):
        if self._password_manager_loaded:
            return self._password_manager
        self._password_manager_loaded = True
        try:
            from security.password_manager import PasswordManager

            self._password_manager = PasswordManager(self.escmd_json_path)
        except ImportError:
            self._password_manager = None
        return self._password_manager

    def _load_existing_config(self):
        """Load existing configuration file if it exists"""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r") as f:
                    self.existing_config = yaml.safe_load(f)
                self.console.print(
                    f"📁 Loaded existing configuration from {self.output_file}",
                    style="blue",
                )

                # Use existing passwords if available, but don't overwrite newly generated ones
                if self.existing_config and "passwords" in self.existing_config:
                    existing_passwords = self.existing_config["passwords"]
                    # Only preserve existing passwords for environments we didn't regenerate
                    for env, creds in existing_passwords.items():
                        if env not in self.passwords:
                            self.passwords[env] = creds
                        # Don't merge/update - keep the newly generated passwords as they are

            except Exception as e:
                self.console.print(
                    f"🔶  Warning: Could not load existing configuration: {e}",
                    style="yellow",
                )
                self.existing_config = None
        else:
            self.console.print(
                f"ℹ️  No existing configuration found at {self.output_file}",
                style="cyan",
            )

    def read_crosscluster_files(self) -> Dict:
        """Read crosscluster YAML files from the yml directory (filtered by environment if specified)"""
        crosscluster_configs = {}
        yml_path = Path(self.yml_directory)

        if not yml_path.exists():
            raise FileNotFoundError(f"Directory {self.yml_directory} not found")

        # Determine which files to process
        if self.environment == "all":
            # Find all crosscluster.nodes_*.yml files
            crosscluster_files = list(yml_path.glob("crosscluster.nodes_*.yml"))
        else:
            # Process only the specified environment
            if self.environment not in self.env_file_mapping:
                raise ValueError(
                    f"Unknown environment: {self.environment}. Valid options: {list(self.env_file_mapping.keys())}"
                )

            target_file = yml_path / self.env_file_mapping[self.environment]
            if not target_file.exists():
                raise FileNotFoundError(f"Environment file not found: {target_file}")

            crosscluster_files = [target_file]

        if not crosscluster_files:
            raise FileNotFoundError(
                f"No crosscluster.nodes_*.yml files found in {self.yml_directory}"
            )

        self.console.print(
            f"🌍 Processing environment(s): {self.environment}", style="bold cyan"
        )

        # Use Rich progress bar for file reading
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            file_task = progress.add_task(
                "Reading configuration files...", total=len(crosscluster_files)
            )

            for file_path in crosscluster_files:
                progress.update(file_task, description=f"Reading {file_path.name}")
                try:
                    with open(file_path, "r") as f:
                        config = yaml.safe_load(f)
                        if config:
                            # Extract environment name from filename (e.g., crosscluster.nodes_us.yml -> us)
                            env_name = file_path.stem.replace("crosscluster.nodes_", "")
                            crosscluster_configs[env_name] = config
                            self.console.print(
                                f"  ✅ Loaded {len(config)} clusters from {file_path.name}",
                                style="green",
                            )
                except yaml.YAMLError as e:
                    self.console.print(
                        f"  ❌ Error reading {file_path.name}: {e}", style="red"
                    )
                    continue

                progress.advance(file_task)

        return crosscluster_configs

    def resolve_hostname_via_racktables(self, hostname: str) -> Optional[str]:
        """
        Resolve hostname using RackTables API when DNS resolution fails.
        Tries production RT first, then stage RT if not found.

        Args:
            hostname: The hostname to resolve (e.g., 'aex09-c01-esm01')

        Returns:
            The resolved FQDN if found, None otherwise
        """
        # RackTables API endpoints
        rt_urls = [
            "http://rt.ringcentral.com/api/hosts/search",  # Production
            "http://rt.stage.ringcentral.com/api/hosts/search",  # Stage
        ]

        for rt_url in rt_urls:
            try:
                # Query RackTables API
                params = {"q": f"name~{hostname}$", "fields": "fqdn"}

                self.console.print(
                    f"    🔍 Querying RackTables: {rt_url.split('//')[1].split('/')[0]}",
                    style="cyan",
                )

                response = requests.get(rt_url, params=params, timeout=30)
                response.raise_for_status()

                # RackTables returns plain text, not JSON
                resolved_fqdn = response.text.strip()

                # Check if we got a valid response
                if resolved_fqdn and "." in resolved_fqdn:
                    # Validate that it looks like a valid FQDN
                    self.console.print(
                        f"    ✅ RackTables resolved '{hostname}' → '{resolved_fqdn}'",
                        style="green",
                    )
                    return resolved_fqdn

                self.console.print(
                    f"    ❌ No valid FQDN found in RackTables response: '{resolved_fqdn}'",
                    style="yellow",
                )

            except requests.exceptions.RequestException as e:
                self.console.print(
                    f"    🔶 RackTables query failed: {e}", style="yellow"
                )
            except (ValueError, KeyError) as e:
                self.console.print(
                    f"    🔶 Invalid RackTables response format: {e}", style="yellow"
                )

        self.console.print(
            f"    ❌ Could not resolve '{hostname}' via RackTables", style="red"
        )
        return None

    def test_basic_connectivity(
        self, host: str, port: int, ssl: bool
    ) -> Tuple[bool, str]:
        """
        Test basic HTTP connectivity without authentication.
        If DNS resolution fails, try to resolve via RackTables API.

        Returns:
            Tuple[bool, str]: (success, resolved_hostname)
        """
        protocol = "https" if ssl else "http"
        url = f"{protocol}://{host}:{port}/"

        try:
            self.console.print(
                f"    🔗 Testing basic connectivity to {url}...", style="dim cyan"
            )
            response = requests.get(url, verify=False, timeout=self.es_timeout)
            if response.status_code == 200:
                self.console.print(
                    f"    ✅ Basic connectivity test: HTTP {response.status_code}",
                    style="green",
                )
            else:
                self.console.print(
                    f"    🔶  Basic connectivity test: HTTP {response.status_code}",
                    style="yellow",
                )
            return True, host
        except requests.exceptions.RequestException as e:
            self.console.print(f"    ❌ Basic connectivity failed: {e}", style="red")

            # Check if this is a DNS resolution error
            if "Failed to establish a new connection" in str(
                e
            ) or "nodename nor servname provided" in str(e):
                self.console.print(
                    f"    🔧 DNS resolution failed, trying RackTables API...",
                    style="yellow",
                )

                # Try to resolve hostname via RackTables
                resolved_hostname = self.resolve_hostname_via_racktables(host)
                if resolved_hostname:
                    # Retry connectivity with resolved hostname
                    resolved_url = f"{protocol}://{resolved_hostname}:{port}/"
                    try:
                        self.console.print(
                            f"    🔗 Retrying connectivity with resolved hostname: {resolved_url}...",
                            style="dim cyan",
                        )
                        response = requests.get(
                            resolved_url, verify=False, timeout=self.es_timeout
                        )
                        if response.status_code == 200:
                            self.console.print(
                                f"    ✅ RackTables-resolved connectivity: HTTP {response.status_code}",
                                style="green",
                            )
                        else:
                            self.console.print(
                                f"    🔶  RackTables-resolved connectivity: HTTP {response.status_code}",
                                style="yellow",
                            )
                        return True, resolved_hostname
                    except requests.exceptions.RequestException as retry_e:
                        self.console.print(
                            f"    ❌ Even resolved hostname failed: {retry_e}",
                            style="red",
                        )
                        return False, host
                else:
                    self.console.print(
                        f"    ❌ RackTables resolution failed, cannot proceed",
                        style="red",
                    )
                    return False, host
            else:
                # Non-DNS error, don't try RackTables
                return False, host

    def _password_envs_for_location(
        self, location: str, file_env: Optional[str]
    ) -> List[str]:
        env = self.location_env_mapping.get(location.lower(), "prod")

        if location.lower() in ["unknown", ""] and file_env:
            file_env_mapping = {
                "eu": "eu",
                "lab": "lab",
                "ops": "ops",
                "stress": "stress",
                "att": "att",
                "in": "in",
                "us": "prod",
                "biz": "biz",
            }
            env = file_env_mapping.get(file_env, "prod")
            self.console.print(
                f"    🔑 Location missing → Using file environment '{file_env}' → Password env '{env}'",
                style="dim cyan",
            )

        return self.env_password_chains.get(file_env if file_env else env, [env])

    def build_credential_attempts(
        self, location: str, file_env: Optional[str] = None
    ) -> List[Tuple[str, str, str, str]]:
        """
        Build ordered credential attempts for a cluster.

        Returns:
            List of (username, password, config_password_env, label).
        """
        password_envs = self._password_envs_for_location(location, file_env)
        pm = self._get_password_manager()
        attempts: List[Tuple[str, str, str, str]] = []
        seen: set = set()

        def add_attempt(username: str, password: str, pwd_env: str, label: str):
            key = (username, password, pwd_env)
            if key in seen:
                return
            seen.add(key)
            attempts.append((username, password, pwd_env, label))

        for pwd_env in password_envs:
            stored_ks = None
            if pm:
                stored_ks = pm.get_password(pwd_env, "kibana_system")
            if stored_ks:
                add_attempt(
                    "kibana_system",
                    stored_ks,
                    pwd_env,
                    f"kibana_system (stored {pwd_env})",
                )

            hash_ks = None
            if pwd_env in self.passwords and "kibana_system" in self.passwords[pwd_env]:
                hash_ks = self.passwords[pwd_env]["kibana_system"]
            if hash_ks and hash_ks != stored_ks:
                add_attempt(
                    "kibana_system",
                    hash_ks,
                    pwd_env,
                    f"kibana_system (seed {pwd_env})",
                )

            if pm and self.state_elastic_username:
                su = self.state_elastic_username
                stored_user_pw = pm.get_password(pwd_env, su)
                if stored_user_pw:
                    add_attempt(su, stored_user_pw, pwd_env, f"{su} (stored {pwd_env})")

            if self.cli_username:
                cli_pw = self._resolve_cli_password_for_env(pwd_env)
                if cli_pw:
                    add_attempt(
                        self.cli_username,
                        cli_pw,
                        pwd_env,
                        f"{self.cli_username} (cli {pwd_env})",
                    )

            if pwd_env in self.passwords and "kibana" in self.passwords[pwd_env]:
                kb = self.passwords[pwd_env]["kibana"]
                add_attempt("kibana", kb, pwd_env, f"kibana (seed {pwd_env})")

        return attempts

    def _elastic_auth_entries(
        self, elastic_username: str, use_inline_kibana_password: bool
    ) -> List[Tuple[str, Any]]:
        if use_inline_kibana_password:
            return [
                ("elastic_username", "kibana"),
                ("elastic_password", "kibana"),
            ]
        if elastic_username:
            return [("elastic_username", elastic_username)]
        return []

    def connect_to_elasticsearch(
        self, discovery_host: str, ssl: bool, location: str, file_env: str = None
    ) -> Optional[Tuple[Elasticsearch, str, str, bool]]:
        """
        Connect to Elasticsearch and return
        (client, config_password_env, elastic_username, use_inline_kibana_password).
        """
        host, port = (
            discovery_host.split(":")
            if ":" in discovery_host
            else (discovery_host, "9200")
        )
        port = int(port)

        credential_chains = self.build_credential_attempts(location, file_env)

        es_config = {
            "hosts": [{"host": host, "port": port}],
            "use_ssl": ssl,
            "verify_certs": False,
            "ssl_show_warn": False,
            "timeout": self.es_timeout,
            "max_retries": 1,
            "retry_on_timeout": False,
        }

        for i, (username, password, env_name, label) in enumerate(credential_chains):
            es_config["http_auth"] = (username, password)

            try:
                attempt_info = label
                if i > 0:
                    self.console.print(
                        f"    🔄 Trying alternative credentials: {attempt_info}...",
                        style="yellow",
                    )
                else:
                    self.console.print(
                        f"    🔌 Connecting to {host}:{port} (SSL: {ssl}) with {attempt_info}...",
                        style="cyan",
                    )

                es = Elasticsearch(**es_config)

                try:
                    cluster_info = es.info()
                    cluster_name = cluster_info.get("cluster_name", "unknown")
                    success_msg = (
                        f"✅ Connected successfully to cluster: [bold green]{cluster_name}[/bold green]"
                    )
                    if len(credential_chains) > 1:
                        success_msg += f" [dim]({label})[/dim]"
                    self.console.print(f"    {success_msg}")
                    return (es, env_name, username, False)
                except exceptions.AuthorizationException as e:
                    if i == len(credential_chains) - 1:
                        self.console.print(
                            f"    🚫 Authorization failed (403 Forbidden) with {attempt_info}: {e}",
                            style="red",
                        )
                    continue
                except exceptions.AuthenticationException as e:
                    if i == len(credential_chains) - 1:
                        self.console.print(
                            f"    🔒 Authentication failed (401 Unauthorized) with {attempt_info}: {e}",
                            style="red",
                        )
                    continue
                except exceptions.ConnectionError as e:
                    self.console.print(
                        f"    📡 Connection/timeout with {attempt_info}: {e}",
                        style="yellow",
                    )
                    self.console.print(
                        "    [dim]Continuing with next credential (timeouts are not always "
                        "auth-related; try --es-timeout 60-120 for slow clusters).[/dim]",
                        style="dim",
                    )
                    continue
                except Exception as e:
                    if i == len(credential_chains) - 1:
                        self.console.print(
                            f"    ❌ Error testing connection with {attempt_info}: {e}",
                            style="red",
                        )
                    continue

            except Exception as e:
                if i == len(credential_chains) - 1:
                    self.console.print(
                        f"    ❌ Failed to connect to {host}:{port}: {e}", style="red"
                    )
                continue

        self.console.print(
            f"    🔄 All configured credentials failed, trying kibana:kibana as final fallback...",
            style="yellow",
        )
        es_config["http_auth"] = ("kibana", "kibana")
        try:
            es = Elasticsearch(**es_config)
            cluster_info = es.info()
            cluster_name = cluster_info.get("cluster_name", "unknown")
            self.console.print(
                f"    ✅ Connected successfully with fallback credentials to cluster: [bold green]{cluster_name}[/bold green] [dim](kibana:kibana)[/dim]"
            )
            return (es, "default", "kibana", True)
        except exceptions.AuthorizationException as e:
            self.console.print(
                f"    🔐  403 Forbidden even with kibana:kibana - ReadonlyREST blocking: {e}",
                style="red",
            )
            return None
        except Exception as e:
            self.console.print(f"    ❌ Final fallback also failed: {e}", style="red")
            return None

    def get_cluster_nodes(self, es_client: Elasticsearch) -> List[Dict]:
        """Get all nodes from the cluster and filter for data nodes"""
        try:
            # Get nodes information
            nodes_info = es_client.nodes.info()
            nodes_stats = es_client.nodes.stats()

            data_nodes = []

            for node_id, node_info in nodes_info["nodes"].items():
                # Check if node is a data node
                node_roles = node_info.get("roles", [])
                if (
                    "data" in node_roles
                    or "data_content" in node_roles
                    or "data_hot" in node_roles
                ):
                    node_name = node_info.get("name", node_id)
                    node_host = node_info.get("host", "unknown")

                    # Get node stats for additional info
                    node_stat = nodes_stats["nodes"].get(node_id, {})

                    data_nodes.append(
                        {
                            "id": node_id,
                            "name": node_name,
                            "host": node_host,
                            "roles": node_roles,
                            "transport_address": node_info.get("transport_address", ""),
                            "http_address": node_info.get("http", {}).get(
                                "publish_address", ""
                            ),
                        }
                    )

            self.console.print(
                f"    📊 Found {len(data_nodes)} data nodes", style="green"
            )
            return data_nodes

        except Exception as e:
            self.console.print(f"    ❌ Error getting cluster nodes: {e}", style="red")
            return []

    def select_best_data_nodes(
        self, data_nodes: List[Dict], cluster_name: str
    ) -> List[Dict]:
        """Select the best 2 different data nodes from different complete hosts, preferring ess nodes over esh nodes"""
        if len(data_nodes) == 0:
            self.console.print(
                f"    🔶  Warning: No data nodes found for cluster {cluster_name}",
                style="yellow",
            )
            return []

        # Filter out esh nodes and prefer ess nodes
        ess_nodes = [node for node in data_nodes if "ess" in node["name"].lower()]
        esh_nodes = [node for node in data_nodes if "esh" in node["name"].lower()]

        # Log filtering results
        if esh_nodes:
            esh_names = [node["name"] for node in esh_nodes]
            self.console.print(
                f"    🚫 Excluding {len(esh_nodes)} esh nodes: {', '.join(esh_names)}",
                style="yellow",
            )

        # Use ess nodes if available, otherwise fall back to remaining nodes (excluding esh)
        filtered_nodes = (
            ess_nodes
            if ess_nodes
            else [node for node in data_nodes if "esh" not in node["name"].lower()]
        )

        if len(filtered_nodes) == 0:
            self.console.print(
                f"    🔶  Warning: No suitable data nodes found after filtering out esh nodes for cluster {cluster_name}",
                style="yellow",
            )
            return []

        if len(filtered_nodes) == 1:
            self.console.print(
                f"    🔶  Warning: Only 1 suitable data node found after filtering for cluster {cluster_name}",
                style="yellow",
            )
            return filtered_nodes

        # Extract host groups from node names (e.g., "iad51-c01-ess01-1" -> "iad51-c01-ess01")
        def get_host_group(node_name):
            parts = node_name.split("-")
            if len(parts) >= 4:
                # Return everything except the last part (instance number)
                return "-".join(parts[:-1])
            return node_name

        # Group nodes by host group
        host_groups = {}
        for node in filtered_nodes:
            host_group = get_host_group(node["name"])
            if host_group not in host_groups:
                host_groups[host_group] = []
            host_groups[host_group].append(node)

        # Sort host groups by name for consistent selection
        sorted_host_groups = sorted(host_groups.keys())

        selected = []
        # Select one node from each different host group, up to 2 nodes
        for host_group in sorted_host_groups:
            if len(selected) >= 2:
                break
            # Sort nodes within each host group and select the first one
            nodes_in_group = sorted(host_groups[host_group], key=lambda x: x["name"])
            selected.append(nodes_in_group[0])

        # If we still need more nodes and have fewer than 2 host groups,
        # select additional nodes from existing groups
        if len(selected) < 2:
            all_sorted_nodes = sorted(filtered_nodes, key=lambda x: x["name"])
            for node in all_sorted_nodes:
                if node not in selected:
                    selected.append(node)
                    if len(selected) >= 2:
                        break

        node_names = [node["name"] for node in selected]
        self.console.print(
            f"    🎯 Selected data nodes from different hosts: [bold blue]{', '.join(node_names)}[/bold blue]"
        )

        return selected

    def create_minimal_config(
        self,
        cluster_name: str,
        discovery_host: str,
        ssl: bool,
        location: str,
        file_env: str,
        preserve: bool = False,
        config_password_override: Optional[str] = None,
        elastic_username_override: Optional[str] = None,
        use_inline_kibana_password: bool = False,
    ) -> Dict:
        """Create minimal configuration using discovery host when node discovery fails"""
        self.console.print(
            f"    🔧 Creating minimal config for {cluster_name} using discovery host",
            style="yellow",
        )

        # Extract host and port
        host, port = (
            discovery_host.split(":")
            if ":" in discovery_host
            else (discovery_host, "9200")
        )
        port = int(port)

        password_envs = self.env_password_chains.get(file_env, ["prod"])
        env = (
            config_password_override
            if config_password_override is not None
            else password_envs[0]
        )

        entries: List[Tuple[str, Any]] = [
            ("name", cluster_name),
            ("config_password", env),
            ("env", file_env),
            ("hostname", host),
            ("port", port),
            ("use_ssl", ssl),
            ("verify_certs", False),
            ("elastic_authentication", True),
        ]
        entries.extend(
            self._elastic_auth_entries(
                elastic_username_override or "",
                use_inline_kibana_password,
            )
        )
        server_config = OrderedDict(entries)

        # Add preserve flag if set in cluster config
        if preserve:
            server_config["preserve"] = preserve
            self.console.print(
                f"    🔒 Server marked as preserve - will not be removed during updates",
                style="blue",
            )

        # Add S3 snapshot repository if configured for this cluster
        if cluster_name in self.s3snapshot_repo_mapping:
            repo_name = self.s3snapshot_repo_mapping[cluster_name]
            server_config["elastic_s3snapshot_repo"] = repo_name
            self.console.print(
                f"    📦 Added S3 snapshot repository: {repo_name}", style="cyan"
            )

        # Add comment explaining the fallback
        fallback_comment = f"# Using discovery host (node discovery failed - possibly ReadonlyREST): {discovery_host}"
        server_config["_primary_node_comment"] = fallback_comment

        return server_config

    def extract_hostname_from_transport(
        self, transport_address: str
    ) -> Tuple[str, str]:
        """Extract hostname/IP from transport address

        Returns:
            Tuple[str, str]: (ip_or_hostname, original_address)
        """
        # Transport address format is usually "hostname:port" or "ip:port"
        if ":" in transport_address:
            address = transport_address.split(":")[0]
            return address, transport_address
        return transport_address, transport_address

    def process_cluster(
        self, cluster_key: str, cluster_config: Dict, file_env: str
    ) -> Optional[Dict]:
        """Process a single cluster configuration"""
        self.console.print(
            f"  🔍 Processing cluster: [bold cyan]{cluster_key}[/bold cyan]"
        )

        cluster_name = cluster_config.get("cluster.name", cluster_key)
        discovery_host = cluster_config.get("discovery.host")
        ssl = cluster_config.get("ssl", False)
        location = cluster_config.get("location", "unknown")
        preserve = cluster_config.get("preserve", False)

        if not discovery_host:
            self.console.print(
                f"    ❌ Error: No discovery.host found for cluster {cluster_key}",
                style="red",
            )
            return None

        # Test basic connectivity first
        host, port = (
            discovery_host.split(":")
            if ":" in discovery_host
            else (discovery_host, "9200")
        )
        port = int(port)

        connectivity_success, resolved_host = self.test_basic_connectivity(
            host, port, ssl
        )
        if not connectivity_success:
            self.console.print(
                f"    ⏩ Basic connectivity failed - skipping cluster {cluster_name}",
                style="yellow",
            )
            return None

        # Use resolved hostname if different from original
        effective_discovery_host = discovery_host
        if resolved_host != host:
            # Update discovery host to use resolved hostname
            effective_discovery_host = f"{resolved_host}:{port}"
            self.console.print(
                f"    🔄 Using resolved hostname for ES connection: {effective_discovery_host}",
                style="cyan",
            )

        # Connect to Elasticsearch
        connection_result = self.connect_to_elasticsearch(
            effective_discovery_host, ssl, location, file_env
        )
        if not connection_result:
            # If connection failed, try to create a minimal config using discovery host
            self.console.print(
                f"    🔧 ES connection failed, creating minimal config using discovery host",
                style="yellow",
            )
            return self.create_minimal_config(
                cluster_name,
                effective_discovery_host,
                ssl,
                location,
                file_env,
                preserve,
            )

        es_client, successful_password_env, winning_username, use_inline_kibana = (
            connection_result
        )

        # Get data nodes
        data_nodes = self.get_cluster_nodes(es_client)
        if not data_nodes:
            # If node discovery failed (ReadonlyREST blocking), use discovery host
            self.console.print(
                f"    🔧 Node discovery failed (possibly ReadonlyREST), using discovery host as fallback",
                style="yellow",
            )
            return self.create_minimal_config(
                cluster_name,
                effective_discovery_host,
                ssl,
                location,
                file_env,
                preserve,
                config_password_override=successful_password_env,
                elastic_username_override=winning_username,
                use_inline_kibana_password=use_inline_kibana,
            )

        # Select best 2 data nodes
        selected_nodes = self.select_best_data_nodes(data_nodes, cluster_name)
        if not selected_nodes:
            return None

        # Extract hostnames and IPs from selected data nodes
        host_data = []
        for node in selected_nodes:
            # Try to extract hostname from transport address first
            address, original_transport = self.extract_hostname_from_transport(
                node["transport_address"]
            )
            if address and address != "unknown":
                host_data.append(
                    {
                        "address": address,
                        "original_hostname": node["name"],
                        "transport_address": original_transport,
                        "host_field": node["host"],
                    }
                )
            else:
                # Fallback to host field
                host_data.append(
                    {
                        "address": node["host"],
                        "original_hostname": node["name"],
                        "transport_address": node["transport_address"],
                        "host_field": node["host"],
                    }
                )

        # Ensure we have at least one hostname
        if not host_data:
            self.console.print(
                f"    ❌ Error: Could not extract hostnames for cluster {cluster_name}",
                style="red",
            )
            return None

        # Get port from discovery host
        port = int(discovery_host.split(":")[1]) if ":" in discovery_host else 9200

        env = successful_password_env

        entries = [
            ("name", cluster_name),
            ("config_password", env),
            ("env", file_env),
            ("hostname", host_data[0]["address"]),
            ("port", port),
            ("use_ssl", ssl),
            ("verify_certs", False),
            ("elastic_authentication", True),
        ]
        entries.extend(
            self._elastic_auth_entries(winning_username, use_inline_kibana)
        )
        server_config = OrderedDict(entries)

        # Add preserve flag if set in cluster config
        if preserve:
            server_config["preserve"] = preserve
            self.console.print(
                f"    🔒 Server marked as preserve - will not be removed during updates",
                style="blue",
            )

        # Add hostname comment for primary host
        primary_comment = f"# Primary data node: {host_data[0]['original_hostname']} ({host_data[0]['transport_address']})"
        server_config["_primary_node_comment"] = primary_comment

        # Add second hostname if we have a second data node
        if len(host_data) > 1:
            server_config["hostname2"] = host_data[1][
                "address"
            ]  # Use IP address of second data node
            secondary_comment = f"# Secondary data node: {host_data[1]['original_hostname']} ({host_data[1]['transport_address']})"
            server_config["_secondary_node_comment"] = secondary_comment

        # Add S3 snapshot repository if configured for this cluster
        if cluster_name in self.s3snapshot_repo_mapping:
            repo_name = self.s3snapshot_repo_mapping[cluster_name]
            server_config["elastic_s3snapshot_repo"] = repo_name
            self.console.print(
                f"    📦 Added S3 snapshot repository: {repo_name}", style="cyan"
            )

        hostname2_info = f" + {host_data[1]['address']}" if len(host_data) > 1 else ""
        selected_node_names = [node["original_hostname"] for node in host_data]
        self.console.print(
            f"    ✅ Generated config for [bold green]{cluster_name}[/bold green]: {host_data[0]['address']}:{port}{hostname2_info} (data nodes: {', '.join(selected_node_names)})"
        )
        return server_config

    def _yaml_to_string_with_comments(self, config: Dict) -> str:
        """Convert configuration to YAML string with comments"""
        # First convert to YAML without comment keys
        clean_config = self._remove_comment_keys(config)
        yaml_content = yaml.dump(
            clean_config, default_flow_style=False, sort_keys=False, indent=2
        )

        # Add comments for servers
        lines = yaml_content.split("\n")
        output_lines = []

        for i, line in enumerate(lines):
            output_lines.append(line)

            # Check if this line defines a server hostname
            if "  hostname:" in line and i > 0:
                # Find the corresponding server config
                server_name = None
                for j in range(i - 1, -1, -1):
                    if lines[j].startswith("- name:"):
                        server_name = lines[j].replace("- name:", "").strip()
                        break

                if server_name:
                    # Find the original server config with comments
                    for server in config.get("servers", []):
                        if server.get("name") == server_name:
                            if "_primary_node_comment" in server:
                                output_lines.append(
                                    f"  {server['_primary_node_comment']}"
                                )
                            break

            # Check if this line defines a server hostname2
            elif "  hostname2:" in line:
                # Find the corresponding server config
                server_name = None
                for j in range(i - 1, -1, -1):
                    if lines[j].startswith("- name:"):
                        server_name = lines[j].replace("- name:", "").strip()
                        break

                if server_name:
                    # Find the original server config with comments
                    for server in config.get("servers", []):
                        if server.get("name") == server_name:
                            if "_secondary_node_comment" in server:
                                output_lines.append(
                                    f"  {server['_secondary_node_comment']}"
                                )
                            break

        return "\n".join(output_lines)

    def _remove_comment_keys(self, config: Dict) -> Dict:
        """Remove comment keys from configuration recursively"""
        if isinstance(config, dict):
            clean_config = {}
            for key, value in config.items():
                if not key.startswith("_") or not key.endswith("_comment"):
                    clean_config[key] = self._remove_comment_keys(value)
            return clean_config
        elif isinstance(config, list):
            return [self._remove_comment_keys(item) for item in config]
        else:
            return config

    def _write_yaml_with_comments(self, config: Dict, filename: str):
        """Write configuration to YAML file with comments"""
        yaml_content = self._yaml_to_string_with_comments(config)
        with open(filename, "w") as f:
            f.write(yaml_content)

    def _merge_configurations(self, new_servers: List[Dict]) -> Dict:
        """Merge new servers with existing configuration"""
        if not self.existing_config:
            # No existing config, create new one
            return {"servers": new_servers}

        # Merge with existing configuration
        merged_config = dict(self.existing_config)

        # Get environment being processed
        if self.environment == "all":
            # Replace all servers
            merged_config["servers"] = new_servers
        else:
            # Remove existing servers from the same CONFIG environment and add new ones
            existing_servers = merged_config.get("servers", [])

            # Find config environments being processed (not password environments)
            processed_config_envs = set()
            for server in new_servers:
                processed_config_envs.add(
                    server.get("config_env", server.get("env"))
                )  # fallback to env for older configs

            # Keep servers from other config environments OR servers marked as preserve
            filtered_servers = [
                server
                for server in existing_servers
                if (
                    server.get("config_env", server.get("env"))
                    not in processed_config_envs
                    or server.get("preserve", False)
                )
            ]

            # Count preserved servers for reporting
            preserved_count = sum(
                1
                for server in existing_servers
                if server.get("preserve", False)
                and server.get("config_env", server.get("env")) in processed_config_envs
            )

            # Add new servers
            merged_config["servers"] = filtered_servers + new_servers

            removed_count = len(existing_servers) - len(filtered_servers)
            if preserved_count > 0:
                self.console.print(
                    f"🔒 Preserved {preserved_count} servers marked with 'preserve: true'",
                    style="blue",
                )
            self.console.print(
                f"❌ Removed {removed_count} existing servers for config environment(s): {processed_config_envs}",
                style="yellow",
            )
            self.console.print(
                f"➕ Added {len(new_servers)} new servers", style="green"
            )

        return merged_config

    def generate_config(
        self, dry_run: bool = False, replace_mode: bool = False
    ) -> Dict:
        """Generate the complete elastic_servers.yml configuration"""
        # Auto-enable update mode when processing single environment (unless explicitly processing 'all' or using --replace)
        auto_update_mode = (
            self.environment != "all" and not self.update_mode and not replace_mode
        )
        effective_update_mode = self.update_mode or auto_update_mode

        mode_msg = f"Processing environment: {self.environment}"
        if effective_update_mode:
            if auto_update_mode:
                mode_msg += " (AUTO-MERGE MODE - preserving other environments)"
            else:
                mode_msg += " (UPDATE MODE)"

        # Create a nice header panel
        header_panel = Panel(
            Text(
                f"🚀 Elasticsearch Servers Configuration Generator\n{mode_msg}",
                justify="center",
            ),
            style="bold cyan",
            border_style="cyan",
        )
        self.console.print(header_panel)

        # Auto-load existing config if we're going to merge and haven't loaded yet
        if effective_update_mode and not self.existing_config:
            self._load_existing_config()

        # Read crosscluster files (filtered by environment if specified)
        crosscluster_configs = self.read_crosscluster_files()

        generated_servers = []

        # Count total clusters for progress tracking
        total_clusters = sum(
            len(clusters) for clusters in crosscluster_configs.values()
        )

        # Process each environment file with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            main_task = progress.add_task(
                "Processing clusters...", total=total_clusters
            )

            for file_env, clusters in crosscluster_configs.items():
                env_panel = Panel(
                    f"📂 Processing environment file: [bold yellow]{file_env}[/bold yellow] ({len(clusters)} clusters)",
                    style="blue",
                    border_style="blue",
                )
                self.console.print(env_panel)

                for cluster_key, cluster_config in clusters.items():
                    if not isinstance(cluster_config, dict):
                        progress.advance(main_task)
                        continue

                    progress.update(main_task, description=f"Processing {cluster_key}")
                    # Pass the command line environment, not the extracted filename environment
                    server_config = self.process_cluster(
                        cluster_key,
                        cluster_config,
                        self.environment if self.environment != "all" else file_env,
                    )
                    if server_config:
                        generated_servers.append(server_config)

                    progress.advance(main_task)

        # Generate final configuration (merge if in update mode or auto-merge mode)
        if effective_update_mode:
            final_config = self._merge_configurations(generated_servers)
        else:
            final_config = {"servers": generated_servers}

        total_servers = len(final_config["servers"])

        # Create summary table
        summary_table = Table(title="🎯 Generation Summary", style="bold")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Environment", self.environment)
        summary_table.add_row("Total Servers", str(total_servers))
        summary_table.add_row("Generated/Updated", str(len(generated_servers)))
        summary_table.add_row(
            "Mode",
            "Auto-Merge"
            if effective_update_mode and auto_update_mode
            else "Update"
            if effective_update_mode
            else "Replace",
        )

        self.console.print(summary_table)

        if not dry_run:
            # Write to file with comments
            self._write_yaml_with_comments(final_config, self.output_file)
            self.console.print(
                f"📁 Configuration written to [bold green]{self.output_file}[/bold green]"
            )
        else:
            self.console.print(
                "[bold yellow]🔍 DRY RUN - Configuration not written to file[/bold yellow]"
            )
            if (
                len(generated_servers) <= 5
            ):  # Only show preview for small number of servers
                self.console.print(f"\n📋 Generated configuration preview:")
                # In dry run, just show the newly generated servers
                preview_config = dict(final_config)
                preview_config["servers"] = generated_servers
                preview_yaml = self._yaml_to_string_with_comments(preview_config)
                # Limit output length for readability
                if len(preview_yaml) > 2000:
                    preview_yaml = preview_yaml[:2000] + "\n... (truncated)"
                self.console.print(preview_yaml)

        return final_config


def _has_per_env_escmd_password_vars() -> bool:
    prefix = "ESCMD_GEN_PASSWORD_"
    return any(k.startswith(prefix) for k in os.environ)


def _load_cli_password_env_file(path: str) -> Dict[str, str]:
    fpath = Path(path)
    if not fpath.is_file():
        raise FileNotFoundError(f"Password env file not found: {path}")
    text = fpath.read_text(encoding="utf-8")
    if path.lower().endswith(".json"):
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(
            "Password env file must be a JSON/YAML object mapping "
            f"config_password env name to password string: {path}"
        )
    out: Dict[str, str] = {}
    for k, v in data.items():
        ks = str(k).lower().strip()
        if not ks or v is None:
            continue
        vs = str(v).strip()
        if vs:
            out[ks] = vs
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Generate Elasticsearch servers configuration"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="elastic_servers.yml",
        help="Output file name (default: elastic_servers_new.yml)",
    )
    parser.add_argument(
        "--yml-dir",
        default="/etc/git/ELK_scripts/ol9/kcs/maintenance/crosscluster",
        help="Directory containing crosscluster YAML files (default: /etc/git/ELK_scripts/ol9/kcs/maintenance/crosscluster)",
    )
    parser.add_argument(
        "--environment",
        "--env",
        choices=["biz", "eu", "in", "lab", "ops", "stress", "us", "all"],
        default="all",
        help="Process specific environment only (default: all)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing configuration file instead of replacing it",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace entire file even when processing single environment (disables auto-merge)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing to file",
    )
    parser.add_argument(
        "--es-timeout",
        type=int,
        default=30,
        metavar="SEC",
        help="Elasticsearch and basic HTTP probe timeout in seconds (default: 30). "
        "Increase for slow auth or busy nodes.",
    )
    parser.add_argument(
        "--escmd-json",
        default=None,
        help="Path to escmd.json for stored passwords and elastic_username (default: beside this script)",
    )
    parser.add_argument(
        "--username",
        "-u",
        default=None,
        help="Try this username per config_password env (see --password-env-file and ESCMD_GEN_PASSWORD_<ENV>)",
    )
    parser.add_argument(
        "--password",
        "-p",
        default=None,
        help="Default/fallback password for --username when no per-env password is set",
    )
    parser.add_argument(
        "--password-env-file",
        default=None,
        metavar="PATH",
        help="YAML or JSON map: config_password env -> password (e.g. prod, eu, in, lab). Requires --username.",
    )
    parser.add_argument(
        "--prompt-password",
        action="store_true",
        help="Always prompt once for default/fallback password (--username)",
    )

    args = parser.parse_args()

    console = Console()
    cli_username = args.username.strip() if args.username else None
    cli_password_by_env: Dict[str, str] = {}
    if args.password_env_file:
        if not cli_username:
            console.print(
                "[bold red]--password-env-file requires --username.[/bold red]"
            )
            sys.exit(1)
        try:
            cli_password_by_env = _load_cli_password_env_file(args.password_env_file)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            console.print(f"[bold red]Invalid password env file: {e}[/bold red]")
            sys.exit(1)

    cli_password = args.password or os.environ.get("ESCMD_GEN_PASSWORD")
    if cli_username:
        if args.prompt_password:
            cli_password = getpass.getpass(
                f"Password for user '{cli_username}' (default/fallback): "
            )
        elif (
            not cli_password
            and not cli_password_by_env
            and not _has_per_env_escmd_password_vars()
        ):
            cli_password = getpass.getpass(
                f"Password for user '{cli_username}' (default/fallback): "
            )

    has_cli_secret = (
        bool(cli_password)
        or bool(cli_password_by_env)
        or _has_per_env_escmd_password_vars()
    )
    if cli_username and not has_cli_secret:
        console.print(
            "[bold red]Provide a password: --password / ESCMD_GEN_PASSWORD, "
            "--password-env-file, ESCMD_GEN_PASSWORD_<ENV> (e.g. ESCMD_GEN_PASSWORD_IN), "
            "or run interactively.[/bold red]"
        )
        sys.exit(1)
    if args.prompt_password and not cli_username:
        console.print(
            "[yellow]Note: --prompt-password has no effect without --username.[/yellow]"
        )

    try:
        generator = ElasticsearchServerGenerator(
            yml_directory=args.yml_dir,
            output_file=args.output,
            environment=args.environment,
            update_mode=args.update,
            escmd_json_path=args.escmd_json,
            cli_username=cli_username,
            cli_password=cli_password,
            cli_password_by_env=cli_password_by_env,
            es_timeout=args.es_timeout,
        )

        config = generator.generate_config(
            dry_run=args.dry_run, replace_mode=args.replace
        )

        if not args.dry_run:
            if args.update or (args.environment != "all" and not args.replace):
                success_panel = Panel(
                    Text(
                        f"✅ Success! Updated configuration saved to: {args.output}",
                        style="bold green",
                    ),
                    style="green",
                    border_style="green",
                )
                console.print(success_panel)
                if args.environment != "all" and not args.replace:
                    console.print(
                        f"🔀 Environment '{args.environment}' has been merged (other environments preserved)",
                        style="cyan",
                    )
                else:
                    console.print(
                        f"➕ Environment '{args.environment}' has been updated/added",
                        style="cyan",
                    )
            else:
                success_panel = Panel(
                    Text(
                        f"✅ Success! Generated configuration saved to: {args.output}",
                        style="bold green",
                    ),
                    style="green",
                    border_style="green",
                )
                console.print(success_panel)
                if args.replace and args.environment != "all":
                    console.print(
                        f"🔄 File replaced with only environment '{args.environment}' (--replace mode)",
                        style="yellow",
                    )

            # Create next steps table
            steps_table = Table(title="📋 Next Steps", style="bold")
            steps_table.add_column("Step", style="cyan", width=5)
            steps_table.add_column("Action", style="white")

            steps_table.add_row(
                "1.", f"Review the generated configuration: {args.output}"
            )
            steps_table.add_row("2.", "Test the configuration with a few clusters")

            if not args.update and (args.environment == "all" or args.replace):
                steps_table.add_row("3.", "Backup your current elastic_servers.yml")
                steps_table.add_row(
                    "4.", f"Replace elastic_servers.yml with {args.output}"
                )
            else:
                steps_table.add_row(
                    "3.", "The configuration has been incrementally updated"
                )
                steps_table.add_row("4.", "Test the new/updated clusters")

            console.print(steps_table)

    except Exception as e:
        console = Console()
        error_panel = Panel(
            Text(f"❌ Error: {e}", style="bold red"), style="red", border_style="red"
        )
        console.print(error_panel)
        sys.exit(1)


if __name__ == "__main__":
    main()
