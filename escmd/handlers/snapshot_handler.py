"""
Snapshot handler for escmd snapshot-related commands.

Handles commands like snapshots list and status.
"""

import json
import os
import re
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.console import Console

from .base_handler import BaseHandler
from commands.snapshot_commands import SnapshotCommands


class SnapshotHandler(BaseHandler):
    """Handler for snapshot-related commands."""

    def handle_repositories(self):
        """
        Handle repositories command and subcommands.
        """
        # Check if we have a repositories_action (new subcommand structure)
        if hasattr(self.args, "repositories_action") and self.args.repositories_action:
            if self.args.repositories_action == "list":
                self._handle_list_repositories()
            elif self.args.repositories_action == "create":
                self._handle_create_repository()
            elif self.args.repositories_action == "verify":
                self._handle_verify_repository()
            else:
                self.es_client.show_message_box(
                    "Error",
                    f"Unknown repositories action: {self.args.repositories_action}",
                    message_style=self.es_client.style_system.get_semantic_style(
                        "secondary"
                    ),
                    panel_style=self.es_client.style_system.get_semantic_style("error"),
                )
        else:
            # Backward compatibility: if no subcommand, default to list
            self._handle_list_repositories()

    def handle_snapshots(self):
        """
        Handle snapshot-related commands.
        """
        if (
            not hasattr(self.args, "snapshots_action")
            or self.args.snapshots_action is None
        ):
            self._show_snapshots_help()
            return

        if self.args.snapshots_action == "list":
            self._handle_list_snapshots()
        elif self.args.snapshots_action == "status":
            self._handle_snapshot_status()
        elif self.args.snapshots_action == "info":
            self._handle_snapshot_info()
        elif self.args.snapshots_action == "create":
            self._handle_create_snapshot()
        elif self.args.snapshots_action == "delete":
            self._handle_delete_snapshot()
        elif self.args.snapshots_action == "list-restored":
            self._handle_list_restored()
        elif self.args.snapshots_action == "clear-staged":
            self._handle_clear_staged()
        elif self.args.snapshots_action == "repositories":
            self._handle_list_repositories()
        else:
            self.es_client.show_message_box(
                "Error",
                f"Unknown snapshots action: {self.args.snapshots_action}",
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )

    def _show_snapshots_help(self):
        """Display comprehensive help screen for snapshot commands."""
        console = Console()

        # Get theme colors
        info_style = self.es_client.style_system.get_semantic_style("info")
        success_style = self.es_client.style_system.get_semantic_style("success")
        primary_style = self.es_client.style_system.get_semantic_style("primary")
        secondary_style = self.es_client.style_system.get_semantic_style("secondary")
        border_style = self.es_client.style_system._get_style(
            "table_styles", "border_style", "white"
        )

        # Create main title with theme colors
        title_text = self.es_client.style_system.create_semantic_text(
            "📦 Elasticsearch Snapshots Management", "info"
        )
        title_panel = Panel(
            title_text,
            subtitle="Available Commands & Usage Examples",
            border_style=info_style,
            padding=(1, 2),
            expand=True,
        )

        # Create commands table with full width
        commands_table = Table(
            show_header=True,
            header_style=primary_style,
            border_style=border_style,
            expand=True,
            show_lines=True,
        )
        commands_table.add_column("Command", style=info_style, ratio=2)
        commands_table.add_column("Description", style="white", ratio=3)
        commands_table.add_column("Usage Example", style=success_style, ratio=3)

        # Add command rows
        commands_table.add_row(
            "list",
            "List all snapshots from configured repository",
            "./escmd.py snapshots list",
        )
        commands_table.add_row(
            "list [pattern]",
            "Filter snapshots by regex pattern",
            "./escmd.py snapshots list 'logs.*'",
        )
        commands_table.add_row(
            "status <name>",
            "Show detailed status of a specific snapshot",
            "./escmd.py snapshots status snapshot_name",
        )
        commands_table.add_row(
            "info <name>",
            "Show comprehensive information about a snapshot",
            "./escmd.py snapshots info snapshot_name",
        )
        commands_table.add_row(
            "create <target>",
            "Create snapshot of indices or datastreams",
            "./escmd.py snapshots create 'logs-*'",
        )
        commands_table.add_row(
            "delete <name>",
            "Delete a specific snapshot",
            "./escmd.py snapshots delete snapshot_name",
        )
        commands_table.add_row(
            "list-restored",
            "List all restored snapshots/indices tracked in system",
            "./escmd.py snapshots list-restored",
        )
        commands_table.add_row(
            "clear-staged",
            "Clear all pending restores (in INIT status)",
            "./escmd.py snapshots clear-staged",
        )
        commands_table.add_row(
            "repositories",
            "List all configured snapshot repositories",
            "./escmd.py snapshots repositories",
        )

        # Create options table with full width
        options_table = Table(
            show_header=True,
            header_style=primary_style,
            border_style=border_style,
            expand=True,
            show_lines=True,
        )
        options_table.add_column("Common Options", style=secondary_style, ratio=2)
        options_table.add_column("Description", style="white", ratio=3)
        options_table.add_column("Example", style=success_style, ratio=3)

        options_table.add_row(
            "--format json",
            "Output in JSON format instead of table",
            "./escmd.py snapshots list --format json",
        )
        options_table.add_row(
            "--pager",
            "Force pager for scrolling long lists",
            "./escmd.py snapshots list --pager",
        )
        options_table.add_row(
            "--slow",
            "Use slow listing mode (full metadata)",
            "./escmd.py snapshots list --slow",
        )
        options_table.add_row(
            "--repository <name>",
            "Specify snapshot repository",
            "./escmd.py snapshots list --repository backup-repo",
        )
        options_table.add_row(
            "--wait",
            "Wait for snapshot completion (create only)",
            "./escmd.py snapshots create 'logs-*' --wait",
        )
        options_table.add_row(
            "--dry-run",
            "Show what would be snapshotted (create only)",
            "./escmd.py snapshots create 'logs-*' --dry-run",
        )
        options_table.add_row(
            "--force",
            "Skip confirmation prompts",
            "./escmd.py snapshots delete snapshot_name --force",
        )

        # Create quick start panel with theme colors
        quick_start_lines = [
            self.es_client.style_system.create_semantic_text(
                "🚀 Quick Start:", "primary"
            ),
            "",
            "1. List all snapshots:",
            "   ./escmd.py snapshots list",
            "",
            "2. Check specific snapshot status:",
            "   ./escmd.py snapshots status <snapshot_name>",
            "",
            "3. Create new snapshot:",
            "   ./escmd.py snapshots create 'index-pattern-*'",
            "",
            self.es_client.style_system.create_semantic_text(
                "💡 Tip: Use tab completion or --help on any command for more options",
                "secondary",
            ),
        ]

        # Create a Text object with proper formatting
        quick_start_text = Text()
        for i, line in enumerate(quick_start_lines):
            if isinstance(line, Text):
                quick_start_text.append(line)
            elif line.strip().startswith("./escmd.py"):
                quick_start_text.append(line, style=success_style)
            else:
                quick_start_text.append(line)

            # Add newline unless it's the last line
            if i < len(quick_start_lines) - 1:
                quick_start_text.append("\n")

        quick_start_panel = Panel(
            quick_start_text,
            title="🏁 Quick Start Guide",
            border_style=success_style,
            padding=(1, 2),
            expand=True,
        )

        # Display all sections
        console.print()
        console.print(title_panel)
        console.print()
        console.print(
            Panel(
                commands_table,
                title="📋 Available Commands",
                border_style=border_style,
                expand=True,
            )
        )
        console.print()
        console.print(
            Panel(
                options_table,
                title="🔩 Common Options",
                border_style=border_style,
                expand=True,
            )
        )
        console.print()
        console.print(quick_start_panel)
        console.print()

    def _handle_list_snapshots(self):
        """
        List all snapshots from the configured repository.
        """
        # Check if elastic_s3snapshot_repo is configured for this cluster
        elastic_s3snapshot_repo = self.location_config.get("elastic_s3snapshot_repo")

        if not elastic_s3snapshot_repo:
            self.es_client.show_message_box(
                "Configuration Error",
                f"No 'elastic_s3snapshot_repo' configured for cluster '{self.args.locations}'.\n"
                f"Please add 'elastic_s3snapshot_repo: \"your-repo-name\"' to the cluster configuration in elastic_servers.yml",
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )
            return

        try:
            # Create console and progress display
            console = Console()

            # Get theme-based styles for the spinner
            spinner_color = self.es_client.style_system.get_semantic_style("info")

            # Check the listing mode (defaults to fast)
            mode = getattr(self.args, "mode", "fast")
            use_fast_mode = mode == "fast"

            # Use a simple spinner status without progress bar
            # Set refresh_per_second to a lower value to reduce flickering
            status_message = (
                f"[bold]Fetching snapshots from repository '{elastic_s3snapshot_repo}'"
            )
            if use_fast_mode:
                status_message += " (fast mode)"
            else:
                status_message += " (full metadata)"
            status_message += "..."

            with console.status(
                status_message,
                spinner="dots",
                spinner_style=spinner_color,
                refresh_per_second=5,  # Lower refresh rate to reduce flickering
            ) as status:
                # Fetch snapshots using fast or regular mode
                if use_fast_mode:
                    snapshots = self.es_client.list_snapshots_fast(
                        elastic_s3snapshot_repo
                    )
                else:
                    snapshots = self.es_client.list_snapshots(elastic_s3snapshot_repo)

            # Check if there was an error from the snapshots command
            last_error = getattr(self.es_client.snapshot_commands, "last_error", None)
            if last_error:
                self.es_client.show_message_box(
                    "Repository Error",
                    f"{last_error}",
                    message_style=self.es_client.style_system.get_semantic_style(
                        "secondary"
                    ),
                    panel_style=self.es_client.style_system.get_semantic_style("error"),
                )
                return

            if not snapshots:
                self.es_client.show_message_box(
                    "No Snapshots",
                    f"No snapshots found in repository '{elastic_s3snapshot_repo}' or repository doesn't exist.",
                )
                return

            # Apply regex filtering if pattern is provided
            original_count = len(snapshots)
            pattern = getattr(self.args, "pattern", None)

            if pattern:
                try:
                    compiled_pattern = re.compile(pattern, re.IGNORECASE)
                    snapshots = [
                        s for s in snapshots if compiled_pattern.search(s["snapshot"])
                    ]
                except re.error as e:
                    self.es_client.show_message_box(
                        "Invalid Pattern",
                        f"Invalid regex pattern '{pattern}': {str(e)}",
                    )
                    return

                if not snapshots:
                    self.es_client.show_message_box(
                        "No Matches",
                        f"No snapshots found matching pattern '{pattern}' in repository '{elastic_s3snapshot_repo}'.\n"
                        f"Total snapshots in repository: {original_count}",
                    )
                    return

            # Display snapshots based on format
            format_type = getattr(self.args, "format", "table")
            if format_type == "json":
                self._display_snapshots_json(
                    snapshots, elastic_s3snapshot_repo, pattern, original_count
                )
            else:
                use_pager = getattr(self.args, "pager", False)
                mode = getattr(self.args, "mode", "fast")
                use_fast_mode = mode == "fast"
                self._display_snapshots_table(
                    snapshots,
                    elastic_s3snapshot_repo,
                    pattern,
                    original_count,
                    use_pager=use_pager,
                    fast_mode=use_fast_mode,
                )

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"Error listing snapshots: {str(e)}",
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )

    def _display_snapshots_table(
        self,
        snapshots,
        repository_name,
        pattern=None,
        original_count=None,
        use_pager=False,
        fast_mode=False,
    ):
        """
        Display snapshots in enhanced multi-panel format following the 2.0+ style.
        """
        console = self.console

        # Calculate statistics
        total_snapshots = len(snapshots)
        state_counts = {"SUCCESS": 0, "FAILED": 0, "IN_PROGRESS": 0, "PARTIAL": 0}
        total_indices = 0
        total_failures = 0

        # Analyze snapshots for statistics
        for snapshot in snapshots:
            state = snapshot.get("state", "UNKNOWN")
            state_counts[state] = state_counts.get(state, 0) + 1
            total_indices += snapshot.get("indices_count", 0)
            total_failures += len(snapshot.get("failures", []))

        # Create title panel with colored statistics
        if pattern:
            title_text = f"📦 Elasticsearch Snapshots Overview \n(Repository: {repository_name}, Pattern: {pattern})"
        else:
            title_text = (
                f"📦 Elasticsearch Snapshots Overview \n(Repository: {repository_name})"
            )

        # Add fast mode indicator to title if enabled
        if fast_mode:
            title_text += " ⚡ Fast Mode"

        # Create colorized subtitle with theme-based styling for statistics
        from rich.text import Text

        subtitle_rich = Text()
        subtitle_rich.append("Total: ", style="default")
        subtitle_rich.append(
            str(total_snapshots),
            style=self.es_client.style_system._get_style("semantic", "info", "cyan"),
        )
        subtitle_rich.append(" | Success: ", style="default")
        subtitle_rich.append(
            str(state_counts.get("SUCCESS", 0)),
            style=self.es_client.style_system._get_style(
                "semantic", "success", "green"
            ),
        )

        if state_counts.get("FAILED", 0) > 0:
            subtitle_rich.append(" | Failed: ", style="default")
            subtitle_rich.append(
                str(state_counts.get("FAILED", 0)),
                style=self.es_client.style_system._get_style(
                    "semantic", "error", "red"
                ),
            )

        if state_counts.get("IN_PROGRESS", 0) > 0:
            subtitle_rich.append(" | In Progress: ", style="default")
            subtitle_rich.append(
                str(state_counts.get("IN_PROGRESS", 0)),
                style=self.es_client.style_system._get_style(
                    "semantic", "warning", "yellow"
                ),
            )

        if state_counts.get("PARTIAL", 0) > 0:
            subtitle_rich.append(" | Partial: ", style="default")
            subtitle_rich.append(
                str(state_counts.get("PARTIAL", 0)),
                style=self.es_client.style_system._get_style(
                    "semantic", "warning", "yellow"
                ),
            )

        if pattern and original_count and original_count != total_snapshots:
            subtitle_rich.append(" | Showing: ", style="default")
            subtitle_rich.append(
                f"{total_snapshots} of {original_count}",
                style=self.es_client.style_system._get_style(
                    "semantic", "secondary", "bright_blue"
                ),
            )
        else:
            subtitle_rich.append(" | Total Indices: ", style="default")
            subtitle_rich.append(
                f"{total_indices:,}",
                style=self.es_client.style_system._get_style(
                    "semantic", "primary", "bright_magenta"
                ),
            )

        if total_failures > 0:
            subtitle_rich.append(" | Failures: ", style="default")
            subtitle_rich.append(
                str(total_failures),
                style=self.es_client.style_system._get_style(
                    "semantic", "error", "red"
                ),
            )

        title_panel = Panel(
            self.es_client.style_system.create_semantic_text(
                title_text, "info", justify="center"
            ),
            subtitle=subtitle_rich,
            border_style=self.es_client.style_system.get_semantic_style("info"),
            padding=(1, 2),
        )

        # Create enhanced snapshots table with emoji headers
        table = Table(
            show_header=True,
            header_style=self.es_client.style_system._get_style(
                "table_styles", "header_style", "bold white"
            ),
            border_style=self.es_client.style_system._get_style(
                "table_styles", "border_style", "white"
            ),
            title="📦 Elasticsearch Snapshots",
            title_style=self.es_client.style_system._get_style(
                "table_styles", "border_style", "white"
            ),
            expand=True,
            box=self.es_client.style_system.get_table_box(),
        )
        table.add_column(
            "📸 Snapshot Name",
            style=self.es_client.style_system.get_semantic_style("info"),
            no_wrap=True,
            overflow="ellipsis",
        )
        table.add_column("🎯 State", justify="center", width=12, no_wrap=True)
        table.add_column(
            "📅 Start Time",
            style=self.es_client.style_system.get_semantic_style("warning"),
            width=16,
            no_wrap=True,
        )
        table.add_column(
            "🕐 Duration",
            style=self.es_client.style_system.get_semantic_style("info"),
            width=8,
            justify="center",
            no_wrap=True,
        )
        table.add_column(
            "📊 Indices",
            style=self.es_client.style_system.get_semantic_style("primary"),
            width=8,
            justify="right",
            no_wrap=True,
        )
        table.add_column(
            "❌ Failures",
            style=self.es_client.style_system.get_semantic_style("error"),
            width=8,
            justify="right",
            no_wrap=True,
        )

        for snapshot in snapshots:
            # Enhanced state formatting with icons
            state = snapshot.get("state", "UNKNOWN")
            if state == "SUCCESS":
                state_display = "✅ Success"
                row_style = self.es_client.style_system.get_semantic_style("success")
            elif state == "IN_PROGRESS":
                state_display = "⏳ Progress"
                row_style = self.es_client.style_system.get_semantic_style("warning")
            elif state == "FAILED":
                state_display = "❌ Failed"
                row_style = self.es_client.style_system.get_semantic_style("error")
            elif state == "PARTIAL":
                state_display = "🔶 Partial"
                row_style = self.es_client.style_system.get_semantic_style("warning")
            else:
                state_display = f"❓ {state}"
                row_style = self.es_client.style_system.get_semantic_style("secondary")

            # Format failures count
            failures_count = len(snapshot.get("failures", []))
            failures_text = str(failures_count)

            # Get values with fallbacks
            snapshot_name = snapshot.get("snapshot", "N/A")
            start_time = snapshot.get("start_time_formatted", "N/A")
            duration = snapshot.get("duration", "N/A")
            indices_count = f"{snapshot.get('indices_count', 0):,}"

            table.add_row(
                snapshot_name,
                state_display,
                start_time,
                duration,
                indices_count,
                failures_text,
                style=row_style,
            )

        # Create combined legend and actions panel with equal width columns
        combined_table = Table.grid(
            padding=(0, 3), expand=True
        )  # Added expand=True and increased padding
        combined_table.add_column(
            style=self.es_client.style_system.get_semantic_style("secondary"),
            no_wrap=False,
            ratio=1,
            justify="left",
        )  # 50% width, left aligned
        combined_table.add_column(
            style=self.es_client.style_system.get_semantic_style("secondary"),
            no_wrap=False,
            ratio=1,
            justify="left",
        )  # 50% width, left aligned

        # Left column - Legend with better alignment
        legend_content = Text()
        legend_content.append(
            "🔍 ", style=self.es_client.style_system.get_semantic_style("info")
        )
        legend_content.append(
            "Legend",
            style=self.es_client.style_system.get_semantic_style("info") + " underline",
        )
        legend_content.append(
            "\n", style=self.es_client.style_system.get_semantic_style("secondary")
        )

        # Status indicators with proper alignment (no extra spaces)
        legend_content.append(
            "✅ ", style=self.es_client.style_system.get_semantic_style("success")
        )
        legend_content.append(
            "Success", style=self.es_client.style_system.get_semantic_style("success")
        )
        legend_content.append(
            "     → Completed successfully\n",
            style="dim " + self.es_client.style_system.get_semantic_style("secondary"),
        )

        legend_content.append(
            "⏳ ", style=self.es_client.style_system.get_semantic_style("warning")
        )
        legend_content.append(
            "In Progress",
            style=self.es_client.style_system.get_semantic_style("warning"),
        )
        legend_content.append(
            " → Currently running\n",
            style="dim " + self.es_client.style_system.get_semantic_style("secondary"),
        )

        legend_content.append(
            "❌ ", style=self.es_client.style_system.get_semantic_style("error")
        )
        legend_content.append(
            "Failed", style=self.es_client.style_system.get_semantic_style("error")
        )
        legend_content.append(
            "      → Failed to complete\n",
            style="dim " + self.es_client.style_system.get_semantic_style("secondary"),
        )

        legend_content.append(
            "🔶  ", style=self.es_client.style_system.get_semantic_style("warning")
        )
        legend_content.append(
            "Partial", style=self.es_client.style_system.get_semantic_style("warning")
        )
        legend_content.append(
            "     → Completed with warnings",
            style="dim " + self.es_client.style_system.get_semantic_style("secondary"),
        )

        # Right column - Quick Actions (more compact)
        actions_content = Text()
        actions_content.append(
            "🚀 ", style=self.es_client.style_system.get_semantic_style("primary")
        )
        actions_content.append(
            "Quick Actions",
            style=self.es_client.style_system.get_semantic_style("primary")
            + " underline",
        )
        actions_content.append(
            "\n", style=self.es_client.style_system.get_semantic_style("secondary")
        )

        # Compact command examples
        actions_content.append(
            "📋 Filter: ", style=self.es_client.style_system.get_semantic_style("info")
        )
        actions_content.append(
            "./escmd.py snapshots list <pattern>\n",
            style="dim " + self.es_client.style_system.get_semantic_style("success"),
        )

        actions_content.append(
            "📄 Pager: ", style=self.es_client.style_system.get_semantic_style("info")
        )
        actions_content.append(
            "./escmd.py snapshots list --pager\n",
            style="dim " + self.es_client.style_system.get_semantic_style("success"),
        )

        actions_content.append(
            "💾 JSON: ", style=self.es_client.style_system.get_semantic_style("info")
        )
        actions_content.append(
            "./escmd.py snapshots list --format json\n",
            style="dim " + self.es_client.style_system.get_semantic_style("success"),
        )

        actions_content.append(
            "🎯 Example: ", style=self.es_client.style_system.get_semantic_style("info")
        )
        actions_content.append(
            "./escmd.py snapshots list 'logs-app.*'",
            style="dim " + self.es_client.style_system.get_semantic_style("success"),
        )

        combined_table.add_row(legend_content, actions_content)

        combined_panel = Panel(
            combined_table,
            title=self.es_client.style_system.create_semantic_text(
                "🔍 Legend & 🚀 Quick Actions", "primary"
            ),
            title_align="center",
            border_style="bright_blue",
            padding=(1, 2),  # Reduced padding for more compact display
            expand=True,  # Force panel to expand to full terminal width
            width=None,  # Allow panel to use full available width
        )

        # Check if we should use pager for large datasets
        from configuration_manager import ConfigurationManager
        import os

        try:
            config_file = os.path.join(os.path.dirname(__file__), "elastic_servers.yml")
            config_manager = ConfigurationManager(
                config_file, os.path.join(os.path.dirname(config_file), "escmd.json")
            )

            # Try to get paging settings with fallback to defaults
            paging_enabled = getattr(
                config_manager, "get_paging_enabled", lambda: False
            )()
            paging_threshold = getattr(
                config_manager, "get_paging_threshold", lambda: 50
            )()
        except Exception:
            # Fallback to safe defaults if configuration fails
            paging_enabled = False
            paging_threshold = 50

        should_use_pager = use_pager or (
            paging_enabled and len(snapshots) > paging_threshold
        )

        if should_use_pager:
            # First show in pager for scrolling through large datasets
            with console.pager():
                console.print()
                console.print(title_panel)
                console.print()
                console.print(table)
                console.print()
                console.print(combined_panel)
                console.print()

            # Then display normally so content remains visible after pager exit
            print()
            console.print(title_panel)
            print()
            console.print(table)
            print()
            console.print(combined_panel)
            print()
        else:
            # Normal display with enhanced layout
            print()
            console.print(title_panel)
            print()
            console.print(table)
            print()
            console.print(combined_panel)
            print()

    def _display_snapshots_json(
        self, snapshots, repository_name, pattern=None, original_count=None
    ):
        """
        Display snapshots in JSON format.
        """
        # Create output structure
        output = {
            "repository": repository_name,
            "total_snapshots": len(snapshots),
            "snapshots": snapshots,
        }

        # Add filtering information if pattern was used
        if pattern and original_count:
            output["filter_pattern"] = pattern
            output["original_total"] = original_count
            output["filtered"] = True
        else:
            output["filtered"] = False

        # Output JSON
        self.es_client.pretty_print_json(output)

    def _handle_snapshot_status(self):
        """
        Handle snapshot status command to show detailed status of a specific snapshot.
        """
        # Get snapshot name from arguments
        snapshot_name = self.args.snapshot_name

        # Determine repository to use
        repository_name = getattr(self.args, "repository", None)
        if not repository_name:
            # Use configured repository for this cluster
            repository_name = self.location_config.get("elastic_s3snapshot_repo")

        if not repository_name:
            self.es_client.show_message_box(
                "Configuration Error",
                f"No snapshot repository specified.\n"
                f"Either use --repository option or configure 'elastic_s3snapshot_repo' for cluster '{self.current_location}'.\n"
                f"Please add 'elastic_s3snapshot_repo: \"your-repo-name\"' to the cluster configuration in elastic_servers.yml",
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )
            return

        try:
            # Get snapshot status from Elasticsearch
            snapshot_status = self.es_client.get_snapshot_status(
                repository_name, snapshot_name
            )

            if not snapshot_status:
                self.es_client.show_message_box(
                    "Snapshot Not Found",
                    f"Snapshot '{snapshot_name}' not found in repository '{repository_name}'.\n"
                    f"Use './escmd.py snapshots list' to see available snapshots.",
                    message_style=self.es_client.style_system.get_semantic_style(
                        "secondary"
                    ),
                    panel_style=self.es_client.style_system.get_semantic_style("error"),
                )
                return

            # Display the status based on format
            if self.args.format == "json":
                self.es_client.pretty_print_json(snapshot_status)
            else:
                self.es_client.display_snapshot_status(snapshot_status, repository_name)

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"Error getting snapshot status: {str(e)}",
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )

    def _handle_create_snapshot(self):
        """
        Handle creating snapshots for indices or datastreams.
        """
        import re

        # Get repository name
        repository_name = getattr(
            self.args, "repository", None
        ) or self.location_config.get("elastic_s3snapshot_repo")

        if not repository_name:
            self.es_client.show_message_box(
                "Configuration Error",
                f"No snapshot repository specified.\n"
                f"Either use --repository option or configure 'elastic_s3snapshot_repo' for cluster '{self.current_location}'.\n"
                f"Please add 'elastic_s3snapshot_repo: \"your-repo-name\"' to the cluster configuration in elastic_servers.yml",
                message_style="bold white",
                panel_style="red",
            )
            return

        target = self.args.target
        target_type = getattr(self.args, "type", "auto")
        wait_for_completion = getattr(self.args, "wait", False)
        dry_run = getattr(self.args, "dry_run", False)
        force = getattr(self.args, "force", False)

        try:
            # Determine if target is a regex pattern
            is_regex = any(
                char in target
                for char in [
                    "*",
                    "?",
                    "[",
                    "]",
                    ".",
                    "^",
                    "$",
                    "+",
                    "(",
                    ")",
                    "{",
                    "}",
                    "|",
                    "\\",
                ]
            )

            if is_regex:
                # Handle regex pattern - get matching indices/datastreams
                targets_to_snapshot = []

                if target_type in ["index", "auto"]:
                    # Get matching indices
                    matching_indices = self._get_matching_indices(target)
                    for index_name in matching_indices:
                        targets_to_snapshot.append(
                            {
                                "name": index_name,
                                "type": "index",
                                "snapshot_name": f"snapshot_{index_name}",
                            }
                        )

                if target_type in ["datastream", "auto"]:
                    # Get matching datastreams
                    matching_datastreams = self._get_matching_datastreams(target)
                    for ds_name in matching_datastreams:
                        targets_to_snapshot.append(
                            {
                                "name": ds_name,
                                "type": "datastream",
                                "snapshot_name": f"snapshot_{ds_name}",
                            }
                        )

                if not targets_to_snapshot:
                    self.es_client.show_message_box(
                        "No Matches",
                        f"No indices or datastreams found matching pattern: {target}",
                        message_style=self.es_client.style_system.get_semantic_style(
                            "secondary"
                        ),
                        panel_style=self.es_client.style_system.get_semantic_style(
                            "warning"
                        ),
                    )
                    return

            else:
                # Single target
                # Auto-detect type if not specified
                actual_type = target_type
                if target_type == "auto":
                    actual_type = self._detect_target_type(target)

                if actual_type is None:
                    self.es_client.show_message_box(
                        "Target Not Found",
                        f"Could not find index or datastream with name: {target}",
                        message_style="bold white",
                        panel_style="red",
                    )
                    return

                targets_to_snapshot = [
                    {
                        "name": target,
                        "type": actual_type,
                        "snapshot_name": f"snapshot_{target}",
                    }
                ]

            # Show what will be snapshotted
            self._display_snapshot_plan(targets_to_snapshot, repository_name, dry_run)

            if dry_run:
                return

            # Confirm unless --force is used
            if not force:
                if len(targets_to_snapshot) > 1:
                    response = (
                        input(f"\nCreate {len(targets_to_snapshot)} snapshots? (y/N): ")
                        .strip()
                        .lower()
                    )
                else:
                    response = (
                        input(
                            f"\nCreate snapshot '{targets_to_snapshot[0]['snapshot_name']}'? (y/N): "
                        )
                        .strip()
                        .lower()
                    )

                if response not in ["y", "yes"]:
                    print("Snapshot creation cancelled.")
                    return

            # Create snapshots
            successful_snapshots = []
            failed_snapshots = []

            for target_info in targets_to_snapshot:
                print(f"\nCreating snapshot '{target_info['snapshot_name']}'...")

                if target_info["type"] == "index":
                    response = self.es_client.create_snapshot(
                        repository_name=repository_name,
                        snapshot_name=target_info["snapshot_name"],
                        indices=[target_info["name"]],
                        wait_for_completion=wait_for_completion,
                    )
                else:  # datastream
                    response = self.es_client.create_snapshot(
                        repository_name=repository_name,
                        snapshot_name=target_info["snapshot_name"],
                        datastreams=[target_info["name"]],
                        wait_for_completion=wait_for_completion,
                    )

                if response:
                    successful_snapshots.append(target_info)
                    if wait_for_completion:
                        print(
                            f"✅ Snapshot '{target_info['snapshot_name']}' completed successfully"
                        )
                    else:
                        print(
                            f"✅ Snapshot '{target_info['snapshot_name']}' initiated successfully"
                        )
                else:
                    failed_snapshots.append(target_info)
                    print(
                        f"❌ Failed to create snapshot '{target_info['snapshot_name']}'"
                    )

            # Display summary
            self._display_snapshot_summary(
                successful_snapshots, failed_snapshots, repository_name
            )

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"Error creating snapshot: {str(e)}",
                message_style="bold white",
                panel_style="red",
            )

    def _get_matching_indices(self, pattern):
        """Get indices matching the given regex pattern."""
        import re

        try:
            # Get all indices
            indices_response = self.es_client.es.cat.indices(format="json", h="index")
            compiled_pattern = re.compile(pattern, re.IGNORECASE)

            matching_indices = []
            for index_info in indices_response:
                index_name = index_info["index"]
                if compiled_pattern.search(index_name):
                    matching_indices.append(index_name)

            return matching_indices

        except Exception as e:
            print(f"Error getting indices: {str(e)}")
            return []

    def _get_matching_datastreams(self, pattern):
        """Get datastreams matching the given regex pattern."""
        import re

        try:
            datastreams_data = self.es_client.list_datastreams()
            datastreams_list = datastreams_data.get("data_streams", [])
            compiled_pattern = re.compile(pattern, re.IGNORECASE)

            matching_datastreams = []
            for ds in datastreams_list:
                ds_name = ds.get("name", "")
                if compiled_pattern.search(ds_name):
                    matching_datastreams.append(ds_name)

            return matching_datastreams

        except Exception as e:
            print(f"Error getting datastreams: {str(e)}")
            return []

    def _detect_target_type(self, target):
        """Detect whether target is an index or datastream."""
        try:
            # Check if it's a datastream first
            datastreams_data = self.es_client.list_datastreams()
            datastreams_list = datastreams_data.get("data_streams", [])
            for ds in datastreams_list:
                if ds.get("name") == target:
                    return "datastream"

            # Check if it's an index
            try:
                indices_response = self.es_client.es.cat.indices(
                    format="json", h="index"
                )
                for index_info in indices_response:
                    if index_info["index"] == target:
                        return "index"
            except:
                pass

            return None

        except Exception as e:
            print(f"Error detecting target type: {str(e)}")
            return None

    def _display_snapshot_plan(self, targets, repository_name, dry_run=False):
        """Display what snapshots will be created."""
        import os
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from esclient import get_theme_styles
        from configuration_manager import ConfigurationManager

        # Handle both dual-file and single-file configuration modes
        if self.config_file is not None:
            # Single-file mode
            config_manager = ConfigurationManager(
                self.config_file,
                os.path.join(os.path.dirname(self.config_file), "escmd.json"),
            )
        else:
            # Dual-file mode - config_file is None, create ConfigurationManager with default paths
            script_directory = os.path.dirname(os.path.abspath(__file__))
            parent_directory = os.path.dirname(script_directory)
            state_file = os.path.join(parent_directory, "escmd.json")
            config_manager = ConfigurationManager(state_file_path=state_file)
        current_styles = get_theme_styles(config_manager)

        action = "Would create" if dry_run else "Will create"
        action_emoji = "🎯" if dry_run else "📸"

        # Create the table without title (panel will have the title)
        table = Table(
            show_header=True,
            header_style=current_styles["header_style"],
            border_style=self.es_client.style_system.get_semantic_style("info"),
            box=self.es_client.style_system.get_table_box(),
        )
        table.add_column(
            "📸 Snapshot Name",
            style=self.es_client.style_system.get_semantic_style("info"),
            no_wrap=True,
        )
        table.add_column(
            "🎯 Target",
            style=self.es_client.style_system.get_semantic_style("secondary"),
        )
        table.add_column(
            "📋 Type", style=self.es_client.style_system.get_semantic_style("warning")
        )

        for target_info in targets:
            table.add_row(
                target_info["snapshot_name"],
                target_info["name"],
                target_info["type"].capitalize(),
            )

        # Create panel title with visual elements
        title_text = Text()
        title_text.append(
            f"{action_emoji} ",
            style=self.es_client.style_system.get_semantic_style("primary"),
        )
        title_text.append(
            f"{action.upper()} ",
            style=self.es_client.style_system.get_semantic_style("primary"),
        )
        title_text.append(
            f"{len(targets)} ",
            style=self.es_client.style_system.get_semantic_style("info"),
        )
        title_text.append(
            "SNAPSHOT(S)",
            style=self.es_client.style_system.get_semantic_style("primary"),
        )

        # Determine panel color based on action
        panel_color = "yellow" if dry_run else "green"

        # Wrap table in a panel
        panel = Panel(
            table,
            title=title_text,
            title_align="center",
            subtitle=f"📦 Repository: {repository_name}",
            subtitle_align="center",
            border_style=panel_color,
            padding=(1, 2),
        )

        self.console.print(panel)

    def _display_snapshot_summary(self, successful, failed, repository_name):
        """Display summary of snapshot creation results."""
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table

        # Create summary content with more visual elements
        content_lines = []

        if successful:
            content_lines.append(
                f"✅ Successfully created {len(successful)} snapshot(s):"
            )
            for target_info in successful:
                content_lines.append(
                    f"  • 📸 {target_info['snapshot_name']} ({target_info['type']}: 🎯 {target_info['name']})"
                )
            content_lines.append("")  # Add spacing

        if failed:
            content_lines.append(f"❌ Failed to create {len(failed)} snapshot(s):")
            for target_info in failed:
                content_lines.append(
                    f"  • 📸 {target_info['snapshot_name']} ({target_info['type']}: 🎯 {target_info['name']})"
                )
            content_lines.append("")  # Add spacing

        # Add repository information
        content_lines.append(f"📦 Repository: {repository_name}")

        summary_text = "\n".join(content_lines)

        # Determine panel styling based on results
        if failed and not successful:
            panel_style = "red"
            title_emoji = "❌"
            title_style = "bold red"
        elif failed and successful:
            panel_style = "yellow"
            title_emoji = "🔶"
            title_style = "bold yellow"
        else:
            panel_style = "green"
            title_emoji = "✅"
            title_style = "bold green"

        panel = Panel(
            summary_text.strip(),
            title=f"{title_emoji} Snapshot Creation Summary",
            title_align="left",
            border_style=panel_style,
            padding=(1, 2),
        )
        self.console.print(panel)

    def _handle_delete_snapshot(self):
        """
        Delete a specific snapshot with confirmation.
        """
        snapshot_name = self.args.snapshot_name

        # Check if elastic_s3snapshot_repo is configured for this cluster
        elastic_s3snapshot_repo = self.location_config.get("elastic_s3snapshot_repo")

        if not elastic_s3snapshot_repo:
            self.es_client.show_message_box(
                "Configuration Error",
                f"No 'elastic_s3snapshot_repo' configured for cluster '{self.args.locations}'.\n"
                f"Please add 'elastic_s3snapshot_repo: \"your-repo-name\"' to the cluster configuration in elastic_servers.yml",
                message_style="bold white",
                panel_style="red",
            )
            return

        # Use repository from args if provided, otherwise use configured default
        repository_name = (
            getattr(self.args, "repository", None) or elastic_s3snapshot_repo
        )

        # First, verify the snapshot exists and get its details
        snapshots = self.es_client.list_snapshots(repository_name)
        target_snapshot = None

        for snapshot in snapshots:
            if snapshot["snapshot"] == snapshot_name:
                target_snapshot = snapshot
                break

        if not target_snapshot:
            self.es_client.show_message_box(
                "Snapshot Not Found",
                f"Snapshot '{snapshot_name}' was not found in repository '{repository_name}'.\n\n"
                f"Use 'escmd.py snapshots list' to see available snapshots.",
                message_style="bold white",
                panel_style="red",
            )
            return

        # Display snapshot information
        from rich.text import Text

        info_text = Text()
        info_text.append("Snapshot to delete:\n\n", style="bold red")
        info_text.append(f"📸 Name: ", style="bold white")
        info_text.append(f"{snapshot_name}\n", style="cyan")
        info_text.append(f"📦 Repository: ", style="bold white")
        info_text.append(f"{repository_name}\n", style="cyan")
        info_text.append(f"📅 Created: ", style="bold white")
        info_text.append(
            f"{target_snapshot.get('start_time', 'Unknown')}\n", style="cyan"
        )
        info_text.append(f"🎯 State: ", style="bold white")

        state = target_snapshot.get("state", "UNKNOWN").upper()
        if state == "SUCCESS":
            info_text.append(f"✅ {state}\n", style="green")
        elif state == "IN_PROGRESS":
            info_text.append(f"⏳ {state}\n", style="yellow")
        elif state == "FAILED":
            info_text.append(f"❌ {state}\n", style="red")
        else:
            info_text.append(f"🔶 {state}\n", style="orange")

        info_text.append(f"📊 Indices: ", style="bold white")
        info_text.append(f"{target_snapshot.get('indices', [])}", style="dim white")

        panel = Panel(
            info_text,
            title="🔶 DELETE SNAPSHOT CONFIRMATION 🔶",
            border_style="red",
            padding=(1, 2),
        )
        self.console.print(panel)

        # Check if force flag is used to skip confirmation
        if not getattr(self.args, "force", False):
            # Prompt for confirmation
            confirmation = (
                input(
                    f"\n🚨 Are you absolutely sure you want to DELETE snapshot '{snapshot_name}'? (yes/no): "
                )
                .strip()
                .lower()
            )

            if confirmation not in ["yes", "y"]:
                self.console.print("\n[yellow]❌ Snapshot deletion cancelled.[/yellow]")
                return

        # Perform the deletion
        self.console.print(
            f"\n[yellow]🗑 Deleting snapshot '{snapshot_name}' from repository '{repository_name}'...[/yellow]"
        )

        result = self.es_client.delete_snapshot(repository_name, snapshot_name)

        if result:
            success_text = f"✅ Successfully deleted snapshot '{snapshot_name}' from repository '{repository_name}'"
            panel = Panel(
                success_text, title="Snapshot Deletion Success", border_style="green"
            )
            self.console.print(panel)
        else:
            error_text = f"❌ Failed to delete snapshot '{snapshot_name}' from repository '{repository_name}'"
            panel = Panel(
                error_text, title="Snapshot Deletion Failed", border_style="red"
            )
            self.console.print(panel)

    def _handle_snapshot_info(self):
        """
        Show comprehensive information about a specific snapshot.
        """
        snapshot_name = self.args.snapshot_name

        # Check if elastic_s3snapshot_repo is configured for this cluster
        elastic_s3snapshot_repo = self.location_config.get("elastic_s3snapshot_repo")

        if not elastic_s3snapshot_repo:
            self.es_client.show_message_box(
                "Configuration Error",
                f"No 'elastic_s3snapshot_repo' configured for cluster '{self.args.locations}'.\n"
                f"Please add 'elastic_s3snapshot_repo: \"your-repo-name\"' to the cluster configuration in elastic_servers.yml",
                message_style="bold white",
                panel_style="red",
            )
            return

        # Use repository from args if provided, otherwise use configured default
        repository_name = (
            getattr(self.args, "repository", None) or elastic_s3snapshot_repo
        )

        # Get comprehensive snapshot information
        snapshot_info = self.es_client.get_snapshot_info(repository_name, snapshot_name)

        if not snapshot_info:
            self.es_client.show_message_box(
                "Snapshot Not Found",
                f"Snapshot '{snapshot_name}' was not found in repository '{repository_name}'.\n\n"
                f"Use 'escmd.py snapshots list' to see available snapshots.",
                message_style="bold white",
                panel_style="red",
            )
            return

        # Handle JSON output format
        output_format = getattr(self.args, "format", "table")
        if output_format == "json":
            import json

            print(json.dumps(snapshot_info, indent=2, default=str))
            return

        # Display comprehensive snapshot information
        self._display_snapshot_info(snapshot_info)

    def _display_snapshot_info(self, info):
        """
        Display comprehensive snapshot information in a single, well-organized panel.
        """
        from rich.text import Text
        from rich.table import Table

        # Create comprehensive info display in a single panel
        info_text = Text()

        # Header
        info_text.append("📸 SNAPSHOT INFORMATION\n\n", style="bold cyan")

        # Basic Information Section
        info_text.append("📋 Basic Details\n", style="bold white underline")
        info_text.append("   🔖  Name: ", style="bold white")
        info_text.append(f"{info['snapshot_name']}\n", style="cyan")
        info_text.append("   📦 Repository: ", style="bold white")
        info_text.append(f"{info['repository_name']}\n", style="cyan")
        info_text.append("   🔑 UUID: ", style="bold white")
        info_text.append(f"{info.get('uuid', 'N/A')}\n", style="dim white")
        info_text.append("   🔖  Version: ", style="bold white")
        info_text.append(f"{info.get('version', 'N/A')}\n", style="dim white")

        # State with appropriate styling
        info_text.append("   🎯 State: ", style="bold white")
        state = info["state"]
        if state == "SUCCESS":
            info_text.append(f"✅ {state}\n\n", style="bold green")
        elif state == "IN_PROGRESS":
            info_text.append(f"⏳ {state}\n\n", style="bold yellow")
        elif state == "FAILED":
            info_text.append(f"❌ {state}\n\n", style="bold red")
        else:
            info_text.append(f"🔶 {state}\n\n", style="bold orange")

        # Timing Section
        info_text.append("🕐 Timing Information\n", style="bold white underline")
        info_text.append("   🚀 Started: ", style="bold white")
        info_text.append(f"{info['start_time_formatted']}\n", style="cyan")
        info_text.append("   🏁 Ended: ", style="bold white")
        info_text.append(f"{info['end_time_formatted']}\n", style="cyan")
        info_text.append("   ⏳ Duration: ", style="bold white")
        info_text.append(f"{info['duration']}\n\n", style="cyan")

        # Data Section
        info_text.append("📊 Data Summary\n", style="bold white underline")
        info_text.append("   📋 Indices: ", style="bold white")
        info_text.append(f"{info['indices_count']}\n", style="cyan")
        info_text.append("   🌊 Data Streams: ", style="bold white")
        info_text.append(f"{info['data_streams_count']}\n", style="cyan")
        info_text.append("   🌐 Global State: ", style="bold white")
        global_state = (
            "✅ Included" if info["include_global_state"] else "❌ Not Included"
        )
        global_color = "green" if info["include_global_state"] else "red"
        info_text.append(f"{global_state}\n\n", style=global_color)

        # Shard Statistics Section
        info_text.append("🔧 Shard Statistics\n", style="bold white underline")
        info_text.append("   📊 Total: ", style="bold white")
        info_text.append(f"{info['total_shards']}\n", style="cyan")
        info_text.append("   ✅ Successful: ", style="bold white")
        info_text.append(f"{info['successful_shards']}\n", style="green")
        info_text.append("   ❌ Failed: ", style="bold white")
        failed_color = "red" if info["failed_shards"] > 0 else "green"
        info_text.append(f"{info['failed_shards']}\n\n", style=failed_color)

        # Repository Section
        info_text.append("🏛️  Repository Details\n", style="bold white underline")
        info_text.append("   📦 Name: ", style="bold white")
        info_text.append(f"{info['repository_name']}\n", style="cyan")
        info_text.append("   🔖  Type: ", style="bold white")
        info_text.append(f"{info['repository_type']}\n", style="cyan")

        # Repository Settings
        if info.get("repository_settings"):
            info_text.append("   🔩  Key Settings:\n", style="bold white")
            settings = info["repository_settings"]
            for key in [
                "bucket",
                "base_path",
                "region",
                "endpoint",
                "compress",
                "chunk_size",
            ]:
                if key in settings:
                    info_text.append(f"      • {key}: ", style="dim white")
                    info_text.append(f"{settings[key]}\n", style="cyan")

        # Add empty line before indices section
        if info["indices"] or info["data_streams"]:
            info_text.append("\n", style="white")

        # Indices and Data Streams Section (integrated into main panel)
        if info["indices"] or info["data_streams"]:
            info_text.append(
                "📋 Included Indices & Data Streams\n", style="bold white underline"
            )

            # Display indices
            if info["indices"]:
                for index in info["indices"]:
                    info_text.append("   📋 Index: ", style="bold white")
                    info_text.append(f"{index}\n", style="cyan")

            # Display data streams
            if info["data_streams"]:
                for ds in info["data_streams"]:
                    info_text.append("   🌊 Data Stream: ", style="bold white")
                    info_text.append(f"{ds}\n", style="cyan")

        # Failures Section (integrated into main panel if present)
        if info["failures"]:
            info_text.append("\n❌ Snapshot Failures\n", style="bold red underline")
            for failure in info["failures"]:
                info_text.append("   📋 Index: ", style="bold white")
                info_text.append(f"{failure.get('index', '-')}\n", style="cyan")
                info_text.append("   🔧 Shard: ", style="bold white")
                info_text.append(f"{failure.get('shard_id', '-')}\n", style="yellow")
                info_text.append("   ❌ Status: ", style="bold white")
                info_text.append(f"{failure.get('status', '-')}\n", style="red")
                info_text.append("   📝 Reason: ", style="bold white")
                info_text.append(f"{failure.get('reason', '-')}\n\n", style="dim white")

        # Create the main panel
        main_panel = Panel(
            info_text,
            title="[bold white]📸 Snapshot Information[/bold white]",
            title_align="center",
            border_style="bright_blue",
            padding=(1, 3),
            expand=True,
        )

        self.console.print(main_panel)

    def _handle_list_restored(self):
        """Handle the list-restored command to show all restored snapshots/indices."""
        try:
            # Get the index name from command line arg or use default from config
            index_name = getattr(self.args, "index", None)

            # Create snapshot commands instance
            snapshot_commands = SnapshotCommands(
                self.es_client,
                theme_manager=getattr(self.es_client, "theme_manager", None),
            )
            restored_records = snapshot_commands.list_restored_snapshots(
                index_name=index_name
            )

            if not restored_records:
                # Create styled warning message
                warning_text = Text()
                warning_text.append(
                    "🔶  ",
                    style=self.es_client.style_system.get_semantic_style("warning"),
                )
                warning_text.append(
                    "No restored snapshots/indices found in the tracking system.",
                    style=self.es_client.style_system.get_semantic_style("secondary"),
                )

                self.console.print(
                    Panel(
                        warning_text,
                        title=self.es_client.style_system.create_semantic_text(
                            "📋 Restored Snapshots", "warning"
                        ),
                        title_align="center",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "warning"
                        ),
                        padding=(1, 2),
                    )
                )
                return

            # Create a Rich table for displaying the results with theme styling
            table = Table(
                show_header=True,
                header_style=self.es_client.style_system._get_style(
                    "table_styles", "header_style", "bold white"
                ),
                border_style=self.es_client.style_system._get_style(
                    "table_styles", "border_style", "white"
                ),
                title="📋 Restored Snapshots/Indices",
                title_style=self.es_client.style_system.get_semantic_style("success"),
                expand=True,
                box=self.es_client.style_system.get_table_box(),
            )

            # Dynamically add columns based on the first record's keys with theme styling
            # Exclude the _id field from display unless it's the only field
            first_record = restored_records[0]
            display_fields = [key for key in first_record.keys() if key != "_id"]

            if not display_fields:  # If only _id exists, show it
                display_fields = ["_id"]

            # Add columns with appropriate styling and emojis
            for field in display_fields:
                column_title = field.replace("_", " ").title()

                # Add appropriate emoji and styling based on field name
                if "index" in field.lower() or "name" in field.lower():
                    column_title = f"📄 {column_title}"
                    style = self.es_client.style_system.get_semantic_style("info")
                elif "user" in field.lower():
                    column_title = f"👤 {column_title}"
                    style = self.es_client.style_system.get_semantic_style("secondary")
                elif (
                    "date" in field.lower()
                    or "time" in field.lower()
                    or "updated" in field.lower()
                ):
                    column_title = f"📅 {column_title}"
                    style = self.es_client.style_system.get_semantic_style("warning")
                elif "status" in field.lower():
                    column_title = f"🎯 {column_title}"
                    style = self.es_client.style_system.get_semantic_style("success")
                else:
                    style = self.es_client.style_system.get_semantic_style("primary")

                # Set column width and justification based on content type
                if "status" in field.lower():
                    table.add_column(
                        column_title,
                        style=style,
                        justify="center",
                        width=12,
                        no_wrap=True,
                    )
                elif "date" in field.lower() or "time" in field.lower():
                    table.add_column(column_title, style=style, width=18, no_wrap=True)
                else:
                    table.add_column(
                        column_title, style=style, no_wrap=True, overflow="ellipsis"
                    )

            # Add rows to the table with proper styling
            for record in restored_records:
                row_data = []
                for field in display_fields:
                    value = record.get(field, "N/A")
                    # Convert to string and handle None values
                    if value is not None:
                        # Add special styling for status field
                        if (
                            "status" in field.lower()
                            and str(value).lower() == "restored"
                        ):
                            # Rich markup for green checkmark with status
                            row_data.append(f"✅ {str(value)}")
                        else:
                            row_data.append(str(value))
                    else:
                        row_data.append("N/A")
                table.add_row(*row_data)

            # Display the table directly (no panel needed since table has title)
            self.console.print(table)

            # Show count with theme styling
            count_text = Text()
            count_text.append(
                "📊 Total restored records found: ",
                style=self.es_client.style_system.get_semantic_style("info"),
            )
            count_text.append(
                str(len(restored_records)),
                style=self.es_client.style_system.get_semantic_style("success"),
            )
            self.console.print(f"\n{count_text}")

        except Exception as e:
            error_msg = f"Failed to retrieve restored snapshots: {str(e)}"
            self.es_client.show_message_box(
                "Error",
                error_msg,
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )

    def _handle_clear_staged(self):
        """Handle the clear-staged command to remove all pending restores in INIT status."""
        try:
            # Get the index name from command line arg or use default from config
            index_name = getattr(self.args, "index", None)

            # Create snapshot commands instance
            snapshot_commands = SnapshotCommands(
                self.es_client,
                theme_manager=getattr(self.es_client, "theme_manager", None),
            )

            # Check if force flag is set
            force = getattr(self.args, "force", False)

            # First, get count of staged items to clear
            try:
                staged_count = snapshot_commands.get_staged_count(index_name=index_name)

                if staged_count == 0:
                    # Create styled info message
                    info_text = Text()
                    info_text.append(
                        "ℹ️  ",
                        style=self.es_client.style_system.get_semantic_style("info"),
                    )
                    info_text.append(
                        "No staged snapshots found to clear.",
                        style=self.es_client.style_system.get_semantic_style(
                            "secondary"
                        ),
                    )

                    self.console.print(
                        Panel(
                            info_text,
                            title=self.es_client.style_system.create_semantic_text(
                                "🧹 Clear Staged Snapshots", "info"
                            ),
                            title_align="center",
                            border_style=self.es_client.style_system.get_semantic_style(
                                "info"
                            ),
                            padding=(1, 2),
                        )
                    )
                    return

                # Show confirmation unless force is used
                if not force:
                    warning_text = Text()
                    warning_text.append(
                        "🔶  ",
                        style=self.es_client.style_system.get_semantic_style("warning"),
                    )
                    warning_text.append(
                        f"About to clear {staged_count} staged snapshot(s) in INIT status.\n",
                        style=self.es_client.style_system.get_semantic_style(
                            "secondary"
                        ),
                    )
                    warning_text.append(
                        "This action cannot be undone.",
                        style=self.es_client.style_system.get_semantic_style("warning"),
                    )

                    self.console.print(
                        Panel(
                            warning_text,
                            title=self.es_client.style_system.create_semantic_text(
                                "🧹 Clear Staged Snapshots", "warning"
                            ),
                            title_align="center",
                            border_style=self.es_client.style_system.get_semantic_style(
                                "warning"
                            ),
                            padding=(1, 2),
                        )
                    )

                    # Prompt for confirmation outside the box
                    self.console.print()  # Add blank line
                    try:
                        confirmation = input("Continue? [y/N]: ").strip().lower()
                        if confirmation not in ["y", "yes"]:
                            self.console.print("Operation cancelled.")
                            return
                    except KeyboardInterrupt:
                        self.console.print("\nOperation cancelled.")
                        return

                # Perform the clear operation
                cleared_count = snapshot_commands.clear_staged_snapshots(
                    index_name=index_name
                )

                # Show success message
                success_text = Text()
                success_text.append(
                    "✅ ",
                    style=self.es_client.style_system.get_semantic_style("success"),
                )
                success_text.append(
                    f"Successfully cleared {cleared_count} staged snapshot(s).",
                    style=self.es_client.style_system.get_semantic_style("secondary"),
                )

                self.console.print(
                    Panel(
                        success_text,
                        title=self.es_client.style_system.create_semantic_text(
                            "🧹 Clear Staged Snapshots", "success"
                        ),
                        title_align="center",
                        border_style=self.es_client.style_system.get_semantic_style(
                            "success"
                        ),
                        padding=(1, 2),
                    )
                )

            except Exception as e:
                error_msg = f"Failed to clear staged snapshots: {str(e)}"
                self.es_client.show_message_box(
                    "Error",
                    error_msg,
                    message_style=self.es_client.style_system.get_semantic_style(
                        "secondary"
                    ),
                    panel_style=self.es_client.style_system.get_semantic_style("error"),
                )

        except Exception as e:
            error_msg = f"Failed to handle clear-staged command: {str(e)}"
            self.es_client.show_message_box(
                "Error",
                error_msg,
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )

    def _handle_list_repositories(self):
        """
        Handle listing all configured snapshot repositories.
        """
        try:
            # Get repositories using the snapshot commands
            repositories_data = self.es_client.get_repositories()

            if "error" in repositories_data:
                self.es_client.show_message_box(
                    "Error",
                    repositories_data["error"],
                    message_style=self.es_client.style_system.get_semantic_style(
                        "secondary"
                    ),
                    panel_style=self.es_client.style_system.get_semantic_style("error"),
                )
                return

            # Check output format
            output_format = getattr(self.args, "format", "table")

            if output_format == "json":
                self._display_repositories_json(repositories_data)
            else:
                # Use enhanced table format with statistics
                self.es_client.print_enhanced_repositories_table(repositories_data)

        except Exception as e:
            error_msg = f"Failed to retrieve repositories: {str(e)}"
            self.es_client.show_message_box(
                "Error",
                error_msg,
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )

    def _handle_verify_repository(self):
        """
        Handle verifying a snapshot repository.
        """
        try:
            repository_name = self.args.repository_name

            # Show starting message
            self.console.print(
                f"[bold blue]Verifying repository '[cyan]{repository_name}[/cyan]'...[/bold blue]"
            )

            # Verify repository using the snapshot commands
            verification_result = self.es_client.verify_repository(repository_name)

            if "error" in verification_result:
                # Check output format before displaying error
                output_format = getattr(self.args, "format", "table")

                # Try to parse and display the error in a user-friendly format
                if self._try_display_verification_error(
                    verification_result["error"], repository_name, output_format
                ):
                    return

                # Fallback to original error display if parsing fails
                self.es_client.show_message_box(
                    "Error",
                    verification_result["error"],
                    message_style=self.es_client.style_system.get_semantic_style(
                        "secondary"
                    ),
                    panel_style=self.es_client.style_system.get_semantic_style("error"),
                )
                return

            # Check output format
            output_format = getattr(self.args, "format", "table")

            if output_format == "json":
                self._display_verify_result_json(verification_result)
            else:
                self._display_verify_result_table(verification_result, repository_name)

        except Exception as e:
            error_msg = (
                f"Failed to verify repository '{self.args.repository_name}': {str(e)}"
            )
            self.es_client.show_message_box(
                "Error",
                error_msg,
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )

    def _handle_create_repository(self):
        """
        Handle creating a new snapshot repository.
        """
        try:
            repository_name = self.args.name
            repo_type = self.args.type

            # Validate required arguments based on repository type
            settings = {}

            if repo_type == "fs":
                if not self.args.location:
                    self.es_client.show_message_box(
                        "Error",
                        "Location is required for filesystem repositories",
                        message_style=self.es_client.style_system.get_semantic_style(
                            "secondary"
                        ),
                        panel_style=self.es_client.style_system.get_semantic_style(
                            "error"
                        ),
                    )
                    return
                settings["location"] = self.args.location

            elif repo_type in ["s3", "gcs", "azure"]:
                if not self.args.bucket:
                    self.es_client.show_message_box(
                        "Error",
                        f"Bucket is required for {repo_type} repositories",
                        message_style=self.es_client.style_system.get_semantic_style(
                            "secondary"
                        ),
                        panel_style=self.es_client.style_system.get_semantic_style(
                            "error"
                        ),
                    )
                    return
                settings["bucket"] = self.args.bucket

            # Add optional settings
            if hasattr(self.args, "base_path") and self.args.base_path:
                settings["base_path"] = self.args.base_path

            if hasattr(self.args, "region") and self.args.region:
                settings["region"] = self.args.region

            if hasattr(self.args, "storage_class") and self.args.storage_class:
                settings["storage_class"] = self.args.storage_class

            if (
                hasattr(self.args, "server_side_encryption")
                and self.args.server_side_encryption
            ):
                settings["server_side_encryption"] = True

            if hasattr(self.args, "compress"):
                settings["compress"] = self.args.compress

            if hasattr(self.args, "readonly") and self.args.readonly:
                settings["readonly"] = True

            if hasattr(self.args, "chunk_size") and self.args.chunk_size:
                settings["chunk_size"] = self.args.chunk_size

            if (
                hasattr(self.args, "max_restore_bytes_per_sec")
                and self.args.max_restore_bytes_per_sec
            ):
                settings["max_restore_bytes_per_sec"] = (
                    self.args.max_restore_bytes_per_sec
                )

            if (
                hasattr(self.args, "max_snapshot_bytes_per_sec")
                and self.args.max_snapshot_bytes_per_sec
            ):
                settings["max_snapshot_bytes_per_sec"] = (
                    self.args.max_snapshot_bytes_per_sec
                )

            if hasattr(self.args, "verify"):
                settings["verify"] = self.args.verify

            # Show dry-run information
            if hasattr(self.args, "dry_run") and self.args.dry_run:
                self._show_repository_dry_run(repository_name, repo_type, settings)
                return

            # Show confirmation unless force is used
            if not (hasattr(self.args, "force") and self.args.force):
                if not self._confirm_repository_creation(
                    repository_name, repo_type, settings
                ):
                    self.es_client.show_message_box(
                        "Info",
                        "Repository creation cancelled",
                        message_style=self.es_client.style_system.get_semantic_style(
                            "info"
                        ),
                        panel_style=self.es_client.style_system.get_semantic_style(
                            "info"
                        ),
                    )
                    return

            # Create the repository
            result = self.es_client.snapshot_commands.create_repository(
                repository_name, repo_type, settings
            )

            if "error" in result:
                self.es_client.show_message_box(
                    "Error",
                    result["error"],
                    message_style=self.es_client.style_system.get_semantic_style(
                        "secondary"
                    ),
                    panel_style=self.es_client.style_system.get_semantic_style("error"),
                )
            else:
                self.es_client.show_message_box(
                    "Success",
                    f"Repository '{repository_name}' created successfully",
                    message_style=self.es_client.style_system.get_semantic_style(
                        "success"
                    ),
                    panel_style=self.es_client.style_system.get_semantic_style(
                        "success"
                    ),
                )

        except Exception as e:
            error_msg = f"Failed to create repository: {str(e)}"
            self.es_client.show_message_box(
                "Error",
                error_msg,
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("error"),
            )

    def _show_repository_dry_run(
        self, repository_name: str, repo_type: str, settings: dict
    ):
        """Show what would be created without actually creating the repository."""
        console = Console()

        # Create dry-run display
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text

        config_table = Table(show_header=False, box=None, padding=(0, 2))
        config_table.add_column("Setting", style="cyan", no_wrap=True)
        config_table.add_column("Value", style="white")

        config_table.add_row("Repository Name:", repository_name)
        config_table.add_row("Type:", repo_type.upper())

        for key, value in settings.items():
            display_key = key.replace("_", " ").title() + ":"
            config_table.add_row(display_key, str(value))

        panel = Panel(
            config_table,
            title="🔍 Repository Configuration (Dry Run)",
            border_style="blue",
            padding=(1, 2),
        )

        console.print(panel)
        console.print(
            "\n[dim]Use --force to create this repository or remove --dry-run to be prompted for confirmation.[/dim]"
        )

    def _confirm_repository_creation(
        self, repository_name: str, repo_type: str, settings: dict
    ) -> bool:
        """Prompt user for confirmation before creating repository."""
        console = Console()

        # Show what will be created
        self._show_repository_dry_run(repository_name, repo_type, settings)

        # Prompt for confirmation
        from rich.prompt import Confirm

        return Confirm.ask("\n[yellow]Create this repository?[/yellow]")

    def _display_repositories_table(self, repositories_data):
        """
        Display repositories in table format.

        Args:
            repositories_data: Dictionary of repository information
        """
        if not repositories_data:
            self.es_client.show_message_box(
                "Info",
                "No snapshot repositories are configured.",
                message_style=self.es_client.style_system.get_semantic_style(
                    "secondary"
                ),
                panel_style=self.es_client.style_system.get_semantic_style("info"),
            )
            return

        from rich.table import Table
        from rich.panel import Panel

        # Create repositories table
        table = Table(
            title="📦 Snapshot Repositories",
            show_header=True,
            header_style=self.es_client.style_system.get_semantic_style("header"),
            border_style=self.es_client.style_system.get_semantic_style("primary"),
            title_style=self.es_client.style_system.get_semantic_style("title"),
        )

        # Add columns
        table.add_column(
            "Repository Name",
            style=self.es_client.style_system.get_semantic_style("primary"),
            min_width=15,
        )
        table.add_column(
            "Type",
            style=self.es_client.style_system.get_semantic_style("secondary"),
            min_width=8,
        )
        table.add_column(
            "Location/Bucket",
            style=self.es_client.style_system.get_semantic_style("info"),
            min_width=20,
        )
        table.add_column(
            "Settings",
            style=self.es_client.style_system.get_semantic_style("muted"),
            min_width=30,
        )

        # Add rows for each repository
        for repo_name, repo_info in repositories_data.items():
            repo_type = repo_info.get("type", "unknown")
            settings = repo_info.get("settings", {})

            # Extract location information based on repository type
            location = self._extract_repository_location(repo_type, settings)

            # Format settings for display (exclude sensitive information)
            settings_display = self._format_repository_settings(settings)

            table.add_row(repo_name, repo_type.upper(), location, settings_display)

        # Display the table
        self.console.print(table)

        # Show summary
        repo_count = len(repositories_data)
        summary_text = f"Found {repo_count} configured repositor{'ies' if repo_count != 1 else 'y'}"

        summary_panel = Panel.fit(
            summary_text,
            title="Summary",
            border_style=self.es_client.style_system.get_semantic_style("info"),
        )
        self.console.print(summary_panel)

    def _display_repositories_json(self, repositories_data):
        """
        Display repositories in JSON format.

        Args:
            repositories_data: Dictionary of repository information
        """
        import json

        self.console.print(json.dumps(repositories_data, indent=2))

    def _extract_repository_location(self, repo_type, settings):
        """
        Extract location information from repository settings based on type.

        Args:
            repo_type: Type of repository (s3, fs, etc.)
            settings: Repository settings dictionary

        Returns:
            str: Human-readable location string
        """
        if repo_type == "s3":
            bucket = settings.get("bucket", "N/A")
            base_path = settings.get("base_path", "")
            if base_path:
                return f"{bucket}/{base_path}"
            return bucket
        elif repo_type == "fs":
            return settings.get("location", "N/A")
        elif repo_type == "azure":
            container = settings.get("container", "N/A")
            account = settings.get("account", "N/A")
            return f"{account}/{container}"
        elif repo_type == "gcs":
            bucket = settings.get("bucket", "N/A")
            base_path = settings.get("base_path", "")
            if base_path:
                return f"{bucket}/{base_path}"
            return bucket
        elif repo_type == "hdfs":
            path = settings.get("path", "N/A")
            return path
        else:
            # For unknown types, try to find a reasonable location field
            location_fields = ["location", "bucket", "container", "path", "base_path"]
            for field in location_fields:
                if field in settings:
                    return settings[field]
            return "N/A"

    def _format_repository_settings(self, settings):
        """
        Format repository settings for display, hiding sensitive information.

        Args:
            settings: Repository settings dictionary

        Returns:
            str: Formatted settings string
        """
        # Fields to exclude from display (sensitive information)
        sensitive_fields = {
            "access_key",
            "secret_key",
            "client_secret",
            "private_key_id",
            "password",
            "token",
            "credential",
            "key",
        }

        # Fields to include in display with their display names
        display_fields = {
            "region": "Region",
            "endpoint": "Endpoint",
            "compress": "Compress",
            "chunk_size": "Chunk Size",
            "max_restore_bytes_per_sec": "Max Restore Rate",
            "max_snapshot_bytes_per_sec": "Max Snapshot Rate",
            "readonly": "Read Only",
            "server_side_encryption": "SSE",
            "storage_class": "Storage Class",
        }

        display_parts = []
        for key, value in settings.items():
            # Skip sensitive fields
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                continue

            # Use display name if available, otherwise use the key
            display_name = display_fields.get(key, key.replace("_", " ").title())

            # Format the value
            if isinstance(value, bool):
                value_str = "Yes" if value else "No"
            elif isinstance(value, (int, float)) and key.endswith("_per_sec"):
                # Format byte rates
                value_str = self._format_bytes(value) + "/sec"
            elif isinstance(value, (int, float)) and "size" in key.lower():
                # Format sizes
                value_str = self._format_bytes(value)
            else:
                value_str = str(value)

            display_parts.append(f"{display_name}: {value_str}")

        return ", ".join(display_parts) if display_parts else "Default settings"

    def _format_bytes(self, size_bytes):
        """
        Format bytes into human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            str: Human-readable size string
        """
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
        import math

        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def _display_verify_result_table(self, verification_result, repository_name):
        """
        Display repository verification results in table format.

        Args:
            verification_result: The verification result from Elasticsearch
            repository_name: Name of the repository being verified
        """
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from rich.align import Align

        # Check if verification was successful
        nodes = verification_result.get("nodes", {})

        if not nodes:
            self.console.print(
                Panel(
                    "[red]No verification results found[/red]",
                    title=f"Repository Verification: {repository_name}",
                    border_style="red",
                )
            )
            return

        # Count successful verifications
        successful_nodes = 0
        total_nodes = len(nodes)

        # Calculate node type statistics
        master_nodes = 0
        data_nodes = 0
        other_nodes = 0

        # Sort nodes by name alphabetically
        sorted_nodes = sorted(
            nodes.items(), key=lambda item: item[1].get("name", "Unknown")
        )

        # Analyze node types based on naming conventions
        for node_id, node_info in sorted_nodes:
            node_name = node_info.get("name", "Unknown")
            successful_nodes += 1

            if "master" in node_name.lower():
                master_nodes += 1
            elif "ess" in node_name.lower() or "data" in node_name.lower():
                data_nodes += 1
            else:
                other_nodes += 1

        # Determine status and styling
        if successful_nodes == total_nodes:
            status_text = "✅ Good - All Nodes Verified"
            title_style = "bold cyan"
            border_style = "green"
        else:
            status_text = "🔶  Warning - Partial Verification"
            title_style = "bold yellow"
            border_style = "yellow"

        # Create colorized subtitle with statistics
        subtitle_rich = Text()
        subtitle_rich.append("Total: ", style="default")
        subtitle_rich.append(str(total_nodes), style="cyan")
        subtitle_rich.append(" | Verified: ", style="default")
        subtitle_rich.append(str(successful_nodes), style="green")

        if master_nodes > 0:
            subtitle_rich.append(" | Master: ", style="default")
            subtitle_rich.append(str(master_nodes), style="bright_magenta")

        if data_nodes > 0:
            subtitle_rich.append(" | Data: ", style="default")
            subtitle_rich.append(str(data_nodes), style="bright_blue")

        if other_nodes > 0:
            subtitle_rich.append(" | Other: ", style="default")
            subtitle_rich.append(str(other_nodes), style="dim")

        # Create title panel matching shards style
        title_panel = Panel(
            Text(
                f"📦 Repository Verification Overview \n {status_text}",
                style=title_style,
                justify="center",
            ),
            subtitle=subtitle_rich,
            border_style=border_style,
            padding=(1, 2),
        )

        # Create verification results table
        table = Table(show_header=True, header_style="bold blue", expand=True)
        table.add_column("Node Name", style="cyan", no_wrap=True, min_width=30)
        table.add_column("Node ID", style="dim", no_wrap=True, min_width=28)
        table.add_column("Status", justify="center", min_width=15)

        # Add rows for each node (now sorted)
        for node_id, node_info in sorted_nodes:
            node_name = node_info.get("name", "Unknown")
            # All nodes returned in verification result are successful
            status = "[green]✓ Verified[/green]"
            table.add_row(node_name, node_id, status)

        # Display results with title panel
        self.console.print()
        self.console.print(title_panel)
        self.console.print()
        self.console.print(
            Panel(
                Align.center(table),
                title=f"📋 Repository '{repository_name}' Node Verification",
                border_style=border_style,
                padding=(1, 2),
            )
        )

    def _display_verify_result_json(self, verification_result):
        """
        Display repository verification results in JSON format.

        Args:
            verification_result: The verification result from Elasticsearch
        """
        import json

        # Pretty print the verification result
        formatted_result = json.dumps(verification_result, indent=2, sort_keys=True)
        self.console.print(formatted_result)

    def _try_display_verification_error(
        self, error_message, repository_name, output_format="table"
    ):
        """
        Try to parse and display repository verification errors in a user-friendly format.

        Args:
            error_message: The raw error message from Elasticsearch
            repository_name: Name of the repository being verified
            output_format: The output format (table or json)

        Returns:
            bool: True if error was successfully parsed and displayed, False otherwise
        """
        try:
            import re
            from rich.table import Table
            from rich.panel import Panel
            from rich.text import Text
            from rich.align import Align

            # Check if this is a TransportError with node failures
            if (
                "TransportError" not in error_message
                or "repository_verification_exception" not in error_message
            ):
                return False

            # Parse node failures from the error message
            node_failures = self._parse_node_failures(error_message)

            if not node_failures:
                return False

            # Display the parsed failures
            if output_format == "json":
                self._display_verification_failures_json(node_failures, repository_name)
            else:
                self._display_verification_failures_table(
                    node_failures, repository_name, error_message
                )
            return True

        except Exception:
            # If parsing fails, return False to use fallback display
            return False

    def _parse_node_failures(self, error_message):
        """
        Parse individual node failures from the repository verification error.

        Args:
            error_message: The raw error message from Elasticsearch

        Returns:
            list: List of dictionaries containing node failure information
        """
        import re

        node_failures = []

        # Extract the TransportError content
        transport_match = re.search(
            r"TransportError\([^,]+,\s*[^,]+,\s*'(.*)'\)", error_message, re.DOTALL
        )
        if not transport_match:
            return node_failures

        error_content = transport_match.group(1)

        # Extract repository name and failures content
        repo_match = re.search(r"\[([^\]]+)\]\s*\[\[(.*)\]\]", error_content, re.DOTALL)
        if not repo_match:
            return node_failures

        failures_content = repo_match.group(2)

        # Split by node failure entries more robustly
        # Each entry starts with "],["  except the first one
        parts = re.split(r"\],\s*\[", failures_content)

        for i, part in enumerate(parts):
            # Clean up the part
            if i == 0:
                # First part, remove leading '[' if present
                if part.startswith("["):
                    part = part[1:]
            if i == len(parts) - 1:
                # Last part, remove trailing ']' if present
                if part.endswith("]"):
                    part = part[:-1]

            # Parse node_id and error text from each part
            # Format should be: node_id, 'error_text'
            comma_pos = part.find(", \\'")

            if comma_pos > 0:
                node_id = part[:comma_pos].strip()
                error_start = comma_pos + 4  # Skip ", \'"

                # Find the end of the error text (last single quote before any trailing characters)
                error_text = ""
                quote_pos = len(part) - 1

                # Work backwards to find the closing quote
                while quote_pos > error_start:
                    if part[quote_pos : quote_pos + 2] == "\\'":
                        error_text = part[error_start:quote_pos]
                        break
                    quote_pos -= 1

                if error_text and node_id:
                    node_info = self._extract_node_info(error_text)
                    node_info["node_id"] = node_id
                    node_failures.append(node_info)
        return node_failures

    def _extract_node_info(self, failure_text):
        """
        Extract detailed information from a single node's failure message.

        Args:
            failure_text: The failure text for a single node

        Returns:
            dict: Extracted node information
        """
        import re

        info = {
            "node_name": "Unknown",
            "ip_address": "Unknown",
            "availability_zone": "Unknown",
            "error_type": "Unknown",
            "error_summary": "Unknown error",
        }

        # Extract node name (like aex10-c01-ess86-1)
        # Look for patterns like [aex10-c01-ess86-1] in the text
        node_name_match = re.search(r"\[([^{}\[\]]*-ess\d+-\d+)\]", failure_text)
        if not node_name_match:
            # Try alternate pattern without brackets
            node_name_match = re.search(r"([^{}\[\]]*-ess\d+-\d+)", failure_text)

        if node_name_match:
            info["node_name"] = node_name_match.group(1)

        # Extract IP address
        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", failure_text)
        if ip_match:
            info["ip_address"] = ip_match.group(1)

        # Extract availability zone
        az_match = re.search(r"availability_zone=([^,\}]+)", failure_text)
        if az_match:
            info["availability_zone"] = az_match.group(1)

        # Determine error type and summary
        if "amazon_s3_exception" in failure_text:
            info["error_type"] = "S3 Access Denied"
            if "s3:PutObject" in failure_text and "AccessDenied" in failure_text:
                info["error_summary"] = "No permission to write to S3 bucket"
            else:
                info["error_summary"] = "S3 access error"
        elif "IOException" in failure_text:
            info["error_type"] = "IO Exception"
            info["error_summary"] = "File system access error"
        elif "RepositoryVerificationException" in failure_text:
            info["error_type"] = "Repository Access"
            info["error_summary"] = "Repository not accessible from node"

        return info

    def _display_verification_failures_table(
        self, node_failures, repository_name, original_error
    ):
        """
        Display repository verification failures in a formatted table.

        Args:
            node_failures: List of node failure information
            repository_name: Name of the repository
            original_error: The original error message for reference
        """
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from rich.align import Align

        # Count failures by type
        error_types = {}
        availability_zones = {}

        for failure in node_failures:
            error_type = failure.get("error_type", "Unknown")
            az = failure.get("availability_zone", "Unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
            availability_zones[az] = availability_zones.get(az, 0) + 1

        # Create summary text
        total_failures = len(node_failures)
        main_error_type = (
            max(error_types.keys(), key=lambda k: error_types[k])
            if error_types
            else "Unknown"
        )

        # Create title panel
        title_text = Text()
        title_text.append("🚫 Repository Verification Failed\n", style="bold red")
        title_text.append(f"Repository: ", style="default")
        title_text.append(f"{repository_name}", style="cyan")
        title_text.append(f" | Failed Nodes: ", style="default")
        title_text.append(f"{total_failures}", style="red")
        title_text.append(f" | Primary Issue: ", style="default")
        title_text.append(f"{main_error_type}", style="yellow")

        # Create subtitle with zone breakdown
        subtitle_text = Text()
        subtitle_text.append("Affected Zones: ", style="default")
        zone_parts = []
        for zone, count in sorted(availability_zones.items()):
            zone_parts.append(f"{zone} ({count})")
        subtitle_text.append(" | ".join(zone_parts), style="dim")

        title_panel = Panel(
            Align.center(title_text),
            subtitle=subtitle_text,
            border_style="red",
            padding=(1, 2),
        )

        # Create failures table
        table = Table(show_header=True, header_style="bold red", expand=True)
        table.add_column("Node Name", style="cyan", no_wrap=True, min_width=20)
        table.add_column("IP Address", style="dim", no_wrap=True, min_width=15)
        table.add_column("Zone", style="blue", no_wrap=True, min_width=12)
        table.add_column("Error Type", style="yellow", no_wrap=True, min_width=15)
        table.add_column("Issue Summary", style="default", min_width=25)

        # Sort failures by node name for consistent display
        sorted_failures = sorted(node_failures, key=lambda x: x.get("node_name", ""))

        for failure in sorted_failures:
            node_name = failure.get("node_name", "Unknown")
            ip_address = failure.get("ip_address", "Unknown")
            zone = failure.get("availability_zone", "Unknown")
            error_type = failure.get("error_type", "Unknown")
            error_summary = failure.get("error_summary", "Unknown error")

            table.add_row(
                f"[red]✗[/red] {node_name}",
                ip_address,
                zone,
                f"[yellow]{error_type}[/yellow]",
                error_summary,
            )

        # Display results
        self.console.print()
        self.console.print(title_panel)
        self.console.print()
        self.console.print(
            Panel(
                Align.center(table),
                title=f"📋 Node Verification Failures for '{repository_name}'",
                border_style="red",
                padding=(1, 2),
            )
        )

    def _display_verification_failures_json(self, node_failures, repository_name):
        """
        Display repository verification failures in JSON format.

        Args:
            node_failures: List of node failure information
            repository_name: Name of the repository
        """
        import json

        # Create structured output for JSON
        output = {
            "repository": repository_name,
            "verification_status": "failed",
            "total_failures": len(node_failures),
            "failures": [],
        }

        # Count failures by type and zone for summary
        error_types = {}
        availability_zones = {}

        for failure in node_failures:
            error_type = failure.get("error_type", "Unknown")
            az = failure.get("availability_zone", "Unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
            availability_zones[az] = availability_zones.get(az, 0) + 1

            # Add to failures list
            output["failures"].append(
                {
                    "node_id": failure.get("node_id", "Unknown"),
                    "node_name": failure.get("node_name", "Unknown"),
                    "ip_address": failure.get("ip_address", "Unknown"),
                    "availability_zone": failure.get("availability_zone", "Unknown"),
                    "error_type": failure.get("error_type", "Unknown"),
                    "error_summary": failure.get("error_summary", "Unknown error"),
                }
            )

        # Add summary information
        output["summary"] = {
            "primary_error_type": max(error_types.keys(), key=lambda k: error_types[k])
            if error_types
            else "Unknown",
            "error_type_counts": error_types,
            "affected_zones": availability_zones,
        }

        # Pretty print the JSON output
        formatted_output = json.dumps(output, indent=2, sort_keys=True)
        self.console.print(formatted_output)

        # Show a helpful summary message
        main_error_type = output["summary"]["primary_error_type"]
        if main_error_type == "S3 Access Denied":
            self.console.print()
            self.console.print(
                Panel(
                    "[yellow]💡 Resolution Suggestion:[/yellow]\n\n"
                    "This appears to be an S3 permissions issue. The user/role specified in the repository "
                    "configuration lacks the necessary permissions to write to the S3 bucket.\n\n"
                    "[bold]Recommended Actions:[/bold]\n"
                    "• Check IAM permissions for the user: [cyan]gitrpm_repo_user[/cyan]\n"
                    "• Ensure the user has [cyan]s3:PutObject[/cyan] permission on the bucket\n"
                    "• Verify the bucket policy allows access from these nodes\n"
                    "• Check if bucket path/prefix restrictions are correctly configured",
                    title="💡 Troubleshooting Tips",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )
