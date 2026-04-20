"""
ILM (Index Lifecycle Management) display renderer for escmd.

This module contains rich console rendering methods for ILM data display.
"""

from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table
from rich.console import Console
from rich import box


class ILMRenderer:
    """Renderer for ILM display operations."""

    def __init__(self, es_client):
        self.es_client = es_client
        self.console = Console()

    def _border(self, fallback: str = "cyan") -> str:
        """Return the theme border style."""
        tm = getattr(self.es_client, 'theme_manager', None)
        if tm:
            return tm.get_theme_styles().get("border_style", fallback)
        return fallback

    def _title_style(self, fallback: str = "bold white") -> str:
        """Return the theme panel title style."""
        tm = getattr(self.es_client, 'theme_manager', None)
        if tm:
            return tm.get_themed_style("panel_styles", "title", fallback)
        return fallback

    def _sem(self, semantic: str, fallback: str = "white") -> str:
        """Return a semantic style from the style system."""
        ss = getattr(self.es_client, 'style_system', None)
        if ss:
            return ss.get_semantic_style(semantic)
        return fallback

    def print_enhanced_ilm_status(self):
        """Display comprehensive ILM status in multi-panel format."""
        try:
            ilm_data = self.es_client.ilm_commands.get_ilm_status()

            # Get style system for semantic styling
            style_system = self.es_client.style_system

            # Extract phase counts for colorized display
            phase_counts = ilm_data['phase_counts']

            # Create colorized subtitle with theme-based styling for statistics
            from rich.text import Text
            subtitle_rich = Text()

            # Operation Mode with appropriate color
            subtitle_rich.append("Mode: ", style="default")
            if ilm_data['operation_mode'] == 'RUNNING':
                subtitle_rich.append("✅ Running", style=style_system._get_style('semantic', 'success', 'green') if style_system else "green")
            elif ilm_data['operation_mode'] == 'STOPPED':
                subtitle_rich.append("⏸️ Stopped", style=style_system._get_style('semantic', 'warning', 'yellow') if style_system else "yellow")
            else:
                subtitle_rich.append(f"🔶 {ilm_data['operation_mode']}", style=style_system._get_style('semantic', 'error', 'red') if style_system else "red")

            # Policies
            subtitle_rich.append(" | Policies: ", style="default")
            subtitle_rich.append(str(ilm_data['policy_count']), style=style_system._get_style('semantic', 'info', 'cyan') if style_system else "cyan")

            # Total managed
            subtitle_rich.append(" | Managed: ", style="default")
            subtitle_rich.append(str(ilm_data['total_managed']), style=style_system._get_style('semantic', 'primary', 'bright_magenta') if style_system else "bright_magenta")

            # Hot phase (only if > 0)
            if phase_counts.get('hot', 0) > 0:
                subtitle_rich.append(" | Hot: ", style="default")
                subtitle_rich.append(str(phase_counts['hot']), style=style_system._get_style('semantic', 'primary', 'bright_magenta') if style_system else "bright_magenta")

            # Warm phase (only if > 0)
            if phase_counts.get('warm', 0) > 0:
                subtitle_rich.append(" | Warm: ", style="default")
                subtitle_rich.append(str(phase_counts['warm']), style=style_system._get_style('semantic', 'warning', 'yellow') if style_system else "yellow")

            # Cold phase (only if > 0)
            if phase_counts.get('cold', 0) > 0:
                subtitle_rich.append(" | Cold: ", style="default")
                subtitle_rich.append(str(phase_counts['cold']), style=style_system._get_style('semantic', 'secondary', 'bright_blue') if style_system else "bright_blue")

            # Frozen phase (only if > 0)
            if phase_counts.get('frozen', 0) > 0:
                subtitle_rich.append(" | Frozen: ", style="default")
                subtitle_rich.append(str(phase_counts['frozen']), style=style_system._get_style('semantic', 'secondary', 'bright_cyan') if style_system else "bright_cyan")

            # Errors (only if > 0)
            if phase_counts.get('error', 0) > 0:
                subtitle_rich.append(" | Errors: ", style="default")
                subtitle_rich.append(str(phase_counts['error']), style=style_system._get_style('semantic', 'error', 'red') if style_system else "red")

            # Create title panel with colorized subtitle
            if style_system:
                title_panel = Panel(
                    style_system.create_semantic_text(f"📋 Index Lifecycle Management (ILM) Status", "primary", justify="center"),
                    subtitle=subtitle_rich,
                    border_style=style_system._get_style('table_styles', 'border_style', 'cyan'),
                    padding=(1, 2)
                )
            else:
                title_panel = Panel(
                    Text(f"📋 Index Lifecycle Management (ILM) Status", style="bold cyan", justify="center"),
                    subtitle=subtitle_rich,
                    border_style="cyan",
                    padding=(1, 2)
                )

            # Create status overview panel
            from rich.table import Table as InnerTable

            status_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            status_table.add_column("Label", style="bold", no_wrap=True)
            status_table.add_column("Icon", justify="left", width=3)
            status_table.add_column("Value", no_wrap=True)

            # ILM Status
            if ilm_data['operation_mode'] == 'RUNNING':
                status_table.add_row("Operation Mode:", "✅", "Running")
            elif ilm_data['operation_mode'] == 'STOPPED':
                status_table.add_row("Operation Mode:", "🔶", "Stopped")
            else:
                status_table.add_row("Operation Mode:", "❌", ilm_data['operation_mode'])

            status_table.add_row("Total Policies:", "📋", str(ilm_data['policy_count']))
            status_table.add_row("Managed Indices:", "📊", str(ilm_data['total_managed']))
            status_table.add_row("Unmanaged Indices:", "⚪", str(ilm_data['phase_counts']['unmanaged']))

            if ilm_data['has_errors']:
                status_table.add_row("Error Count:", "🔶", str(ilm_data['phase_counts']['error']))

            status_panel = Panel(
                status_table,
                title=f"[{self._title_style()}]📊 ILM Status[/{self._title_style()}]",
                border_style=self._sem("success", "green"),
                padding=(1, 2)
            )

            # Create phase distribution panel
            phase_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            phase_table.add_column("Phase", style="bold", no_wrap=True)
            phase_table.add_column("Icon", justify="left", width=3)
            phase_table.add_column("Count", no_wrap=True)

            phase_icons = {'hot': '🔥', 'warm': '🟡', 'cold': '🧊', 'frozen': '🧊', 'delete': '🗑'}

            for phase, count in ilm_data['phase_counts'].items():
                if count > 0 and phase in phase_icons:
                    phase_table.add_row(
                        f"{phase.title()}:",
                        phase_icons[phase],
                        f"{count:,}"
                    )

            phase_panel = Panel(
                phase_table,
                title=f"[{self._title_style()}]🔄 Phase Distribution[/{self._title_style()}]",
                border_style=self._sem("info", "blue"),
                padding=(1, 2)
            )

            # Create quick actions panel
            actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            actions_table.add_column("Action", style=self._sem("primary", "bold cyan"), no_wrap=True)
            actions_table.add_column("Command", style="dim white")

            actions_table.add_row("List policies:", "./escmd.py ilm policies")
            actions_table.add_row("Policy details:", "./escmd.py ilm policy <name>")
            actions_table.add_row("Check errors:", "./escmd.py ilm errors")
            actions_table.add_row("Explain index:", "./escmd.py ilm explain <index>")
            actions_table.add_row("JSON output:", "./escmd.py ilm status --format json")

            actions_panel = Panel(
                actions_table,
                title=f"[{self._title_style()}]🚀 Quick Actions[/{self._title_style()}]",
                border_style=self._sem("secondary", "magenta"),
                padding=(1, 2)
            )

            # Display everything
            print()
            self.console.print(title_panel)
            print()
            self.console.print(Columns([status_panel, phase_panel], expand=True))
            print()
            self.console.print(actions_panel)
            print()

        except Exception as e:
            self.console.print(f"[red]❌ Error retrieving ILM status: {str(e)}[/red]")

    def print_enhanced_ilm_policies(self):
        """Display ILM policies in enhanced format."""
        policies = self.es_client.ilm_commands.get_ilm_policies()

        if 'error' in policies:
            self.console.print(f"[red]❌ Error retrieving ILM policies: {policies['error']}[/red]")
            return

        # Get cluster name and version for context
        try:
            cluster_info = self.es_client.cluster_commands.get_cluster_info()
            cluster_name = cluster_info.get('cluster_name', 'Unknown')
            cluster_version = cluster_info.get('version', {}).get('number', 'Unknown')
        except Exception:
            cluster_name = 'Unknown'
            cluster_version = 'Unknown'

        # Build cluster info text for subtitle
        if cluster_version != 'Unknown':
            cluster_info_text = f"Cluster: {cluster_name} (v{cluster_version})"
        else:
            cluster_info_text = f"Cluster: {cluster_name}"

        style_system = getattr(self.es_client, 'style_system', None)

        # --- Summary panel (matches template / indices pattern) ---
        total = len(policies)
        policy_word = "Policy" if total == 1 else "Policies"
        status_text = f"✅ {total} ILM {policy_word} Configured"

        subtitle_rich = Text()
        subtitle_rich.append(cluster_info_text, style=self._sem('info', 'cyan'))
        subtitle_rich.append(" | Total: ", style="default")
        subtitle_rich.append(str(total), style=self._sem('primary', 'bright_magenta'))

        border = style_system._get_style('table_styles', 'border_style', 'bright_magenta') if style_system else self._border('bright_magenta')
        title_style = style_system._get_style('semantic', 'primary', 'bold cyan') if style_system else 'bold cyan'

        summary_panel = Panel(
            Text(status_text, style="bold green", justify="center"),
            title=f"[{title_style}]📋 ILM Policies Overview[/{title_style}]",
            subtitle=subtitle_rich,
            border_style=border,
            padding=(1, 2)
        )

        # --- Policies table (standard themed table) ---
        if style_system:
            table = style_system.create_standard_table(title="📋 ILM Policies")
            style_system.add_themed_column(table, "Policy Name", "name", no_wrap=True)
            style_system.add_themed_column(table, "🔥 Hot", "status", justify="center")
            style_system.add_themed_column(table, "🟡 Warm", "status", justify="center")
            style_system.add_themed_column(table, "🧊 Cold", "status", justify="center")
            style_system.add_themed_column(table, "🧊 Frozen", "status", justify="center")
            style_system.add_themed_column(table, "🗑 Delete", "status", justify="center")
        else:
            theme_manager = getattr(self.es_client, 'theme_manager', None)
            from display.style_system import StyleSystem
            _ss = StyleSystem(theme_manager)
            table_box = _ss.get_table_box()
            full_theme = theme_manager.get_full_theme_data() if theme_manager else {}
            table_styles = full_theme.get('table_styles', {})
            header_style = table_styles.get('header_style', 'bold white on dark_blue')
            border_style = table_styles.get('border_style', 'white')

            table = Table(
                show_header=True,
                header_style=header_style,
                expand=True,
                box=table_box,
                border_style=border_style,
                title="📋 ILM Policies",
                title_style="bold bright_white"
            )
            table.add_column("Policy Name", style="cyan", no_wrap=True)
            table.add_column("🔥 Hot", justify="center")
            table.add_column("🟡 Warm", justify="center")
            table.add_column("🧊 Cold", justify="center")
            table.add_column("🧊 Frozen", justify="center")
            table.add_column("🗑 Delete", justify="center")

        success_style = self._sem('success', 'green')
        error_style = self._sem('error', 'red')

        # Sort policies alphabetically for consistent display
        sorted_policies = sorted(policies.items())

        for i, (policy_name, policy_data) in enumerate(sorted_policies):
            policy_def = policy_data.get('policy', {})
            phases = policy_def.get('phases', {})

            def _phase_indicator(phase_name):
                if phase_name in phases:
                    return f"[{success_style}]✅[/{success_style}]"
                return f"[{error_style}]❌[/{error_style}]"

            table.add_row(
                policy_name,
                _phase_indicator('hot'),
                _phase_indicator('warm'),
                _phase_indicator('cold'),
                _phase_indicator('frozen'),
                _phase_indicator('delete'),
                style=style_system.get_zebra_style(i) if style_system else None,
            )

        self.console.print()
        self.console.print(summary_panel)
        self.console.print()
        self.console.print(table)
        self.console.print()

    def print_enhanced_ilm_policy_detail(self, policy_name, show_all_indices=False):
        """Display detailed information for a specific ILM policy with improved readability."""
        policy_data = self.es_client.ilm_commands.get_ilm_policy_detail(policy_name)

        if 'error' in policy_data:
            self.console.print(f"[red]❌ Error retrieving policy '{policy_name}': {policy_data['error']}[/red]")
            return

        # Get cluster name and version for context (same method as indices command)
        try:
            cluster_info = self.es_client.cluster_commands.get_cluster_info()
            cluster_name = cluster_info.get('cluster_name', 'Unknown')
            cluster_version = cluster_info.get('version', {}).get('number', 'Unknown')
        except Exception:
            cluster_name = 'Unknown'
            cluster_version = 'Unknown'

        policy_info = policy_data[policy_name]
        policy_def = policy_info.get('policy', {})
        phases = policy_def.get('phases', {})
        using_indices = policy_info.get('using_indices', [])

        # Analyze phases and indices for summary
        active_phases = list(phases.keys())
        phase_stats = {}
        for index in using_indices:
            phase = index.get('phase', 'unknown')
            phase_stats[phase] = phase_stats.get(phase, 0) + 1

        # Create title panel with enhanced summary including version
        active_phases_str = " → ".join([f"{phase.title()} {self._get_phase_icon(phase)}" for phase in ['hot', 'warm', 'cold', 'frozen', 'delete'] if phase in phases])
        if not active_phases_str:
            active_phases_str = "No phases configured"

        # Build subtitle with cluster info and version
        if cluster_version != 'Unknown':
            cluster_info_text = f"Cluster: {cluster_name} (v{cluster_version})"
        else:
            cluster_info_text = f"Cluster: {cluster_name}"

        # Get style system for themed styling like indices command
        style_system = self.es_client.style_system

        # Create colorized subtitle with theme-based styling
        subtitle_rich = Text()
        subtitle_rich.append(f"{cluster_info_text}", style=style_system._get_style('semantic', 'info', 'cyan'))
        subtitle_rich.append(" | Version: ", style="default")
        subtitle_rich.append(str(policy_info.get('version', 'N/A')), style=style_system._get_style('semantic', 'primary', 'bright_magenta'))
        subtitle_rich.append(" | Lifecycle: ", style="default")
        subtitle_rich.append(active_phases_str, style=style_system._get_style('semantic', 'success', 'green'))
        subtitle_rich.append(" | Managing ", style="default")
        subtitle_rich.append(str(len(using_indices)), style=style_system._get_style('semantic', 'warning', 'yellow'))
        subtitle_rich.append(" indices", style="default")

        title_panel = Panel(
            style_system.create_semantic_text(f"📋 ILM Policy: {policy_name}", "primary", justify="center"),
            subtitle=subtitle_rich,
            border_style=style_system._get_style('table_styles', 'border_style', 'bright_magenta'),
            padding=(1, 2)
        )

        # Create individual phase cards instead of a single table
        phase_panels = []
        phase_order = ['hot', 'warm', 'cold', 'frozen', 'delete']

        for phase_name in phase_order:
            if phase_name in phases:
                phase_config = phases[phase_name]

                # Create phase details table
                phase_table = Table(show_header=False, box=None, padding=(0, 1))
                phase_table.add_column("Detail", style="bold", no_wrap=True, width=12)
                phase_table.add_column("Value", style="white")

                # Get actions with better formatting
                actions = []
                if 'actions' in phase_config:
                    for action_name, action_config in phase_config['actions'].items():
                        action_display = action_name.replace('_', ' ').title()
                        if isinstance(action_config, dict) and action_config:
                            # Show key configuration details
                            config_items = []
                            for key, value in action_config.items():
                                config_items.append(f"{key}: {value}")
                            if config_items:
                                action_display += f" ({', '.join(config_items)})"
                        actions.append(action_display)

                # Add phase information
                phase_table.add_row("Status:", f"✅ Active {self._get_phase_icon(phase_name)}")

                if 'min_age' in phase_config:
                    phase_table.add_row("Trigger:", f"After {phase_config['min_age']}")
                else:
                    phase_table.add_row("Trigger:", "Immediate")

                if actions:
                    phase_table.add_row("Actions:", f"{len(actions)} configured")
                    for i, action in enumerate(actions, 1):
                        phase_table.add_row(f"  └─ Action {i}:", action)
                else:
                    phase_table.add_row("Actions:", "None")

                # Add index count in this phase
                indices_in_phase = phase_stats.get(phase_name, 0)
                if indices_in_phase > 0:
                    phase_table.add_row("Indices:", f"{indices_in_phase} currently in this phase")

                # Create phase panel with appropriate color
                phase_colors = {
                    'hot': 'red',
                    'warm': 'yellow',
                    'cold': 'blue',
                    'frozen': 'cyan',
                    'delete': 'magenta'
                }

                phase_panel = Panel(
                    phase_table,
                    title=f"[bold]{self._get_phase_icon(phase_name)} {phase_name.title()} Phase",
                    border_style=phase_colors.get(phase_name, 'white'),
                    padding=(1, 1)
                )
                phase_panels.append(phase_panel)

        # Create lifecycle flow visualization
        if phase_panels:
            # Group phase panels in rows of 2 for better readability
            flow_content = "📋 **Policy Lifecycle Flow**\n\n"
            configured_phases = [p for p in phase_order if p in phases]

            for i, phase in enumerate(configured_phases):
                arrow = " → " if i < len(configured_phases) - 1 else ""
                flow_content += f"{self._get_phase_icon(phase)} **{phase.title()}**{arrow}"

            flow_panel = Panel(
                Text(flow_content, style="bold white"),
                title=f"[{self._title_style()}]🔄 Lifecycle Overview[/{self._title_style()}]",
                border_style=self._sem("success", "green"),
                padding=(1, 2)
            )

        # Create enhanced indices display with better organization
        if using_indices:
            # Group indices by phase for better readability
            indices_by_phase = {}
            for index in using_indices:
                phase = index.get('phase', 'unknown')
                if phase not in indices_by_phase:
                    indices_by_phase[phase] = []
                indices_by_phase[phase].append(index)

            # Create summary stats
            summary_table = Table(show_header=False, box=None, padding=(0, 1))
            summary_table.add_column("Phase", style="bold", width=12)
            summary_table.add_column("Count", justify="center", width=8)
            summary_table.add_column("Icon", justify="center", width=6)

            for phase in phase_order:
                if phase in indices_by_phase:
                    count = len(indices_by_phase[phase])
                    summary_table.add_row(
                        f"{phase.title()}:",
                        f"{count}",
                        self._get_phase_icon(phase)
                    )

            summary_panel = Panel(
                summary_table,
                title=f"[{self._title_style()}]📊 Indices Distribution by Phase[/{self._title_style()}]",
                border_style=self._sem("info", "blue"),
                padding=(1, 1)
            )

            # Create detailed indices table
            indices_table = Table(
                show_header=True,
                header_style="bold white",
                expand=True,
                box=self.es_client.style_system.get_table_box() if hasattr(self.es_client, 'style_system') else None
            )
            indices_table.add_column("📁 Index Name", style="cyan", no_wrap=False, min_width=40)
            indices_table.add_column("🔄 Phase", justify="center", width=12)
            indices_table.add_column("🔩 Action", style="dim", width=20)
            indices_table.add_column("📊 Status", justify="center", width=10)

            # Sort indices by phase, then by name
            sorted_indices = sorted(using_indices, key=lambda x: (
                phase_order.index(x.get('phase', 'unknown')) if x.get('phase', 'unknown') in phase_order else 999,
                x.get('name', '')
            ))

            # Determine how many indices to show
            indices_to_show = sorted_indices if show_all_indices else sorted_indices[:15]

            current_phase = None
            for index in indices_to_show:
                phase = index.get('phase', 'unknown')

                # Add phase separator for better visual grouping
                if phase != current_phase and len(indices_to_show) > 5:
                    if current_phase is not None:  # Not the first phase
                        indices_table.add_row("", "", "", "")  # Empty separator row
                    current_phase = phase

                phase_display = f"{self._get_phase_icon(phase)} {phase.title()}"
                managed_display = "✅ Managed" if index.get('managed', False) else "🔶 Unmanaged"

                indices_table.add_row(
                    index.get('name', 'Unknown'),
                    phase_display,
                    index.get('action', 'N/A'),
                    managed_display
                )

            # Add "more" indicator with better styling
            if not show_all_indices and len(using_indices) > 15:
                indices_table.add_row(
                    "...",
                    f"[dim]+{len(using_indices) - 15} more[/dim]",
                    "[dim]Use --show-all to see all[/dim]",
                    ""
                )

            # Create enhanced indices panel
            if show_all_indices or len(using_indices) <= 15:
                indices_title = f"📁 All Indices Using This Policy ({len(using_indices)} total)"
            else:
                indices_title = f"📁 Indices Using This Policy (showing 15 of {len(using_indices)})"

            indices_panel = Panel(
                indices_table,
                title=indices_title,
                border_style=self._sem("success", "green"),
                padding=(1, 1)
            )
        else:
            # No indices using this policy
            summary_panel = Panel(
                Text("🔵  This policy is not currently being used by any indices.\n\nTo apply this policy to an index template or data stream, update your index template configuration.",
                     style="dim white", justify="center"),
                title=f"[{self._title_style()}]📊 Policy Usage[/{self._title_style()}]",
                border_style=self._sem("warning", "yellow"),
                padding=(2, 2)
            )
            indices_panel = None

        # Create quick actions with more relevant commands
        actions_table = Table(show_header=False, box=None, padding=(0, 1))
        actions_table.add_column("Action", style="bold magenta", no_wrap=True)
        actions_table.add_column("Command", style="cyan")

        actions_table.add_row("📋 All policies:", "./escmd.py ilm policies")
        actions_table.add_row("📊 ILM status:", "./escmd.py ilm status")
        actions_table.add_row("🔶 Check errors:", "./escmd.py ilm errors")

        if using_indices:
            # Pick a representative index from the largest phase
            largest_phase = max(phase_stats.items(), key=lambda x: x[1])[0] if phase_stats else None
            sample_index = next((idx for idx in using_indices if idx.get('phase') == largest_phase), using_indices[0])
            actions_table.add_row("🔍 Explain index:", f"./escmd.py ilm explain {sample_index['name']}")

            if not show_all_indices and len(using_indices) > 15:
                actions_table.add_row("📋 Show all indices:", f"./escmd.py ilm policy {policy_name} --show-all")

        actions_table.add_row("📄 JSON format:", f"./escmd.py ilm policy {policy_name} --format json")

        actions_panel = Panel(
            actions_table,
            title=f"[{self._title_style()}]🚀 Quick Actions[/{self._title_style()}]",
            border_style=self._sem("secondary", "magenta"),
            padding=(1, 1)
        )

        # Display everything with improved layout
        print()
        self.console.print(title_panel)
        print()

        # Show lifecycle flow if phases exist
        if phase_panels:
            self.console.print(flow_panel)
            print()

            # Display phase panels in a more readable layout
            if len(phase_panels) <= 2:
                # Show side by side for 1-2 phases
                self.console.print(Columns(phase_panels, expand=True))
            elif len(phase_panels) <= 4:
                # Show in 2x2 grid for 3-4 phases
                for i in range(0, len(phase_panels), 2):
                    row_panels = phase_panels[i:i+2]
                    self.console.print(Columns(row_panels, expand=True))
                    if i + 2 < len(phase_panels):  # Add spacing between rows
                        print()
            else:
                # Stack vertically for many phases
                for panel in phase_panels:
                    self.console.print(panel)
            print()

        # Show indices information
        if using_indices:
            self.console.print(summary_panel)
            print()
            if indices_panel:
                self.console.print(indices_panel)
                print()
        else:
            self.console.print(summary_panel)
            print()

        # Actions panel spans full width
        self.console.print(actions_panel)
        print()

    def print_enhanced_ilm_explain(self, index_name):
        """Display ILM explain for specific index."""
        explain_data = self.es_client.ilm_commands.get_ilm_explain(index_name)

        if 'error' in explain_data:
            self.console.print(f"[red]❌ Error explaining ILM for index '{index_name}': {explain_data['error']}[/red]")
            return

        # Check if index exists in the response
        if 'indices' not in explain_data:
            self.console.print(f"[red]❌ No ILM data found for index '{index_name}'[/red]")
            return

        index_info = explain_data.get('indices', {}).get(index_name, {})

        if not index_info:
            self.console.print(f"[red]❌ Index '{index_name}' not found in ILM explain response[/red]")
            return

        # Create title panel
        title_panel = Panel(
            Text(f"📋 ILM Explain: {index_name}", style=self._title_style(), justify="center"),
            border_style=self._border(),
            padding=(1, 2)
        )

        # Create details table
        details_table = Table(show_header=False, box=None, padding=(0, 1))
        details_table.add_column("Property", style="bold", no_wrap=True)
        details_table.add_column("Value", no_wrap=True)

        managed = index_info.get('managed', False)
        details_table.add_row("Managed:", "✅ Yes" if managed else "❌ No")

        if managed:
            details_table.add_row("Policy:", index_info.get('policy', 'N/A'))
            details_table.add_row("Current Phase:", f"{index_info.get('phase', 'N/A')} {self._get_phase_icon(index_info.get('phase', ''))}")
            details_table.add_row("Current Action:", index_info.get('action', 'N/A'))
            details_table.add_row("Current Step:", index_info.get('step', 'N/A'))

            # Check for errors
            if 'step_info' in index_info and 'error' in index_info.get('step_info', {}):
                error_info = index_info['step_info']['error']
                details_table.add_row("Error:", f"❌ {error_info.get('type', 'Unknown')}")
                details_table.add_row("Error Reason:", error_info.get('reason', 'N/A'))

        details_panel = Panel(
            details_table,
            title=f"[{self._title_style()}]📊 ILM Details[/{self._title_style()}]",
            border_style=self._sem("info", "blue"),
            padding=(1, 2)
        )

        print()
        self.console.print(title_panel)
        print()
        self.console.print(details_panel)
        print()

    def print_enhanced_ilm_errors(self):
        """Display indices with ILM errors."""
        errors = self.es_client.ilm_commands.get_ilm_errors()

        if 'error' in errors:
            self.console.print(f"[red]❌ Error retrieving ILM errors: {errors['error']}[/red]")
            return

        # Create title panel — style depends on whether errors exist
        if not errors:
            self.console.print(Panel(
                Text("✅ No ILM errors found!", style=self._sem("success", "bold green"), justify="center"),
                title=f"[{self._title_style()}]🔍 ILM Errors Report[/{self._title_style()}]",
                border_style=self._sem("success", "green"),
                padding=(1, 2)
            ))
            print()
            return

        title_panel = Panel(
            Text(f"🔶 ILM Errors Report", style=self._sem("error", "bold red"), justify="center"),
            subtitle=f"Indices with errors: {len(errors)}",
            border_style=self._sem("error", "red"),
            padding=(1, 2)
        )

        # Create errors table
        table = Table(
            show_header=True,
            header_style=getattr(self.es_client, 'theme_manager', None) and self.es_client.theme_manager.get_theme_styles().get('header_style', 'bold white') or 'bold white',
            expand=True,
            box=self.es_client.style_system.get_table_box() if hasattr(self.es_client, 'style_system') else None
        )
        table.add_column("📋 Index Name", style="cyan", no_wrap=False)
        table.add_column("📋 Policy", style="yellow", width=15)
        table.add_column("🔥 Phase", style="magenta", width=10)
        table.add_column("❌ Error Type", style="red", width=20)
        table.add_column("📝 Error Reason", style="white", no_wrap=False)

        for index_name, index_info in errors.items():
            policy = index_info.get('policy', 'N/A')
            phase = index_info.get('phase', 'N/A')

            error_info = index_info.get('step_info', {}).get('error', {})
            error_type = error_info.get('type', 'Unknown')
            error_reason = error_info.get('reason', 'N/A')

            # Truncate long error reasons
            if len(error_reason) > 50:
                error_reason = f"{error_reason[:47]}..."

            table.add_row(index_name, policy, phase, error_type, error_reason)

        print()
        self.console.print(title_panel)
        print()
        self.console.print(table)
        print()

    def print_ilm_policy_index_patterns(self, policy_name, show_all=False):
        """Display unique index base patterns for all indices managed by a given ILM policy."""
        data = self.es_client.ilm_commands.get_ilm_policy_index_patterns(policy_name)

        if 'error' in data:
            self.console.print(
                f"[red]❌ Error retrieving index patterns for policy '{policy_name}': {data['error']}[/red]"
            )
            return

        total_indices = data['total_indices']
        unique_patterns = data['unique_patterns']
        patterns = data['patterns']

        style_system = getattr(self.es_client, 'style_system', None)

        subtitle_rich = Text()
        subtitle_rich.append("Policy: ", style="default")
        subtitle_rich.append(policy_name, style="bold cyan")
        subtitle_rich.append("  |  Total Indices: ", style="default")
        subtitle_rich.append(str(total_indices), style="bold magenta")
        subtitle_rich.append("  |  Unique Patterns: ", style="default")
        subtitle_rich.append(str(unique_patterns), style="bold green")

        border = (
            style_system._get_style('table_styles', 'border_style', 'cyan')
            if style_system else 'cyan'
        )

        title_panel = Panel(
            Text("📂 ILM Policy Index Pattern Report", style="bold cyan", justify="center"),
            subtitle=subtitle_rich,
            border_style=border,
            padding=(1, 2),
        )

        print()
        self.console.print(title_panel)
        print()

        if not patterns:
            self.console.print(Panel(
                Text(
                    f"🔵  No indices are currently using policy '{policy_name}'.",
                    style="bold yellow",
                    justify="center",
                ),
                border_style="yellow",
                padding=(1, 2),
            ))
            print()
            return

        box_style = (
            style_system.get_table_box()
            if style_system and hasattr(style_system, 'get_table_box')
            else None
        )
        table = Table(
            show_header=True,
            header_style="bold white",
            expand=True,
            box=box_style,
        )
        table.add_column("#", style="dim white", width=4, justify="right")
        table.add_column("📋 Index Pattern", style="cyan", no_wrap=False)
        table.add_column("Count", style="bold magenta", width=7, justify="right")
        table.add_column("Phases", style="yellow", width=30)

        max_show = len(patterns) if show_all else min(len(patterns), 50)
        for idx, entry in enumerate(patterns[:max_show], start=1):
            phase_icons = []
            for phase in entry['phases']:
                icon = self._get_phase_icon(phase)
                phase_icons.append(f"{icon} {phase}")
            phases_str = "  ".join(phase_icons) if phase_icons else "N/A"

            table.add_row(
                str(idx),
                entry['pattern'],
                str(entry['count']),
                phases_str,
            )

        self.console.print(table)

        truncated = len(patterns) - max_show
        if truncated > 0:
            print()
            self.console.print(
                f"[dim]... {truncated} more pattern(s) not shown. Use --show-all to display all.[/dim]"
            )

        print()

    def _get_phase_icon(self, phase):
        """Get icon for ILM phase."""
        phase_icons = {
            'hot': '🔥',
            'warm': '🟡',
            'cold': '🧊',
            'frozen': '🧊',
            'delete': '🗑'
        }
        return phase_icons.get(phase, '❓')
