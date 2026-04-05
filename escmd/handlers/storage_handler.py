"""
Storage handler for escmd storage and shard-related commands.

Handles commands like storage, shards, and shard-colocation.
"""

import re

from .base_handler import BaseHandler
from utils import safe_sort_shards_by_size


class StorageHandler(BaseHandler):
    """Handler for storage-related commands like storage, shards, and shard colocation."""

    def handle_storage(self):
        """Handle storage command - display storage allocation information."""
        allocation_data = self.es_client.get_allocation_as_dict()

        if self.args.format == 'json':
            self.es_client.pretty_print_json(allocation_data)
        else:
            # Get indices count for enhanced display
            indices_count = self._get_indices_count()
            self.es_client.print_enhanced_storage_table(allocation_data, indices_count)

    def handle_shards(self):
        """Handle shards command - display shard information with various filters."""
        if self.args.regex:
            self._handle_regex_shards()
            return
        self._handle_default_shards()

    def handle_shard_colocation(self):
        """
        Handle shard colocation detection command.
        Finds indices where primary and replica shards are on the same host.
        """
        try:
            # Get shard colocation analysis
            colocation_results = self.es_client.analyze_shard_colocation(pattern=self.args.regex)

            if self.args.format == 'json':
                self.es_client.pretty_print_json(colocation_results)
            else:
                use_pager = getattr(self.args, 'pager', False)
                self.es_client.print_shard_colocation_results(colocation_results, use_pager=use_pager)

        except Exception as e:
            # from utils import show_message_box
            self.es_client.show_message_box("Error", f"Failed to analyze shard colocation: {str(e)}", message_style="bold white", panel_style="red")

    def _handle_regex_shards(self):
        """Handle shards command when a regex pattern is provided."""
        if self.args.regex == 'unassigned':
            self._handle_unassigned_shards()
            return

        if self.args.format == 'json':
            shards_data = self.es_client.get_shards_stats(pattern=self.args.regex)

            # Apply the same filtering as default shards handling
            if self.args.size:
                shards_data = safe_sort_shards_by_size(shards_data, reverse=True)

            if self.args.server:
                search_location = self.args.server[0]
                pattern = f".*{search_location}.*"
                shards_data = [item for item in shards_data if item.get('node') and isinstance(item['node'], str) and re.search(pattern, item['node'], re.IGNORECASE)]

            if self.args.limit != 0:
                shards_data = shards_data[:int(self.args.limit)]

            self.es_client.pretty_print_json(shards_data)
            return

        shards_data = self.es_client.get_shards_stats(pattern=self.args.regex)

        # Apply the same filtering as default shards handling
        if self.args.size:
            shards_data = safe_sort_shards_by_size(shards_data, reverse=True)

        if self.args.server:
            search_location = self.args.server[0]
            pattern = f".*{search_location}.*"
            shards_data = [item for item in shards_data if item.get('node') and isinstance(item['node'], str) and re.search(pattern, item['node'], re.IGNORECASE)]

        if self.args.limit != 0:
            shards_data = shards_data[:int(self.args.limit)]

        use_pager = getattr(self.args, 'pager', False)
        self.es_client.print_table_shards(shards_data, use_pager=use_pager)

    def _handle_unassigned_shards(self):
        """Handle special case of showing only unassigned shards."""
        if self.args.format == 'json':
            shards_data = self.es_client.get_shards_stats(pattern='*')
            filtered_data = [item for item in shards_data if item['state'] == 'UNASSIGNED']
            self.es_client.pretty_print_json(filtered_data)
            return

        shards_data = self.es_client.get_shards_stats(pattern='*')
        filtered_data = [item for item in shards_data if item['state'] == 'UNASSIGNED']
        if not filtered_data:
            self.es_client.show_message_box(f'Results: Shards [ {self.args.locations} ]', 'There was no unassigned shards found in cluster.', 'white on blue', 'bold white')
        else:
            use_pager = getattr(self.args, 'pager', False)
            self.es_client.print_table_shards(filtered_data, use_pager=use_pager)



    def _handle_default_shards(self):
        """Handle default shards display with optional sorting and filtering."""
        shards_data_dict = self.es_client.get_shards_as_dict()

        if self.args.size:
            shards_data_dict = safe_sort_shards_by_size(shards_data_dict, reverse=True)

        if self.args.server:
            search_location = self.args.server[0]
            pattern = f".*{search_location}.*"
            shards_data_dict = [item for item in shards_data_dict if item.get('node') and isinstance(item['node'], str) and re.search(pattern, item['node'], re.IGNORECASE)]

        if self.args.limit != 0:
            shards_data_dict = shards_data_dict[:int(self.args.limit)]

        if self.args.format == 'json':
            self.es_client.pretty_print_json(shards_data_dict)
        else:
            use_pager = getattr(self.args, 'pager', False)
            self.es_client.print_table_shards(shards_data_dict, use_pager=use_pager)

    def _get_indices_count(self):
        """Get the total number of unique indices in the cluster."""
        try:
            # Get all indices
            indices_response = self.es_client.es.cat.indices(format='json')
            return len(indices_response)
        except Exception as e:
            # If we can't get indices count, return None so it won't be displayed
            return None
