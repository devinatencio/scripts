"""
Utility functions for escmd.

Common utility functions used across multiple handlers and commands.
"""

import os
import re
import sys


def get_script_dir():
    """
    Return the directory where the escmd binary (or script) lives.

    Under normal Python execution this is the directory containing escmd.py.
    Under Nuitka onefile builds, __file__ for sub-modules points to the temp
    extraction directory, so we use sys.argv[0] which always resolves to the
    real binary location.
    """
    # sys.argv[0] reliably points to the actual script/binary in both
    # normal Python and Nuitka onefile builds.
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def load_json_tolerant(path):
    """Load a JSON file, tolerating trailing commas before } or ]."""
    import json
    with open(path, "r") as f:
        text = f.read()
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return json.loads(text)

def convert_size_to_bytes(size_str):
    """
    Convert Elasticsearch size string to bytes for sorting and comparison.

    Args:
        size_str (str): Size string like '1.2gb', '500mb', '10kb', '1024b', etc.

    Returns:
        float: Size in bytes, or 0 if invalid/empty

    Examples:
        >>> convert_size_to_bytes('1.5gb')
        1610612736.0
        >>> convert_size_to_bytes('500mb')
        524288000.0
        >>> convert_size_to_bytes('10kb')
        10240.0
        >>> convert_size_to_bytes('-')
        0
        >>> convert_size_to_bytes('')
        0
    """
    if not size_str or size_str == '-' or size_str == 'null':
        return 0

    # Handle both 'store' field format and other size formats
    size_str = str(size_str).lower().strip()

    if not size_str or size_str == 'none':
        return 0

    try:
        if size_str.endswith('b'):
            if size_str.endswith('tb'):
                return float(size_str[:-2]) * 1024 * 1024 * 1024 * 1024
            elif size_str.endswith('gb'):
                return float(size_str[:-2]) * 1024 * 1024 * 1024
            elif size_str.endswith('mb'):
                return float(size_str[:-2]) * 1024 * 1024
            elif size_str.endswith('kb'):
                return float(size_str[:-2]) * 1024
            else:
                # Just 'b' - extract number before 'b'
                num_str = size_str[:-1]
                if num_str.replace('.', '').replace('-', '').isdigit():
                    return float(num_str)

        # Try to parse as a plain number
        if size_str.replace('.', '').replace('-', '').isdigit():
            return float(size_str)

    except (ValueError, IndexError):
        pass

    return 0


def get_shard_size_bytes(shard):
    """
    Get size in bytes from a shard dictionary, handling various field names.

    Args:
        shard (dict): Shard data from Elasticsearch API

    Returns:
        float: Size in bytes
    """
    # Try different possible field names for size
    size_str = (
        shard.get('store') or
        shard.get('size') or
        shard.get('store_size') or
        shard.get('disk.total') or
        '0b'
    )

    return convert_size_to_bytes(size_str)


def safe_sort_shards_by_size(shards_data, reverse=True):
    """
    Safely sort shards by size, handling missing or invalid size data.

    Args:
        shards_data (list): List of shard dictionaries
        reverse (bool): Sort in descending order if True

    Returns:
        list: Sorted list of shards
    """
    return sorted(shards_data, key=get_shard_size_bytes, reverse=reverse)


def format_bytes_human_readable(bytes_value):
    """
    Format bytes into human readable format.

    Args:
        bytes_value (float): Size in bytes

    Returns:
        str: Human readable size string
    """
    if bytes_value == 0:
        return '0b'

    for unit in ['b', 'kb', 'mb', 'gb', 'tb']:
        if bytes_value < 1024.0:
            if unit == 'b':
                return f"{int(bytes_value)}{unit}"
            else:
                return f"{bytes_value:.1f}{unit}"
        bytes_value /= 1024.0

    return f"{bytes_value:.1f}pb"


def validate_size_string(size_str):
    """
    Validate if a size string is in correct format.

    Args:
        size_str (str): Size string to validate

    Returns:
        bool: True if valid size format, False otherwise
    """
    if not size_str or size_str in ['-', 'null', 'none', None]:
        return False

    # Check if it's a valid size format
    size_str = str(size_str).lower().strip()

    # Valid formats: number + unit (b, kb, mb, gb, tb) or just number
    import re
    valid_pattern = r'^(\d+\.?\d*)(b|kb|mb|gb|tb)?$'

    if re.match(valid_pattern, size_str):
        return True

    return False
