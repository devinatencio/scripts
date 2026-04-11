"""
Lifecycle handler for escmd ILM, rollover and auto-rollover commands.

Handles commands related to Index Lifecycle Management (ILM), rollover operations, and automatic rollover.
"""

import json
import os
import re
from datetime import datetime
from rich import print
from rich.panel import Panel
from rich.text import Text
from rich.table import Table as InnerTable

from .base_handler import BaseHandler
from utils import safe_sort_shards_by_size


class LifecycleHandler(BaseHandler):
    """Handler for lifecycle management commands like ILM, rollover, and auto-rollover."""

    def handle_rollover(self):
        """Enhanced rollover command for datastreams with Rich formatting."""
        console = self.console

        if not self.args.datastream:
            if hasattr(self.args, "format") and self.args.format == "json":
                import json

                error_data = {
                    "error": "No datastream specified",
                    "message": "Please provide a datastream name for rollover operation",
                }
                print(json.dumps(error_data, indent=2))
            else:
                error_panel = Panel(
                    Text(
                        "❌ No datastream specified", style="bold red", justify="center"
                    ),
                    subtitle="Please provide a datastream name for rollover operation",
                    border_style="red",
                    padding=(1, 2),
                )
                console.print(error_panel)
            exit(1)

        try:
            # Perform rollover operation
            if hasattr(self.args, "format") and self.args.format == "json":
                rollover_stats = self.es_client.rollover_datastream(
                    self.args.datastream
                )
                self.es_client.pretty_print_json(rollover_stats)
                return

            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get("cluster_name", "Unknown")
            except:
                cluster_name = "Unknown"

            # Create title panel
            title_panel = Panel(
                Text(
                    f"🔄 Datastream Rollover Operation",
                    style="bold cyan",
                    justify="center",
                ),
                subtitle=f"Target: {self.args.datastream} | Cluster: {cluster_name}",
                border_style="cyan",
                padding=(1, 2),
            )

            print()
            console.print(title_panel)
            print()

            # Perform rollover operation
            with console.status(f"Rolling over datastream '{self.args.datastream}'..."):
                rollover_stats = self.es_client.rollover_datastream(
                    self.args.datastream
                )

            # Check if rollover was successful
            rolled_over = rollover_stats.get("rolled_over", False)
            old_index = rollover_stats.get("old_index", "Unknown")
            new_index = rollover_stats.get("new_index", "Unknown")
            dry_run = rollover_stats.get("dry_run", False)

            if rolled_over:
                # Success panel
                success_text = f"🎉 Datastream '{self.args.datastream}' rolled over successfully!\n\n"
                success_text += f"Operation Details:\n"
                success_text += f"• 📂 Old Index: {old_index}\n"
                success_text += f"• 🆕 New Index: {new_index}\n"
                success_text += f"• 🔄 Status: Completed\n"
                if dry_run:
                    success_text += f"• 🧪 Mode: Dry Run (simulation only)"
                else:
                    success_text += f"• ✅ Mode: Executed"

                success_panel = Panel(
                    success_text,
                    title="✅ Rollover Successful",
                    border_style="green",
                    padding=(1, 2),
                )

                # Create detailed results table
                results_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                results_table.add_column("Property", style="bold cyan", no_wrap=True)
                results_table.add_column("Value", style="white")

                for key, value in rollover_stats.items():
                    if key == "rolled_over":
                        icon = "✅" if value else "❌"
                        results_table.add_row(
                            f"{key.replace('_', ' ').title()}:", f"{icon} {value}"
                        )
                    else:
                        results_table.add_row(
                            f"{key.replace('_', ' ').title()}:", str(value)
                        )

                results_panel = Panel(
                    results_table,
                    title="📊 Operation Results",
                    border_style="blue",
                    padding=(1, 2),
                )

                console.print(success_panel)
                print()
                console.print(results_panel)
                print()

            else:
                # Rollover was not performed
                info_text = f"🔵 Rollover was not performed for datastream '{self.args.datastream}'\n\n"
                info_text += (
                    "This typically means the rollover conditions were not met.\n"
                )
                info_text += f"Current Index: {old_index}\n\n"
                info_text += "Common reasons:\n"
                info_text += "• Index size hasn't reached rollover threshold\n"
                info_text += "• Document count hasn't reached rollover threshold\n"
                info_text += "• Index age hasn't reached rollover threshold"

                info_panel = Panel(
                    info_text,
                    title="🔵 Rollover Not Required",
                    border_style="yellow",
                    padding=(1, 2),
                )

                # Still show the results for transparency
                results_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                results_table.add_column("Property", style="bold cyan", no_wrap=True)
                results_table.add_column("Value", style="white")

                for key, value in rollover_stats.items():
                    results_table.add_row(
                        f"{key.replace('_', ' ').title()}:", str(value)
                    )

                results_panel = Panel(
                    results_table,
                    title="📊 Check Results",
                    border_style="blue",
                    padding=(1, 2),
                )

                console.print(info_panel)
                print()
                console.print(results_panel)
                print()

            # Create next steps panel
            actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            actions_table.add_column("Action", style="bold cyan", no_wrap=True)
            actions_table.add_column("Command", style="dim white")

            actions_table.add_row("Check datastreams:", "./escmd.py datastreams")
            actions_table.add_row("View indices:", "./escmd.py indices")
            actions_table.add_row("Check ILM status:", "./escmd.py ilm status")
            actions_table.add_row("Monitor health:", "./escmd.py health")

            actions_panel = Panel(
                actions_table,
                title="🚀 Next Steps",
                border_style="magenta",
                padding=(1, 2),
            )
            console.print(actions_panel)
            print()

        except Exception as e:
            if hasattr(self.args, "format") and self.args.format == "json":
                import json

                error_data = {
                    "error": f"Rollover operation failed: {str(e)}",
                    "datastream": self.args.datastream,
                    "success": False,
                }
                print(json.dumps(error_data, indent=2))
            else:
                error_panel = Panel(
                    Text(
                        f"❌ Rollover operation failed: {str(e)}",
                        style="bold red",
                        justify="center",
                    ),
                    subtitle=f"Failed to rollover datastream: {self.args.datastream}",
                    border_style="red",
                    padding=(1, 2),
                )
                print()
                console.print(error_panel)
                print()

    def handle_auto_rollover(self):
        """Handle automatic rollover based on largest shard."""
        if not self.args.host:
            print("ERROR: No hostname passed.")
            exit(1)
        self._process_auto_rollover()

    def handle_ilm(self):
        """
        Handle ILM (Index Lifecycle Management) related commands.
        """
        if not hasattr(self.args, "ilm_action") or self.args.ilm_action is None:
            self._show_ilm_help()
            return

        if self.args.ilm_action == "status":
            self._handle_ilm_status()
        elif self.args.ilm_action == "policies":
            self._handle_ilm_policies()
        elif self.args.ilm_action == "policy":
            self._handle_ilm_policy()
        elif self.args.ilm_action == "explain":
            self._handle_ilm_explain()
        elif self.args.ilm_action == "errors":
            self._handle_ilm_errors()
        elif self.args.ilm_action == "remove-policy":
            self._handle_ilm_remove_policy()
        elif self.args.ilm_action == "set-policy":
            self._handle_ilm_set_policy()
        elif self.args.ilm_action == "create-policy":
            self._handle_ilm_create_policy()
        elif self.args.ilm_action == "delete-policy":
            self._handle_ilm_delete_policy()
        elif self.args.ilm_action == "backup-policies":
            self._handle_ilm_backup_policies()
        elif self.args.ilm_action == "restore-policies":
            self._handle_ilm_restore_policies()
        elif self.args.ilm_action == "index-patterns":
            self._handle_ilm_index_patterns()
        else:
            self.es_client.show_message_box(
                "Error",
                f"Unknown ILM action: {self.args.ilm_action}",
                message_style="bold white",
                panel_style="red",
            )

    def _process_auto_rollover(self):
        """Process automatic rollover for the largest shard on specified host."""
        shards_data_dict = safe_sort_shards_by_size(
            self.es_client.get_shards_as_dict(), reverse=True
        )
        pattern = f".*{self.args.host}.*"
        filtered_data = [
            item
            for item in shards_data_dict
            if re.search(pattern, item["node"], re.IGNORECASE)
        ]
        largest_primary_shard = next(
            (item for item in filtered_data if item["prirep"] == "p"), None
        )

        if not largest_primary_shard:
            print("No matching shards found")
            return

        datastream_name = self._extract_datastream_name(largest_primary_shard["index"])
        if datastream_name:
            rollover_stats = self.es_client.rollover_datastream(datastream_name)
            self.es_client.print_json_as_table(rollover_stats)
        else:
            print(
                f"Could not extract datastream name from: {largest_primary_shard['index']}"
            )

    def _extract_datastream_name(self, index_name):
        """Extract datastream name from index name."""
        match = re.search(r"\.ds-(.+)-\d{4}\.\d{2}\.\d{2}-\d+$", index_name)
        if match:
            return match.group(1)
        return None

    def _handle_ilm_status(self):
        """Handle ILM status command with comprehensive multi-panel display."""
        if self.args.format == "json":
            ilm_data = self.es_client._get_ilm_status()
            self.es_client.pretty_print_json(ilm_data)
        else:
            self.es_client.print_enhanced_ilm_status()

    def _handle_ilm_policies(self):
        """Handle ILM policies list command."""
        if self.args.format == "json":
            policies = self.es_client.get_ilm_policies()
            self.es_client.pretty_print_json(policies)
        else:
            self.es_client.print_enhanced_ilm_policies()

    def _handle_ilm_policy(self):
        """Handle ILM policy detail command."""
        show_all = getattr(self.args, "show_all", False)
        if self.args.format == "json":
            policy_data = self.es_client.get_ilm_policy_detail(self.args.policy_name)
            self.es_client.pretty_print_json(policy_data)
        else:
            self.es_client.print_enhanced_ilm_policy_detail(
                self.args.policy_name, show_all_indices=show_all
            )

    def _handle_ilm_index_patterns(self):
        """Handle ILM index-patterns command: show unique base patterns for a policy."""
        show_all = getattr(self.args, 'show_all', False)
        if self.args.format == "json":
            data = self.es_client.get_ilm_policy_index_patterns(self.args.policy_name)
            self.es_client.pretty_print_json(data)
        else:
            self.es_client.print_ilm_policy_index_patterns(self.args.policy_name, show_all)

    def _handle_ilm_explain(self):
        """Handle ILM explain command to show specific index lifecycle status."""
        if self.args.format == "json":
            explain_data = self.es_client.get_ilm_explain(self.args.index)
            self.es_client.pretty_print_json(explain_data)
        else:
            self.es_client.print_enhanced_ilm_explain(self.args.index)

    def _handle_ilm_errors(self):
        """Handle ILM errors command to show indices with ILM errors."""
        if self.args.format == "json":
            errors_data = self.es_client.get_ilm_errors()
            self.es_client.pretty_print_json(errors_data)
        else:
            self.es_client.print_enhanced_ilm_errors()

    def _handle_ilm_remove_policy(self):
        """
        Handle ILM policy removal from indices matching regex pattern or from file.
        """
        input_file = getattr(self.args, "file", None)
        pattern = self.args.pattern

        # Validate arguments
        if input_file and pattern:
            self.es_client.show_message_box(
                "Invalid Arguments",
                "Cannot use both pattern and --file. Choose one.",
                message_style="bold white",
                panel_style="red",
            )
            return

        if not input_file and not pattern:
            self.es_client.show_message_box(
                "Invalid Arguments",
                "Must provide either a pattern or --file.",
                message_style="bold white",
                panel_style="red",
            )
            return

        try:
            # Get matching indices based on input method
            if input_file:
                # Load indices from file (text or JSON)
                matching_indices = self._load_indices_from_file(input_file)
                if not matching_indices:
                    return  # Error already displayed in _load_indices_from_file
                source_description = f"file: {input_file}"
            else:
                # Validate regex pattern
                try:
                    re.compile(pattern)
                except re.error as e:
                    self.es_client.show_message_box(
                        "Invalid Pattern",
                        f"Invalid regex pattern '{pattern}': {str(e)}",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return

                # Get indices matching pattern
                matching_indices = self.es_client.get_matching_indices(pattern)
                if not matching_indices:
                    self.es_client.show_message_box(
                        "No Matches",
                        f"No indices found matching pattern '{pattern}'.",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return
                source_description = f"pattern: {pattern}"

            # Perform bulk ILM policy removal
            results = self.es_client.remove_ilm_policy_from_indices(
                matching_indices,
                dry_run=getattr(self.args, "dry_run", False),
                max_concurrent=getattr(self.args, "max_concurrent", 5),
            )

            # Save results to JSON if requested
            if getattr(self.args, "save_json", None):
                save_source = input_file if input_file else f"pattern-{pattern}"
                self._save_removed_indices_to_json(
                    results, self.args.save_json, save_source
                )

            # Display results
            if self.args.format == "json":
                self.es_client.pretty_print_json(results)
            else:
                self.es_client.display_ilm_bulk_operation_results(
                    results, "Policy Removal"
                )

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"Error during ILM policy removal: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )

    def _handle_ilm_set_policy(self):
        """
        Handle ILM policy assignment to indices matching regex pattern, from file,
        or all indices currently on a source policy (--from-policy).
        """
        policy_name = self.args.policy_name
        input_file = getattr(self.args, "file", None)
        pattern = self.args.pattern
        from_policy = getattr(self.args, "from_policy", None)

        # Validate argument combinations
        if from_policy:
            if input_file or pattern:
                self.es_client.show_message_box(
                    "Invalid Arguments",
                    "Cannot use --from-policy together with a pattern or --file.",
                    message_style="bold white",
                    panel_style="red",
                )
                return
        elif input_file and pattern:
            self.es_client.show_message_box(
                "Invalid Arguments",
                "Cannot use both pattern and --file. Choose one.",
                message_style="bold white",
                panel_style="red",
            )
            return
        elif not input_file and not pattern:
            self.es_client.show_message_box(
                "Invalid Arguments",
                "Must provide a pattern, --file, or --from-policy.",
                message_style="bold white",
                panel_style="red",
            )
            return

        if from_policy and from_policy == policy_name:
            self.es_client.show_message_box(
                "Invalid Arguments",
                "Source and target ILM policy are the same; nothing to migrate.",
                message_style="bold white",
                panel_style="red",
            )
            return

        try:
            # Validate target policy exists
            if not self.es_client.validate_ilm_policy_exists(policy_name):
                self.es_client.show_message_box(
                    "Policy Not Found",
                    f"ILM policy '{policy_name}' does not exist.",
                    message_style="bold white",
                    panel_style="red",
                )
                return

            if from_policy:
                if not self.es_client.validate_ilm_policy_exists(from_policy):
                    self.es_client.show_message_box(
                        "Policy Not Found",
                        f"Source ILM policy '{from_policy}' does not exist.",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return

                matching_indices, err = self.es_client.get_indices_for_ilm_policy(
                    from_policy
                )
                if err:
                    self.es_client.show_message_box(
                        "Error",
                        err,
                        message_style="bold white",
                        panel_style="red",
                    )
                    return
                if not matching_indices:
                    self.es_client.show_message_box(
                        "No Matches",
                        f"No indices are using ILM policy '{from_policy}'.",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return
                source_description = f"from-policy: {from_policy}"
            elif input_file:
                # Load indices from file (text or JSON)
                matching_indices = self._load_indices_from_file(input_file)
                if not matching_indices:
                    return  # Error already displayed in _load_indices_from_file
                source_description = f"file: {input_file}"
            else:
                # Validate regex pattern
                try:
                    re.compile(pattern)
                except re.error as e:
                    self.es_client.show_message_box(
                        "Invalid Pattern",
                        f"Invalid regex pattern '{pattern}': {str(e)}",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return

                # Get indices matching pattern
                matching_indices = self.es_client.get_matching_indices(pattern)
                if not matching_indices:
                    self.es_client.show_message_box(
                        "No Matches",
                        f"No indices found matching pattern '{pattern}'.",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return
                source_description = f"pattern: {pattern}"

            # Show confirmation unless --yes is specified or it's a dry run
            is_dry_run = getattr(self.args, "dry_run", False)
            if not getattr(self.args, "yes", False) and not is_dry_run:
                from rich.panel import Panel
                from rich.table import Table
                from rich.text import Text

                console = self.console

                # Analyze which indices would be updated vs skipped
                indices_to_update = []
                indices_to_skip = []

                for index_info in matching_indices:
                    current_policy = index_info.get("current_policy")
                    if current_policy == policy_name:
                        indices_to_skip.append(index_info)
                    else:
                        indices_to_update.append(index_info)

                # Create confirmation table
                confirm_table = Table(show_header=False, box=None, padding=(0, 1))
                confirm_table.add_column("Property", style="bold yellow", no_wrap=True)
                confirm_table.add_column("Value", style="white")

                confirm_table.add_row("Target policy:", policy_name)
                if from_policy:
                    confirm_table.add_row("Source policy:", from_policy)
                confirm_table.add_row("Source:", source_description)
                confirm_table.add_row("Indices Found:", str(len(matching_indices)))
                confirm_table.add_row(
                    "  • To Update:",
                    f"[bold green]{len(indices_to_update)}[/bold green]",
                )
                confirm_table.add_row(
                    "  • To Skip:",
                    f"[bold yellow]{len(indices_to_skip)}[/bold yellow] (already have policy)",
                )
                confirm_table.add_row(
                    "Action:", f"[bold green]SET ILM POLICY[/bold green]"
                )

                warning_panel = Panel(
                    confirm_table,
                    title="🔶  Confirm ILM Policy Assignment",
                    border_style="yellow",
                    padding=(1, 2),
                )
                console.print(warning_panel)

                # Ask for confirmation with updated text
                if len(indices_to_update) == 0:
                    confirm = (
                        input(
                            f"\nAll {len(matching_indices)} indices already have policy '{policy_name}'. Continue anyway? (yes/no): "
                        )
                        .lower()
                        .strip()
                    )
                else:
                    confirm = (
                        input(
                            f"\nAre you sure you want to set ILM policy '{policy_name}' on {len(indices_to_update)} indices ({len(indices_to_skip)} will be skipped)? (yes/no): "
                        )
                        .lower()
                        .strip()
                    )

                if confirm not in ["yes", "y"]:
                    self.es_client.show_message_box(
                        "Cancelled",
                        "ILM policy assignment cancelled.",
                        message_style="bold white",
                        panel_style="blue",
                    )
                    return

            # Perform bulk ILM policy assignment
            results = self.es_client.set_ilm_policy_for_indices(
                matching_indices,
                policy_name,
                dry_run=is_dry_run,
                max_concurrent=getattr(self.args, "max_concurrent", 5),
            )

            # Save results to JSON if requested
            if getattr(self.args, "save_json", None):
                self._save_set_indices_to_json(
                    results, self.args.save_json, source_description, policy_name
                )

            # Display results
            if self.args.format == "json":
                self.es_client.pretty_print_json(results)
            else:
                self.es_client.display_ilm_bulk_operation_results(
                    results, f"Policy Assignment ({policy_name})"
                )

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"Error during ILM policy assignment: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )

    def _load_indices_from_file(self, file_path):
        """Load indices list from a text file (one index per line) or JSON file."""
        try:
            with open(file_path, "r") as f:
                content = f.read().strip()

            # Try to parse as JSON first
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "indices" in data:
                    return data["indices"]
                else:
                    self.es_client.show_message_box(
                        "Invalid JSON Format",
                        f"JSON file must contain a list of indices or an object with 'indices' key.",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return None
            except json.JSONDecodeError:
                # Not JSON, treat as text file with one index per line
                indices = [line.strip() for line in content.split('\n') if line.strip()]
                return indices

        except FileNotFoundError:
            self.es_client.show_message_box(
                "File Not Found",
                f"File '{file_path}' not found.",
                message_style="bold white",
                panel_style="red",
            )
            return None
        except Exception as e:
            self.es_client.show_message_box(
                "File Load Error",
                f"Error loading file: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )
            return None

    def _load_indices_from_json(self, file_path):
        """Load indices list from JSON file (for backward compatibility)."""
        return self._load_indices_from_file(file_path)

    def _save_removed_indices_to_json(self, results, file_path, source):
        """Save removed indices results to JSON file."""
        try:
            output_data = {
                "operation": "remove_policy",
                "source": source,
                "timestamp": json.dumps(
                    {"timestamp": "now"}, default=str
                ),  # Placeholder for timestamp
                "results": results,
            }

            with open(file_path, "w") as f:
                json.dump(output_data, f, indent=2)

            print(f"Results saved to: {file_path}")

        except Exception as e:
            self.es_client.show_message_box(
                "Save Error",
                f"Error saving results to JSON file: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )

    def _save_set_indices_to_json(self, results, file_path, source, policy_name):
        """Save set policy results to JSON file."""
        try:
            output_data = {
                "operation": "set_policy",
                "policy_name": policy_name,
                "source": source,
                "timestamp": json.dumps(
                    {"timestamp": "now"}, default=str
                ),  # Placeholder for timestamp
                "results": results,
            }

            with open(file_path, "w") as f:
                json.dump(output_data, f, indent=2)

            print(f"Results saved to: {file_path}")

        except Exception as e:
            self.es_client.show_message_box(
                "Save Error",
                f"Error saving results to JSON file: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )

    def _handle_ilm_backup_policies(self):
        """
        Backup ILM policies for indices listed in a file.
        Reads a text file (one index per line) and saves a JSON file with each index and its ILM policy.
        """
        input_file = getattr(self.args, "input_file", None)
        output_file = getattr(self.args, "output_file", None)

        if not input_file:
            self.es_client.show_message_box(
                "Missing Argument",
                "Must provide --input-file containing list of indices.",
                message_style="bold white",
                panel_style="red",
            )
            return

        if not output_file:
            self.es_client.show_message_box(
                "Missing Argument",
                "Must provide --output-file to save the backup.",
                message_style="bold white",
                panel_style="red",
            )
            return

        try:
            # Load indices from input file
            indices = self._load_indices_from_file(input_file)
            if not indices:
                return  # Error already displayed

            # Get ILM policy for each index
            backup_data = {
                "operation": "backup_policies",
                "timestamp": datetime.now().isoformat(),
                "source_file": input_file,
                "indices": []
            }

            success_count = 0
            error_count = 0

            for index_name in indices:
                try:
                    # Get ILM explain for the index
                    explain_data = self.es_client.es.ilm.explain_lifecycle(index=index_name)

                    if 'indices' in explain_data and index_name in explain_data['indices']:
                        index_info = explain_data['indices'][index_name]
                        policy_name = index_info.get('policy', None)
                        managed = index_info.get('managed', False)

                        backup_data['indices'].append({
                            'index': index_name,
                            'policy': policy_name,
                            'managed': managed,
                            'phase': index_info.get('phase', None),
                            'action': index_info.get('action', None),
                            'step': index_info.get('step', None)
                        })
                        success_count += 1
                    else:
                        backup_data['indices'].append({
                            'index': index_name,
                            'policy': None,
                            'managed': False,
                            'error': 'Index not found in explain response'
                        })
                        error_count += 1

                except Exception as e:
                    backup_data['indices'].append({
                        'index': index_name,
                        'policy': None,
                        'managed': False,
                        'error': str(e)
                    })
                    error_count += 1

            # Save backup to output file
            with open(output_file, 'w') as f:
                json.dump(backup_data, f, indent=2)

            # Display results
            if self.args.format == "json":
                self.es_client.pretty_print_json(backup_data)
            else:
                from rich.panel import Panel
                from rich.text import Text

                summary = Text()
                summary.append(f"✅ Successfully backed up: {success_count} indices\n", style="bold green")
                if error_count > 0:
                    summary.append(f"🔶  Errors encountered: {error_count} indices\n", style="bold yellow")
                summary.append(f"\n📁 Backup saved to: {output_file}", style="bold cyan")

                self.console.print(Panel(
                    summary,
                    title="ILM Policy Backup Complete",
                    border_style="green",
                    padding=(1, 2)
                ))

        except Exception as e:
            self.es_client.show_message_box(
                "Backup Error",
                f"Error during ILM policy backup: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )

    def _handle_ilm_restore_policies(self):
        """
        Restore ILM policies from a backup JSON file.
        Reads the JSON file created by backup-policies and reapplies the policies.
        """
        input_file = getattr(self.args, "input_file", None)
        dry_run = getattr(self.args, "dry_run", False)

        if not input_file:
            self.es_client.show_message_box(
                "Missing Argument",
                "Must provide --input-file containing the backup.",
                message_style="bold white",
                panel_style="red",
            )
            return

        try:
            # Load backup file
            with open(input_file, 'r') as f:
                backup_data = json.load(f)

            if 'indices' not in backup_data:
                self.es_client.show_message_box(
                    "Invalid Backup File",
                    "Backup file must contain 'indices' array.",
                    message_style="bold white",
                    panel_style="red",
                )
                return

            indices_data = backup_data['indices']

            # Process each index
            results = {
                "operation": "restore_policies",
                "timestamp": datetime.now().isoformat(),
                "source_file": input_file,
                "dry_run": dry_run,
                "results": []
            }

            success_count = 0
            skip_count = 0
            error_count = 0

            for item in indices_data:
                index_name = item.get('index')
                policy_name = item.get('policy')

                if not policy_name or not item.get('managed', False):
                    results['results'].append({
                        'index': index_name,
                        'action': 'skipped',
                        'reason': 'No policy or not managed'
                    })
                    skip_count += 1
                    continue

                try:
                    if dry_run:
                        # Just report what would be done
                        results['results'].append({
                            'index': index_name,
                            'policy': policy_name,
                            'action': 'would_restore',
                            'status': 'dry_run'
                        })
                        success_count += 1
                    else:
                        # Actually restore the policy
                        body = {
                            "index": {
                                "lifecycle": {
                                    "name": policy_name
                                }
                            }
                        }
                        self.es_client.es.indices.put_settings(index=index_name, body=body)

                        results['results'].append({
                            'index': index_name,
                            'policy': policy_name,
                            'action': 'restored',
                            'status': 'success'
                        })
                        success_count += 1

                except Exception as e:
                    results['results'].append({
                        'index': index_name,
                        'policy': policy_name,
                        'action': 'restore',
                        'status': 'error',
                        'error': str(e)
                    })
                    error_count += 1

            # Display results
            if self.args.format == "json":
                self.es_client.pretty_print_json(results)
            else:
                from rich.panel import Panel
                from rich.text import Text

                summary = Text()
                if dry_run:
                    summary.append("🔍 DRY RUN - No changes made\n\n", style="bold yellow")

                summary.append(f"✅ Successfully restored: {success_count} policies\n", style="bold green")
                if skip_count > 0:
                    summary.append(f"💤 Skipped (no policy): {skip_count} indices\n", style="bold blue")
                if error_count > 0:
                    summary.append(f"❌ Errors encountered: {error_count} indices\n", style="bold red")

                if not dry_run:
                    summary.append(f"\n📊 Total indices processed: {len(indices_data)}", style="bold cyan")

                self.console.print(Panel(
                    summary,
                    title="ILM Policy Restore Complete" if not dry_run else "ILM Policy Restore Preview",
                    border_style="green" if error_count == 0 else "yellow",
                    padding=(1, 2)
                ))

        except FileNotFoundError:
            self.es_client.show_message_box(
                "File Not Found",
                f"Backup file '{input_file}' not found.",
                message_style="bold white",
                panel_style="red",
            )
        except json.JSONDecodeError as e:
            self.es_client.show_message_box(
                "Invalid JSON",
                f"Invalid JSON in backup file: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )
        except Exception as e:
            self.es_client.show_message_box(
                "Restore Error",
                f"Error during ILM policy restore: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )

    def _show_ilm_help(self):
        """Display ILM help menu with available commands and examples."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()

        # Get theme styles for consistent theming
        from esclient import get_theme_styles

        styles = get_theme_styles(self.es_client.configuration_manager)

        # Create command table
        help_table = Table.grid(padding=(0, 3))
        help_table.add_column(
            style=styles.get("health_styles", {})
            .get("green", {})
            .get("text", "bold cyan"),
            min_width=15,
        )
        help_table.add_column(style=styles.get("border_style", "white"))

        help_table.add_row("📊 status", "Show comprehensive ILM status and statistics")
        help_table.add_row(
            "📋 policies", "List all ILM policies with phase configurations"
        )
        help_table.add_row(
            "🔍 policy <name>", "Show detailed configuration for specific ILM policy"
        )
        help_table.add_row("🔎 explain <index>", "Show ILM status for specific index")
        help_table.add_row("🔶 errors", "Show indices with ILM errors")
        help_table.add_row(
            "➕ set-policy <policy> …",
            "Assign ILM policy (pattern, --file, or --from-policy)",
        )
        help_table.add_row(
            "➖ remove-policy <pattern>",
            "Remove ILM policy from indices matching pattern",
        )
        help_table.add_row(
            "🆕 create-policy <name> <json>",
            "Create new ILM policy from JSON definition or file",
        )
        help_table.add_row("🗑 delete-policy <name>", "Delete an existing ILM policy")
        help_table.add_row(
            "💾 backup-policies --input-file <file> --output-file <file>",
            "Backup ILM policies for indices to JSON file",
        )
        help_table.add_row(
            "🔄 restore-policies --input-file <file>",
            "Restore ILM policies from backup JSON file",
        )
        help_table.add_row(
            "📂 index-patterns <name>",
            "Show unique index base patterns (date stripped) for a policy",
        )

        # Create examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(
            style=styles.get("health_styles", {})
            .get("green", {})
            .get("text", "bold green"),
            min_width=15,
        )
        examples_table.add_column(style=styles.get("border_style", "white"))

        examples_table.add_row("Basic Status:", "./escmd.py ilm status")
        examples_table.add_row("List Policies:", "./escmd.py ilm policies")
        examples_table.add_row("Policy Details:", "./escmd.py ilm policy logs")
        examples_table.add_row("Check Index:", "./escmd.py ilm explain myindex-001")
        examples_table.add_row(
            "Set Policy:", "./escmd.py ilm set-policy 30-days-default 'logs-*'"
        )
        examples_table.add_row(
            "Migrate by policy:",
            "./escmd.py ilm set-policy new-policy --from-policy old-policy --dry-run",
        )
        examples_table.add_row(
            "Remove Policy:", "./escmd.py ilm remove-policy 'temp-*'"
        )
        examples_table.add_row(
            "Create Policy:", "./escmd.py ilm create-policy my-policy policy.json"
        )
        examples_table.add_row(
            "Delete Policy:", "./escmd.py ilm delete-policy old-policy"
        )
        examples_table.add_row(
            "Inline JSON:", "./escmd.py ilm create-policy test '{\"policy\":{...}}'"
        )
        examples_table.add_row("JSON Output:", "./escmd.py ilm status --format json")
        examples_table.add_row(
            "Backup Policies:", "./escmd.py ilm backup-policies --input-file indices.txt --output-file backup.json"
        )
        examples_table.add_row(
            "Restore Policies:", "./escmd.py ilm restore-policies --input-file backup.json"
        )
        examples_table.add_row(
            "Restore (Dry Run):", "./escmd.py ilm restore-policies --input-file backup.json --dry-run"
        )
        examples_table.add_row(
            "Index Patterns:", "./escmd.py ilm index-patterns my-policy"
        )
        examples_table.add_row(
            "Patterns (all):", "./escmd.py ilm index-patterns my-policy --show-all"
        )

        # Display help
        print()
        console.print(
            Panel(
                help_table,
                title="🔄 Index Lifecycle Management (ILM) Commands",
                border_style="blue",
                padding=(1, 2),
            )
        )

        print()
        console.print(
            Panel(
                examples_table,
                title="🚀 Usage Examples",
                border_style="green",
                padding=(1, 2),
            )
        )
        print()

    def _handle_ilm_create_policy(self):
        """
        Handle ILM policy creation from JSON definition (inline or file).
        """
        import json
        import os

        policy_name = self.args.policy_name
        policy_definition = getattr(self.args, "policy_definition", None)
        policy_file = getattr(self.args, "file", None)

        try:
            # Determine policy source and load JSON
            policy_json = None
            source_description = ""

            if policy_file:
                # Load from file specified with --file
                if not os.path.exists(policy_file):
                    self.es_client.show_message_box(
                        "File Not Found",
                        f"Policy file '{policy_file}' not found.",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return

                try:
                    with open(policy_file, "r") as f:
                        policy_json = json.load(f)
                    source_description = f"file: {policy_file}"
                except json.JSONDecodeError as e:
                    self.es_client.show_message_box(
                        "Invalid JSON",
                        f"Invalid JSON in file '{policy_file}': {str(e)}",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return
                except Exception as e:
                    self.es_client.show_message_box(
                        "File Error",
                        f"Error reading policy file: {str(e)}",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return

            elif policy_definition:
                # Check if it's a file path or inline JSON
                if os.path.exists(policy_definition):
                    # It's a file path
                    try:
                        with open(policy_definition, "r") as f:
                            policy_json = json.load(f)
                        source_description = f"file: {policy_definition}"
                    except json.JSONDecodeError as e:
                        self.es_client.show_message_box(
                            "Invalid JSON",
                            f"Invalid JSON in file '{policy_definition}': {str(e)}",
                            message_style="bold white",
                            panel_style="red",
                        )
                        return
                    except Exception as e:
                        self.es_client.show_message_box(
                            "File Error",
                            f"Error reading policy file: {str(e)}",
                            message_style="bold white",
                            panel_style="red",
                        )
                        return
                else:
                    # It's inline JSON - but first check if it might be a typo for a filename
                    if policy_definition.endswith(
                        ".json"
                    ) and not policy_definition.startswith("{"):
                        self.es_client.show_message_box(
                            "File Not Found",
                            f"Policy file '{policy_definition}' not found.",
                            message_style="bold white",
                            panel_style="red",
                        )
                        return
                    try:
                        policy_json = json.loads(policy_definition)
                        source_description = "inline JSON"
                    except json.JSONDecodeError as e:
                        self.es_client.show_message_box(
                            "Invalid JSON",
                            f"Invalid inline JSON: {str(e)}",
                            message_style="bold white",
                            panel_style="red",
                        )
                        return
            else:
                self.es_client.show_message_box(
                    "Missing Policy Definition",
                    "Please provide either:\n- Inline JSON: ./escmd.py ilm create-policy my-policy '{\"policy\":{...}}'\n- File path: ./escmd.py ilm create-policy my-policy policy.json\n- Or use --file flag: ./escmd.py ilm create-policy my-policy --file policy.json",
                    message_style="bold white",
                    panel_style="red",
                )
                return

            # Validate policy structure
            if not isinstance(policy_json, dict):
                self.es_client.show_message_box(
                    "Invalid Policy Structure",
                    "Policy definition must be a JSON object.",
                    message_style="bold white",
                    panel_style="red",
                )
                return

            # Create the policy using the ES client
            result = self.es_client.create_ilm_policy(policy_name, policy_json)

            # Handle results
            if isinstance(result, dict) and "error" in result:
                self.es_client.show_message_box(
                    "Policy Creation Failed",
                    f"Failed to create ILM policy '{policy_name}': {result['error']}",
                    message_style="bold white",
                    panel_style="red",
                )
            else:
                if self.args.format == "json":
                    self.es_client.pretty_print_json(
                        {
                            "policy_name": policy_name,
                            "source": source_description,
                            "result": result,
                            "status": "created",
                        }
                    )
                else:
                    # Display success message with policy summary
                    from rich.panel import Panel
                    from rich.text import Text
                    from rich.table import Table

                    console = self.console

                    # Create summary table
                    summary_table = Table(show_header=False, box=None, padding=(0, 1))
                    summary_table.add_column(
                        "Property", style="bold cyan", no_wrap=True
                    )
                    summary_table.add_column("Value", style="white")

                    summary_table.add_row("Policy Name:", policy_name)
                    summary_table.add_row("Source:", source_description)
                    summary_table.add_row(
                        "Status:", "[bold green]✓ Created Successfully[/bold green]"
                    )

                    # Extract phases info for display
                    if "policy" in policy_json and "phases" in policy_json["policy"]:
                        phases = list(policy_json["policy"]["phases"].keys())
                        summary_table.add_row("Phases:", ", ".join(phases))

                    success_panel = Panel(
                        summary_table,
                        title="🎯 ILM Policy Created",
                        border_style="green",
                        padding=(1, 2),
                    )
                    console.print(success_panel)

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"Error creating ILM policy: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )

    def _handle_ilm_delete_policy(self):
        """
        Handle ILM policy deletion.
        """
        policy_name = self.args.policy_name

        try:
            # First, check if the policy exists
            if not self.es_client.validate_ilm_policy_exists(policy_name):
                self.es_client.show_message_box(
                    "Policy Not Found",
                    f"ILM policy '{policy_name}' does not exist.",
                    message_style="bold white",
                    panel_style="red",
                )
                return

            # Get policy details for confirmation display
            try:
                policy_details = self.es_client.es.ilm.get_lifecycle(policy=policy_name)
                if hasattr(policy_details, "body"):
                    policy_info = policy_details.body
                elif hasattr(policy_details, "get"):
                    policy_info = dict(policy_details)
                else:
                    policy_info = policy_details

                # Extract phases info for display
                phases = []
                if (
                    policy_name in policy_info
                    and "policy" in policy_info[policy_name]
                    and "phases" in policy_info[policy_name]["policy"]
                ):
                    phases = list(policy_info[policy_name]["policy"]["phases"].keys())
            except Exception as e:
                # If we can't get details, still allow deletion but with less info
                phases = ["unknown"]

            # Show confirmation unless --yes is specified
            if not getattr(self.args, "yes", False):
                from rich.panel import Panel
                from rich.table import Table
                from rich.text import Text

                console = self.console

                # Create confirmation table
                confirm_table = Table(show_header=False, box=None, padding=(0, 1))
                confirm_table.add_column("Property", style="bold yellow", no_wrap=True)
                confirm_table.add_column("Value", style="white")

                confirm_table.add_row("Policy Name:", policy_name)
                confirm_table.add_row(
                    "Phases:", ", ".join(phases) if phases else "none"
                )
                confirm_table.add_row("Action:", "[bold red]DELETE[/bold red]")

                warning_panel = Panel(
                    confirm_table,
                    title="🔶  Confirm ILM Policy Deletion",
                    border_style="yellow",
                    padding=(1, 2),
                )
                console.print(warning_panel)

                # Ask for confirmation
                confirm = (
                    input(
                        "\nAre you sure you want to delete this ILM policy? (yes/no): "
                    )
                    .lower()
                    .strip()
                )
                if confirm not in ["yes", "y"]:
                    self.es_client.show_message_box(
                        "Cancelled",
                        "ILM policy deletion cancelled.",
                        message_style="bold white",
                        panel_style="blue",
                    )
                    return

            # Delete the policy
            result = self.es_client.delete_ilm_policy(policy_name)

            # Handle results
            if isinstance(result, dict) and "error" in result:
                self.es_client.show_message_box(
                    "Policy Deletion Failed",
                    f"Failed to delete ILM policy '{policy_name}': {result['error']}",
                    message_style="bold white",
                    panel_style="red",
                )
            else:
                if self.args.format == "json":
                    self.es_client.pretty_print_json(
                        {
                            "policy_name": policy_name,
                            "phases": phases,
                            "result": result,
                            "status": "deleted",
                        }
                    )
                else:
                    # Display success message
                    from rich.panel import Panel
                    from rich.table import Table

                    console = self.console

                    # Create success table
                    success_table = Table(show_header=False, box=None, padding=(0, 1))
                    success_table.add_column(
                        "Property", style="bold cyan", no_wrap=True
                    )
                    success_table.add_column("Value", style="white")

                    success_table.add_row("Policy Name:", policy_name)
                    success_table.add_row(
                        "Phases:", ", ".join(phases) if phases else "none"
                    )
                    success_table.add_row(
                        "Status:", "[bold green]✓ Deleted Successfully[/bold green]"
                    )

                    success_panel = Panel(
                        success_table,
                        title="🗑 ILM Policy Deleted",
                        border_style="green",
                        padding=(1, 2),
                    )
                    console.print(success_panel)

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"Error deleting ILM policy: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )
