"""
Snapshot renderer for escmd snapshot display operations.

This module handles the display and formatting of snapshot-related information
using Rich components and theme management with enhanced semantic styling.
"""

from typing import Dict, Any, Optional, List
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich.console import Console


class SnapshotRenderer:
    """
    Renderer for snapshot-related display operations.

    This class handles the formatting and display of snapshot information,
    status displays, and snapshot panels with consistent theming.
    """

    def __init__(self, es_client):
        """Initialize the SnapshotRenderer with ES client reference."""
        self.es_client = es_client
        self.console = Console()
        self.theme_manager = es_client.theme_manager

        # Initialize style system if available
        self.style_system = None
        try:
            from display.style_system import StyleSystem
            self.style_system = StyleSystem(self.theme_manager)
        except ImportError:
            pass

    def _border(self, fallback: str = "cyan") -> str:
        """Return the theme border style."""
        if self.theme_manager:
            return self.theme_manager.get_theme_styles().get("border_style", fallback)
        return fallback

    def _title_style(self, fallback: str = "bold white") -> str:
        """Return the theme panel title style."""
        if self.theme_manager:
            return self.theme_manager.get_themed_style("panel_styles", "title", fallback)
        return fallback

    def create_snapshots_panel(self, theme_color: str, snapshot_repo: Optional[str] = None,
                             snapshots: Optional[Any] = None) -> Panel:
        """
        Create snapshots information panel using semantic styling.

        Args:
            theme_color: Color theme for the panel
            snapshot_repo: Repository name (optional)
            snapshots: Snapshot data (can be stats dict or list)

        Returns:
            Panel: Rich panel with snapshot information
        """
        if self.style_system:
            return self._create_snapshots_panel_semantic(snapshot_repo, snapshots)
        else:
            return self._create_snapshots_panel_legacy(theme_color, snapshot_repo, snapshots)

    def _create_snapshots_panel_semantic(self, snapshot_repo: Optional[str] = None,
                                       snapshots: Optional[Any] = None) -> Panel:
        """Create snapshots panel using new semantic styling system."""

        # Create inner table with semantic styling
        table = Table.grid(padding=(0, 1))
        table.add_column(style=self.style_system.get_semantic_style('neutral'), no_wrap=True)
        table.add_column(justify="left", width=15)
        table.add_column(style="", no_wrap=True)

        if not snapshot_repo:
            # No snapshot repository configured - use warning semantics
            warning_text = self.style_system.create_semantic_text("NOT CONFIGURED", 'warning')
            table.add_row("📦 Repository:",
                         self.style_system.create_semantic_text("None", 'muted'),
                         self.style_system.create_semantic_text("🔶", 'warning'))
            table.add_row("📸 Total:",
                         self.style_system.create_semantic_text("N/A", 'muted'),
                         Text(""))
            table.add_row("✅ Successful:",
                         self.style_system.create_semantic_text("N/A", 'muted'),
                         Text(""))
            table.add_row("❌ Failed:",
                         self.style_system.create_semantic_text("N/A", 'muted'),
                         Text(""))
            table.add_row("🎯 Status:", warning_text,
                         self.style_system.create_semantic_text("🔶", 'warning'))
        else:
            # Repository is configured - extract statistics
            if isinstance(snapshots, dict) and 'total' in snapshots:
                # New fast stats format
                stats = snapshots
                total_snapshots = stats.get('total', 0)
                successful = stats.get('successful', 0)
                failed = stats.get('failed', 0)
                in_progress = stats.get('in_progress', 0)
            else:
                # Old format - list of snapshots or empty list
                if snapshots is None:
                    snapshots = []
                total_snapshots = len(snapshots)
                successful = sum(1 for s in snapshots if s.get('state') == 'SUCCESS')
                failed = sum(1 for s in snapshots if s.get('state') == 'FAILED')
                in_progress = sum(1 for s in snapshots if s.get('state') == 'IN_PROGRESS')

            # Repository status - using semantic success indicator
            table.add_row("📦 Repository:",
                         self.style_system.create_semantic_text(snapshot_repo, 'info'),
                         self.style_system.create_semantic_text("✅", 'success'))

            # Total snapshots with semantic status
            total_status = self.style_system.create_semantic_text("📊", 'info') if total_snapshots > 0 else \
                          self.style_system.create_semantic_text("🔶", 'warning')
            table.add_row("📸 Total:",
                         self.style_system.create_semantic_text(str(total_snapshots), 'neutral'),
                         total_status)

            # Successful snapshots
            success_icon = self.style_system.create_semantic_text("✅", 'success') if successful > 0 else Text("")
            table.add_row("✅ Successful:",
                         self.style_system.create_semantic_text(str(successful), 'neutral'),
                         success_icon)

            # Failed snapshots - semantic error styling when > 0
            if failed > 0:
                failed_icon = self.style_system.create_semantic_text("❌", 'error')
                failed_text = self.style_system.create_semantic_text(str(failed), 'error')
            else:
                failed_icon = self.style_system.create_semantic_text("✅", 'success')
                failed_text = self.style_system.create_semantic_text(str(failed), 'neutral')

            table.add_row("❌ Failed:", failed_text, failed_icon)

            # Overall status determination using semantic logic
            if total_snapshots == 0:
                status_text = self.style_system.create_semantic_text("NO SNAPSHOTS", 'warning')
                status_icon = self.style_system.create_semantic_text("🔶", 'warning')
            elif failed > 0:
                status_text = self.style_system.create_semantic_text("ISSUES DETECTED", 'error')
                status_icon = self.style_system.create_semantic_text("❌", 'error')
            elif in_progress > 0:
                status_text = self.style_system.create_semantic_text("IN PROGRESS", 'info')
                status_icon = self.style_system.create_semantic_text("🔄", 'info')
            else:
                status_text = self.style_system.create_semantic_text("HEALTHY", 'success')
                status_icon = self.style_system.create_semantic_text("✅", 'success')

            table.add_row("🎯 Status:", status_text, status_icon)

        # Create panel using semantic panel creation
        return self.style_system.create_dashboard_panel(table, "Snapshots", "📸")

    def _create_snapshots_panel_legacy(self, theme_color: str, snapshot_repo: Optional[str] = None,
                                     snapshots: Optional[Any] = None) -> Panel:
        """Legacy panel creation for backward compatibility."""
        # Get theme styles
        styles = self.theme_manager.get_theme_styles()
        panel_styles = styles.get('panel_styles', {})

        # Create inner table with 3 columns: Label, Value, Status
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(justify="left", width=15)
        table.add_column(style="", no_wrap=True)

        if not snapshot_repo:
            # No snapshot repository configured
            warning_style = panel_styles.get('warning', 'bold yellow')
            table.add_row("📦 Repository:", Text("None", style=panel_styles.get('info', 'bold white')), Text("🔶", style=warning_style))
            table.add_row("📸 Total:", Text("N/A", style=panel_styles.get('info', 'bold white')), Text("", style=""))
            table.add_row("✅ Successful:", Text("N/A", style=panel_styles.get('info', 'bold white')), Text("", style=""))
            table.add_row("❌ Failed:", Text("N/A", style=panel_styles.get('info', 'bold white')), Text("", style=""))
            table.add_row("🎯 Status:", Text("NOT CONFIGURED", style=warning_style), Text("🔶", style=warning_style))
        else:
            # Get theme colors for different status indicators
            success_style = panel_styles.get('success', 'bold green')
            error_style = panel_styles.get('error', 'bold red')
            warning_style = panel_styles.get('warning', 'bold yellow')
            info_style = panel_styles.get('info', 'bold blue')

            # Check if we have stats dict (fast method) or list of snapshots (old method)
            if isinstance(snapshots, dict) and 'total' in snapshots:
                # New fast stats format
                stats = snapshots
                total_snapshots = stats.get('total', 0)
                successful = stats.get('successful', 0)
                failed = stats.get('failed', 0)
                in_progress = stats.get('in_progress', 0)
            else:
                # Old format - list of snapshots or empty list
                if snapshots is None:
                    snapshots = []
                total_snapshots = len(snapshots)
                successful = sum(1 for s in snapshots if s.get('state') == 'SUCCESS')
                failed = sum(1 for s in snapshots if s.get('state') == 'FAILED')
                in_progress = sum(1 for s in snapshots if s.get('state') == 'IN_PROGRESS')

            # Repository status
            table.add_row("📦 Repository:", Text(snapshot_repo, style=panel_styles.get('info', 'bold white')), Text("✅", style=success_style))

            # Total snapshots
            total_status = Text("📊", style=info_style) if total_snapshots > 0 else Text("🔶", style=warning_style)
            table.add_row("📸 Total:", Text(str(total_snapshots), style=panel_styles.get('info', 'bold white')), total_status)

            # Successful snapshots
            success_status = Text("✅", style=success_style) if successful > 0 else Text("", style="")
            table.add_row("✅ Successful:", Text(str(successful), style=panel_styles.get('info', 'bold white')), success_status)

            # Failed snapshots
            failed_status = Text("❌", style=error_style) if failed > 0 else Text("✅", style=success_style)
            table.add_row("❌ Failed:", Text(str(failed), style=panel_styles.get('info', 'bold white')), failed_status)

            # Overall status
            if failed > 0:
                status_text = "FAILURES DETECTED"
                status_icon = Text("❌", style=error_style)
            elif successful > 0:
                status_text = "HEALTHY"
                status_icon = Text("✅", style=success_style)
            elif in_progress > 0:
                status_text = "IN PROGRESS"
                status_icon = Text("⏳", style=warning_style)
            else:
                status_text = "NO SNAPSHOTS"
                status_icon = Text("📭", style=warning_style)

            table.add_row("🎯 Status:", Text(status_text, style=panel_styles.get('info', 'bold white')), status_icon)

        # Apply theme color to panel border
        panel_border_style = panel_styles.get('border', self._border())
        ts = self._title_style()

        return Panel(
            table,
            title=f"[{ts}]📸 Snapshots[/{ts}]",
            border_style=panel_border_style,
            padding=(1, 1)
        )

    def display_snapshot_status(self, status_info: Dict[str, Any], repository_name: str) -> None:
        """
        Display snapshot status with Rich formatting.

        Args:
            status_info: Snapshot status information
            repository_name: Repository name
        """
        # Determine state styling and icon
        state = status_info.get('state', 'UNKNOWN')
        if state == 'SUCCESS':
            state_text = Text("✅ SUCCESS", style="bold green")
            panel_style = "green"
        elif state == 'IN_PROGRESS':
            state_text = Text("⏳ IN PROGRESS", style="bold yellow")
            panel_style = "yellow"
        elif state == 'FAILED':
            state_text = Text("❌ FAILED", style="bold red")
            panel_style = "red"
        elif state == 'PARTIAL':
            state_text = Text("🔶 PARTIAL", style="bold orange3")
            panel_style = "orange3"
        else:
            state_text = Text(f"❓ {state}", style="bold white")
            panel_style = "white"

        # Create main status table
        status_table = Table.grid(padding=(0, 1))
        status_table.add_column(style="bold white", no_wrap=True)
        status_table.add_column(style="bold cyan")

        # Basic information
        status_table.add_row("📦 Repository:", repository_name)
        status_table.add_row("📸 Snapshot:", status_info.get('snapshot_name', status_info.get('snapshot', 'N/A')))
        status_table.add_row("🔖 State:", state_text)

        # Timing information
        status_table.add_row("🕐 Start Time:", status_info.get('start_time_formatted', 'N/A'))
        status_table.add_row("🕑 End Time:", status_info.get('end_time_formatted', 'N/A'))
        status_table.add_row("🕐 Duration:", status_info.get('duration', 'N/A'))

        # Version information
        if status_info.get('version') != 'N/A':
            status_table.add_row("🔖 ES Version:", status_info.get('version', 'N/A'))

        # Global state
        global_state = "✅ Yes" if status_info.get('include_global_state') else "❌ No"
        status_table.add_row("🌐 Global State:", global_state)

        # Create statistics table
        stats_table = Table.grid(padding=(0, 1))
        stats_table.add_column(style="bold white", no_wrap=True)
        stats_table.add_column(style="bold cyan")

        stats_table.add_row("📊 Total Indices:", str(status_info.get('indices_count', 0)))
        stats_table.add_row("✅ Total Shards:", str(status_info.get('total_shards', 0)))
        stats_table.add_row("🎯 Successful Shards:", str(status_info.get('successful_shards', 0)))

        failed_shards = status_info.get('failed_shards', 0)
        failed_style = "bold red" if failed_shards > 0 else "bold green"
        stats_table.add_row("❌ Failed Shards:", Text(str(failed_shards), style=failed_style))

        failures_count = status_info.get('failures_count', 0)
        failures_style = "bold red" if failures_count > 0 else "bold green"
        stats_table.add_row("🔶 Failures:", Text(str(failures_count), style=failures_style))

        # Create panels
        ts = self._title_style()
        main_panel = Panel(
            status_table,
            title=f"[{ts}]📸 Snapshot Information[/{ts}]",
            border_style=panel_style,
            padding=(1, 2)
        )

        stats_panel = Panel(
            stats_table,
            title=f"[{ts}]📊 Statistics[/{ts}]",
            border_style=panel_style,
            padding=(1, 2)
        )

        # Display main panels side by side
        print()
        columns = Columns([main_panel, stats_panel], equal=True, expand=True)
        self.console.print(columns)

        # Show indices list if not too many
        indices = status_info.get('indices', [])
        if indices:
            if len(indices) <= 10:
                indices_text = Text("\n".join(f"• {idx}" for idx in indices))
            else:
                indices_text = Text(f"Total: {len(indices)} indices\n")
                indices_text.append("First 10:\n", style="dim")
                indices_text.append("\n".join(f"• {idx}" for idx in indices[:10]))
                indices_text.append(f"\n... and {len(indices) - 10} more", style="dim")

            indices_panel = Panel(
                indices_text,
                title=f"[{ts}]📂 Included Indices[/{ts}]",
                border_style=panel_style,
                padding=(1, 2)
            )
            self.console.print(indices_panel)

        # Show failures if any
        failures = status_info.get('failures', [])
        if failures:
            failures_text = Text()
            for i, failure in enumerate(failures):
                if i > 0:
                    failures_text.append("\n")
                failures_text.append(f"• Index: {failure.get('index', 'Unknown')}\n", style="bold white")
                failures_text.append(f"  Shard: {failure.get('shard_id', 'Unknown')}\n", style="white")
                failures_text.append(f"  Reason: {failure.get('reason', 'No details')}\n", style="red")

            failures_panel = Panel(
                failures_text,
                title=f"[{self.style_system.get_semantic_style('error') if self.style_system else ts}]❌ Failures Details[/{self.style_system.get_semantic_style('error') if self.style_system else ts}]",
                border_style=self.style_system.get_semantic_style("error") if self.style_system else "red",
                padding=(1, 2)
            )
            self.console.print(failures_panel)

        print()


# Backward compatibility functions
def create_snapshots_panel(es_client, theme_color: str, snapshot_repo: Optional[str] = None,
                          snapshots: Optional[Any] = None) -> Panel:
    """Backward compatibility function for creating snapshots panel."""
    renderer = SnapshotRenderer(es_client)
    return renderer.create_snapshots_panel(theme_color, snapshot_repo, snapshots)


def display_snapshot_status(es_client, status_info: Dict[str, Any], repository_name: str) -> None:
    """Backward compatibility function for displaying snapshot status."""
    renderer = SnapshotRenderer(es_client)
    return renderer.display_snapshot_status(status_info, repository_name)
