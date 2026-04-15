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
        Render allocation settings in condensed multi-panel format.

        Layout: Title panel + two side-by-side panels (Status & Quick Actions).
        Configuration and exclusion details are folded into the status panel.

        Args:
            settings: Cluster settings data
            health_data: Cluster health data

        Returns:
            JSON string representation of settings for reference
        """
        import json

        style_system = self.style_system

        try:
            # Parse allocation settings
            allocation_settings = None
            excluded_nodes = []

            # Check transient settings
            transient_exclusions = []
            if 'transient' in settings and 'cluster' in settings['transient']:
                if 'routing' in settings['transient']['cluster']:
                    if 'allocation' in settings['transient']['cluster']['routing']:
                        allocation_settings = settings['transient']['cluster']['routing']['allocation']
                        if 'exclude' in allocation_settings and '_name' in allocation_settings['exclude']:
                            exclusion_settings = allocation_settings['exclude']['_name']
                            if exclusion_settings and exclusion_settings.strip():
                                transient_exclusions = [node.strip() for node in exclusion_settings.split(',') if node.strip()]

            # Check persistent settings
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

            # Combine exclusions
            excluded_nodes = list(set(transient_exclusions + persistent_exclusions))

            # Determine allocation state
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

            # --- Title panel with status data as body ---
            from rich.text import Text
            from rich.table import Table as InnerTable

            ts = style_system._get_style('semantic', 'primary', 'bold cyan') if style_system else 'bold cyan'
            _title = self.theme_manager.get_themed_style("panel_styles", "title", "bold white") if self.theme_manager else "bold white"

            # Body: allocation status centered
            if allocation_enabled:
                status_text = "✅ Enabled - All Shards Allocated"
                body_style = "bold green"
                border_style = style_system._get_style('table_styles', 'border_style', 'cyan') if style_system else "cyan"
            else:
                status_text = "🔶 Disabled - Primaries Only"
                body_style = "bold yellow"
                border_style = "yellow"

            # Subtitle: node stats bar
            subtitle_rich = Text()
            subtitle_rich.append("Total Nodes: ", style="default")
            subtitle_rich.append(str(total_nodes), style=style_system._get_style('semantic', 'info', 'cyan') if style_system else "cyan")
            subtitle_rich.append(" | Data: ", style="default")
            subtitle_rich.append(str(data_nodes), style=style_system._get_style('semantic', 'primary', 'bright_magenta') if style_system else "bright_magenta")
            if excluded_count > 0:
                subtitle_rich.append(" | Excluded: ", style="default")
                subtitle_rich.append(str(excluded_count), style=style_system._get_style('semantic', 'error', 'red') if style_system else "red")
            subtitle_rich.append(" | Active: ", style="default")
            subtitle_rich.append(str(active_nodes), style=style_system._get_style('semantic', 'success', 'green') if style_system else "green")

            # Build body table with status data
            body_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            body_table.add_column("Label", style="bold", no_wrap=True)
            body_table.add_column("Icon", justify="left", width=3)
            body_table.add_column("Value", no_wrap=True)

            if allocation_enabled:
                body_table.add_row("Allocation Status:", "✅", "Enabled (All Shards)")
                body_table.add_row("Shard Movement:", "🔄", "Primary & Replica")
            else:
                body_table.add_row("Allocation Status:", "🔶", "Disabled (Primaries Only)")
                body_table.add_row("Shard Movement:", "🔒", "Primaries Only")

            body_table.add_row("Total Nodes:", "💻", str(total_nodes))
            body_table.add_row("Data Nodes:", "💾", str(data_nodes))
            body_table.add_row("Active Nodes:", "✅", str(active_nodes))

            if excluded_nodes:
                body_table.add_row("", "", "")
                body_table.add_row("Excluded Nodes:", "❌", str(excluded_count))
                for node in excluded_nodes:
                    body_table.add_row("", "🔴", node)
            else:
                body_table.add_row("Excluded Nodes:", "✅", "None")

            title_panel = Panel(
                body_table,
                title=f"[{ts}]🔀 Elasticsearch Allocation Settings[/{ts}]",
                subtitle=subtitle_rich,
                border_style=border_style,
                padding=(1, 2)
            )

            # --- Help table (matching snapshots/ilm/template standard) ---
            full_theme = self.theme_manager.get_full_theme_data() if self.theme_manager else {}
            table_styles = full_theme.get('table_styles', {})
            header_style = table_styles.get('header_style', 'bold white')
            tbl_border = style_system._get_style('table_styles', 'border_style', 'white') if style_system else 'white'
            box_style = style_system.get_table_box() if style_system else None

            primary_style = style_system.get_semantic_style("primary") if style_system else "bold"
            success_style = style_system.get_semantic_style("success") if style_system else "green"
            muted_style = style_system._get_style('semantic', 'muted', 'dim') if style_system else 'dim'

            help_table = Table(
                show_header=True,
                header_style=header_style,
                border_style=tbl_border,
                box=box_style,
                show_lines=False,
                expand=True,
            )
            help_table.add_column("Command", style=primary_style, ratio=2)
            help_table.add_column("Description", style="white", ratio=3)
            help_table.add_column("Example", style=success_style, ratio=3)

            rows = [
                ("allocation", "Show allocation settings overview", "allocation"),
                ("allocation enable", "Enable shard allocation (all shards)", "allocation enable"),
                ("allocation disable", "Disable shard allocation (primaries only)", "allocation disable"),
                ("allocation explain <index>", "Explain allocation decisions for an index", "allocation explain mylog"),
            ]
            for i, (cmd, desc, ex) in enumerate(rows):
                help_table.add_row(cmd, desc, f"./escmd.py {ex}", style=style_system.get_zebra_style(i) if style_system else None)

            help_table.add_row(
                Text("── Node Exclusions ──", style=muted_style),
                Text("", style=muted_style),
                Text("", style=muted_style),
            )

            excl_rows = [
                ("allocation exclude add <host>", "Exclude node from allocation", "allocation exclude add node-3"),
                ("allocation exclude remove <host>", "Remove node from exclusion list", "allocation exclude remove node-3"),
                ("allocation exclude reset", "Reset all node exclusions", "allocation exclude reset"),
            ]
            for i, (cmd, desc, ex) in enumerate(excl_rows):
                help_table.add_row(
                    Text(cmd, style=style_system._get_style('semantic', 'secondary', 'magenta') if style_system else 'magenta'),
                    desc,
                    Text(f"./escmd.py {ex}", style=muted_style),
                    style=style_system.get_zebra_style(i) if style_system else None,
                )

            # --- Render layout ---
            print()
            self.console.print(title_panel)
            print()
            self.console.print(help_table)
            print()

        except Exception as e:
            self.console.print(f"[red]❌ Error retrieving allocation settings: {str(e)}[/red]")

        # Return the full JSON for reference
        return json.dumps(settings)

    def render_allocation_explain_results(self, explain_result: Dict[str, Any]) -> None:
        """
        Render allocation explain results in themed multi-panel format.

        Args:
            explain_result: Enhanced allocation explanation data from AllocationProcessor
        """
        style_system = self.style_system
        ss = style_system
        basic = explain_result.get("basic_explanation", {})

        # Theme helpers matching ILM/health renderer patterns
        tm = self.theme_manager
        _title = tm.get_themed_style("panel_styles", "title", "bold white") if tm else "bold white"
        _border = ss._get_style('table_styles', 'border_style', 'cyan') if ss else "cyan"

        if "error" in explain_result:
            self.console.print(f"[red]❌ {explain_result['error']}[/red]")
            return

        index_name = explain_result.get("index_name", "Unknown")
        shard_number = explain_result.get("shard_number", "?")
        shard_type = explain_result.get("shard_type", "unknown")
        current_alloc = explain_result.get("current_allocation", {})
        summary = explain_result.get("summary", {})
        metadata = explain_result.get("enhancement_metadata", {})
        is_allocated = current_alloc.get("allocated")
        alloc_possible = summary.get("allocation_possible", False)
        nodes_evaluated = summary.get("total_nodes_evaluated", 0)

        # --- Title panel with subtitle bar ---
        shard_overview = explain_result.get("shard_overview", {})
        idx_health = shard_overview.get("health", "unknown")
        total_shards = shard_overview.get("total_shards", 0)
        pri_count = shard_overview.get("primary_count", 0)
        rep_count = shard_overview.get("replica_count", 0)
        shard_states = shard_overview.get("states", {})
        shard_nodes = shard_overview.get("nodes", {})

        health_icon = "🟢" if idx_health == "green" else "🟡" if idx_health == "yellow" else "🔴" if idx_health == "red" else "⚪"
        health_style_key = "success" if idx_health == "green" else "warning" if idx_health == "yellow" else "error" if idx_health == "red" else "muted"

        subtitle_rich = Text()
        subtitle_rich.append("Index: ", style="default")
        subtitle_rich.append(index_name, style=ss._get_style('semantic', 'info', 'cyan') if ss else "cyan")
        subtitle_rich.append(" | Health: ", style="default")
        subtitle_rich.append(f"{health_icon} {idx_health.capitalize()}", style=ss._get_style('semantic', health_style_key, 'white') if ss else "white")
        subtitle_rich.append(" | Shards: ", style="default")
        subtitle_rich.append(f"{pri_count}p", style=ss._get_style('semantic', 'primary', 'bright_magenta') if ss else "bright_magenta")
        subtitle_rich.append("/", style="default")
        subtitle_rich.append(f"{rep_count}r", style=ss._get_style('semantic', 'info', 'blue') if ss else "blue")

        started = shard_states.get("STARTED", 0)
        unassigned = shard_states.get("UNASSIGNED", 0)
        if started:
            subtitle_rich.append(" | Started: ", style="default")
            subtitle_rich.append(str(started), style=ss._get_style('semantic', 'success', 'green') if ss else "green")
        if unassigned:
            subtitle_rich.append(" | Unassigned: ", style="default")
            subtitle_rich.append(str(unassigned), style=ss._get_style('semantic', 'error', 'red') if ss else "red")

        if ss:
            title_panel = Panel(
                Text(f"{index_name} [shard {shard_number}] ({shard_type})", style=ss.get_semantic_style("neutral") or "bold white", justify="center"),
                title=f"[{_title}]🔍 Allocation Explain[/{_title}]",
                subtitle=subtitle_rich,
                border_style=_border,
                padding=(1, 2)
            )
        else:
            title_panel = Panel(
                Text(f"{index_name} [shard {shard_number}] ({shard_type})", style="bold white", justify="center"),
                title=f"[{_title}]🔍 Allocation Explain[/{_title}]",
                subtitle=subtitle_rich,
                border_style=_border,
                padding=(1, 2)
            )

        # --- Allocation Detail panel (left) ---
        alloc_table = Table(show_header=False, box=None, padding=(0, 1))
        alloc_table.add_column("Label", style="bold", no_wrap=True)
        alloc_table.add_column("Icon", justify="left", width=3)
        alloc_table.add_column("Value", no_wrap=True)

        if is_allocated:
            alloc_table.add_row("Status:", "✅", "Allocated")
            alloc_table.add_row("Node:", "💻", current_alloc.get("node_name", "N/A"))
            alloc_table.add_row("Node ID:", "🔑", current_alloc.get("node_id", "N/A"))
            weight = current_alloc.get("weight_ranking")
            if weight is not None:
                alloc_table.add_row("Weight Ranking:", "📈", str(weight))

            can_remain = basic.get("can_remain_on_current_node")
            if can_remain is not None:
                alloc_table.add_row("Can Remain:", "🔒", str(can_remain))

            remain_decisions = basic.get("can_remain_decisions", [])
            for rd in remain_decisions:
                if rd.get("decision") == "no":
                    alloc_table.add_row(f"  {rd.get('decider', '?')}:", "🚫", rd.get("explanation", ""))

            can_move = basic.get("can_move_to_other_node")
            if can_move is not None:
                alloc_table.add_row("Can Move:", "🔄", str(can_move))

            alloc_border = ss.get_semantic_style("success") if ss else "green"
        else:
            alloc_table.add_row("Status:", "❌", "Unassigned")

            can_allocate = basic.get("can_allocate")
            if can_allocate is not None:
                alloc_table.add_row("Can Allocate:", "🔀", str(can_allocate))

            allocate_explanation = basic.get("allocate_explanation")
            if allocate_explanation:
                alloc_table.add_row("Explanation:", "📝", str(allocate_explanation))

            unassigned_details = explain_result.get("unassigned_details", {})
            reason = unassigned_details.get("reason")
            if reason:
                alloc_table.add_row("Reason:", "📋", str(reason))
            last_status = unassigned_details.get("last_allocation_status")
            if last_status:
                alloc_table.add_row("Last Status:", "🔄", str(last_status))
            if unassigned_details.get("at"):
                alloc_table.add_row("Since:", "🕐", str(unassigned_details["at"]))
            failed = unassigned_details.get("failed_attempts", 0)
            if failed:
                alloc_table.add_row("Failed Attempts:", "🔶", str(failed))

            alloc_border = ss.get_semantic_style("warning") if ss else "yellow"

        alloc_panel = Panel(
            alloc_table,
            title=f"[{_title}]📊 Allocation Detail[/{_title}]",
            border_style=alloc_border,
            padding=(1, 2)
        )

        # --- Summary & Shards panel (right) ---
        summary_table = Table(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Label", style="bold", no_wrap=True)
        summary_table.add_column("Icon", justify="left", width=3)
        summary_table.add_column("Value", no_wrap=True)

        recommendation = summary.get("recommendation", "")

        summary_table.add_row("Nodes Evaluated:", "💻", str(nodes_evaluated))
        nodes_available = metadata.get("nodes_available", 0)
        if nodes_available:
            summary_table.add_row("Nodes Available:", "💾", str(nodes_available))

        if alloc_possible:
            summary_table.add_row("Allocation Possible:", "✅", "Yes")
        else:
            summary_table.add_row("Allocation Possible:", "❌", "No")

        barriers = summary.get("primary_barriers", [])
        for barrier in barriers:
            barrier_name = barrier.get("barrier", "Unknown")
            affected = barrier.get("affected_nodes", 0)
            summary_table.add_row("Barrier:", "🚧", f"{barrier_name} ({affected} node(s))")

        if recommendation:
            summary_table.add_row("Recommendation:", "💡", recommendation)

        # Shard overview section
        if total_shards > 0:
            summary_table.add_row("", "", "")
            summary_table.add_row("Total Shards:", "📊", str(total_shards))

            # Primary status
            pri_started = 0
            pri_other = 0
            for shard in shard_overview.get('_raw_shards', []):
                if shard.get('prirep') == 'p':
                    if shard.get('state') == 'STARTED':
                        pri_started += 1
                    else:
                        pri_other += 1

            if pri_other == 0:
                summary_table.add_row("Primary:", "🔑", f"{pri_count} Started")
            else:
                summary_table.add_row("Primary:", "🔑", f"{pri_started} Started, {pri_other} Other")

            # Replica status
            rep_started = shard_states.get('STARTED', 0) - pri_started
            rep_unassigned = unassigned
            if rep_unassigned > 0:
                summary_table.add_row("Replica:", "📋", f"{rep_unassigned} Unassigned")
            elif rep_count > 0:
                summary_table.add_row("Replica:", "📋", f"{rep_count} Started")

            # Node distribution (top node)
            if shard_nodes:
                top_nodes = sorted(shard_nodes.items(), key=lambda x: x[1], reverse=True)
                for node_name, count in top_nodes[:2]:
                    if node_name != 'unassigned':
                        shard_word = "shard" if count == 1 else "shards"
                        summary_table.add_row("Node:", "💻", f"{node_name} ({count} {shard_word})")

        summary_panel = Panel(
            summary_table,
            title=f"[{_title}]📋 Summary & Shards[/{_title}]",
            border_style=ss.get_semantic_style("success" if alloc_possible else "warning") if ss else ("green" if alloc_possible else "yellow"),
            padding=(1, 2)
        )

        # --- Node Allocation Decisions panel (full width) ---
        node_decisions = explain_result.get("node_decisions", [])
        decisions_panel = None
        if node_decisions:
            decisions_table = Table(
                show_header=True,
                box=None,
                padding=(0, 1),
                expand=True,
            )
            decisions_table.add_column("Node", style="bold", no_wrap=True)
            decisions_table.add_column("Transport", no_wrap=True, style="dim")
            decisions_table.add_column("Decision", no_wrap=True)
            decisions_table.add_column("Weight", justify="right", no_wrap=True)
            decisions_table.add_column("Deciders", ratio=1)

            for node in node_decisions:
                node_name = node.get("node_name", "Unknown")
                transport = node.get("transport_address", "")
                decision = node.get("node_decision", "unknown")
                weight = str(node.get("weight_ranking", ""))

                if decision == "yes":
                    decision_text = Text("Yes", style=ss.get_semantic_style("success") if ss else "green")
                elif decision == "throttle":
                    decision_text = Text("Throttled", style=ss.get_semantic_style("warning") if ss else "yellow")
                elif decision == "no":
                    decision_text = Text("No", style=ss.get_semantic_style("error") if ss else "red")
                elif decision == "worse":
                    decision_text = Text("Worse", style=ss.get_semantic_style("warning") if ss else "yellow")
                else:
                    decision_text = Text(decision, style="dim")

                deciders = node.get("deciders", [])
                if deciders:
                    decider_lines = []
                    for d in deciders:
                        decider_name = d.get("decider", "?")
                        decider_decision = d.get("decision", "?")
                        explanation = d.get("explanation", "")
                        if decider_decision == "no":
                            decider_lines.append(f"NO  {decider_name}: {explanation}")
                        elif decider_decision == "yes":
                            decider_lines.append(f"YES {decider_name}")
                        else:
                            decider_lines.append(f"    {decider_name}: {explanation}")
                    details = "\n".join(decider_lines)
                else:
                    details = "No deciders"

                decisions_table.add_row(node_name, transport, decision_text, weight, details)

            decisions_panel = Panel(
                decisions_table,
                title=f"[{_title}]🔀 Node Allocation Decisions[/{_title}]",
                border_style=ss.get_semantic_style("info") if ss else "blue",
                padding=(1, 2)
            )

        # --- Render layout ---
        print()
        self.console.print(title_panel)
        print()
        self.console.print(Columns([alloc_panel, summary_panel], expand=True))
        print()
        if decisions_panel:
            self.console.print(decisions_panel)
            print()
