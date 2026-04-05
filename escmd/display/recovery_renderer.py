"""
Recovery display rendering for Elasticsearch command-line tool.

This module provides recovery-related display capabilities including
recovery status displays, progress visualization, and recovery statistics.
"""

from typing import Dict, Any, Optional, List
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich.console import Console
from .style_system import StyleSystem


class RecoveryRenderer:
    """
    Handles recovery-related display rendering.

    Provides methods for rendering recovery status displays, progress bars,
    and recovery operation visualizations.
    """

    def __init__(self, theme_manager=None):
        """
        Initialize the recovery renderer.

        Args:
            theme_manager: Theme manager instance for styling
        """
        self.theme_manager = theme_manager
        self.style_system = StyleSystem(theme_manager) if theme_manager else None
        self.console = Console()

    def render_enhanced_recovery_status(self, recovery_status: Dict[str, Any]) -> None:
        """
        Render enhanced recovery status with Rich formatting.

        Args:
            recovery_status: Recovery status data from HealthCommands.get_shard_recovery()
        """
        if not recovery_status:
            no_recovery_panel = Panel(
                Text("🎉 No active recovery operations", style="bold green", justify="center"),
                title="🔄 Cluster Recovery Status",
                border_style="cyan",
                padding=(2, 4)
            )
            self.console.print(no_recovery_panel)
            return

        # Calculate recovery statistics
        stats = self._calculate_recovery_statistics(recovery_status)

        # If no active recoveries, show the simple message
        if stats['active_recoveries'] == 0:
            no_recovery_panel = Panel(
                Text("🎉 No active recovery operations", style="bold green", justify="center"),
                title="🔄 Cluster Recovery Status",
                border_style="cyan",
                padding=(2, 4)
            )
            self.console.print(no_recovery_panel)
            return

        # Create title panel
        title_panel = Panel(
            Text("🔄 Cluster Recovery Status", style="bold blue", justify="center"),
            subtitle=f"Active recovery operations: {stats['active_recoveries']}",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create summary and stage panels
        summary_panel = self._create_recovery_summary_panel(stats)
        stage_panel = self._create_recovery_stages_panel(stats['stage_counts'])

        # Create detailed recovery table
        recovery_table = self._create_recovery_table(recovery_status)

        # Display everything
        self.console.print(title_panel)
        print()
        self.console.print(Columns([summary_panel, stage_panel], expand=True))
        print()
        self.console.print(Panel(
            recovery_table,
            title="🔄 Active Recovery Operations",
            border_style="cyan",
            padding=(1, 2)
        ))

    def _calculate_recovery_statistics(self, recovery_status: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate recovery statistics from status data."""
        total_shards = 0
        completed_shards = 0
        active_recoveries = 0
        recovery_types = {}
        stage_counts = {}

        for index_name, index_data in recovery_status.items():
            shards = index_data.get('shards', [])
            for shard in shards:
                total_shards += 1

                # Only count as active recovery if not in DONE stage
                stage = shard.get('stage', 'unknown')
                if stage and stage.upper() != 'DONE':
                    active_recoveries += 1

                # Count recovery types (only for active recoveries)
                if stage and stage.upper() != 'DONE':
                    shard_type = shard.get('type', 'unknown')
                    recovery_types[shard_type] = recovery_types.get(shard_type, 0) + 1

                # Count stages (only for active recoveries)
                if stage and stage.upper() != 'DONE':
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1

                # Check completion
                translog_percent = shard.get('translog', {}).get('percent', '0%')
                try:
                    percent_value = float(translog_percent.replace('%', '').strip())
                    if percent_value >= 100:
                        completed_shards += 1
                except:
                    pass

        return {
            'total_shards': total_shards,
            'completed_shards': completed_shards,
            'active_recoveries': active_recoveries,
            'recovery_types': recovery_types,
            'stage_counts': stage_counts
        }

    def _create_recovery_summary_panel(self, stats: Dict[str, Any]) -> Panel:
        """Create recovery summary panel."""
        summary_table = Table(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Label", style="bold", no_wrap=True)
        summary_table.add_column("Icon", justify="left", width=3)
        summary_table.add_column("Value", no_wrap=True)

        summary_table.add_row("Total Shards:", "📊", str(stats['total_shards']))
        summary_table.add_row("Active Recoveries:", "🔄", str(stats['active_recoveries']))

        if stats['total_shards'] > 0:
            completion_rate = (stats['completed_shards'] / stats['total_shards']) * 100
            summary_table.add_row("Completion Rate:", "✅", f"{completion_rate:.1f}%")

        # Recovery types breakdown
        if stats['recovery_types']:
            type_text = ", ".join([f"{count} {rtype}" for rtype, count in stats['recovery_types'].items()])
            summary_table.add_row("Recovery Types:", "🔧", type_text)

        return Panel(
            summary_table,
            title="📈 Recovery Summary",
            border_style="cyan",
            padding=(1, 2)
        )

    def _create_recovery_stages_panel(self, stage_counts: Dict[str, int]) -> Panel:
        """Create recovery stages panel."""
        if stage_counts:
            stage_table = Table(show_header=False, box=None, padding=(0, 1))
            stage_table.add_column("Stage", style="bold", no_wrap=True)
            stage_table.add_column("Icon", justify="left", width=3)
            stage_table.add_column("Count", no_wrap=True)

            stage_icons = {
                'init': '🔨',
                'index': '📚',
                'start': '🚀',
                'translog': '📝',
                'finalize': '🏁',
                'done': '✅'
            }

            for stage, count in stage_counts.items():
                icon = stage_icons.get(stage, '🔩')
                stage_table.add_row(stage.title(), icon, str(count))

            return Panel(
                stage_table,
                title="🎯 Recovery Stages",
                border_style="cyan",
                padding=(1, 2)
            )
        else:
            return Panel(
                Text("No stage information available", style="dim", justify="center"),
                title="🎯 Recovery Stages",
                border_style="cyan",
                padding=(1, 2)
            )

    def _create_recovery_table(self, recovery_status: Dict[str, Any]) -> Table:
        """Create detailed recovery table."""
        recovery_table = Table(
            show_header=True,
            header_style="bold white",
            expand=True,
            box=self.style_system.get_table_box() if self.style_system else None
        )
        recovery_table.add_column("📚 Index", no_wrap=True)
        recovery_table.add_column("📋 Shard", justify="center", width=8)
        recovery_table.add_column("🎯 Stage", justify="center", width=12)
        recovery_table.add_column("📤 Source Node", no_wrap=True)
        recovery_table.add_column("📥 Target Node", no_wrap=True)
        recovery_table.add_column("🔧 Type", justify="center", width=10)
        recovery_table.add_column("📊 Progress", justify="center", width=15)

        for index_name, index_data in recovery_status.items():
            shards = index_data.get('shards', [])
            for shard in shards:
                stage = shard.get('stage', '-')

                # Only show active recoveries (not DONE)
                if stage and stage.upper() == 'DONE':
                    continue

                shard_id = shard.get('id', '-')
                source = shard.get('source', {}).get('name', '-')
                target = shard.get('target', {}).get('name', '-')
                shard_type = shard.get('type', '-')
                translog_percent = shard.get('translog', {}).get('percent', '0%')

                # Determine progress and styling
                try:
                    percent_value = float(translog_percent.replace('%', '').strip())

                    # Create progress bar display
                    progress_bar = self.create_progress_bar(percent_value)

                    if percent_value >= 100:
                        row_style = "green"
                        progress_display = f"✅ {progress_bar} 100%"
                    elif percent_value >= 75:
                        row_style = "yellow"
                        progress_display = f"📊 {progress_bar} {percent_value:.1f}%"
                    elif percent_value >= 25:
                        row_style = "cyan"
                        progress_display = f"📊 {progress_bar} {percent_value:.1f}%"
                    else:
                        row_style = "red"
                        progress_display = f"📊 {progress_bar} {percent_value:.1f}%"
                except (ValueError, AttributeError):
                    progress_display = "❓ Unknown"
                    row_style = "dim"

                # Format stage with appropriate styling
                stage_styled = self._format_stage(stage)

                recovery_table.add_row(
                    index_name,
                    str(shard_id),
                    stage_styled,
                    source,
                    target,
                    shard_type,
                    progress_display,
                    style=row_style
                )

        return recovery_table

    def _format_stage(self, stage: str) -> str:
        """Format stage with appropriate styling."""
        stage_lower = stage.lower()
        if stage_lower == 'done':
            return "✅ Done"
        elif stage_lower == 'finalize':
            return "🏁 Finalize"
        elif stage_lower == 'translog':
            return "📝 Translog"
        elif stage_lower == 'index':
            return "📚 Index"
        elif stage_lower == 'init':
            return "🔨 Init"
        elif stage_lower == 'start':
            return "🚀 Start"
        else:
            return stage.title()

    def create_progress_bar(self, percent: float, width: int = 8) -> str:
        """
        Create a visual progress bar for recovery operations.

        Args:
            percent: Completion percentage (0-100)
            width: Width of the progress bar in characters

        Returns:
            Formatted progress bar string with Rich markup
        """
        filled = int((percent / 100) * width)
        empty = width - filled

        # Use theme-aware colors if available, otherwise fallback to defaults
        if self.style_system:
            success_color = self.style_system.get_semantic_style("success").replace("bold ", "")
            warning_color = self.style_system.get_semantic_style("warning").replace("bold ", "")
            error_color = self.style_system.get_semantic_style("error").replace("bold ", "")
            muted_color = self.style_system.get_semantic_style("muted").replace("bold ", "")
        else:
            success_color = "green"
            warning_color = "yellow"
            error_color = "red"
            muted_color = "dim"

        if percent >= 100:
            return f"[{success_color}]{'█' * width}[/{success_color}]"
        elif percent >= 75:
            return f"[{success_color}]{'█' * filled}[/{success_color}][{muted_color}]{'░' * empty}[/{muted_color}]"
        elif percent >= 50:
            return f"[{warning_color}]{'█' * filled}[/{warning_color}][{muted_color}]{'░' * empty}[/{muted_color}]"
        elif percent >= 25:
            return f"[orange1]{'█' * filled}[/orange1][{muted_color}]{'░' * empty}[/{muted_color}]"
        else:
            return f"[{error_color}]{'█' * filled}[/{error_color}][{muted_color}]{'░' * empty}[/{muted_color}]"
