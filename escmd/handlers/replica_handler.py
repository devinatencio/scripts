"""
Replica management command handlers for escmd.

This module contains handlers for replica count management operations.
"""

import json
from .base_handler import BaseHandler


class ReplicaHandler(BaseHandler):
    """Handler for replica management commands."""

    def handle_set_replicas(self):
        """Handle replica count management command."""
        # Extract arguments
        target_count = getattr(self.args, 'count', 1)
        indices_arg = getattr(self.args, 'indices', None)
        pattern = getattr(self.args, 'pattern', None)
        no_replicas_only = getattr(self.args, 'no_replicas_only', False)
        dry_run = getattr(self.args, 'dry_run', False)
        force = getattr(self.args, 'force', False)
        format_output = getattr(self.args, 'format', 'table')
        
        try:
            # Parse indices if provided
            target_indices = []
            if indices_arg:
                target_indices = [idx.strip() for idx in indices_arg.split(',') if idx.strip()]
            
            # Use the new replica commands
            replica_commands = self.es_client.replica_commands
            result = replica_commands.set_replicas(
                target_count=target_count,
                indices=target_indices,
                pattern=pattern,
                no_replicas_only=no_replicas_only,
                dry_run=dry_run,
                force=force,
                format_output=format_output
            )
            
            # Handle JSON output format
            if format_output == 'json':
                print(json.dumps(result, indent=2))
                
        except Exception as e:
            if format_output == 'json':
                error_result = {'error': str(e), 'success': False}
                print(json.dumps(error_result, indent=2))
            else:
                self.console.print(f"[red]Error: {str(e)}[/red]")
