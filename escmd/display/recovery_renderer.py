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

    def _sem(self, semantic: str, fallback: str = "white") -> str:
        """Return a semantic style from the style system."""
        if self.style_system:
            return self.style_system.get_semantic_style(semantic)
        return fallback

    def _ts(self) -> str:
        """Return themed primary style for title bar text."""
        ss = self.style_system
        return ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'

    def render_enhanced_recovery_status(self, recovery_status: Dict[str, Any]) -> None:
        """
        Render enhanced recovery status with Rich formatting.

        Args:
            recovery_status: Recovery status data from HealthCommands.get_shard_recovery()
        """
        ts = self._ts()

        if not recovery_status:
            panel = Panel(
                Text("✅ No Active Recovery Operations", style=self._sem("success", "bold green"), justify="center"),
                title=f"[{ts}]🔄 Cluster Recovery Status[/{ts}]",
                border_style=self._border(),
                padding=(1, 2)
            )
            print()
            self.console.print(panel)
            print()
            return

        # Calculate recovery statistics
        stats = self._calculate_recovery_statistics(recovery_status)

        if stats['active_recoveries'] == 0:
            panel = Panel(
                Text("✅ No Active Recovery Operations", style=self._sem("success", "bold green"), justify="center"),
                title=f"[{ts}]🔄 Cluster Recovery Status[/{ts}]",
                border_style=self._border(),
                padding=(1, 2)
            )
            print()
            self.console.print(panel)
            print()
            return

        # --- Title panel (standard pattern) ---
        ss = self.style_system
        active = stats['active_recoveries']
        total = stats['total_shards']
        completion = (stats['completed_shards'] / total * 100) if total > 0 else 0

        # Body: status centered
        status_text = f"🔶 {active} Recovery Operation{'s' if active != 1 else ''} In Progress"

        # Subtitle bar
        subtitle_rich = Text()
        subtitle_rich.append("Active: ", style="default")
        subtitle_rich.append(str(active), style=ss._get_style('semantic', 'warning', 'yellow') if ss else "yellow")
        subtitle_rich.append(" | Total Shards: ", style="default")
        subtitle_rich.append(str(total), style=ss._get_style('semantic', 'info', 'cyan') if ss else "cyan")
        subtitle_rich.append(" | Completion: ", style="default")
        if completion >= 75:
            subtitle_rich.append(f"{completion:.1f}%", style=ss._get_style('semantic', 'success', 'green') if ss else "green")
        elif completion >= 25:
            subtitle_rich.append(f"{completion:.1f}%", style=ss._get_style('semantic', 'warning', 'yellow') if ss else "yellow")
        else:
            subtitle_rich.append(f"{completion:.1f}%", style=ss._get_style('semantic', 'error', 'red') if ss else "red")

        if stats['recovery_types']:
            subtitle_rich.append(" | Types: ", style="default")
            type_parts = []
            for rtype, count in stats['recovery_types'].items():
                type_parts.append(f"{count} {rtype}")
            subtitle_rich.append(", ".join(type_parts), style=ss._get_style('semantic', 'primary', 'bright_magenta') if ss else "bright_magenta")

        title_panel = Panel(
            Text(status_text, style="bold yellow", justify="center"),
            title=f"[{ts}]🔄 Cluster Recovery Status[/{ts}]",
            subtitle=subtitle_rich,
            border_style="yellow",
            padding=(1, 2)
        )

        # --- Stages & Types panel (left) ---
        stages_table = Table(show_header=False, box=None, padding=(0, 1))
        stages_table.add_column("Label", style="bold", no_wrap=True)
        stages_table.add_column("Icon", justify="left", width=3)
        stages_table.add_column("Value", no_wrap=True)

        stage_icons = {
            'init': '🔨', 'index': '📚', 'start': '🚀',
            'translog': '📝', 'finalize': '🏁', 'done': '✅'
        }

        for stage, count in stats['stage_counts'].items():
            icon = stage_icons.get(stage.lower(), '🔩')
            stages_table.add_row(f"{stage.title()}:", icon, str(count))

        if stats['recovery_types']:
            stages_table.add_row("", "", "")
            for rtype, count in stats['recovery_types'].items():
                if rtype == 'peer':
                    stages_table.add_row("Peer Recovery:", "🔄", str(count))
                elif rtype == 'existing_store':
                    stages_table.add_row("Existing Store:", "💾", str(count))
                else:
                    stages_table.add_row(f"{rtype.title()}:", "🔧", str(count))

        stages_panel = Panel(
            stages_table,
            title=f"[{self._title_style()}]🎯 Stages & Types[/{self._title_style()}]",
            border_style=self._border(),
            padding=(1, 2)
        )

        # --- Progress panel (right) ---
        progress_table = Table(show_header=False, box=None, padding=(0, 1))
        progress_table.add_column("Label", style="bold", no_wrap=True)
        progress_table.add_column("Icon", justify="left", width=3)
        progress_table.add_column("Value", no_wrap=True)

        # Calculate per-shard progress for fastest/slowest/average
        shard_progress = self._collect_shard_progress(recovery_status)

        if shard_progress:
            fastest = max(shard_progress, key=lambda x: x['percent'])
            slowest = min(shard_progress, key=lambda x: x['percent'])
            avg_pct = sum(s['percent'] for s in shard_progress) / len(shard_progress)

            progress_table.add_row(
                "Fastest:", "🚀",
                Text(f"{fastest['label']} {fastest['percent']:.1f}%",
                     style=ss.get_semantic_style("success") if ss else "green")
            )
            progress_table.add_row(
                "Slowest:", "🐢",
                Text(f"{slowest['label']} {slowest['percent']:.1f}%",
                     style=ss.get_semantic_style("warning") if ss else "yellow")
            )
            progress_table.add_row(
                "Average:", "📊",
                Text(f"{avg_pct:.1f}%",
                     style=ss.get_semantic_style("info") if ss else "cyan")
            )
        else:
            progress_table.add_row("Progress:", "📊", "Calculating...")

        progress_panel = Panel(
            progress_table,
            title=f"[{self._title_style()}]📈 Progress[/{self._title_style()}]",
            border_style=self._border(),
            padding=(1, 2)
        )

        # --- Recovery table ---
        recovery_table = self._create_recovery_table(recovery_status)

        # --- Render layout ---
        print()
        self.console.print(title_panel)
        print()
        self.console.print(Columns([stages_panel, progress_panel], expand=True))
        print()
        self.console.print(Panel(
            recovery_table,
            title=f"[{self._title_style()}]🔄 Active Recovery Operations[/{self._title_style()}]",
            border_style=self._border(),
            padding=(1, 2)
        ))
        print()

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

                stage = shard.get('stage', 'unknown')
                if stage and stage.upper() != 'DONE':
                    active_recoveries += 1
                    shard_type = shard.get('type', 'unknown')
                    recovery_types[shard_type] = recovery_types.get(shard_type, 0) + 1
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1

                translog_percent = shard.get('translog', {}).get('percent', '0%')
                try:
                    percent_value = float(translog_percent.replace('%', '').strip())
                    if percent_value >= 100:
                        completed_shards += 1
                except Exception:
                    pass

        return {
            'total_shards': total_shards,
            'completed_shards': completed_shards,
            'active_recoveries': active_recoveries,
            'recovery_types': recovery_types,
            'stage_counts': stage_counts
        }

    def _collect_shard_progress(self, recovery_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect per-shard progress for active recoveries."""
        progress = []
        for index_name, index_data in recovery_status.items():
            for shard in index_data.get('shards', []):
                stage = shard.get('stage', '')
                if stage and stage.upper() == 'DONE':
                    continue
                translog_percent = shard.get('translog', {}).get('percent', '0%')
                try:
                    pct = float(translog_percent.replace('%', '').strip())
                except Exception:
                    pct = 0.0
                shard_id = shard.get('id', '?')
                progress.append({
                    'label': f"{index_name}[{shard_id}]",
                    'percent': pct
                })
        return progress

    def _create_recovery_table(self, recovery_status: Dict[str, Any]) -> Table:
        """Create detailed recovery table."""
        recovery_table = Table(
            show_header=True,
            header_style=self.theme_manager.get_theme_styles().get("header_style", "bold white") if self.theme_manager else "bold white",
            expand=True,
            box=self.style_system.get_table_box() if self.style_system else None
        )
        recovery_table.add_column("Index", no_wrap=True)
        recovery_table.add_column("Shard", justify="center", width=6)
        recovery_table.add_column("Stage", justify="center", width=12)
        recovery_table.add_column("Source", no_wrap=True)
        recovery_table.add_column("Target", no_wrap=True)
        recovery_table.add_column("Type", justify="center", width=14)
        recovery_table.add_column("Progress", justify="center", width=15)

        for index_name, index_data in recovery_status.items():
            shards = index_data.get('shards', [])
            for shard in shards:
                stage = shard.get('stage', '-')

                if stage and stage.upper() == 'DONE':
                    continue

                shard_id = shard.get('id', '-')
                source = shard.get('source', {}).get('name', '-')
                target = shard.get('target', {}).get('name', '-')
                shard_type = shard.get('type', '-')
                translog_percent = shard.get('translog', {}).get('percent', '0%')

                try:
                    percent_value = float(translog_percent.replace('%', '').strip())
                    progress_bar = self.create_progress_bar(percent_value)

                    if percent_value >= 100:
                        row_style = "green"
                        progress_display = f"{progress_bar} 100%"
                    elif percent_value >= 75:
                        row_style = "yellow"
                        progress_display = f"{progress_bar} {percent_value:.1f}%"
                    elif percent_value >= 25:
                        row_style = "cyan"
                        progress_display = f"{progress_bar} {percent_value:.1f}%"
                    else:
                        row_style = "red"
                        progress_display = f"{progress_bar} {percent_value:.1f}%"
                except (ValueError, AttributeError):
                    progress_display = "Unknown"
                    row_style = "dim"

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
        """Create a visual progress bar for recovery operations."""
        filled = int((percent / 100) * width)
        empty = width - filled

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
