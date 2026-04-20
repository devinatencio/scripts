"""
config_loader.py - YAML configuration reading, validation, and defaults.

Reads server connection settings and retention policies from YAML files.
Provides fallback path searching, case-insensitive server selection,
required field validation, numeric field validation, and default value
population.
"""

import os
import re

import yaml


# Default values applied when settings are missing
DEFAULTS = {
    'elastic_default_timeout': 300,
    'elastic_restored_maxdays': 3,
    'default_retention_maxdays': 30,
    'elastic_restore_batch_size': 3,
    'elastic_max_shards_per_node': 1000,
    'elastic_restored_indice': 'rc_snapshots',
    'elastic_history_indice': 'rc_snapshots_history',
    'ilm_curator_delay': '6h',
}

# Fields that must be present in a server entry
_REQUIRED_FIELDS = ['hostname', 'port', 'repository']

# Fields that must be valid integers
_NUMERIC_FIELDS = [
    'port',
    'elastic_default_timeout',
    'elastic_restored_maxdays',
    'default_retention_maxdays',
    'elastic_restore_batch_size',
    'elastic_max_shards_per_node',
]


_DURATION_RE = re.compile(r'^(\d+)\s*([smhd])$', re.IGNORECASE)

_DURATION_MULTIPLIERS = {
    's': 1.0 / 3600,
    'm': 1.0 / 60,
    'h': 1.0,
    'd': 24.0,
}


def parse_duration_to_hours(value):
    # type: (object) -> float
    """Parse a duration string (or plain number) into hours.

    Supported suffixes (case-insensitive):
        s  - seconds   (e.g. ``"3600s"`` → 1.0)
        m  - minutes   (e.g. ``"30m"``   → 0.5)
        h  - hours     (e.g. ``"6h"``    → 6.0)
        d  - days      (e.g. ``"1d"``    → 24.0)

    A bare integer or float (no suffix) is treated as hours for
    backwards compatibility with the old ``ilm_curator_hours_delay``
    setting.

    Args:
        value: Duration string like ``"30m"`` or a numeric value.

    Returns:
        Duration expressed as a float in hours.

    Raises:
        ValueError: If the value cannot be parsed.
    """
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    # Bare number (no suffix) → treat as hours for backwards compat
    try:
        return float(text)
    except ValueError:
        pass

    match = _DURATION_RE.match(text)
    if not match:
        raise ValueError(
            "Invalid duration '%s'. Use a number with suffix s/m/h/d "
            "(e.g. '30m', '6h', '1d')." % value
        )

    amount = float(match.group(1))
    unit = match.group(2).lower()
    return amount * _DURATION_MULTIPLIERS[unit]


def find_config_file(filename, search_dirs):
    # type: (str, list) -> str
    """
    Search for a config file across multiple directories.

    Args:
        filename: Name of the config file to find.
        search_dirs: List of directory paths to search.

    Returns:
        Absolute path to the found file.

    Raises:
        FileNotFoundError: File not found in any search directory.
    """
    searched = []
    for d in search_dirs:
        path = os.path.join(d, filename)
        searched.append(os.path.abspath(path))
        if os.path.isfile(path):
            return os.path.abspath(path)

    raise FileNotFoundError(
        "Config file '%s' not found. Searched: %s" % (filename, ', '.join(searched))
    )


def load_server_config(config_file, server_name='DEFAULT'):
    # type: (str, str) -> dict
    """
    Load and validate server configuration from YAML.

    Reads the YAML file, selects the named server (case-insensitive),
    merges global settings with server-level overrides, validates required
    fields and numeric types, and fills in defaults for missing optional
    settings.

    Args:
        config_file: Path to elastic_servers.yml.
        server_name: Server name to select (case-insensitive).

    Returns:
        dict with keys: hostname, port, use_ssl, repository,
        elastic_authentication, elastic_username, elastic_password,
        elastic_default_timeout, elastic_restored_indice,
        elastic_history_indice, elastic_restored_maxdays,
        default_retention_maxdays, elastic_restore_batch_size,
        elastic_max_shards_per_node, and any extra settings from YAML.

    Raises:
        FileNotFoundError: Config file not found at path.
        ValueError: Missing required fields, invalid numeric values,
                    or server name not found.
    """
    if not os.path.isfile(config_file):
        raise FileNotFoundError(
            "Config file not found: %s" % os.path.abspath(config_file)
        )

    with open(config_file, 'r') as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        data = {}

    settings = data.get('settings', {}) or {}
    servers = data.get('servers', []) or []

    # Find server by name (case-insensitive)
    available_names = [s.get('name', '') for s in servers if isinstance(s, dict)]
    matched_server = None
    for s in servers:
        if not isinstance(s, dict):
            continue
        name = s.get('name', '')
        if name.lower() == server_name.lower():
            matched_server = s
            break

    if matched_server is None:
        raise ValueError(
            "Server '%s' not found. Available servers: %s"
            % (server_name, ', '.join(available_names))
        )

    # Build result: start with defaults, layer settings, then server overrides
    result = {}

    # Apply defaults first
    for key, value in DEFAULTS.items():
        result[key] = value

    # Apply global settings (overrides defaults)
    for key, value in settings.items():
        result[key] = value

    # Apply server-level fields (overrides settings)
    for key, value in matched_server.items():
        if key == 'name':
            continue
        result[key] = value

    # Validate required fields
    missing = [f for f in _REQUIRED_FIELDS if f not in result or result[f] is None]
    if missing:
        raise ValueError(
            "Missing required fields: %s" % ', '.join(missing)
        )

    # Validate numeric fields
    for field in _NUMERIC_FIELDS:
        if field not in result:
            continue
        val = result[field]
        if val is None:
            continue
        try:
            result[field] = int(val)
        except (TypeError, ValueError):
            raise ValueError(
                "Field '%s' must be a valid integer, got: %s" % (field, val)
            )

    # Validate and normalise duration fields
    if 'ilm_curator_delay' in result and result['ilm_curator_delay'] is not None:
        try:
            result['ilm_curator_delay'] = parse_duration_to_hours(
                result['ilm_curator_delay']
            )
        except ValueError:
            raise ValueError(
                "Field 'ilm_curator_delay' must be a valid duration "
                "(e.g. '30m', '6h', '1d'), got: %s" % result['ilm_curator_delay']
            )

    return result


def load_retention_config(retention_file):
    # type: (str) -> dict
    """
    Load retention policies from YAML.

    Args:
        retention_file: Path to elastic_retention.yml.

    Returns:
        dict mapping regex pattern strings to max_days integers.

    Raises:
        FileNotFoundError: Retention file not found.
    """
    if not os.path.isfile(retention_file):
        raise FileNotFoundError(
            "Retention config file not found: %s" % os.path.abspath(retention_file)
        )

    with open(retention_file, 'r') as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        return {}

    retention_list = data.get('retention', []) or []
    policies = {}
    for entry in retention_list:
        if not isinstance(entry, dict):
            continue
        pattern = entry.get('pattern')
        max_days = entry.get('max_days')
        if pattern is not None and max_days is not None:
            policies[pattern] = int(max_days)

    return policies
