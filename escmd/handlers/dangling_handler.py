#!/usr/bin/env python3

import json
import logging
import subprocess
import sys
import time
import os
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table, Table as InnerTable
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)

from .base_handler import BaseHandler
from metrics.dangling_metrics import DanglingMetrics


class DanglingHandler(BaseHandler):
    """Handler for Elasticsearch dangling indices operations."""

    def handle_dangling(self):
        """Handle dangling indices command - list, delete, or cleanup all based on arguments."""
        console = self.console

        try:
            # Use the logger passed from the command handler, or set up local logging
            logger = self.logger
            if hasattr(self.args, "log_file") and self.args.log_file:
                logger = self._setup_dangling_logging(self.args.log_file)

            # Log the start of dangling command execution
            if logger:
                logger.info("Starting dangling indices operation")
                logger.info(
                    f"Command arguments: cleanup_all={getattr(self.args, 'cleanup_all', False)}, "
                    f"group={getattr(self.args, 'group', None)}, "
                    f"env={getattr(self.args, 'env', None)}, "
                    f"metrics={getattr(self.args, 'metrics', False)}"
                )

            # Initialize metrics if --metrics flag is specified
            metrics_handler = None
            if hasattr(self.args, "metrics") and self.args.metrics:
                metrics_handler = DanglingMetrics(
                    config_manager=self.es_client.configuration_manager,
                    environment=getattr(self.args, "env", None),
                )
                if not metrics_handler.is_enabled():
                    error_msg = "Metrics are enabled but not properly configured"
                    if logger:
                        logger.error(error_msg)
                    self.es_client.show_message_box(
                        "Metrics Configuration Error",
                        "❌ Metrics are enabled but not properly configured.\n\n"
                        + "Please configure metrics in escmd.yml or set environment variables:\n"
                        + "- ESCMD_METRICS_ENDPOINT\n"
                        + "- ESCMD_METRICS_DATABASE (optional)\n"
                        + "- ESCMD_METRICS_USERNAME (optional)\n"
                        + "- ESCMD_METRICS_PASSWORD (optional)",
                        message_style="bold red",
                        border_style="red",
                    )
                    return
                else:
                    if logger:
                        logger.info("Metrics handler initialized and enabled")

            # Check for cleanup all functionality with group/environment scope
            if hasattr(self.args, "cleanup_all") and self.args.cleanup_all:
                if hasattr(self.args, "group") and self.args.group:
                    if logger:
                        logger.info(
                            f"Starting group cleanup for group: {self.args.group}"
                        )
                    self._handle_group_cleanup_all(logger)
                    return
                elif hasattr(self.args, "env") and self.args.env:
                    if logger:
                        logger.info(
                            f"Starting environment cleanup for env: {self.args.env}"
                        )
                    self._handle_environment_cleanup_all(logger)
                    return
                else:
                    if logger:
                        logger.info("Starting cleanup all operation")
                    self._handle_dangling_cleanup_all(logger)
                    return

            # Check for cluster group report functionality
            if hasattr(self.args, "group") and self.args.group:
                if logger:
                    logger.info(
                        f"Starting cluster group report for group: {self.args.group}"
                    )
                self._handle_cluster_group_report()
                return

            # Check for environment report functionality
            if hasattr(self.args, "env") and self.args.env:
                if logger:
                    logger.info(f"Starting environment report for env: {self.args.env}")
                self._handle_environment_report()
                return

            # Check if deletion is requested for single index
            if hasattr(self.args, "delete") and self.args.delete:
                if hasattr(self.args, "uuid") and self.args.uuid:
                    if logger:
                        logger.info(
                            f"Starting single index deletion for UUID: {self.args.uuid}"
                        )
                    self._handle_dangling_delete()
                    return
                else:
                    error_msg = "UUID is required for deletion"
                    if logger:
                        logger.error(error_msg)
                    self.es_client.show_message_box(
                        "Missing UUID Parameter",
                        "❌ UUID is required for deletion.\nUsage: ./escmd.py dangling <uuid> --delete",
                        message_style="bold red",
                        border_style="red",
                    )
                    return

            # Regular listing functionality
            if logger:
                logger.info("Starting dangling indices listing operation")

            # Regular listing functionality (existing code)
            # Get dangling indices data first
            if logger:
                logger.info("Retrieving dangling indices from cluster")
            dangling_result = self._get_dangling_indices_enhanced()

            if "error" in dangling_result:
                error_msg = (
                    f"Error retrieving dangling indices: {dangling_result['error']}"
                )
                if logger:
                    logger.error(error_msg)
                self.es_client.show_message_box(
                    "Error",
                    f"❌ {error_msg}",
                    message_style="bold red",
                    panel_style="red",
                )
                return

            dangling_indices = dangling_result.get("dangling_indices", [])
            if logger:
                logger.info(f"Found {len(dangling_indices)} dangling indices")

            # Get cluster information for context
            try:
                if logger:
                    logger.debug("Retrieving cluster health information")
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get("cluster_name", "Unknown")
                total_nodes = health_data.get("number_of_nodes", 0)
                if logger:
                    logger.info(f"Cluster: {cluster_name}, Nodes: {total_nodes}")
            except Exception as e:
                cluster_name = "Unknown"
                total_nodes = 0
                if logger:
                    logger.warning(f"Failed to retrieve cluster health: {str(e)}")

            # Send metrics if metrics flag is enabled
            if metrics_handler:
                # Count unique nodes affected
                nodes_affected = set()
                for index in dangling_indices:
                    node_ids = index.get("node_ids", [])
                    nodes_affected.update(node_ids)

                nodes_affected_count = len(nodes_affected)
                found_count = len(dangling_indices)
                dry_run = getattr(self.args, "dry_run", False)

                if logger:
                    logger.info(
                        f"Sending metrics: found={found_count}, nodes_affected={nodes_affected_count}, dry_run={dry_run}"
                    )

                success = metrics_handler.send_dangling_metric(
                    cluster_name=cluster_name,
                    found=found_count,
                    deleted=0,  # No deletion in list mode
                    nodes_affected=nodes_affected_count,
                    dry_run=dry_run,
                )

                if logger:
                    logger.info(f"Metrics sent successfully: {success}")

                if success:
                    if not dry_run:
                        self.es_client.show_message_box(
                            "Metrics Sent Successfully",
                            f"✅ Dangling indices metrics sent to database:\n\n"
                            + f"• Cluster: {cluster_name}\n"
                            + f"• Found: {found_count}\n"
                            + f"• Nodes Affected: {nodes_affected_count}",
                            message_style="bold green",
                            border_style="green",
                        )
                else:
                    self.es_client.show_message_box(
                        "Metrics Send Failed",
                        "❌ Failed to send metrics to database.\n"
                        + "Check logs for more details.",
                        message_style="bold yellow",
                        border_style="yellow",
                    )
                return  # Exit early when metrics mode is used

            # Handle JSON format - return immediately with pure JSON output
            if getattr(self.args, "format", "table") == "json":
                self.es_client.pretty_print_json({"dangling_indices": dangling_indices})
                return

            # Calculate statistics
            total_dangling = len(dangling_indices)
            unique_nodes = set()
            creation_dates = []

            for idx in dangling_indices:
                node_ids = idx.get("node_ids", [])
                unique_nodes.update(node_ids)
                creation_date = idx.get("creation_date", "Unknown")
                if creation_date != "Unknown":
                    creation_dates.append(creation_date)

            ss = self.es_client.style_system

            # Build colorized subtitle — same pattern as shards/storage/ilm commands
            subtitle_rich = Text()
            subtitle_rich.append("Cluster: ", style="default")
            subtitle_rich.append(cluster_name, style=ss._get_style('semantic', 'info', 'cyan') if ss else "cyan")
            subtitle_rich.append(" | Nodes: ", style="default")
            subtitle_rich.append(str(total_nodes), style=ss._get_style('semantic', 'primary', 'bright_magenta') if ss else "bright_magenta")

            # Check if there are dangling indices
            if not dangling_indices:
                subtitle_rich.append(" | Status: ", style="default")
                subtitle_rich.append("✅ Clean", style=ss._get_style('semantic', 'success', 'green') if ss else "green")

                clean_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                clean_table.add_column("Icon", justify="left", width=3)
                clean_table.add_column("Detail", no_wrap=True)

                clean_table.add_row("🎉", ss.create_semantic_text("No dangling indices found in the cluster!", "success") if ss else Text("No dangling indices found in the cluster!", style="green"))
                clean_table.add_row("✅", Text("All indices are properly assigned to nodes"))
                clean_table.add_row("✅", Text("No orphaned index metadata exists"))
                clean_table.add_row("✅", Text("Cluster index management is healthy"))

                clean_panel = Panel(
                    clean_table,
                    title=f"[{ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'}]🔍 Dangling Indices Analysis[/{ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'}]",
                    subtitle=subtitle_rich,
                    border_style=ss._get_style('semantic', 'success', 'green') if ss else "green",
                    padding=(1, 2),
                )
                print()
                console.print(clean_panel)
                print()

                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style=ss._get_style('semantic', 'primary', 'bold cyan') if ss else "bold cyan", no_wrap=True)
                actions_table.add_column("Command", style=ss._get_style('semantic', 'muted', 'dim white') if ss else "dim white")

                actions_table.add_row("Check cluster health:", "./escmd.py health")
                actions_table.add_row("List all indices:", "./escmd.py indices")
                actions_table.add_row("View cluster nodes:", "./escmd.py nodes")
                actions_table.add_row("Monitor recovery:", "./escmd.py recovery")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Related Commands",
                    border_style=ss._get_style('table_styles', 'border_style', 'cyan') if ss else "cyan",
                    padding=(1, 2),
                )

                print()
                console.print(actions_panel)
                print()
                return

            # Dangling indices found — add counts to subtitle
            subtitle_rich.append(" | Dangling: ", style="default")
            subtitle_rich.append(str(total_dangling), style=ss._get_style('semantic', 'warning', 'orange1') if ss else "orange1")
            subtitle_rich.append(" | Affected Nodes: ", style="default")
            subtitle_rich.append(str(len(unique_nodes)), style=ss._get_style('semantic', 'error', 'red') if ss else "red")

            stats_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            stats_table.add_column("Label", style="bold", no_wrap=True)
            stats_table.add_column("Icon", justify="left", width=3)
            stats_table.add_column("Value", no_wrap=True)

            stats_table.add_row("Status:", "🔶", ss.create_semantic_text("Dangling indices detected", "warning") if ss else Text("Dangling indices detected", style="yellow"))
            stats_table.add_row("Total Dangling:", "🔶", ss.create_semantic_text(f"{total_dangling:,}", "warning") if ss else Text(f"{total_dangling:,}", style="yellow"))
            stats_table.add_row("Affected Nodes:", "💻", ss.create_semantic_text(f"{len(unique_nodes):,}", "error") if ss else Text(f"{len(unique_nodes):,}", style="red"))
            stats_table.add_row("Cluster Nodes:", "📊", ss.create_semantic_text(f"{total_nodes:,}", "info") if ss else Text(f"{total_nodes:,}", style="cyan"))

            if creation_dates:
                oldest_date = min(creation_dates)
                stats_table.add_row("Oldest Found:", "📅", ss.create_semantic_text(oldest_date, "muted") if ss else Text(oldest_date, style="dim"))

            title_panel = Panel(
                stats_table,
                title=f"[{ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'}]🔍 Dangling Indices Analysis[/{ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'}]",
                subtitle=subtitle_rich,
                border_style=ss._get_style('semantic', 'warning', 'orange1') if ss else "orange1",
                padding=(1, 2),
            )

            print()
            console.print(title_panel)
            print()

            # Get node mapping once for efficient hostname resolution
            node_id_to_hostname_map = self.es_client.get_node_id_to_hostname_map()

            # Get theme styles for consistent theming
            from esclient import get_theme_styles

            styles = get_theme_styles(self.es_client.configuration_manager)

            # Create detailed dangling indices table
            table = Table(
                show_header=True,
                header_style=styles["header_style"],
                expand=True,
                box=self.es_client.style_system.get_table_box(),
            )
            table.add_column(
                "🆔 Index UUID",
                style=styles.get("health_styles", {})
                .get("green", {})
                .get("text", "cyan"),
                no_wrap=True,
                width=38,
            )
            table.add_column(
                "📅 Creation Date",
                style=styles.get("health_styles", {})
                .get("yellow", {})
                .get("text", "yellow"),
                width=20,
                no_wrap=True,
            )
            table.add_column(
                "💻 Hostnames",
                style=styles.get("status_styles", {})
                .get("close", {})
                .get("text", "magenta"),
                no_wrap=False,
            )
            table.add_column(
                "📊 Node Count",
                style=styles.get("border_style", "white"),
                width=12,
                justify="center",
            )

            # Add rows to the table
            for idx in dangling_indices:
                index_uuid = idx.get("index_uuid", "N/A")
                creation_date = idx.get("creation_date", "N/A")
                node_ids = idx.get("node_ids", [])
                node_count = len(node_ids)

                # Resolve node IDs to hostnames using pre-built mapping
                if node_ids:
                    hostnames = self.es_client.resolve_node_ids_to_hostnames(
                        node_ids, node_id_to_hostname_map
                    )
                    # Format hostnames - truncate if too many
                    if len(hostnames) > 3:
                        node_display = (
                            ", ".join(hostnames[:3]) + f" (+{len(hostnames) - 3} more)"
                        )
                    else:
                        node_display = ", ".join(hostnames)
                else:
                    node_display = "N/A"

                # Color coding based on node count
                if node_count > 1:
                    row_style = "yellow"  # Multiple nodes have this dangling index
                elif node_count == 1:
                    row_style = "red"  # Only one node has this index
                else:
                    row_style = "dim"  # No nodes specified

                table.add_row(
                    index_uuid,
                    creation_date,
                    node_display,
                    str(node_count),
                    style=row_style,
                )

            # Create table panel
            table_panel = Panel(
                table,
                title="🔶 Dangling Indices Details",
                border_style="orange1",
                padding=(1, 2),
            )

            console.print(table_panel)
            print()

            # Create warning and actions panel
            warning_text = (
                "🔶 WARNING: Dangling indices detected!\n\n"
                f"Found {total_dangling} dangling indices across {len(unique_nodes)} nodes.\n"
                "These indices contain data that is not accessible through normal cluster operations.\n\n"
                "🚨 IMPORTANT: Review these indices carefully before taking action.\n"
                "Consider consulting Elasticsearch documentation for recovery procedures."
            )

            warning_panel = Panel(
                warning_text,
                title="🚨 Action Required",
                border_style=self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 2),
            )

            # Create recovery actions panel
            recovery_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            recovery_table.add_column(
                "Action",
                style=self.es_client.style_system.get_semantic_style("error"),
                no_wrap=True,
            )
            recovery_table.add_column(
                "Command",
                style=self.es_client.style_system.get_semantic_style("secondary"),
            )

            recovery_table.add_row(
                "Delete Single Index:", f"./escmd.py dangling <uuid> --delete"
            )
            recovery_table.add_row(
                "Delete All (Dry Run):", f"./escmd.py dangling --cleanup-all --dry-run"
            )
            recovery_table.add_row(
                "Delete All (DANGER):",
                f"./escmd.py dangling --cleanup-all --yes-i-really-mean-it",
            )
            recovery_table.add_row(
                "Check Logs:", "Review Elasticsearch logs for root cause"
            )

            recovery_panel = Panel(
                recovery_table,
                title="🔧 Recovery Options",
                border_style=self.es_client.style_system.get_semantic_style("primary"),
                padding=(1, 2),
            )

            console.print(Columns([warning_panel, recovery_panel], expand=True))
            print()

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"❌ Error handling dangling indices: {str(e)}",
                message_style="bold red",
                panel_style="red",
            )

    def _setup_dangling_logging(self, log_file=None):
        """
        Set up logging for dangling operations.

        Args:
            log_file: Optional path to log file

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger("dangling_cleanup")
        logger.setLevel(logging.INFO)

        # Clear any existing handlers
        logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Add console handler (always works)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Add file handler if specified
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                logger.info(f"Logging to file: {log_file}")
            except Exception as e:
                logger.warning(f"Could not set up file logging to {log_file}: {e}")

        return logger

    def _delete_dangling_index_with_retry(
        self,
        index_uuid,
        index_name=None,
        max_retries=3,
        retry_delay=5,
        dry_run=False,
        logger=None,
    ):
        """
        Delete a single dangling index with retry logic.

        Args:
            index_uuid: UUID of the dangling index
            index_name: Optional name of the index for logging
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retry attempts
            dry_run: If True, only simulate the deletion
            logger: Logger instance for output

        Returns:
            True if deletion successful, False otherwise
        """
        if not logger:
            logger = self.logger or logging.getLogger("dangling_cleanup")

        index_info = (
            f"'{index_name}' ({index_uuid})" if index_name else f"UUID: {index_uuid}"
        )

        if dry_run:
            logger.info(f"DRY RUN: Would delete dangling index {index_info}")
            return True

        # Retry logic for dangling index deletion
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(
                        f"Retrying deletion of dangling index {index_info} (attempt {attempt}/{max_retries})"
                    )
                else:
                    logger.info(f"Deleting dangling index {index_info}")

                # Delete the dangling index using the existing method
                delete_response = self.es_client.delete_dangling_index(index_uuid)

                if "error" in delete_response:
                    error_msg = delete_response["error"]

                    # Check if this is a retryable error
                    if attempt < max_retries and (
                        "timeout" in error_msg.lower() or "503" in str(error_msg)
                    ):
                        logger.warning(
                            f"Retryable error deleting dangling index {index_info}: {error_msg}"
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(
                            f"Error deleting dangling index {index_info}: {error_msg}"
                        )
                        return False

                logger.info(f"Successfully deleted dangling index {index_info}")
                return True

            except Exception as e:
                # Handle specific error types
                error_msg = str(e)

                if "process_cluster_event_timeout_exception" in error_msg:
                    if attempt < max_retries:
                        logger.warning(
                            f"Timeout deleting dangling index {index_info} - retrying in {retry_delay} seconds"
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.warning(
                            f"Timeout deleting dangling index {index_info} after {max_retries} attempts. The deletion may still complete in the background."
                        )
                        return True  # Consider this a partial success

                elif "No dangling index found for UUID" in error_msg:
                    logger.warning(
                        f"Dangling index {index_info} was already cleaned up or doesn't exist anymore - skipping"
                    )
                    return True  # Consider this a success as the index is already gone

                elif (
                    "illegal_argument_exception" in error_msg
                    and "No dangling index found" in error_msg
                ):
                    logger.warning(
                        f"Dangling index {index_info} no longer exists - likely already cleaned up"
                    )
                    return True

                else:
                    if attempt < max_retries:
                        logger.warning(
                            f"Error deleting dangling index {index_info}: {e} - retrying in {retry_delay} seconds"
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(
                            f"Error deleting dangling index {index_info} after {max_retries} attempts: {e}"
                        )
                        return False

        return False

    def _get_dangling_indices_enhanced(self):
        """
        Get dangling indices with enhanced error handling.

        Returns:
            Dictionary with dangling_indices list or error information
        """
        try:
            return self.es_client.list_dangling_indices()
        except Exception as e:
            return {"error": str(e)}

    def _handle_dangling_cleanup_all(self, logger=None):
        """Handle cleanup of all dangling indices with confirmation and logging."""
        from rich.progress import (
            Progress,
            SpinnerColumn,
            TextColumn,
            BarColumn,
            TaskProgressColumn,
        )

        console = self.console
        if not logger:
            logger = self.logger or logging.getLogger("dangling_cleanup")

        # Initialize metrics if --metrics flag is specified
        metrics_handler = None
        if hasattr(self.args, "metrics") and self.args.metrics:
            if logger:
                logger.info("Initializing metrics handler for cleanup all operation")
            metrics_handler = DanglingMetrics(
                config_manager=self.es_client.configuration_manager,
                environment=getattr(self.args, "env", None),
            )
            if not metrics_handler.is_enabled():
                self.es_client.show_message_box(
                    "Metrics Configuration Error",
                    "❌ Metrics are enabled but not properly configured.\n\n"
                    + "Please configure metrics in escmd.yml or set environment variables:\n"
                    + "- ESCMD_METRICS_ENDPOINT\n"
                    + "- ESCMD_METRICS_DATABASE (optional)\n"
                    + "- ESCMD_METRICS_USERNAME (optional)\n"
                    + "- ESCMD_METRICS_PASSWORD (optional)",
                    message_style="bold red",
                    border_style="red",
                )
                return

        try:
            # First, get the list of dangling indices
            with console.status("[bold blue]Scanning for dangling indices..."):
                dangling_result = self._get_dangling_indices_enhanced()

            if "error" in dangling_result:
                self.es_client.show_message_box(
                    "Error",
                    f"❌ Error retrieving dangling indices: {dangling_result['error']}",
                    message_style="bold red",
                    border_style="red",
                )
                return

            dangling_indices = dangling_result.get("dangling_indices", [])

            if not dangling_indices:
                self.es_client.show_message_box(
                    "Cluster is clean",
                    "✅ No dangling indices found to clean up!",
                    message_style="bold green",
                    border_style="green",
                )
                return

            total_count = len(dangling_indices)

            # Handle batch processing
            batch_size = getattr(self.args, "batch", None)
            if batch_size is not None and batch_size > 0:
                if batch_size > total_count:
                    console.print(
                        f"[bold yellow]🔶 Batch size ({batch_size}) is larger than available indices ({total_count}). Processing all {total_count} indices.[/bold yellow]"
                    )
                    batch_size = total_count
                else:
                    dangling_indices = dangling_indices[:batch_size]
                    console.print(
                        f"[bold blue]📦 Batch mode: Processing {batch_size} out of {total_count} dangling indices.[/bold blue]"
                    )
                    print()

            # Update count after potential batch limiting
            processing_count = len(dangling_indices)

            # Get node mapping for hostname resolution
            node_id_to_hostname_map = self.es_client.get_node_id_to_hostname_map()

            # Check for dry run mode
            dry_run = hasattr(self.args, "dry_run") and self.args.dry_run

            # Create summary panel
            batch_text = ""
            if batch_size is not None and batch_size > 0:
                batch_text = f" (batch of {processing_count}/{total_count})"

            summary_text = f"Found {processing_count} dangling indices to {'simulate deletion' if dry_run else 'delete'}{batch_text}.\n\n"
            if dry_run:
                summary_text += "🔍 DRY RUN MODE: No actual deletions will occur.\n"
                summary_text += "This is a simulation to show what would be deleted."
            else:
                summary_text += (
                    "🔶 DANGER: This will permanently delete all dangling indices!\n"
                )
                summary_text += "This action cannot be undone."

            batch_title_text = ""
            if batch_size is not None and batch_size > 0:
                batch_title_text = f" (Batch: {processing_count}/{total_count})"

            summary_panel = Panel(
                Text(summary_text, justify="center"),
                title=f"🧹 Cleanup {'Batch of ' if batch_size else ''}Dangling Indices{batch_title_text} {'(DRY RUN)' if dry_run else ''}",
                border_style=self.es_client.style_system.get_semantic_style("warning")
                if dry_run
                else self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 1),
            )

            print()
            console.print(summary_panel)
            print()

            # Always show "What Would Be Deleted" table (for both dry-run and production modes)
            preview_title = (
                "Indices Scheduled for Deletion (DRY RUN)"
                if dry_run
                else "Indices Scheduled for Deletion"
            )
            self._show_deletion_preview(
                dangling_indices, node_id_to_hostname_map, dry_run, preview_title
            )

            print()

            # Safety confirmation (unless --yes-i-really-mean-it is used)
            if not dry_run and not (
                hasattr(self.args, "yes_i_really_mean_it")
                and self.args.yes_i_really_mean_it
            ):
                if batch_size is not None and batch_size > 0:
                    console.print(
                        f"[bold red]🔶 WARNING: About to delete {processing_count} dangling indices (batch {processing_count}/{total_count})![/bold red]"
                    )
                    console.print(
                        f"[dim]This is batch mode - {total_count - processing_count} indices will remain for future batches.[/dim]"
                    )
                else:
                    console.print(
                        f"[bold red]🔶 WARNING: About to delete {processing_count} dangling indices![/bold red]"
                    )
                console.print(
                    "[dim]This action is irreversible and will permanently remove data.[/dim]"
                )
                print()

                try:
                    confirmation = input(
                        "Type 'yes-i-really-mean-it' to proceed with deletion: "
                    )
                    if confirmation != "yes-i-really-mean-it":
                        console.print(
                            "[bold yellow]❌ Operation cancelled.[/bold yellow]"
                        )
                        return
                except KeyboardInterrupt:
                    console.print(
                        "\n[bold yellow]❌ Operation cancelled by user.[/bold yellow]"
                    )
                    return

                print()

            # Process deletions with progress tracking
            successful_deletions = []
            failed_deletions = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task_description = (
                    f"{'Simulating' if dry_run else 'Deleting'} dangling indices"
                )
                if batch_size is not None and batch_size > 0:
                    task_description += f" (batch {processing_count}/{total_count})"
                task_description += "..."

                cleanup_task = progress.add_task(
                    f"[bold {'blue' if dry_run else 'red'}]{task_description}",
                    total=processing_count,
                )

                for i, idx in enumerate(dangling_indices):
                    index_uuid = idx.get("index_uuid", "Unknown")
                    index_name = idx.get("index_name", f"Unknown-{i + 1}")

                    progress.update(
                        cleanup_task,
                        description=f"[bold {'blue' if dry_run else 'red'}]Processing {index_name}...",
                    )

                    # Attempt deletion with retry
                    success = self._delete_dangling_index_with_retry(
                        index_uuid=index_uuid,
                        index_name=index_name,
                        max_retries=3,
                        retry_delay=2,
                        dry_run=dry_run,
                        logger=logger,
                    )

                    if success:
                        successful_deletions.append(
                            {"uuid": index_uuid, "name": index_name}
                        )
                    else:
                        failed_deletions.append(
                            {"uuid": index_uuid, "name": index_name}
                        )

                    progress.advance(cleanup_task)
                    time.sleep(0.1)  # Small delay to prevent overwhelming the cluster

            # Results summary
            print()

            if successful_deletions:
                success_count = len(successful_deletions)
                batch_info = ""
                if batch_size is not None and batch_size > 0:
                    remaining = total_count - processing_count
                    batch_info = f" from batch ({remaining} remaining)"

                success_text = f"{'Simulated' if dry_run else 'Successfully deleted'} {success_count} dangling indices{batch_info}"
                if not dry_run:
                    success_text += ":\n\n"
                    for idx in successful_deletions[:5]:  # Show first 5
                        success_text += f"• {idx['name']} ({idx['uuid'][:8]}...)\n"
                    if success_count > 5:
                        success_text += f"• ... and {success_count - 5} more indices"
                else:
                    success_text += " (simulation completed successfully)"

                success_panel = Panel(
                    success_text,
                    title=f"✅ {'Simulation' if dry_run else 'Cleanup'} Results",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "success"
                    ),
                    padding=(1, 2),
                )
                console.print(success_panel)

            if failed_deletions:
                failed_count = len(failed_deletions)
                failure_text = f"Failed to {'simulate' if dry_run else 'delete'} {failed_count} dangling indices:\n\n"
                for idx in failed_deletions[:5]:  # Show first 5 failures
                    failure_text += f"• {idx['name']} ({idx['uuid'][:8]}...)\n"
                if failed_count > 5:
                    failure_text += f"• ... and {failed_count - 5} more indices"

                failure_panel = Panel(
                    failure_text,
                    title="❌ Failed Operations",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                print()
                console.print(failure_panel)

            # Send metrics if enabled and not dry run
            if metrics_handler and not dry_run:
                try:
                    # Get cluster information
                    health_data = self.es_client.get_cluster_health()
                    cluster_name = health_data.get("cluster_name", "Unknown")

                    # Count unique nodes affected
                    nodes_affected = set()
                    for index in successful_deletions + failed_deletions:
                        node_ids = index.get("node_ids", [])
                        nodes_affected.update(node_ids)

                    nodes_affected_count = len(nodes_affected)
                    found_count = len(successful_deletions) + len(failed_deletions)
                    deleted_count = len(successful_deletions)

                    dry_run = getattr(self.args, "dry_run", False)
                    success = metrics_handler.send_dangling_metric(
                        cluster_name=cluster_name,
                        found=found_count,
                        deleted=deleted_count,
                        nodes_affected=nodes_affected_count,
                        additional_tags={"operation": "cleanup_all"},
                        dry_run=dry_run,
                    )

                    if success:
                        print()
                        if not dry_run:
                            self.es_client.show_message_box(
                                "Metrics Sent Successfully",
                                f"✅ Cleanup metrics sent to database:\n\n"
                                + f"• Cluster: {cluster_name}\n"
                                + f"• Found: {found_count}\n"
                                + f"• Deleted: {deleted_count}\n"
                                + f"• Nodes Affected: {nodes_affected_count}",
                                message_style="bold green",
                                border_style="green",
                            )
                    else:
                        print()
                        self.es_client.show_message_box(
                            "Metrics Send Failed",
                            "❌ Failed to send cleanup metrics to database.\n"
                            + "Check logs for more details.",
                            message_style="bold yellow",
                            border_style="yellow",
                        )
                except Exception as e:
                    logger.error(f"Error sending metrics: {str(e)}")

            # Final summary
            print()
            batch_summary = ""
            if batch_size is not None and batch_size > 0:
                remaining = total_count - processing_count
                batch_summary = f" | Batch: {processing_count}/{total_count} processed, {remaining} remaining"

            final_summary = f"Operation completed: {len(successful_deletions)} successful, {len(failed_deletions)} failed{batch_summary}"
            if dry_run:
                final_summary += " (dry run simulation)"
            logger.info(final_summary)

        except KeyboardInterrupt:
            console.print(
                "\n[bold yellow]❌ Operation cancelled by user.[/bold yellow]"
            )
            if logger:
                logger.info("Cleanup operation cancelled by user")
        except Exception as e:
            error_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    f"❌ Error during cleanup operation: {str(e)}",
                    "error",
                    justify="center",
                ),
                subtitle="Check logs for details",
                border_style=self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 2),
            )
            print()
            console.print(error_panel)
            print()
            if logger:
                logger.error(f"Error during cleanup operation: {str(e)}")

    def _handle_dangling_delete(self):
        """Handle deletion of a single dangling index by UUID."""
        console = self.console
        index_uuid = self.args.uuid

        try:
            # Get cluster info for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get("cluster_name", "Unknown")
            except:
                cluster_name = "Unknown"

            # Create title panel
            title_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    f"🗑 Delete Dangling Index", "error", justify="center"
                ),
                subtitle=f"UUID: {index_uuid} | Cluster: {cluster_name}",
                border_style=self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 2),
            )

            print()
            console.print(title_panel)
            print()

            # Check if this is a dry run
            dry_run = hasattr(self.args, "dry_run") and self.args.dry_run

            if dry_run:
                console.print(
                    "[bold blue]🔍 DRY RUN MODE: Simulating deletion...[/bold blue]"
                )
                print()

            # Verify the dangling index exists
            with console.status(f"Verifying dangling index {index_uuid[:8]}..."):
                dangling_result = self._get_dangling_indices_enhanced()

            if "error" in dangling_result:
                error_panel = Panel(
                    self.es_client.style_system.create_semantic_text(
                        f"❌ Error retrieving dangling indices: {dangling_result['error']}",
                        "error",
                        justify="center",
                    ),
                    subtitle="Cannot verify index existence",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                console.print(error_panel)
                print()
                return

            dangling_indices = dangling_result.get("dangling_indices", [])
            target_index = None

            # Find the specific index
            for idx in dangling_indices:
                if idx.get("index_uuid") == index_uuid:
                    target_index = idx
                    break

            if not target_index:
                warning_panel = Panel(
                    self.es_client.style_system.create_semantic_text(
                        f"🔶 Dangling index with UUID {index_uuid} not found.\n\n"
                        "Possible reasons:\n"
                        "• Index was already deleted\n"
                        "• UUID was mistyped\n"
                        "• Index was recovered by cluster",
                        "warning",
                        justify="center",
                    ),
                    title="Index Not Found",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "warning"
                    ),
                    padding=(1, 2),
                )
                console.print(warning_panel)
                print()
                return

            # Display index information
            creation_date = target_index.get("creation_date", "Unknown")
            node_ids = target_index.get("node_ids", [])

            # Get node hostnames
            node_id_to_hostname_map = self.es_client.get_node_id_to_hostname_map()
            if node_ids:
                hostnames = self.es_client.resolve_node_ids_to_hostnames(
                    node_ids, node_id_to_hostname_map
                )
                nodes_display = ", ".join(hostnames)
            else:
                nodes_display = "N/A"

            # Create info table
            info_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            info_table.add_column("Label", style="bold", no_wrap=True)
            info_table.add_column("Icon", justify="left", width=3)
            info_table.add_column("Value", no_wrap=True)

            info_table.add_row("Index UUID:", "🆔", index_uuid)
            info_table.add_row("Created:", "📅", creation_date)
            info_table.add_row("Nodes:", "💻", nodes_display)
            info_table.add_row("Node Count:", "📊", str(len(node_ids)))

            info_panel = Panel(
                info_table,
                title="📋 Index Information",
                border_style=self.es_client.style_system._get_style(
                    "table_styles", "border_style", "white"
                ),
                padding=(1, 2),
            )

            # Create operation details
            op_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            op_table.add_column("Label", style="bold", no_wrap=True)
            op_table.add_column("Icon", justify="left", width=3)
            op_table.add_column("Value", no_wrap=True)

            op_table.add_row("Operation:", "🗑", "Delete Dangling Index")
            op_table.add_row(
                "Mode:",
                "🔍" if dry_run else "💥",
                "Dry Run" if dry_run else "Actual Deletion",
            )
            op_table.add_row("Reversible:", "❌", "No - Permanent")
            op_table.add_row("Data Loss:", "🔶", "Yes - All data will be lost")

            op_panel = Panel(
                op_table,
                title="🔩 Operation Details",
                border_style=self.es_client.style_system.get_semantic_style("error")
                if not dry_run
                else self.es_client.style_system._get_style(
                    "table_styles", "border_style", "white"
                ),
                padding=(1, 2),
            )

            console.print(Columns([info_panel, op_panel], expand=True))
            print()

            # Confirmation for actual deletion (skip for dry run)
            if not dry_run:
                if not (hasattr(self.args, "yes") and self.args.yes):
                    console.print(
                        f"[bold red]🔶 WARNING: About to permanently delete dangling index![/bold red]"
                    )
                    console.print(f"[dim]UUID: {index_uuid}[/dim]")
                    console.print(
                        f"[dim]This action cannot be undone and will result in permanent data loss.[/dim]"
                    )
                    print()

                    try:
                        confirmation = input("Type 'yes' to confirm deletion: ")
                        if confirmation.lower() != "yes":
                            console.print(
                                "[bold yellow]❌ Operation cancelled.[/bold yellow]"
                            )
                            return
                    except KeyboardInterrupt:
                        console.print(
                            "\n[bold yellow]❌ Operation cancelled by user.[/bold yellow]"
                        )
                        return

                    print()

            # Perform the deletion
            with console.status(
                f"{'Simulating' if dry_run else 'Deleting'} dangling index..."
            ):
                success = self._delete_dangling_index_with_retry(
                    index_uuid=index_uuid,
                    index_name=f"dangling-{index_uuid[:8]}",
                    max_retries=3,
                    retry_delay=2,
                    dry_run=dry_run,
                )

            if success:
                if dry_run:
                    success_panel = Panel(
                        self.es_client.style_system.create_semantic_text(
                            f"🎉 Dry run completed successfully!\n\n"
                            f"The dangling index {index_uuid[:8]}... would be deleted.\n"
                            f"No actual changes were made to the cluster.",
                            "success",
                            justify="center",
                        ),
                        title="✅ Simulation Successful",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "success"
                        ),
                        padding=(1, 2),
                    )
                else:
                    success_panel = Panel(
                        self.es_client.style_system.create_semantic_text(
                            f"🎉 Dangling index deleted successfully!\n\n"
                            f"UUID: {index_uuid}\n"
                            f"The index has been permanently removed from the cluster.",
                            "success",
                            justify="center",
                        ),
                        title="✅ Deletion Successful",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "success"
                        ),
                        padding=(1, 2),
                    )

                console.print(success_panel)
                print()
            else:
                error_panel = Panel(
                    self.es_client.style_system.create_semantic_text(
                        f"❌ Failed to {'simulate deletion of' if dry_run else 'delete'} dangling index.\n\n"
                        f"UUID: {index_uuid}\n"
                        f"Check cluster logs for detailed error information.",
                        "error",
                        justify="center",
                    ),
                    title=f"❌ {'Simulation' if dry_run else 'Deletion'} Failed",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                console.print(error_panel)
                print()

        except KeyboardInterrupt:
            console.print(
                "\n[bold yellow]❌ Operation cancelled by user.[/bold yellow]"
            )
        except Exception as e:
            error_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    f"❌ Error during dangling index {'simulation' if hasattr(self.args, 'dry_run') and self.args.dry_run else 'deletion'}: {str(e)}",
                    "error",
                    justify="center",
                ),
                subtitle="Check cluster connectivity and permissions",
                border_style=self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 2),
            )
            print()
            console.print(error_panel)
            print()

    def _show_deletion_preview(
        self,
        dangling_indices,
        node_id_to_hostname_map,
        dry_run=True,
        title_override=None,
    ):
        """Show a detailed table of what would be deleted in both dry-run and production modes."""
        console = self.console

        # Get theme styles for consistent theming
        from esclient import get_theme_styles

        styles = get_theme_styles(self.es_client.configuration_manager)

        # Create "What Would Be Deleted" table
        preview_table = Table(
            show_header=True,
            header_style=styles["header_style"],
            expand=True,
            box=self.es_client.style_system.get_table_box(),
        )

        # Add columns with proper styling
        preview_table.add_column(
            "🗑 Index Name",
            style=styles.get("health_styles", {}).get("red", {}).get("text", "red"),
            no_wrap=False,
        )
        preview_table.add_column(
            "🆔 UUID",
            style=styles.get("health_styles", {}).get("cyan", {}).get("text", "cyan"),
            no_wrap=True,
            width=30,
        )
        preview_table.add_column(
            "💻 Node Hostnames",
            style=styles.get("status_styles", {})
            .get("close", {})
            .get("text", "magenta"),
            no_wrap=False,
        )
        preview_table.add_column(
            "📊 Nodes",
            style=styles.get("border_style", "white"),
            width=8,
            justify="center",
        )

        # Add rows for each index that would be deleted
        for idx in dangling_indices:
            index_uuid = idx.get("index_uuid", "N/A")
            index_name = idx.get("index_name", f"dangling-{index_uuid[:8]}")
            node_ids = idx.get("node_ids", [])
            node_count = len(node_ids)

            # Show more of the UUID (first 24 characters + ...)
            if len(index_uuid) > 28:
                uuid_display = f"{index_uuid[:28]}..."
            else:
                uuid_display = index_uuid

            # Resolve node IDs to hostnames
            if node_ids:
                hostnames = self.es_client.resolve_node_ids_to_hostnames(
                    node_ids, node_id_to_hostname_map
                )
                # Format hostnames - truncate if too many
                if len(hostnames) > 2:
                    node_display = (
                        ", ".join(hostnames[:2]) + f" (+{len(hostnames) - 2})"
                    )
                else:
                    node_display = ", ".join(hostnames)
            else:
                node_display = "N/A"

            preview_table.add_row(
                index_name, uuid_display, node_display, str(node_count)
            )

        # Create preview panel with dynamic title
        panel_title = (
            title_override
            if title_override
            else "🗑 Indices Scheduled for Deletion (DRY RUN)"
        )
        border_style = "warning" if dry_run else "error"

        preview_panel = Panel(
            preview_table,
            title=f"🗑 {panel_title}",
            border_style=self.es_client.style_system.get_semantic_style(border_style),
            padding=(1, 1),
        )

        print()
        console.print(preview_panel)

        # Add summary information
        total_indices = len(dangling_indices)
        affected_nodes = set()
        for idx in dangling_indices:
            node_ids = idx.get("node_ids", [])
            affected_nodes.update(node_ids)

        if dry_run:
            summary_text = (
                f"📊 Summary: {total_indices} indices would be deleted from {len(affected_nodes)} nodes\n"
                f"💡 To actually delete these indices, run the same command without --dry-run"
            )
        else:
            summary_text = (
                f"📊 Summary: {total_indices} indices will be permanently deleted from {len(affected_nodes)} nodes\n"
                f"🔶 This action cannot be undone - proceed with extreme caution"
            )

        panel_title = "📋 Dry Run Summary" if dry_run else "📋 Deletion Summary"
        border_style = "info" if dry_run else "error"

        summary_panel = Panel(
            Text(summary_text, justify="center"),
            title=panel_title,
            border_style=self.es_client.style_system.get_semantic_style(border_style),
            padding=(1, 2),
        )

        console.print(summary_panel)

    def _handle_cluster_group_report(self):
        """Handle dangling indices report for a cluster group."""
        from reports import DanglingReport
        from esclient import get_theme_styles

        try:
            # Initialize metrics if --metrics flag is specified
            metrics_handler = None
            if hasattr(self.args, "metrics") and self.args.metrics:
                metrics_handler = DanglingMetrics(
                    config_manager=self.es_client.configuration_manager,
                    environment=getattr(self.args, "env", None),
                )
                if not metrics_handler.is_enabled():
                    self.es_client.show_message_box(
                        "Metrics Configuration Error",
                        "❌ Metrics are enabled but not properly configured.\n\n"
                        + "Please configure metrics in escmd.yml or set environment variables:\n"
                        + "- ESCMD_METRICS_ENDPOINT\n"
                        + "- ESCMD_METRICS_DATABASE (optional)\n"
                        + "- ESCMD_METRICS_USERNAME (optional)\n"
                        + "- ESCMD_METRICS_PASSWORD (optional)",
                        message_style="bold red",
                        border_style="red",
                    )
                    return

            # Get theme styles for consistent formatting
            theme_styles = get_theme_styles(self.es_client.configuration_manager)

            # Create report generator
            report_generator = DanglingReport(
                configuration_manager=self.es_client.configuration_manager,
                console=self.console,
                theme_styles=theme_styles,
                logger=self.logger,
            )

            # If metrics is specified, generate minimal report for metrics only
            if metrics_handler:
                # Generate report data without display for metrics processing
                report_result = report_generator.generate_cluster_group_report(
                    group_name=self.args.group,
                    format_type="json",  # Use JSON format for data processing
                )

                # Send metrics if report was successful
                if "error" not in report_result:
                    cluster_data = report_result.get("clusters", {})
                    if cluster_data:
                        dry_run = getattr(self.args, "dry_run", False)
                        metrics_results = metrics_handler.send_environment_metrics(
                            environment_name=f"group_{self.args.group}",
                            cluster_data=cluster_data,
                            additional_tags={"report_type": "cluster_group"},
                            dry_run=dry_run,
                        )

                        successful_metrics = sum(
                            1 for success in metrics_results.values() if success
                        )
                        total_clusters = len(metrics_results)

                        if not dry_run:
                            if successful_metrics == total_clusters:
                                self.es_client.show_message_box(
                                    "Metrics Sent Successfully",
                                    f"✅ Dangling indices metrics sent for all {total_clusters} clusters in group '{self.args.group}'",
                                    message_style="bold green",
                                    border_style="green",
                                )
                            else:
                                self.es_client.show_message_box(
                                    "Metrics Partially Sent",
                                    f"🔶 Metrics sent for {successful_metrics}/{total_clusters} clusters.\n"
                                    + "Check logs for details on failed clusters.",
                                    message_style="bold yellow",
                                    border_style="yellow",
                                )
                    else:
                        self.es_client.show_message_box(
                            "No Data Available",
                            f"❌ No dangling indices data available for group '{self.args.group}'.",
                            message_style="bold yellow",
                            border_style="yellow",
                        )
                else:
                    self.es_client.show_message_box(
                        "Report Generation Error",
                        f"❌ Failed to generate cluster group report: {report_result.get('error', 'Unknown error')}",
                        message_style="bold red",
                        border_style="red",
                    )
                return  # Exit early when metrics mode is used

            # Generate the full report for display
            report_result = report_generator.generate_cluster_group_report(
                group_name=self.args.group,
                format_type=getattr(self.args, "format", "table"),
            )

            # Handle JSON format output
            if getattr(self.args, "format", "table") == "json":
                if "error" not in report_result:
                    self.es_client.pretty_print_json(report_result)
                else:
                    # For JSON format, still output as JSON even if there's an error
                    self.es_client.pretty_print_json(report_result)

        except ImportError as e:
            self.es_client.show_message_box(
                "Import Error",
                f"❌ Failed to import DanglingReport module: {str(e)}\n\n"
                "This feature requires the reports module to be properly installed.",
                message_style="bold red",
                border_style="red",
            )
        except Exception as e:
            self.es_client.show_message_box(
                "Report Generation Error",
                f"❌ Failed to generate cluster group report: {str(e)}\n\n"
                "Please check your cluster group configuration and try again.",
                message_style="bold red",
                border_style="red",
            )

    def _handle_group_cleanup_all(self, logger=None):
        """Handle cleanup of all dangling indices across a cluster group."""
        console = self.console
        if not logger:
            logger = self.logger or logging.getLogger("dangling_cleanup")

        try:
            # Validate cluster group exists
            if not self.es_client.configuration_manager.is_cluster_group(
                self.args.group
            ):
                available_groups = list(
                    self.es_client.configuration_manager.get_cluster_groups().keys()
                )
                error_msg = f"Cluster group '{self.args.group}' not found."
                if available_groups:
                    error_msg += f" Available groups: {', '.join(available_groups)}"

                self.es_client.show_message_box(
                    "Group Not Found",
                    error_msg,
                    message_style="bold red",
                    border_style="red",
                )
                return

            # Get cluster members
            cluster_members = (
                self.es_client.configuration_manager.get_cluster_group_members(
                    self.args.group
                )
            )
            if not cluster_members:
                self.es_client.show_message_box(
                    "Empty Group",
                    f"Cluster group '{self.args.group}' has no members.",
                    message_style="bold red",
                    border_style="red",
                )
                return

            self._handle_multi_cluster_cleanup(
                cluster_members, f"cluster group '{self.args.group}'", logger
            )

        except Exception as e:
            self.es_client.show_message_box(
                "Group Cleanup Error",
                f"❌ Failed to cleanup cluster group: {str(e)}",
                message_style="bold red",
                border_style="red",
            )

    def _handle_environment_cleanup_all(self, logger=None):
        """Handle cleanup of all dangling indices across an environment."""
        console = self.console
        if not logger:
            logger = self.logger or logging.getLogger("dangling_cleanup")

        try:
            # Validate environment exists
            if not self.es_client.configuration_manager.is_environment(self.args.env):
                available_environments = list(
                    self.es_client.configuration_manager.get_environments().keys()
                )
                error_msg = f"Environment '{self.args.env}' not found."
                if available_environments:
                    error_msg += (
                        f" Available environments: {', '.join(available_environments)}"
                    )

                self.es_client.show_message_box(
                    "Environment Not Found",
                    error_msg,
                    message_style="bold red",
                    border_style="red",
                )
                return

            # Get environment members
            env_members = self.es_client.configuration_manager.get_environment_members(
                self.args.env
            )
            if not env_members:
                self.es_client.show_message_box(
                    "Empty Environment",
                    f"Environment '{self.args.env}' has no members.",
                    message_style="bold red",
                    border_style="red",
                )
                return

            self._handle_multi_cluster_cleanup(
                env_members, f"environment '{self.args.env}'", logger
            )

        except Exception as e:
            self.es_client.show_message_box(
                "Environment Cleanup Error",
                f"❌ Failed to cleanup environment: {str(e)}",
                message_style="bold red",
                border_style="red",
            )

    def _handle_multi_cluster_cleanup(self, cluster_list, scope_description, logger):
        """Handle cleanup across multiple clusters."""
        import os
        from concurrent.futures import ThreadPoolExecutor, as_completed

        console = self.console

        # Check for dry run mode
        dry_run = hasattr(self.args, "dry_run") and self.args.dry_run

        # Create title panel
        title_panel = Panel(
            Text(
                f"🧹 Multi-Cluster Dangling Cleanup: {scope_description}",
                style="bold orange1",
                justify="center",
            ),
            subtitle=f"Clusters: {', '.join(cluster_list)}",
            border_style="orange1",
            padding=(1, 2),
        )

        print()
        console.print(title_panel)
        print()

        # First phase: Scan all clusters to get preview data
        with console.status("[bold blue]Scanning all clusters for dangling indices..."):
            scan_results = self._scan_all_clusters_for_dangling(cluster_list)

        # Display comprehensive preview
        total_indices, total_clusters_with_dangling = self._show_multi_cluster_preview(
            scan_results, dry_run, scope_description
        )

        if total_indices == 0:
            success_panel = Panel(
                Text(
                    f"✅ All clusters in {scope_description} are clean!\n\n"
                    "No dangling indices found across any cluster.",
                    style="green",
                    justify="center",
                ),
                title="🎉 Clean Environment",
                border_style=self.es_client.style_system.get_semantic_style("success"),
                padding=(1, 2),
            )
            console.print(success_panel)
            return

        # Safety confirmation for actual deletion
        if not dry_run and not (
            hasattr(self.args, "yes_i_really_mean_it")
            and self.args.yes_i_really_mean_it
        ):
            warning_panel = Panel(
                Text(
                    f"🔶 WARNING: About to run cleanup across {len(cluster_list)} clusters!\n\n"
                    f"This will permanently delete {total_indices} dangling indices\n"
                    f"from {total_clusters_with_dangling} clusters in {scope_description}.\n\n"
                    "This action cannot be undone!",
                    style="bold red",
                    justify="center",
                ),
                title="🚨 Confirmation Required",
                border_style=self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 2),
            )

            print()
            console.print(warning_panel)
            print()

            try:
                confirmation = input(
                    "Type 'yes-i-really-mean-it' to proceed with multi-cluster cleanup: "
                )
                if confirmation != "yes-i-really-mean-it":
                    console.print("[bold yellow]❌ Operation cancelled.[/bold yellow]")
                    return
            except KeyboardInterrupt:
                console.print(
                    "\n[bold yellow]❌ Operation cancelled by user.[/bold yellow]"
                )
                return

            print()

        # Filter clusters to only process those with dangling indices
        clusters_to_process = [
            cluster
            for cluster in cluster_list
            if scan_results.get(cluster, {}).get("count", 0) > 0
        ]

        if not clusters_to_process:
            # This shouldn't happen since we already checked total_indices > 0,
            # but adding as a safety check
            console.print("[bold yellow]No clusters need processing.[/bold yellow]")
            return

        # Show information about cluster filtering
        if len(clusters_to_process) < len(cluster_list):
            skipped_clusters = [
                cluster
                for cluster in cluster_list
                if cluster not in clusters_to_process
            ]
            info_panel = Panel(
                Text(
                    f"🔵  Processing {len(clusters_to_process)} of {len(cluster_list)} clusters\n\n"
                    f"Clusters with dangling indices: {', '.join(clusters_to_process)}\n"
                    f"Skipped (clean): {', '.join(skipped_clusters)}",
                    style="blue",
                    justify="left",
                ),
                title="🎯 Optimized Processing",
                border_style="blue",
                padding=(1, 2),
            )
            console.print(info_panel)
            print()

        # Execute cleanup on filtered clusters only
        results = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            cleanup_task = progress.add_task(
                f"[bold {'blue' if dry_run else 'red'}]Processing clusters...",
                total=len(clusters_to_process),
            )

            with ThreadPoolExecutor(
                max_workers=min(len(clusters_to_process), 3)
            ) as executor:
                future_to_cluster = {}

                for cluster in clusters_to_process:
                    # Build cleanup command for each cluster
                    cmd = [
                        sys.executable,
                        "escmd.py",
                        "--location",
                        cluster,
                        "dangling",
                        "--cleanup-all",
                    ]

                    if dry_run:
                        cmd.append("--dry-run")
                    else:
                        cmd.append("--yes-i-really-mean-it")

                    if hasattr(self.args, "batch") and self.args.batch:
                        cmd.extend(["--batch", str(self.args.batch)])

                    if hasattr(self.args, "max_retries") and self.args.max_retries:
                        cmd.extend(["--max-retries", str(self.args.max_retries)])

                    if hasattr(self.args, "retry_delay") and self.args.retry_delay:
                        cmd.extend(["--retry-delay", str(self.args.retry_delay)])

                    if hasattr(self.args, "timeout") and self.args.timeout:
                        cmd.extend(["--timeout", str(self.args.timeout)])

                    future = executor.submit(
                        self._execute_cluster_cleanup, cluster, cmd, logger
                    )
                    future_to_cluster[future] = cluster

                for future in as_completed(future_to_cluster):
                    cluster = future_to_cluster[future]
                    try:
                        result = future.result(
                            timeout=300
                        )  # 5 minute timeout per cluster
                        results[cluster] = result

                        progress.update(
                            cleanup_task,
                            description=f"[bold {'blue' if dry_run else 'red'}]Processed {cluster}...",
                        )

                    except Exception as e:
                        logger.error(f"Error processing cluster {cluster}: {e}")
                        results[cluster] = {
                            "status": "error",
                            "error": str(e),
                            "deleted": 0,
                            "failed": 0,
                        }

                    progress.advance(cleanup_task)

        # Display results summary
        self._display_multi_cluster_results(
            results, scope_description, dry_run, scan_results, cluster_list
        )

    def _scan_all_clusters_for_dangling(self, cluster_list):
        """Scan all clusters to get dangling indices information for preview."""
        scan_results = {}

        for cluster in cluster_list:
            try:
                # Build command to list dangling indices
                cmd = [
                    sys.executable,
                    "escmd.py",
                    "--location",
                    cluster,
                    "dangling",
                    "--format",
                    "json",
                ]

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    timeout=60,  # 1 minute timeout for scan
                    cwd=os.path.dirname(os.path.abspath(__file__ + "/../")),
                )

                if result.returncode == 0:
                    try:
                        # Parse JSON output
                        output_data = json.loads(result.stdout)
                        dangling_indices = output_data.get("dangling_indices", [])
                        scan_results[cluster] = {
                            "status": "success",
                            "dangling_indices": dangling_indices,
                            "count": len(dangling_indices),
                        }
                    except json.JSONDecodeError:
                        scan_results[cluster] = {
                            "status": "error",
                            "error": "Failed to parse JSON output",
                            "count": 0,
                        }
                else:
                    scan_results[cluster] = {
                        "status": "error",
                        "error": result.stderr.strip() or "Command failed",
                        "count": 0,
                    }

            except Exception as e:
                scan_results[cluster] = {"status": "error", "error": str(e), "count": 0}

        return scan_results

    def _show_multi_cluster_preview(self, scan_results, dry_run, scope_description):
        """Show comprehensive preview of what would be deleted across all clusters."""
        console = self.console

        # Calculate totals
        total_indices = 0
        total_clusters_with_dangling = 0
        successful_scans = 0

        # Get theme styles for consistent theming
        from esclient import get_theme_styles

        styles = get_theme_styles(self.es_client.configuration_manager)

        # Create summary table
        summary_table = Table(
            show_header=True,
            header_style=styles["header_style"],
            expand=True,
            box=self.es_client.style_system.get_table_box(),
        )

        summary_table.add_column(
            "🏗️ Cluster",
            style=styles.get("health_styles", {}).get("green", {}).get("text", "cyan"),
            no_wrap=True,
        )
        summary_table.add_column(
            "📊 Status",
            style=styles.get("border_style", "white"),
            width=12,
            justify="center",
        )
        summary_table.add_column(
            "🔶 Dangling Count",
            style=styles.get("health_styles", {})
            .get("yellow", {})
            .get("text", "yellow"),
            width=16,
            justify="center",
        )
        summary_table.add_column(
            "📝 Details",
            style=styles.get("status_styles", {}).get("close", {}).get("text", "white"),
            no_wrap=False,
        )

        for cluster, data in scan_results.items():
            if data["status"] == "success":
                successful_scans += 1
                count = data["count"]
                total_indices += count
                if count > 0:
                    total_clusters_with_dangling += 1

                status_icon = "✅ Clean" if count == 0 else "🔶 Found"
                status_style = "green" if count == 0 else "yellow"

                if count == 0:
                    details = "No dangling indices"
                else:
                    # Show sample UUIDs
                    sample_indices = data["dangling_indices"][:2]
                    uuids = [
                        idx.get("index_uuid", "Unknown")[:8] + "..."
                        for idx in sample_indices
                    ]
                    details = ", ".join(uuids)
                    if count > 2:
                        details += f" (+{count - 2} more)"

                summary_table.add_row(
                    cluster,
                    status_icon,
                    str(count) if count > 0 else "-",
                    details,
                    style=status_style,
                )
            else:
                summary_table.add_row(
                    cluster,
                    "❌ Error",
                    "-",
                    data.get("error", "Unknown error")[:50],
                    style="red",
                )

        # Create preview panel
        mode_text = "DRY RUN PREVIEW" if dry_run else "DELETION PREVIEW"
        border_style = "warning" if dry_run else "error"

        preview_panel = Panel(
            summary_table,
            title=f"🔍 {mode_text}: {scope_description}",
            border_style=self.es_client.style_system.get_semantic_style(border_style),
            padding=(1, 2),
        )

        print()
        console.print(preview_panel)

        # Create statistics panel
        stats_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        stats_table.add_column("Label", style="bold", no_wrap=True)
        stats_table.add_column("Icon", justify="left", width=3)
        stats_table.add_column("Value", no_wrap=True)

        stats_table.add_row("Total Clusters:", "🏗️", f"{len(scan_results):,}")
        stats_table.add_row("Scanned Successfully:", "✅", f"{successful_scans:,}")
        stats_table.add_row(
            "Clusters with Dangling:", "🔶", f"{total_clusters_with_dangling:,}"
        )
        stats_table.add_row("Total Dangling Indices:", "🗑", f"{total_indices:,}")

        action_text = "would be deleted" if dry_run else "will be deleted"
        if total_indices > 0:
            if dry_run:
                info_text = f"📊 Summary: {total_indices} indices {action_text} across {total_clusters_with_dangling} clusters\n💡 Add --dry-run to simulate, remove it for actual deletion"
            else:
                info_text = f"📊 Summary: {total_indices} indices {action_text} across {total_clusters_with_dangling} clusters\n🔶 This action cannot be undone - proceed with extreme caution"
        else:
            info_text = f"✅ No dangling indices found across any cluster in {scope_description}"

        stats_panel = Panel(
            stats_table,
            title="📊 Multi-Cluster Statistics",
            border_style=self.es_client.style_system.get_semantic_style("info"),
            padding=(1, 2),
        )

        info_panel = Panel(
            Text(info_text, justify="center"),
            title="🔵 Action Summary",
            border_style=self.es_client.style_system.get_semantic_style(border_style),
            padding=(1, 2),
        )

        console.print(Columns([stats_panel, info_panel], expand=True))
        print()

        return total_indices, total_clusters_with_dangling

    def _execute_cluster_cleanup(self, cluster_name, cmd, logger):
        """Execute cleanup command for a single cluster."""
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=300,  # 5 minute timeout
                cwd=os.path.dirname(os.path.abspath(__file__ + "/../")),
            )

            if result.returncode == 0:
                # Parse output to extract statistics
                output = result.stdout + result.stderr
                deleted_count = (
                    output.count("Successfully deleted")
                    if "Successfully deleted" in output
                    else 0
                )
                failed_count = (
                    output.count("Failed to delete")
                    if "Failed to delete" in output
                    else 0
                )

                return {
                    "status": "success",
                    "deleted": deleted_count,
                    "failed": failed_count,
                    "output": output[:500],  # Truncate long output
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr or result.stdout or "Unknown error",
                    "deleted": 0,
                    "failed": 0,
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "Operation timed out after 5 minutes",
                "deleted": 0,
                "failed": 0,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "deleted": 0, "failed": 0}

    def _display_multi_cluster_results(
        self, results, scope_description, dry_run, scan_results=None, all_clusters=None
    ):
        """Display summary results from multi-cluster cleanup."""
        console = self.console

        # Calculate totals
        total_deleted = sum(r.get("deleted", 0) for r in results.values())
        total_failed = sum(r.get("failed", 0) for r in results.values())
        successful_clusters = sum(
            1 for r in results.values() if r.get("status") == "success"
        )
        failed_clusters = len(results) - successful_clusters

        print()

        # Results table
        results_table = Table(
            show_header=True,
            header_style="bold white",
            expand=True,
            box=self.es_client.style_system.get_table_box(),
        )
        results_table.add_column("🏗️ Cluster", style="bold cyan", no_wrap=True)
        results_table.add_column("📊 Status", justify="center", min_width=12)
        results_table.add_column("✅ Deleted", justify="center", min_width=10)
        results_table.add_column("❌ Failed", justify="center", min_width=10)
        results_table.add_column("📝 Details", style="dim white")

        for cluster, result in sorted(results.items()):
            status = result.get("status", "unknown")
            deleted = result.get("deleted", 0)
            failed = result.get("failed", 0)
            error = result.get("error", "")

            if status == "success":
                status_text = f"[green]✅ Success[/green]"
                details = (
                    "Completed successfully"
                    if deleted > 0 or not dry_run
                    else "No dangling indices"
                )
            elif status == "timeout":
                status_text = f"[yellow]🕐 Timeout[/yellow]"
                details = "Operation timed out"
            else:
                status_text = f"[red]❌ Error[/red]"
                details = error[:50] + "..." if len(error) > 50 else error

            results_table.add_row(
                cluster,
                status_text,
                str(deleted) if deleted > 0 else "-",
                str(failed) if failed > 0 else "-",
                details,
            )

        results_panel = Panel(
            results_table,
            title=f"[bold white]📋 Multi-Cluster {'Simulation' if dry_run else 'Cleanup'} Results[/bold white]",
            border_style="cyan",
            padding=(1, 2),
        )

        console.print(results_panel)
        print()

        # Summary panel
        processed_count = len(results)
        total_clusters = len(all_clusters) if all_clusters else processed_count
        skipped_count = total_clusters - processed_count

        summary_text = f"{'Simulated' if dry_run else 'Processed'} {processed_count} of {total_clusters} clusters in {scope_description}\n\n"
        summary_text += f"• Successful clusters: {successful_clusters}\n"
        summary_text += f"• Failed clusters: {failed_clusters}\n"
        if skipped_count > 0:
            summary_text += (
                f"• Skipped clusters (no dangling indices): {skipped_count}\n"
            )
        summary_text += f"• Total indices {'would be deleted' if dry_run else 'deleted'}: {total_deleted}\n"
        summary_text += f"• Total failed operations: {total_failed}"

        summary_style = "success" if failed_clusters == 0 else "warning"
        summary_panel = Panel(
            summary_text,
            title=f"[bold white]📊 {'Simulation' if dry_run else 'Cleanup'} Summary[/bold white]",
            border_style=self.es_client.style_system.get_semantic_style(summary_style),
            padding=(1, 2),
        )

        console.print(summary_panel)
        print()

    def _handle_environment_report(self):
        """Handle dangling indices report for an environment."""
        from reports import DanglingReport
        from esclient import get_theme_styles

        try:
            # Initialize metrics if --metrics flag is specified
            metrics_handler = None
            if hasattr(self.args, "metrics") and self.args.metrics:
                metrics_handler = DanglingMetrics(
                    config_manager=self.es_client.configuration_manager,
                    environment=getattr(self.args, "env", None),
                )
                if not metrics_handler.is_enabled():
                    self.es_client.show_message_box(
                        "Metrics Configuration Error",
                        "❌ Metrics are enabled but not properly configured.\n\n"
                        + "Please configure metrics in escmd.yml or set environment variables:\n"
                        + "- ESCMD_METRICS_ENDPOINT\n"
                        + "- ESCMD_METRICS_DATABASE (optional)\n"
                        + "- ESCMD_METRICS_USERNAME (optional)\n"
                        + "- ESCMD_METRICS_PASSWORD (optional)",
                        message_style="bold red",
                        border_style="red",
                    )
                    return

            # Get theme styles for consistent formatting
            theme_styles = get_theme_styles(self.es_client.configuration_manager)

            # Create report generator
            report_generator = DanglingReport(
                configuration_manager=self.es_client.configuration_manager,
                console=self.console,
                theme_styles=theme_styles,
                logger=self.logger,
            )

            # If metrics is specified, generate minimal report for metrics only
            if metrics_handler:
                # Generate report data without display for metrics processing
                report_result = report_generator.generate_environment_report(
                    env_name=self.args.env,
                    format_type="json",  # Use JSON format for data processing
                )

                # Send metrics if report was successful
                if "error" not in report_result:
                    cluster_data = report_result.get("clusters", {})
                    if cluster_data:
                        dry_run = getattr(self.args, "dry_run", False)
                        metrics_results = metrics_handler.send_environment_metrics(
                            environment_name=self.args.env,
                            cluster_data=cluster_data,
                            additional_tags={"report_type": "environment"},
                            dry_run=dry_run,
                        )

                        successful_metrics = sum(
                            1 for success in metrics_results.values() if success
                        )
                        total_clusters = len(metrics_results)

                        if not dry_run:
                            if successful_metrics == total_clusters:
                                self.es_client.show_message_box(
                                    "Metrics Sent Successfully",
                                    f"✅ Dangling indices metrics sent for all {total_clusters} clusters in environment '{self.args.env}'",
                                    message_style="bold green",
                                    border_style="green",
                                )
                            else:
                                self.es_client.show_message_box(
                                    "Metrics Partially Sent",
                                    f"🔶 Metrics sent for {successful_metrics}/{total_clusters} clusters.\n"
                                    + "Check logs for details on failed clusters.",
                                    message_style="bold yellow",
                                    border_style="yellow",
                                )
                    else:
                        self.es_client.show_message_box(
                            "No Data Available",
                            f"❌ No dangling indices data available for environment '{self.args.env}'.",
                            message_style="bold yellow",
                            border_style="yellow",
                        )
                else:
                    self.es_client.show_message_box(
                        "Report Generation Error",
                        f"❌ Failed to generate environment report: {report_result.get('error', 'Unknown error')}",
                        message_style="bold red",
                        border_style="red",
                    )
                return  # Exit early when metrics mode is used

            # Generate the full environment report for display
            report_result = report_generator.generate_environment_report(
                env_name=self.args.env,
                format_type=getattr(self.args, "format", "table"),
            )

            # Handle JSON format output
            if getattr(self.args, "format", "table") == "json":
                if "error" not in report_result:
                    self.es_client.pretty_print_json(report_result)
                else:
                    # For JSON format, still output as JSON even if there's an error
                    self.es_client.pretty_print_json(report_result)

        except ImportError as e:
            self.es_client.show_message_box(
                "Import Error",
                f"❌ Failed to import DanglingReport module: {str(e)}\n\n"
                "This feature requires the reports module to be properly installed.",
                message_style="bold red",
                border_style="red",
            )
        except Exception as e:
            self.es_client.show_message_box(
                "Report Generation Error",
                f"❌ Failed to generate environment report: {str(e)}\n\n"
                "Please check your environment configuration and try again.",
                message_style="bold red",
                border_style="red",
            )
