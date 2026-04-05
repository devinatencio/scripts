"""
Repositories rendering utilities for Elasticsearch command-line tool.

This module provides repositories-related display capabilities including enhanced
repositories tables with Rich formatting and statistics.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from typing import Dict, Any


class RepositoriesRenderer:
    """
    Handles repositories-related display rendering with Rich formatting.
    """

    def __init__(self, theme_manager=None, statistics_processor=None, style_system=None):
        """
        Initialize the repositories renderer.

        Args:
            theme_manager: Optional theme manager for styling
            statistics_processor: Statistics processor for data formatting
            style_system: Optional style system for consistent theming
        """
        self.theme_manager = theme_manager
        self.statistics_processor = statistics_processor
        self.style_system = style_system

    def get_themed_style(self, category: str, key: str, default: str) -> str:
        """Get themed style or return default."""
        if self.theme_manager:
            return self.theme_manager.get_themed_style(category, key, default)
        return default

    def print_enhanced_repositories_table(self, repositories_data: Dict[str, Any], console=None) -> None:
        """
        Print enhanced repositories table with Rich formatting and statistics

        Args:
            repositories_data: Dictionary containing repository information
            console: Optional console instance to use for printing
        """
        if console is None:
            console = Console()

        if not repositories_data:
            # Create informative empty state panel consistent with other components
            empty_state_panel = Panel(
                Text.from_markup(
                    "ℹ️  No snapshot repositories are currently configured.\n\n"
                    "Repositories are required for creating backups of your Elasticsearch data.\n"
                    "Common repository types include:\n"
                    "• [cyan]S3[/cyan] - Amazon S3 storage\n"
                    "• [cyan]GCS[/cyan] - Google Cloud Storage\n"
                    "• [cyan]Azure[/cyan] - Azure Blob Storage\n"
                    "• [cyan]FS[/cyan] - Local filesystem\n\n"
                    "[bold green]💡 Quick Start:[/bold green]\n"
                    "Create a repository using: [cyan]./escmd.py repositories create <name> --type <type>[/cyan]\n"
                    "Example: [cyan]./escmd.py repositories create my-s3-repo --type s3 --bucket my-backups[/cyan]\n\n"
                    "[dim]You can also use your cluster management tools or Elasticsearch API to configure repositories.[/dim]",
                    justify="left"
                ),
                title="📦 Snapshot Repositories",
                title_align="left",
                border_style=self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else "yellow",
                padding=(1, 2),
                expand=False
            )
            console.print(empty_state_panel)
            return

        # Calculate statistics
        total_repos = len(repositories_data)
        repo_types = {}
        locations_by_type = {}

        # Analyze repository data
        for repo_name, repo_info in repositories_data.items():
            repo_type = repo_info.get('type', 'unknown')
            repo_types[repo_type] = repo_types.get(repo_type, 0) + 1

            # Track locations by type
            if repo_type not in locations_by_type:
                locations_by_type[repo_type] = []

            settings = repo_info.get('settings', {})
            location = self._extract_repository_location(repo_type, settings)
            locations_by_type[repo_type].append(location)

        # Get theme styles
        full_theme = self.theme_manager.get_full_theme_data() if self.theme_manager else {}
        table_styles = full_theme.get('table_styles', {})

        # Theme colors
        title_color = self.get_themed_style('panel_styles', 'title', 'bright_cyan')
        border_color = table_styles.get('border_style', 'bright_magenta')
        header_style = table_styles.get('header_style', 'bold bright_white on dark_magenta')

        # Create colorized subtitle with repository statistics
        subtitle_rich = Text()
        subtitle_rich.append("Total Repositories: ", style="default")
        subtitle_rich.append(str(total_repos), style=self.style_system._get_style('semantic', 'info', 'cyan') if self.style_system else "cyan")

        # Add repository type breakdown
        if repo_types:
            type_parts = []
            for repo_type, count in repo_types.items():
                type_parts.append(f"{repo_type.upper()}: {count}")

            subtitle_rich.append(" | Types: ", style="default")
            subtitle_rich.append(" • ".join(type_parts), style=self.style_system._get_style('semantic', 'primary', 'bright_magenta') if self.style_system else "bright_magenta")

        # Determine overall health status
        if total_repos == 0:
            health_status = "No repositories configured"
            health_style = self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else "yellow"
        elif total_repos < 2:
            health_status = "Limited backup redundancy"
            health_style = self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else "yellow"
        else:
            health_status = "Good backup coverage"
            health_style = self.style_system._get_style('semantic', 'success', 'green') if self.style_system else "green"

        subtitle_rich.append(" | Status: ", style="default")
        subtitle_rich.append(health_status, style=health_style)

        # Create title panel with statistics
        title_panel = Panel(
            Text("📦 Elasticsearch Snapshot Repositories", style=f"bold {title_color}", justify="center"),
            subtitle=subtitle_rich,
            border_style=border_color,
            padding=(1, 2)
        )

        # Create enhanced repositories table
        table = Table(
            show_header=True,
            header_style=header_style,
            title="📦 Repository Details",
            title_style=f"bold {title_color}",
            border_style=border_color,
            box=self.style_system.get_table_box() if self.style_system else None,
            expand=True
        )

        table.add_column("📦 Repository Name", justify="left", width=20)
        table.add_column("🔧 Type", justify="center", width=12)
        table.add_column("📍 Location/Bucket", justify="left", width=30)
        table.add_column("🔩 Settings", justify="left", width=35)
        table.add_column("🎯 Status", justify="center", width=12)

        # Sort repositories by type then by name for consistent display
        sorted_repos = sorted(repositories_data.items(), key=lambda x: (x[1].get('type', 'unknown'), x[0]))

        for repo_name, repo_info in sorted_repos:
            repo_type = repo_info.get('type', 'unknown')
            settings = repo_info.get('settings', {})

            # Extract location information based on repository type
            location = self._extract_repository_location(repo_type, settings)

            # Format settings for display (exclude sensitive information)
            settings_display = self._format_repository_settings(settings)

            # Determine status based on repository type and configuration
            status_icon, status_text, row_style = self._get_repository_status(repo_type, settings)

            table.add_row(
                repo_name,
                repo_type.upper(),
                location,
                settings_display,
                f"{status_icon} {status_text}",
                style=row_style
            )

        # Create summary statistics panel
        from rich.table import Table as InnerTable
        summary_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Metric", style="bold", no_wrap=True)
        summary_table.add_column("Icon", justify="center", width=4)
        summary_table.add_column("Value", style=title_color)

        summary_table.add_row("Total Repositories:", "📦", f"{total_repos}")

        # Add breakdown by type
        for repo_type, count in repo_types.items():
            type_icon = self._get_type_icon(repo_type)
            summary_table.add_row(f"{repo_type.upper()} Repositories:", type_icon, f"{count}")

        summary_panel = Panel(
            summary_table,
            title="📈 Repository Summary",
            border_style=self.get_themed_style('panel_styles', 'secondary', 'magenta'),
            padding=(1, 2)
        )

        # Print all panels and table
        console.print(title_panel)
        console.print()
        console.print(table)
        console.print()
        console.print(summary_panel)

    def _extract_repository_location(self, repo_type: str, settings: Dict[str, Any]) -> str:
        """
        Extract location information based on repository type.

        Args:
            repo_type: Type of repository
            settings: Repository settings

        Returns:
            str: Formatted location string
        """
        if repo_type == 'fs':
            return settings.get('location', 'Not specified')
        elif repo_type == 's3':
            bucket = settings.get('bucket', 'Not specified')
            base_path = settings.get('base_path', '')
            if base_path:
                return f"s3://{bucket}/{base_path}"
            return f"s3://{bucket}"
        elif repo_type == 'gcs':
            bucket = settings.get('bucket', 'Not specified')
            base_path = settings.get('base_path', '')
            if base_path:
                return f"gs://{bucket}/{base_path}"
            return f"gs://{bucket}"
        elif repo_type == 'azure':
            account = settings.get('account', 'Not specified')
            container = settings.get('container', 'Not specified')
            return f"azure://{account}/{container}"
        elif repo_type == 'hdfs':
            uri = settings.get('uri', 'Not specified')
            path = settings.get('path', '')
            if path:
                return f"{uri}{path}"
            return uri
        else:
            # Try to find common location-like settings
            for key in ['location', 'path', 'bucket', 'uri', 'url']:
                if key in settings:
                    return str(settings[key])
            return 'Configuration varies'

    def _format_repository_settings(self, settings: Dict[str, Any]) -> str:
        """
        Format repository settings for display, excluding sensitive information.

        Args:
            settings: Repository settings dictionary

        Returns:
            str: Formatted settings string
        """
        # Sensitive keys to exclude from display
        sensitive_keys = {
            'access_key', 'secret_key', 'password', 'token',
            'private_key', 'credentials', 'auth', 'key'
        }

        # Keys to prioritize for display
        important_keys = {
            'compress', 'chunk_size', 'readonly', 'verify',
            'max_restore_bytes_per_sec', 'max_snapshot_bytes_per_sec',
            'server_side_encryption', 'storage_class'
        }

        display_settings = []

        # Add important settings first
        for key in important_keys:
            if key in settings:
                value = settings[key]
                if key in ['max_restore_bytes_per_sec', 'max_snapshot_bytes_per_sec', 'chunk_size']:
                    # Format byte values
                    if isinstance(value, (int, str)) and str(value).isdigit():
                        value = self._format_bytes_simple(int(value))
                display_settings.append(f"{key}: {value}")

        # Add other non-sensitive settings
        for key, value in settings.items():
            if (key not in important_keys and
                key not in sensitive_keys and
                not any(sensitive in key.lower() for sensitive in sensitive_keys) and
                key not in ['location', 'bucket', 'path', 'uri', 'base_path']):  # Already shown in location

                # Limit value length for display
                str_value = str(value)
                if len(str_value) > 20:
                    str_value = str_value[:17] + "..."
                display_settings.append(f"{key}: {str_value}")

        if not display_settings:
            return "Default configuration"

        # Limit total number of settings shown
        if len(display_settings) > 3:
            return " • ".join(display_settings[:3]) + f" (+{len(display_settings)-3} more)"
        else:
            return " • ".join(display_settings)

    def _get_repository_status(self, repo_type: str, settings: Dict[str, Any]) -> tuple:
        """
        Determine repository status based on type and configuration.

        Args:
            repo_type: Repository type
            settings: Repository settings

        Returns:
            tuple: (status_icon, status_text, row_style)
        """
        # Check for readonly repositories
        if settings.get('readonly', False):
            return ("🔒", "Read-Only", self.get_themed_style('table_styles', 'warning_health', 'yellow'))

        # Check repository type reliability
        if repo_type in ['s3', 'gcs', 'azure']:
            return ("✅", "Active", self.get_themed_style('table_styles', 'healthy', 'green'))
        elif repo_type == 'fs':
            return ("📁", "Local", self.get_themed_style('table_styles', 'normal', 'white'))
        elif repo_type == 'hdfs':
            return ("📂", "HDFS", self.get_themed_style('table_styles', 'normal', 'white'))
        else:
            return ("❓", "Unknown", self.get_themed_style('table_styles', 'warning_health', 'yellow'))

    def _get_type_icon(self, repo_type: str) -> str:
        """Get appropriate icon for repository type."""
        type_icons = {
            's3': '☁️',
            'gcs': '☁️',
            'azure': '☁️',
            'fs': '📁',
            'hdfs': '📂',
            'url': '🌐'
        }
        return type_icons.get(repo_type, '❓')

    def _format_bytes_simple(self, bytes_value: int) -> str:
        """Simple byte formatting fallback."""
        if bytes_value >= 1024**4:
            return f"{bytes_value / (1024**4):.1f}TB"
        elif bytes_value >= 1024**3:
            return f"{bytes_value / (1024**3):.1f}GB"
        elif bytes_value >= 1024**2:
            return f"{bytes_value / (1024**2):.1f}MB"
        elif bytes_value >= 1024:
            return f"{bytes_value / 1024:.1f}KB"
        else:
            return f"{bytes_value}B"
