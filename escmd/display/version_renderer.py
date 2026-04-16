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
from rich.columns import Columns  # noqa: F401  kept for potential future use


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
        self.style_system = None
        if theme_manager:
            try:
                from display.style_system import StyleSystem
                self.style_system = StyleSystem(theme_manager)
            except ImportError:
                pass

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
        self._render_banner(version_data)
        self._render_main_version_panel(version_data)
        self.console.print()
        self._render_footer()

    def _border(self, fallback: str = "cyan") -> str:
        """Return the theme border style, falling back to the given value."""
        if self.theme_manager:
            return self.theme_manager.get_theme_styles().get("border_style", fallback)
        return fallback

    def _title_style(self, fallback: str = "bold white") -> str:
        """Return the theme panel title style."""
        if self.theme_manager:
            return self.theme_manager.get_themed_style("panel_styles", "title", fallback)
        return fallback

    def _sem(self, semantic: str, fallback: str = "white") -> str:
        """Return a semantic style from the style system."""
        if self.style_system:
            return self.style_system.get_semantic_style(semantic)
        return fallback

    def _render_banner(self, version_data):
        """Render gradient ASCII art banner using theme colors."""
        tool_name = version_data.get("tool_name", "ESTERM")
        letters = [
            " ███████╗███████╗████████╗███████╗██████╗ ███╗   ███╗",
            " ██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║",
            " █████╗  ███████╗   ██║   █████╗  ██████╔╝██╔████╔██║",
            " ██╔══╝  ╚════██║   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║",
            " ███████╗███████║   ██║   ███████╗██║  ██║██║ ╚═╝ ██║",
            " ╚══════╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝",
        ]
        # Use theme colors for the gradient: info → primary → secondary
        c_info = f"bold {self._sem('info', 'cyan')}"
        c_primary = f"bold {self._sem('primary', 'blue')}"
        c_secondary = f"bold {self._sem('secondary', 'magenta')}"
        colours = [c_info, c_info, c_primary, c_primary, c_secondary, c_secondary]

        banner = Text()
        for line, colour in zip(letters, colours):
            banner.append(line + "\n", style=colour)
        self.console.print(Align.center(banner))

        subtitle_bg = self._sem('primary', 'dark_blue')
        self.console.print(
            Align.center(
                Text("⚡  Elasticsearch Commander Terminal  ⚡", style=f"bold white on {subtitle_bg}")
            )
        )
        self.console.print()

    def _render_main_version_panel(self, version_data):
        """Render centered info + performance in a single merged table."""
        version = version_data.get("version", "3.12.0")
        date = version_data.get("date", "04/14/2026")
        commit_hash = version_data.get("hash", "")

        label_style = f"bold {self._sem('primary', 'cyan')}"
        value_style = self._sem('neutral', 'white')
        success_style = f"bold {self._sem('success', 'green')}"
        muted_style = self._sem('muted', 'dim')
        info_style = self._sem('info', 'cyan')

        info = Table.grid(padding=(0, 2))
        info.add_column(style=label_style, no_wrap=True, min_width=14)
        info.add_column(style=value_style)

        version_cell = Text()
        version_cell.append(version, style=success_style)
        if commit_hash:
            version_cell.append(f"  ({commit_hash})", style=muted_style)
        info.add_row("📦 Version",  version_cell)
        info.add_row("📅 Released", Text(date, style=f"bold {info_style}"))
        info.add_row("🎯 Purpose",  "Advanced ES CLI Management & Monitoring")
        info.add_row("👥 Team",     "Monitoring Team US")
        info.add_row("🐍 Python",   Text(sys.version.split()[0], style=muted_style))
        info.add_row("💻 Platform", Text(f"{platform.system()} v{platform.mac_ver()[0]} {platform.machine()}", style=muted_style))

        # Merge performance rows
        info.add_row("", "")  # spacer

        warning_style = self._sem('warning', 'yellow')
        error_style = self._sem('error', 'red')

        def _bar(percent: float, width: int = 20) -> Text:
            filled = int(percent / 100 * width)
            empty  = width - filled
            colour = success_style if percent < 60 else (f"bold {warning_style}" if percent < 85 else f"bold {error_style}")
            bar = Text()
            bar.append("█" * filled, style=colour)
            bar.append("░" * empty,  style=muted_style)
            bar.append(f"  {percent:.1f}%", style=colour)
            return bar

        try:
            import psutil
            cpu  = psutil.cpu_percent(interval=0.1)
            mem  = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            info.add_row("💻 CPU",    _bar(cpu))
            info.add_row("🧠 Memory", Text.assemble(_bar(mem.percent),  (" ", ""), (f"{mem.available // (1024**3)} GB free", muted_style)))
            info.add_row("💾 Disk",   Text.assemble(_bar(disk.percent), (" ", ""), (f"{disk.free // (1024**3)} GB free", muted_style)))
        except ImportError:
            info.add_row("📊 Metrics", Text("Install psutil for live system metrics", style=muted_style))
        except Exception:
            info.add_row("📊 Status", Text("System monitoring temporarily unavailable", style=muted_style))

        info.add_row("🕐 Time", Text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style=f"bold {value_style}"))

        self.console.print(Align.center(info))

    def _render_command_stats_panel(self):
        """Render command statistics panel (unused, kept for compatibility)."""
        pass

    def _render_capabilities_panel(self):
        """Render core capabilities panel (unused, kept for compatibility)."""
        pass

    def _render_performance_panel(self):
        """Render performance and system information panel with progress bars."""
        perf_table = self._generate_performance_info_table()
        perf_panel = Panel(
            Align.center(perf_table),
            title="[bold white]⚡ Performance & System[/bold white]",
            border_style=self._border("green"),
            padding=(1, 2),
        )
        self.console.print(perf_panel)

    def _render_footer(self):
        """Render helpful footer with quick start information."""
        info_style = self._sem('info', 'cyan')
        muted_style = self._sem('muted', 'dim')
        warning_style = self._sem('warning', 'yellow')

        footer_text = Text(justify="center")
        footer_text.append("💡 ", style=f"bold {warning_style}")
        footer_text.append("Quick Start: ", style="bold white")
        footer_text.append("./esterm", style=f"bold {info_style}")
        footer_text.append("  for interactive mode  │  ", style=muted_style)
        footer_text.append("./escmd.py help", style=f"bold {info_style}")
        footer_text.append("  for command reference", style=muted_style)

        self.console.print(Panel(Align.center(footer_text), border_style=muted_style, padding=(0, 2)))

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
        """Generate performance and system information table with colour-coded progress bars."""

        def _bar(percent: float, width: int = 20) -> Text:
            filled = int(percent / 100 * width)
            empty  = width - filled
            if percent < 60:
                colour = "bold green"
            elif percent < 85:
                colour = "bold yellow"
            else:
                colour = "bold red"
            bar = Text()
            bar.append("█" * filled, style=colour)
            bar.append("░" * empty,  style="dim")
            bar.append(f"  {percent:.1f}%", style=colour)
            return bar

        perf_table = Table.grid(padding=(0, 2))
        perf_table.add_column(style="bold white", no_wrap=True, min_width=12)
        perf_table.add_column(min_width=28)
        perf_table.add_column(style="dim")

        try:
            import psutil

            cpu  = psutil.cpu_percent(interval=0.1)
            mem  = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            perf_table.add_row("💻 CPU",    _bar(cpu),          "")
            perf_table.add_row("🧠 Memory", _bar(mem.percent),  f"{mem.available // (1024**3)} GB free")
            perf_table.add_row("💾 Disk",   _bar(disk.percent), f"{disk.free // (1024**3)} GB free")
            perf_table.add_row("", Text(""), "")
            perf_table.add_row(
                "🕐 Time",
                Text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style="bold white"),
                "",
            )

        except ImportError:
            perf_table.add_row(
                "📊 Metrics",
                Text("Install psutil for live system metrics", style="dim"),
                "",
            )
            perf_table.add_row(
                "🕐 Time",
                Text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style="bold white"),
                "",
            )
        except Exception:
            perf_table.add_row("📊 Status", Text("System monitoring temporarily unavailable", style="dim"), "")
            perf_table.add_row(
                "🕐 Time",
                Text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style="bold white"),
                "",
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
