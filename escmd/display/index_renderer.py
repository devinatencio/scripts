"""
Index rendering utilities for Elasticsearch command-line tool.

This module provides index-related display capabilities including detailed
index information with Rich formatting and comprehensive analysis.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table


class IndexRenderer:
    """
    Handles index-related display rendering with Rich formatting.
    """

    def __init__(self, theme_manager=None, es_client=None):
        """
        Initialize the index renderer.

        Args:
            theme_manager: Optional theme manager for styling
            es_client: ElasticsearchClient instance for data access
        """
        self.theme_manager = theme_manager
        self.es_client = es_client

    def get_themed_style(self, category: str, key: str, default: str) -> str:
        """Get themed style or return default."""
        if self.theme_manager:
            return self.theme_manager.get_themed_style(category, key, default)
        return default

    def print_detailed_indice_info(self, indice_name: str, console=None) -> None:
        """
        Print detailed information about a specific index with Rich formatting

        Args:
            indice_name: Name of the index to display details for
            console: Optional console instance to use for printing
        """
        if console is None:
            console = Console()

        try:
            # Get comprehensive index data
            indices_data = self.es_client.filter_indices(pattern=None, status=None)
            shards_data = self.es_client.get_shards_as_dict()
            cluster_all_settings = self.es_client.get_all_index_settings()

            # Get index mapping for metadata
            try:
                index_mapping = self.es_client.es.indices.get_mapping(index=indice_name)
                mapping_meta = index_mapping[indice_name]['mappings'].get('_meta', {})
            except:
                mapping_meta = {}

            # Find the specific index
            index_info = None
            for index in indices_data:
                if index['index'] == indice_name:
                    index_info = index
                    break

            if not index_info:
                self.es_client.show_message_box("❌ Index Not Found", f"Index '{indice_name}' not found", message_style="bold white", panel_style="red")
                return

            # Get index settings
            index_settings = cluster_all_settings.get(indice_name, {})
            settings = index_settings.get('settings', {}).get('index', {})

            # Filter shards for this index
            index_shards = [shard for shard in shards_data if shard['index'] == indice_name]

            # Determine index type and styling
            is_hot = indice_name in getattr(self.es_client, 'cluster_indices_hot_indexes', [])
            is_frozen = settings.get('frozen', 'false') == 'true'

            # Set theme colors using the theme system
            if is_hot:
                theme_color = self.get_themed_style('panel_styles', 'error', 'bright_red')
                type_indicator = "🔥 Hot Index"
            elif is_frozen:
                theme_color = self.get_themed_style('panel_styles', 'info', 'bright_blue')
                type_indicator = "🧊 Frozen Index"
            else:
                theme_color = self.get_themed_style('panel_styles', 'title', 'bright_cyan')
                type_indicator = "📋 Standard Index"

            # Create title panel
            title_text = Text(f"Index Details: {indice_name}", style=f"bold {theme_color}", justify="center")
            title_panel = Panel(
                title_text,
                subtitle=type_indicator,
                border_style=theme_color,
                padding=(1, 2)
            )

            # Index Overview Panel - Create table for aligned columns
            from rich.table import Table as InnerTable

            health_icon = "🟢" if index_info['health'] == 'green' else "🟡" if index_info['health'] == 'yellow' else "🔴"
            status_icon = "📂" if index_info['status'] == 'open' else "🔒"
            docs_count = f"{int(index_info['docs.count']):,}" if index_info['docs.count'] != '-' else 'N/A'

            overview_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            overview_table.add_column("Label", style="bold", no_wrap=True)
            overview_table.add_column("Icon", justify="left", width=2)
            overview_table.add_column("Value", no_wrap=True)

            overview_table.add_row("Health:", health_icon, str(index_info['health']).title())
            overview_table.add_row("Status:", status_icon, str(index_info['status']).title())
            overview_table.add_row("Documents:", "📊", str(docs_count))
            overview_table.add_row("Primary Shards:", "🔢", str(index_info['pri']))
            overview_table.add_row("Replica Shards:", "📋", str(index_info['rep']))
            overview_table.add_row("Primary Size:", "💾", str(index_info['pri.store.size']))
            overview_table.add_row("Total Size:", "📦", str(index_info['store.size']))

            overview_panel = Panel(
                overview_table,
                title="Overview",
                border_style=self.get_themed_style('panel_styles', 'secondary', 'magenta'),
                padding=(1, 2)
            )

            # Index Settings Panel
            creation_date = settings.get('creation_date', 'Unknown')
            if creation_date != 'Unknown':
                try:
                    import datetime
                    creation_date = datetime.datetime.fromtimestamp(int(creation_date) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            uuid = settings.get('uuid', 'Unknown')
            version = settings.get('version', {}).get('created', 'Unknown')
            number_of_shards = settings.get('number_of_shards', 'Unknown')
            number_of_replicas = settings.get('number_of_replicas', 'Unknown')

            # Get ILM policy information
            ilm_policy = settings.get('lifecycle', {}).get('name', 'None')
            ilm_icon = "📋" if ilm_policy != 'None' else "❌"

            # Get ILM phase if available
            ilm_phase = 'Unknown'
            ilm_phase_icon = ''
            if ilm_policy != 'None':
                try:
                    # Try to get ILM explain info for this index
                    ilm_explain = self.es_client.es.ilm.explain_lifecycle(index=indice_name)
                    if indice_name in ilm_explain['indices']:
                        index_ilm = ilm_explain['indices'][indice_name]
                        phase_name = index_ilm.get('phase', 'Unknown')
                        # Add phase icon
                        phase_icons = {
                            'hot': '🔥',
                            'warm': '🟡',
                            'cold': '🧊',
                            'frozen': '🧊',
                            'delete': '🗑'
                        }
                        ilm_phase_icon = phase_icons.get(phase_name, '❓')
                        ilm_phase = phase_name.title()
                except:
                    pass

            # Index Settings Panel - Create table for aligned columns
            settings_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            settings_table.add_column("Label", style="bold", no_wrap=True)
            settings_table.add_column("Icon", justify="left", width=2)
            settings_table.add_column("Value", no_wrap=True)

            settings_table.add_row("UUID:", "🆔", str(uuid))
            settings_table.add_row("Created:", "📅", str(creation_date))
            settings_table.add_row("Version:", "🔩", str(version))
            settings_table.add_row("ILM Policy:", ilm_icon, str(ilm_policy))
            settings_table.add_row("ILM Phase:", ilm_phase_icon, str(ilm_phase))
            settings_table.add_row("Configured Shards:", "🔢", str(number_of_shards))
            settings_table.add_row("Configured Replicas:", "📋", str(number_of_replicas))

            settings_panel = Panel(
                settings_table,
                title="Settings",
                border_style=self.get_themed_style('panel_styles', 'info', 'blue'),
                padding=(1, 2)
            )

            # Metadata Panel - Display as themed table
            metadata_panel = None
            metadata = mapping_meta
            if metadata:
                # Create metadata table with full theme integration (same pattern as shards table)
                full_theme = self.theme_manager.get_full_theme_data() if self.theme_manager else {}
                table_styles = full_theme.get('table_styles', {})

                # Get table box style from theme
                table_box = table_styles.get('table_box', 'heavy')
                box_style = None
                if table_box == 'heavy':
                    from rich.box import HEAVY
                    box_style = HEAVY
                elif table_box == 'rounded':
                    from rich.box import ROUNDED
                    box_style = ROUNDED
                elif table_box == 'simple':
                    from rich.box import SIMPLE
                    box_style = SIMPLE
                elif table_box == 'double':
                    from rich.box import DOUBLE
                    box_style = DOUBLE
                elif table_box is None or table_box == 'None':
                    box_style = None
                else:
                    from rich.box import HEAVY
                    box_style = HEAVY  # Default fallback

                header_style = table_styles.get('header_style', 'bold bright_white on dark_magenta')
                border_style = table_styles.get('border_style', 'bright_magenta')

                metadata_table = Table(
                    show_header=True,
                    header_style=header_style,
                    border_style=border_style,
                    box=box_style,
                    expand=True
                )

                # Add columns without individual styles - header_style handles all headers
                metadata_table.add_column("Key", no_wrap=True)
                metadata_table.add_column("Value")
                metadata_table.add_column("Type", justify="center", width=10)

                # Recursively flatten nested metadata for table display
                def flatten_metadata(data, prefix=""):
                    rows = []
                    if isinstance(data, dict):
                        for key, value in data.items():
                            full_key = f"{prefix}.{key}" if prefix else key
                            if isinstance(value, (dict, list)) and value:
                                # For complex nested objects, show a summary
                                if isinstance(value, dict):
                                    rows.append((full_key, f"[dim]{len(value)} properties[/dim]", "object"))
                                    rows.extend(flatten_metadata(value, full_key))
                                elif isinstance(value, list):
                                    rows.append((full_key, f"[dim]{len(value)} items[/dim]", "array"))
                                    # For lists, show first few items if they're simple values
                                    for i, item in enumerate(value[:3]):
                                        if not isinstance(item, (dict, list)):
                                            rows.append((f"{full_key}[{i}]", str(item), type(item).__name__))
                                    if len(value) > 3:
                                        rows.append((f"{full_key}[...]", f"[dim]+{len(value)-3} more items[/dim]", "..."))
                            else:
                                # Simple value
                                display_value = str(value) if value is not None else "[dim]null[/dim]"
                                if len(display_value) > 60:
                                    display_value = display_value[:57] + "..."
                                rows.append((full_key, display_value, type(value).__name__))
                    return rows

                metadata_rows = flatten_metadata(metadata)

                # Get themed data cell styles (same pattern as shards table)
                key_style = table_styles.get('metadata_key', {}).get('style', 'bright_cyan')
                value_style = table_styles.get('metadata_value', {}).get('style', 'bright_white')
                type_style = table_styles.get('metadata_type', {}).get('style', 'dim bright_white')

                # Add rows to table with proper themed styling
                for key, value, value_type in metadata_rows:
                    # Style the key based on nesting level
                    key_parts = key.split('.')
                    indent = "  " * (len(key_parts) - 1)
                    display_key = f"{indent}{key_parts[-1]}"

                    metadata_table.add_row(
                        Text(display_key, style=key_style),
                        Text(value, style=value_style),
                        Text(value_type, style=type_style)
                    )

                metadata_panel = Panel(
                    metadata_table,
                    title="Metadata",
                    border_style=self.get_themed_style('panel_styles', 'success', 'green'),
                    padding=(1, 2)
                )

            # Shards Distribution Panel - Create 3 separate tables
            shard_states = {}
            shard_types = {'primary': 0, 'replica': 0}
            nodes_distribution = {}

            for shard in index_shards:
                # Count states
                state = shard['state']
                shard_states[state] = shard_states.get(state, 0) + 1

                # Count types
                if shard['prirep'] == 'p':
                    shard_types['primary'] += 1
                else:
                    shard_types['replica'] += 1

                # Count node distribution
                node = shard.get('node', 'unassigned')
                nodes_distribution[node] = nodes_distribution.get(node, 0) + 1

            # Create Shard Totals Table
            totals_table = Table.grid(padding=(0, 3))
            totals_table.add_column(style="bold cyan", min_width=16)
            totals_table.add_column(style="white")
            totals_table.add_row("Total Shards:", f"📊 {len(index_shards)}")
            totals_table.add_row("Primary:", f"🔑 {shard_types['primary']}")
            totals_table.add_row("Replica:", f"📋 {shard_types['replica']}")

            totals_panel = Panel(
                totals_table,
                title="Shard Totals",
                border_style=self.get_themed_style('panel_styles', 'success', 'green'),
                padding=(1, 1)
            )

            # Create States Table
            states_table = Table.grid(padding=(0, 3))
            states_table.add_column(style="bold cyan", min_width=16)
            states_table.add_column(style="white")
            for state, count in shard_states.items():
                icon = "✅" if state == "STARTED" else "🔄" if state == "INITIALIZING" else "❌"
                states_table.add_row(f"{state}:", f"{icon} {count}")

            states_panel = Panel(
                states_table,
                title="🔄 Shard States",
                border_style=self.get_themed_style('panel_styles', 'warning', 'yellow'),
                padding=(1, 1)
            )

            # Create Nodes Table
            nodes_table = Table.grid(padding=(0, 3))
            nodes_table.add_column(style="bold cyan", min_width=16)
            nodes_table.add_column(style="white")
            top_nodes = sorted(nodes_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
            for node, count in top_nodes:
                if node != 'unassigned':
                    nodes_table.add_row(f"{node}:", f"💻 {count}")
                else:
                    nodes_table.add_row("None:", f"🔶 {count}")

            nodes_panel = Panel(
                nodes_table,
                title="💻 Node Distribution",
                border_style=self.get_themed_style('panel_styles', 'secondary', 'magenta'),
                padding=(1, 1)
            )

            # Create detailed shards table with full theme integration
            full_theme = self.theme_manager.get_full_theme_data() if self.theme_manager else {}
            table_styles = full_theme.get('table_styles', {})

            # Get table box style from theme
            table_box = table_styles.get('table_box', 'heavy')
            box_style = None
            if table_box == 'heavy':
                from rich.box import HEAVY
                box_style = HEAVY
            elif table_box == 'rounded':
                from rich.box import ROUNDED
                box_style = ROUNDED
            elif table_box == 'simple':
                from rich.box import SIMPLE
                box_style = SIMPLE
            elif table_box == 'double':
                from rich.box import DOUBLE
                box_style = DOUBLE
            elif table_box is None or table_box == 'None':
                box_style = None
            else:
                from rich.box import HEAVY
                box_style = HEAVY  # Default fallback

            header_style = table_styles.get('header_style', 'bold bright_white on dark_magenta')
            border_style = table_styles.get('border_style', 'bright_magenta')

            shards_table = Table(
                show_header=True,
                header_style=header_style,
                title="Detailed Shards Information",
                title_style="bold bright_white",
                border_style=border_style,
                box=box_style,
                expand=True
            )

            # Column styles don't need to be set individually since header_style handles all headers
            shards_table.add_column("State", justify="center", width=12)
            shards_table.add_column("Type", justify="center", width=10)
            shards_table.add_column("Shard", justify="center", width=8)
            shards_table.add_column("Documents", justify="right", width=12)
            shards_table.add_column("Store", justify="right", width=10)
            shards_table.add_column("Node", no_wrap=True)

            # Sort shards by shard number and type
            sorted_shards = sorted(index_shards, key=lambda x: (int(x['shard']), x['prirep']))

            for shard in sorted_shards:
                # Format state using meaningful shapes and muted colors for easier viewing
                from rich.table import Table as MiniTable
                state = shard['state']

                # Create mini table for icon and text
                mini_table = MiniTable.grid(padding=(0, 1))
                mini_table.add_column(justify="center", width=1)  # Icon column
                mini_table.add_column(justify="left", width=10)  # Text column

                # Get theme styles from configuration
                full_theme = self.theme_manager.get_full_theme_data() if self.theme_manager else {}
                state_styles = full_theme.get('table_styles', {}).get('state_styles', {})

                if state == "STARTED":
                    style_config = state_styles.get('STARTED', {})
                    icon_style = style_config.get('icon', 'green')
                    text_style = style_config.get('text', 'green')
                    row_style = style_config.get('row', 'bright_green')
                    mini_table.add_row(Text("◉", style=icon_style),
                                      Text("Started", style=text_style))
                elif state == "INITIALIZING":
                    style_config = state_styles.get('INITIALIZING', {})
                    icon_style = style_config.get('icon', 'yellow')
                    text_style = style_config.get('text', 'yellow')
                    row_style = style_config.get('row', 'bright_yellow')
                    mini_table.add_row(Text("◐", style=icon_style),
                                      Text("Initializing", style=text_style))
                elif state == "RELOCATING":
                    style_config = state_styles.get('RELOCATING', {})
                    icon_style = style_config.get('icon', 'blue')
                    text_style = style_config.get('text', 'blue')
                    row_style = style_config.get('row', 'bright_blue')
                    mini_table.add_row(Text("⬌", style=icon_style),
                                      Text("Relocating", style=text_style))
                elif state == "UNASSIGNED":
                    style_config = state_styles.get('UNASSIGNED', {})
                    icon_style = style_config.get('icon', 'red')
                    text_style = style_config.get('text', 'red')
                    row_style = style_config.get('row', 'bright_red')
                    mini_table.add_row(Text("○", style=icon_style),
                                      Text("Unassigned", style=text_style))
                else:
                    style_config = state_styles.get('default', {})
                    icon_style = style_config.get('icon', 'white')
                    text_style = style_config.get('text', 'white')
                    row_style = style_config.get('row', 'bright_white')
                    mini_table.add_row(Text("●", style=icon_style),
                                      Text(state, style=text_style))

                state_display = mini_table

                # Format type with theme styles
                type_mini_table = MiniTable.grid(padding=(0, 1))
                type_mini_table.add_column(justify="center", width=1)  # Icon column
                type_mini_table.add_column(justify="left", width=6)  # Text column

                type_styles = full_theme.get('table_styles', {}).get('type_styles', {})

                if shard['prirep'] == 'p':
                    style_config = type_styles.get('primary', {})
                    icon_style = style_config.get('icon', 'cyan')
                    text_style = style_config.get('text', 'cyan')
                    type_mini_table.add_row(Text("■", style=icon_style),
                                           Text("Primary", style=text_style))
                else:
                    style_config = type_styles.get('replica', {})
                    icon_style = style_config.get('icon', 'blue')
                    text_style = style_config.get('text', 'blue')
                    type_mini_table.add_row(Text("□", style=icon_style),
                                           Text("Replica", style=text_style))

                shard_type = type_mini_table

                # Format documents with themed styling
                docs = shard.get('docs', '-')
                if docs != '-' and docs is not None:
                    try:
                        docs = f"{int(docs):,}"
                    except:
                        pass

                # Get themed data cell styles
                data_cell_style = table_styles.get('data_cells', {}).get('style', 'bright_white')
                shard_number_style = table_styles.get('shard_number', {}).get('style', 'bright_cyan')
                docs_style = table_styles.get('documents', {}).get('style', 'bright_white')
                store_style = table_styles.get('storage', {}).get('style', 'bright_yellow')
                node_style = table_styles.get('node', {}).get('style', 'bright_magenta')

                shards_table.add_row(
                    state_display,
                    shard_type,
                    Text(str(shard['shard']), style=shard_number_style),
                    Text(str(docs), style=docs_style),
                    Text(str(shard.get('store', '-')), style=store_style),
                    Text(str(shard.get('node', 'unassigned')), style=node_style),
                    style=row_style
                )

            # Display everything
            print()
            console.print(title_panel)
            print()

            # Create layout for top panels - two columns
            top_panels = Columns([overview_panel, settings_panel], expand=True)
            console.print(top_panels)
            print()

            # Display metadata panel if it exists
            if metadata_panel:
                console.print(metadata_panel)
                print()

            # Shards distribution in three columns
            shards_distribution_panels = Columns([totals_panel, states_panel, nodes_panel], expand=True)
            console.print(shards_distribution_panels)
            print()

            console.print(shards_table)

        except Exception as e:
            console.print(f"[red]❌ Error retrieving index details: {str(e)}[/red]")

    def print_indices_traffic_analysis(
        self,
        result: dict,
        console=None,
        use_pager: bool = False,
    ) -> None:
        """Print rollover-series traffic analysis (doc/store vs peer medians)."""
        from configuration_manager import ConfigurationManager
        import os

        if console is None:
            console = Console()

        summary = result.get("summary", {})
        rows = result.get("rows", [])
        style_system = getattr(self.es_client, "style_system", None) if self.es_client else None

        flagged = summary.get("flagged_rows", len(rows))
        sub = (
            f"Indices scanned: {summary.get('indices_input', 0)} | "
            f"Rollover groups: {summary.get('rollover_groups', 0)} | "
            f"Flagged: {flagged}"
        )
        if summary.get("within_days") is not None:
            sub += (
                f" | Rollover date ≥ {summary.get('rollover_date_cutoff_utc', '?')} "
                f"(UTC, last {summary['within_days']}d)"
            )
        md = summary.get("min_docs")
        if md is not None and md > 0:
            sub += f" | Docs ≥ {md:,}"
        title_text = Text("Index traffic analysis", style="bold", justify="center")
        title_panel = Panel(
            title_text,
            subtitle=sub,
            border_style=self.get_themed_style(
                "table_styles", "border_style", "bright_magenta"
            ),
            padding=(1, 2),
        )

        if not rows:
            console.print()
            console.print(title_panel)
            console.print()
            console.print(
                "[dim]No indices matched the filters (ratio, optional rollover window, min docs). "
                "Try --min-ratio 2, --min-docs 0, or a wider pattern.[/dim]"
            )
            console.print()
            return

        if style_system:
            table = style_system.create_standard_table(
                title="Outliers vs leave-one-out peer median (sorted by docs ratio)",
                style_variant="dashboard",
            )
        else:
            table = Table(
                title="Outliers vs leave-one-out peer median",
                show_header=True,
                header_style="bold",
            )

        table.add_column("Ratio", justify="right", width=7)
        table.add_column("Docs", justify="right", width=14)
        table.add_column("Med docs", justify="right", width=14)
        table.add_column("Store Δ", justify="right", width=8)
        table.add_column("Index", no_wrap=False, min_width=36)
        table.add_column("Hot", justify="center", width=4)
        table.add_column("Gap d", justify="right", width=7)

        hot_names = set(
            getattr(self.es_client, "cluster_indices_hot_indexes", []) or []
        )

        for r in rows:
            idx = r.get("index", "")
            hot_mark = "🔥" if idx in hot_names else ""
            sr = r.get("store_ratio")
            store_delta = f"{sr:.2f}x" if sr is not None else "—"
            med_gap = r.get("median_days_between_rollovers")
            gap_s = f"{med_gap:.1f}" if med_gap is not None else "—"

            row_style = "bright_red" if r.get("docs_ratio", 0) >= 4 else None
            if not row_style and r.get("docs_ratio", 0) >= 2.5:
                row_style = "yellow"

            table.add_row(
                f"{r.get('docs_ratio', 0):.2f}x",
                f"{r.get('docs', 0):,}",
                f"{r.get('peer_median_docs', 0):,}",
                store_delta,
                idx,
                hot_mark,
                gap_s,
                style=row_style,
            )

        try:
            config_file = os.path.join(
                os.path.dirname(__file__), "..", "elastic_servers.yml"
            )
            state_file = os.path.join(os.path.dirname(__file__), "..", "escmd.json")
            config_manager = ConfigurationManager(config_file, state_file)
            paging_enabled = getattr(
                config_manager, "get_paging_enabled", lambda: False
            )()
            paging_threshold = getattr(
                config_manager, "get_paging_threshold", lambda: 50
            )()
        except Exception:
            paging_enabled = False
            paging_threshold = 50

        should_page = use_pager or (
            paging_enabled and len(rows) > paging_threshold
        )

        def _render():
            console.print()
            console.print(title_panel)
            console.print()
            console.print(table)
            console.print()
            console.print(
                f"[dim]Med docs = median doc count among sibling backing indices in the "
                f"same rollover series. Store Δ = primary store vs peer median. "
                f"Gap d = median days between generations in that series.[/dim]"
            )
            console.print()

        if should_page:
            with console.pager():
                _render()
            _render()
        else:
            _render()

    def print_s3_storage_estimate(self, result: dict, console=None) -> None:
        """Print primary-size S3 monthly cost estimate (table)."""
        if console is None:
            console = Console()

        assumptions = result.get("assumptions", {})
        counts = result.get("counts", {})
        cost = result.get("cost", {})
        bytes_info = result.get("bytes", {})

        fmt = (
            self.es_client.format_bytes
            if self.es_client and hasattr(self.es_client, "format_bytes")
            else lambda b: str(b)
        )

        table = Table(title="S3 storage estimate (primary bytes)", show_header=False)
        table.add_column("Field", style="bold cyan", min_width=28)
        table.add_column("Value", style="white")

        table.add_row("Est. month 1 (USD)", f"{cost.get('estimated_monthly_usd', 0):,.4f}")
        m2_usd = cost.get("estimated_month_2_usd")
        m3_usd = cost.get("estimated_month_3_usd")
        if m2_usd is not None and m3_usd is not None:
            table.add_row("Est. month 2 cumulative (USD)", f"{m2_usd:,.4f}")
            table.add_row("Est. month 3 cumulative (USD)", f"{m3_usd:,.4f}")
        table.add_row("Primary size (sum)", fmt(bytes_info.get("total_pri", 0)))
        table.add_row("After buffer (sum)", fmt(bytes_info.get("buffered_pri", 0)))
        b2 = bytes_info.get("cumulative_buffered_pri_month_2")
        b3 = bytes_info.get("cumulative_buffered_pri_month_3")
        if b2 is not None and b3 is not None:
            table.add_row("Cumulative buffered (mo 2)", fmt(b2))
            table.add_row("Cumulative buffered (mo 3)", fmt(b3))
        table.add_row("Primary (GiB)", f"{cost.get('total_pri_gib', 0):,.6f}")
        table.add_row("Buffered (GiB, month-1 slice)", f"{cost.get('buffered_pri_gib', 0):,.6f}")
        cg2 = cost.get("cumulative_buffered_pri_gib_month_2")
        cg3 = cost.get("cumulative_buffered_pri_gib_month_3")
        if cg2 is not None and cg3 is not None:
            table.add_row("Cumulative buffered GiB (mo 2)", f"{cg2:,.6f}")
            table.add_row("Cumulative buffered GiB (mo 3)", f"{cg3:,.6f}")
        table.add_row("Indices (dated, in window)", str(counts.get("indices_matched_dated", 0)))
        table.add_row(
            "Dated before cutoff (excluded)",
            str(counts.get("indices_excluded_dated_before_cutoff", 0)),
        )
        if assumptions.get("include_undated"):
            table.add_row(
                "Undated included",
                str(counts.get("indices_undated_included", 0)),
            )
        else:
            table.add_row(
                "Undated skipped (no YYYY.MM.DD in name)",
                str(counts.get("indices_undated_skipped", 0)),
            )
        table.add_row("Within last N days (UTC)", str(assumptions.get("within_days", "")))
        table.add_row("Buffer %", str(assumptions.get("buffer_percent", 0)))
        table.add_row("Price (USD / GiB-mo)", str(assumptions.get("price_per_gib_month_usd", "")))
        table.add_row("As-of date (UTC)", str(assumptions.get("as_of_date_utc", "")))
        table.add_row("Rollover cutoff (UTC)", str(assumptions.get("rollover_date_cutoff_utc", "")))

        console.print()
        console.print(
            Panel(
                table,
                title="[bold]indices-s3-estimate[/bold]",
                subtitle="[dim]Rough planning figure; not an AWS bill[/dim]",
                border_style=self.get_themed_style(
                    "table_styles", "border_style", "bright_blue"
                ),
                padding=(1, 2),
            )
        )
        console.print()
        mm = assumptions.get("multi_month_model")
        if mm:
            console.print(f"[dim]{mm}[/dim]")
            console.print()
        note = assumptions.get("note")
        if note:
            console.print(f"[dim]{note}[/dim]")
            console.print()
