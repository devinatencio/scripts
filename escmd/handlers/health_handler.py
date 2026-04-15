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
            try:
                from rich.panel import Panel
                from rich.table import Table
                from rich.text import Text
                from rich.console import Console

                console = self.console if hasattr(self.console, 'print') else Console()
                tm = self.es_client.theme_manager
                ss = self.es_client.style_system
                styles = tm.get_theme_styles()

                # Resolve styles
                primary     = ss.get_semantic_style("primary")
                success     = ss.get_semantic_style("success")
                warning     = ss.get_semantic_style("warning")
                error       = ss.get_semantic_style("error")
                info        = ss.get_semantic_style("info")
                muted       = ss.get_semantic_style("muted")
                border      = styles.get('border_style', 'white')
                label_style = "bold white"
                health_styles = styles.get('health_styles', {})
                type_styles   = styles.get('type_styles', {})
                row_styles    = styles.get('row_styles', {})
                normal        = row_styles.get('normal', 'bright_white')
                primary_shard = type_styles.get('primary', {}).get('text', 'bright_cyan')
                replica_shard = type_styles.get('replica', {}).get('text', 'bright_blue')

                # Data
                status       = health_data.get('status', 'unknown')
                cluster_name = health_data.get('cluster_name', 'Unknown')
                version      = health_data.get('cluster_version', {})
                version_str  = version.get('number', '') if isinstance(version, dict) else str(version or '')
                total_nodes  = health_data.get('number_of_nodes', 0)
                data_nodes   = health_data.get('number_of_data_nodes', 0)
                primary_s    = health_data.get('active_primary_shards', 0)
                total_shards = health_data.get('active_shards', 0)
                replicas     = total_shards - primary_s
                unassigned   = health_data.get('unassigned_shards', 0)
                relocating   = health_data.get('relocating_shards', 0)
                initializing = health_data.get('initializing_shards', 0)
                index_count  = health_data.get('number_of_indices')
                timed_out    = health_data.get('timed_out', False)

                if status == 'green':
                    status_icon  = "🟢"
                    status_style = health_styles.get('green', {}).get('text', success)
                elif status == 'yellow':
                    status_icon  = "🟡"
                    status_style = health_styles.get('yellow', {}).get('text', warning)
                elif status == 'red':
                    status_icon  = "🔴"
                    status_style = health_styles.get('red', {}).get('text', error)
                else:
                    status_icon  = "⚪"
                    status_style = muted

                from rich.rule import Rule

                def make_section():
                    t = Table.grid(padding=(0, 2))
                    t.add_column(justify="left", no_wrap=True, width=4)   # icon
                    t.add_column(justify="left", no_wrap=True, width=16)  # label
                    t.add_column(justify="left")                           # value
                    return t

                def add_row(t, icon, label, value_text):
                    t.add_row(icon, Text(label, style=label_style), value_text)

                # Single-column outer table — Rule rows span full width here
                outer = Table.grid(padding=(0, 0))
                outer.add_column(ratio=1)

                # ── Cluster + Nodes ──────────────────────────────────────
                s1 = make_section()
                cluster_val = Text()
                cluster_val.append(cluster_name, style=primary)
                if version_str:
                    cluster_val.append(f"  v{version_str}", style=muted)
                add_row(s1, "🏢", "Cluster", cluster_val)

                status_val = Text()
                status_val.append(f"{status_icon} {status.upper()}", style=status_style)
                add_row(s1, "📊", "Status", status_val)

                nodes_val = Text()
                nodes_val.append(str(total_nodes), style=normal)
                nodes_val.append("  data: ", style=muted)
                nodes_val.append(str(data_nodes), style=success)
                other = total_nodes - data_nodes
                if other > 0:
                    nodes_val.append("  master: ", style=muted)
                    nodes_val.append(str(other), style=warning)
                add_row(s1, "💻", "Nodes", nodes_val)
                outer.add_row(s1)

                # ── Indices + Shards ──────────────────────────────────────
                outer.add_row(Rule(style=muted))
                s2 = make_section()
                if index_count is not None:
                    add_row(s2, "📂", "Indices", Text(f"{index_count:,}", style=normal))

                shards_val = Text()
                shards_val.append(str(total_shards), style=normal)
                shards_val.append("  primary: ", style=muted)
                shards_val.append(str(primary_s), style=primary_shard)
                shards_val.append("  replicas: ", style=muted)
                shards_val.append(str(replicas), style=replica_shard)
                add_row(s2, "🔵", "Shards", shards_val)

                if relocating > 0:
                    add_row(s2, "🔀", "Relocating", Text(f"{relocating:,}", style=warning))
                if initializing > 0:
                    add_row(s2, "⏳", "Initializing", Text(f"{initializing:,}", style=info))

                if unassigned > 0:
                    unassigned_val = Text()
                    unassigned_val.append(str(unassigned), style=error)
                    unassigned_val.append("  ⚠ not assigned", style=warning)
                    add_row(s2, "🔴", "Unassigned", unassigned_val)
                    try:
                        reasons = self.es_client.health_commands.get_unassigned_shard_reasons()
                        if reasons:
                            reason_str = ", ".join(
                                f"{r}: {c}" for r, c in sorted(reasons.items(), key=lambda x: -x[1])
                            )
                            add_row(s2, "  ", "", Text(f"└─ {reason_str}", style=warning))
                    except Exception:
                        pass
                else:
                    add_row(s2, "✅", "Unassigned", Text("0  all assigned", style=success))
                outer.add_row(s2)

                if timed_out:
                    outer.add_row(Rule(style=error))
                    s3 = make_section()
                    add_row(s3, "⚠️ ", "Timed Out", Text("health check incomplete", style=error))
                    outer.add_row(s3)

                title_style = styles.get('panel_styles', {}).get('title', 'bold white')
                if status == 'green':
                    panel_border = 'green'
                elif status == 'yellow':
                    panel_border = 'yellow'
                elif status == 'red':
                    panel_border = 'red'
                else:
                    panel_border = border
                panel = Panel(
                    outer,
                    title=f"[{title_style}]⚡ Cluster Health[/{title_style}]",
                    border_style=panel_border,
                    padding=(1, 3),
                )

                print()
                console.print(panel)
                print()

            except ImportError:
                print(f"Cluster: {health_data.get('cluster_name', 'Unknown')}")
                print(f"Status: {health_data.get('status', 'unknown').upper()}")
                print(f"Nodes: {health_data.get('number_of_nodes', 0)}")
                print(f"Primary Shards: {health_data.get('active_primary_shards', 0):,}")
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
        from rich.console import Console, Group
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich.rule import Rule
        from datetime import datetime
        from configuration_manager import ConfigurationManager

        console = Console()

        def emit_panel(renderable, ending_newline=True):
            console.print(renderable)
            if ending_newline:
                print()

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

        # Create combined header panel — title + summary in one
        try:
            cluster_name = self.es_client.get_cluster_health().get('cluster_name', 'Unknown')
        except:
            cluster_name = 'Unknown'

        ss = self.es_client.style_system

        # Determine overall status
        has_ilm_errors = len(ilm_errors) > 0
        has_ilm_unmanaged = len(ilm_no_policy) > 0
        has_issues = has_ilm_errors or has_ilm_unmanaged or len(no_replica_indices) > 0 or len(large_shards) > 0

        err_style = ss._get_style('semantic', 'error', 'red') if ss else 'red'
        warn_style = ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'
        ok_style = ss._get_style('semantic', 'success', 'green') if ss else 'green'
        info_style = ss._get_style('semantic', 'info', 'cyan') if ss else 'cyan'
        muted_style_hdr = ss._get_style('semantic', 'muted', 'dim') if ss else 'dim'

        # ILM row content (Label / Icon / Value pattern per ui-standards)
        if isinstance(ilm_results, dict) and ilm_results.get('not_supported'):
            ilm_icon = "🔶"
            ilm_value = "Not supported on this cluster"
            ilm_val_style = warn_style
        elif isinstance(ilm_results, dict) and ilm_results.get('skipped'):
            ilm_icon = "🔶"
            ilm_value = "Skipped (omit --skip-ilm to check)"
            ilm_val_style = muted_style_hdr
        else:
            ec = len(ilm_errors)
            npc = len(ilm_no_policy)
            s3c = len(ilm_s3_managed)
            if ec == 0 and npc == 0:
                ilm_icon = "✅"
                ilm_value = (
                    f"All managed ({s3c} S3-snapshot)" if s3c > 0 else "All indices have ILM policies"
                )
                ilm_val_style = ok_style
            elif ec > 0:
                ilm_icon = "❌"
                parts = [f"{ec} error{'s' if ec != 1 else ''}"]
                if npc > 0:
                    parts.append(f"{npc} unmanaged")
                if s3c > 0:
                    parts.append(f"{s3c} S3-snapshot")
                ilm_value = ", ".join(parts)
                ilm_val_style = err_style
            elif npc > 0:
                ilm_icon = "🔶"
                parts = [f"{npc} without policy"]
                if s3c > 0:
                    parts.append(f"{s3c} S3-snapshot")
                ilm_value = ", ".join(parts)
                ilm_val_style = warn_style
            else:
                ilm_icon = "✅"
                ilm_value = f"{s3c} S3-snapshot managed"
                ilm_val_style = ok_style

        if len(no_replica_indices) == 0:
            rep_icon, rep_value, rep_val_style = "✅", "All indices have replicas", ok_style
        else:
            nrep = len(no_replica_indices)
            rep_icon, rep_value, rep_val_style = "🔶", f"{nrep} index{'es' if nrep != 1 else ''} without replicas", warn_style

        if len(large_shards) == 0:
            sh_icon, sh_value, sh_val_style = "✅", f"None over {max_shard_size} GB", ok_style
        else:
            ns = len(large_shards)
            sh_icon, sh_value, sh_val_style = "🔶", f"{ns} shard{'s' if ns != 1 else ''} over {max_shard_size} GB", warn_style

        # Top panel: centered status line (bold green / yellow / red) per ui-standards
        if has_ilm_errors:
            body_line = "❌ ILM Errors Detected — Review Details Below"
            body_style = "bold red"
            title_border = err_style
        elif has_issues:
            body_line = "🔶 Health Warnings — Review Details Below"
            body_style = "bold yellow"
            title_border = warn_style
        else:
            body_line = "✅ Cluster Healthy — All Checks Passed"
            body_style = "bold green"
            title_border = ss._get_style('table_styles', 'border_style', 'cyan') if ss else 'cyan'

        ts = ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'

        # Subtitle: key stats with themed colors (ui-standards §1)
        subtitle_rich = Text()
        subtitle_rich.append("Cluster: ", style="default")
        subtitle_rich.append(cluster_name, style=info_style)
        subtitle_rich.append(" | ", style="default")
        subtitle_rich.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), style=muted_style_hdr)
        if isinstance(ilm_results, dict) and ilm_results.get('skipped'):
            subtitle_rich.append(" | ILM: ", style="default")
            subtitle_rich.append("skipped", style=muted_style_hdr)
        elif isinstance(ilm_results, dict) and ilm_results.get('not_supported'):
            subtitle_rich.append(" | ILM: ", style="default")
            subtitle_rich.append("n/a", style=muted_style_hdr)
        else:
            subtitle_rich.append(" | ILM err: ", style="default")
            subtitle_rich.append(str(len(ilm_errors)), style=err_style if len(ilm_errors) else ok_style)
            subtitle_rich.append(" | Unmanaged: ", style="default")
            subtitle_rich.append(str(len(ilm_no_policy)), style=warn_style if len(ilm_no_policy) else ok_style)
            subtitle_rich.append(" | S3-managed: ", style="default")
            subtitle_rich.append(str(len(ilm_s3_managed)), style=info_style)
        subtitle_rich.append(" | Replicas: ", style="default")
        subtitle_rich.append(
            "OK" if len(no_replica_indices) == 0 else str(len(no_replica_indices)),
            style=ok_style if not no_replica_indices else warn_style,
        )
        subtitle_rich.append(" | Shards: ", style="default")
        subtitle_rich.append(
            "OK" if len(large_shards) == 0 else str(len(large_shards)),
            style=ok_style if not large_shards else warn_style,
        )

        # Inner key-value table — ui-standards §4 (Label bold, icon width=3, value)
        status_inner = Table(show_header=False, box=None, padding=(0, 1))
        status_inner.add_column("Label", style="bold", no_wrap=True)
        status_inner.add_column("Icon", justify="left", width=3)
        status_inner.add_column("Value", no_wrap=False)
        status_inner.add_row("ILM:", ilm_icon, Text(ilm_value, style=ilm_val_style))
        status_inner.add_row("Replicas:", rep_icon, Text(rep_value, style=rep_val_style))
        status_inner.add_row(f"Shards (>{max_shard_size} GB):", sh_icon, Text(sh_value, style=sh_val_style))

        title_body = Group(
            Text(body_line, style=body_style, justify="center"),
            Text(""),
            status_inner,
        )

        title_panel = Panel(
            title_body,
            title=f"[{ts}]🏥 Cluster Health Check Report[/{ts}]",
            subtitle=subtitle_rich,
            border_style=title_border,
            padding=(1, 2),
            expand=True,
        )

        # Display header
        print()
        emit_panel(title_panel)

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
                padding=(1, 2),
                expand=True,
            )
            panels.append(info_panel)
        elif isinstance(ilm_results, dict) and ilm_results.get('not_supported'):
            # Show info panel for unsupported ILM
            info_text = f"🔵 {ilm_results.get('reason', 'ILM is not supported on this cluster')}\n\nThis cluster may be running an older version of Elasticsearch or have ILM disabled."
            info_panel = Panel(
                Text(info_text, style="bright_blue", justify="left"),
                title="🔵 ILM Not Available",
                border_style="blue",
                padding=(1, 2),
                expand=True,
            )
            panels.append(info_panel)
        elif ilm_errors or ilm_no_policy or ilm_s3_managed or show_details:
            # ILM Errors Panel
            if ilm_errors:
                error_table = Table(
                    box=self.es_client.style_system.get_table_box(),
                    show_header=True,
                    header_style=self.es_client.style_system.get_semantic_style("primary"),
                    expand=True,
                    padding=(0, 1),
                )
                error_table.add_column("Index", style="cyan", no_wrap=True, max_width=28, overflow="ellipsis")
                error_table.add_column("Error", style="red", overflow="fold", ratio=2)
                error_table.add_column("Policy", style="yellow", max_width=22, overflow="ellipsis")
                error_table.add_column("Phase", style="green", max_width=10)
                error_table.add_column("Action", style="blue", max_width=14)

                # Sort error indices alphabetically for better readability
                sorted_errors = sorted(ilm_errors, key=lambda x: x.get('index', ''))
                for error in sorted_errors:
                    policy = error.get('policy', 'Unknown')
                    phase = error.get('phase', 'Unknown')
                    action = error.get('action', 'Unknown')
                    step_info = error.get('step_info', {})
                    error_reason = step_info.get('reason', 'Unknown error') if isinstance(step_info, dict) else 'Unknown error'
                    if len(error_reason) > 600:
                        error_reason = error_reason[:597] + "..."

                    error_table.add_row(
                        error['index'],
                        error_reason,
                        policy,
                        phase,
                        action
                    )

                error_panel = Panel(
                    error_table,
                    title=f"❌ ILM Errors ({len(ilm_errors)} indices)",
                    border_style="red",
                    padding=(1, 2),
                    expand=True,
                )
                panels.append(error_panel)

            # Combined issues panel — one index per line, centered
            if ilm_no_policy or no_replica_indices:
                ss = self.es_client.style_system
                warning_style = ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'
                primary_style = ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan'
                muted_style = ss._get_style('semantic', 'muted', 'dim') if ss else 'dim'

                combined = Table.grid(padding=(0, 0))
                combined.add_column(justify="left")

                if ilm_no_policy:
                    combined.add_row(Text(f"🔶 Unmanaged Indices ({len(ilm_no_policy)})", style=warning_style))
                    combined.add_row(Rule(style=warning_style))

                    sorted_no_policy = sorted(ilm_no_policy, key=lambda x: x.get('index', ''))
                    display_list = sorted_no_policy if show_details else sorted_no_policy[:ilm_display_limit]
                    remainder = len(ilm_no_policy) - len(display_list)

                    name_grid = Table.grid(padding=(0, 0))
                    name_grid.add_column(style=primary_style, no_wrap=True)
                    for item in display_list:
                        name_grid.add_row(item['index'])
                    if remainder > 0:
                        name_grid.add_row(Text(f"... and {remainder} more", style=muted_style))

                    combined.add_row(name_grid)

                if ilm_no_policy and no_replica_indices:
                    combined.add_row(Text(""))
                    combined.add_row(Rule(style=muted_style))
                    combined.add_row(Text(""))

                if no_replica_indices:
                    combined.add_row(Text(f"📊 Indices Without Replicas ({len(no_replica_indices)})", style=warning_style))
                    combined.add_row(Rule(style=warning_style))

                    rep_grid = Table.grid(padding=(0, 3))
                    rep_grid.add_column(style=primary_style, no_wrap=True)
                    rep_grid.add_column(style=muted_style, no_wrap=True)

                    shown_count = 0
                    for index_info in no_replica_indices:
                        if not show_details and shown_count >= 10:
                            rep_grid.add_row(Text(f"... and {len(no_replica_indices) - shown_count} more", style=muted_style), "")
                            break
                        creation_date = index_info.get('creation_date', 'Unknown')
                        if creation_date not in ('Unknown', 'N/A'):
                            try:
                                import datetime as dt
                                creation_date = dt.datetime.fromtimestamp(int(creation_date) / 1000).strftime('%Y-%m-%d %H:%M')
                            except (ValueError, TypeError):
                                pass
                        rep_grid.add_row(index_info['index'], f"created {creation_date}")
                        shown_count += 1

                    combined.add_row(rep_grid)

                issues_panel = Panel(
                    combined,
                    title=f"[{warning_style}]Issues Found[/{warning_style}]",
                    border_style=warning_style,
                    padding=(1, 2),
                    expand=True,
                )
                panels.append(issues_panel)

            # S3-Snapshot Managed Panel
            if ilm_s3_managed:
                s3_table = Table(
                    box=self.es_client.style_system.get_table_box(),
                    show_header=True,
                    header_style=self.es_client.style_system.get_semantic_style("primary"),
                    expand=True,
                    padding=(0, 1),
                )
                s3_table.add_column("Index", style="cyan", ratio=1)
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
                    padding=(1, 2),
                    expand=True,
                )
                panels.append(s3_panel)

        # Large Shards Panel
        if large_shards or show_details:
            # Show detailed shard allocation issues panel
            shard_table = Table(
                box=self.es_client.style_system.get_table_box(),
                show_header=True,
                header_style=self.es_client.style_system.get_semantic_style("primary"),
                expand=True,
                padding=(0, 1),
            )
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
                    padding=(1, 2),
                    expand=True,
                )
                panels.append(shard_panel)

        # Display all panels
        if panels:
            print()
            for panel in panels:
                emit_panel(panel)

        # Footer — recommendations + count in one styled panel
        if has_issues:
            recommendations = []
            if ilm_errors:
                recommendations.append(("❌", "Fix ILM errors to ensure proper index lifecycle management"))
            if ilm_no_policy:
                recommendations.append(("🔶", "Attach ILM policies to unmanaged indices"))
            if no_replica_indices:
                recommendations.append(("🔶", "Add replicas to indices for high availability"))
            if large_shards:
                recommendations.append(("🔶", f"Break down shards larger than {max_shard_size}GB"))

            warning_count = (len(no_replica_indices) > 0) + (len(large_shards) > 0) + (len(ilm_no_policy) > 0)
            error_count = len(ilm_errors)

            ss = self.es_client.style_system
            error_style = ss._get_style('semantic', 'error', 'red') if ss else 'red'
            warning_style = ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'
            success_style = ss._get_style('semantic', 'success', 'green') if ss else 'green'
            muted_style = ss._get_style('semantic', 'muted', 'dim') if ss else 'dim'
            primary_style = ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan'
            border_color = error_style if error_count > 0 else warning_style

            rec_grid = Table.grid(padding=(0, 0))
            rec_grid.add_column(justify="left")

            # Count summary line
            parts = []
            if error_count > 0:
                parts.append(Text(f"{error_count} error{'s' if error_count != 1 else ''}", style=error_style))
            if warning_count > 0:
                parts.append(Text(f"{warning_count} warning{'s' if warning_count != 1 else ''}", style=warning_style))

            count_line = Text()
            for i, part in enumerate(parts):
                count_line.append_text(part)
                if i < len(parts) - 1:
                    count_line.append(" and ", style=muted_style)
            count_line.append(" require attention", style=muted_style)
            rec_grid.add_row(count_line)
            rec_grid.add_row(Rule(style=border_color))
            rec_grid.add_row(Text(""))

            action_grid = Table.grid(padding=(0, 2))
            action_grid.add_column(justify="left", width=3)
            action_grid.add_column(style=primary_style, no_wrap=False, ratio=1)
            for icon, msg in recommendations:
                action_grid.add_row(Text(icon), Text(msg, style=primary_style))

            rec_grid.add_row(action_grid)

            emit_panel(Panel(
                rec_grid,
                title=f"[{warning_style}]Recommendations[/{warning_style}]",
                border_style=border_color,
                padding=(1, 2),
                expand=True,
            ))
        else:
            ss = self.es_client.style_system
            success_style = ss._get_style('semantic', 'success', 'green') if ss else 'green'
            emit_panel(Panel(
                Text("No issues found. Your cluster appears to be healthy.", style="bold green", justify="center"),
                title=f"[{success_style}]All Clear[/{success_style}]",
                border_style=success_style,
                padding=(1, 2),
                expand=True,
            ))

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
