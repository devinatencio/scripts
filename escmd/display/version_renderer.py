"""
Version information renderer for ESCMD.

This module handles all display logic for version information, extracting
the presentation layer from command handlers for better separation of concerns.
"""

import sys
import platform
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text


class VersionRenderer:
    """Handles rendering of version information with rich formatting."""

    def __init__(self, console=None, theme_manager=None):
        """
        Initialize the version renderer.

        Args:
            console: Rich Console instance (creates new one if None)
            theme_manager: Theme manager for styling (optional)
        """
        self.console = console or Console()
        self.theme_manager = theme_manager

    def render_version_info(self, version_data):
        """
        Render complete version information display.

        Args:
            version_data: Dictionary containing version information
                - version: Version string
                - date: Release date
                - tool_name: Tool name (defaults to ESTERM)
        """
        self.console.print()
        self._render_main_version_panel(version_data)
        self.console.print()
        # self._render_command_stats_panel()
        # self.console.print()
        # self._render_capabilities_panel()
        # self.console.print()
        self._render_performance_panel()
        self.console.print()
        self._render_footer()

    def _render_main_version_panel(self, version_data):
        """Render the main version information panel."""
        version = version_data.get("version", "3.7.4")
        date = version_data.get("date", "03/25/2026")
        tool_name = version_data.get("tool_name", "ESTERM")

        # Main version header
        version_header = Text()
        version_header.append("⚡ ", style="bold yellow")
        version_header.append(tool_name, style="bold cyan")
        version_header.append(" v", style="dim")
        version_header.append(version, style="bold white")

        # Create main version info table with better styling
        version_table = Table.grid(padding=(0, 4))
        version_table.add_column(style="bold blue", no_wrap=True, min_width=15)
        version_table.add_column(style="white", no_wrap=False)

        version_table.add_row("🚀 Tool:", "Elasticsearch Terminal (ESTERM)")
        version_table.add_row("📦 Version:", f"[bold green]{version}[/bold green]")
        version_table.add_row("📅 Released:", f"[bold cyan]{date}[/bold cyan]")
        version_table.add_row(
            "🎯 Purpose:", "Advanced Elasticsearch CLI Management & Monitoring"
        )
        version_table.add_row("👥 Team:", "Monitoring Team US")
        version_table.add_row("🐍 Python:", f"{sys.version.split()[0]}")
        version_table.add_row(
            "💻 Platform:", f"{platform.system()} {platform.machine()}"
        )

        # Create elegant main panel
        main_panel = Panel(
            Align.center(version_table),
            title=version_header,
            subtitle="[dim]Interactive Elasticsearch Command Line Interface[/dim]",
            border_style="cyan",
            padding=(2, 3),
        )

        self.console.print(main_panel)

    def _render_command_stats_panel(self):
        """Render command statistics panel."""
        stats_table = self._generate_enhanced_command_stats_table()
        stats_panel = Panel(
            stats_table,
            title="[bold green]📊 Command Arsenal[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(stats_panel)

    def _render_capabilities_panel(self):
        """Render core capabilities panel."""
        capabilities_table = self._generate_enhanced_capabilities_table()
        capabilities_panel = Panel(
            capabilities_table,
            title="[bold magenta]🧰 Core Capabilities[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
        self.console.print(capabilities_panel)

    def _render_performance_panel(self):
        """Render performance and system information panel."""
        perf_table = self._generate_performance_info_table()
        perf_panel = Panel(
            Align.center(perf_table),
            title="[bold yellow]⚡ Performance & System[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
        self.console.print(perf_panel)

    def _render_footer(self):
        """Render helpful footer with quick start information."""
        footer_text = Text()
        footer_text.append("💡 ", style="bold yellow")
        footer_text.append("Quick Start: ", style="bold")
        footer_text.append("Run ", style="dim")
        footer_text.append("./esterm", style="bold cyan")
        footer_text.append(" for interactive mode or ", style="dim")
        footer_text.append("./escmd.py help", style="bold cyan")
        footer_text.append(" for command reference", style="dim")

        footer_panel = Panel(
            Align.center(footer_text), border_style="dim", padding=(1, 2)
        )
        self.console.print(footer_panel)

    def _generate_enhanced_command_stats_table(self):
        """Generate enhanced command statistics table with better presentation."""
        stats_table = Table(show_header=True, header_style="bold green")
        stats_table.add_column("📂 Category", style="bold cyan", min_width=18)
        stats_table.add_column(
            "📊 Count", justify="center", style="bold white", min_width=8
        )
        stats_table.add_column("🔍 Key Commands", style="dim", no_wrap=False)

        # Enhanced categories with more detail
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

        total_commands = 0
        for category, info in categories.items():
            stats_table.add_row(category, str(info["count"]), info["commands"])
            total_commands += info["count"]

        # Add total row with separator
        stats_table.add_row("", "", "", style="dim")
        stats_table.add_row(
            "[bold]📋 TOTAL COMMANDS",
            f"[bold green]{total_commands}[/bold green]",
            "[italic]Complete Elasticsearch management suite[/italic]",
        )

        return stats_table

    def _generate_enhanced_capabilities_table(self):
        """Generate enhanced capabilities table with modern styling."""
        capabilities_table = Table.grid(padding=(0, 3))
        capabilities_table.add_column(style="bold magenta", min_width=25)
        capabilities_table.add_column(style="white")

        capabilities_table.add_row(
            "🎨 Rich UI Framework:", "Advanced terminal formatting & themes"
        )
        capabilities_table.add_row(
            "🔐 Security Features:", "SSL/TLS, authentication, secure configs"
        )
        capabilities_table.add_row(
            "📊 Data Visualization:", "Tables, JSON syntax highlighting, panels"
        )
        capabilities_table.add_row(
            "⚡ Performance Optimized:", "Efficient API calls, caching, streaming"
        )
        capabilities_table.add_row(
            "🔍 Advanced Filtering:", "Complex queries, pattern matching"
        )
        capabilities_table.add_row(
            "🔐 Error Handling:", "Comprehensive validation & recovery"
        )
        capabilities_table.add_row("📋 Export Formats:", "JSON, CSV, table formats")
        capabilities_table.add_row(
            "🎯 Interactive Mode:", "ESterm terminal with persistent sessions"
        )

        return capabilities_table

    def _generate_performance_info_table(self):
        """Generate performance and system information table."""
        perf_table = Table.grid(padding=(0, 3))
        perf_table.add_column(style="bold yellow", min_width=20)
        perf_table.add_column(style="white")

        # Try to import psutil for system metrics
        try:
            import psutil

            # System metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            perf_table.add_row("💻 CPU Usage:", f"{cpu_percent}%")
            perf_table.add_row(
                "🧠 Memory:",
                f"{memory.percent}% used ({memory.available // (1024**3)}GB available)",
            )
            perf_table.add_row(
                "💾 Disk Space:",
                f"{disk.percent}% used ({disk.free // (1024**3)}GB free)",
            )
            perf_table.add_row(
                "🕐 System Time:", f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        except ImportError:
            # Fallback if psutil unavailable
            perf_table.add_row(
                "📊 System Metrics:",
                "[dim]Install psutil for detailed system info[/dim]",
            )
            perf_table.add_row(
                "🕐 Current Time:", f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception:
            # Fallback for any other psutil errors
            perf_table.add_row(
                "📊 System Status:", "System monitoring temporarily unavailable"
            )
            perf_table.add_row(
                "🕐 Current Time:", f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        perf_table.add_row(
            "🚀 Optimization:", "Multi-threading, connection pooling, caching"
        )
        perf_table.add_row(
            "🔄 API Efficiency:", "Bulk operations, batched requests, streaming"
        )

        return perf_table

    def render_simple_version(self, version_data):
        """
        Render a simplified version display for quick reference.

        Args:
            version_data: Dictionary containing version information
        """
        version = version_data.get("version", "3.7.4")
        tool_name = version_data.get("tool_name", "ESTERM")

        version_text = Text()
        version_text.append(f"{tool_name} ", style="bold cyan")
        version_text.append(f"v{version}", style="bold green")

        self.console.print(version_text)

    def render_json_version(self, version_data):
        """
        Render version information in JSON format.

        Args:
            version_data: Dictionary containing version information
        """
        import json

        output_data = {
            "tool": version_data.get("tool_name", "ESTERM"),
            "version": version_data.get("version", "3.7.4"),
            "release_date": version_data.get("date", "03/25/2026"),
            "python_version": sys.version.split()[0],
            "platform": f"{platform.system()} {platform.machine()}",
            "purpose": "Advanced Elasticsearch CLI Management & Monitoring",
        }

        self.console.print_json(json.dumps(output_data, indent=2))
