"""
Shard display rendering for Elasticsearch command-line tool.

This module provides shard-related display capabilities including
shard tables, colocation analysis results, and shard status visualization.
"""

from typing import Dict, Any, Optional, List, Union
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.console import Console
from .style_system import StyleSystem


class ShardRenderer:
    """
    Handles shard-related display rendering.

    Provides methods for rendering shard tables, colocation analysis,
    and other shard-related visualizations.
    """

    def __init__(self, theme_manager=None):
        """
        Initialize the shard renderer.

        Args:
            theme_manager: Theme manager for styling
        """
        self.theme_manager = theme_manager
        self.style_system = StyleSystem(theme_manager) if theme_manager else None
        self.console = Console()

    def print_table_shards(self, shards_info: List[Dict[str, Any]],
                          cluster_all_settings: Dict[str, Any] = None,
                          cluster_indices_hot_indexes: List[str] = None,
                          use_pager: bool = False) -> None:
        """
        Print a formatted table of shards information matching the original format.

        Args:
            shards_info: List of shard dictionaries containing shard data
            cluster_all_settings: Cluster settings for additional context
            cluster_indices_hot_indexes: List of hot indices
            use_pager: Whether to use pager for output
        """
        if not shards_info:
            self._show_no_shards_message()
            return

        # Initialize defaults
        cluster_all_settings = cluster_all_settings or {}
        cluster_indices_hot_indexes = cluster_indices_hot_indexes or []

        # Calculate statistics
        stats = self._calculate_shard_statistics(shards_info, cluster_all_settings, cluster_indices_hot_indexes)

        # Get theme styles from configuration
        styles = self.theme_manager.get_theme_styles() if self.theme_manager else {}

        # Create title panel
        title_panel = self._create_title_panel(stats, styles)

        # Create detailed table
        table = self._create_detailed_shards_table(shards_info, cluster_all_settings, cluster_indices_hot_indexes, styles)

        # Display results
        if use_pager:
            with self.console.pager():
                self.console.print(title_panel)
                self.console.print()
                self.console.print(table)
        else:
            self.console.print(title_panel)
            self.console.print()
            self.console.print(table)

    def _calculate_shard_statistics(self, shards_info: List[Dict[str, Any]],
                                  cluster_all_settings: Dict[str, Any],
                                  cluster_indices_hot_indexes: List[str]) -> Dict[str, Any]:
        """Calculate shard statistics for the header panel."""
        stats = {
            'total': len(shards_info),
            'state_counts': {},
            'type_counts': {'primary': 0, 'replica': 0},
            'hot_count': 0,
            'frozen_count': 0
        }

        for shard_info in shards_info:
            # Count states
            state = shard_info.get('state', 'UNKNOWN')
            stats['state_counts'][state] = stats['state_counts'].get(state, 0) + 1

            # Count types
            if shard_info.get('prirep') == 'p':
                stats['type_counts']['primary'] += 1
            else:
                stats['type_counts']['replica'] += 1

            # Count hot indices
            if shard_info['index'] in cluster_indices_hot_indexes:
                stats['hot_count'] += 1

            # Count frozen indices
            index_settings = cluster_all_settings.get(shard_info['index'], {})
            if index_settings:
                frozen_status = index_settings.get('settings', {}).get('index', {}).get('frozen', False)
                if frozen_status == "true":
                    stats['frozen_count'] += 1

        return stats

    def _create_title_panel(self, stats: Dict[str, Any], styles: Dict[str, Any]) -> Panel:
        """Create the title panel with overview and statistics."""
        # Determine status based on unassigned shards
        unassigned_count = stats['state_counts'].get('UNASSIGNED', 0)
        if unassigned_count > 0:
            status_text = "🔶 Warning - Unassigned Shards Detected"
            title_style = f"bold {self.style_system.get_semantic_style('warning')}" if self.style_system else "bold yellow"
            border_style = self.style_system.get_semantic_style('warning') if self.style_system else "yellow"
        else:
            status_text = "✅ Good - All Shards Assigned"
            title_style = f"bold {self.style_system._get_style('semantic', 'info', 'cyan')}" if self.style_system else "bold cyan"
            border_style = styles.get('border_style', 'white')

        # Create colorized subtitle with theme-based styling for statistics
        subtitle_rich = Text()
        subtitle_rich.append("Total: ", style="default")
        subtitle_rich.append(str(stats['total']), style=self.style_system._get_style('semantic', 'info', 'cyan') if self.style_system else "cyan")
        subtitle_rich.append(" | Started: ", style="default")
        subtitle_rich.append(str(stats['state_counts'].get('STARTED', 0)), style=self.style_system._get_style('semantic', 'success', 'green') if self.style_system else "green")

        if stats['state_counts'].get('INITIALIZING', 0) > 0:
            subtitle_rich.append(" | Initializing: ", style="default")
            subtitle_rich.append(str(stats['state_counts'].get('INITIALIZING', 0)), style=self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else "yellow")

        if stats['state_counts'].get('RELOCATING', 0) > 0:
            subtitle_rich.append(" | Relocating: ", style="default")
            subtitle_rich.append(str(stats['state_counts'].get('RELOCATING', 0)), style=self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else "yellow")

        if unassigned_count > 0:
            subtitle_rich.append(" | Unassigned: ", style="default")
            subtitle_rich.append(str(unassigned_count), style=self.style_system._get_style('semantic', 'error', 'red') if self.style_system else "red")

        subtitle_rich.append(" | Primary: ", style="default")
        subtitle_rich.append(str(stats['type_counts']['primary']), style=self.style_system._get_style('semantic', 'primary', 'bright_magenta') if self.style_system else "bright_magenta")
        subtitle_rich.append(" | Replica: ", style="default")
        subtitle_rich.append(str(stats['type_counts']['replica']), style=self.style_system._get_style('semantic', 'secondary', 'bright_blue') if self.style_system else "bright_blue")

        if stats['hot_count'] > 0:
            subtitle_rich.append(" | Hot: ", style="default")
            subtitle_rich.append(str(stats['hot_count']), style=self.style_system._get_style('semantic', 'primary', 'bright_magenta') if self.style_system else "bright_magenta")

        if stats['frozen_count'] > 0:
            subtitle_rich.append(" | Frozen: ", style="default")
            subtitle_rich.append(str(stats['frozen_count']), style=self.style_system._get_style('semantic', 'secondary', 'bright_blue') if self.style_system else "bright_blue")

        # Create title panel
        ts = self.style_system._get_style('semantic', 'primary', 'bold cyan') if self.style_system else 'bold cyan'
        return Panel(
            Text(status_text, style=title_style, justify="center"),
            title=f"[{ts}]📊 Elasticsearch Shards Overview[/{ts}]",
            subtitle=subtitle_rich,
            border_style=border_style,
            padding=(1, 2)
        )

    def _create_detailed_shards_table(self, shards_info: List[Dict[str, Any]],
                                    cluster_all_settings: Dict[str, Any],
                                    cluster_indices_hot_indexes: List[str],
                                    styles: Dict[str, Any]) -> Table:
        """Create the detailed shards table with emoji headers."""
        # Create enhanced shards table
        table = Table(
            show_header=True,
            header_style=styles.get('header_style', 'white'),
            expand=True,
            box=self.style_system.get_table_box() if self.style_system else None
        )

        table.add_column("🔄 State", justify="left", width=12)
        table.add_column("🔀 Type", justify="left", width=8)
        table.add_column("📋 Index Name", no_wrap=True)
        table.add_column("🔢 Shard", justify="center", width=8)
        table.add_column("📊 Documents", justify="right", width=12)
        table.add_column("💾 Store", justify="right", width=10)
        table.add_column("💻 Node", no_wrap=True)

        # Add rows to table — group-by-index zebra striping, UNASSIGNED rows get red background
        current_index_group = None
        group_counter = 0

        for shard_info in shards_info:
            raw_index = str(shard_info.get("index", "N/A"))
            index_name = raw_index
            shard_state = str(shard_info.get("state", "UNKNOWN"))

            # Track index group changes for zebra striping
            if raw_index != current_index_group:
                current_index_group = raw_index
                group_counter += 1

            # Add hot/frozen indicators
            if index_name in cluster_indices_hot_indexes:
                index_name = f"{index_name} 🔥"

            index_settings = cluster_all_settings.get(shard_info.get('index'), {})
            if index_settings:
                frozen_status = index_settings.get('settings', {}).get('index', {}).get('frozen', False)
                if frozen_status == "true":
                    index_name = f"{index_name} 🧊"

            # Format values and apply theme styles
            shard_type = "Primary" if shard_info.get("prirep") == "p" else "Replica"

            # Get theme-based styles for state and type
            state_style = self._get_themed_state_style(shard_state, styles)
            type_style = self._get_themed_type_style(shard_info.get("prirep"), styles)

            # Format document count
            docs_count = shard_info.get("docs")
            if docs_count and docs_count != "-" and docs_count != "null" and docs_count is not None:
                try:
                    docs_count = f"{int(docs_count):,}"
                except:
                    docs_count = "-"
            else:
                docs_count = "-"

            # Format store size
            store_size = shard_info.get("store")
            if store_size and store_size != "-" and store_size != "null" and store_size is not None:
                store_size = str(store_size)
            else:
                store_size = "-"

            # Format node name
            node_name = shard_info.get("node")
            if node_name and node_name != "-" and node_name != "null" and node_name is not None:
                node_name = str(node_name)
            else:
                node_name = "-"

            # Determine row background:
            # UNASSIGNED always gets a red background to stand out;
            # otherwise alternate by index group for visual grouping.
            if shard_state == "UNASSIGNED":
                error_color = self.style_system._get_style('table_styles', 'row_styles.critical_health', 'dark_red') if self.style_system else 'dark_red'
                row_style = f"on {error_color}"
            else:
                zebra = self.style_system.get_zebra_style(group_counter) if self.style_system else None
                row_style = zebra  # None = default background for even groups

            table.add_row(
                Text(shard_state, style=state_style),
                Text(shard_type, style=type_style),
                index_name,
                str(shard_info.get("shard", "N/A")),
                str(docs_count),
                str(store_size),
                str(node_name),
                style=row_style
            )

        return table

    def _get_themed_state_style(self, state: str, styles: Dict[str, Any]) -> str:
        """Get themed style for shard state."""
        state_styles = styles.get('state_styles', {})
        state_config = state_styles.get(state, state_styles.get('default', {}))
        return state_config.get('text', 'white')

    def _get_themed_type_style(self, prirep: str, styles: Dict[str, Any]) -> str:
        """Get themed style for shard type."""
        type_styles = styles.get('type_styles', {})
        if prirep == 'p':
            type_config = type_styles.get('primary', {})
        else:
            type_config = type_styles.get('replica', {})
        return type_config.get('text', 'white')

    def print_shard_colocation_results(self, colocation_results: Dict[str, Any],
                                     use_pager: bool = False,
                                     console: Console = None,
                                     theme_manager=None) -> None:
        """
        Print shard colocation analysis results.

        Args:
            colocation_results: Results from shard colocation analysis
            use_pager: Whether to use pager for output
            console: Console instance for output
            theme_manager: Theme manager for styling
        """
        if console is None:
            console = self.console

        # Create summary panel
        summary_panel = self._create_colocation_summary_panel(colocation_results)

        # Create detailed results
        details_content = self._create_colocation_details(colocation_results)

        # Combine summary and details
        output_content = [summary_panel]
        if details_content:
            output_content.extend(details_content)

        # Display results
        if use_pager:
            with console.pager():
                for content in output_content:
                    console.print(content)
                    console.print()  # Add spacing
        else:
            for content in output_content:
                console.print(content)
                console.print()  # Add spacing

    def show_unassigned_shards_message(self, location: str = "") -> None:
        """
        Show message when no unassigned shards are found.

        Args:
            location: Location context for the message
        """
        title = f'Results: Shards [{location}]' if location else 'Results: Shards'
        message = 'There was no unassigned shards found in cluster.'

        panel = Panel(
            Text(message, style=self.style_system._get_style('semantic', 'neutral', 'white') if self.style_system else 'white'),
            title=Text(title, style=self.style_system._get_style('semantic', 'info', 'blue') if self.style_system else 'blue'),
            border_style=self.style_system._get_style('semantic', 'info', 'blue') if self.style_system else 'blue',
            padding=(1, 2)
        )

        self.console.print(panel)

    def _show_no_shards_message(self) -> None:
        """Show message when no shards are found."""
        panel = Panel(
            Text("No shards found matching the specified criteria.",
                 style=self.style_system._get_style('semantic', 'neutral', 'white') if self.style_system else 'white'),
            title=Text("Shards", style=self.style_system._get_style('semantic', 'primary', 'cyan') if self.style_system else 'cyan'),
            border_style=self.style_system._get_style('semantic', 'info', 'blue') if self.style_system else 'blue',
            padding=(1, 2)
        )
        self.console.print(panel)

    def _create_colocation_summary_panel(self, results: Dict[str, Any]) -> Panel:
        """Create summary panel for colocation analysis."""
        ss = self.style_system
        total_issues = len(results.get('colocated_indices', []))
        total_indices = len(results.get('all_indices', [])) if 'all_indices' in results else 0

        # Subtitle bar with themed colors
        from rich.text import Text as SubText
        subtitle_rich = SubText()
        subtitle_rich.append("Analyzed: ", style="default")
        subtitle_rich.append(str(total_indices) if total_indices else "all", style=ss._get_style('semantic', 'info', 'cyan') if ss else 'cyan')
        subtitle_rich.append(" | Issues: ", style="default")
        if total_issues > 0:
            subtitle_rich.append(str(total_issues), style=ss._get_style('semantic', 'error', 'red') if ss else 'red')
        else:
            subtitle_rich.append(str(total_issues), style=ss._get_style('semantic', 'success', 'green') if ss else 'green')

        # Body: status centered
        ts = ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'
        if total_issues == 0:
            body = Text("✅ No Colocation Issues - All Shards Properly Distributed", style="bold green", justify="center")
            border = ss._get_style('table_styles', 'border_style', 'cyan') if ss else 'cyan'
        else:
            issue_word = "Index" if total_issues == 1 else "Indices"
            body = Text(f"🔶 {total_issues} {issue_word} With Colocation Issues", style="bold yellow", justify="center")
            border = "yellow"

        return Panel(
            body,
            title=f"[{ts}]🔍 Shard Colocation Analysis[/{ts}]",
            subtitle=subtitle_rich,
            border_style=border,
            padding=(1, 2)
        )

    def _create_colocation_details(self, results: Dict[str, Any]) -> List[Union[Table, Panel]]:
        """
        Create detailed colocation results.

        Args:
            results: Colocation analysis results

        Returns:
            List of renderable objects for detailed results
        """
        details = []
        colocated_indices = results.get('colocated_indices', [])

        if not colocated_indices:
            return details  # summary panel already covers the no-issues case

        # Create table for colocation issues
        ss = self.style_system
        table = Table(
            title="Indices with Colocation Issues",
            title_style=ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan',
            border_style=ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow',
            header_style=ss._get_style('semantic', 'primary', 'bold white') if ss else 'bold white',
            show_header=True,
            show_lines=False,
            box=ss.get_table_box() if ss else None,
            expand=True
        )

        table.add_column("Index", style=ss._get_style('semantic', 'info', 'cyan') if ss else 'cyan', min_width=30)
        table.add_column("Affected Shards", style=ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow', justify="center", min_width=15)
        table.add_column("Nodes with Issues", style=ss._get_style('semantic', 'info', 'cyan') if ss else 'cyan', min_width=20)

        affected_nodes_all = set()
        for index_info in colocated_indices:
            index_name = index_info.get('index', 'N/A')
            shard_count = str(len(index_info.get('colocated_shards', [])))
            nodes = index_info.get('affected_nodes', [])
            affected_nodes_all.update(nodes)

            table.add_row(
                Text(index_name, style=ss._get_style('semantic', 'info', 'cyan') if ss else 'cyan'),
                Text(shard_count, style=ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'),
                Text(', '.join(nodes), style=ss._get_style('semantic', 'info', 'cyan') if ss else 'cyan')
            )

        details.append(table)

        # Contextual recommendations based on actual findings
        ts = ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan'
        border = ss._get_style('table_styles', 'border_style', 'blue') if ss else 'blue'
        warning_style = ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'
        muted_style = ss._get_style('semantic', 'muted', 'dim') if ss else 'dim'

        from rich.table import Table as InnerTable
        from rich.align import Align
        rec_grid = InnerTable(show_header=False, box=None, padding=(0, 2))
        rec_grid.add_column(justify="center", width=3)
        rec_grid.add_column(style=ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan')

        rec_grid.add_row("•", f"Review allocation on {len(affected_nodes_all)} affected node{'s' if len(affected_nodes_all) != 1 else ''}: {', '.join(sorted(affected_nodes_all))}")
        rec_grid.add_row("•", "Use allocation filters to separate primary and replica shards onto different nodes")
        if len(colocated_indices) > 1:
            rec_grid.add_row("•", f"Consider adding nodes — {len(colocated_indices)} indices are affected, suggesting insufficient node count for replication")
        rec_grid.add_row("•", "Run ./escmd.py shards to inspect current shard placement in detail")

        details.append(Panel(
            Align.center(rec_grid),
            title=f"[{ts}]Recommendations[/{ts}]",
            border_style=border,
            padding=(1, 2)
        ))

        return details
