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
        collect = getattr(self.args, 'collect', False)
        collect_dir = getattr(self.args, 'collect_dir', None)
        new_session = getattr(self.args, 'new_session', False) or False
        join_latest = getattr(self.args, 'join_latest', False) or False
        label = getattr(self.args, 'label', None)

        if config_manager:
            interval = max(10, cli_interval if cli_interval is not None else config_manager.get_estop_interval())
            top_nodes = cli_top_nodes if cli_top_nodes is not None else config_manager.get_estop_top_nodes()
            top_indices = cli_top_indices if cli_top_indices is not None else config_manager.get_estop_top_indices()
            hot_indicator = config_manager.get_estop_hot_indicator()
        else:
            interval = max(10, cli_interval if cli_interval is not None else 30)
            top_nodes = cli_top_nodes if cli_top_nodes is not None else 5
            top_indices = cli_top_indices if cli_top_indices is not None else 10
            hot_indicator = "emoji"

        dashboard = EsTopDashboard(
            es_client=self.es_client,
            interval=interval,
            top_nodes=top_nodes,
            top_indices=top_indices,
            console=self.console,
            hot_indicator=hot_indicator,
            collect=collect,
            collect_dir=collect_dir,
            current_location=self.current_location,
            new_session=new_session,
            join_latest=join_latest,
            label=label,
        )
        dashboard.run()
