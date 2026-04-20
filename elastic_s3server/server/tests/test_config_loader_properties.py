"""
Property-based tests for config_loader.py

Feature: server-v2-modernization, Property 1: Configuration loading round-trip
Validates: Requirements 2.1, 2.4, 2.5
"""

import os
import tempfile

import yaml
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from server.config_loader import load_server_config, DEFAULTS, _REQUIRED_FIELDS, _NUMERIC_FIELDS, parse_duration_to_hours

# Duration fields that get parsed to floats during loading
_DURATION_FIELDS = {'ilm_curator_delay'}


# --- Strategies ---

# Required fields for a valid server entry
hostname_st = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-."),
    min_size=1,
    max_size=50,
).filter(lambda s: s[0].isalnum())

port_st = st.integers(min_value=1, max_value=65535)

repository_st = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_-"),
    min_size=1,
    max_size=30,
)

server_name_st = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"),
    min_size=1,
    max_size=20,
)

# Optional settings that can appear in the config
optional_settings_st = st.fixed_dictionaries({}, optional={
    'elastic_default_timeout': st.integers(min_value=1, max_value=3600),
    'elastic_restored_maxdays': st.integers(min_value=1, max_value=365),
    'default_retention_maxdays': st.integers(min_value=1, max_value=365),
    'elastic_restore_batch_size': st.integers(min_value=1, max_value=100),
    'elastic_max_shards_per_node': st.integers(min_value=1, max_value=10000),
})


# Optional string settings
optional_string_settings_st = st.fixed_dictionaries({}, optional={
    'elastic_restored_indice': st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_"),
        min_size=1, max_size=30,
    ),
    'elastic_history_indice': st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_"),
        min_size=1, max_size=30,
    ),
})


def build_yaml_config(server_name, hostname, port, repository,
                      optional_numeric, optional_strings,
                      global_settings):
    """Build a valid YAML config dict for serialization."""
    server_entry = {
        'name': server_name,
        'hostname': hostname,
        'port': port,
        'repository': repository,
    }
    # Merge optional settings into the server entry
    server_entry.update(optional_numeric)
    server_entry.update(optional_strings)

    config = {
        'settings': global_settings,
        'servers': [server_entry],
    }
    return config


def write_yaml_to_tempfile(config_dict):
    """Serialize config dict to a temporary YAML file, return path."""
    fd, path = tempfile.mkstemp(suffix='.yml')
    try:
        with os.fdopen(fd, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
    except Exception:
        os.close(fd)
        raise
    return path


# --- Property Test ---

@given(
    server_name=server_name_st,
    hostname=hostname_st,
    port=port_st,
    repository=repository_st,
    optional_numeric=optional_settings_st,
    optional_strings=optional_string_settings_st,
    global_settings=optional_settings_st,
)
@settings(max_examples=200)
def test_config_round_trip(server_name, hostname, port, repository,
                           optional_numeric, optional_strings,
                           global_settings):
    """
    Property 1: Configuration loading round-trip

    For any valid server config with required fields and random subsets of
    optional settings, serializing to YAML and loading via load_server_config
    should produce a dict containing all original values with defaults filled
    in for omitted optional settings.

    **Validates: Requirements 2.1, 2.4, 2.5**
    """
    config_dict = build_yaml_config(
        server_name, hostname, port, repository,
        optional_numeric, optional_strings, global_settings,
    )

    path = write_yaml_to_tempfile(config_dict)
    try:
        result = load_server_config(path, server_name=server_name)
    finally:
        os.unlink(path)

    # Required fields must be present and match
    assert result['hostname'] == hostname
    assert result['port'] == port
    assert result['repository'] == repository

    # Server-level optional numeric settings override globals and defaults
    for key in optional_numeric:
        assert result[key] == optional_numeric[key], (
            "Server-level setting %s: expected %r, got %r"
            % (key, optional_numeric[key], result[key])
        )

    # Server-level optional string settings must be present
    for key in optional_strings:
        assert result[key] == optional_strings[key], (
            "Server-level string setting %s: expected %r, got %r"
            % (key, optional_strings[key], result[key])
        )

    # Global settings should appear if not overridden by server entry
    for key in global_settings:
        if key not in optional_numeric:
            assert result[key] == global_settings[key], (
                "Global setting %s: expected %r, got %r"
                % (key, global_settings[key], result[key])
            )

    # Defaults must be filled in for any key not provided at any level
    for key, default_val in DEFAULTS.items():
        if key not in optional_numeric and key not in optional_strings and key not in global_settings:
            if key in _DURATION_FIELDS:
                expected = parse_duration_to_hours(default_val)
            else:
                expected = default_val
            assert result[key] == expected, (
                "Default %s: expected %r, got %r"
                % (key, expected, result[key])
            )


# --- Property 2: Configuration validation rejects invalid configs ---
# Feature: server-v2-modernization, Property 2: Configuration validation rejects invalid configs


# Strategy: generate a valid base config, then remove at least one required field
required_fields_st = st.sampled_from(_REQUIRED_FIELDS)

# Non-integer strings for numeric field injection
non_integer_st = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz!@#$%^&*"),
    min_size=1,
    max_size=10,
).filter(lambda s: not s.lstrip('-').isdigit())

numeric_field_st = st.sampled_from(_NUMERIC_FIELDS)

# Unknown server name that won't collide with the real one
unknown_server_name_st = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
    min_size=1,
    max_size=20,
)


@given(
    server_name=server_name_st,
    hostname=hostname_st,
    port=port_st,
    repository=repository_st,
    fields_to_remove=st.lists(required_fields_st, min_size=1, max_size=3, unique=True),
)
@settings(max_examples=200)
def test_missing_required_fields_raises_valueerror(
    server_name, hostname, port, repository, fields_to_remove
):
    """
    Property 2a: Missing required fields cause ValueError.

    For any valid config with at least one required field removed,
    load_server_config must raise ValueError.

    **Validates: Requirements 2.3, 2.7**
    """
    server_entry = {
        'name': server_name,
        'hostname': hostname,
        'port': port,
        'repository': repository,
    }
    for field in fields_to_remove:
        server_entry.pop(field, None)

    config_dict = {
        'settings': {},
        'servers': [server_entry],
    }

    path = write_yaml_to_tempfile(config_dict)
    try:
        try:
            load_server_config(path, server_name=server_name)
            assert False, (
                "Expected ValueError for missing fields %s but no exception raised"
                % fields_to_remove
            )
        except ValueError:
            pass  # Expected
    finally:
        os.unlink(path)


@given(
    server_name=server_name_st,
    hostname=hostname_st,
    port=port_st,
    repository=repository_st,
    numeric_field=numeric_field_st,
    bad_value=non_integer_st,
)
@settings(max_examples=200)
def test_non_integer_numeric_fields_raises_valueerror(
    server_name, hostname, port, repository, numeric_field, bad_value
):
    """
    Property 2b: Non-integer numeric fields cause ValueError.

    For any valid config where a numeric field is set to a non-integer string,
    load_server_config must raise ValueError.

    **Validates: Requirements 2.3, 2.7**
    """
    server_entry = {
        'name': server_name,
        'hostname': hostname,
        'port': port,
        'repository': repository,
        numeric_field: bad_value,
    }

    config_dict = {
        'settings': {},
        'servers': [server_entry],
    }

    path = write_yaml_to_tempfile(config_dict)
    try:
        try:
            load_server_config(path, server_name=server_name)
            assert False, (
                "Expected ValueError for non-integer %s=%r but no exception raised"
                % (numeric_field, bad_value)
            )
        except ValueError:
            pass  # Expected
    finally:
        os.unlink(path)


@given(
    real_server_name=server_name_st,
    hostname=hostname_st,
    port=port_st,
    repository=repository_st,
    unknown_name=unknown_server_name_st,
)
@settings(max_examples=200)
def test_unknown_server_name_raises_valueerror_with_available_names(
    real_server_name, hostname, port, repository, unknown_name
):
    """
    Property 2c: Unknown server name causes ValueError listing available names.

    For any server name not present in the config, load_server_config must
    raise ValueError whose message contains the available server names.

    **Validates: Requirements 2.3, 2.7**
    """
    # Ensure the unknown name differs from the real name (case-insensitive)
    assume(unknown_name.lower() != real_server_name.lower())

    server_entry = {
        'name': real_server_name,
        'hostname': hostname,
        'port': port,
        'repository': repository,
    }

    config_dict = {
        'settings': {},
        'servers': [server_entry],
    }

    path = write_yaml_to_tempfile(config_dict)
    try:
        try:
            load_server_config(path, server_name=unknown_name)
            assert False, (
                "Expected ValueError for unknown server '%s' but no exception raised"
                % unknown_name
            )
        except ValueError as exc:
            msg = str(exc)
            assert real_server_name in msg, (
                "ValueError message should contain available server name '%s', got: %s"
                % (real_server_name, msg)
            )
    finally:
        os.unlink(path)


# --- Property 3: Case-insensitive server selection ---
# Feature: server-v2-modernization, Property 3: Case-insensitive server selection


def _random_case_transform(s, draw):
    """Apply a random case transformation to each character of a string."""
    result = []
    for ch in s:
        choice = draw(st.sampled_from(['upper', 'lower', 'keep']))
        if choice == 'upper':
            result.append(ch.upper())
        elif choice == 'lower':
            result.append(ch.lower())
        else:
            result.append(ch)
    return ''.join(result)


@st.composite
def case_variant_st(draw, name):
    """Generate a case variant of the given name."""
    return _random_case_transform(name, draw)


@st.composite
def server_config_with_case_variants(draw):
    """
    Generate a valid server config and multiple case variants of the server name.
    """
    server_name = draw(server_name_st)
    hostname = draw(hostname_st)
    port = draw(port_st)
    repository = draw(repository_st)
    optional_numeric = draw(optional_settings_st)
    optional_strings = draw(optional_string_settings_st)
    global_settings = draw(optional_settings_st)

    # Generate 3 case variants of the server name
    variants = []
    for _ in range(3):
        variants.append(_random_case_transform(server_name, draw))
    # Also include the canonical forms
    variants.append(server_name.upper())
    variants.append(server_name.lower())

    config_dict = build_yaml_config(
        server_name, hostname, port, repository,
        optional_numeric, optional_strings, global_settings,
    )

    return config_dict, server_name, variants


@given(data=st.data())
@settings(max_examples=200)
def test_case_insensitive_server_selection(data):
    """
    Property 3: Case-insensitive server selection

    For any server configuration containing a named server entry, selecting
    that server by any case variation of its name (upper, lower, mixed)
    should return the same server configuration as selecting by the original
    name.

    **Validates: Requirements 2.2**
    """
    bundle = data.draw(server_config_with_case_variants())
    config_dict, original_name, case_variants = bundle

    path = write_yaml_to_tempfile(config_dict)
    try:
        # Load with the original name as baseline
        baseline = load_server_config(path, server_name=original_name)

        # Load with each case variant and assert identical result
        for variant in case_variants:
            result = load_server_config(path, server_name=variant)
            assert result == baseline, (
                "Config mismatch for case variant '%s' vs original '%s':\n"
                "  baseline: %r\n  variant:  %r"
                % (variant, original_name, baseline, result)
            )
    finally:
        os.unlink(path)
