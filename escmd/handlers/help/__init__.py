"""
Help system package for escmd.

Provides modular help content management with theme support.
"""

from .help_registry import get_help_registry, get_help_for_topic, register_help_module
from .base_help_content import BaseHelpContent

__all__ = [
    'get_help_registry',
    'get_help_for_topic',
    'register_help_module',
    'BaseHelpContent'
]
