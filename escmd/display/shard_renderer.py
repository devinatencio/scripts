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
            title_style = "bold yellow"
            border_style = "yellow"
        else:
            status_text = "✅ Good - All Shards Assigned"
            title_style = "bold cyan"
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
        return Panel(
            Text(f"📊 Elasticsearch Shards Overview \n {status_text}", style=title_style, justify="center"),
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
            title="📊 Elasticsearch Shards",
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

        # Add rows to table
        for shard_info in shards_info:
            index_name = str(shard_info.get("index", "N/A"))
            shard_state = str(shard_info.get("state", "UNKNOWN"))

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

            # Apply styles to the row data
            from rich.text import Text
            table.add_row(
                Text(shard_state, style=state_style),
                Text(shard_type, style=type_style),
                index_name,
                str(shard_info.get("shard", "N/A")),
                str(docs_count),
                str(store_size),
                str(node_name)
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
        """
        Create summary panel for colocation analysis.

        Args:
            results: Colocation analysis results

        Returns:
            Panel with summary information
        """
        total_issues = len(results.get('colocated_indices', []))
        total_indices = len(results.get('all_indices', [])) if 'all_indices' in results else 0

        summary_text = f"Found {total_issues} indices with colocation issues"
        if total_indices > 0:
            summary_text += f" out of {total_indices} total indices analyzed"

        return Panel(
            Text(summary_text, style=self.style_system._get_style('semantic', 'neutral', 'white') if self.style_system else 'white'),
            title=Text("Shard Colocation Analysis", style=self.style_system._get_style('semantic', 'primary', 'cyan') if self.style_system else 'cyan'),
            border_style=self.style_system._get_style('semantic', 'info', 'blue') if self.style_system else 'blue',
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
            details.append(Panel(
                Text("No colocation issues found. All primary and replica shards are properly distributed.",
                     style=self.style_system._get_style('semantic', 'success', 'green') if self.style_system else 'green'),
                title=Text("Results", style=self.style_system._get_style('semantic', 'primary', 'cyan') if self.style_system else 'cyan'),
                border_style=self.style_system._get_style('semantic', 'success', 'green') if self.style_system else 'green',
                padding=(1, 2)
            ))
            return details

        # Create table for colocation issues
        table = Table(
            title="Indices with Colocation Issues",
            title_style=self.style_system._get_style('semantic', 'primary', 'cyan') if self.style_system else 'cyan',
            border_style=self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else 'yellow',
            header_style=self.style_system._get_style('semantic', 'primary', 'bold white') if self.style_system else 'bold white',
            show_header=True,
            show_lines=True
        )

        table.add_column("Index", style=self.style_system._get_style('semantic', 'info', 'cyan') if self.style_system else 'cyan', min_width=30)
        table.add_column("Affected Shards", style=self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else 'yellow', min_width=15)
        table.add_column("Nodes with Issues", style=self.style_system._get_style('semantic', 'info', 'cyan') if self.style_system else 'cyan', min_width=20)

        for index_info in colocated_indices:
            index_name = index_info.get('index', 'N/A')
            shard_count = str(len(index_info.get('colocated_shards', [])))
            nodes = ', '.join(index_info.get('affected_nodes', []))

            table.add_row(
                Text(index_name, style=self.style_system._get_style('semantic', 'info', 'cyan') if self.style_system else 'cyan'),
                Text(shard_count, style=self.style_system._get_style('semantic', 'warning', 'yellow') if self.style_system else 'yellow'),
                Text(nodes, style=self.style_system._get_style('semantic', 'info', 'cyan') if self.style_system else 'cyan')
            )

        details.append(table)

        # Add recommendations panel
        recommendations = Panel(
            Text(
                "Recommendations:\n"
                "• Consider using allocation filters to separate primary and replica shards\n"
                "• Review your cluster's allocation strategy\n"
                "• Check if you have sufficient nodes for proper shard distribution",
                style=self.style_system._get_style('semantic', 'neutral', 'white') if self.style_system else 'white'
            ),
            title=Text("Recommendations", style=self.style_system._get_style('semantic', 'primary', 'cyan') if self.style_system else 'cyan'),
            border_style=self.style_system._get_style('semantic', 'info', 'blue') if self.style_system else 'blue',
            padding=(1, 2)
        )
        details.append(recommendations)

        return details
