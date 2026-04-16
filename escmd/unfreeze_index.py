#!/usr/bin/env python3
"""
Index Opener (DataStream) version.
Written by Devin Acosta
- Adding in date range for opens.
- Updated to work with unified escmd configuration system
"""

import warnings
import urllib3
from dataclasses import dataclass
from requests.auth import HTTPBasicAuth
from elasticsearch import Elasticsearch, ConnectionTimeout
from collections import defaultdict
from rich import print
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import Progress, Spinner
from rich.syntax import Syntax
from rich.text import Text
from rich import box
from rich.box import Box

import getpass
import argparse
import datetime
from io import StringIO
import pickle
import re
import requests
import subprocess
import time
import urllib3
import warnings
import yaml
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from typing import Optional

# Import unified configuration components
from configuration_manager import ConfigurationManager
from security.password_manager import PasswordManager
from display.theme_manager import ThemeManager
from display.style_system import StyleSystem

# VERSION/DATE INFO
VERSION = "2.1.0"
DATE = "04/16/2026"


@dataclass
class UnfreezeUI:
    """Shared console + theme wiring for escmd.json + themes.yml."""

    console: Console
    theme_manager: ThemeManager
    style_system: StyleSystem


def make_configuration_manager(script_directory: str) -> ConfigurationManager:
    """Load escmd.yml + elastic_servers.yml when present so themes_file resolves."""
    state_file = os.path.join(script_directory, "escmd.json")
    main_yml = os.path.join(script_directory, "escmd.yml")
    servers_yml = os.path.join(script_directory, "elastic_servers.yml")
    if os.path.isfile(main_yml) and os.path.isfile(servers_yml):
        return ConfigurationManager(
            state_file_path=state_file,
            main_config_path=main_yml,
            servers_config_path=servers_yml,
        )
    return ConfigurationManager(state_file_path=state_file)


def build_unfreeze_ui(console: Console, config_manager: ConfigurationManager) -> UnfreezeUI:
    theme_manager = ThemeManager(config_manager)
    return UnfreezeUI(
        console=console,
        theme_manager=theme_manager,
        style_system=StyleSystem(theme_manager),
    )


def print_unfreeze_banner(ui: UnfreezeUI, today_date: str) -> None:
    border = ui.theme_manager.get_themed_style(
        "table_styles", "border_style", "bright_magenta"
    )
    title_st = ui.theme_manager.get_themed_style("panel_styles", "title", "bold cyan")
    sub_st = ui.theme_manager.get_themed_style("panel_styles", "subtitle", "dim")
    info_st = ui.style_system.get_semantic_style("info")
    theme_name = ui.theme_manager.get_theme_name()
    body = Text.assemble(
        ("Unfreeze indices by location, component, and date range.\n", sub_st),
        (f"Active theme: ", sub_st),
        (theme_name, info_st),
        (f"  ·  Today: {today_date}", sub_st),
    )
    ui.console.print(
        Panel.fit(
            body,
            title=Text("UNFREEZE INDEX", style=title_st),
            subtitle=Text(f"v{VERSION} · {DATE}", style=sub_st),
            border_style=border,
            padding=(1, 2),
        )
    )
    ui.console.print()


def print_no_frozen_celebration(ui: UnfreezeUI, normal_count: int) -> None:
    """Themed, centered success when every matched index is already unfrozen."""
    ss = ui.style_system
    tm = ui.theme_manager
    succ = ss.get_semantic_style("success")
    neu = ss.get_semantic_style("neutral")
    prim = ss.get_semantic_style("primary")
    sub_st = tm.get_themed_style("panel_styles", "subtitle", neu)
    idx_word = "indices" if normal_count != 1 else "index"

    hero = Text.assemble(
        ("✓  ", succ),
        ("ALL CLEAR", succ),
    )
    blurb = Text.assemble(
        ("No frozen indices in this selection.\n", neu),
        (f"{normal_count}", prim),
        (f" {idx_word} ", neu),
        ("checked — ", neu),
        ("already unfrozen", succ),
        (" and ready to query.", neu),
    )
    foot = Text(
        "No unfreeze operations were required for this selection.",
        style=sub_st,
    )
    body = Group(
        Align.center(hero),
        Text(""),
        Align.center(blurb),
        Text(""),
        Align.center(foot),
    )
    ui.console.print()
    ui.console.print(ss.create_success_panel(body, title="Index state", icon="✨"))
    ui.console.print()


# Define Global Variables
gbl_password = False
cmd_password = None

# Suppress the UserWarning
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")

# Suppress only the InsecureRequestWarning from urllib3 needed for Elasticsearch
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(DeprecationWarning)


def Merge(dict1, dict2):
    return dict2.update(dict1)


def returnDict(dictlist):
    return dict(dictlist)


def find_most_likely_file(file_dict, target_date):
    """
    Find the file with the date closest to the target date.
    """
    target_datetime = datetime.datetime.strptime(target_date, "%Y.%m.%d")
    closest_file = None
    closest_diff = float("inf")

    for filename in file_dict.keys():
        file_date = extract_and_format_date(filename)
        if file_date:
            file_datetime = datetime.datetime.strptime(file_date, "%Y.%m.%d")
            diff = abs((file_datetime - target_datetime).days)
            if diff < closest_diff:
                closest_diff = diff
                closest_file = filename

    return closest_file


def find_closest_file(filenames, target_date):
    """
    Find the file with the date closest to the target date, but only considering dates
    on or before the target date (never after).
    Takes a list of filenames and extracts date from filename using split.
    """
    # Convert the target date string to a datetime object
    target_datetime = datetime.datetime.strptime(target_date, "%Y.%m.%d")

    closest_file = None
    closest_delta = None

    for filename in filenames:
        try:
            # Extract date from filename using the same method as original
            file_date_str = filename.split("-")[-2]
            file_datetime = datetime.datetime.strptime(file_date_str, "%Y.%m.%d")

            # Skip any files with dates after the target date
            if file_datetime > target_datetime:
                continue

            # Calculate the time delta between the target date and the file date
            delta = target_datetime - file_datetime

            # Update the closest file if necessary
            if closest_file is None or delta < closest_delta:
                closest_file = filename
                closest_delta = delta
        except (ValueError, IndexError):
            # Skip files that don't have the expected date format
            continue

    return closest_file


def read_yaml_file(file_path):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def get_server_config(location, config_manager):
    """
    Get server configuration for a location with fallback logic.
    First tries exact match, then tries with -c01 suffix.
    """

    # Get all servers as a dictionary keyed by name
    servers_dict = config_manager.servers_dict

    # First try exact match (case insensitive)
    for server_name, server_config in servers_dict.items():
        if server_name.upper() == location.upper():
            return server_config

    # If no exact match, try with -c01 suffix
    fallback_name = f"{location}-c01"
    for server_name, server_config in servers_dict.items():
        if server_name.upper() == fallback_name.upper():
            return server_config

    # If still no match, raise an error
    raise ValueError(
        f"No server configuration found for location '{location}' or '{fallback_name}'"
    )


def get_password_for_server(
    server_config, password_manager, gbl_password, cmd_password, username=None
):
    """
    Get password for a server using the unified password management system.
    """

    # If password was provided via command line, use it
    if gbl_password and cmd_password:
        return cmd_password

    # Check if server requires authentication
    if not server_config.get("elastic_authentication", False):
        return None

    # First check if password is directly configured in server config
    direct_password = server_config.get("elastic_password")
    if direct_password:
        return direct_password

    # Try to get password from encrypted storage
    config_password_env = server_config.get("config_password")
    if config_password_env:
        # Try with username first (e.g., "prod.kibana_system")
        stored_password = password_manager.get_password(config_password_env, username)
        if stored_password:
            return stored_password

    # Fallback: try global password
    global_password = password_manager.get_password("global", username)
    if global_password:
        return global_password

    # If no stored password found and authentication is required, prompt user
    if server_config.get("elastic_authentication", False):
        env_key = (
            f"{config_password_env}.{username}"
            if config_password_env and username
            else config_password_env or "global"
        )
        print(
            f"[yellow]No stored password found for '{env_key}' (trying username: {username or 'none'})[/yellow]"
        )
        print(
            f"[cyan]Store password with: ./escmd.py store-password {config_password_env or 'global'} --username {username or 'kibana_system'}[/cyan]"
        )
        return getpass.getpass(
            f"Enter password for {username}@{server_config.get('hostname', 'server')}: "
        )

    return None


def uniquePatterns(dictionaries):
    patterns = set()
    for dictionary in dictionaries:
        # Extract pattern by removing date-like substrings AND the sequential number
        # Example: .ds-iad41-c02-logs-asg-app-2025.08.20-000080 -> .ds-iad41-c02-logs-asg-app
        pattern = re.sub(r"-\d{4}\.\d{2}\.\d{2}-\d+$", "", dictionary)
        patterns.add(pattern)
    return list(patterns)


def getIndices(
    location, port, config_manager, password_manager, gbl_password, cmd_password
):
    """
    Get indices from Elasticsearch server.
    """
    try:
        server_config = get_server_config(location, config_manager)
        hostname = server_config.get("hostname")
        hostname2 = server_config.get("hostname2")
        use_ssl = server_config.get("use_ssl", False)
        verify_certs = server_config.get("verify_certs", True)

        username = config_manager._resolve_username(server_config) or "kibana_system"
        password = get_password_for_server(
            server_config, password_manager, gbl_password, cmd_password, username
        )

        # Build connection URL
        protocol = "https" if use_ssl else "http"
        es_url = f"{protocol}://{hostname}:{port}"

        # Create Elasticsearch client with reasonable timeouts
        if server_config.get("elastic_authentication", False) and password:
            es = Elasticsearch(
                [es_url],
                http_auth=(username, password),
                verify_certs=verify_certs,
                timeout=15,  # Increased timeout for reliability
                max_retries=2,  # Add retries for reliability
                retry_on_timeout=True,
            )
        else:
            es = Elasticsearch(
                [es_url],
                verify_certs=verify_certs,
                timeout=15,  # Increased timeout for reliability
                max_retries=2,  # Add retries for reliability
                retry_on_timeout=True,
            )

        # Test connection with timeout - try primary hostname first
        if not es.ping() and hostname2:
            # print(f"[yellow]Connection to {hostname} failed. Attempting to connect to {hostname2}...[/yellow]")
            # Try backup hostname
            es_url2 = f"{protocol}://{hostname2}:{port}"
            if server_config.get("elastic_authentication", False) and password:
                es = Elasticsearch(
                    [es_url2],
                    http_auth=(username, password),
                    verify_certs=verify_certs,
                    timeout=15,
                    max_retries=2,
                    retry_on_timeout=True,
                )
            else:
                es = Elasticsearch(
                    [es_url2],
                    verify_certs=verify_certs,
                    timeout=15,
                    max_retries=2,
                    retry_on_timeout=True,
                )

            if not es.ping():
                return {location: {}}

        # Get all indices
        indices_response = es.cat.indices(
            format="json",
            h="index,status,health,pri,rep,docs.count,store.size",
            request_timeout=15,
        )

        indices_dict = {}
        for idx in indices_response:
            index_name = idx["index"]
            indices_dict[index_name] = {
                "status": idx.get("status", "unknown"),
                "health": idx.get("health", "unknown"),
                "pri": idx.get("pri", "0"),
                "rep": idx.get("rep", "0"),
                "docs_count": idx.get("docs.count", "0"),
                "store_size": idx.get("store.size", "0"),
                "port": port,
                "hostname": hostname,
            }

        return {location: indices_dict}

    except (ConnectionTimeout, Exception):
        return {location: {}}


def processResults(indices_dict, components):
    """
    Filter indices based on component patterns.
    """
    matching_indices = []

    for index_name, index_info in indices_dict.items():
        for component in components:
            if component.lower() in index_name.lower():
                matching_indices.append(index_name)
                break

    return matching_indices


def matchingIndices(indices_list, pattern):
    """
    Find indices matching a specific pattern.
    Returns a list of matching index names (not a dictionary).
    """
    matching_keys = []
    search_pattern = f".*{pattern}.*"
    regex_pattern = re.compile(search_pattern)

    # Loop through indices and find matches
    for index_name in indices_list:
        if regex_pattern.match(index_name):
            matching_keys.append(index_name)

    return matching_keys


def fetch_elastic_frozen_data(
    location,
    index_name,
    port,
    config_manager,
    password_manager,
    gbl_password,
    cmd_password,
):
    """
    Check if an index is frozen.
    """
    try:
        server_config = get_server_config(location, config_manager)
        hostname = server_config.get("hostname")
        hostname2 = server_config.get("hostname2")
        use_ssl = server_config.get("use_ssl", False)
        verify_certs = server_config.get("verify_certs", True)

        username = config_manager._resolve_username(server_config) or "kibana_system"
        password = get_password_for_server(
            server_config, password_manager, gbl_password, cmd_password, username
        )

        # Build connection URL
        protocol = "https" if use_ssl else "http"
        es_url = f"{protocol}://{hostname}:{port}"

        # Create Elasticsearch client with shorter timeout
        if server_config.get("elastic_authentication", False) and password:
            es = Elasticsearch(
                [es_url],
                http_auth=(username, password),
                verify_certs=verify_certs,
                timeout=5,
            )
        else:
            es = Elasticsearch([es_url], verify_certs=verify_certs, timeout=5)

        # Test connection and try backup hostname if needed
        if not es.ping() and hostname2:
            # Try backup hostname
            es_url2 = f"{protocol}://{hostname2}:{port}"
            if server_config.get("elastic_authentication", False) and password:
                es = Elasticsearch(
                    [es_url2],
                    http_auth=(username, password),
                    verify_certs=verify_certs,
                    timeout=5,
                )
            else:
                es = Elasticsearch([es_url2], verify_certs=verify_certs, timeout=5)

            if not es.ping():
                return False

        # Check if index is frozen
        settings = es.indices.get_settings(index=index_name, request_timeout=5)
        index_settings = (
            settings.get(index_name, {}).get("settings", {}).get("index", {})
        )

        frozen = index_settings.get("frozen", "false")
        return frozen.lower() == "true"

    except Exception:
        return False


def get_frozenStatus(
    batched_dict,
    config_manager,
    password_manager,
    gbl_password,
    cmd_password,
    ui: UnfreezeUI,
):
    """
    Get frozen status for all indices in batched dictionary.
    """
    ss = ui.style_system
    results = {}
    total_indices = len(batched_dict)
    prim = ss.get_semantic_style("primary")
    sec = ss.get_semantic_style("secondary")
    neu = ss.get_semantic_style("neutral")

    with ui.console.status(
        Text.assemble(
            ("⠋ ", prim),
            ("Checking frozen status for ", neu),
            (str(total_indices), sec),
            (" indices…", neu),
        )
    ) as status:
        for i, (index_name, info) in enumerate(batched_dict.items(), 1):
            status.update(
                Text.assemble(
                    ("⠙ ", prim),
                    ("Checking [", neu),
                    (f"{i}", sec),
                    (f"/{total_indices}]: ", neu),
                    (index_name, sec),
                )
            )
            location = info["location"]
            port = info["port"]
            is_frozen = fetch_elastic_frozen_data(
                location,
                index_name,
                port,
                config_manager,
                password_manager,
                gbl_password,
                cmd_password,
            )
            results[index_name] = {
                "location": location,
                "port": port,
                "frozen": is_frozen,
            }

    return results


def test_connection(
    location,
    port,
    config_manager,
    password_manager,
    gbl_password,
    cmd_password,
    ui: Optional[UnfreezeUI] = None,
):
    """
    Test connection to Elasticsearch cluster before attempting operations.
    """
    try:
        server_config = get_server_config(location, config_manager)
        hostname = server_config.get("hostname")
        hostname2 = server_config.get("hostname2")
        use_ssl = server_config.get("use_ssl", False)
        verify_certs = server_config.get("verify_certs", True)

        username = config_manager._resolve_username(server_config) or "kibana_system"
        password = get_password_for_server(
            server_config, password_manager, gbl_password, cmd_password, username
        )

        # Build connection URL
        protocol = "https" if use_ssl else "http"
        es_url = f"{protocol}://{hostname}:{port}"

        # Create Elasticsearch client with shorter timeout for testing
        if server_config.get("elastic_authentication", False) and password:
            es = Elasticsearch(
                [es_url],
                http_auth=(username, password),
                verify_certs=verify_certs,
                timeout=10,
                max_retries=1,
                retry_on_timeout=False,
            )
        else:
            es = Elasticsearch(
                [es_url],
                verify_certs=verify_certs,
                timeout=10,
                max_retries=1,
                retry_on_timeout=False,
            )

        # Test primary connection
        if es.ping():
            return es, hostname

        # Try backup hostname if available
        if hostname2:
            es_url2 = f"{protocol}://{hostname2}:{port}"
            if server_config.get("elastic_authentication", False) and password:
                es2 = Elasticsearch(
                    [es_url2],
                    http_auth=(username, password),
                    verify_certs=verify_certs,
                    timeout=10,
                    max_retries=1,
                    retry_on_timeout=False,
                )
            else:
                es2 = Elasticsearch(
                    [es_url2],
                    verify_certs=verify_certs,
                    timeout=10,
                    max_retries=1,
                    retry_on_timeout=False,
                )

            if es2.ping():
                return es2, hostname2

        return None, None

    except Exception as e:
        msg = f"Connection test failed for {location}:{port} - {str(e)}"
        if ui:
            ui.console.print(
                Text(msg, style=ui.style_system.get_semantic_style("error"))
            )
        else:
            print(f"[red]{msg}[/red]")
        return None, None


def action_unFreezeIndice(
    location,
    index_name,
    port,
    config_manager,
    password_manager,
    gbl_password,
    cmd_password,
    ui: Optional[UnfreezeUI] = None,
):
    """
    Unfreeze a specific index using Elasticsearch client for consistency.
    Returns a tuple (success: bool, message: str, hostname: str)
    """
    try:
        # Test connection first
        es, active_hostname = test_connection(
            location,
            port,
            config_manager,
            password_manager,
            gbl_password,
            cmd_password,
            ui,
        )

        if not es:
            return False, f"No working connection found for {location}:{port}", ""

        # Unfreeze the index using Elasticsearch client
        try:
            response = es.indices.unfreeze(index=index_name, request_timeout=60)
            # Check if the response indicates success
            if response.get("acknowledged", False):
                return (
                    True,
                    f"Successfully unfroze on {active_hostname}",
                    active_hostname,
                )
            else:
                return (
                    False,
                    f"Unfreeze not acknowledged by server (response: {response})",
                    active_hostname,
                )
        except Exception as e:
            return (
                False,
                f"Error unfreezing on {active_hostname}:{port}: {str(e)}",
                active_hostname,
            )

    except Exception as e:
        return False, f"Error unfreezing {index_name}: {str(e)}", ""


def unFreezeIndices(
    frozen_indices,
    config_manager,
    password_manager,
    gbl_password,
    cmd_password,
    ui: UnfreezeUI,
):
    """
    Unfreeze multiple indices with clean output formatting.
    """
    success_count = 0
    total_count = len(frozen_indices)
    ss = ui.style_system
    ok = ss.get_semantic_style("success")
    bad = ss.get_semantic_style("error")
    warn = ss.get_semantic_style("warning")
    info = ss.get_semantic_style("info")
    prim = ss.get_semantic_style("primary")

    # First, validate connections for all target hosts
    ui.console.print(
        Text(
            "Validating connections before unfreezing…",
            style=info,
        )
    )
    connection_status = {}
    for index_name, info in frozen_indices.items():
        location = info["location"]
        port = info["port"]
        conn_key = f"{location}:{port}"

        if conn_key not in connection_status:
            es, active_hostname = test_connection(
                location,
                port,
                config_manager,
                password_manager,
                gbl_password,
                cmd_password,
                ui,
            )
            connection_status[conn_key] = {
                "es": es,
                "hostname": active_hostname,
                "working": es is not None,
            }
            if es:
                ui.console.print(
                    Text.assemble(
                        ("✓ ", ok),
                        (f"Connection validated: {conn_key} → {active_hostname}", ok),
                    )
                )
            else:
                ui.console.print(
                    Text.assemble(
                        ("✗ ", bad),
                        (f"Connection failed: {conn_key}", bad),
                    )
                )

    ui.console.print()
    ui.console.print(
        Text("Starting unfreezing process…", style=prim),
    )

    # Import progress bar if available
    try:
        from rich.progress import (
            Progress,
            SpinnerColumn,
            TextColumn,
            BarColumn,
            TaskProgressColumn,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=ui.console,
        ) as progress:
            task = progress.add_task(f"Unfreezing indices", total=total_count)

            for i, (index_name, info) in enumerate(frozen_indices.items(), 1):
                location = info["location"]
                port = info["port"]
                conn_key = f"{location}:{port}"

                # Update progress description
                progress.update(
                    task,
                    description=f"Processing {index_name[:50]}{'...' if len(index_name) > 50 else ''}",
                )

                # Skip if connection is known to be bad
                if not connection_status[conn_key]["working"]:
                    ui.console.print(
                        Text.assemble(
                            ("⚠  ", warn),
                            (f"[{i:2d}/{total_count}] ", warn),
                            ("Skipping ", warn),
                            (index_name, bad),
                            (f": No connection to {conn_key}", bad),
                        )
                    )
                    progress.advance(task)
                    continue

                # Attempt to unfreeze
                success, message, hostname = action_unFreezeIndice(
                    info["location"],
                    index_name,
                    info["port"],
                    config_manager,
                    password_manager,
                    gbl_password,
                    cmd_password,
                    ui,
                )

                if success:
                    success_count += 1
                    ui.console.print(
                        Text.assemble(
                            ("✓  ", ok),
                            (f"[{i:2d}/{total_count}] ", ok),
                            (index_name, ok),
                            (" → ", ok),
                            (message, ok),
                        )
                    )
                else:
                    ui.console.print(
                        Text.assemble(
                            ("✗  ", bad),
                            (f"[{i:2d}/{total_count}] ", bad),
                            (index_name, bad),
                            (" → ", bad),
                            (message, bad),
                        )
                    )

                progress.advance(task)

    except ImportError:
        # Fallback to simple progress without progress bar
        ui.console.print()
        for i, (index_name, info) in enumerate(frozen_indices.items(), 1):
            location = info["location"]
            port = info["port"]
            conn_key = f"{location}:{port}"

            # Skip if connection is known to be bad
            if not connection_status[conn_key]["working"]:
                ui.console.print(
                    Text.assemble(
                        ("⚠  ", warn),
                        (f"[{i:2d}/{total_count}] ", warn),
                        ("Skipping ", warn),
                        (index_name, bad),
                        (f": No connection to {conn_key}", bad),
                    )
                )
                continue

            # Attempt to unfreeze
            success, message, hostname = action_unFreezeIndice(
                info["location"],
                index_name,
                info["port"],
                config_manager,
                password_manager,
                gbl_password,
                cmd_password,
                ui,
            )

            if success:
                success_count += 1
                ui.console.print(
                    Text.assemble(
                        ("✓  ", ok),
                        (f"[{i:2d}/{total_count}] ", ok),
                        (index_name, ok),
                        (" → ", ok),
                        (message, ok),
                    )
                )
            else:
                ui.console.print(
                    Text.assemble(
                        ("✗  ", bad),
                        (f"[{i:2d}/{total_count}] ", bad),
                        (index_name, bad),
                        (" → ", bad),
                        (message, bad),
                    )
                )

    ui.console.print()
    return success_count, total_count


def create_table(
    title: Optional[str],
    data_dict: dict,
    style_system: StyleSystem,
) -> Table:
    """
    Create a rich table for display using themes.yml table + semantic styles.
    If title is None, the table has no title (e.g. when wrapped in a Panel).
    """
    tm = style_system.theme_manager
    table_title = None
    if title:
        table_title = Text(
            title,
            style=tm.get_themed_style("panel_styles", "title", "bold white"),
        )
    table = Table(
        title=table_title,
        show_header=True,
        box=style_system.get_table_box(),
        expand=True,
        header_style=tm.get_themed_style("table_styles", "header_style", "bold white"),
        border_style=tm.get_themed_style("table_styles", "border_style", "white"),
    )
    style_system.add_themed_column(table, "Index Name", "name", overflow="fold")
    style_system.add_themed_column(table, "Location", "status")
    style_system.add_themed_column(table, "Port", "count", justify="center")
    style_system.add_themed_column(table, "Status", "status", justify="center")

    frozen_cell = tm.get_themed_style(
        "table_styles", "row_styles.frozen", style_system.get_semantic_style("primary")
    )
    normal_cell = style_system.get_semantic_style("success")

    for row_idx, (index_name, info) in enumerate(data_dict.items()):
        status = "FROZEN" if info.get("frozen", False) else "NORMAL"
        stat_style = frozen_cell if status == "FROZEN" else normal_cell
        zebra = style_system.get_zebra_style(row_idx)
        table.add_row(
            index_name,
            info.get("location", "unknown"),
            str(info.get("port", "unknown")),
            Text(status, style=stat_style),
            style=zebra,
        )

    return table


def wrap_indices_results_panel(
    ui: UnfreezeUI,
    table: Table,
    panel_heading: str,
    subtitle: str,
) -> Panel:
    """
    Same panel chrome as the opening UNFREEZE INDEX banner (border + title + subtitle).
    """
    tm = ui.theme_manager
    border = tm.get_themed_style("table_styles", "border_style", "bright_magenta")
    title_st = tm.get_themed_style("panel_styles", "title", "bold cyan")
    sub_st = tm.get_themed_style("panel_styles", "subtitle", "dim")
    return Panel(
        table,
        title=Text(panel_heading, style=title_st),
        subtitle=Text(subtitle, style=sub_st),
        border_style=border,
        padding=(1, 2),
        expand=True,
    )


def displayResults(frozen_status_dict: dict, ui: UnfreezeUI):
    """
    Display results in formatted tables.
    """
    frozen_indices = {
        k: v for k, v in frozen_status_dict.items() if v.get("frozen", False)
    }
    normal_indices = {
        k: v for k, v in frozen_status_dict.items() if not v.get("frozen", False)
    }

    if frozen_indices:
        fn = len(frozen_indices)
        f_idx = "indices" if fn != 1 else "index"
        frozen_subtitle = (
            f"{fn} matching {f_idx} · frozen (will unfreeze if you confirm)"
        )
        frozen_table = create_table(None, frozen_indices, ui.style_system)
        ui.console.print(
            wrap_indices_results_panel(
                ui,
                frozen_table,
                "FROZEN INDICES",
                frozen_subtitle,
            )
        )
        ui.console.print()

    if normal_indices:
        n = len(normal_indices)
        idx_lbl = "indices" if n != 1 else "index"
        subtitle = f"{n} matching {idx_lbl} · already unfrozen (no action needed)"
        normal_table = create_table(None, normal_indices, ui.style_system)
        ui.console.print(
            wrap_indices_results_panel(
                ui,
                normal_table,
                "NORMAL INDICES",
                subtitle,
            )
        )
        ui.console.print()

    return len(frozen_indices), len(normal_indices)


def tabData(data_dict, col_names):
    """
    Format data for tabular display.
    """
    table_data = []
    for key, value in data_dict.items():
        row = [key]
        for col in col_names[1:]:  # Skip first column (key)
            row.append(str(value.get(col.lower().replace(" ", "_"), "N/A")))
        table_data.append(row)
    return table_data


def validateProceed(ui: UnfreezeUI) -> bool:
    """
    Ask user for confirmation to proceed.
    """
    prompt_style = ui.style_system.get_semantic_style("warning")
    response = ui.console.input(
        Text("Do you want to proceed with unfreezing? (y/n): ", style=prompt_style)
    )
    return response.lower() in ["y", "yes"]


def status_bar_update(ui: UnfreezeUI, message: str) -> None:
    """
    Print status update message using theme info accent.
    """
    info = ui.style_system.get_semantic_style("info")
    ui.console.print(Text.assemble(("▸ ", info), Text.from_markup(f" {message}")))


class UnfreezeArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that renders argparse errors with the same Rich theme as the script."""

    def __init__(self, ui: UnfreezeUI, *args, **kwargs):
        self._ui = ui
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> None:
        ss = self._ui.style_system
        console = self._ui.console
        err_st = ss.get_semantic_style("error")
        neu = ss.get_semantic_style("neutral")
        info = ss.get_semantic_style("info")
        sec = ss.get_semantic_style("secondary")
        prim = ss.get_semantic_style("primary")

        headline = Text.assemble(("⛔ ", err_st), ("CLI ERROR", err_st))
        detail = Text(message, style=err_st)

        buf = StringIO()
        self.print_usage(buf)
        usage_line = buf.getvalue().rstrip()
        usage_block = Syntax(
            usage_line,
            lexer="text",
            word_wrap=True,
            theme="monokai",
            background_color="default",
        )

        hint = Text.assemble(
            ("Required: ", neu),
            ("-l/--locations", sec),
            (" (clusters) and ", neu),
            ("-c/--component", sec),
            (" (index name parts). ", neu),
            ("Try ", neu),
            ("--help", prim),
            (" for every flag.", neu),
        )

        body = Group(
            Align.center(headline),
            Text(""),
            Align.center(detail),
            Text(""),
            Text("usage", style=info),
            usage_block,
            Text(""),
            hint,
        )
        console.print()
        console.print(ss.create_error_panel(body, title="Unfreeze index", icon="⚡"))
        console.print()
        sys.exit(2)


def extract_and_format_date(filename):
    """
    Extract date from filename and format it.
    """
    # Look for date pattern YYYY.MM.DD
    date_pattern = r"(\d{4})\.(\d{2})\.(\d{2})"
    match = re.search(date_pattern, filename)

    if match:
        return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"

    return None


def print_matches_table(matches, title):
    """
    Print matches in a formatted table.
    """
    console = Console()
    table = Table(title=title, show_header=True)
    table.add_column("Index Name")
    table.add_column("Location")
    table.add_column("Port")

    for match in matches:
        table.add_row(
            match.get("index", ""),
            match.get("location", ""),
            str(match.get("port", "")),
        )

    console.print(table)


def show_message_box(message, style="info"):
    """
    Show a message in a box.
    """
    console = Console()
    console.print(Panel(message, style=style))


def returnOldestDates(indices_list, patterns):
    """
    Return the oldest dates for each pattern.
    """
    oldest_dates = {}

    for pattern in patterns:
        pattern_indices = [idx for idx in indices_list if pattern in idx]
        dates = []

        for idx in pattern_indices:
            date_str = extract_and_format_date(idx)
            if date_str:
                try:
                    date_obj = datetime.datetime.strptime(date_str, "%Y.%m.%d")
                    dates.append(date_obj)
                except ValueError:
                    continue

        if dates:
            oldest_date = min(dates)
            oldest_dates[pattern] = oldest_date.strftime("%Y.%m.%d")

    return oldest_dates


# Main Function starts here
if __name__ == "__main__":
    # Suppress Elasticsearch and urllib3 warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")
    warnings.filterwarnings("ignore", message=".*Elasticsearch.*")
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Initialize configuration and password managers
    try:
        script_directory = os.path.dirname(os.path.abspath(__file__))
        config_manager = make_configuration_manager(script_directory)
        password_manager = PasswordManager()
    except Exception as e:
        print(f"[red]Error initializing configuration: {str(e)}[/red]")
        sys.exit(1)

    console = Console()
    ui = build_unfreeze_ui(console, config_manager)
    today_date = datetime.datetime.today().strftime("%Y-%m-%d")
    print_unfreeze_banner(ui, today_date)
    status_bar_update(
        ui,
        f"UNFREEZE Index Script [white](v{VERSION}), Today: {today_date}[/white]",
    )

    # Parser Stuff
    parser = UnfreezeArgumentParser(
        ui, description="Unfreeze Elasticsearch indices"
    )
    # Locations(split by ,) where indexes need to be opened
    parser.add_argument(
        "-l",
        "--locations",
        required=True,
        help="Comma-separated list of locations (e.g., iad41,sjc01)",
    )
    parser.add_argument(
        "-d", "--date", required=False, help="Specific date (YYYY.mm.dd)"
    )
    parser.add_argument("-s", "--start", help="Start Date (YYYY.mm.dd)")
    parser.add_argument("-e", "--end", help="End Date (YYYY.mm.dd)")
    parser.add_argument(
        "-c",
        "--component",
        required=True,
        help="Comma-separated list of components to search for",
    )
    parser.add_argument(
        "-p",
        "--password",
        help="Prompt for password",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--dry-run",
        help="Show what would be unfrozen without actually doing it",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--yes",
        help="Automatically answer yes to confirmation prompt",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()

    locations = [loc.strip() for loc in args.locations.split(",")]
    dt = args.date
    comp = [c.strip() for c in args.component.split(",")]
    indx2openList = []
    prompt_password = args.password
    gbl_password = False
    cmd_password = None

    # Calculate Date to show
    if args.date is not None:
        args.start = args.date
    if args.end is None:
        # Now Set End to Start if not provided
        args.end = args.start

    # Parse start and end dates into datetime objects using custom date format
    start_date = datetime.datetime.strptime(args.start, "%Y.%m.%d")
    end_date = datetime.datetime.strptime(args.end, "%Y.%m.%d")
    # Generate date range using start and end dates
    date_range = [
        start_date + datetime.timedelta(days=x)
        for x in range((end_date - start_date).days + 1)
    ]

    # Update Console with Information
    status_bar_update(
        ui,
        f"COMPONENT: [bold green]{comp}[/bold green], LOCATIONS: [bold green] {locations} [/bold green]",
    )
    status_bar_update(
        ui,
        f"DATES: Start [{start_date.strftime('%Y.%m.%d')}]   End [{end_date.strftime('%Y.%m.%d')}]",
    )

    if prompt_password:
        gbl_password = True
        cmd_password = getpass.getpass(prompt="Enter your Password: ")

    batched_final = defaultdict(dict)
    oldest_final = defaultdict(dict)

    time.sleep(1)

    ss = ui.style_system
    prim = ss.get_semantic_style("primary")
    sec = ss.get_semantic_style("secondary")
    neu = ss.get_semantic_style("neutral")

    # Process each location with individual spinners
    for location in locations:
        with ui.console.status(
            Text.assemble(
                ("⠋ ", prim),
                ("Collecting data from cluster: ", neu),
                (location, sec),
            )
        ) as status:
            try:
                # Verify server configuration exists
                server_config = get_server_config(location, config_manager)
                resolved_name = None
                for name, config in config_manager.servers_dict.items():
                    if config == server_config:
                        resolved_name = name
                        break

                # Update spinner status and print info
                status.update(
                    Text.assemble(
                        ("⠙ ", prim),
                        ("Connecting to cluster: ", neu),
                        (location, sec),
                    )
                )
                status_bar_update(
                    ui,
                    f"Found server configuration for: {location} -> {resolved_name}",
                )
            except ValueError as e:
                ui.console.print(Text(str(e), style=ss.get_semantic_style("error")))
                continue

            # Get Indices from all ports in parallel for faster execution
            status.update(
                Text.assemble(
                    ("⠸ ", prim),
                    ("Scanning ports for cluster: ", neu),
                    (location, sec),
                )
            )
            ports = [9201, 9202, 9203, 9200]
            get_indices_partial = partial(
                getIndices,
                location,
                config_manager=config_manager,
                password_manager=password_manager,
                gbl_password=gbl_password,
                cmd_password=cmd_password,
            )

            indices_results = []
            with ThreadPoolExecutor(
                max_workers=2
            ) as executor:  # Reduced workers to avoid overwhelming
                future_to_port = {
                    executor.submit(get_indices_partial, port=port): port
                    for port in ports
                }
                for future in as_completed(future_to_port):
                    port = future_to_port[future]
                    try:
                        result = future.result()
                        # Only append results that actually contain data
                        if location in result and result[location]:
                            indices_results.append(result)
                        else:
                            # Only show this if we want verbose debugging
                            pass
                    except Exception as exc:
                        ui.console.print(
                            Text(
                                f"Port {port} generated an exception: {exc}",
                                style=ss.get_semantic_style("error"),
                            )
                        )
                        # Don't append empty results that could interfere

            # Create new dictionary and append results from all ports
            status.update(
                Text.assemble(
                    ("⠼ ", prim),
                    ("Processing indices for cluster: ", neu),
                    (location, sec),
                )
            )
            merged_indices = {}
            for result in indices_results:
                if location in result and result[location]:
                    # Merge indices, keeping track of which port provided each index
                    for index_name, index_data in result[location].items():
                        if index_name not in merged_indices:
                            merged_indices[index_name] = index_data

            # Show total indices found (useful for troubleshooting)
            if len(merged_indices) == 0:
                ui.console.print(
                    Text(
                        f"Warning: No indices found across all ports for {location}",
                        style=ss.get_semantic_style("warning"),
                    )
                )

            # Look for matches of indices
            matching_indices = processResults(merged_indices, comp)
            unique_indices_patterns = uniquePatterns(matching_indices)

            # Get Oldest Dates for each pattern (so when no matches we can inform admin)
            oldest_indices = returnOldestDates(
                matching_indices, unique_indices_patterns
            )
            oldest_final.update(oldest_indices)

            # Loop through each unique pattern and get that match
            final_matching_indices = []

            # Now Loop over each date and append matches
            status.update(
                Text.assemble(
                    ("⠦ ", prim),
                    ("Matching indices for cluster: ", neu),
                    (location, sec),
                )
            )
            for current_date in date_range:
                current_date_fmt = current_date.strftime("%Y.%m.%d")
                # Loop over each match
                for match in unique_indices_patterns:
                    _matches = matchingIndices(matching_indices, match)
                    most_likely_match = find_closest_file(_matches, current_date_fmt)
                    # Only Append if there is something to append
                    if most_likely_match != None:
                        final_matching_indices.append(most_likely_match)

            # Convert to Set to remove duplicates
            final_matching_indices = list(set(final_matching_indices))

            # Only show debug info if no matches found
            if len(final_matching_indices) == 0:
                ui.console.print(
                    Text(
                        f"No matching indices found after date filtering for {location}",
                        style=ss.get_semantic_style("warning"),
                    )
                )

            """
            Create (batched_final) and append all indices so we can open those at the end.
            """
            if len(final_matching_indices) > 0:
                for indices in final_matching_indices:
                    if indices in merged_indices:
                        port = merged_indices[indices]["port"]
                        batched_final[indices] = {"location": location, "port": port}
                    else:
                        ui.console.print(
                            Text(
                                f"Warning: Index {indices} not found in merged_indices for {location}",
                                style=ss.get_semantic_style("error"),
                            )
                        )
            matches = len(final_matching_indices)

    # Show results for each location
    ui.console.print()
    for location in locations:
        location_matches = len(
            [k for k, v in batched_final.items() if v["location"] == location]
        )
        if location_matches > 0:
            status_bar_update(
                ui,
                f"Found {location_matches} matching indices for {location}",
            )

    # Check if we found any indices
    if not batched_final:
        ui.console.print(
            Text(
                "No matching indices found for the specified criteria.",
                style=ss.get_semantic_style("warning"),
            )
        )
        if oldest_final:
            ui.console.print(
                Text(
                    "Oldest available dates by pattern:",
                    style=ss.get_semantic_style("info"),
                )
            )
            for pattern, date in oldest_final.items():
                ui.console.print(
                    Text.assemble(
                        ("  ", neu),
                        (pattern, sec),
                        (": ", neu),
                        (date, prim),
                    )
                )
        sys.exit(0)

    # Get frozen status for all matching indices
    ui.console.print()
    frozen_status = get_frozenStatus(
        batched_final,
        config_manager,
        password_manager,
        gbl_password,
        cmd_password,
        ui,
    )

    ui.console.print()

    # Display results
    frozen_count, normal_count = displayResults(frozen_status, ui)

    if frozen_count == 0:
        print_no_frozen_celebration(ui, normal_count)
        sys.exit(0)

    ui.console.print(
        Text(
            f"Summary: {frozen_count} frozen indices, {normal_count} normal indices",
            style=ss.get_semantic_style("warning"),
        )
    )

    # Ask for confirmation to unfreeze (skip if dry-run)
    if args.dry_run:
        frozen_indices = {
            k: v for k, v in frozen_status.items() if v.get("frozen", False)
        }
        ui.console.print()
        ui.console.print(
            Text(
                f"DRY RUN: Would unfreeze {len(frozen_indices)} indices.",
                style=ss.get_semantic_style("warning"),
            )
        )
        for index_name, info in frozen_indices.items():
            ui.console.print(
                Text.assemble(
                    ("  - ", neu),
                    (index_name, sec),
                    (f" (port {info['port']})", neu),
                )
            )
    elif args.yes or validateProceed(ui):
        frozen_indices = {
            k: v for k, v in frozen_status.items() if v.get("frozen", False)
        }
        success_count, total_count = unFreezeIndices(
            frozen_indices,
            config_manager,
            password_manager,
            gbl_password,
            cmd_password,
            ui,
        )

        ui.console.print()
        ui.console.print(
            Text(
                f"Unfreezing completed: {success_count}/{total_count} indices processed successfully.",
                style=ss.get_semantic_style("success"),
            )
        )
    else:
        ui.console.print(
            Text("Operation cancelled by user.", style=ss.get_semantic_style("warning"))
        )
