"""
Health-related command handlers for escmd.
"""

import json
import os
import time
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table as InnerTable
from rich.prompt import Confirm

from .base_handler import BaseHandler


class HealthHandler(BaseHandler):
    """Handler for health monitoring and cluster checking commands."""

    def handle_health(self):
        """Handle basic cluster health display - quick mode without detailed diagnostics."""
        # Check if group health is requested
        if hasattr(self.args, 'group') and self.args.group:
            self._handle_health_group()
            return

        # Get only the basic cluster health data
        health_data = self.es_client.get_cluster_health()

        if self.args.format == 'json':
            print(json.dumps(health_data))
        else:
            # Simple, fast display of core health metrics
            try:
                from rich.table import Table
                from rich.panel import Panel
                from rich.console import Console
                from rich.text import Text

                console = self.console if hasattr(self.console, 'print') else Console()

                # Get cluster status and set colors
                status = health_data.get('status', 'unknown').upper()
                if status == 'GREEN':
                    status_color = "bright_green"
                    status_icon = "🟢"
                elif status == 'YELLOW':
                    status_color = "bright_yellow"
                    status_icon = "🟡"
                elif status == 'RED':
                    status_color = "bright_red"
                    status_icon = "🔴"
                else:
                    status_color = "dim"
                    status_icon = "⚪"

                # Create quick health table
                table = Table.grid(padding=(0, 1))
                table.add_column(style=self.es_client.style_system.get_semantic_style("primary"), no_wrap=True)
                table.add_column(style=self.es_client.style_system.get_semantic_style("secondary"))

                # Core health metrics only
                table.add_row("🏢 Cluster:", health_data.get('cluster_name', 'Unknown'))
                table.add_row(f"{status_icon} Status:", f"[bold {status_color}]{status}[/bold {status_color}]")
                table.add_row("💻  Nodes:", str(health_data.get('number_of_nodes', 0)))
                table.add_row("💾 Data Nodes:", str(health_data.get('number_of_data_nodes', 0)))
                table.add_row("🟢 Primary Shards:", f"{health_data.get('active_primary_shards', 0):,}")
                table.add_row("🔵 Total Shards:", f"{health_data.get('active_shards', 0):,}")

                unassigned = health_data.get('unassigned_shards', 0)
                if unassigned > 0:
                    table.add_row("🔴 Unassigned:", self.es_client.style_system.create_semantic_text(f"{unassigned:,}", "error"))
                else:
                    table.add_row("✅ Assignment:", self.es_client.style_system.create_semantic_text("Complete", "success"))

                # Create panel and display
                panel = Panel(
                    table,
                    title=f"⚡ Quick Health Check",
                    subtitle=f"Cluster: {health_data.get('cluster_name', 'Unknown')}",
                    border_style=self.es_client.style_system.get_semantic_style("primary"),
                    padding=(1, 2)
                )

                print()
                console.print(panel)
                print()

            except ImportError as e:
                # Fallback to basic output if rich components aren't available
                print(f"Cluster: {health_data.get('cluster_name', 'Unknown')}")
                print(f"Status: {health_data.get('cluster_status', 'unknown').upper()}")
                print(f"Nodes: {health_data.get('number_of_nodes', 0)}")
                print(f"Data Nodes: {health_data.get('number_of_data_nodes', 0)}")
                print(f"Primary Shards: {health_data.get('active_primary_shards', 0):,}")
                print(f"Total Shards: {health_data.get('active_shards', 0):,}")
                print(f"Unassigned Shards: {health_data.get('unassigned_shards', 0):,}")

    def handle_health_detail(self):
        """Handle detailed cluster health display with comprehensive diagnostics and various modes."""
        # Check if group health is requested
        if hasattr(self.args, 'group') and self.args.group:
            self._handle_health_group()
            return

        # Check if comparison is requested
        if hasattr(self.args, 'compare') and self.args.compare:
            self._handle_health_compare()
            return

        # For JSON output, gather data quickly without progress
        if self.args.format == 'json':
            health_data = self.es_client.get_cluster_health()
            print(json.dumps(health_data))
        else:
            # Choose display style: command-line argument overrides config file
            if hasattr(self.args, 'style') and self.args.style:
                style = self.args.style
            else:
                # Use configured style from elastic_servers.yml
                style = self.location_config.get('health_style', 'dashboard')

            if style == 'classic':
                # For classic mode, show simple progress with semantic styling
                styles = self.es_client.get_theme_styles()
                style_system = self.es_client.style_system

                if style_system:
                    status_style = style_system.get_semantic_style("info")
                    success_style = style_system.get_semantic_style("success")
                else:
                    status_style = style_system.get_semantic_style("error")
                    success_style = style_system.get_semantic_style("error")

                with self.console.status(f"[{status_style}]Gathering cluster health data...") as status:
                    health_data = self.es_client.get_cluster_health()
                    status.update(f"[{success_style}]Processing health data...")

                # Determine classic format: command-line override or config file
                if hasattr(self.args, 'classic_style') and self.args.classic_style:
                    classic_format = self.args.classic_style
                else:
                    classic_format = self.location_config.get('classic_style', 'panel')

                print("")
                if classic_format == 'table':
                    # Original key-value table format
                    self.es_client.print_json_as_table(health_data)
                else:
                    # New styled panel format (same as comparison)
                    self.es_client.print_json_as_table(health_data)
            else:
                # Dashboard mode with detailed progress tracking
                self._handle_health_dashboard()

    def _handle_health_dashboard(self):
        """Handle dashboard health display with progress tracking."""
        import time

        # Set snapshot repository for dashboard
        snapshot_repo = self.location_config.get('elastic_s3snapshot_repo')
        self.es_client.snapshot_repo = snapshot_repo

        # Get theme styles
        styles = self.es_client.get_theme_styles()

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=True
        ) as progress:

            # Get style system for semantic styling
            style_system = self.es_client.style_system

            # Create main task with semantic styling
            if style_system:
                main_task_style = style_system.get_semantic_style("info")
                step1_style = style_system.get_semantic_style("info")
                step2_style = style_system.get_semantic_style("warning")
                step3_style = style_system.get_semantic_style("warning")
                step4_style = style_system.get_semantic_style("success")
                step5_style = style_system.get_semantic_style("secondary")
                step6_style = style_system.get_semantic_style("info")
            else:
                main_task_style = styles.get('header_style', 'bold cyan')
                step1_style = styles.get('header_style', 'bold cyan')
                step2_style = styles.get('warning_style', 'bold yellow')
                step3_style = styles.get('warning_style', 'bold orange1')
                step4_style = styles.get('success_style', 'bold green')
                step5_style = styles.get('value_style', 'bold magenta')
                step6_style = styles.get('header_style', 'bold blue')

            main_task = progress.add_task(f"[{main_task_style}]Gathering cluster diagnostics...", total=6)

            # Step 1: Basic cluster health
            progress.update(main_task, description=f"[{step1_style}]📊 Getting cluster health...")
            health_data = self.es_client.get_cluster_health()
            progress.advance(main_task)
            time.sleep(0.1)  # Brief pause to show progress

            # Step 2: Recovery status
            progress.update(main_task, description=f"[{step2_style}]🔄 Checking recovery status...")
            recovery_status = self.es_client.get_recovery_status()
            progress.advance(main_task)
            time.sleep(0.1)

            # Step 3: Allocation issues
            progress.update(main_task, description=f"[{step3_style}]🔶  Analyzing allocation issues...")
            allocation_issues = self.es_client.check_allocation_issues()
            progress.advance(main_task)
            time.sleep(0.1)

            # Step 4: Node information
            progress.update(main_task, description=f"[{step4_style}]💻  Getting node details...")
            try:
                nodes = self.es_client.get_nodes()
                progress.advance(main_task)
            except:
                nodes = []
                progress.advance(main_task)
            time.sleep(0.1)

            # Step 5: Master node identification
            progress.update(main_task, description=f"[{step5_style}]👑 Identifying master node...")
            try:
                master_node = self.es_client.get_master_node()
                progress.advance(main_task)
            except:
                master_node = "Unknown"
                progress.advance(main_task)
            time.sleep(0.1)

            # Step 6: Snapshot information (if configured)
            if snapshot_repo:
                progress.update(main_task, description=f"[{step6_style}]📦 Checking snapshot status...")
                try:
                    snapshots = self.es_client.list_snapshots(snapshot_repo)
                    progress.advance(main_task)
                except:
                    snapshots = []
                    progress.advance(main_task)
            else:
                progress.update(main_task, description=f"[{self.es_client.style_system.get_semantic_style('info')}]📦 Finalizing dashboard...")
                snapshots = []
                progress.advance(main_task)
            time.sleep(0.1)

            # Final update
            progress.update(main_task, description=f"[{self.es_client.style_system.get_semantic_style('success')}]✅ Dashboard ready!")
            time.sleep(0.2)  # Brief pause to show completion

        # Store additional data in health_data for dashboard
        health_data['_recovery_status'] = recovery_status
        health_data['_allocation_issues'] = allocation_issues
        health_data['_nodes'] = nodes
        health_data['_master_node'] = master_node
        health_data['_snapshots'] = snapshots

        # Display the dashboard
        self.es_client.print_stylish_health_dashboard(health_data)



    def _handle_health_compare(self):
        """Handle health comparison between two clusters."""
        from esclient import ElasticsearchClient
        from configuration_manager import ConfigurationManager

        current_cluster = self.current_location
        compare_cluster = self.args.compare

        # Get health data from current cluster
        try:
            current_health = self.es_client.get_cluster_health()
            current_status = "✅"
        except Exception as e:
            current_health = {"error": str(e)}
            current_status = "❌"

        # Get configuration for comparison cluster
        config_manager = ConfigurationManager(self.config_file, "default.state")
        try:
            compare_config = config_manager.get_server_config_by_location(compare_cluster)
            if not compare_config:
                print(f"❌ Error: Cluster '{compare_cluster}' not found in configuration")
                return

            # Map configuration keys to ElasticsearchClient format
            hostname = compare_config.get('elastic_host')
            hostname2 = compare_config.get('elastic_host2')
            port = compare_config.get('elastic_port', 9200)

            # Validate required configuration
            if not hostname:
                print(f"❌ Error: No hostname configured for cluster '{compare_cluster}'")
                return

            # Create client for comparison cluster with proper authentication handling
            username = compare_config.get('elastic_username')
            password = compare_config.get('elastic_password')

            # Handle None values that might cause issues
            if username is None:
                username = ""
            if password is None:
                password = ""
            if hostname2 is None:
                hostname2 = ""

            compare_es_client = ElasticsearchClient(
                hostname,           # host1
                hostname2,          # host2
                port,               # port
                compare_config.get('use_ssl', False),                  # use_ssl
                compare_config.get('verify_certs', False),             # verify_certs
                compare_config.get('read_timeout', 60),                # timeout
                compare_config.get('elastic_authentication', False),   # elastic_authentication
                username,           # elastic_username
                password            # elastic_password
            )

            # Get health data from comparison cluster
            try:
                compare_health = compare_es_client.get_cluster_health()
                compare_status = "✅"
            except Exception as e:
                compare_health = {"error": str(e)}
                compare_status = "❌"

        except Exception as e:
            print(f"❌ Error connecting to cluster '{compare_cluster}': {str(e)}")
            return

        # Display side-by-side comparison
        if self.args.format == 'json':
            comparison_data = {
                current_cluster: current_health,
                compare_cluster: compare_health
            }
            print(json.dumps(comparison_data))
        else:
            self.es_client.print_side_by_side_health(
                current_cluster, current_health, current_status,
                compare_cluster, compare_health, compare_status
            )

    def _handle_health_group(self):
        """Handle health display for all clusters in a group."""
        group_name = self.args.group
        output_format = getattr(self.args, 'format', 'table')

        # Use the existing multi-cluster health comparison method
        self.es_client.print_multi_cluster_health_comparison(self.config_file, group_name, output_format)

    def handle_ping(self):
        """Enhanced ping command with Rich formatting and detailed connection information."""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table as InnerTable

        console = self.console

        try:
            # Test the connection
            if self.es_client.ping():
                # Get comprehensive cluster information
                cluster_connection_info = self._get_cluster_connection_info()

                # Get cluster health for additional context
                try:
                    health_data = self.es_client.get_cluster_health()
                    cluster_name = health_data.get('cluster_name', 'Unknown')
                    cluster_status = health_data.get('cluster_status', 'unknown')
                    total_nodes = health_data.get('number_of_nodes', 0)
                    data_nodes = health_data.get('number_of_data_nodes', 0)
                except:
                    cluster_name = 'Unknown'
                    cluster_status = 'unknown'
                    total_nodes = 0
                    data_nodes = 0

                # Handle JSON format
                if getattr(self.args, 'format', 'table') == 'json':
                    ping_data = {
                        'connection_successful': True,
                        'cluster_name': cluster_name,
                        'cluster_status': cluster_status,
                        'connection_details': {
                            'host': self.es_client.host1,
                            'port': self.es_client.port,
                            'ssl_enabled': self.es_client.use_ssl,
                            'verify_certs': self.es_client.verify_certs,
                            'username': self.es_client.elastic_username if self.es_client.elastic_username else None
                        },
                        'cluster_overview': {
                            'total_nodes': total_nodes,
                            'data_nodes': data_nodes
                        }
                    }
                    print(json.dumps(ping_data, indent=2))
                    return True

                # Get theme styles for consistent coloring
                from esclient import get_theme_styles
                # Create title panel
                title_panel = Panel(
                    self.es_client.style_system.create_semantic_text("🏓 Elasticsearch Connection Test", "success", justify="center"),
                    subtitle=f"✅ Connection Successful | Cluster: {cluster_name} | Status: {cluster_status.title()}",
                    border_style=self.es_client.style_system.get_semantic_style("success"),
                    padding=(1, 2)
                )

                # Create connection details panel
                connection_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                connection_table.add_column("Label", style=self.es_client.style_system.get_semantic_style("primary"), no_wrap=True)
                connection_table.add_column("Icon", justify="left", width=3)
                connection_table.add_column("Value", style=self.es_client.style_system.get_semantic_style("secondary"), no_wrap=True)

                connection_table.add_row("Host:", "🌐", self.es_client.host1)
                connection_table.add_row("Port:", "🔌", str(self.es_client.port))
                connection_table.add_row("SSL Enabled:", "🔒", "Yes" if self.es_client.use_ssl else "No")
                connection_table.add_row("Verify Certs:", "📜", "Yes" if self.es_client.verify_certs else "No")

                if self.es_client.elastic_username:
                    connection_table.add_row("Username:", "👤", self.es_client.elastic_username)
                    connection_table.add_row("Password:", "🔐", "***" + self.es_client.elastic_password[-2:] if len(self.es_client.elastic_password) > 2 else "***")
                else:
                    connection_table.add_row("Authentication:", "🔓", "None")

                connection_panel = Panel(
                    connection_table,
                    title="🔗 Connection Details",
                    border_style=self.es_client.style_system.get_semantic_style("info"),
                    padding=(1, 2)
                )

                # Create cluster overview panel
                overview_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                overview_table.add_column("Label", style=self.es_client.style_system.get_semantic_style("primary"), no_wrap=True)
                overview_table.add_column("Icon", justify="left", width=3)
                overview_table.add_column("Value", style=self.es_client.style_system.get_semantic_style("secondary"), no_wrap=True)

                status_icon = "🟢" if cluster_status == 'green' else "🟡" if cluster_status == 'yellow' else "🔴"
                overview_table.add_row("Cluster Name:", "🏢", cluster_name)
                overview_table.add_row("Status:", status_icon, cluster_status.title())
                overview_table.add_row("Total Nodes:", "💻", str(total_nodes))
                overview_table.add_row("Data Nodes:", "💾", str(data_nodes))

                overview_panel = Panel(
                    overview_table,
                    title="📊 Cluster Overview",
                    border_style=self.es_client.style_system.get_semantic_style("info"),
                    padding=(1, 2)
                )

                # Create quick actions panel
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style=self.es_client.style_system.get_semantic_style("primary"), no_wrap=True)
                actions_table.add_column("Command", style=self.es_client.style_system.get_semantic_style("secondary"))

                actions_table.add_row("Check health:", "./escmd.py health")
                actions_table.add_row("View nodes:", "./escmd.py nodes")
                actions_table.add_row("List indices:", "./escmd.py indices")
                actions_table.add_row("View settings:", "./escmd.py settings")
                actions_table.add_row("JSON output:", "./escmd.py ping --format json")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Next Steps",
                    border_style=self.es_client.style_system.get_semantic_style("primary"),
                    padding=(1, 2)
                )

                # Display everything
                print()
                console.print(title_panel)
                print()
                console.print(Columns([connection_panel, overview_panel], expand=True))
                print()
                console.print(actions_panel)
                print()

                return True
            else:
                # Connection failed
                if getattr(self.args, 'format', 'table') == 'json':
                    error_data = {
                        'connection_successful': False,
                        'error': 'Connection failed',
                        'host': self.es_client.host1,
                        'port': self.es_client.port
                    }
                    print(json.dumps(error_data, indent=2))
                    return False

                # Get theme styles for consistent coloring
                from esclient import get_theme_styles
                error_panel = Panel(
                    self.es_client.style_system.create_semantic_text("❌ Connection Failed", "error", justify="center"),
                    subtitle=f"Unable to connect to {self.es_client.host1}:{self.es_client.port}",
                    border_style=self.es_client.style_system.get_semantic_style("error"),
                    padding=(1, 2)
                )
                print()
                console.print(error_panel)
                print()
                return False

        except Exception as e:
            # Handle connection errors
            if getattr(self.args, 'format', 'table') == 'json':
                error_data = {
                    'connection_successful': False,
                    'error': str(e),
                    'host': self.es_client.host1,
                    'port': self.es_client.port
                }
                print(json.dumps(error_data, indent=2))
                return False

            self.es_client.show_message_box("Connection Error", f"❌ Connection Error: {str(e)}\nFailed to ping {self.es_client.host1}:{self.es_client.port}",
                                           message_style=self.es_client.style_system.get_semantic_style("secondary"),
                                           panel_style=self.es_client.style_system.get_semantic_style("error"))
            return False

    def _get_cluster_connection_info(self):
        """Get cluster connection information for ping command."""
        return {
            'host': self.es_client.host1,
            'port': self.es_client.port,
            'ssl_enabled': self.es_client.use_ssl,
            'verify_certs': self.es_client.verify_certs,
            'username': self.es_client.elastic_username if self.es_client.elastic_username else None
        }

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
            print(json.dumps(sanitized_results, indent=2, ensure_ascii=True))
        else:
            # Rich formatted output with progress tracking
            styles = self.es_client.get_theme_styles()
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
                main_task = progress.add_task(f"[{self.es_client.style_system.get_semantic_style('info')}]Running cluster health checks...", total=total_steps)

                # Step 1: ILM errors check (skip if requested)
                if not skip_ilm:
                    progress.update(main_task, description=f"[{self.es_client.style_system.get_semantic_style('warning')}]🔍 Checking for ILM errors...")
                    ilm_errors = self.es_client.check_ilm_errors()
                    progress.advance(main_task)
                    time.sleep(0.1)
                else:
                    ilm_errors = {'skipped': True, 'reason': 'ILM checks skipped via --skip-ilm flag'}

                # Step 2: No replicas check
                progress.update(main_task, description=f"[{self.es_client.style_system.get_semantic_style('info')}]📊 Checking indices with no replicas...")
                no_replica_indices = self.es_client.check_no_replica_indices()
                progress.advance(main_task)
                time.sleep(0.1)

                # Step 3: Large shards check
                progress.update(main_task, description=f"[{self.es_client.style_system.get_semantic_style('warning')}]📏 Checking for oversized shards...")
                large_shards = self.es_client.check_large_shards(max_shard_size)
                progress.advance(main_task)
                time.sleep(0.1)

                # Step 4: Generate report
                progress.update(main_task, description=f"[{self.es_client.style_system.get_semantic_style('success')}]📋 Generating health report...")
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
        try:
            # Get no-replica indices from check results
            no_replica_indices = check_results.get('no_replica_indices', [])
            if not no_replica_indices:
                return {
                    'success': True,
                    'message': 'No indices found with 0 replicas - nothing to fix',
                    'indices_processed': 0,
                    'indices_updated': 0,
                    'results': []
                }

            # Convert to target indices list
            target_indices = [idx['index'] for idx in no_replica_indices]

            # Extract arguments
            dry_run = getattr(self.args, 'dry_run', False)
            force = getattr(self.args, 'force', False)

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
                'success': False,
                'error': str(e),
                'target_count': target_count
            }

    def display_cluster_health_report(self, check_results):
        """
        Display a comprehensive cluster health report using Rich formatting.
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.columns import Columns
        from rich.text import Text
        from rich import box
        from datetime import datetime
        from configuration_manager import ConfigurationManager

        console = Console()

        # Get configuration for display limits
        config_manager = ConfigurationManager(self.config_file, "escmd.json")

        # Use ILM limit from check_results if provided (from command-line arg), otherwise use config setting
        ilm_display_limit = check_results.get('ilm_display_limit')
        if ilm_display_limit is None:
            ilm_display_limit = config_manager.get_ilm_display_limit()

        # Extract results
        ilm_results = check_results.get('ilm_errors', check_results.get('ilm_results', []))
        no_replica_indices = check_results.get('no_replica_indices', [])
        large_shards = check_results.get('large_shards', [])
        max_shard_size = check_results.get('max_shard_size', 50)
        show_details = check_results.get('show_details', False)

        # Handle both old format (list) and new format (dict) for backward compatibility
        if isinstance(ilm_results, dict):
            ilm_errors = ilm_results.get('errors', [])
            ilm_no_policy_raw = ilm_results.get('no_policy', [])
            ilm_managed_count = ilm_results.get('managed_count', 0)
            ilm_total_count = ilm_results.get('total_indices', 0)
        else:
            # Old format - treat as error list only
            ilm_errors = ilm_results
            ilm_no_policy_raw = []
            ilm_managed_count = 0
            ilm_total_count = len(ilm_errors)

        # Separate no_policy indices into two categories
        ilm_no_policy = []
        ilm_s3_managed = []

        for idx_info in ilm_no_policy_raw:
            reason = idx_info.get('reason', '')
            if reason == 'S3-Snapshot managed':
                ilm_s3_managed.append(idx_info)
            else:
                ilm_no_policy.append(idx_info)

        # Update managed count to include S3-managed indices
        total_managed_count = ilm_managed_count + len(ilm_s3_managed)

        # Create title panel
        try:
            cluster_name = self.es_client.get_cluster_health().get('cluster_name', 'Unknown')
        except:
            cluster_name = 'Unknown'

        title_text = f"🏥 Cluster Health Check Report"
        subtitle_text = f"Cluster: {cluster_name} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        title_panel = Panel(
            self.es_client.style_system.create_semantic_text(title_text, "info", justify="center"),
            subtitle=subtitle_text,
            border_style="cyan",
            padding=(1, 2)
        )

        # Create summary panel
        summary_table = Table.grid(padding=(0, 1))
        summary_table.add_column(style=self.es_client.style_system.get_semantic_style("primary"), no_wrap=True)
        summary_table.add_column(style=self.es_client.style_system.get_semantic_style("info"))

        # Add summary with status indicators
        if isinstance(ilm_results, dict) and ilm_results.get('not_supported'):
            ilm_status = "🔵 Not supported on this cluster"
        elif isinstance(ilm_results, dict) and ilm_results.get('skipped'):
            ilm_status = "💤 Skipped"
        else:
            error_count = len(ilm_errors)
            no_policy_count = len(ilm_no_policy)
            s3_managed_count = len(ilm_s3_managed)

            if error_count == 0 and no_policy_count == 0:
                if s3_managed_count > 0:
                    ilm_status = f"✅ All managed ({s3_managed_count} S3-managed)"
                else:
                    ilm_status = "✅ All indices managed"
            elif error_count > 0 and no_policy_count > 0:
                status_parts = [f"❌ {error_count} errors", f"🔶 {no_policy_count} unmanaged"]
                if s3_managed_count > 0:
                    status_parts.append(f"✅ {s3_managed_count} S3-managed")
                ilm_status = ", ".join(status_parts)
            elif error_count > 0:
                status_parts = [f"❌ {error_count} errors found"]
                if s3_managed_count > 0:
                    status_parts.append(f"✅ {s3_managed_count} S3-managed")
                ilm_status = ", ".join(status_parts)
            elif no_policy_count > 0:
                status_parts = [f"🔶 {no_policy_count} indices unmanaged"]
                if s3_managed_count > 0:
                    status_parts.append(f"✅ {s3_managed_count} S3-managed")
                ilm_status = ", ".join(status_parts)
            else:
                ilm_status = f"✅ {s3_managed_count} S3-managed"

        replica_status = "✅ All have replicas" if len(no_replica_indices) == 0 else f"🔶 {len(no_replica_indices)} without replicas"
        shard_status = "✅ All within limits" if len(large_shards) == 0 else f"🔶 {len(large_shards)} oversized shards"

        summary_table.add_row("🔍 ILM Status:", ilm_status)
        summary_table.add_row("📊 Replica Status:", replica_status)
        summary_table.add_row(f"📏 Shard Size (>{max_shard_size}GB):", shard_status)

        # Determine border color based on issues found
        has_ilm_errors = len(ilm_errors) > 0
        has_ilm_unmanaged = len(ilm_no_policy) > 0  # Only truly unmanaged indices count as issues
        has_issues = has_ilm_errors or has_ilm_unmanaged or len(no_replica_indices) > 0 or len(large_shards) > 0

        summary_panel = Panel(
            summary_table,
            title="📋 Summary",
            border_style="green" if not has_issues else "yellow",
            padding=(1, 2)
        )

        # Display header
        print()
        console.print(title_panel)
        print()
        console.print(summary_panel)

        # Create detailed panels if there are issues or details requested
        panels = []

        # ILM Issues Panel
        if isinstance(ilm_results, dict) and ilm_results.get('skipped'):
            # Show info panel for skipped ILM checks
            info_text = f"💤 {ilm_results.get('reason', 'ILM checks were skipped')}\n\nUse the command without --skip-ilm to include ILM checks."
            info_panel = Panel(
                Text(info_text, style="bright_blue", justify="left"),
                title="🔵 ILM Checks Skipped",
                border_style="blue",
                padding=(1, 2)
            )
            panels.append(info_panel)
        elif isinstance(ilm_results, dict) and ilm_results.get('not_supported'):
            # Show info panel for unsupported ILM
            info_text = f"🔵 {ilm_results.get('reason', 'ILM is not supported on this cluster')}\n\nThis cluster may be running an older version of Elasticsearch or have ILM disabled."
            info_panel = Panel(
                Text(info_text, style="bright_blue", justify="left"),
                title="🔵 ILM Not Available",
                border_style="blue",
                padding=(1, 2)
            )
            panels.append(info_panel)
        elif ilm_errors or ilm_no_policy or ilm_s3_managed or show_details:
            # ILM Errors Panel
            if ilm_errors:
                error_table = Table(box=self.es_client.style_system.get_table_box(), show_header=True, header_style=self.es_client.style_system.get_semantic_style("primary"))
                error_table.add_column("Index", style="cyan")
                error_table.add_column("Error", style="red")
                error_table.add_column("Policy", style="yellow")
                error_table.add_column("Phase", style="green")
                error_table.add_column("Action", style="blue")

                # Sort error indices alphabetically for better readability
                sorted_errors = sorted(ilm_errors, key=lambda x: x.get('index', ''))
                for error in sorted_errors:
                    policy = error.get('policy', 'Unknown')
                    phase = error.get('phase', 'Unknown')
                    action = error.get('action', 'Unknown')
                    step_info = error.get('step_info', {})
                    error_reason = step_info.get('reason', 'Unknown error') if isinstance(step_info, dict) else 'Unknown error'

                    error_table.add_row(
                        error['index'],
                        f"{error_reason[:60]}{'...' if len(error_reason) > 60 else ''}",
                        policy,
                        phase,
                        action
                    )

                error_panel = Panel(
                    error_table,
                    title=f"❌ ILM Errors ({len(ilm_errors)} indices)",
                    border_style="red",
                    padding=(1, 1)
                )
                panels.append(error_panel)

            # No Policy Panel (truly unmanaged indices)
            if ilm_no_policy:
                no_policy_table = Table(box=self.es_client.style_system.get_table_box(), show_header=True, header_style=self.es_client.style_system.get_semantic_style("primary"))
                no_policy_table.add_column("Index", style="cyan")
                no_policy_table.add_column("Status", style="yellow")

                no_policy_shown = 0
                # Sort indices alphabetically for better readability
                sorted_no_policy = sorted(ilm_no_policy, key=lambda x: x.get('index', ''))
                for no_policy in sorted_no_policy:
                    if not show_details and no_policy_shown >= ilm_display_limit:
                        no_policy_table.add_row("...", f"{len(ilm_no_policy) - no_policy_shown} more unmanaged indices")
                        break

                    no_policy_table.add_row(
                        no_policy['index'],
                        no_policy.get('reason', 'No ILM policy attached')
                    )
                    no_policy_shown += 1

                no_policy_panel = Panel(
                    no_policy_table,
                    title=f"🔶  Unmanaged Indices ({len(ilm_no_policy)} indices)",
                    border_style="yellow",
                    padding=(1, 1)
                )
                panels.append(no_policy_panel)

            # S3-Snapshot Managed Panel
            if ilm_s3_managed:
                s3_table = Table(box=self.es_client.style_system.get_table_box(), show_header=True, header_style=self.es_client.style_system.get_semantic_style("primary"))
                s3_table.add_column("Index", style="cyan")
                s3_table.add_column("Management", style="green")

                s3_shown = 0
                # Sort indices alphabetically for better readability
                sorted_s3_managed = sorted(ilm_s3_managed, key=lambda x: x.get('index', ''))
                for s3_managed in sorted_s3_managed:
                    if not show_details and s3_shown >= ilm_display_limit:
                        s3_table.add_row("...", f"{len(ilm_s3_managed) - s3_shown} more S3-managed indices")
                        break

                    s3_table.add_row(
                        s3_managed['index'],
                        s3_managed.get('reason', 'S3-Snapshot managed')
                    )
                    s3_shown += 1

                s3_panel = Panel(
                    s3_table,
                    title=f"✅ S3-Managed Indices ({len(ilm_s3_managed)} indices)",
                    border_style="green",
                    padding=(1, 1)
                )
                panels.append(s3_panel)

        # No Replicas Panel
        if no_replica_indices or show_details:
            # Show detailed replica issues panel
            replica_table = Table(box=self.es_client.style_system.get_table_box(), show_header=True, header_style=self.es_client.style_system.get_semantic_style("primary"))
            replica_table.add_column("Index", style="cyan")
            replica_table.add_column("Shards", style="yellow")
            replica_table.add_column("Replicas", style="red")
            replica_table.add_column("Creation Date", style="green")

            shown_count = 0
            for index_info in no_replica_indices:
                if not show_details and shown_count >= 10:
                    replica_table.add_row("...", "", "", f"and {len(no_replica_indices) - shown_count} more")
                    break

                creation_date = index_info.get('creation_date', 'Unknown')
                if creation_date != 'Unknown' and creation_date != 'N/A':
                    try:
                        # Convert timestamp to readable format
                        import datetime as dt
                        date_obj = dt.datetime.fromtimestamp(int(creation_date) / 1000)
                        creation_date = date_obj.strftime('%Y-%m-%d %H:%M')
                    except (ValueError, TypeError):
                        pass

                replica_table.add_row(
                    index_info['index'],
                    str(index_info.get('shards', 'Unknown')),
                    str(index_info.get('replicas', 0)),
                    creation_date
                )
                shown_count += 1

            if replica_table.rows:
                replica_panel = Panel(
                    replica_table,
                    title=f"📊 Indices Without Replicas ({len(no_replica_indices)})",
                    border_style="yellow",
                    padding=(1, 1)
                )
                panels.append(replica_panel)

        # Large Shards Panel
        if large_shards or show_details:
            # Show detailed shard allocation issues panel
            shard_table = Table(box=self.es_client.style_system.get_table_box(), show_header=True, header_style=self.es_client.style_system.get_semantic_style("primary"))
            shard_table.add_column("Index", style="cyan")
            shard_table.add_column("Shard", style="yellow")
            shard_table.add_column("Type", style="blue")
            shard_table.add_column("Size (GB)", style="red", justify="right")
            shard_table.add_column("Node", style="green")

            shown_count = 0
            for shard_info in large_shards:
                if not show_details and shown_count >= 10:
                    shard_table.add_row("...", "", "", "", f"and {len(large_shards) - shown_count} more")
                    break

                shard_table.add_row(
                    shard_info['index'],
                    str(shard_info['shard']),
                    shard_info['type'],
                    f"{shard_info['size_gb']:.2f}",
                    shard_info.get('node', 'unassigned')
                )
                shown_count += 1

            if shard_table.rows:
                shard_panel = Panel(
                    shard_table,
                    title=f"📏 Large Shards (>{max_shard_size}GB) - ({len(large_shards)})",
                    border_style="yellow",
                    padding=(1, 1)
                )
                panels.append(shard_panel)

        # Display all panels
        if panels:
            print()
            for panel in panels:
                console.print(panel)
                print()

        # Add footer with recommendations
        if has_issues:
            recommendations = []
            if ilm_errors:
                recommendations.append("• Fix ILM errors to ensure proper index lifecycle management")
            if ilm_no_policy:
                recommendations.append("• Consider attaching ILM policies to unmanaged indices")
            if no_replica_indices:
                recommendations.append("• Add replicas to indices for high availability")
            if large_shards:
                recommendations.append(f"• Consider breaking down shards larger than {max_shard_size}GB")

            if recommendations:
                rec_text = "\n".join(recommendations)
                rec_panel = Panel(
                    Text(rec_text, style="bright_yellow"),
                    title="💡 Recommendations",
                    border_style="yellow",
                    padding=(1, 2)
                )
                console.print(rec_panel)
                print()

        # Final status
        if not has_issues:
            success_panel = Panel(
                self.es_client.style_system.create_semantic_text("🎉 No issues found! Your cluster appears to be healthy.", "success", justify="center"),
                border_style="green",
                padding=(1, 2)
            )
            console.print(success_panel)
        else:
            warning_count = (len(no_replica_indices) > 0) + (len(large_shards) > 0) + (len(ilm_no_policy) > 0)
            error_count = len(ilm_errors)

            status_text = f"Found {error_count} errors and {warning_count} warnings that need attention."
            status_panel = Panel(
                self.es_client.style_system.create_semantic_text(status_text, "error" if error_count > 0 else "warning", justify="center"),
                border_style="red" if error_count > 0 else "yellow",
                padding=(1, 2)
            )
            console.print(status_panel)

        print()

    def _sanitize_for_json(self, data):
        """Sanitize data to ensure it's JSON serializable."""
        if isinstance(data, dict):
            return {key: self._sanitize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_json(item) for item in data]
        elif isinstance(data, (str, int, float, bool)) or data is None:
            return data
        else:
            # Convert any other type to string
            return str(data)
