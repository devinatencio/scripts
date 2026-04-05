"""
Replica management display rendering for Elasticsearch replica operations.

This module handles the display and formatting of replica management results,
including update plans and execution results.
"""

from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


class ReplicaRenderer:
    """Renderer for replica management display operations."""

    def __init__(self, console: Console = None):
        """
        Initialize replica renderer.

        Args:
            console: Rich console instance (optional)
        """
        self.console = console if console else Console()

    def render_update_plan(self, plan_result: Dict[str, Any], dry_run: bool = False):
        """
        Display the replica update plan in a formatted table.

        Args:
            plan_result: Plan result from ReplicaProcessor
            dry_run: Whether this is a dry run (no actual changes)
        """
        # Summary information
        summary_info = [
            f"📊 Total indices analyzed: {plan_result['total_candidates']}",
            f"🔧 Indices requiring updates: {plan_result['total_updates_needed']}",
            f"💤 Indices to skip: {len(plan_result['skipped_indices'])}",
            f"🎯 Target replica count: {plan_result['target_count']}"
        ]

        if plan_result.get('pattern'):
            summary_info.append(f"🔍 Pattern filter: {plan_result['pattern']}")
        if plan_result.get('no_replicas_only'):
            summary_info.append("📋 Mode: No-replicas-only")

        summary_text = "\n".join(summary_info)
        summary_panel = Panel(
            summary_text,
            title="📋 Replica Update Plan Summary",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(summary_panel)
        print()

        # Show indices to update
        if plan_result['indices_to_update']:
            self._render_indices_to_update(plan_result['indices_to_update'], dry_run)

        # Show skipped indices (first 10)
        if plan_result['skipped_indices']:
            self._render_skipped_indices(plan_result['skipped_indices'])

    def render_update_results(self, result: Dict[str, Any]):
        """
        Display the results of replica updates.

        Args:
            result: Execution result from ReplicaProcessor
        """
        # Summary
        summary_info = [
            f"✅ Successful updates: {result['success_count']}/{result['total_attempted']}",
            f"❌ Failed updates: {result['failure_count']}/{result['total_attempted']}",
            f"🎯 Target replica count: {result['target_count']}"
        ]

        summary_text = "\n".join(summary_info)
        border_style = "green" if result['failure_count'] == 0 else "red"
        summary_panel = Panel(
            summary_text,
            title="📊 Replica Update Results",
            border_style=border_style,
            padding=(1, 2)
        )
        self.console.print(summary_panel)
        print()

        # Show successful updates
        if result['successful_updates']:
            self._render_successful_updates(result['successful_updates'])

        # Show failed updates
        if result['failed_updates']:
            self._render_failed_updates(result['failed_updates'])

    def render_replica_summary(self, replica_settings: Dict[str, Any]):
        """
        Display a summary of replica settings across indices.

        Args:
            replica_settings: Index replica settings data
        """
        if not replica_settings:
            self.console.print("[yellow]No replica settings data available[/yellow]")
            return

        # Create summary table
        summary_table = Table(
            title="📊 Replica Settings Summary",
            box=box.ROUNDED,
            expand=True
        )
        summary_table.add_column("Index", style="bold cyan", ratio=4)
        summary_table.add_column("Current Replicas", style="yellow", ratio=2)
        summary_table.add_column("Status", style="green", ratio=3)

        for index_name, index_data in replica_settings.items():
            current_replicas = index_data.get('settings', {}).get('index', {}).get('number_of_replicas', 'unknown')

            # Determine status
            if current_replicas == 'unknown':
                status = "❓ Unable to determine"
                status_style = "red"
            elif str(current_replicas) == "0":
                status = "🔶 No replicas"
                status_style = "yellow"
            else:
                status = "✅ Has replicas"
                status_style = "green"

            summary_table.add_row(
                index_name,
                str(current_replicas),
                f"[{status_style}]{status}[/{status_style}]"
            )

        self.console.print(Panel(summary_table, border_style="blue", padding=(1, 2)))

    def _render_indices_to_update(self, indices_to_update: List[Dict[str, Any]], dry_run: bool):
        """
        Render the table of indices that will be updated.

        Args:
            indices_to_update: List of indices to update
            dry_run: Whether this is a dry run
        """
        update_table = Table(title="🔧 Indices to Update", box=box.ROUNDED, expand=True)
        update_table.add_column("Index", style="bold cyan", ratio=4)
        update_table.add_column("Current Replicas", style="red", ratio=1)
        update_table.add_column("Target Replicas", style="green", ratio=1)
        update_table.add_column("Status", style="yellow", ratio=2)

        for index_info in indices_to_update:
            status = "🔄 Ready for update" if not dry_run else "📋 Dry run (no changes)"
            update_table.add_row(
                index_info['index'],
                str(index_info['current_replicas']),
                str(index_info['target_replicas']),
                status
            )

        self.console.print(Panel(update_table, border_style="green", padding=(1, 2)))
        print()

    def _render_skipped_indices(self, skipped_indices: List[Dict[str, Any]]):
        """
        Render the table of skipped indices.

        Args:
            skipped_indices: List of indices that were skipped
        """
        skipped_table = Table(title="💤 Skipped Indices (First 10)", box=box.ROUNDED, expand=True)
        skipped_table.add_column("Index", style="bold yellow", ratio=3)
        skipped_table.add_column("Reason", style="dim", ratio=3)

        for index_info in skipped_indices[:10]:
            skipped_table.add_row(
                index_info['index'],
                index_info['reason']
            )

        if len(skipped_indices) > 10:
            skipped_table.add_row("...", f"and {len(skipped_indices) - 10} more")

        self.console.print(Panel(skipped_table, border_style="yellow", padding=(1, 2)))
        print()

    def _render_successful_updates(self, successful_updates: List[Dict[str, Any]]):
        """
        Render the table of successful updates.

        Args:
            successful_updates: List of successful update results
        """
        success_table = Table(title="✅ Successful Updates", box=box.ROUNDED, expand=True)
        success_table.add_column("Index", style="bold green", ratio=4)
        success_table.add_column("Previous", style="red", ratio=1)
        success_table.add_column("New", style="green", ratio=1)
        success_table.add_column("Status", style="bright_green", ratio=2)

        for update_info in successful_updates:
            success_table.add_row(
                update_info['index'],
                str(update_info['previous_replicas']),
                str(update_info['new_replicas']),
                "✅ Updated successfully"
            )

        self.console.print(Panel(success_table, border_style="green", padding=(1, 2)))
        print()

    def _render_failed_updates(self, failed_updates: List[Dict[str, Any]]):
        """
        Render the table of failed updates.

        Args:
            failed_updates: List of failed update results
        """
        failure_table = Table(title="❌ Failed Updates", box=box.ROUNDED, expand=True)
        failure_table.add_column("Index", style="bold red", ratio=3)
        failure_table.add_column("Previous", style="yellow", ratio=1)
        failure_table.add_column("Error", style="red", ratio=4)

        for failure_info in failed_updates:
            failure_table.add_row(
                failure_info['index'],
                str(failure_info['previous_replicas']),
                failure_info['error']
            )

        self.console.print(Panel(failure_table, border_style="red", padding=(1, 2)))
        print()
