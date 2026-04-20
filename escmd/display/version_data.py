"""
Version data collection module for ESCMD.

This module handles all business logic for collecting version and system
information, separating data gathering from presentation logic.
"""

import os
import sys
import platform
from datetime import datetime

# Ensure the escmd root is on sys.path so version.py is importable from this sub-package
_parent_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Central version — only version.py needs updating to change across all tools
try:
    from version import VERSION as _ESCMD_VERSION, DATE as _ESCMD_DATE, HASH as _ESCMD_HASH
except ImportError:
    _ESCMD_VERSION = "3.8.4"
    _ESCMD_DATE = "04/04/2026"
    _ESCMD_HASH = "unknown"


class VersionDataCollector:
    """Handles collection of version and system information."""

    def __init__(self):
        """Initialize the version data collector."""
        pass

    def collect_version_data(self, version=None, date=None):
        """
        Collect all version-related data for display.

        Args:
            version: Optional version override
            date: Optional date override

        Returns:
            Dictionary containing all version information
        """
        # Use central version.py values when not explicitly provided
        if not version or not date:
            version = version or _ESCMD_VERSION
            date = date or _ESCMD_DATE

        return {
            "version": version,
            "hash": _ESCMD_HASH,
            "date": date,
            "tool_name": "ESCMD",
            "full_name": "Elasticsearch Terminal (ESTERM)",
            "purpose": "Advanced Elasticsearch CLI Management & Monitoring",
            "team": "Monitoring Team US",
            "python_version": sys.version.split()[0],
            "platform": f"{platform.system()} {platform.machine()}",
            "system_info": self._collect_system_info(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _read_version_from_esterm(self):
        """
        Returns version info from the central version.py module.
        Kept for backward compatibility; prefer _ESCMD_VERSION/_ESCMD_DATE directly.
        """
        return _ESCMD_VERSION, _ESCMD_DATE

    def _collect_system_info(self):
        """
        Collect system information including performance metrics.

        Returns:
            Dictionary containing system information
        """
        system_info = {
            "python_executable": sys.executable,
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Try to collect performance metrics with psutil
        try:
            import psutil

            system_info.update(
                {
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "memory_available_gb": psutil.virtual_memory().available
                    // (1024**3),
                    "disk_percent": psutil.disk_usage("/").percent,
                    "disk_free_gb": psutil.disk_usage("/").free // (1024**3),
                    "psutil_available": True,
                }
            )
        except ImportError:
            system_info["psutil_available"] = False
        except Exception as e:
            system_info["psutil_available"] = False
            system_info["psutil_error"] = str(e)

        return system_info

    def get_script_location(self):
        """
        Get the current script location information.

        Returns:
            Dictionary containing script location details
        """
        from utils import get_script_dir

        script_path = get_script_dir()

        return {
            "script_directory": str(script_path),
            "current_working_directory": os.getcwd(),
            "script_file": sys.argv[0],
        }

    def collect_command_statistics(self):
        """
        Collect command statistics (could be enhanced to dynamically discover commands).

        Returns:
            Dictionary containing command statistics
        """
        # This could be enhanced to dynamically discover commands
        # For now, using static data matching the current implementation
        categories = {
            "🏥 Health & Monitoring": {
                "count": 8,
                "commands": "health, nodes, ping, cluster-check",
            },
            "📑 Index Management": {
                "count": 12,
                "commands": "indices, freeze, set-replicas, templates",
            },
            "💾 Storage & Shards": {
                "count": 6,
                "commands": "storage, shards, allocation, exclude",
            },
            "🔄 Lifecycle (ILM)": {
                "count": 15,
                "commands": "ilm, rollover, datastreams, policies",
            },
            "📸 Backup & Snapshots": {
                "count": 5,
                "commands": "snapshots, restore, repositories",
            },
            "🔩 Settings & Config": {
                "count": 4,
                "commands": "cluster-settings, set, show-settings",
            },
            "🔧 Utilities & Tools": {
                "count": 18,
                "commands": "help, version, themes, locations",
            },
        }

        total_commands = sum(info["count"] for info in categories.values())

        return {"categories": categories, "total_commands": total_commands}

    def get_capabilities_info(self):
        """
        Get information about tool capabilities.

        Returns:
            Dictionary containing capability descriptions
        """
        return {
            "🎨 Rich UI Framework": "Advanced terminal formatting & themes",
            "🔐 Security Features": "SSL/TLS, authentication, secure configs",
            "📊 Data Visualization": "Tables, JSON syntax highlighting, panels",
            "⚡ Performance Optimized": "Efficient API calls, caching, streaming",
            "🔍 Advanced Filtering": "Complex queries, pattern matching",
            "🔐 Error Handling": "Comprehensive validation & recovery",
            "📋 Export Formats": "JSON, CSV, table formats",
            "🎯 Interactive Mode": "ESterm terminal with persistent sessions",
        }

    def get_performance_features(self):
        """
        Get information about performance features.

        Returns:
            List of performance feature descriptions
        """
        return [
            "Multi-threading, connection pooling, caching",
            "Bulk operations, batched requests, streaming",
        ]
