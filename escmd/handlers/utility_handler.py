"""
Utility command handlers for escmd.

Handles commands like locations and cluster-check.
"""

import json
import os
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm

from .base_handler import BaseHandler
from configuration_manager import ConfigurationManager


class UtilityHandler(BaseHandler):
    """Handler for utility commands like locations and cluster health checks."""

    def handle_show_settings(self):
        """
        Display current configuration settings.
        """
        from cli.special_commands import handle_show_settings
        config_manager = ConfigurationManager(self.config_file, os.path.join(os.path.dirname(self.config_file), 'escmd.json'))
        format_output = getattr(self.args, 'format', None)
        handle_show_settings(config_manager, format_output)

    def handle_cluster_check(self):
        """Handle comprehensive cluster health checking command."""
        import time

        max_shard_size = getattr(self.args, 'max_shard_size', 50)  # Default 50GB
        show_details = getattr(self.args, 'show_details', False)
        skip_ilm = getattr(self.args, 'skip_ilm', False)

        if self.args.format == 'json':
            # Gather all data for JSON output
            check_results = self.es_client.perform_cluster_health_checks(max_shard_size, skip_ilm)

            # Handle replica fixing if requested
            fix_replicas = getattr(self.args, 'fix_replicas', None)
            if fix_replicas is not None:
                replica_results = self._perform_replica_fixing_json(check_results, fix_replicas)
                check_results['replica_fixing'] = replica_results

            # Sanitize the data to ensure valid JSON
            sanitized_results = self._sanitize_for_json(check_results)
            self.es_client.pretty_print_json(sanitized_results)
        else:
            # Rich formatted output with progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
                transient=True
            ) as progress:

                # Create main task (adjust total based on whether ILM is skipped)
                total_steps = 3 if skip_ilm else 4
                main_task = progress.add_task("[bold cyan]Running cluster health checks...", total=total_steps)

                # Step 1: ILM errors check (skip if requested)
                if not skip_ilm:
                    progress.update(main_task, description="[bold yellow]🔍 Checking for ILM errors...")
                    ilm_errors = self.es_client.check_ilm_errors()
                    progress.advance(main_task)
                    time.sleep(0.1)
                else:
                    ilm_errors = {'skipped': True, 'reason': 'ILM checks skipped via --skip-ilm flag'}

                # Step 2: No replicas check
                progress.update(main_task, description="[bold blue]📊 Checking indices with no replicas...")
                no_replica_indices = self.es_client.check_no_replica_indices()
                progress.advance(main_task)
                time.sleep(0.1)

                # Step 3: Large shards check
                progress.update(main_task, description="[bold orange1]📏 Checking for oversized shards...")
                large_shards = self.es_client.check_large_shards(max_shard_size)
                progress.advance(main_task)
                time.sleep(0.1)

                # Step 4: Generate report
                progress.update(main_task, description="[bold green]📋 Generating health report...")
                progress.advance(main_task)

            # Get ILM display limit from args or config
            ilm_display_limit = getattr(self.args, 'ilm_limit', None)

            # Display comprehensive health report
            self.es_client.display_cluster_health_report({
                'ilm_results': ilm_errors,  # Pass as ilm_results to match new format
                'no_replica_indices': no_replica_indices,
                'large_shards': large_shards,
                'max_shard_size': max_shard_size,
                'show_details': show_details,
                'ilm_display_limit': ilm_display_limit
            })

            # Handle replica fixing if requested
            fix_replicas = getattr(self.args, 'fix_replicas', None)
            if fix_replicas is not None:
                self._handle_replica_fixing_in_cluster_check(no_replica_indices, fix_replicas)

    def handle_set_replicas(self):
        """Handle replica count management command."""
        import json

        # Extract arguments
        target_count = getattr(self.args, 'count', 1)
        indices_arg = getattr(self.args, 'indices', None)
        pattern = getattr(self.args, 'pattern', None)
        no_replicas_only = getattr(self.args, 'no_replicas_only', False)
        dry_run = getattr(self.args, 'dry_run', False)
        force = getattr(self.args, 'force', False)
        format_output = getattr(self.args, 'format', 'table')

        # Show help if no targeting args provided
        if not indices_arg and not pattern and not no_replicas_only:
            if format_output == 'json':
                error_result = {'error': 'No indices specified. Use --indices, --pattern, or --no-replicas-only.', 'success': False}
                self.es_client.pretty_print_json(error_result)
            else:
                self._show_set_replicas_help()
            return

        try:
            # Parse indices if provided
            target_indices = []
            if indices_arg:
                target_indices = [idx.strip() for idx in indices_arg.split(',') if idx.strip()]

            # Use the new replica commands to set replicas
            result = self.es_client.replica_commands.set_replicas(
                target_count=target_count,
                indices=target_indices,
                pattern=pattern,
                no_replicas_only=no_replicas_only,
                dry_run=dry_run,
                force=force,
                format_output=format_output
            )

        except Exception as e:
            if format_output == 'json':
                error_result = {'error': str(e), 'success': False}
                self.es_client.pretty_print_json(error_result)
            else:
                self.console.print(f"[red]Error: {str(e)}[/red]")

    def _show_set_replicas_help(self):
        """Display help screen for set-replicas command."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = self.console
        ss = self.es_client.style_system
        tm = self.es_client.theme_manager

        primary_style = ss.get_semantic_style("primary")
        success_style = ss.get_semantic_style("success")
        muted_style = ss._get_style('semantic', 'muted', 'dim')
        border_style = ss._get_style('table_styles', 'border_style', 'white')
        header_style = tm.get_theme_styles().get('header_style', 'bold white') if tm else 'bold white'
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        box_style = ss.get_table_box()

        header_panel = Panel(
            Text("Run ./escmd.py set-replicas --count <n> [target options]", style="bold white"),
            title=f"[{title_style}]🔢 Set Replicas[/{title_style}]",
            subtitle=Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]for full options[/dim]"),
            border_style=border_style,
            padding=(1, 2),
            expand=True,
        )

        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border_style,
            box=box_style,
            show_lines=False,
            expand=True,
        )
        table.add_column("Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("--count <n>", "Target replica count (default: 1)", "set-replicas --count 1 --pattern 'logs-*'"),
            ("--indices <list>", "Comma-separated list of indices", "set-replicas --count 0 --indices idx1,idx2"),
            ("--pattern <regex>", "Pattern to match indices", "set-replicas --count 1 --pattern 'temp-*'"),
            ("--no-replicas-only", "Only update indices with 0 replicas", "set-replicas --count 1 --no-replicas-only"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Safety ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        safety = [
            ("--dry-run", "Preview changes without applying", "set-replicas --count 1 --pattern 'logs-*' --dry-run"),
            ("--force", "Skip confirmation prompts", "set-replicas --count 0 --pattern 'temp-*' --force"),
            ("--format json", "JSON output", "set-replicas --count 1 --pattern '*' --format json"),
        ]
        for i, (opt, desc, ex) in enumerate(safety):
            table.add_row(
                Text(opt, style=ss._get_style('semantic', 'secondary', 'magenta')),
                desc,
                Text(f"./escmd.py {ex}", style=muted_style),
                style=ss.get_zebra_style(i) if ss else None,
            )

        console.print()
        console.print(header_panel)
        console.print()
        console.print(table)
        console.print()

    def _sanitize_for_json(self, obj):
        """Recursively sanitize data to ensure valid JSON by removing problematic fields and characters."""
        import re

        if isinstance(obj, dict):
            # Remove problematic fields that contain stack traces
            sanitized_dict = {}
            for key, value in obj.items():
                if key in ['stack_trace', 'step_info']:
                    # For step_info, keep only essential fields
                    if key == 'step_info' and isinstance(value, dict):
                        clean_step_info = {}
                        for step_key, step_value in value.items():
                            if step_key in ['type', 'reason'] and isinstance(step_value, str):
                                # Clean the reason/type but remove stack traces
                                cleaned = re.sub(r'[\x00-\x1F]', ' ', str(step_value))
                                cleaned = re.sub(r'\\n.*', '', cleaned)  # Remove everything after \n
                                clean_step_info[step_key] = cleaned[:200]  # Limit length
                        sanitized_dict[key] = clean_step_info
                    # Skip stack_trace entirely
                elif key == 'reason' and isinstance(value, str) and '\\n' in value:
                    # For reason fields, keep only the first line
                    cleaned = value.split('\\n')[0]
                    cleaned = re.sub(r'[\x00-\x1F]', ' ', cleaned)
                    sanitized_dict[key] = cleaned[:200]  # Limit length
                else:
                    sanitized_dict[key] = self._sanitize_for_json(value)
            return sanitized_dict
        elif isinstance(obj, list):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, str):
            # Aggressively clean strings - remove all control characters
            sanitized = re.sub(r'[\x00-\x1F]', ' ', obj)
            # Limit very long strings
            if len(sanitized) > 500:
                sanitized = sanitized[:497] + "..."
            return sanitized
        else:
            return obj

    def _handle_replica_fixing_in_cluster_check(self, no_replica_indices, target_count):
        """Handle replica fixing in table mode during cluster-check."""
        if not no_replica_indices:
            self.console.print("\n[green]✅ No indices found with 0 replicas - nothing to fix![/green]")
            return

        # Extract arguments
        dry_run = getattr(self.args, 'dry_run', False)
        force = getattr(self.args, 'force', False)

        try:
            # Convert no_replica_indices to the format expected by ReplicaCommands
            target_indices = [idx['index'] for idx in no_replica_indices]

            # Display section header
            header_text = f"🔧 Replica Fixing (Integrated with Cluster Check)"
            header_panel = Panel(
                header_text,
                title="🏥➜🔧 Health Check ➜ Replica Fixing",
                border_style="blue",
                padding=(1, 2)
            )
            self.console.print(header_panel)
            print()

            # Use the new replica commands to set replicas
            result = self.es_client.replica_commands.set_replicas(
                target_count=target_count,
                indices=target_indices,
                pattern=None,
                no_replicas_only=False,  # We already filtered to no-replica indices
                dry_run=dry_run,
                force=force,
                format_output='table'
            )

        except Exception as e:
            self.console.print(f"[red]Error during replica fixing: {str(e)}[/red]")

    def _perform_replica_fixing_json(self, check_results, target_count):
        """Handle replica fixing in JSON mode during cluster-check."""
        dry_run = getattr(self.args, 'dry_run', False)
        force = getattr(self.args, 'force', False)

        try:
            # Extract no replica indices from check results
            no_replica_indices = check_results.get('checks', {}).get('no_replica_indices', [])
            if not no_replica_indices:
                return {
                    'status': 'no_action_needed',
                    'message': 'No indices found with 0 replicas',
                    'target_count': target_count,
                    'dry_run': dry_run
                }

            # Convert to format expected by ReplicaCommands
            target_indices = [idx['index'] for idx in no_replica_indices]

            # Use the new replica commands to set replicas
            result = self.es_client.replica_commands.set_replicas(
                target_count=target_count,
                indices=target_indices,
                pattern=None,
                no_replicas_only=False,  # We already filtered to no-replica indices
                dry_run=dry_run,
                force=force,
                format_output='json'
            )

            return result

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'target_count': target_count,
                'dry_run': dry_run
            }
