"""
Allocation display rendering for Elasticsearch command-line tool.

This module provides allocation-related display capabilities including
allocation issues panels, allocation settings display, and allocation
status visualization.
"""

from typing import Dict, Any, Optional, List
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich.console import Console
from .style_system import StyleSystem


class AllocationRenderer:
    """
    Handles allocation-related display rendering.

    Provides methods for rendering allocation issues panels, allocation settings,
    and other allocation-related visualizations.
    """

    def __init__(self, theme_manager=None):
        """
        Initialize the allocation renderer.

        Args:
            theme_manager: Theme manager instance for styling
        """
        self.theme_manager = theme_manager
        self.style_system = StyleSystem(theme_manager) if theme_manager else None
        self.console = Console()

    def create_allocation_issues_panel(self, allocation_issues: Dict[str, Any]) -> Optional[Panel]:
        """
        Create allocation issues panel for health dashboard.

        Args:
            allocation_issues: Allocation issues data from AllocationCommands.check_allocation_issues()

        Returns:
            Panel widget for allocation issues or None if no issues
        """
        if not allocation_issues:
            return None

        # Handle both old and new allocation issues data structures
        if isinstance(allocation_issues, dict):
            # New structure from AllocationCommands
            summary = allocation_issues.get('summary', {})
            unassigned_shards = allocation_issues.get('unassigned_shards', [])
            total_issues = summary.get('total_issues', 0)
            critical_issues = summary.get('critical_issues', 0)
            warning_issues = summary.get('warning_issues', 0)

            # If no issues, don't show panel
            if total_issues == 0:
                return None
        else:
            # Old structure (list or has_issues format)
            if hasattr(allocation_issues, '__len__'):
                total_issues = len(allocation_issues)
                unassigned_shards = allocation_issues
                critical_issues = total_issues
                warning_issues = 0
            else:
                return None

        # Get theme styles and style system
        styles = self.theme_manager.get_theme_styles() if self.theme_manager else {}
        style_system = self.style_system

        # Create inner table
        table = Table.grid(padding=(0, 1))
        table.add_column(style=style_system.get_semantic_style("primary") if style_system else "bold white", no_wrap=True)
        table.add_column()

        # Determine severity using semantic styling
        if critical_issues > 0:
            severity_style = "error"
            severity_icon = "🔴"
            severity_text = "Critical"
        elif warning_issues > 0:
            severity_style = "warning"
            severity_icon = "🔶"
            severity_text = "Warning"
        else:
            severity_style = "success"
            severity_icon = "✅"
            severity_text = "Good"

        # Add allocation issue summary with semantic styling
        if style_system:
            table.add_row("🔴 Issues Found:", style_system.create_semantic_text(str(total_issues), severity_style))

            if critical_issues > 0:
                table.add_row("🔶 Critical:", style_system.create_semantic_text(str(critical_issues), "error"))

            if warning_issues > 0:
                table.add_row("⚡ Warning:", style_system.create_semantic_text(str(warning_issues), "warning"))
        else:
            # Fallback for when style_system is not available
            severity_color = "red" if critical_issues > 0 else "yellow" if warning_issues > 0 else "green"
            table.add_row("🔴 Issues Found:", Text(str(total_issues), style=f"bold {severity_color}"))

            if critical_issues > 0:
                table.add_row("🔶 Critical:", Text(str(critical_issues), style="bold red"))

            if warning_issues > 0:
                table.add_row("⚡ Warning:", Text(str(warning_issues), style="bold yellow"))

        # Show sample unassigned shards if available
        if unassigned_shards and len(unassigned_shards) > 0:
            sample_count = min(3, len(unassigned_shards))
            for i, shard in enumerate(unassigned_shards[:sample_count]):
                if isinstance(shard, dict):
                    index_name = shard.get('index', 'Unknown')
                    shard_num = shard.get('shard', '?')
                    shard_type = 'Primary' if shard.get('type') == 'p' else 'Replica'
                    shard_text = f"{index_name}[{shard_num}] ({shard_type})"
                    if style_system:
                        table.add_row(f"📋 Shard {i+1}:", style_system.create_semantic_text(shard_text, "warning"))
                    else:
                        table.add_row(f"📋 Shard {i+1}:", Text(shard_text, style="yellow"))
                else:
                    if style_system:
                        table.add_row(f"📋 Issue {i+1}:", style_system.create_semantic_text(str(shard), "warning"))
                    else:
                        table.add_row(f"📋 Issue {i+1}:", Text(str(shard), style="yellow"))

            if len(unassigned_shards) > 3:
                more_text = f"+{len(unassigned_shards) - 3} additional issues"
                if style_system:
                    table.add_row("📋 More:", style_system.create_semantic_text(more_text, "muted"))
                else:
                    table.add_row("📋 More:", Text(more_text, style="dim"))

        return Panel(
            table,
            title=f"[{styles.get('panel_styles', {}).get('title', 'bold red')}]🔶 Allocation Issues[/{styles.get('panel_styles', {}).get('title', 'bold red')}]",
            border_style=severity_color,
            padding=(1, 2)
        )

    def render_enhanced_allocation_settings(self, settings: Dict[str, Any], health_data: Dict[str, Any]) -> str:
        """
        Render allocation settings in enhanced multi-panel format.

        Args:
            settings: Cluster settings data
            health_data: Cluster health data

        Returns:
            JSON string representation of settings for reference
        """
        import json

        # Get style system for semantic styling
        style_system = self.style_system

        try:
            # Parse allocation settings
            allocation_settings = None
            exclusion_settings = None
            excluded_nodes = []

            # Check both transient and persistent settings for exclusions
            # Transient settings
            transient_exclusions = []
            if 'transient' in settings and 'cluster' in settings['transient']:
                if 'routing' in settings['transient']['cluster']:
                    if 'allocation' in settings['transient']['cluster']['routing']:
                        allocation_settings = settings['transient']['cluster']['routing']['allocation']
                        if 'exclude' in allocation_settings and '_name' in allocation_settings['exclude']:
                            exclusion_settings = allocation_settings['exclude']['_name']
                            if exclusion_settings and exclusion_settings.strip():
                                transient_exclusions = [node.strip() for node in exclusion_settings.split(',') if node.strip()]

            # Persistent settings
            persistent_exclusions = []
            persistent_allocation_settings = None
            if 'persistent' in settings and 'cluster' in settings['persistent']:
                if 'routing' in settings['persistent']['cluster']:
                    if 'allocation' in settings['persistent']['cluster']['routing']:
                        persistent_allocation_settings = settings['persistent']['cluster']['routing']['allocation']
                        if 'exclude' in persistent_allocation_settings and '_name' in persistent_allocation_settings['exclude']:
                            persistent_exclusion_settings = persistent_allocation_settings['exclude']['_name']
                            if persistent_exclusion_settings and persistent_exclusion_settings.strip():
                                persistent_exclusions = [node.strip() for node in persistent_exclusion_settings.split(',') if node.strip()]

            # Combine exclusions from both sources
            excluded_nodes = list(set(transient_exclusions + persistent_exclusions))

            # Check if allocation is enabled by looking for enable setting in either location
            allocation_enabled = True
            if allocation_settings and 'enable' in allocation_settings:
                if allocation_settings['enable'] == 'primaries':
                    allocation_enabled = False
            if persistent_allocation_settings and 'enable' in persistent_allocation_settings:
                if persistent_allocation_settings['enable'] == 'primaries':
                    allocation_enabled = False

            # Calculate statistics
            total_nodes = health_data.get('number_of_nodes', 0)
            data_nodes = health_data.get('number_of_data_nodes', 0)
            excluded_count = len(excluded_nodes)
            active_nodes = data_nodes - excluded_count

            # Create title panel - status_text and status_style now handled in subtitle

            # Create colorized subtitle with theme-based styling for statistics
            from rich.text import Text
            subtitle_rich = Text()

            # Status with appropriate color
            subtitle_rich.append("Status: ", style="default")
            if allocation_enabled:
                subtitle_rich.append("✅ Enabled", style=style_system._get_style('semantic', 'success', 'green') if style_system else "green")
            else:
                subtitle_rich.append("🔶 Disabled", style=style_system._get_style('semantic', 'warning', 'yellow') if style_system else "yellow")

            # Total nodes
            subtitle_rich.append(" | Total: ", style="default")
            subtitle_rich.append(str(total_nodes), style=style_system._get_style('semantic', 'info', 'cyan') if style_system else "cyan")

            # Data nodes
            subtitle_rich.append(" | Data: ", style="default")
            subtitle_rich.append(str(data_nodes), style=style_system._get_style('semantic', 'primary', 'bright_magenta') if style_system else "bright_magenta")

            # Excluded nodes (only if any exist)
            if excluded_count > 0:
                subtitle_rich.append(" | Excluded: ", style="default")
                subtitle_rich.append(str(excluded_count), style=style_system._get_style('semantic', 'error', 'red') if style_system else "red")

            # Active nodes
            subtitle_rich.append(" | Active: ", style="default")
            subtitle_rich.append(str(active_nodes), style=style_system._get_style('semantic', 'success', 'green') if style_system else "green")

            # Create title panel with semantic styling
            if style_system:
                title_panel = Panel(
                    style_system.create_semantic_text("🔀 Elasticsearch Allocation Settings Overview", "primary", justify="center"),
                    subtitle=subtitle_rich,
                    border_style=style_system.get_semantic_style("info"),
                    padding=(1, 2)
                )
            else:
                title_panel = Panel(
                    Text("🔀 Elasticsearch Allocation Settings Overview", style="bold cyan", justify="center"),
                    subtitle=subtitle_rich,
                    border_style="cyan",
                    padding=(1, 2)
                )

            # Create allocation status panel
            status_table = Table(show_header=False, box=None, padding=(0, 1))
            status_table.add_column("Label", style=style_system.get_semantic_style("primary") if style_system else "bold", no_wrap=True)
            status_table.add_column("Icon", justify="left", width=3)
            status_table.add_column("Value", no_wrap=True)

            if allocation_enabled:
                status_table.add_row("Allocation Status:", "✅", "Enabled (All Shards)")
                status_table.add_row("Shard Movement:", "🔄", "Primary & Replica")
            else:
                status_table.add_row("Allocation Status:", "🔶", "Disabled (Primaries Only)")
                status_table.add_row("Shard Movement:", "🔒", "Primaries Only")

            status_table.add_row("Total Nodes:", "💻", str(total_nodes))
            status_table.add_row("Data Nodes:", "💾", str(data_nodes))
            status_table.add_row("Excluded Nodes:", "❌", str(excluded_count))
            status_table.add_row("Active Nodes:", "✅", str(active_nodes))

            status_panel = Panel(
                status_table,
                title="📊 Allocation Status",
                border_style=style_system.get_semantic_style("success" if allocation_enabled else "warning") if style_system else ("green" if allocation_enabled else "yellow"),
                padding=(1, 2)
            )

            # Create exclusions panel
            if excluded_nodes:
                exclusion_content = ""
                if style_system:
                    error_style = style_system.get_semantic_style("error")
                    for i, node in enumerate(excluded_nodes, 1):
                        exclusion_content += f"[{error_style}]{i}. {node}[/{error_style}]\n"
                else:
                    for i, node in enumerate(excluded_nodes, 1):
                        exclusion_content += f"[bold red]{i}.[/bold red] [red]{node}[/red]\n"
                exclusion_content = exclusion_content.rstrip()

                exclusions_panel = Panel(
                    exclusion_content,
                    title="❌ Excluded Nodes",
                    border_style=style_system.get_semantic_style("error") if style_system else "red",
                    padding=(1, 2)
                )
            else:
                exclusions_panel = Panel(
                    Text("✅ No nodes are currently excluded from allocation", style="bold green", justify="center"),
                    title="❌ Excluded Nodes",
                    border_style="green",
                    padding=(1, 2)
                )

            # Create configuration details panel
            config_table = Table(show_header=False, box=None, padding=(0, 1))
            config_table.add_column("Setting", style="bold", no_wrap=True)
            config_table.add_column("Icon", justify="left", width=3)
            config_table.add_column("Value", no_wrap=True)

            if allocation_settings:
                for key, value in allocation_settings.items():
                    if key == 'exclude':
                        continue  # Skip - handled in exclusions panel
                    elif key == 'enable':
                        icon = "✅" if value == 'all' else "🔶" if value == 'primaries' else "❌"
                        display_value = "All Shards" if value == 'all' else "Primaries Only" if value == 'primaries' else "Disabled"
                        config_table.add_row("Enable Setting:", icon, display_value)
                    else:
                        config_table.add_row(f"{key.title()}:", "🔩", str(value))
            else:
                config_table.add_row("Configuration:", "📋", "Default Settings (No Custom Config)")

            config_panel = Panel(
                config_table,
                title="🔩 Configuration Details",
                border_style="blue",
                padding=(1, 2)
            )

            # Create quick actions panel
            actions_table = Table(show_header=False, box=None, padding=(0, 1))
            actions_table.add_column("Action", style="bold magenta", no_wrap=True)
            actions_table.add_column("Command", style="dim white")

            actions_table.add_row("Enable allocation:", "./escmd.py allocation enable")
            actions_table.add_row("Disable allocation:", "./escmd.py allocation disable")
            actions_table.add_row("Exclude node:", "./escmd.py allocation exclude add <hostname>")
            actions_table.add_row("Remove exclusion:", "./escmd.py allocation exclude remove <hostname>")
            actions_table.add_row("Reset exclusions:", "./escmd.py allocation exclude reset")

            actions_panel = Panel(
                actions_table,
                title="🚀 Quick Actions",
                border_style="magenta",
                padding=(1, 2)
            )

            # Display everything with enhanced layout
            print()
            self.console.print(title_panel)
            print()

            # Create two-column layout for main panels - Status and Quick Actions
            self.console.print(Columns([status_panel, actions_panel], expand=True))
            print()

            # Configuration details panel spans full width
            self.console.print(config_panel)
            print()

            # Excluded nodes panel at the bottom, spans full width
            self.console.print(exclusions_panel)
            print()

        except Exception as e:
            self.console.print(f"[red]❌ Error retrieving allocation settings: {str(e)}[/red]")

        # Return the full JSON for reference
        return json.dumps(settings)
