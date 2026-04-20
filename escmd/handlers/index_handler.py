"""
IndexHandler - Handles index-related operationsß
"""

from .base_handler import BaseHandler
import json
import re
from rich import box
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich.table import Table as InnerTable
from rich.prompt import Confirm


class IndexHandler(BaseHandler):
    """Handler for index-related operations."""

    def handle_flush(self):
        """Enhanced flush command with Rich formatting and operation details."""
        console = self.console

        try:
            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get("cluster_name", "Unknown")
                total_nodes = health_data.get("number_of_nodes", 0)
            except:
                cluster_name = "Unknown"
                total_nodes = 0

            # Enhanced flush with retry logic
            max_retries = 10
            retry_count = 0
            failed_shards = 1  # Initialize to enter the loop

            while failed_shards > 0 and retry_count <= max_retries:
                retry_count += 1

                # Show current attempt status
                if retry_count == 1:
                    status_message = "Performing synced flush operation..."
                else:
                    status_message = f"Retrying flush operation (attempt {retry_count}/{max_retries + 1})..."

                with console.status(status_message):
                    flushsync = self.es_client.flush_synced_elasticsearch(
                        host=self.es_client.host1,
                        port=self.es_client.port,
                        use_ssl=self.es_client.use_ssl,
                        authentication=self.es_client.elastic_authentication,
                        username=self.es_client.elastic_username,
                        password=self.es_client.elastic_password,
                    )

                # Check results
                if isinstance(flushsync, dict):
                    failed_shards = flushsync.get("_shards", {}).get("failed", 0)
                    total_shards = flushsync.get("_shards", {}).get("total", 0)
                    successful_shards = flushsync.get("_shards", {}).get(
                        "successful", 0
                    )

                    if failed_shards > 0 and retry_count <= max_retries:
                        # Show retry information
                        retry_panel = Panel(
                            self.es_client.style_system.create_semantic_text(
                                f"🔶 Flush attempt {retry_count} completed with {failed_shards}/{total_shards} failed shards.\n"
                                f"💤 Waiting 10 seconds before retry {retry_count + 1}...",
                                "warning",
                                justify="center",
                            ),
                            title=f"🔄 Retry {retry_count}/{max_retries + 1}",
                            border_style=self.es_client.style_system.get_semantic_style(
                                "warning"
                            ),
                            padding=(1, 2),
                        )
                        console.print(retry_panel)

                        # Wait 10 seconds before retry
                        import time

                        time.sleep(10)
                    elif failed_shards == 0:
                        # Success - show completion message if retries were needed
                        if retry_count > 1:
                            success_panel = Panel(
                                self.es_client.style_system.create_semantic_text(
                                    f"🎉 Flush operation successful after {retry_count} attempts!\n"
                                    f"All {total_shards} shards successfully flushed.",
                                    "success",
                                    justify="center",
                                ),
                                title="✅ Operation Complete",
                                border_style=self.es_client.style_system.get_semantic_style(
                                    "success"
                                ),
                                padding=(1, 2),
                            )
                            console.print(success_panel)
                        break
                else:
                    # Non-dict response, exit retry loop
                    break

            # Check if we hit max retries
            if failed_shards > 0 and retry_count > max_retries:
                max_retry_panel = Panel(
                    self.es_client.style_system.create_semantic_text(
                        f"🔶 Maximum retry attempts ({max_retries + 1}) exceeded.\n"
                        f"Final result: {failed_shards}/{total_shards} shards still failed.",
                        "error",
                        justify="center",
                    ),
                    title="❌ Max Retries Exceeded",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                console.print(max_retry_panel)
                print()

            # Process and display results
            if isinstance(flushsync, dict):
                # Extract statistics from flush response
                total_shards = flushsync.get("_shards", {}).get("total", 0)
                successful_shards = flushsync.get("_shards", {}).get("successful", 0)
                failed_shards = flushsync.get("_shards", {}).get("failed", 0)
                skipped_shards = flushsync.get("_shards", {}).get("skipped", 0)

                # Calculate success rate
                success_rate = (
                    (successful_shards / total_shards * 100) if total_shards > 0 else 0
                )

                # Create operation summary panel
                summary_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                summary_table.add_column("Label", style="bold", no_wrap=True)
                summary_table.add_column("Icon", justify="left", width=3)
                summary_table.add_column("Value", no_wrap=True)

                summary_table.add_row("Total Shards:", "📊", f"{total_shards:,}")
                summary_table.add_row("Successful:", "✅", f"{successful_shards:,}")
                summary_table.add_row("Failed:", "❌", f"{failed_shards:,}")
                summary_table.add_row("Skipped:", "💤", f"{skipped_shards:,}")
                summary_table.add_row("Success Rate:", "📈", f"{success_rate:.1f}%")

                # Add retry information if retries were performed
                if retry_count > 1:
                    summary_table.add_row("Retry Attempts:", "🔄", f"{retry_count}")
                    if failed_shards == 0:
                        summary_table.add_row(
                            "Final Status:", "🎉", "Success after retries"
                        )
                    elif retry_count > max_retries:
                        summary_table.add_row(
                            "Final Status:", "🔶", "Max retries exceeded"
                        )

                summary_panel = Panel(
                    summary_table,
                    title="📊 Flush Summary",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "success" if failed_shards == 0 else "warning"
                    ),
                    padding=(1, 2),
                )

                # Create operation details panel
                details_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                details_table.add_column("Label", style="bold", no_wrap=True)
                details_table.add_column("Icon", justify="left", width=3)
                details_table.add_column("Value", no_wrap=True)

                # Determine operation type and status based on retry attempts
                operation_type = (
                    "Synced Flush with Auto-Retry"
                    if retry_count > 1
                    else "Synced Flush"
                )
                if failed_shards == 0:
                    if retry_count > 1:
                        status_text = f"Success (after {retry_count} attempts)"
                        status_icon = "🎉"
                    else:
                        status_text = "Success"
                        status_icon = "✅"
                elif retry_count > max_retries:
                    status_text = "Failed (max retries exceeded)"
                    status_icon = "❌"
                else:
                    status_text = "Partial Success"
                    status_icon = "🔶"

                details_table.add_row("Operation:", "🔄", operation_type)
                details_table.add_row("Cluster:", "🏢", cluster_name)
                details_table.add_row("Target:", "🎯", "All Indices")
                details_table.add_row("Status:", status_icon, status_text)

                details_panel = Panel(
                    details_table,
                    title="🔩 Operation Details",
                    border_style=self.es_client.style_system._get_style(
                        "table_styles", "border_style", "white"
                    ),
                    padding=(1, 2),
                )

                # Show detailed results if there are failures
                if failed_shards > 0 or "failures" in flushsync:
                    if retry_count > max_retries:
                        failures_content = f"❌ Flush operation failed after {retry_count} attempts (including {retry_count - 1} retries).\n\n"
                        failures_content += f"🔶 {failed_shards}/{total_shards} shards still failed after maximum retry attempts:\n\n"
                    else:
                        failures_content = "🔶 Some shards failed to flush:\n\n"

                    failures = flushsync.get("failures", [])
                    for i, failure in enumerate(failures[:5]):  # Show first 5 failures
                        index = failure.get("index", "Unknown")
                        shard = failure.get("shard", "Unknown")
                        reason = failure.get("reason", {}).get(
                            "reason", "Unknown error"
                        )
                        failures_content += f"• {index}[{shard}]: {reason}\n"

                    if len(failures) > 5:
                        failures_content += f"... and {len(failures) - 5} more failures"

                    # Add retry recommendation if max retries exceeded
                    if retry_count > max_retries:
                        failures_content += f"\n\n💡 Consider investigating cluster health or specific index issues."

                    failures_panel = Panel(
                        failures_content.rstrip(),
                        title="❌ Persistent Flush Failures"
                        if retry_count > max_retries
                        else "🔶 Flush Failures",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "error"
                        ),
                        padding=(1, 2),
                    )
                else:
                    # Success message
                    if retry_count > 1:
                        success_text = self.es_client.style_system.create_semantic_text(
                            f"🎉 All shards flushed successfully after {retry_count} attempts!\nThe synced flush operation completed successfully with automatic retry recovery.",
                            "success",
                        )
                        title = "🎉 Success with Auto-Retry"
                    else:
                        success_text = self.es_client.style_system.create_semantic_text(
                            "🎉 All shards flushed successfully!\nThe synced flush operation completed without errors.",
                            "success",
                        )
                        title = "✅ Success"

                    failures_panel = Panel(
                        success_text,
                        title=title,
                        border_style=self.es_client.style_system.get_semantic_style(
                            "success"
                        ),
                        padding=(1, 2),
                    )

                # Create quick actions panel
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column(
                    "Action",
                    style=self.es_client.style_system.get_semantic_style("primary"),
                    no_wrap=True,
                )
                actions_table.add_column(
                    "Command",
                    style=self.es_client.style_system.get_semantic_style("secondary"),
                )

                actions_table.add_row("Check health:", "./escmd.py health")
                actions_table.add_row("View shards:", "./escmd.py shards")
                actions_table.add_row("Monitor recovery:", "./escmd.py recovery")
                actions_table.add_row("View indices:", "./escmd.py indices")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Related Commands",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "primary"
                    ),
                    padding=(1, 2),
                )

                # Build a single header panel — stats in subtitle, status as body
                ss = self.es_client.style_system
                rate_style = ss.get_semantic_style("success" if failed_shards == 0 else "warning")
                border     = ss.get_semantic_style("success" if failed_shards == 0 else "warning")

                # Stats line as subtitle
                subtitle = Text()
                subtitle.append("Cluster: ", style="default")
                subtitle.append(cluster_name, style=ss.get_semantic_style("primary"))
                subtitle.append("  |  Total: ", style="default")
                subtitle.append(str(total_shards), style=ss.get_semantic_style("info"))
                subtitle.append("  |  Successful: ", style="default")
                subtitle.append(str(successful_shards), style=ss.get_semantic_style("success"))
                if failed_shards > 0:
                    subtitle.append("  |  Failed: ", style="default")
                    subtitle.append(str(failed_shards), style=ss.get_semantic_style("error"))
                if skipped_shards > 0:
                    subtitle.append("  |  Skipped: ", style="default")
                    subtitle.append(str(skipped_shards), style=ss.get_semantic_style("warning"))
                subtitle.append("  |  Rate: ", style="default")
                subtitle.append(f"{success_rate:.1f}%", style=rate_style)
                if retry_count > 1:
                    subtitle.append(f"  |  Retries: {retry_count}", style="default")

                # Related commands folded into the title bar
                ts = ss._get_style("semantic", "primary", "bold cyan")
                cmd = ss.get_semantic_style("secondary")
                title = (
                    f"[{ts}]🔄 Elasticsearch Flush Operation[/{ts}]"
                    f"  [{cmd}]health[/{cmd}]"
                    f" [dim]·[/dim]"
                    f" [{cmd}]shards[/{cmd}]"
                    f" [dim]·[/dim]"
                    f" [{cmd}]recovery[/{cmd}]"
                    f" [dim]·[/dim]"
                    f" [{cmd}]indices[/{cmd}]"
                )

                print()
                console.print(Panel(
                    Align.center(failures_panel.renderable, vertical="middle"),
                    title=title,
                    subtitle=subtitle,
                    border_style=border,
                    padding=(1, 2),
                ))
                print()

            else:
                # Simple response display
                simple_panel = Panel(
                    self.es_client.style_system.create_semantic_text(
                        f"🔄 Flush completed: {flushsync}", "success", justify="center"
                    ),
                    title="✅ Flush Operation Complete",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "success"
                    ),
                    padding=(1, 2),
                )
                print()
                console.print(simple_panel)
                print()

        except Exception as e:
            error_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    f"❌ Flush operation failed: {str(e)}", "error", justify="center"
                ),
                subtitle="Check cluster connectivity and permissions",
                border_style=self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 2),
            )
            print()
            console.print(error_panel)
            print()

    def _is_regex_pattern(self, pattern):
        """
        Automatically detect if a pattern contains regex metacharacters.

        Args:
            pattern (str): The pattern to analyze

        Returns:
            bool: True if pattern appears to contain regex syntax
        """
        if not pattern:
            return False

        # Common regex metacharacters that indicate regex usage
        regex_indicators = [
            r"\.\*",  # .* (very common in Elasticsearch patterns)
            r"\.\+",  # .+
            r"\[.*\]",  # [character class]
            r"\{.*\}",  # {quantifier}
            r"\|",  # | (alternation)
            r"\^",  # ^ (start anchor)
            r"\$",  # $ (end anchor)
            r"\+",  # + (one or more)
            r"\?",  # ? (zero or one)
            r"\(",  # ( (grouping start)
            r"\)",  # ) (grouping end)
            r"\\[a-zA-Z]",  # escaped characters like \d, \w, etc.
        ]

        # Check for regex indicators
        for indicator in regex_indicators:
            if re.search(indicator, pattern):
                return True

        # Special case: if pattern ends with .* it's almost certainly regex
        if pattern.endswith(".*"):
            return True

        # Special case: if pattern contains * but not at the end (glob-like)
        # Convert common glob patterns to suggest regex usage
        if "*" in pattern and not pattern.endswith("*"):
            return True

        # Special case: single asterisk is likely a regex wildcard
        if pattern == "*":
            return True

        # Special case: dots in the middle of patterns with other chars might be regex
        # But be conservative - only if there are other regex-like indicators
        # Don't treat simple index names with dots as regex (like index.with.dots)
        if "." in pattern and len(pattern) > 1:
            # Only consider it regex if there are other indicators or it's a clear pattern
            dot_count = pattern.count(".")
            # If there are multiple dots or dots with other special chars, likely regex
            if dot_count > 2 or any(
                char in pattern
                for char in ["*", "+", "?", "[", "]", "^", "$", "|", "(", ")"]
            ):
                return True

        return False

    def handle_freeze(self):
        """Enhanced freeze command with regex support and confirmation prompts."""
        import re

        console = self.console

        if not getattr(self.args, 'pattern', None):
            self._show_freeze_help("freeze", "🧊 Freeze Index")
            return

        # Handle --exact flag to disable auto-detection
        if hasattr(self.args, "exact") and self.args.exact:
            self.args.regex = False
        # Auto-detect regex patterns if --regex not explicitly set and --exact not used
        elif not self.args.regex:
            auto_detected = self._is_regex_pattern(self.args.pattern)
            if auto_detected:
                self.args.regex = True
                console.print(
                    f"[dim yellow]Auto-detected regex pattern: '{self.args.pattern}' (use --exact to disable)[/dim yellow]"
                )
                console.print()

        try:
            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get("cluster_name", "Unknown")
            except:
                cluster_name = "Unknown"

            # Create title panel
            title_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    "🧊 Elasticsearch Index Freeze Operation", "info", justify="center"
                ),
                subtitle=f"Pattern: {self.args.pattern} | Cluster: {cluster_name}",
                border_style=self.es_client.style_system._get_style(
                    "table_styles", "border_style", "white"
                ),
                padding=(1, 2),
            )

            print()
            console.print(title_panel)
            print()

            # Get all indices to search through
            with console.status(f"Retrieving cluster indices..."):
                cluster_active_indices = self.es_client.get_indices_stats(
                    pattern=None, status=None
                )

            # Ensure cluster_active_indices is a list
            if isinstance(cluster_active_indices, str):
                try:
                    import json

                    cluster_active_indices = json.loads(cluster_active_indices)
                except json.JSONDecodeError:
                    cluster_active_indices = []

            if not cluster_active_indices:
                error_panel = Panel(
                    self.es_client.style_system.create_semantic_text(
                        f"❌ No active indices found in cluster",
                        "error",
                        justify="center",
                    ),
                    subtitle="Unable to retrieve cluster indices",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                console.print(error_panel)
                return

            # Find matching indices
            matching_indices = []

            if self.args.regex:
                # Use regex matching
                try:
                    pattern = re.compile(self.args.pattern)
                    for idx in cluster_active_indices:
                        if isinstance(idx, dict):
                            index_name = idx.get("index", "")
                            if pattern.search(index_name):
                                matching_indices.append(idx)
                except re.error as e:
                    error_panel = Panel(
                        self.es_client.style_system.create_semantic_text(
                            f"❌ Invalid regex pattern: {str(e)}",
                            "error",
                            justify="center",
                        ),
                        subtitle="Please check your regex syntax",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "error"
                        ),
                        padding=(1, 2),
                    )
                    console.print(error_panel)
                    return
            else:
                # Exact match
                for idx in cluster_active_indices:
                    if isinstance(idx, dict) and idx.get("index") == self.args.pattern:
                        matching_indices.append(idx)

            if not matching_indices:
                # Show available indices for reference
                try:
                    available_indices = [
                        idx.get("index", "Unknown")
                        for idx in cluster_active_indices[:10]
                        if isinstance(idx, dict)
                    ]
                except (AttributeError, TypeError):
                    available_indices = ["Unable to retrieve index list"]

                error_content = (
                    f"No indices found matching pattern '{self.args.pattern}'\n\n"
                )
                error_content += "Available indices (showing first 10):\n"
                for idx in available_indices:
                    error_content += f"• {idx}\n"

                error_panel = Panel(
                    error_content.rstrip(),
                    title="❌ No Matching Indices",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                console.print(error_panel)
                return

            # Display matching indices
            indices_table = InnerTable(show_header=True, box=None, padding=(0, 1))
            indices_table.add_column(
                "Index Name",
                style=self.es_client.style_system.get_semantic_style("primary"),
                no_wrap=True,
            )
            indices_table.add_column("Health", justify="center", width=8)
            indices_table.add_column("Status", justify="center", width=8)
            indices_table.add_column("Documents", justify="right", width=12)
            indices_table.add_column("Size", justify="right", width=10)

            for idx in matching_indices:
                index_name = idx.get("index", "Unknown")
                health = idx.get("health", "unknown")
                status = idx.get("status", "unknown")
                docs_count = idx.get("docs.count", "0")
                size = idx.get("store.size", "0")

                # Format documents count safely
                try:
                    formatted_docs = (
                        f"{int(docs_count):,}"
                        if docs_count and str(docs_count).isdigit()
                        else str(docs_count)
                    )
                except (ValueError, TypeError):
                    formatted_docs = str(docs_count) if docs_count else "0"

                health_icon = (
                    "🟢" if health == "green" else "🟡" if health == "yellow" else "🔴"
                )
                status_icon = "📂" if status == "open" else "🔒"

                indices_table.add_row(
                    str(index_name),
                    f"{health_icon} {str(health).title()}",
                    f"{status_icon} {str(status).title()}",
                    str(formatted_docs),
                    str(size),
                )

            indices_panel = Panel(
                indices_table,
                title=f"🎯 Found {len(matching_indices)} Matching Indices",
                border_style=self.es_client.style_system._get_style(
                    "table_styles", "border_style", "white"
                ),
                padding=(1, 2),
            )

            console.print(indices_panel)
            print()

            # Confirmation prompt for multiple indices
            if len(matching_indices) > 1 and not self.args.yes:
                warning_text = (
                    f"🔶  You are about to freeze {len(matching_indices)} indices.\n\n"
                )
                warning_text += "This operation will:\n"
                warning_text += "• Make all selected indices read-only\n"
                warning_text += "• Optimize storage for reduced memory usage\n"
                warning_text += (
                    "• Indices remain searchable but with potential latency\n\n"
                )
                warning_text += "Are you sure you want to continue?"

                warning_panel = Panel(
                    warning_text,
                    title="🔶 Multiple Indices Confirmation",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "warning"
                    ),
                    padding=(1, 2),
                )

                console.print(warning_panel)
                print()

                # Custom confirmation that supports y/n/yes/no
                while True:
                    try:
                        response = (
                            input("Proceed with freezing all matched indices? [y/N]: ")
                            .strip()
                            .lower()
                        )
                        if response in ["y", "yes"]:
                            proceed = True
                            break
                        elif response in [
                            "n",
                            "no",
                            "",
                        ]:  # Empty input defaults to 'no'
                            proceed = False
                            break
                        else:
                            console.print(
                                "[yellow]Please enter 'yes', 'no', 'y', or 'n'[/yellow]"
                            )
                            continue
                    except (EOFError, KeyboardInterrupt):
                        proceed = False
                        break

                if not proceed:
                    cancelled_panel = Panel(
                        self.es_client.style_system.create_semantic_text(
                            "❌ Operation cancelled by user",
                            "warning",
                            justify="center",
                        ),
                        subtitle="No indices were frozen",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "warning"
                        ),
                        padding=(1, 2),
                    )
                    console.print(cancelled_panel)
                    return

            # Perform freeze operations
            successful_indices = []
            failed_indices = []

            for idx in matching_indices:
                index_name = idx.get("index", "Unknown")

                with console.status(f"Freezing index '{index_name}'..."):
                    result = self.es_client.freeze_index(index_name)

                if result:
                    successful_indices.append(index_name)
                else:
                    failed_indices.append(index_name)

            # Display results
            if successful_indices:
                success_text = (
                    f"🎉 Successfully frozen {len(successful_indices)} indices!\n\n"
                )
                success_text += "Frozen indices:\n"
                for idx in successful_indices:
                    success_text += f"• ✅ {idx}\n"

                success_text += "\nThese indices are now:\n"
                success_text += "• 🔒 Read-only (no new writes allowed)\n"
                success_text += "• 💾 Storage optimized for reduced memory usage\n"
                success_text += "• 🔍 Still searchable but with potential latency\n"
                success_text += "• 🧊 Frozen state persists until manually unfrozen"

                success_panel = Panel(
                    success_text.rstrip(),
                    title="✅ Freeze Operation Successful",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "success"
                    ),
                    padding=(1, 2),
                )
                console.print(success_panel)
                print()

            if failed_indices:
                failure_text = f"❌ Failed to freeze {len(failed_indices)} indices:\n\n"
                for idx in failed_indices:
                    failure_text += f"• ❌ {idx}\n"

                failure_panel = Panel(
                    failure_text.rstrip(),
                    title="🔶 Some Operations Failed",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                console.print(failure_panel)
                print()

            # Create next steps panel
            actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            actions_table.add_column(
                "Action",
                style=self.es_client.style_system.get_semantic_style("primary"),
                no_wrap=True,
            )
            actions_table.add_column(
                "Command",
                style=self.es_client.style_system.get_semantic_style("secondary"),
            )

            actions_table.add_row("Verify status:", "./escmd.py indices")
            actions_table.add_row(
                "Check specific index:", "./escmd.py indice <index-name>"
            )
            if successful_indices:
                actions_table.add_row(
                    "Unfreeze again:", f"./escmd.py unfreeze <index-name>"
                )

            actions_panel = Panel(
                actions_table,
                title="🚀 Next Steps",
                border_style=self.es_client.style_system.get_semantic_style("primary"),
                padding=(1, 2),
            )
            console.print(actions_panel)
            print()

        except Exception as e:
            error_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    f"❌ Freeze operation error: {str(e)}", "error", justify="center"
                ),
                subtitle=f"Failed to process pattern: {self.args.pattern}",
                border_style=self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 2),
            )
            print()
            console.print(error_panel)
            print()

    def handle_unfreeze(self):
        """Enhanced unfreeze command with regex support and confirmation prompts."""
        import re

        console = self.console

        if not getattr(self.args, 'pattern', None):
            self._show_freeze_help("unfreeze", "🔥 Unfreeze Index")
            return

        # Handle --exact flag to disable auto-detection
        if hasattr(self.args, "exact") and self.args.exact:
            self.args.regex = False
        # Auto-detect regex patterns if --regex not explicitly set and --exact not used
        elif not self.args.regex:
            auto_detected = self._is_regex_pattern(self.args.pattern)
            if auto_detected:
                self.args.regex = True
                console.print(
                    f"[dim yellow]Auto-detected regex pattern: '{self.args.pattern}' (use --exact to disable)[/dim yellow]"
                )
                console.print()

        try:
            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get("cluster_name", "Unknown")
            except:
                cluster_name = "Unknown"

            # Create title panel
            title_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    "🔥 Elasticsearch Index Unfreeze Operation", "info", justify="center"
                ),
                subtitle=f"Pattern: {self.args.pattern} | Cluster: {cluster_name}",
                border_style=self.es_client.style_system._get_style(
                    "table_styles", "border_style", "white"
                ),
                padding=(1, 2),
            )

            print()
            console.print(title_panel)
            print()

            # Get all indices to search through
            with console.status(f"Retrieving cluster indices..."):
                cluster_active_indices = self.es_client.get_indices_stats(
                    pattern=None, status=None
                )

            # Ensure cluster_active_indices is a list
            if isinstance(cluster_active_indices, str):
                try:
                    import json

                    cluster_active_indices = json.loads(cluster_active_indices)
                except json.JSONDecodeError:
                    cluster_active_indices = []

            if not cluster_active_indices:
                error_panel = Panel(
                    self.es_client.style_system.create_semantic_text(
                        f"❌ No active indices found in cluster",
                        "error",
                        justify="center",
                    ),
                    subtitle="Unable to retrieve cluster indices",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                console.print(error_panel)
                return

            # Find matching indices
            matching_indices = []

            if self.args.regex:
                # Use regex matching
                try:
                    pattern = re.compile(self.args.pattern)
                    for idx in cluster_active_indices:
                        if isinstance(idx, dict):
                            index_name = idx.get("index", "")
                            if pattern.search(index_name):
                                matching_indices.append(idx)
                except re.error as e:
                    error_panel = Panel(
                        self.es_client.style_system.create_semantic_text(
                            f"❌ Invalid regex pattern: {str(e)}",
                            "error",
                            justify="center",
                        ),
                        subtitle="Please check your regex syntax",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "error"
                        ),
                        padding=(1, 2),
                    )
                    console.print(error_panel)
                    return
            else:
                # Exact match
                for idx in cluster_active_indices:
                    if isinstance(idx, dict) and idx.get("index") == self.args.pattern:
                        matching_indices.append(idx)

            if not matching_indices:
                # Show available indices for reference
                try:
                    available_indices = [
                        idx.get("index", "Unknown")
                        for idx in cluster_active_indices[:10]
                        if isinstance(idx, dict)
                    ]
                except (AttributeError, TypeError):
                    available_indices = ["Unable to retrieve index list"]

                error_content = (
                    f"No indices found matching pattern '{self.args.pattern}'\n\n"
                )
                error_content += "Available indices (showing first 10):\n"
                for idx in available_indices:
                    error_content += f"• {idx}\n"

                error_panel = Panel(
                    error_content.rstrip(),
                    title="❌ No Matching Indices",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                console.print(error_panel)
                return

            # Display matching indices
            indices_table = InnerTable(show_header=True, box=None, padding=(0, 1))
            indices_table.add_column(
                "Index Name",
                style=self.es_client.style_system.get_semantic_style("primary"),
                no_wrap=True,
            )
            indices_table.add_column("Health", justify="center", width=8)
            indices_table.add_column("Status", justify="center", width=8)
            indices_table.add_column("Documents", justify="right", width=12)
            indices_table.add_column("Size", justify="right", width=10)

            for idx in matching_indices:
                index_name = idx.get("index", "Unknown")
                health = idx.get("health", "unknown")
                status = idx.get("status", "unknown")
                docs_count = idx.get("docs.count", "0")
                size = idx.get("store.size", "0")

                # Format documents count safely
                try:
                    formatted_docs = (
                        f"{int(docs_count):,}"
                        if docs_count and str(docs_count).isdigit()
                        else str(docs_count)
                    )
                except (ValueError, TypeError):
                    formatted_docs = str(docs_count) if docs_count else "0"

                health_icon = (
                    "🟢" if health == "green" else "🟡" if health == "yellow" else "🔴"
                )
                status_icon = "📂" if status == "open" else "🔒"

                indices_table.add_row(
                    str(index_name),
                    f"{health_icon} {str(health).title()}",
                    f"{status_icon} {str(status).title()}",
                    str(formatted_docs),
                    str(size),
                )

            indices_panel = Panel(
                indices_table,
                title=f"🎯 Found {len(matching_indices)} Matching Indices",
                border_style=self.es_client.style_system._get_style(
                    "table_styles", "border_style", "white"
                ),
                padding=(1, 2),
            )

            console.print(indices_panel)
            print()

            # Confirmation prompt for multiple indices
            if len(matching_indices) > 1 and not self.args.yes:
                warning_text = (
                    f"🔶  You are about to unfreeze {len(matching_indices)} indices.\n\n"
                )
                warning_text += "This operation will:\n"
                warning_text += "• Make all selected indices writable again\n"
                warning_text += "• Remove storage optimizations\n"
                warning_text += "• Allow new documents to be indexed\n\n"
                warning_text += "Are you sure you want to continue?"

                warning_panel = Panel(
                    warning_text,
                    title="🔶 Multiple Indices Confirmation",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "warning"
                    ),
                    padding=(1, 2),
                )

                console.print(warning_panel)
                print()

                # Custom confirmation that supports y/n/yes/no
                while True:
                    try:
                        response = (
                            input(
                                "Proceed with unfreezing all matched indices? [y/N]: "
                            )
                            .strip()
                            .lower()
                        )
                        if response in ["y", "yes"]:
                            proceed = True
                            break
                        elif response in [
                            "n",
                            "no",
                            "",
                        ]:  # Empty input defaults to 'no'
                            proceed = False
                            break
                        else:
                            console.print(
                                "[yellow]Please enter 'yes', 'no', 'y', or 'n'[/yellow]"
                            )
                            continue
                    except (EOFError, KeyboardInterrupt):
                        proceed = False
                        break

                if not proceed:
                    cancelled_panel = Panel(
                        self.es_client.style_system.create_semantic_text(
                            "❌ Operation cancelled by user",
                            "warning",
                            justify="center",
                        ),
                        subtitle="No indices were unfrozen",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "warning"
                        ),
                        padding=(1, 2),
                    )
                    console.print(cancelled_panel)
                    return

            # Perform unfreeze operations
            successful_indices = []
            failed_indices = []

            for idx in matching_indices:
                index_name = idx.get("index", "Unknown")

                with console.status(f"Unfreezing index '{index_name}'..."):
                    result = self.es_client.unfreeze_index(index_name)

                if result:
                    successful_indices.append(index_name)
                else:
                    failed_indices.append(index_name)

            # Display results
            if successful_indices:
                success_text = (
                    f"🎉 Successfully unfrozen {len(successful_indices)} indices!\n\n"
                )
                success_text += "Unfrozen indices:\n"
                for idx in successful_indices:
                    success_text += f"• ✅ {idx}\n"

                success_text += "\nThese indices are now:\n"
                success_text += "• ✏️  Writable (accepting new documents)\n"
                success_text += "• 🔄 Using normal memory management\n"
                success_text += "• 🔍 Fully searchable with normal performance\n"

                success_panel = Panel(
                    success_text.rstrip(),
                    title="✅ Unfreeze Operation Successful",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "success"
                    ),
                    padding=(1, 2),
                )
                console.print(success_panel)
                print()

            if failed_indices:
                failure_text = (
                    f"❌ Failed to unfreeze {len(failed_indices)} indices:\n\n"
                )
                for idx in failed_indices:
                    failure_text += f"• ❌ {idx}\n"

                failure_panel = Panel(
                    failure_text.rstrip(),
                    title="🔶 Some Operations Failed",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
                console.print(failure_panel)
                print()

            # Create next steps panel
            actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            actions_table.add_column(
                "Action",
                style=self.es_client.style_system.get_semantic_style("primary"),
                no_wrap=True,
            )
            actions_table.add_column(
                "Command",
                style=self.es_client.style_system.get_semantic_style("secondary"),
            )

            actions_table.add_row("Verify status:", "./escmd.py indices")
            actions_table.add_row(
                "Check specific index:", "./escmd.py indice <index-name>"
            )
            if successful_indices:
                actions_table.add_row(
                    "Freeze again:", f"./escmd.py freeze <index-name>"
                )

            actions_panel = Panel(
                actions_table,
                title="🚀 Next Steps",
                border_style=self.es_client.style_system.get_semantic_style("primary"),
                padding=(1, 2),
            )
            console.print(actions_panel)
            print()

        except Exception as e:
            error_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    f"❌ Unfreeze operation error: {str(e)}", "error", justify="center"
                ),
                subtitle=f"Failed to process pattern: {self.args.pattern}",
                border_style=self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 2),
            )
            print()
            console.print(error_panel)
            print()

    def handle_indice(self):
        """Display detailed information about a specific index."""
        indice = getattr(self.args, 'indice', None)

        if not indice:
            self._show_indice_help()
            return

        self.es_client.print_detailed_indice_info(indice)

    def _show_indice_help(self):
        """Display help screen for indice command."""
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
            Text("Run ./escmd.py indice <index-name>", style="bold white"),
            title=f"[{title_style}]📋 Index Details[/{title_style}]",
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
        table.add_column("Command", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("indice <name>", "Show detailed info for a specific index", "indice myindex-001"),
            ("indice <datastream>", "Show details for a datastream index", "indice .ds-logs-app-2025.08.28-000001"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Related ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        related = [
            ("indices", "List all indices", "indices"),
            ("indices '<pattern>'", "Search indices with pattern", "indices 'logs-*'"),
            ("indices --status yellow", "Filter by health status", "indices --status yellow"),
            ("indice-add-metadata <n> '<json>'", "Add metadata to an index", "indice-add-metadata my-idx '{\"team\": \"sre\"}'"),
        ]
        for i, (opt, desc, ex) in enumerate(related):
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

    def handle_indices(self):
        """List and manage indices with filtering options."""
        if self.args.cold:
            self._handle_cold_indices()
            return

        if self.args.regex:
            self._handle_regex_indices()
            return

        if self.args.format == "json":
            indices = self.es_client.filter_indices(
                pattern=None, status=self.args.status
            )

            if self.args.delete:
                # For JSON format with deletion, create comprehensive output
                output = {"indices": indices, "deletion_requested": True}

                # Perform deletion and capture results
                deletion_result = self._handle_indices_deletion_json(indices)
                output["deletion_results"] = deletion_result

                print(json.dumps(output, indent=2))
            else:
                # Just print indices without deletion
                print(json.dumps(indices, indent=2))
        else:
            # Get filtered indices
            indices = self.es_client.filter_indices(
                pattern=None, status=self.args.status
            )

            # If filtering by status and no results, provide better feedback
            if not indices and self.args.status:
                # Get total indices count for context
                all_indices = self.es_client.filter_indices(pattern=None, status=None)
                if all_indices:
                    self._display_no_matching_status_message(
                        self.args.status, len(all_indices)
                    )
                else:
                    # Use original message if truly no indices exist
                    use_pager = getattr(self.args, "pager", False)
                    self.es_client.print_table_indices(indices, use_pager=use_pager)
            else:
                # Check if pager argument exists and use it
                use_pager = getattr(self.args, "pager", False)
                self.es_client.print_table_indices(indices, use_pager=use_pager)

            # Handle deletion if requested
            if self.args.delete:
                self._handle_indices_deletion(indices)

    def handle_indices_analyze(self):
        """Compare backing indices to siblings in the same rollover series."""
        from processors.index_traffic_analyzer import analyze_index_traffic

        pattern = getattr(self.args, "regex", None)
        status = getattr(self.args, "status", None)
        min_peers = getattr(self.args, "min_peers", 1)
        min_ratio = getattr(self.args, "min_ratio", 5.0)
        min_docs = getattr(self.args, "min_docs", 1_000_000)
        top = getattr(self.args, "top", None)
        within_days = getattr(self.args, "within_days", None)

        indices = self.es_client.filter_indices(pattern=pattern, status=status)
        result = analyze_index_traffic(
            indices,
            min_peers=min_peers,
            min_ratio=min_ratio,
            min_docs=min_docs,
            top=top,
            within_days=within_days,
        )

        if getattr(self.args, "format", "table") == "json":
            print(json.dumps(result, indent=2))
            return

        use_pager = getattr(self.args, "pager", False)
        if hasattr(self.es_client, "index_renderer"):
            self.es_client.index_renderer.print_indices_traffic_analysis(
                result, console=self.console, use_pager=use_pager
            )
        else:
            print(json.dumps(result, indent=2))

    def handle_indices_s3_estimate(self):
        """Estimate monthly S3 cost from summed primary store for dated indices in a UTC window."""
        from processors.s3_storage_estimate import estimate_s3_monthly_storage_cost

        pattern = getattr(self.args, "regex", None)
        status = getattr(self.args, "status", None)
        within_days = int(getattr(self.args, "within_days", 30) or 30)
        buffer_percent = float(getattr(self.args, "buffer_percent", 0.0) or 0.0)
        price = float(getattr(self.args, "price_per_gib_month", 0.0) or 0.0)
        include_undated = bool(getattr(self.args, "include_undated", False))

        indices = self.es_client.filter_indices(pattern=pattern, status=status)
        result = estimate_s3_monthly_storage_cost(
            indices,
            within_days=within_days,
            buffer_percent=buffer_percent,
            price_per_gib_month_usd=price,
            include_undated=include_undated,
        )

        if getattr(self.args, "format", "table") == "json":
            print(json.dumps(result, indent=2))
            return

        if hasattr(self.es_client, "index_renderer"):
            self.es_client.index_renderer.print_s3_storage_estimate(
                result, console=self.console
            )
        else:
            print(json.dumps(result, indent=2))

    def handle_indices_watch_collect(self):
        """Periodically snapshot index stats to JSON files (multi-host retry)."""
        import signal
        import sys
        import time
        from datetime import datetime, timezone
        from pathlib import Path

        from processors.indices_watch import (
            default_run_dir,
            index_watch_storage_slug,
            collect_indices_and_nodes_with_failover,
            pick_or_create_session_dir,
            save_sample_file,
            utc_today_iso,
            write_run_metadata,
        )

        interval = max(1, int(getattr(self.args, "interval", 60) or 60))
        duration = getattr(self.args, "duration", None)
        pattern = getattr(self.args, "regex", None)
        status = getattr(self.args, "status", None)
        retries = max(1, int(getattr(self.args, "retries", 3) or 3))
        retry_delay = max(0.0, float(getattr(self.args, "retry_delay", 2.0) or 2.0))

        raw_loc = self.current_location or "default"
        cm = getattr(self.es_client, "configuration_manager", None)
        cluster = (
            index_watch_storage_slug(raw_loc, cm)
            if cm is not None
            else raw_loc
        )
        collect_out = getattr(self.args, "collect_output_dir", None)
        day_iso = utc_today_iso()
        new_session = getattr(self.args, "new_session", False) or False
        join_latest = getattr(self.args, "join_latest", False) or False
        label = getattr(self.args, "label", None)

        if collect_out and str(collect_out).strip():
            out_dir = Path(str(collect_out).strip()).expanduser()
            out_dir.mkdir(parents=True, exist_ok=True)
            write_run_metadata(
                out_dir,
                cluster=cluster,
                interval_seconds=interval,
                duration_seconds=duration,
                pattern=pattern,
                status=status,
            )
        else:
            out_dir, is_new = pick_or_create_session_dir(
                cluster,
                day_iso,
                new_session=new_session,
                join_latest=join_latest,
                label=label,
                console=self.console,
                is_tty=sys.stdin.isatty(),
            )
            out_dir.mkdir(parents=True, exist_ok=True)
            if is_new:
                write_run_metadata(
                    out_dir,
                    cluster=cluster,
                    interval_seconds=interval,
                    duration_seconds=duration,
                    pattern=pattern,
                    status=status,
                    session_id=out_dir.name,
                    label=label,
                )

        stop_flag = {"stop": False}

        def on_sigint(_signum, _frame):
            stop_flag["stop"] = True

        signal.signal(signal.SIGINT, on_sigint)

        self.console.print(
            f"[bold]indices-watch-collect[/bold] → {out_dir}  interval={interval}s"
        )
        if duration:
            self.console.print(f"duration={duration}s (Ctrl+C stops early)")
        else:
            self.console.print("Run until Ctrl+C")

        # When joining an existing session, pick up the sequence counter where it left off
        from processors.indices_watch import _is_sample_file
        seq = sum(1 for p in out_dir.iterdir() if p.is_file() and _is_sample_file(p)) if out_dir.is_dir() else 0
        if seq > 0:
            self.console.print(
                f"[bold]Loaded {seq} previous sample{'s' if seq != 1 else ''}"
                f" from session[/bold] → resuming at Pull #{seq + 1}"
            )
        start = time.time()
        while not stop_flag["stop"]:
            if duration is not None and (time.time() - start) >= duration:
                break
            loop_start = time.time()
            data, nodes_stats, cluster_health, host = collect_indices_and_nodes_with_failover(
                self.es_client,
                pattern=pattern,
                status=status,
                retries_per_host=retries,
                retry_delay_sec=retry_delay,
            )
            if host is None:
                self.console.print(
                    "[red]Sample failed on all hosts; retrying next interval[/red]"
                )
            else:
                seq += 1
                now = datetime.now(timezone.utc)
                path = save_sample_file(
                    out_dir,
                    cluster=cluster,
                    indices=data,
                    captured_at=now,
                    host_used=host,
                    sequence=seq,
                    nodes_stats=nodes_stats,
                    cluster_health=cluster_health,
                )
                self.console.print(
                    f"  saved {path.name}  ({len(data)} indices) host={host}"
                )

            elapsed_loop = time.time() - loop_start
            rem = interval - elapsed_loop
            while rem > 0 and not stop_flag["stop"]:
                if duration is not None and (time.time() - start) >= duration:
                    stop_flag["stop"] = True
                    break
                sleep_chunk = min(1.0, rem)
                time.sleep(sleep_chunk)
                rem -= sleep_chunk

        self.console.print("[dim]indices-watch-collect finished[/dim]")

    def handle_indice_add_metadata(self):
        """Add metadata to a specific index."""
        import json
        from rich.panel import Panel
        from rich.text import Text

        indice_name = getattr(self.args, 'indice_name', None)
        metadata_json = getattr(self.args, 'metadata_json', None)

        if not indice_name or not metadata_json:
            self._show_indice_add_metadata_help()
            return

        # Validate JSON input
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError as e:
            error_text = Text()
            error_text.append(
                "❌ Invalid JSON format.\n\n",
                style=self.es_client.style_system.get_semantic_style("error"),
            )
            error_text.append(
                f"Error: {str(e)}",
                style=self.es_client.style_system.get_semantic_style("error"),
            )

            self.console.print()
            self.console.print(
                Panel(
                    error_text,
                    title="JSON Parse Error",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
            )
            self.console.print()
            return

        # Check if index exists
        try:
            indices_data = self.es_client.filter_indices(pattern=None, status=None)
            index_exists = any(index["index"] == indice_name for index in indices_data)

            if not index_exists:
                error_text = Text()
                error_text.append(
                    f"❌ Index '{indice_name}' not found.\n\n",
                    style=self.es_client.style_system.get_semantic_style("error"),
                )
                error_text.append(
                    "Please check the index name and try again.",
                    style=self.es_client.style_system.get_semantic_style("primary"),
                )

                self.console.print()
                self.console.print(
                    Panel(
                        error_text,
                        title="Index Not Found",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "error"
                        ),
                        padding=(1, 2),
                    )
                )
                self.console.print()
                return

        except Exception as e:
            error_text = Text()
            error_text.append(
                "❌ Error checking index existence.\n\n",
                style=self.es_client.style_system.get_semantic_style("error"),
            )
            error_text.append(
                f"Error: {str(e)}",
                style=self.es_client.style_system.get_semantic_style("error"),
            )

            self.console.print()
            self.console.print(
                Panel(
                    error_text,
                    title="Connection Error",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
            )
            self.console.print()
            return

        # Add metadata to index mapping
        try:
            # Get current index mapping to check for existing _meta
            current_mapping = self.es_client.es.indices.get_mapping(index=indice_name)
            existing_mapping = current_mapping[indice_name]["mappings"]

            # Extract _meta content if user provided it wrapped in _meta
            if (
                isinstance(metadata, dict)
                and "_meta" in metadata
                and len(metadata) == 1
            ):
                # User provided {"_meta": {...}}, extract the inner content
                metadata_content = metadata["_meta"]
            else:
                # User provided the content directly
                metadata_content = metadata

            # Merge with existing _meta if it exists
            existing_meta = existing_mapping.get("_meta", {})
            if isinstance(existing_meta, dict) and isinstance(metadata_content, dict):
                # Deep merge the metadata
                for key, value in metadata_content.items():
                    if (
                        key in existing_meta
                        and isinstance(existing_meta[key], dict)
                        and isinstance(value, dict)
                    ):
                        existing_meta[key].update(value)
                    else:
                        existing_meta[key] = value
                final_meta = existing_meta
            else:
                final_meta = metadata_content

            # Update index mapping with new metadata
            mapping_update = {"_meta": final_meta}

            self.es_client.es.indices.put_mapping(
                index=indice_name, body=mapping_update
            )

            # Success message
            success_text = Text()
            success_text.append(
                f"✅ Metadata successfully added to index '{indice_name}'.\n\n",
                style=self.es_client.style_system.get_semantic_style("success"),
            )
            success_text.append(
                "Added metadata:\n",
                style=self.es_client.style_system.get_semantic_style("primary"),
            )
            success_text.append(
                json.dumps(final_meta, indent=2),
                style=self.es_client.style_system.get_semantic_style("info"),
            )

            self.console.print()
            self.console.print(
                Panel(
                    success_text,
                    title="Metadata Added Successfully",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "success"
                    ),
                    padding=(1, 2),
                )
            )
            self.console.print()

        except Exception as e:
            error_text = Text()
            error_text.append(
                "❌ Error adding metadata to index.\n\n",
                style=self.es_client.style_system.get_semantic_style("error"),
            )
            error_text.append(
                f"Error: {str(e)}",
                style=self.es_client.style_system.get_semantic_style("error"),
            )

            self.console.print()
            self.console.print(
                Panel(
                    error_text,
                    title="Metadata Update Error",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "error"
                    ),
                    padding=(1, 2),
                )
            )
            self.console.print()

    def _display_no_matching_status_message(self, status_filter, total_indices_count):
        """Display a themed message when no indices match the status filter."""
        from display.style_system import StyleSystem

        # Reuse the client's existing theme manager
        theme_manager = getattr(self.es_client, 'theme_manager', None)
        if theme_manager is None:
            from display.theme_manager import ThemeManager
            config_manager = getattr(self.es_client, "config_manager", None)
            theme_manager = ThemeManager(config_manager)
        style_system = StyleSystem(theme_manager)

        # Create the message content
        message_lines = [
            f"No indices found with status: [bold]{status_filter}[/bold]",
            "",
            f"Total indices in cluster: [cyan]{total_indices_count}[/cyan]",
            "",
            "Try one of these options:",
            f"• [dim]./escmd.py indices[/dim] - Show all indices",
            f"• [dim]./escmd.py indices --status green[/dim] - Show green indices",
            f"• [dim]./escmd.py indices --status yellow[/dim] - Show yellow indices",
            f"• [dim]./escmd.py indices --status red[/dim] - Show red indices",
        ]

        content = "\n".join(message_lines)

        # Create a themed info panel
        panel = style_system.create_info_panel(
            content, f"Index Status Filter: {status_filter}", "🔍"
        )

        self.console.print(panel)

    def _show_indice_add_metadata_help(self):
        """Display help screen for indice-add-metadata command."""
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
            Text("Run ./escmd.py indice-add-metadata <index> '<json>'", style="bold white"),
            title=f"[{title_style}]📝 Add Index Metadata[/{title_style}]",
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
        table.add_column("Usage / Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("<index> '<json>'", "Add metadata key-value pairs to an index", "indice-add-metadata my-idx '{\"team\": \"platform\"}'"),
            ("<index> '<json>'", "Tag with environment and owner", "indice-add-metadata my-idx '{\"env\": \"prod\", \"owner\": \"sre\"}'"),
            ("<index> '<json>'", "Set retention policy metadata", "indice-add-metadata my-idx '{\"retention_days\": 30}'"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Related ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        related = [
            ("indice <name>", "View index details including metadata", "indice my-index"),
        ]
        for i, (opt, desc, ex) in enumerate(related):
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

    def handle_create_index(self):
        """Create a new empty index with optional settings and mappings."""
        import json

        # Get index name
        index_name = self.args.index_name

        # Show help table if no index name provided
        if not index_name or not index_name.strip():
            self._show_create_index_help()
            return

        # Build settings
        settings = {
            "number_of_shards": self.args.shards,
            "number_of_replicas": self.args.replicas,
        }

        # Parse custom settings if provided
        if hasattr(self.args, "settings") and self.args.settings:
            try:
                custom_settings = json.loads(self.args.settings)
                settings.update(custom_settings)
            except json.JSONDecodeError as e:
                self.console.print(
                    f"[red]❌ Error: Invalid JSON in settings: {e}[/red]"
                )
                return

        # Parse custom mappings if provided
        mappings = None
        if hasattr(self.args, "mappings") and self.args.mappings:
            try:
                mappings = json.loads(self.args.mappings)
            except json.JSONDecodeError as e:
                self.console.print(
                    f"[red]❌ Error: Invalid JSON in mappings: {e}[/red]"
                )
                return

        # Show creation summary
        self.console.print(f"\n[bold blue]📋 Creating Index: {index_name}[/bold blue]")
        self.console.print(f"  Primary Shards: {settings['number_of_shards']}")
        self.console.print(f"  Replica Shards: {settings['number_of_replicas']}")

        if len(settings) > 2:  # More than just shards and replicas
            self.console.print("  Custom Settings: Yes")
        if mappings:
            self.console.print("  Custom Mappings: Yes")

        # Create the index
        try:
            result = self.es_client.create_index(
                index_name, {"index": settings}, mappings
            )

            if self.args.format == "json":
                print(json.dumps(result, indent=2))
            else:
                if result.get("success"):
                    self.console.print(
                        f"\n[green]✅ {result.get('message', 'Index created successfully')}[/green]"
                    )
                    if result.get("acknowledged"):
                        self.console.print("  Cluster acknowledged: ✓")
                    if result.get("shards_acknowledged"):
                        self.console.print("  Shards acknowledged: ✓")

                    # Show next steps with proper Rich formatting
                    next_steps = f"""
[dim]💡 Next steps:
  • View index: ./escmd.py indice {index_name}
  • List indices: ./escmd.py indices
  • Add documents via your application or curl[/dim]"""
                    self.console.print(next_steps)
                else:
                    self.console.print(
                        f"\n[red]❌ {result.get('message', 'Index creation failed')}[/red]"
                    )
                    if "error" in result:
                        self.console.print(f"  Error: {result['error']}")

        except Exception as e:
            self.console.print(f"\n[red]❌ Unexpected error creating index: {e}[/red]")

    def _show_create_index_help(self):
        """Display help screen for create-index command."""
        from rich.console import Console
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
            Text("Run ./escmd.py create-index <name> [options]", style="bold white"),
            title=f"[{title_style}]📝 Create Index[/{title_style}]",
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
        table.add_column("Usage / Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("create-index <name>", "Create index with default settings (1p/1r)", "create-index my-new-index"),
            ("-s, --shards <n>", "Number of primary shards (default: 1)", "create-index logs-2026 -s 3"),
            ("-r, --replicas <n>", "Number of replicas (default: 1)", "create-index logs-2026 -r 0"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Advanced ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        advanced = [
            ("--settings '<json>'", "Custom index settings as JSON", 'create-index my-idx --settings \'{"analysis": {}}\''),
            ("--mappings '<json>'", "Custom index mappings as JSON", 'create-index my-idx --mappings \'{"properties": {}}\''),
            ("--format json", "JSON output instead of table", "create-index my-idx --format json"),
        ]
        for i, (opt, desc, ex) in enumerate(advanced):
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

    def _show_freeze_help(self, command, title_text):
        """Display help screen for freeze/unfreeze commands."""
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
            Text(f"Run ./escmd.py {command} <index-or-pattern>", style="bold white"),
            title=f"[{title_style}]{title_text}[/{title_style}]",
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
        table.add_column("Usage / Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            (f"{command} <index>", f"{command.capitalize()} a specific index", f"{command} my-index-001"),
            (f"{command} '<pattern>'", f"{command.capitalize()} indices matching pattern", f"{command} 'logs-2025.*'"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Options ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        options = [
            ("--regex, -r", "Force treat pattern as regex", f"{command} 'logs-.*' --regex"),
            ("--exact, -e", "Force exact match (no auto-detect)", f"{command} my-index --exact"),
            ("--yes, -y", "Skip confirmation prompt", f"{command} my-index --yes"),
        ]
        for i, (opt, desc, ex) in enumerate(options):
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

    def handle_recovery(self):
        """Monitor index recovery status."""
        if self.args.format == "json":
            es_recovery = self.es_client.get_recovery_status()
            self.es_client.pretty_print_json(es_recovery)
        else:
            with self.console.status("Retrieving recovery data..."):
                es_recovery = self.es_client.get_recovery_status()
            self.es_client.health_commands.print_enhanced_recovery_status(es_recovery)

    def _handle_cold_indices(self):
        """Handle cold indices listing."""
        try:
            # Get all indices data
            indices_data = self.es_client.get_indices_stats(
                pattern=self.args.regex, status=self.args.status
            )

            # Get ILM information to identify cold indices
            index_ilms = self.es_client.get_index_ilms(short=True)

            # Filter indices to only show those in cold phase
            cold_indices_names = [
                index
                for index, info in index_ilms.items()
                if info.get("phase") == "cold"
            ]

            if not cold_indices_names:
                # Show message if no cold indices found
                self.es_client.show_message_box(
                    "Cold Indices",
                    "No indices found in the 'cold' ILM phase.\n\nThis could mean:\n• No indices are using ILM policies\n• No indices have progressed to the cold phase\n• The cluster may not have ILM configured",
                    message_style="yellow",
                    panel_style="bold blue",
                )
                return

            # Filter the indices data to only include cold indices
            if isinstance(indices_data, list):
                cold_indices_data = [
                    idx
                    for idx in indices_data
                    if idx.get("index") in cold_indices_names
                ]
            else:
                # Handle case where indices_data might be a dict or other format
                cold_indices_data = []

            if not cold_indices_data:
                # Fallback: create basic data structure for cold indices
                cold_indices_data = []
                for index_name in cold_indices_names:
                    cold_indices_data.append(
                        {
                            "index": index_name,
                            "health": "unknown",
                            "status": "open",
                            "docs_count": 0,
                            "shards": 0,
                            "pri_size": "0b",
                            "size": "0b",
                            "phase": "🧊 cold",
                        }
                    )

            # Display cold indices in table format
            if self.args.format == "json":
                import json

                print(json.dumps(cold_indices_data, indent=2))
            else:
                # Add cold phase indicator to each index for display
                for idx in cold_indices_data:
                    ilm_info = index_ilms.get(idx["index"], {})
                    idx["ilm_phase"] = f"🧊 {ilm_info.get('phase', 'cold')}"
                    idx["ilm_policy"] = ilm_info.get("policy", "N/A")
                    idx["ilm_age"] = ilm_info.get("age", "N/A")

                # Show summary message
                self.es_client.show_message_box(
                    "Cold Indices Found",
                    f"Found {len(cold_indices_data)} indices in the cold ILM phase.\n\nThese indices have been moved to cold storage tier for long-term retention.",
                    message_style="white",
                    panel_style="bold blue",
                )

                # Use the standard table display
                use_pager = getattr(self.args, "pager", False)
                self.es_client.print_table_indices(
                    cold_indices_data, use_pager=use_pager
                )

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"Failed to retrieve cold indices information:\n{str(e)}",
                message_style="red",
                panel_style="red",
            )

    def _handle_regex_indices(self):
        """Handle indices matching regex patterns."""
        if self.args.format == "json":
            indices = self.es_client.filter_indices(
                pattern=self.args.regex, status=self.args.status
            )

            if self.args.delete:
                # For JSON format with deletion, create comprehensive output
                output = {"indices": indices, "deletion_requested": True}

                # Perform deletion and capture results
                deletion_result = self._handle_indices_deletion_json(indices)
                output["deletion_results"] = deletion_result

                print(json.dumps(output, indent=2))
            else:
                # Just print indices without deletion (convert to JSON format for consistency)
                print(json.dumps(indices, indent=2))
            return

        indices = self.es_client.filter_indices(
            pattern=self.args.regex, status=self.args.status
        )
        if not indices:
            self.es_client.show_message_box(
                "Indices",
                f"Pattern: {self.args.regex}\nThere were no matching indices found",
                message_style="white",
                panel_style="bold white",
            )
            return

        use_pager = getattr(self.args, "pager", False)
        self.es_client.print_table_indices(indices, use_pager=use_pager)

        if self.args.delete:
            self._handle_indices_deletion(indices)

    def _delete_indices_with_progress(self, indices):
        """
        Delete indices via the ES client, showing a Rich spinner on TTY when
        multiple deletions run (unless --quiet).
        """
        if isinstance(indices, list) and indices and isinstance(indices[0], dict):
            index_names = [
                indice.get("index") for indice in indices if indice.get("index")
            ]
        else:
            index_names = list(indices) if isinstance(indices, list) else [indices]

        total = len(index_names)
        use_status = (
            total > 0
            and self.console.is_terminal
            and not getattr(self.console, "is_dumb_terminal", False)
            and not getattr(self.args, "quiet", False)
        )

        if not use_status:
            return self.es_client.delete_indices(indices)

        with self.console.status(
            f"Deleting indices (0/{total})…",
            spinner="dots",
        ) as status:

            def on_progress(n: int, tot: int, name: str):
                shown = name if len(name) <= 64 else f"{name[:61]}…"
                status.update(
                    f"Deleting indices [bold]{n}[/bold]/{tot}: [dim]{shown}[/dim]"
                )

            return self.es_client.delete_indices(indices, on_progress=on_progress)

    def _render_indices_deletion_results(self, result: dict) -> None:
        """Rich panels and tables for index deletion outcomes (matches flush-style summaries)."""
        successful = result.get("successful_deletions", [])
        failed = result.get("failed_deletions", [])
        total_requested = result.get(
            "total_requested", len(successful) + len(failed)
        )
        max_rows = 40
        styles = self.es_client.style_system

        print()
        summary_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Label", style="bold", no_wrap=True)
        summary_table.add_column("Icon", justify="left", width=3)
        summary_table.add_column("Value", no_wrap=False)
        summary_table.add_row("Indices requested:", "📋", f"{total_requested:,}")
        summary_table.add_row("Removed successfully:", "✅", f"{len(successful):,}")
        if failed:
            summary_table.add_row("Failed:", "❌", f"{len(failed):,}")

        if failed and successful:
            outcome_style = "warning"
        elif failed:
            outcome_style = "error"
        else:
            outcome_style = "success"

        summary_panel = Panel(
            summary_table,
            title="🗑️ Index deletion summary",
            border_style=styles.get_semantic_style(outcome_style),
            padding=(1, 2),
        )
        self.console.print(summary_panel)

        if successful:
            idx_table = InnerTable(
                show_header=True,
                box=box.ROUNDED,
                padding=(0, 1),
                header_style="bold cyan",
            )
            idx_table.add_column("#", style="dim", justify="right", width=5)
            idx_table.add_column("Index", style="white", overflow="fold")
            shown = successful[:max_rows]
            for i, name in enumerate(shown, start=1):
                idx_table.add_row(f"{i:,}", name)
            omitted = len(successful) - max_rows
            if omitted > 0:
                idx_table.add_row(
                    "",
                    Text(f"… and {omitted:,} more not shown", style="dim"),
                )

            removed_panel = Panel(
                idx_table,
                title=f"✅ Removed indices ({len(successful):,} total)",
                border_style=styles.get_semantic_style("success"),
                padding=(1, 2),
            )
            print()
            self.console.print(removed_panel)

        if failed:
            fail_table = InnerTable(
                show_header=True,
                box=box.ROUNDED,
                padding=(0, 1),
                header_style="bold red",
            )
            fail_table.add_column("Index", style="white", overflow="fold")
            fail_table.add_column("Error", style="red", overflow="fold")
            shown_f = failed[:max_rows]
            for item in shown_f:
                if isinstance(item, dict):
                    err = str(item.get("error", "unknown error"))
                    if len(err) > 200:
                        err = err[:197] + "…"
                    fail_table.add_row(item.get("index", "unknown"), err)
                else:
                    fail_table.add_row(str(item), "")
            omitted_f = len(failed) - max_rows
            if omitted_f > 0:
                fail_table.add_row(
                    Text(f"… and {omitted_f:,} more failures", style="dim"),
                    "",
                )

            fail_panel = Panel(
                fail_table,
                title=f"❌ Failed deletions ({len(failed):,} total)",
                border_style=styles.get_semantic_style("error"),
                padding=(1, 2),
            )
            print()
            self.console.print(fail_panel)

        print()

    def _handle_indices_deletion(self, indices):
        """Handle deletion of multiple indices with confirmation."""
        # Extract index names from the indices data
        if isinstance(indices, list) and indices and isinstance(indices[0], dict):
            index_names = [idx.get("index", "unknown") for idx in indices]
        else:
            index_names = indices if isinstance(indices, list) else [str(indices)]

        # Show confirmation with Rich prompt (unless --yes flag is used)
        if getattr(self.args, "yes", False):
            self.console.print(
                f"[dim]🔶  Auto-confirmed deletion of {len(index_names)} indices (--yes flag)[/dim]"
            )
        elif not Confirm.ask(
            f"🔶  Are you sure you want to delete {len(index_names)} indices?"
        ):
            self.console.print("[yellow]Operation cancelled.[/yellow]")
            return

        # Perform deletion
        try:
            result = self._delete_indices_with_progress(indices)

            # Show results
            if isinstance(result, dict):
                self._render_indices_deletion_results(result)
            else:
                done = Panel(
                    self.es_client.style_system.create_semantic_text(
                        "Deletion completed.",
                        "success",
                        justify="center",
                    ),
                    title="✅ Done",
                    border_style=self.es_client.style_system.get_semantic_style(
                        "success"
                    ),
                    padding=(1, 2),
                )
                print()
                self.console.print(done)
                print()

        except Exception as e:
            self.console.print(f"[red]❌ Error during deletion: {e}[/red]")

    def _handle_indices_deletion_json(self, indices):
        """Handle deletion of multiple indices for JSON output format."""
        # Extract index names from the indices data
        if isinstance(indices, list) and indices and isinstance(indices[0], dict):
            index_names = [idx.get("index", "unknown") for idx in indices]
        else:
            index_names = indices if isinstance(indices, list) else [str(indices)]

        # Check for confirmation (unless --yes flag is used)
        if not getattr(self.args, "yes", False):
            if not Confirm.ask(
                f"🔶  Are you sure you want to delete {len(index_names)} indices?"
            ):
                return {
                    "status": "cancelled",
                    "message": "Operation cancelled by user",
                    "total_requested": len(index_names),
                }

        # Perform deletion
        try:
            result = self._delete_indices_with_progress(indices)

            # Return structured result for JSON output
            if isinstance(result, dict):
                result["status"] = "completed"
                return result
            else:
                return {
                    "status": "completed",
                    "message": "Deletion completed successfully",
                    "total_requested": len(index_names),
                    "successful_deletions": index_names,
                    "failed_deletions": [],
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during deletion: {str(e)}",
                "total_requested": len(index_names),
                "successful_deletions": [],
                "failed_deletions": [{"error": str(e)}],
            }
