"""
Handler for the es-top live dashboard command.
"""

from handlers.base_handler import BaseHandler
from commands.estop_commands import EsTopDashboard


class EsTopHandler(BaseHandler):
    """Handler for the es-top command — live Elasticsearch terminal dashboard."""

    def handle_es_top(self) -> None:
        """Parse args and run the es-top dashboard."""
        # Resolve config manager for settings fallback
        config_manager = getattr(self.es_client, 'configuration_manager', None)

        # Priority: CLI arg → escmd.yml es_top settings → hardcoded default
        cli_interval = getattr(self.args, 'interval', None)
        cli_top_nodes = getattr(self.args, 'top_nodes', None)
        cli_top_indices = getattr(self.args, 'top_indices', None)

        if config_manager:
            interval = max(10, cli_interval if cli_interval is not None else config_manager.get_estop_interval())
            top_nodes = cli_top_nodes if cli_top_nodes is not None else config_manager.get_estop_top_nodes()
            top_indices = cli_top_indices if cli_top_indices is not None else config_manager.get_estop_top_indices()
        else:
            interval = max(10, cli_interval if cli_interval is not None else 30)
            top_nodes = cli_top_nodes if cli_top_nodes is not None else 5
            top_indices = cli_top_indices if cli_top_indices is not None else 10

        dashboard = EsTopDashboard(
            es_client=self.es_client,
            interval=interval,
            top_nodes=top_nodes,
            top_indices=top_indices,
            console=self.console,
        )
        dashboard.run()
