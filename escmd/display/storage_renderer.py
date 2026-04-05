"""
Storage rendering utilities for Elasticsearch command-line tool.

This module provides storage-related display capabilities including enhanced
storage allocation tables with Rich formatting and statistics.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table


class StorageRenderer:
    """
    Handles storage-related display rendering with Rich formatting.
    """

    def __init__(self, theme_manager=None, statistics_processor=None, style_system=None):
        """
        Initialize the storage renderer.

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

    def create_usage_progress_bar(self, usage_percent: float, width: int = 12) -> Text:
        """
        Create a visual progress bar for storage usage percentage.

        Args:
            usage_percent: Usage percentage (0-100)
            width: Width of progress bar in characters

        Returns:
            Text: Rich Text object with themed progress bar
        """
        filled = int((usage_percent / 100) * width)
        empty = width - filled

        # Create progress bar with theme-aware colors
        progress_text = Text()

        # Determine colors based on usage thresholds (matching status logic)
        if usage_percent >= 90:
            # Critical - red
            bar_style = self.get_themed_style('table_styles', 'critical_health', 'red')
        elif usage_percent >= 80:
            # High - red/orange
            bar_style = self.get_themed_style('table_styles', 'critical_health', 'red')
        elif usage_percent >= 70:
            # Elevated - yellow
            bar_style = self.get_themed_style('table_styles', 'warning_health', 'yellow')
        elif usage_percent >= 60:
            # Moderate - default/white
            bar_style = self.get_themed_style('table_styles', 'normal', 'white')
        else:
            # Good - green
            bar_style = self.get_themed_style('table_styles', 'healthy', 'green')

        # Empty portion style
        empty_style = self.get_themed_style('table_styles', 'normal', 'dim white')

        # Build progress bar
        progress_text.append("█" * filled, style=bar_style)
        progress_text.append("░" * empty, style=empty_style)
        progress_text.append(f" {usage_percent:5.1f}%", style=bar_style)

        return progress_text

    def print_enhanced_storage_table(self, data_dict: dict, console=None, indices_count=None) -> None:
        """
        Print enhanced storage allocation table with Rich formatting and statistics

        Args:
            data_dict: Dictionary containing storage data for nodes
            console: Optional console instance to use for printing
            indices_count: Optional total number of unique indices
        """
        if console is None:
            console = Console()

        if not data_dict:
            console.print("[red]❌ No storage data available[/red]")
            return

        # Calculate statistics (exclude UNASSIGNED from node count)
        total_nodes = len([node for node in data_dict.keys() if node != "UNASSIGNED"])
        total_shards = sum(node_data['shards'] for node_data in data_dict.values())
        # Exclude UNASSIGNED from disk usage calculations (it has no actual storage)
        total_used_bytes = sum(node_data['disk.used'] for node, node_data in data_dict.items() if node != "UNASSIGNED")
        total_avail_bytes = sum(node_data['disk.avail'] for node, node_data in data_dict.items() if node != "UNASSIGNED")
        total_size_bytes = sum(node_data['disk.total'] for node, node_data in data_dict.items() if node != "UNASSIGNED")

        # Calculate cluster-wide disk usage percentage
        if total_size_bytes > 0:
            cluster_used_percent = (total_used_bytes / total_size_bytes) * 100
        else:
            cluster_used_percent = 0

        # Find nodes with different disk usage levels (exclude UNASSIGNED)
        critical_nodes = [node for node, data in data_dict.items() if node != "UNASSIGNED" and float(data['disk.percent']) >= 90]
        high_usage_nodes = [node for node, data in data_dict.items() if node != "UNASSIGNED" and 80 <= float(data['disk.percent']) < 90]
        elevated_nodes = [node for node, data in data_dict.items() if node != "UNASSIGNED" and 70 <= float(data['disk.percent']) < 80]

        # Get theme styles from the theme system
        full_theme = self.theme_manager.get_full_theme_data() if self.theme_manager else {}
        table_styles = full_theme.get('table_styles', {})

        # Theme colors
        title_color = self.get_themed_style('panel_styles', 'title', 'bright_cyan')
        border_color = table_styles.get('border_style', 'bright_magenta')
        header_style = table_styles.get('header_style', 'bold bright_white on dark_magenta')

        # Create colorized subtitle with theme-based styling for statistics (similar to shards command)
        subtitle_rich = Text()
        subtitle_rich.append("Nodes: ", style="default")
        subtitle_rich.append(str(total_nodes), style=self.style_system._get_style('semantic', 'info', 'cyan') if self.style_system else "cyan")

        # Add indices count if provided
        if indices_count is not None:
            subtitle_rich.append(" | Indices: ", style="default")
            subtitle_rich.append(f"{indices_count:,}", style=self.style_system._get_style('semantic', 'primary', 'bright_magenta') if self.style_system else "bright_magenta")

        subtitle_rich.append(" | Shards: ", style="default")
        subtitle_rich.append(f"{total_shards:,}", style=self.style_system._get_style('semantic', 'success', 'green') if self.style_system else "green")
        subtitle_rich.append(" | Cluster Usage: ", style="default")

        # Color code cluster usage based on percentage
        if cluster_used_percent >= 90:
            usage_style = self.style_system._get_style('semantic', 'error', 'red') if self.style_system else "red"
        elif cluster_used_percent >= 80:
            usage_style = self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else "yellow"
        elif cluster_used_percent >= 70:
            usage_style = self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else "yellow"
        else:
            usage_style = self.style_system._get_style('semantic', 'success', 'green') if self.style_system else "green"

        subtitle_rich.append(f"{cluster_used_percent:.1f}%", style=usage_style)

        # Add status indicators for problematic nodes
        if len(elevated_nodes) > 0:
            subtitle_rich.append(" | Elevated: ", style="default")
            subtitle_rich.append(str(len(elevated_nodes)), style=self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else "yellow")

        if len(high_usage_nodes) > 0:
            subtitle_rich.append(" | High: ", style="default")
            subtitle_rich.append(str(len(high_usage_nodes)), style=self.style_system._get_style('semantic', 'warning', 'orange') if self.style_system else "orange")

        if len(critical_nodes) > 0:
            subtitle_rich.append(" | Critical: ", style="default")
            subtitle_rich.append(str(len(critical_nodes)), style=self.style_system._get_style('semantic', 'error', 'red') if self.style_system else "red")

        # Create title panel with colorful subtitle
        title_panel = Panel(
            Text("💾 Elasticsearch Storage Overview", style=f"bold {title_color}", justify="center"),
            subtitle=subtitle_rich,
            border_style=border_color,
            padding=(1, 2)
        )

        # Create enhanced storage table
        table = Table(
            show_header=True,
            header_style=header_style,
            title="💾 Node Storage Details",
            title_style=f"bold {title_color}",
            border_style=border_color,
            box=self.style_system.get_table_box() if self.style_system else None,
            expand=True
        )
        table.add_column("💻 Node", justify="left", width=16)
        table.add_column("🔄 Shards", justify="center", width=8)
        table.add_column("📊 Usage %", justify="center", width=22)  # Centered for progress bar
        table.add_column("💾 Used", justify="right", width=12)
        table.add_column("🆓 Available", justify="right", width=12)
        table.add_column("📦 Total", justify="right", width=12)
        table.add_column("🎯 Status", justify="center", width=10)

        # Sort nodes by disk usage percentage (highest first)
        sorted_nodes = sorted(data_dict.items(), key=lambda x: float(x[1]['disk.percent']), reverse=True)

        for node_name, node_data in sorted_nodes:
            shards = node_data['shards']
            disk_percent = float(node_data['disk.percent'])

            # Format storage sizes using statistics processor if available
            if self.statistics_processor:
                disk_used = self.statistics_processor.format_bytes(node_data['disk.used'])
                disk_avail = self.statistics_processor.format_bytes(node_data['disk.avail'])
                disk_total = self.statistics_processor.format_bytes(node_data['disk.total'])
            else:
                # Fallback formatting
                disk_used = self._format_bytes_fallback(node_data['disk.used'])
                disk_avail = self._format_bytes_fallback(node_data['disk.avail'])
                disk_total = self._format_bytes_fallback(node_data['disk.total'])

            # Special handling for UNASSIGNED nodes
            if node_name == "UNASSIGNED":
                row_style = self.get_themed_style('table_styles', 'warning_health', 'yellow')
                status_icon = "🔶 "
                status_text = "Warning"
            # Determine row styling and status based on disk usage using theme colors
            elif disk_percent >= 90:
                row_style = self.get_themed_style('table_styles', 'critical_health', 'bright_red')
                status_icon = "🔴"
                status_text = "Critical"
            elif disk_percent >= 80:
                row_style = self.get_themed_style('table_styles', 'warning_health', 'red')
                status_icon = "🔶 "
                status_text = "High"
            elif disk_percent >= 70:
                row_style = self.get_themed_style('table_styles', 'warning_health', 'yellow')
                status_icon = "🟡"
                status_text = "Elevated"
            elif disk_percent >= 60:
                row_style = self.get_themed_style('table_styles', 'normal', 'white')
                status_icon = "📊"
                status_text = "Moderate"
            else:
                row_style = self.get_themed_style('table_styles', 'healthy', 'green')
                status_icon = "✅"
                status_text = "Good"

            # Create usage progress bar
            usage_progress_bar = self.create_usage_progress_bar(disk_percent, width=10)

            table.add_row(
                node_name,
                f"{shards:,}",
                usage_progress_bar,  # Use progress bar instead of plain percentage
                disk_used,
                disk_avail,
                disk_total,
                f"{status_icon} {status_text}",
                style=row_style
            )

        # Create summary statistics panel with aligned table
        from rich.table import Table as InnerTable
        summary_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Metric", style="bold", no_wrap=True)
        summary_table.add_column("Icon", justify="center", width=4)
        summary_table.add_column("Value", style=title_color)

        formatted_used = self.statistics_processor.format_bytes(total_used_bytes) if self.statistics_processor else self._format_bytes_fallback(total_used_bytes)
        formatted_avail = self.statistics_processor.format_bytes(total_avail_bytes) if self.statistics_processor else self._format_bytes_fallback(total_avail_bytes)
        formatted_total = self.statistics_processor.format_bytes(total_size_bytes) if self.statistics_processor else self._format_bytes_fallback(total_size_bytes)

        summary_table.add_row("Total Nodes:", "💻", f"{total_nodes}")
        if indices_count is not None:
            summary_table.add_row("Total Indices:", "📑", f"{indices_count:,}")
        summary_table.add_row("Total Shards:", "🔄", f"{total_shards:,}")
        summary_table.add_row("Cluster Used:", "💾", formatted_used)
        summary_table.add_row("Cluster Available:", "🆓", formatted_avail)
        summary_table.add_row("Cluster Total:", "📦", formatted_total)
        summary_table.add_row("Average Usage:", "📊", f"{cluster_used_percent:.1f}%")

        summary_panel = Panel(
            summary_table,
            title="📈 Cluster Summary",
            border_style=self.get_themed_style('panel_styles', 'secondary', 'magenta'),
            padding=(1, 2)
        )

        # Create alerts panel if there are issues
        if critical_nodes or high_usage_nodes or elevated_nodes:
            alerts_content = ""
            if critical_nodes:
                alerts_content += f"[bold bright_red]🔴 Critical Nodes ({len(critical_nodes)}):[/bold bright_red]\n"
                for node in critical_nodes[:3]:  # Show first 3
                    usage = data_dict[node]['disk.percent']
                    alerts_content += f"  • {node}: {usage}%\n"
                if len(critical_nodes) > 3:
                    alerts_content += f"  • ... and {len(critical_nodes) - 3} more\n"
                alerts_content += "\n"

            if high_usage_nodes:
                alerts_content += f"[bold red]🔶 High Usage Nodes ({len(high_usage_nodes)}):[/bold red]\n"
                for node in high_usage_nodes[:3]:  # Show first 3
                    usage = data_dict[node]['disk.percent']
                    alerts_content += f"  • {node}: {usage}%\n"
                if len(high_usage_nodes) > 3:
                    alerts_content += f"  • ... and {len(high_usage_nodes) - 3} more\n"
                alerts_content += "\n"

            if elevated_nodes:
                alerts_content += f"[bold yellow]🟡 Elevated Usage Nodes ({len(elevated_nodes)}):[/bold yellow]\n"
                for node in elevated_nodes[:3]:  # Show first 3
                    usage = data_dict[node]['disk.percent']
                    alerts_content += f"  • {node}: {usage}%\n"
                if len(elevated_nodes) > 3:
                    alerts_content += f"  • ... and {len(elevated_nodes) - 3} more\n"

            alerts_panel = Panel(
                alerts_content.rstrip(),
                title="🔶 Storage Alerts",
                border_style=self.get_themed_style('panel_styles', 'error', 'bright_red') if critical_nodes else (self.get_themed_style('panel_styles', 'warning', 'red') if high_usage_nodes else self.get_themed_style('panel_styles', 'warning', 'yellow')),
                padding=(1, 2)
            )

            # Display everything
            print()
            console.print(title_panel)
            print()
            console.print(Columns([summary_panel, alerts_panel], expand=True))
            print()
            console.print(table)
        else:
            # No alerts - just show summary
            print()
            console.print(title_panel)
            print()
            console.print(summary_panel)
            print()
            console.print(table)

    def _format_bytes_fallback(self, bytes_value: int) -> str:
        """Fallback bytes formatting when statistics processor is not available."""
        if bytes_value == 0:
            return "0B"

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0

        return f"{bytes_value:.1f}PB"
