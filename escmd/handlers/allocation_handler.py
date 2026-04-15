"""
AllocationHandler - Handles cluster allocation and node exclusion operations

This module contains handlers for:
- allocation: Cluster-level shard allocation management (enable, disable, exclude operations)
- exclude: Index-level exclusion from specific nodes
- exclude-reset: Reset index exclusion settings
"""

from .base_handler import BaseHandler
import json


class AllocationHandler(BaseHandler):
    """Handler for allocation and exclusion operations."""

    def handle_allocation(self):
        """Handle cluster-level allocation management operations."""
        # Handle main allocation actions
        if not hasattr(self.args, 'allocation_action') or self.args.allocation_action is None:
            # Default to display if no action specified
            format_type = getattr(self.args, 'format', 'table')
            if format_type == 'json':
                settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                import json
                self.es_client.pretty_print_json(settings)
            else:
                self.es_client.print_enhanced_allocation_settings()
            return

        if self.args.allocation_action == "enable":
            success = self.es_client.change_shard_allocation('all')
            if success:
                self.es_client.show_message_box("Success", "✅ Successfully enabled shard allocation (all shards).", message_style="bold white", panel_style="green")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                    import json
                    self.es_client.pretty_print_json(settings)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                self.es_client.show_message_box("Error", "❌ An ERROR occurred trying to enable allocation", message_style="bold white", panel_style="red")
                exit(1)
            return

        elif self.args.allocation_action == "disable":
            success = self.es_client.change_shard_allocation('primaries')
            if success:
                self.es_client.show_message_box("Success", "🔶 Successfully disabled shard allocation (primaries only).\nReplica shards will not be allocated or moved.", message_style="bold white", panel_style="yellow")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                    import json
                    self.es_client.pretty_print_json(settings)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                self.es_client.show_message_box("Error", "❌ An ERROR occurred trying to disable allocation", message_style="bold white", panel_style="red")
                exit(1)
            return

        elif self.args.allocation_action == "exclude":
            # Handle exclude subcommands
            if not hasattr(self.args, 'exclude_action') or self.args.exclude_action is None:
                self.es_client.show_message_box("Error", "No exclude action specified. Use 'add', 'remove', or 'reset'.", message_style="bold white", panel_style="red")
                return

            if self.args.exclude_action == "add":
                if not hasattr(self.args, 'hostname') or not self.args.hostname:
                    self.es_client.show_message_box("Error", "Hostname is required for exclude add operation", message_style="bold white", panel_style="red")
                    return

                hostname = self.args.hostname

                # Get current exclusions
                current_exclusions = self._get_current_exclusions()

                # Check if hostname is already excluded
                if hostname in current_exclusions:
                    excluded_hosts_list = "\n".join([f"  • {host}" for host in current_exclusions])
                    self.es_client.show_message_box("Info", f"🔵 Host '{hostname}' is already in the exclusion list.\n\nCurrently excluded hosts:\n{excluded_hosts_list}", message_style="bold white", panel_style="blue")
                    return

                # Add hostname to exclusion list
                updated_exclusions = current_exclusions + [hostname]

                # Apply updated exclusions
                success = self._set_exclusions(updated_exclusions)
                if success:
                    excluded_hosts_list = "\n".join([f"  • {host}" for host in updated_exclusions])
                    self.es_client.show_message_box("Success", f"✅ Successfully excluded node '{hostname}' from allocation.\nShards will be moved away from this node.\n\nCurrently excluded hosts:\n{excluded_hosts_list}", message_style="bold white", panel_style="green")
                    # Show updated settings
                    format_type = getattr(self.args, 'format', 'table')
                    if format_type == 'json':
                        settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                        import json
                        self.es_client.pretty_print_json(settings)
                    else:
                        self.es_client.print_enhanced_allocation_settings()
                else:
                    self.es_client.show_message_box("Error", f"❌ Failed to exclude node '{hostname}' from allocation", message_style="bold white", panel_style="red")
                    exit(1)
                return

            elif self.args.exclude_action == "remove":
                if not hasattr(self.args, 'hostname') or not self.args.hostname:
                    self.es_client.show_message_box("Error", "Hostname is required for exclude remove operation", message_style="bold white", panel_style="red")
                    return
                self._handle_allocation_remove()
                return

            elif self.args.exclude_action == "reset":
                # Get current exclusions to show what will be reset
                current_exclusions = self._get_current_exclusions()

                if not current_exclusions:
                    self.es_client.show_message_box("🔵  Info", " No hosts are currently excluded from allocation.\nNothing to reset.", message_style="bold white", panel_style="blue")
                    return

                # Check if confirmation bypass flag is used
                if not getattr(self.args, 'yes_i_really_mean_it', False):
                    # Show warning and require confirmation
                    excluded_hosts_list = "\n".join([f"  • {host}" for host in current_exclusions])
                    warning_message = f"""🔶  WARNING: This will reset ALL node allocation exclusions!

Currently excluded hosts:
{excluded_hosts_list}

This action will:
• Remove all node exclusions from the cluster
• Allow shard allocation on ALL nodes
• Potentially cause significant shard movement

This is a cluster-wide operation that cannot be undone easily."""

                    self.es_client.show_message_box("WARNING", warning_message, message_style="bold yellow", panel_style="red")

                    # Require confirmation
                    confirmation = input("\nType 'RESET' to confirm this cluster-wide reset: ").strip()

                    if confirmation != 'RESET':
                        self.es_client.show_message_box("Cancelled", "❌ Reset operation cancelled. No changes made.", message_style="bold white", panel_style="yellow")
                        return

                success = self.es_client.reset_node_allocation_exclusion()
                if success:
                    self.es_client.show_message_box("Success", "✅ Successfully reset node allocation exclusions.\nAll nodes are now available for allocation.", message_style="bold white", panel_style="green")
                    # Show updated settings
                    format_type = getattr(self.args, 'format', 'table')
                    if format_type == 'json':
                        settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                        import json
                        self.es_client.pretty_print_json(settings)
                    else:
                        self.es_client.print_enhanced_allocation_settings()
                else:
                    self.es_client.show_message_box("Error", "❌ An ERROR occurred trying to reset node allocation exclusion", message_style="bold white", panel_style="red")
                    exit(1)
                return

        elif self.args.allocation_action == "explain":
            self._handle_allocation_explain()
            return
        else:
            self.es_client.show_message_box("Error", f"Unknown allocation action: {self.args.allocation_action}", message_style="bold white", panel_style="red")

    def handle_exclude(self):
        """Handle index-level exclusion from specific nodes."""
        if not self.args.indice or not self.args.server:
            self._show_exclude_help()
            return
        self._process_exclude()

    def handle_exclude_reset(self):
        """Handle resetting index exclusion settings."""
        if not getattr(self.args, 'indice', None):
            self._show_exclude_reset_help()
            return
        self._process_exclude_reset()

    def _show_exclude_reset_help(self):
        """Display help screen for exclude-reset command."""
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
            Text("Run ./escmd.py exclude-reset <index>", style="bold white"),
            title=f"[{title_style}]🔄 Exclude Reset[/{title_style}]",
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
            ("exclude-reset <index>", "Reset exclusion settings for an index", "exclude-reset .ds-aex10-c01-logs-2025.04.03-000732"),
            ("exclude-reset <index>", "Reset by simple index name", "exclude-reset my-index-001"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Related ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        related = [
            ("exclude <index> -s <host>", "Exclude index from a specific host", "exclude .ds-logs-000732 -s ess01"),
            ("indice <index>", "View index details", "indice my-index-001"),
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

    def _handle_allocation_remove(self):
        """Remove a specific host from the cluster-wide exclusion list."""
        hostname = self.args.hostname

        # Get current exclusions
        current_exclusions = self._get_current_exclusions()

        if not current_exclusions:
            self.es_client.show_message_box("Info", "🔵 No hosts are currently excluded from allocation", message_style="bold white", panel_style="blue")
            return

        # Check if hostname is in exclusion list
        if hostname not in current_exclusions:
            excluded_hosts_list = "\n".join([f"  • {host}" for host in current_exclusions])
            self.es_client.show_message_box("Info", f"🔵 Host '{hostname}' is not in the exclusion list.\n\nCurrently excluded hosts:\n{excluded_hosts_list}", message_style="bold white", panel_style="blue")
            return

        # Remove hostname from list
        updated_exclusions = [host for host in current_exclusions if host != hostname]

        # Apply updated exclusions
        if updated_exclusions:
            # Set exclusions with remaining hosts
            success = self._set_exclusions(updated_exclusions)
            if success:
                excluded_hosts_list = "\n".join([f"  • {host}" for host in updated_exclusions])
                self.es_client.show_message_box("Success", f"✅ Successfully removed '{hostname}' from exclusion list.\n\nRemaining excluded hosts:\n{excluded_hosts_list}", message_style="bold white", panel_style="green")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                    import json
                    self.es_client.pretty_print_json(settings)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                self.es_client.show_message_box("Error", f"❌ Failed to remove '{hostname}' from exclusion list", message_style="bold white", panel_style="red")
        else:
            # Reset if no hosts remain
            success = self._reset_all_exclusions()
            if success:
                self.es_client.show_message_box("Success", f"✅ Successfully removed '{hostname}' from exclusion list.\n\nNo hosts remain excluded - all nodes are available for allocation.", message_style="bold white", panel_style="green")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                    import json
                    self.es_client.pretty_print_json(settings)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                self.es_client.show_message_box("Error", f"❌ Failed to remove '{hostname}' from exclusion list", message_style="bold white", panel_style="red")

    def _handle_allocation_explain(self):
        """
        Handle allocation explain command.
        Provides detailed allocation information for a specific index/shard.
        Automatically detects unassigned shards and explains them.
        """
        try:
            index_name = self.args.index
            shard_number = getattr(self.args, 'shard', None)
            explicit_primary = hasattr(self.args, 'primary') and self.args.primary

            # Gather shard overview data for the index
            shard_overview = self._build_shard_overview(index_name)

            # If user explicitly specified --primary or a shard number, do a single explain
            if explicit_primary or shard_number is not None:
                if shard_number is None:
                    shard_number = 0
                is_primary = explicit_primary if explicit_primary else True

                explain_result = self.es_client.get_enhanced_allocation_explain(index_name, shard_number, is_primary)
                explain_result['shard_overview'] = shard_overview

                if self.args.format == 'json':
                    self.es_client.pretty_print_json(explain_result)
                else:
                    self.es_client.print_allocation_explain_results(explain_result)
                return

            # Auto-detect: find all shards for this index and prefer unassigned ones
            index_shards = shard_overview.get('_raw_shards', [])

            if not index_shards:
                # No shard info available, fall back to primary shard 0
                explain_result = self.es_client.get_enhanced_allocation_explain(index_name, 0, True)
                explain_result['shard_overview'] = shard_overview
                if self.args.format == 'json':
                    self.es_client.pretty_print_json(explain_result)
                else:
                    self.es_client.print_allocation_explain_results(explain_result)
                return

            # Find unassigned shards (UNASSIGNED, INITIALIZING, RELOCATING)
            problem_shards = [s for s in index_shards if s.get('state') in ('UNASSIGNED', 'INITIALIZING', 'RELOCATING')]

            if problem_shards:
                shards_to_explain = problem_shards
            else:
                shards_to_explain = [{'shard': '0', 'prirep': 'p'}]

            results = []
            for shard in shards_to_explain:
                s_num = int(shard.get('shard', 0))
                s_primary = shard.get('prirep', 'p') == 'p'
                result = self.es_client.get_enhanced_allocation_explain(index_name, s_num, s_primary)
                result['shard_overview'] = shard_overview
                results.append(result)

            if self.args.format == 'json':
                if len(results) == 1:
                    self.es_client.pretty_print_json(results[0])
                else:
                    self.es_client.pretty_print_json(results)
            else:
                for result in results:
                    self.es_client.print_allocation_explain_results(result)

        except Exception as e:
            self.es_client.show_message_box("Error", f"Failed to explain allocation for {self.args.index}: {str(e)}", message_style="bold white", panel_style="red")

    def _build_shard_overview(self, index_name):
        """Build a shard overview dict for the given index."""
        overview = {
            'health': 'unknown',
            'total_shards': 0,
            'primary_count': 0,
            'replica_count': 0,
            'states': {},
            'nodes': {},
            '_raw_shards': [],
        }

        try:
            shards_data = self.es_client.get_shards_as_dict()
            index_shards = [s for s in shards_data if s.get('index') == index_name]
            overview['_raw_shards'] = index_shards
            overview['total_shards'] = len(index_shards)

            for shard in index_shards:
                if shard.get('prirep') == 'p':
                    overview['primary_count'] += 1
                else:
                    overview['replica_count'] += 1

                state = shard.get('state', 'UNKNOWN')
                overview['states'][state] = overview['states'].get(state, 0) + 1

                node = shard.get('node') or 'unassigned'
                overview['nodes'][node] = overview['nodes'].get(node, 0) + 1
        except Exception:
            pass

        # Get index health
        try:
            indices_data = self.es_client.filter_indices(pattern=None, status=None)
            for idx in indices_data:
                if idx.get('index') == index_name:
                    overview['health'] = idx.get('health', 'unknown')
                    break
        except Exception:
            pass

        return overview

    def _get_current_exclusions(self):
        """Get list of currently excluded hosts from both persistent and transient settings."""
        try:
            settings = self.es_client.es.cluster.get_settings()

            # Check transient settings
            transient_exclusions = []
            transient_setting = settings.get('transient', {}).get('cluster', {}).get('routing', {}).get('allocation', {}).get('exclude', {}).get('_name', '')
            if transient_setting:
                transient_exclusions = [host.strip() for host in transient_setting.split(',') if host.strip()]

            # Check persistent settings
            persistent_exclusions = []
            persistent_setting = settings.get('persistent', {}).get('cluster', {}).get('routing', {}).get('allocation', {}).get('exclude', {}).get('_name', '')
            if persistent_setting:
                persistent_exclusions = [host.strip() for host in persistent_setting.split(',') if host.strip()]

            # Combine and deduplicate
            all_exclusions = list(set(transient_exclusions + persistent_exclusions))
            return all_exclusions

        except Exception as e:
            print(f"Error getting current exclusions: {str(e)}")
            return []

    def _set_exclusions(self, hostnames):
        """Set exclusions to specific list of hostnames."""
        try:
            exclusion_string = ','.join(hostnames)
            settings = {
                "transient": {
                    "cluster.routing.allocation.exclude._name": exclusion_string
                }
            }
            self.es_client.es.cluster.put_settings(body=settings)
            return True
        except Exception as e:
            print(f"Error setting exclusions: {str(e)}")
            return False

    def _reset_all_exclusions(self):
        """Reset all exclusions in both persistent and transient settings."""
        try:
            settings = {
                "persistent": {
                    "cluster.routing.allocation.exclude._name": None,
                    "cluster.routing.allocation.exclude._ip": None,
                    "cluster.routing.allocation.exclude._host": None
                },
                "transient": {
                    "cluster.routing.allocation.exclude._name": None,
                    "cluster.routing.allocation.exclude._ip": None,
                    "cluster.routing.allocation.exclude._host": None
                }
            }
            self.es_client.es.cluster.put_settings(body=settings)
            return True
        except Exception as e:
            print(f"Error resetting exclusions: {str(e)}")
            return False

    def _show_exclude_help(self):
        """Display help screen for exclude command."""
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
            Text("Run ./escmd.py exclude <index> -s <server>", style="bold white"),
            title=f"[{title_style}]🚫 Index Exclusion[/{title_style}]",
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
        table.add_column("Command / Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("exclude <index> -s <host>", "Exclude index from a specific host", "exclude .ds-logs-2025.04.03-000732 -s ess01"),
            ("exclude-reset <index>", "Reset exclusion settings for an index", "exclude-reset .ds-logs-2025.04.03-000732"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Cluster-Level ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        cluster_rows = [
            ("allocation exclude add <host>", "Exclude entire node from allocation", "allocation exclude add node-3"),
            ("allocation exclude remove <host>", "Remove node exclusion", "allocation exclude remove node-3"),
            ("allocation exclude reset", "Reset all node exclusions", "allocation exclude reset"),
        ]
        for i, (cmd, desc, ex) in enumerate(cluster_rows):
            table.add_row(
                Text(cmd, style=ss._get_style('semantic', 'secondary', 'magenta')),
                desc,
                Text(f"./escmd.py {ex}", style=muted_style),
                style=ss.get_zebra_style(i) if ss else None,
            )

        console.print()
        console.print(header_panel)
        console.print()
        console.print(table)
        console.print()

    def _process_exclude(self):
        """Process index exclusion from specific server."""
        args_server = self.args.server[0]
        cluster_active_indices = self.es_client.get_indices_stats(pattern=None, status=None)

        if not self.es_client.find_matching_index(cluster_active_indices, self.args.indice):
            self.es_client.show_message_box('ERROR', f"No such indice found: {self.args.indice}", message_style="white", panel_style="white")
            exit(1)

        cluster_shards = self.es_client.get_shards_stats(pattern='*')
        indice_server_fullname = self.es_client.find_matching_node(cluster_shards, self.args.indice, args_server)

        if not indice_server_fullname:
            self.es_client.show_message_box('ERROR', f"ERROR: No matching Shard for {self.args.indice} on Server {args_server}", message_style="white", panel_style="white")
            exit(1)

        response = self.es_client.exclude_index_from_host(self.args.indice, indice_server_fullname)
        if response:
            self.es_client.show_message_box('SUCCESS', f"Indice: {self.args.indice}\nHost: {indice_server_fullname}")
        else:
            self.es_client.show_message_box('ERROR', "An error has occured trying to exclude indice from host.")
            exit(1)

    def _process_exclude_reset(self):
        """Process resetting index exclusion settings."""
        from rich.panel import Panel
        from rich.text import Text

        ss = self.es_client.style_system
        ts = ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'
        indice_name = self.args.indice

        response, message = self.es_client.exclude_index_reset(indice_name)
        if response:
            border = ss._get_style('table_styles', 'border_style', 'cyan') if ss else 'cyan'
            panel = Panel(
                Text(f"✅ Successfully removed exclude settings from {indice_name}", style="bold green", justify="center"),
                title=f"[{ts}]🔄 Exclude Reset[/{ts}]",
                border_style=border,
                padding=(1, 2)
            )
            print()
            self.console.print(panel)
            print()
        else:
            panel = Panel(
                Text(f"❌ {message}", style="bold red", justify="center"),
                title=f"[{ts}]🔄 Exclude Reset[/{ts}]",
                border_style="red",
                padding=(1, 2)
            )
            print()
            self.console.print(panel)
            print()
            exit(1)
