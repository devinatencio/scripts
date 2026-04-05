"""
Replica management commands for Elasticsearch indices.

This module provides command-level operations for replica count management,
including validation, orchestration, and integration with processors and renderers.
"""

from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm

from .base_command import BaseCommand
from processors.replica_processor import ReplicaProcessor
from display.replica_renderer import ReplicaRenderer


class ReplicaCommands(BaseCommand):
    """Command handler for replica management operations."""

    def __init__(self, es_client, console: Console = None):
        """
        Initialize replica commands.
        
        Args:
            es_client: ElasticsearchClient instance
            console: Rich console instance
        """
        super().__init__(es_client, console)
        self.processor = ReplicaProcessor(es_client)
        self.renderer = ReplicaRenderer(console)

    def get_command_group(self) -> str:
        """Get the command group name."""
        return "replica"

    def set_replicas(
        self,
        target_count: int,
        indices: Optional[List[str]] = None,
        pattern: Optional[str] = None,
        no_replicas_only: bool = False,
        dry_run: bool = False,
        force: bool = False,
        format_output: str = 'table'
    ) -> Dict[str, Any]:
        """
        Set replica count for specified indices.

        Args:
            target_count: Target number of replicas
            indices: Specific indices to update (optional)
            pattern: Pattern to match indices (optional)
            no_replicas_only: Only update indices with 0 replicas
            dry_run: Show plan without executing changes
            force: Skip confirmation prompt
            format_output: Output format ('table' or 'json')

        Returns:
            dict: Operation results

        Raises:
            ValueError: If invalid arguments provided
            Exception: If operation fails
        """
        # Validate arguments
        self._validate_replica_arguments(target_count, indices, pattern)

        try:
            # Plan the replica updates
            plan_result = self._plan_replica_updates(
                target_count, indices, pattern, no_replicas_only, format_output
            )

            # Handle different output formats
            if format_output == 'json':
                return self._handle_json_output(plan_result, target_count, dry_run)
            else:
                return self._handle_table_output(plan_result, target_count, dry_run, force)

        except Exception as e:
            if format_output == 'json':
                return {'error': str(e), 'success': False}
            else:
                self.console.print(f"[red]Error: {str(e)}[/red]")
                return {'error': str(e), 'success': False}

    def get_replica_settings(
        self, 
        indices: Optional[List[str]] = None,
        format_output: str = 'table'
    ) -> Dict[str, Any]:
        """
        Get current replica settings for indices.

        Args:
            indices: Specific indices to check (optional, defaults to all)
            format_output: Output format ('table' or 'json')

        Returns:
            dict: Replica settings data
        """
        try:
            settings_data = self.processor.get_index_replica_settings(indices)
            
            if format_output == 'json':
                return self._format_json_output(settings_data)
            else:
                self.renderer.render_replica_summary(settings_data)
                return {'success': True, 'data': settings_data}

        except Exception as e:
            if format_output == 'json':
                return {'error': str(e), 'success': False}
            else:
                self.console.print(f"[red]Error: {str(e)}[/red]")
                return {'error': str(e), 'success': False}

    def _validate_replica_arguments(
        self, 
        target_count: int, 
        indices: Optional[List[str]], 
        pattern: Optional[str]
    ):
        """
        Validate replica management arguments.

        Args:
            target_count: Target replica count
            indices: List of specific indices
            pattern: Index pattern

        Raises:
            ValueError: If arguments are invalid
        """
        if target_count < 0:
            raise ValueError("Target replica count cannot be negative")

        if target_count > 10:
            self.console.print(
                "[yellow]Warning: Setting replica count > 10 may impact cluster performance[/yellow]"
            )

        if indices and pattern:
            raise ValueError("Cannot specify both specific indices and pattern")

        if indices and not isinstance(indices, list):
            raise ValueError("Indices must be provided as a list")

        if pattern and not isinstance(pattern, str):
            raise ValueError("Pattern must be provided as a string")

    def _plan_replica_updates(
        self,
        target_count: int,
        indices: Optional[List[str]],
        pattern: Optional[str],
        no_replicas_only: bool,
        format_output: str
    ) -> Dict[str, Any]:
        """
        Plan replica updates with progress indication.

        Args:
            target_count: Target replica count
            indices: Specific indices list
            pattern: Index pattern
            no_replicas_only: Only update indices with 0 replicas
            format_output: Output format

        Returns:
            dict: Plan results
        """
        if format_output == 'table':
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
                transient=True
            ) as progress:
                plan_task = progress.add_task("[bold cyan]Planning replica updates...", total=1)
                plan_result = self.processor.plan_replica_updates(
                    target_count=target_count,
                    indices=indices,
                    pattern=pattern,
                    no_replicas_only=no_replicas_only
                )
                progress.advance(plan_task)
        else:
            plan_result = self.processor.plan_replica_updates(
                target_count=target_count,
                indices=indices,
                pattern=pattern,
                no_replicas_only=no_replicas_only
            )

        return plan_result

    def _handle_json_output(
        self, 
        plan_result: Dict[str, Any], 
        target_count: int, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Handle JSON output format.

        Args:
            plan_result: Plan results from processor
            target_count: Target replica count
            dry_run: Whether this is a dry run

        Returns:
            dict: JSON formatted results
        """
        if not dry_run and plan_result['indices_to_update']:
            # Execute updates for JSON output
            result = self.processor.execute_replica_updates(
                plan_result['indices_to_update'], 
                target_count
            )
            return self._format_json_output(result)
        else:
            return self._format_json_output(plan_result)

    def _handle_table_output(
        self, 
        plan_result: Dict[str, Any], 
        target_count: int, 
        dry_run: bool, 
        force: bool
    ) -> Dict[str, Any]:
        """
        Handle table output format with Rich formatting.

        Args:
            plan_result: Plan results from processor
            target_count: Target replica count
            dry_run: Whether this is a dry run
            force: Skip confirmation prompt

        Returns:
            dict: Operation results
        """
        # Display the plan
        self.renderer.render_update_plan(plan_result, dry_run)

        # Execute if not dry run and there are updates
        if not dry_run and plan_result['indices_to_update']:
            if not force:
                if not Confirm.ask(
                    f"\n🔶  This will update {len(plan_result['indices_to_update'])} indices. Continue?"
                ):
                    self.console.print("[yellow]Operation cancelled.[/yellow]")
                    return {'success': False, 'cancelled': True}

            # Execute the updates with progress
            result = self._execute_updates_with_progress(plan_result, target_count)
            
            # Display results
            self.renderer.render_update_results(result)
            return {'success': True, 'result': result}
        
        return {'success': True, 'plan': plan_result}

    def _execute_updates_with_progress(
        self, 
        plan_result: Dict[str, Any], 
        target_count: int
    ) -> Dict[str, Any]:
        """
        Execute replica updates with progress indication.

        Args:
            plan_result: Plan results with indices to update
            target_count: Target replica count

        Returns:
            dict: Execution results
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=True
        ) as progress:
            
            update_task = progress.add_task(
                "[bold green]Updating replica counts...", 
                total=len(plan_result['indices_to_update'])
            )
            
            result = self.processor.execute_replica_updates(
                plan_result['indices_to_update'], 
                target_count,
                progress=progress,
                task_id=update_task
            )
            
        return result
