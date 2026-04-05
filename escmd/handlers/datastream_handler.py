"""
Datastream-related command handlers for escmd.

This module contains handlers for datastream operations and management commands.
"""

import json
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .base_handler import BaseHandler


class DatastreamHandler(BaseHandler):
    """Handler for datastream operations and management commands."""

    def handle_datastreams(self):
        """Handle datastreams command - list all datastreams, show details, or delete a specific one"""
        try:
            if hasattr(self.args, 'name') and self.args.name and hasattr(self.args, 'delete') and self.args.delete:
                # Delete the specified datastream with confirmation
                self._handle_datastream_delete()
            elif hasattr(self.args, 'name') and self.args.name:
                # Show details for specific datastream
                datastream_details = self.es_client.get_datastream_details(self.args.name)
                if self.args.format == 'json':
                    print(json.dumps(datastream_details, indent=2))
                else:
                    self._print_datastream_details_table(datastream_details)
            elif hasattr(self.args, 'delete') and self.args.delete:
                # Delete option requires a datastream name
                print("❌ Error: Datastream name is required when using --delete option")
                print("Usage: ./escmd.py datastreams <datastream_name> --delete")
            else:
                # List all datastreams
                datastreams_data = self.es_client.list_datastreams()

                if self.args.format == 'json':
                    print(json.dumps(datastreams_data, indent=2))
                else:
                    self._print_datastreams_table(datastreams_data)

        except Exception as e:
            print(f"Error with datastreams operation: {e}")

    def _print_datastreams_table(self, datastreams_data):
        """Print datastreams list in table format with themed title panel"""
        # Use full terminal width
        console = Console(width=None)  # None means use full terminal width

        # Get cluster information for context
        try:
            health_data = self.es_client.get_cluster_health()
            cluster_name = health_data.get('cluster_name', 'Unknown')
            total_nodes = health_data.get('number_of_nodes', 0)
        except:
            cluster_name = 'Unknown'
            total_nodes = 0

        # Check if there are any datastreams
        datastreams_list = datastreams_data.get('data_streams', [])

        # Calculate statistics
        total_datastreams = len(datastreams_list)
        status_counts = {}
        total_indices = 0
        total_generation = 0
        ilm_policy_count = 0

        for datastream in datastreams_list:
            status = datastream.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            total_indices += len(datastream.get('indices', []))
            total_generation += datastream.get('generation', 0)
            if datastream.get('ilm_policy') and datastream.get('ilm_policy') != 'N/A':
                ilm_policy_count += 1

        # Create colorized subtitle with theme-based styling for statistics
        from rich.text import Text
        subtitle_rich = Text()
        subtitle_rich.append("Cluster: ", style="default")
        subtitle_rich.append(cluster_name, style=self.es_client.style_system._get_style('semantic', 'info', 'cyan'))
        subtitle_rich.append(" | Total: ", style="default")
        subtitle_rich.append(str(total_datastreams), style=self.es_client.style_system._get_style('semantic', 'info', 'cyan'))

        if status_counts.get('open', 0) > 0:
            subtitle_rich.append(" | Open: ", style="default")
            subtitle_rich.append(str(status_counts.get('open', 0)), style=self.es_client.style_system._get_style('semantic', 'success', 'green'))

        if status_counts.get('closed', 0) > 0:
            subtitle_rich.append(" | Closed: ", style="default")
            subtitle_rich.append(str(status_counts.get('closed', 0)), style=self.es_client.style_system._get_style('semantic', 'warning', 'yellow'))

        if total_indices > 0:
            subtitle_rich.append(" | Total Indices: ", style="default")
            subtitle_rich.append(f"{total_indices:,}", style=self.es_client.style_system._get_style('semantic', 'primary', 'bright_magenta'))

        if ilm_policy_count > 0:
            subtitle_rich.append(" | With ILM: ", style="default")
            subtitle_rich.append(str(ilm_policy_count), style=self.es_client.style_system._get_style('semantic', 'secondary', 'bright_blue'))

        # Create title panel with cluster context
        title_panel = Panel(
            self.es_client.style_system.create_semantic_text(
                "📊 Elasticsearch Datastreams",
                "info",
                justify="center"
            ),
            subtitle=subtitle_rich,
            border_style=self.es_client.style_system._get_style('table_styles', 'border_style', 'white'),
            padding=(1, 2),
            expand=True  # Use full width
        )

        print("\n")  # Force newlines
        console.print(title_panel)
        print("\n")

        if not datastreams_list:
            # Create a nice panel showing no datastreams found
            no_data_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    "🔍 No datastreams found in this cluster\n\n"
                    "💡 Datastreams store time-series data (logs, metrics).\n"
                    "   Create using index templates with 'data_stream' config.",
                    "warning",
                    justify="center"
                ),
                title="🔶 No Data Found",
                border_style=self.es_client.style_system.get_semantic_style("warning"),
                padding=(1, 2),
                expand=True  # Use full width
            )

            console.print(no_data_panel)
            print()
            return

        # Create themed table with full width
        table = Table(
            show_header=True,
            header_style=self.es_client.style_system._get_style('table_styles', 'header_style', 'bold white'),
            title=None,  # We have our own title panel now
            expand=True,  # Use full width
            box=self.es_client.style_system.get_table_box()  # Use themed table box
        )

        # Add columns with semantic styling and flexible widths
        table.add_column("Name", style=self.es_client.style_system.get_semantic_style("primary"), no_wrap=False, min_width=15)
        table.add_column("Status", style=self.es_client.style_system.get_semantic_style("success"), min_width=8)
        table.add_column("Template", style=self.es_client.style_system.get_semantic_style("secondary"), min_width=20)
        table.add_column("ILM Policy", style=self.es_client.style_system.get_semantic_style("info"), min_width=12)
        table.add_column("Generation", style=self.es_client.style_system.get_semantic_style("secondary"), justify="right", min_width=10)
        table.add_column("Indices Count", style=self.es_client.style_system.get_semantic_style("secondary"), justify="right", min_width=12)

        for datastream in datastreams_list:
            name = datastream.get('name', 'N/A')
            status = datastream.get('status', 'N/A')
            template = datastream.get('template', 'N/A')
            ilm_policy = datastream.get('ilm_policy', 'N/A')
            generation = str(datastream.get('generation', 0))
            indices_count = str(len(datastream.get('indices', [])))

            table.add_row(name, status, template, ilm_policy, generation, indices_count)

        console.print(table)
        print("\n")  # Extra spacing

        # Create summary panel with actions - also full width
        actions_table = Table(show_header=False, box=None, padding=(0, 1))
        actions_table.add_column("Action", style=self.es_client.style_system.get_semantic_style("primary"), no_wrap=True, min_width=20)
        actions_table.add_column("Command", style=self.es_client.style_system.get_semantic_style("secondary"), min_width=40)

        actions_table.add_row("Rollover datastream:", "./escmd.py rollover <datastream-name>")
        actions_table.add_row("View specific details:", "./escmd.py datastreams <datastream-name>")
        actions_table.add_row("Check index patterns:", "./escmd.py indices")
        actions_table.add_row("Monitor health:", "./escmd.py health")

        actions_panel = Panel(
            actions_table,
            title="🚀 Available Actions",
            border_style=self.es_client.style_system.get_semantic_style("primary"),
            padding=(1, 2),
            expand=True  # Use full width
        )

        console.print(actions_panel)
        print("\n")

    def _print_datastream_details_table(self, datastream_details):
        """Print detailed datastream information in table format"""
        console = Console()

        # Extract the actual datastream data from the API response
        if 'data_streams' in datastream_details and len(datastream_details['data_streams']) > 0:
            datastream = datastream_details['data_streams'][0]
        else:
            datastream = datastream_details

        # Create main details table
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(style="cyan")

        # Basic Information
        table.add_row("🔖  Name:", datastream.get('name', 'N/A'))
        table.add_row("📊 Status:", datastream.get('status', 'N/A'))
        table.add_row("📋 Template:", datastream.get('template', 'N/A'))
        table.add_row("🔄 Generation:", str(datastream.get('generation', 0)))

        # ILM Policy Information
        ilm_policy = datastream.get('ilm_policy', 'N/A')
        table.add_row("🔄 ILM Policy:", ilm_policy if ilm_policy else 'None')

        # Timestamp Field
        timestamp_field = datastream.get('timestamp_field', {})
        if timestamp_field and 'name' in timestamp_field:
            table.add_row("🕐 Timestamp Field:", timestamp_field['name'])
        else:
            table.add_row("🕐 Timestamp Field:", '@timestamp (default)')

        # Flags
        flags = []
        if datastream.get('hidden', False):
            flags.append("Hidden")
        if datastream.get('system', False):
            flags.append("System")
        if datastream.get('replicated', False):
            flags.append("Replicated")

        table.add_row("🔖  Flags:", ', '.join(flags) if flags else 'None')

        # Indices Information
        indices = datastream.get('indices', [])
        table.add_row("📁 Indices Count:", str(len(indices)))

        if indices:
            # Get the write index (most recent)
            write_index = indices[-1]['index_name'] if indices else 'N/A'
            table.add_row("✍️  Write Index:", write_index)

            # Extract dates from index names for age calculation
            index_dates = []
            for idx in indices:
                index_name = idx['index_name']
                # Extract date from index name pattern like .ds-name-2025.09.03-000654
                import re
                date_match = re.search(r'-(\d{4}\.\d{2}\.\d{2})-', index_name)
                if date_match:
                    index_dates.append(date_match.group(1))

            if index_dates:
                oldest_date = min(index_dates)
                newest_date = max(index_dates)
                table.add_row("📅 Date Range:", f"{oldest_date} → {newest_date}")

        panel = Panel(
            table,
            title=f"[bold cyan]📊 Datastream Details[/bold cyan]",
            border_style=self.es_client.style_system._get_style('table_styles', 'border_style', 'white'),
            padding=(1, 2)
        )

        print()
        console.print(panel)

        # Show detailed indices list if there are indices
        if indices and len(indices) > 0:
            print()
            indices_table = Table(
                show_header=True,
                header_style=self.es_client.style_system._get_style('table_styles', 'header_style', 'bold white'),
                title="📁 Backing Indices",
                expand=True,
                box=self.es_client.style_system.get_table_box()
            )

            indices_table.add_column("Index Name", style=self.es_client.style_system.get_semantic_style("primary"), no_wrap=False)
            indices_table.add_column("UUID", style=self.es_client.style_system.get_semantic_style("secondary"), no_wrap=False)
            indices_table.add_column("Type", style=self.es_client.style_system.get_semantic_style("info"), justify="center")

            for i, idx in enumerate(indices):
                index_name = idx['index_name']
                index_uuid = idx['index_uuid']
                # Mark the write index (last one)
                index_type = "✍️  Write" if i == len(indices) - 1 else "📖 Read"

                indices_table.add_row(index_name, index_uuid, index_type)

            console.print(indices_table)

        print()

    def handle_rollover(self):
        """Handle datastream rollover command with Rich formatting."""
        console = self.console

        try:
            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
            except:
                cluster_name = 'Unknown'

            # Create title panel
            title_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    f"🔄 Elasticsearch Datastream Rollover Operation",
                    "info",
                    justify="center"
                ),
                subtitle=f"Target Datastream: {self.args.datastream} | Cluster: {cluster_name}",
                border_style=self.es_client.style_system._get_style('table_styles', 'border_style', 'white'),
                padding=(1, 2)
            )

            print()
            console.print(title_panel)
            print()

            # Perform rollover operation
            with console.status(f"Rolling over datastream '{self.args.datastream}'..."):
                rollover_result = self.es_client.rollover_datastream(self.args.datastream)

            if rollover_result:
                # Success panel
                success_text = f"🎉 Datastream '{self.args.datastream}' has been successfully rolled over!\n\n"
                success_text += "Rollover Details:\n"

                if 'acknowledged' in rollover_result and rollover_result['acknowledged']:
                    success_text += "• ✅ Operation acknowledged by cluster\n"
                if 'shards_acknowledged' in rollover_result and rollover_result['shards_acknowledged']:
                    success_text += "• ✅ Shards acknowledged by cluster\n"
                if 'old_index' in rollover_result:
                    success_text += f"• 📁 Previous index: {rollover_result['old_index']}\n"
                if 'new_index' in rollover_result:
                    success_text += f"• 🆕 New index: {rollover_result['new_index']}\n"
                if 'rolled_over' in rollover_result:
                    success_text += f"• 🔄 Rolled over: {rollover_result['rolled_over']}\n"

                success_panel = Panel(
                    success_text,
                    title="✅ Rollover Operation Successful",
                    border_style=self.es_client.style_system.get_semantic_style("success"),
                    padding=(1, 2)
                )

                console.print(success_panel)
                print()

            else:
                # Failure panel
                error_panel = Panel(
                    self.es_client.style_system.create_semantic_text(
                        f"❌ Failed to rollover datastream '{self.args.datastream}'",
                        "error",
                        justify="center"
                    ),
                    subtitle="Check datastream name and cluster status",
                    border_style=self.es_client.style_system.get_semantic_style("error"),
                    padding=(1, 2)
                )
                console.print(error_panel)
                print()

        except Exception as e:
            error_panel = Panel(
                self.es_client.style_system.create_semantic_text(
                    f"❌ Rollover operation error: {str(e)}",
                    "error",
                    justify="center"
                ),
                subtitle=f"Failed to rollover datastream: {self.args.datastream}",
                border_style=self.es_client.style_system.get_semantic_style("error"),
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()

    def _handle_datastream_delete(self):
        """Handle datastream deletion with confirmation"""
        print(f"❌ Error: Datastream deletion functionality not yet implemented")
        print("This is a destructive operation that requires careful implementation")
