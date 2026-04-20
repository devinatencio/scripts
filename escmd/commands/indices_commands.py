"""
Indices command processors extracted from ElasticsearchClient.

This module handles index-related operations including:
- Index listing and statistics
- Index management operations
- Index pattern matching and filtering
- Index lifecycle management
"""

from typing import Any, Callable, Dict, List, Optional
from .base_command import BaseCommand


class IndicesCommands(BaseCommand):
    """
    Command processor for index-related operations.
    """

    def get_command_group(self) -> str:
        """Get the command group identifier."""
        return 'indices'

    def list_indices_stats(self, pattern: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get comprehensive index statistics with optional filtering.

        Args:
            pattern: Index name pattern to filter by
            status: Health status to filter by ('green', 'yellow', 'red')

        Returns:
            list: Index statistics data
        """
        try:
            # Get all indices stats (including frozen indices)
            cat_indices = self.es_client.es.cat.indices(
                format='json',
                bytes='b',  # Show bytes in raw format for processing
                h='health,status,index,uuid,pri,rep,docs.count,docs.deleted,store.size,pri.store.size',
                expand_wildcards='all'  # Include all indices including frozen, closed, and hidden
            )

            # Handle response format differences
            if hasattr(cat_indices, 'body'):
                indices_data = cat_indices.body
            elif hasattr(cat_indices, 'get') and callable(cat_indices.get):
                indices_data = list(cat_indices) if hasattr(cat_indices, '__iter__') else [dict(cat_indices)]
            else:
                indices_data = cat_indices if isinstance(cat_indices, list) else [cat_indices]

            # Process the indices data
            processed_indices = []
            for index in indices_data:
                processed_index = {
                    'health': index.get('health', 'unknown'),
                    'status': index.get('status', 'unknown'),
                    'index': index.get('index', 'unknown'),
                    'uuid': index.get('uuid', 'unknown'),
                    'pri': int(index.get('pri', 0)) if index.get('pri') else 0,
                    'rep': int(index.get('rep', 0)) if index.get('rep') else 0,
                    'docs.count': int(index.get('docs.count', 0)) if index.get('docs.count') else 0,
                    'docs.deleted': int(index.get('docs.deleted', 0)) if index.get('docs.deleted') else 0,
                    'store.size': int(index.get('store.size', 0)) if index.get('store.size') else 0,
                    'pri.store.size': int(index.get('pri.store.size', 0)) if index.get('pri.store.size') else 0
                }
                processed_indices.append(processed_index)

            # Apply filtering if requested
            if pattern or status:
                filtered_indices = self.es_client.index_processor.filter_indices(
                    processed_indices, pattern, status
                )
                # Sort filtered indices alphabetically by index name
                filtered_indices.sort(key=lambda x: x.get('index', '').lower())
                return filtered_indices

            # Sort indices alphabetically by index name
            processed_indices.sort(key=lambda x: x.get('index', '').lower())
            return processed_indices

        except Exception as e:
            return []

    def get_indices_stats(self, pattern: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Alias for list_indices_stats for backward compatibility.

        Args:
            pattern: Index name pattern to filter by
            status: Health status to filter by

        Returns:
            list: Index statistics data
        """
        return self.list_indices_stats(pattern, status)

    def delete_indices(
        self,
        indice_data: List[str],
        *,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Delete multiple indices.

        Args:
            indice_data: List of index names to delete
            on_progress: Optional callback invoked as (1-based index, total, name)
                before each deletion.

        Returns:
            dict: Deletion results
        """
        results = {
            'successful_deletions': [],
            'failed_deletions': [],
            'total_requested': len(indice_data)
        }

        total = len(indice_data)
        for i, index_name in enumerate(indice_data, start=1):
            if on_progress is not None:
                on_progress(i, total, index_name)
            try:
                self.es_client.es.indices.delete(index=index_name)
                results['successful_deletions'].append(index_name)
            except Exception as e:
                results['failed_deletions'].append({
                    'index': index_name,
                    'error': str(e)
                })

        return results

    def create_index(self, index_name: str, settings: Optional[Dict[str, Any]] = None,
                    mappings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new empty index.

        Args:
            index_name: Name of the index to create
            settings: Index settings (optional)
            mappings: Index mappings (optional)

        Returns:
            dict: Creation results
        """
        try:
            # Build the index body
            index_body = {}

            if settings:
                index_body['settings'] = settings

            if mappings:
                index_body['mappings'] = mappings

            # Create the index
            result = self.es_client.es.indices.create(index=index_name, body=index_body)

            return {
                'success': True,
                'index': index_name,
                'acknowledged': result.get('acknowledged', False),
                'shards_acknowledged': result.get('shards_acknowledged', False),
                'message': f"Index '{index_name}' created successfully"
            }

        except Exception as e:
            return {
                'success': False,
                'index': index_name,
                'error': str(e),
                'message': f"Failed to create index '{index_name}': {str(e)}"
            }

    def get_all_index_settings(self) -> Dict[str, Any]:
        """
        Get settings for all indices.

        Returns:
            dict: Index settings for all indices
        """
        try:
            settings = self.es_client.es.indices.get_settings()

            # Handle response format differences
            if hasattr(settings, 'body'):
                return settings.body
            elif hasattr(settings, 'get'):
                return dict(settings)
            else:
                return settings

        except Exception as e:
            return {"error": f"Failed to get index settings: {str(e)}"}

    def get_index_settings(self, index_name: str) -> Dict[str, Any]:
        """
        Get settings for a specific index.

        Args:
            index_name: Name of the index

        Returns:
            dict: Index settings
        """
        try:
            settings = self.es_client.es.indices.get_settings(index=index_name)

            # Handle response format differences
            if hasattr(settings, 'body'):
                return settings.body
            elif hasattr(settings, 'get'):
                return dict(settings)
            else:
                return settings

        except Exception as e:
            return {"error": f"Failed to get settings for index '{index_name}': {str(e)}"}

    def get_index_info(self, index_name: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a specific index.

        Args:
            index_name: Name of the index

        Returns:
            dict: Comprehensive index information
        """
        try:
            # Get basic index info
            index_info = self.es_client.es.indices.get(index=index_name)

            # Get index stats
            index_stats = self.es_client.es.indices.stats(index=index_name)

            # Get index mapping
            index_mapping = self.es_client.es.indices.get_mapping(index=index_name)

            # Handle response format differences and combine data
            if hasattr(index_info, 'body'):
                info_data = index_info.body
                stats_data = index_stats.body if hasattr(index_stats, 'body') else index_stats
                mapping_data = index_mapping.body if hasattr(index_mapping, 'body') else index_mapping
            else:
                info_data = index_info
                stats_data = index_stats
                mapping_data = index_mapping

            combined_info = {
                'index_name': index_name,
                'settings': info_data.get(index_name, {}).get('settings', {}),
                'mappings': mapping_data.get(index_name, {}).get('mappings', {}),
                'aliases': info_data.get(index_name, {}).get('aliases', {}),
                'stats': stats_data
            }

            return combined_info

        except Exception as e:
            return {
                'index_name': index_name,
                'error': f"Failed to get index info: {str(e)}"
            }

    def get_template(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get index templates.

        Args:
            name: Specific template name (optional)

        Returns:
            dict: Template information
        """
        try:
            if name:
                templates = self.es_client.es.indices.get_template(name=name)
            else:
                templates = self.es_client.es.indices.get_template()

            # Handle response format differences
            if hasattr(templates, 'body'):
                return templates.body
            elif hasattr(templates, 'get'):
                return dict(templates)
            else:
                return templates

        except Exception as e:
            return {"error": f"Failed to get templates: {str(e)}"}

    def exclude_index_from_host(self, index_name: Optional[str] = None, host_to_exclude: Optional[str] = None) -> Dict[str, Any]:
        """
        Exclude an index from allocation on a specific host.

        Args:
            index_name: Name of the index to exclude
            host_to_exclude: Hostname to exclude from allocation

        Returns:
            dict: Operation result
        """
        if not index_name or not host_to_exclude:
            return {"error": "Both index_name and host_to_exclude are required"}

        try:
            self.es_client.es.indices.put_settings(
                index=index_name,
                body={
                    "index.routing.allocation.exclude._name": host_to_exclude
                }
            )
            return {
                "success": True,
                "message": f"Index '{index_name}' excluded from host '{host_to_exclude}'"
            }
        except Exception as e:
            return {
                "error": f"Failed to exclude index from host: {str(e)}",
                "index": index_name,
                "host": host_to_exclude
            }

    def exclude_index_reset(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Reset index allocation exclusions.

        Args:
            index_name: Name of the index to reset

        Returns:
            dict: Operation result
        """
        if not index_name:
            return {"error": "index_name is required"}

        try:
            self.es_client.es.indices.put_settings(
                index=index_name,
                body={
                    "index.routing.allocation.exclude._name": None
                }
            )
            return {
                "success": True,
                "message": f"Allocation exclusions reset for index '{index_name}'"
            }
        except Exception as e:
            return {
                "error": f"Failed to reset index exclusions: {str(e)}",
                "index": index_name
            }

    def get_index_patterns(self) -> List[str]:
        """
        Extract unique patterns from current index data.

        Returns:
            list: Unique index patterns
        """
        try:
            indices_data = self.list_indices_stats()
            return self.es_client.index_processor.extract_unique_patterns(indices_data)
        except Exception:
            return []

    def get_latest_indices(self) -> List[str]:
        """
        Find the latest indices based on date patterns.

        Returns:
            list: Latest index names
        """
        try:
            indices_data = self.list_indices_stats()
            return self.es_client.index_processor.find_latest_indices(indices_data)
        except Exception:
            return []

    def list_dangling_indices(self) -> Dict[str, Any]:
        """
        List dangling indices in the cluster.

        Returns:
            dict: Dangling indices information
        """
        try:
            # Use the low-level client for this endpoint
            resp = self.es_client.es.transport.perform_request('GET', '/_dangling')

            # Handle both dictionary response (older versions) and TransportApiResponse (newer versions)
            if hasattr(resp, 'body'):
                return resp.body
            elif hasattr(resp, 'get'):
                return resp
            else:
                # If it's not a dict-like object, try to convert it
                return dict(resp) if resp else {}

        except Exception as e:
            return {"error": str(e)}

    def delete_dangling_index(self, uuid: str) -> Dict[str, Any]:
        """
        Delete a dangling index by its UUID.

        Args:
            uuid: UUID of the dangling index

        Returns:
            dict: Operation result
        """
        try:
            # Use the low-level client for the DELETE endpoint
            # DELETE /_dangling/<index-uuid>?accept_data_loss=true
            from esclient import ES_VERSION_MAJOR

            if ES_VERSION_MAJOR >= 8:
                # ES client 8.x+ - query parameters included in URL path
                resp = self.es_client.es.transport.perform_request(
                    'DELETE',
                    f'/_dangling/{uuid}?accept_data_loss=true'
                )
            else:
                # ES client 7.x - query parameters as separate argument
                resp = self.es_client.es.transport.perform_request(
                    'DELETE',
                    f'/_dangling/{uuid}',
                    params={'accept_data_loss': 'true'}
                )

            # Handle response format
            if hasattr(resp, 'body'):
                return resp.body
            elif hasattr(resp, 'get'):
                return resp
            else:
                return dict(resp) if resp else {"success": True}

        except Exception as e:
            return {"error": str(e), "uuid": uuid}

    def print_table_indices(self, data_dict, use_pager=False):
        """Print enhanced indices table with Rich formatting and statistics - ORIGINAL DESIGN"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table
        from rich.console import Console

        console = Console()

        # Get theme styles
        theme_manager = getattr(self.es_client, 'theme_manager', None)
        if theme_manager is None:
            from display import ThemeManager
            config_manager = getattr(self.es_client, 'config_manager', None)
            theme_manager = ThemeManager(config_manager)
        styles = theme_manager.get_theme_styles()

        if not data_dict:
            # Use theme-aware styling for the no data message
            from display.style_system import StyleSystem
            style_system = StyleSystem(theme_manager)

            # Create a themed info panel for no data
            no_data_panel = style_system.create_info_panel(
                "No indices found in this cluster.\n\nThis could mean:\n• The cluster has no indices\n• Connection issues\n• Insufficient permissions",
                "Index Information",
                "🔵"
            )
            console.print(no_data_panel)
            return

        # Get cluster settings for hot/frozen detection
        try:
            cluster_all_settings = self.es_client.get_all_index_settings()
        except:
            cluster_all_settings = {}

        # Get hot indices info
        try:
            cluster_indices_hot_indexes = getattr(self.es_client, 'cluster_indices_hot_indexes', [])
        except:
            cluster_indices_hot_indexes = []

        # Get cluster info for title
        try:
            cluster_info = self.es_client.cluster_commands.get_cluster_info()
            cluster_name = cluster_info.get('cluster_name', 'Unknown')
            cluster_version = cluster_info.get('version', {}).get('number', 'Unknown')
        except Exception:
            cluster_name = 'Unknown'
            cluster_version = 'Unknown'

        # Calculate statistics
        total_indices = len(data_dict)
        health_counts = {'green': 0, 'yellow': 0, 'red': 0}
        status_counts = {'open': 0, 'close': 0}
        hot_count = 0
        frozen_count = 0

        # Count statistics
        for indice in data_dict:
            health_counts[indice['health']] = health_counts.get(indice['health'], 0) + 1
            status_counts[indice['status']] = status_counts.get(indice['status'], 0) + 1
            if indice['index'] in cluster_indices_hot_indexes:
                hot_count += 1

            index_settings = cluster_all_settings.get(indice['index'], {})
            if index_settings:
                frozen_status = index_settings.get('settings', {}).get('index', {}).get('frozen', False)
                if frozen_status == "true":
                    frozen_count += 1

        # Use semantic styling with theme manager
        style_system = self.es_client.style_system

        # Create colorized subtitle with theme-based styling for statistics
        from rich.text import Text
        subtitle_rich = Text()
        subtitle_rich.append("Total: ", style="default")
        subtitle_rich.append(str(total_indices), style=style_system._get_style('semantic', 'info', 'cyan'))
        subtitle_rich.append(" | Green: ", style="default")
        subtitle_rich.append(str(health_counts.get('green', 0)), style=style_system._get_style('semantic', 'success', 'green'))
        subtitle_rich.append(" | Yellow: ", style="default")
        subtitle_rich.append(str(health_counts.get('yellow', 0)), style=style_system._get_style('semantic', 'warning', 'yellow'))
        subtitle_rich.append(" | Red: ", style="default")
        subtitle_rich.append(str(health_counts.get('red', 0)), style=style_system._get_style('semantic', 'error', 'red'))

        if hot_count > 0:
            subtitle_rich.append(" | Hot: ", style="default")
            subtitle_rich.append(str(hot_count), style=style_system._get_style('semantic', 'primary', 'bright_magenta'))
        if frozen_count > 0:
            subtitle_rich.append(" | Frozen: ", style="default")
            subtitle_rich.append(str(frozen_count), style=style_system._get_style('semantic', 'secondary', 'bright_blue'))

        # Build status body text based on index health
        red_count = health_counts.get('red', 0)
        yellow_count = health_counts.get('yellow', 0)
        green_count = health_counts.get('green', 0)

        if red_count > 0:
            status_text = f"🔴 Critical - {red_count} Indic{'es' if red_count != 1 else 'e'} Red"
            body_style = f"bold {style_system.get_semantic_style('error')}"
            border = style_system.get_semantic_style('error')
        elif yellow_count > 0:
            status_text = f"🟡 Warning - {yellow_count} Indic{'es' if yellow_count != 1 else 'e'} Yellow"
            body_style = f"bold {style_system.get_semantic_style('warning')}"
            border = style_system.get_semantic_style('warning')
        else:
            status_text = f"✅ Cluster Healthy - {green_count} of {total_indices} Indices Green"
            body_style = f"bold {style_system.get_semantic_style('success')}"
            border = style_system._get_style('table_styles', 'border_style', 'bright_magenta')

        # Build cluster subtitle
        cluster_subtitle = Text()
        cluster_subtitle.append(cluster_name, style=style_system._get_style('semantic', 'primary', 'cyan'))
        cluster_subtitle.append("  ", style="default")
        cluster_subtitle.append(f"v{cluster_version}", style=style_system._get_style('semantic', 'muted', 'dim'))
        cluster_subtitle.append("   ", style="default")
        cluster_subtitle.append_text(subtitle_rich)

        title_panel = Panel(
            Text(status_text, style=body_style, justify="center"),
            title=style_system.create_semantic_text("📊 Elasticsearch Indices", "primary"),
            subtitle=cluster_subtitle,
            border_style=border,
            padding=(1, 2)
        )

        # Create enhanced indices table with semantic styling
        normal_style = style_system._get_style('table_styles', 'row_styles.normal', 'white')
        table = style_system.create_standard_table(
            title=None,
            style_variant='dashboard'
        )
        table.add_column("Index Name", style=normal_style, no_wrap=False, min_width=40)
        table.add_column("Health", justify="left", no_wrap=True)
        table.add_column("Status", justify="left", no_wrap=True)
        table.add_column("Docs", style=normal_style, justify="right", width=10)
        table.add_column("Shards", style=normal_style, justify="right", width=10)
        table.add_column("Primary", style=normal_style, justify="right", width=10)
        table.add_column("Total", style=normal_style, justify="right", width=10)

        for indice in data_dict:
            # Health formatting with semantic styling
            health = indice['health']
            health_mini = Table.grid(padding=(0, 1))
            health_mini.add_column(justify="center")
            health_mini.add_column(justify="left")

            if health == 'green':
                health_mini.add_row(style_system.create_semantic_text("◉", "success"),
                                   style_system.create_semantic_text("Green", "success"))
            elif health == 'yellow':
                health_mini.add_row(style_system.create_semantic_text("◐", "warning"),
                                   style_system.create_semantic_text("Yellow", "warning"))
            else:
                health_mini.add_row(style_system.create_semantic_text("○", "error"),
                                   style_system.create_semantic_text("Red", "error"))

            health_display = health_mini

            # Status with semantic styling
            status = indice['status']
            status_mini = Table.grid(padding=(0, 1))
            status_mini.add_column(justify="center")
            status_mini.add_column(justify="left")

            if status == 'open':
                status_mini.add_row(style_system.create_semantic_text("◆", "success"),
                                   style_system.create_semantic_text("Open", "success"))
            else:
                status_mini.add_row(style_system.create_semantic_text("◇", "warning"),
                                   style_system.create_semantic_text("Closed", "warning"))

            status_display = status_mini

            # Index name with hot/frozen indicators - ORIGINAL DESIGN
            indice_name = indice['index']

            # Determine foreground color based on health and index state
            health = indice['health']
            if health == 'red':
                fg_style = style_system.get_semantic_style('error')
            elif health == 'yellow':
                fg_style = style_system.get_semantic_style('warning')
            else:
                fg_style = style_system._get_style('table_styles', 'row_styles.normal', 'white')

            # Check if hot and add flame indicator
            if indice_name in cluster_indices_hot_indexes:
                indice_name = f"{indice_name} 🔥"
                fg_style = style_system._get_style('table_styles', 'row_styles.hot', 'bright_red')

            # Check if frozen and add snowflake indicator
            index_settings = cluster_all_settings.get(indice['index'], {})
            if index_settings:
                frozen_status = index_settings.get('settings', {}).get('index', {}).get('frozen', False)
                if frozen_status == "true":
                    indice_name = f"{indice_name} 🧊"
                    if not indice_name.endswith("🔥 🧊"):  # Only set frozen if not already hot
                        fg_style = style_system._get_style('table_styles', 'row_styles.frozen', 'bright_blue')

            # Combine foreground with theme-aware zebra background
            zebra_bg = style_system.get_zebra_style(data_dict.index(indice))
            row_style = f"{fg_style} {zebra_bg}" if zebra_bg else fg_style

            # Format numbers with proper commas - handle None, empty, and dash values
            docs_count_raw = indice.get('docs.count')
            if docs_count_raw is None or docs_count_raw == '-' or docs_count_raw == '':
                docs_count = '-'
            else:
                try:
                    docs_count = f"{int(docs_count_raw):,}"
                except (ValueError, TypeError):
                    docs_count = str(docs_count_raw)

            # Shard information - handle None values
            pri = indice.get('pri', '-')
            rep = indice.get('rep', '-')
            pri_rep = f"{pri}|{rep}"

            # Handle potential None values for size fields
            pri_store_size = indice.get('pri.store.size')
            store_size = indice.get('store.size')

            # Format sizes in human-readable format
            if pri_store_size is not None and pri_store_size != '-' and pri_store_size != '':
                try:
                    pri_store_display = self.es_client.format_bytes(int(pri_store_size))
                except (ValueError, TypeError):
                    pri_store_display = str(pri_store_size)
            else:
                pri_store_display = '-'

            if store_size is not None and store_size != '-' and store_size != '':
                try:
                    store_display = self.es_client.format_bytes(int(store_size))
                except (ValueError, TypeError):
                    store_display = str(store_size)
            else:
                store_display = '-'

            table.add_row(
                indice_name,
                health_display,
                status_display,
                docs_count,
                pri_rep,
                pri_store_display,
                store_display,
                style=row_style
            )

        # Check if we should use pager for large datasets
        from configuration_manager import ConfigurationManager
        import os

        try:
            from utils import get_script_dir
            _sd = get_script_dir()
            config_file = os.path.join(_sd, 'elastic_servers.yml')
            state_file = os.path.join(_sd, 'escmd.json')
            config_manager = ConfigurationManager(config_file, state_file)

            # Try to get paging settings with fallback to defaults
            paging_enabled = getattr(config_manager, 'get_paging_enabled', lambda: False)()
            paging_threshold = getattr(config_manager, 'get_paging_threshold', lambda: 50)()
        except Exception:
            # Fallback to safe defaults if configuration fails
            paging_enabled = False
            paging_threshold = 50

        should_use_pager = use_pager or (paging_enabled and len(data_dict) > paging_threshold)

        if should_use_pager:
            # First show in pager for scrolling through large datasets
            with console.pager():
                console.print()
                console.print(title_panel)
                console.print()
                console.print(table)
                console.print()

            # Then display normally so content remains visible after pager exit
            console.print()
            console.print(title_panel)
            console.print()
            console.print(table)
            console.print()
        else:
            # Normal display only
            console.print()
            console.print(title_panel)
            console.print()
            console.print(table)
            console.print()

    def freeze_index(self, index_name: str) -> bool:
        """
        Freeze an index to make it read-only.

        Args:
            index_name: The name of the index to freeze.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # First check if the index exists
            if not self.es_client.es.indices.exists(index=index_name):
                print(f"Index {index_name} does not exist.")
                return False

            # Freeze the index
            self.es_client.es.indices.freeze(index=index_name)
            return True
        except Exception as e:
            print(f"Error freezing index {index_name}: {str(e)}")
            return False

    def unfreeze_index(self, index_name: str) -> bool:
        """
        Unfreeze an index to make it writable again.

        Args:
            index_name: The name of the index to unfreeze.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # First check if the index exists
            if not self.es_client.es.indices.exists(index=index_name):
                print(f"Index {index_name} does not exist.")
                return False

            # Unfreeze the index
            self.es_client.es.indices.unfreeze(index=index_name)
            return True
        except Exception as e:
            print(f"Error unfreezing index {index_name}: {str(e)}")
            return False


# Backward compatibility functions
def list_indices_stats(es_client, pattern: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Backward compatibility function for existing code."""
    indices_cmd = IndicesCommands(es_client)
    return indices_cmd.list_indices_stats(pattern, status)

def delete_indices(
    es_client,
    indice_data: List[str],
    *,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    indices_cmd = IndicesCommands(es_client)
    return indices_cmd.delete_indices(indice_data, on_progress=on_progress)

def get_all_index_settings(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    indices_cmd = IndicesCommands(es_client)
    return indices_cmd.get_all_index_settings()

def list_dangling_indices(es_client) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    indices_cmd = IndicesCommands(es_client)
    return indices_cmd.list_dangling_indices()

def delete_dangling_index(es_client, uuid: str) -> Dict[str, Any]:
    """Backward compatibility function for existing code."""
    indices_cmd = IndicesCommands(es_client)
    return indices_cmd.delete_dangling_index(uuid)

def create_index(es_client, index_name: str, settings=None, mappings=None):
    """Backward compatibility function for existing code."""
    indices_cmd = IndicesCommands(es_client)
    return indices_cmd.create_index(index_name, settings, mappings)


def freeze_index(es_client, index_name: str) -> bool:
    """Backward compatibility function for existing code."""
    indices_cmd = IndicesCommands(es_client)
    return indices_cmd.freeze_index(index_name)


def unfreeze_index(es_client, index_name: str) -> bool:
    """Backward compatibility function for existing code."""
    indices_cmd = IndicesCommands(es_client)
    return indices_cmd.unfreeze_index(index_name)
