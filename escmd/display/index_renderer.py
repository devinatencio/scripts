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
        from display.style_system import StyleSystem
        self.theme_manager = theme_manager
        self.es_client = es_client
        self.style_system = StyleSystem(theme_manager) if theme_manager else None

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
            is_hot = indice_name in getattr(self.es_client, 'cluster_indices_hot_indexes', [])
            is_frozen = settings.get('frozen', 'false') == 'true'

            ss = self.style_system
            ts = ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'
            _title = self.theme_manager.get_themed_style("panel_styles", "title", "bold white") if self.theme_manager else "bold white"

            # --- Title panel (standard pattern) ---
            health = index_info['health']
            health_icon = "🟢" if health == 'green' else "🟡" if health == 'yellow' else "🔴"
            docs_count = f"{int(index_info['docs.count']):,}" if index_info['docs.count'] != '-' else 'N/A'
            pri_count = str(index_info['pri'])
            rep_count = str(index_info['rep'])

            # Shard state counts for status text
            shard_states = {}
            shard_types = {'primary': 0, 'replica': 0}
            nodes_distribution = {}
            for shard in index_shards:
                state = shard['state']
                shard_states[state] = shard_states.get(state, 0) + 1
                if shard['prirep'] == 'p':
                    shard_types['primary'] += 1
                else:
                    shard_types['replica'] += 1
                node = shard.get('node', 'unassigned')
                nodes_distribution[node] = nodes_distribution.get(node, 0) + 1

            unassigned_count = shard_states.get('UNASSIGNED', 0)

            # Body: health-aware status
            if health == 'red':
                status_text = f"🔴 {indice_name} - {unassigned_count} Unassigned Shard{'s' if unassigned_count != 1 else ''}"
                body_style = f"bold {ss.get_semantic_style('error')}" if ss else "bold red"
                border = ss.get_semantic_style('error') if ss else "red"
            elif health == 'yellow':
                status_text = f"🟡 {indice_name} - {unassigned_count} Unassigned Replica{'s' if unassigned_count != 1 else ''}"
                body_style = f"bold {ss.get_semantic_style('warning')}" if ss else "bold yellow"
                border = ss.get_semantic_style('warning') if ss else "yellow"
            else:
                status_text = f"🟢 {indice_name} - Healthy (All Shards Assigned)"
                body_style = f"bold {ss.get_semantic_style('success')}" if ss else "bold green"
                border = ss._get_style('table_styles', 'border_style', 'bright_magenta') if ss else "bright_magenta"

            # Subtitle bar
            subtitle_rich = Text()
            subtitle_rich.append("Docs: ", style="default")
            subtitle_rich.append(str(docs_count), style=ss._get_style('semantic', 'info', 'cyan') if ss else "cyan")
            subtitle_rich.append(" | Shards: ", style="default")
            subtitle_rich.append(f"{pri_count}p", style=ss._get_style('semantic', 'primary', 'bright_magenta') if ss else "bright_magenta")
            subtitle_rich.append("/", style="default")
            subtitle_rich.append(f"{rep_count}r", style=ss._get_style('semantic', 'info', 'blue') if ss else "blue")
            subtitle_rich.append(" | Size: ", style="default")
            subtitle_rich.append(str(index_info.get('pri.store.size', '-')), style=ss._get_style('semantic', 'info', 'cyan') if ss else "cyan")
            subtitle_rich.append(" / ", style="default")
            subtitle_rich.append(str(index_info.get('store.size', '-')), style=ss._get_style('semantic', 'info', 'cyan') if ss else "cyan")
            subtitle_rich.append(" | Status: ", style="default")
            if index_info['status'] == 'open':
                subtitle_rich.append("Open", style=ss._get_style('semantic', 'success', 'green') if ss else "green")
            else:
                subtitle_rich.append("Closed", style=ss._get_style('semantic', 'warning', 'yellow') if ss else "yellow")

            # ILM info in subtitle
            ilm_policy = settings.get('lifecycle', {}).get('name', None)
            ilm_phase = None
            ilm_phase_icon = ''
            if ilm_policy:
                try:
                    ilm_explain = self.es_client.es.ilm.explain_lifecycle(index=indice_name)
                    if indice_name in ilm_explain['indices']:
                        phase_name = ilm_explain['indices'][indice_name].get('phase', '')
                        phase_icons = {'hot': '🔥', 'warm': '🟡', 'cold': '🧊', 'frozen': '🧊', 'delete': '🗑'}
                        ilm_phase_icon = phase_icons.get(phase_name, '')
                        ilm_phase = phase_name.title()
                except Exception:
                    pass

                subtitle_rich.append(" | ILM: ", style="default")
                subtitle_rich.append(ilm_policy, style=ss._get_style('semantic', 'primary', 'bright_magenta') if ss else "bright_magenta")
                if ilm_phase:
                    subtitle_rich.append(f" ({ilm_phase_icon} {ilm_phase})", style=ss._get_style('semantic', 'primary', 'bright_magenta') if ss else "bright_magenta")

            if is_hot:
                subtitle_rich.append(" | 🔥 Hot Index", style=ss._get_style('semantic', 'error', 'bright_red') if ss else "bright_red")
            elif is_frozen:
                subtitle_rich.append(" | 🧊 Frozen", style=ss._get_style('semantic', 'info', 'bright_blue') if ss else "bright_blue")

            title_panel = Panel(
                Text(status_text, style=body_style, justify="center"),
                title=f"[{ts}]📋 Index Details[/{ts}]",
                subtitle=subtitle_rich,
                border_style=border,
                padding=(1, 2)
            )

            # --- Settings panel (left) ---
            from rich.table import Table as InnerTable

            creation_date = settings.get('creation_date', 'Unknown')
            if creation_date != 'Unknown':
                try:
                    import datetime
                    creation_date = datetime.datetime.fromtimestamp(int(creation_date) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass

            uuid = settings.get('uuid', 'Unknown')
            version = settings.get('version', {}).get('created', 'Unknown')
            number_of_shards = settings.get('number_of_shards', 'Unknown')
            number_of_replicas = settings.get('number_of_replicas', 'Unknown')

            settings_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            settings_table.add_column("Label", style="bold", no_wrap=True)
            settings_table.add_column("Icon", justify="left", width=3)
            settings_table.add_column("Value", no_wrap=True)

            settings_table.add_row("UUID:", "🆔", str(uuid))
            settings_table.add_row("Created:", "📅", str(creation_date))
            settings_table.add_row("Version:", "🔩", str(version))
            if ilm_policy:
                settings_table.add_row("ILM Policy:", "📋", str(ilm_policy))
                if ilm_phase:
                    settings_table.add_row("ILM Phase:", ilm_phase_icon or "📋", str(ilm_phase))
            else:
                settings_table.add_row("ILM Policy:", "❌", "None")
            settings_table.add_row("Shards:", "🔢", f"{number_of_shards} primary / {number_of_replicas} replica")

            settings_panel = Panel(
                settings_table,
                title=f"[{_title}]🔩 Settings[/{_title}]",
                border_style=ss._get_style('table_styles', 'border_style', 'bright_magenta') if ss else "bright_magenta",
                padding=(1, 2)
            )

            # --- Shard Overview panel (right) ---
            shard_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            shard_table.add_column("Label", style="bold", no_wrap=True)
            shard_table.add_column("Icon", justify="left", width=3)
            shard_table.add_column("Value", no_wrap=True)

            shard_table.add_row("Total Shards:", "📊", str(len(index_shards)))

            # Primary status
            pri_started = sum(1 for s in index_shards if s['prirep'] == 'p' and s['state'] == 'STARTED')
            pri_other = shard_types['primary'] - pri_started
            if pri_other == 0:
                shard_table.add_row("Primary:", "🔑", Text(f"{shard_types['primary']} Started", style=ss.get_semantic_style("success") if ss else "green"))
            else:
                shard_table.add_row("Primary:", "🔑", Text(f"{pri_started} Started, {pri_other} Other", style=ss.get_semantic_style("warning") if ss else "yellow"))

            # Replica status
            rep_unassigned = sum(1 for s in index_shards if s['prirep'] == 'r' and s['state'] == 'UNASSIGNED')
            rep_started = shard_types['replica'] - rep_unassigned
            if rep_unassigned > 0:
                shard_table.add_row("Replica:", "📋", Text(f"{rep_unassigned} Unassigned", style=ss.get_semantic_style("error") if ss else "red"))
            elif shard_types['replica'] > 0:
                shard_table.add_row("Replica:", "📋", Text(f"{shard_types['replica']} Started", style=ss.get_semantic_style("success") if ss else "green"))
            else:
                shard_table.add_row("Replica:", "📋", "0")

            # Node distribution
            if nodes_distribution:
                shard_table.add_row("", "", "")
                top_nodes = sorted(nodes_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
                for node, count in top_nodes:
                    shard_word = "shard" if count == 1 else "shards"
                    if node != 'unassigned':
                        shard_table.add_row(f"{node}:", "💻", f"{count} {shard_word}")
                    else:
                        shard_table.add_row("Unassigned:", "🔶", f"{count} {shard_word}")

            shard_border = ss.get_semantic_style("warning") if unassigned_count > 0 else ss.get_semantic_style("success") if ss else ("yellow" if unassigned_count > 0 else "green")
            shard_panel = Panel(
                shard_table,
                title=f"[{_title}]📊 Shard Overview[/{_title}]",
                border_style=shard_border,
                padding=(1, 2)
            )

            # --- Metadata Panel ---
            metadata_panel = None
            metadata = mapping_meta
            if metadata:
                # Create metadata table with full theme integration (same pattern as shards table)
                full_theme = self.theme_manager.get_full_theme_data() if self.theme_manager else {}
                table_styles = full_theme.get('table_styles', {})

                box_style = self.style_system.get_table_box() if self.style_system else None
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

            # Create detailed shards table with full theme integration
            full_theme = self.theme_manager.get_full_theme_data() if self.theme_manager else {}
            table_styles = full_theme.get('table_styles', {})

            box_style = self.style_system.get_table_box() if self.style_system else None
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
                type_mini_table.add_column(justify="left", width=7)  # Text column

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

            # Settings + Shard Overview side by side
            console.print(Columns([settings_panel, shard_panel], expand=True))
            print()

            # Display metadata panel if it exists
            if metadata_panel:
                console.print(metadata_panel)
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

        # Build themed subtitle bar
        subtitle_rich = Text()
        subtitle_rich.append("Scanned: ", style="default")
        subtitle_rich.append(str(summary.get('indices_input', 0)), style=style_system._get_style('semantic', 'info', 'cyan') if style_system else "cyan")
        subtitle_rich.append(" | Groups: ", style="default")
        subtitle_rich.append(str(summary.get('rollover_groups', 0)), style=style_system._get_style('semantic', 'primary', 'bright_magenta') if style_system else "bright_magenta")
        subtitle_rich.append(" | Flagged: ", style="default")
        if flagged > 0:
            subtitle_rich.append(str(flagged), style=style_system._get_style('semantic', 'warning', 'yellow') if style_system else "yellow")
        else:
            subtitle_rich.append(str(flagged), style=style_system._get_style('semantic', 'success', 'green') if style_system else "green")

        if summary.get("within_days") is not None:
            subtitle_rich.append(" | Window: ", style="default")
            subtitle_rich.append(
                f"last {summary['within_days']}d",
                style=style_system._get_style('semantic', 'info', 'cyan') if style_system else "cyan"
            )

        md = summary.get("min_docs")
        if md is not None and md > 0:
            subtitle_rich.append(" | Docs ≥ ", style="default")
            subtitle_rich.append(f"{md:,}", style=style_system._get_style('semantic', 'info', 'cyan') if style_system else "cyan")

        # Body: status text centered
        if flagged > 0:
            status_text = f"🔶 {flagged} Outlier{'s' if flagged != 1 else ''} Detected"
            body_style = f"bold {style_system.get_semantic_style('warning')}" if style_system else "bold yellow"
            border = style_system.get_semantic_style('warning') if style_system else "yellow"
        else:
            status_text = "✅ No Outliers - All Indices Within Normal Range"
            body_style = f"bold {style_system.get_semantic_style('success')}" if style_system else "bold green"
            border = self.get_themed_style("table_styles", "border_style", "cyan")

        ts = style_system._get_style('semantic', 'primary', 'bold cyan') if style_system else 'bold cyan'
        title_panel = Panel(
            Text(status_text, style=body_style, justify="center"),
            title=f"[{ts}]📊 Index Traffic Analysis[/{ts}]",
            subtitle=subtitle_rich,
            border_style=border,
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

        for i, r in enumerate(rows):
            idx = r.get("index", "")
            hot_mark = "🔥" if idx in hot_names else ""
            sr = r.get("store_ratio")
            store_delta = f"{sr:.2f}x" if sr is not None else "—"
            med_gap = r.get("median_days_between_rollovers")
            gap_s = f"{med_gap:.1f}" if med_gap is not None else "—"

            dr = r.get("docs_ratio", 0) or 0
            severity_style = "bright_red" if dr >= 4 else None
            if not severity_style and dr >= 2.5:
                severity_style = "yellow"

            zebra_bg = (
                style_system.get_zebra_style(i) if style_system else None
            )
            if severity_style and zebra_bg:
                row_style = f"{severity_style} {zebra_bg}"
            elif zebra_bg:
                row_style = zebra_bg
            else:
                row_style = severity_style

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

        # --- Theme access (§3) ---
        try:
            from display.style_system import StyleSystem
            ss = StyleSystem(self.theme_manager) if self.theme_manager else None
        except ImportError:
            ss = None

        if ss:
            border_style = ss._get_style('table_styles', 'border_style', 'bright_magenta')
            info_style = ss._get_style('semantic', 'info', 'cyan')
            muted_style = ss._get_style('semantic', 'muted', 'dim')
            success_style = ss.get_semantic_style("success")
            warning_style = ss.get_semantic_style("warning")
        else:
            border_style = self.get_themed_style("table_styles", "border_style", "bright_blue")
            info_style = "cyan"
            muted_style = "dim"
            success_style = "green"
            warning_style = "yellow"

        title_style = (
            self.theme_manager.get_themed_style('panel_styles', 'title', 'bold white')
            if self.theme_manager else 'bold white'
        )

        # --- Title panel (§1) ---
        m1_usd = cost.get("estimated_monthly_usd", 0)
        n_dated = counts.get("indices_matched_dated", 0)
        n_undated = counts.get("indices_undated_skipped", 0) or counts.get("indices_undated_included", 0)
        total_pri = bytes_info.get("total_pri", 0)
        within_days = assumptions.get("within_days", 30)

        subtitle_rich = Text()
        subtitle_rich.append("Indices: ", style="default")
        subtitle_rich.append(str(n_dated), style=info_style)
        subtitle_rich.append(" | Primary: ", style="default")
        subtitle_rich.append(fmt(total_pri), style=info_style)
        subtitle_rich.append(" | Window: ", style="default")
        subtitle_rich.append(f"{within_days}d", style=info_style)
        subtitle_rich.append(" | Price: ", style="default")
        subtitle_rich.append(f"${assumptions.get('price_per_gib_month_usd', 0)}/GiB-mo", style=info_style)

        title_panel = Panel(
            Text(
                f"💰 Est. ${m1_usd:,.4f} / month",
                style="bold green",
                justify="center",
            ),
            title=f"[{title_style}]💾 S3 Storage Estimate[/{title_style}]",
            subtitle=subtitle_rich,
            border_style=border_style,
            padding=(1, 2),
        )

        # --- Inner panel table (§4) ---
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="bold", no_wrap=True)
        table.add_column("Icon", justify="left", width=3)
        table.add_column("Value", no_wrap=True)

        table.add_row("Est. month 1 (USD):", "💰", f"${m1_usd:,.4f}")
        m2_usd = cost.get("estimated_month_2_usd")
        m3_usd = cost.get("estimated_month_3_usd")
        if m2_usd is not None and m3_usd is not None:
            table.add_row("Est. month 2 cumulative:", "💰", f"${m2_usd:,.4f}")
            table.add_row("Est. month 3 cumulative:", "💰", f"${m3_usd:,.4f}")
        table.add_row("", "", "")
        table.add_row("Primary size (sum):", "💾", fmt(bytes_info.get("total_pri", 0)))
        table.add_row("After buffer (sum):", "💾", fmt(bytes_info.get("buffered_pri", 0)))
        b2 = bytes_info.get("cumulative_buffered_pri_month_2")
        b3 = bytes_info.get("cumulative_buffered_pri_month_3")
        if b2 is not None and b3 is not None:
            table.add_row("Cumulative buffered (mo 2):", "💾", fmt(b2))
            table.add_row("Cumulative buffered (mo 3):", "💾", fmt(b3))
        table.add_row("Primary (GiB):", "📊", f"{cost.get('total_pri_gib', 0):,.6f}")
        table.add_row("Buffered (GiB, mo 1):", "📊", f"{cost.get('buffered_pri_gib', 0):,.6f}")
        cg2 = cost.get("cumulative_buffered_pri_gib_month_2")
        cg3 = cost.get("cumulative_buffered_pri_gib_month_3")
        if cg2 is not None and cg3 is not None:
            table.add_row("Cumulative GiB (mo 2):", "📊", f"{cg2:,.6f}")
            table.add_row("Cumulative GiB (mo 3):", "📊", f"{cg3:,.6f}")
        table.add_row("", "", "")
        table.add_row("Indices (dated, in window):", "📋", str(counts.get("indices_matched_dated", 0)))
        table.add_row(
            "Dated before cutoff:",
            "🚫",
            str(counts.get("indices_excluded_dated_before_cutoff", 0)),
        )
        if assumptions.get("include_undated"):
            table.add_row("Undated included:", "📋", str(counts.get("indices_undated_included", 0)))
        else:
            table.add_row("Undated skipped:", "🚫", str(counts.get("indices_undated_skipped", 0)))
        table.add_row("", "", "")
        table.add_row("Window (days):", "📅", str(assumptions.get("within_days", "")))
        table.add_row("Buffer %:", "📈", str(assumptions.get("buffer_percent", 0)))
        table.add_row("Price (USD/GiB-mo):", "💰", str(assumptions.get("price_per_gib_month_usd", "")))
        table.add_row("As-of date (UTC):", "📅", str(assumptions.get("as_of_date_utc", "")))
        table.add_row("Rollover cutoff (UTC):", "📅", str(assumptions.get("rollover_date_cutoff_utc", "")))

        detail_panel = Panel(
            table,
            border_style=border_style,
            padding=(1, 2),
        )

        # --- Layout (§9) ---
        console.print()
        console.print(title_panel)
        console.print()
        console.print(detail_panel)
        console.print()

        mm = assumptions.get("multi_month_model")
        if mm:
            console.print(f"[{muted_style}]{mm}[/{muted_style}]")
            console.print()
        note = assumptions.get("note")
        if note:
            console.print(f"[{muted_style}]{note}[/{muted_style}]")
            console.print()
