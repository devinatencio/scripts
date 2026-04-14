#!/usr/bin/env python3

import builtins
import json
import logging
import re
import time
from datetime import datetime
from handlers.utility_handler import UtilityHandler
from handlers.storage_handler import StorageHandler
from handlers.lifecycle_handler import LifecycleHandler
from handlers.cluster_handler import ClusterHandler
from handlers.allocation_handler import AllocationHandler
from handlers.index_handler import IndexHandler
from handlers.dangling_handler import DanglingHandler
from handlers.settings_handler import SettingsHandler
from handlers.snapshot_handler import SnapshotHandler
from handlers.shard_handler import ShardHandler
from handlers.datastream_handler import DatastreamHandler
from handlers.help_handler import HelpHandler
from handlers.themes_handler import ThemesHandler
from handlers.password_handler import PasswordCommands
from handlers.template_handler import TemplateHandler
from handlers.action_handler import ActionHandler
from handlers.estop_handler import EsTopHandler
import os

from configuration_manager import ConfigurationManager


class CommandHandler:
    def __init__(
        self,
        es_client,
        args,
        console,
        config_file,
        location_config,
        current_location=None,
        logger=None,
    ):
        self.es_client = es_client
        self.args = args
        self.console = console
        self.config_file = config_file
        self.location_config = location_config
        self.current_location = current_location
        self.logger = logger or logging.getLogger(__name__)

        # Initialize handlers
        self.utility_handler = UtilityHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.storage_handler = StorageHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.snapshot_handler = SnapshotHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.lifecycle_handler = LifecycleHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.cluster_handler = ClusterHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.allocation_handler = AllocationHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.index_handler = IndexHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.dangling_handler = DanglingHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.settings_handler = SettingsHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.shard_handler = ShardHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.datastream_handler = DatastreamHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.help_handler = HelpHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.themes_handler = ThemesHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.password_handler = PasswordCommands(
            None, args, console, config_file, location_config, current_location, logger
        )  # Password handler doesn't need ES client
        self.template_handler = TemplateHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.action_handler = ActionHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.estop_handler = EsTopHandler(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )

        # Create handlers dictionary for tests compatibility
        # Map to the actual handlers that execute() uses for each command type
        self.handlers = {
            "health": self.cluster_handler,  # health, ping -> cluster_handler
            "health-detail": self.cluster_handler,  # health-detail -> cluster_handler
            "index": self.index_handler,  # Use index_handler as base for index commands
            "allocation": self.allocation_handler,
            "ilm": self.lifecycle_handler,  # ilm, rollover, auto-rollover -> lifecycle_handler
            "shard": self.shard_handler,  # shards, shard-colocation -> shard_handler
            "snapshot": self.snapshot_handler,
            "replica": self.utility_handler,  # set-replicas -> utility_handler
            "node": self.cluster_handler,  # nodes -> cluster_handler
            "datastream": self.datastream_handler,  # datastreams -> datastream_handler
            "cluster-settings": self.settings_handler,
            "configuration": self.utility_handler,  # locations, cluster-check -> utility_handler
            "template": self.template_handler,  # templates, template, template-usage -> template_handler
        }

        # Add methods that don't exist on the mapped handlers but are expected by tests
        # cluster-check goes to utility_handler but tests expect it on health handler
        if not hasattr(self.handlers["health"], "handle_cluster_check"):
            self.handlers[
                "health"
            ].handle_cluster_check = self.utility_handler.handle_cluster_check

        # dangling goes to dangling_handler but tests expect it on index handler
        if not hasattr(self.handlers["index"], "handle_dangling"):
            self.handlers[
                "index"
            ].handle_dangling = self.dangling_handler.handle_dangling

    def execute(self):
        command_handlers = {
            "ping": self.cluster_handler.handle_ping,  # Using handler
            "allocation": self.allocation_handler.handle_allocation,  # Using handler
            "current-master": self.cluster_handler.handle_current_master,  # Using handler
            "flush": self.index_handler.handle_flush,  # Using handler
            "freeze": self.index_handler.handle_freeze,  # Using handler
            "unfreeze": self.index_handler.handle_unfreeze,  # Using handler
            "nodes": self.cluster_handler.handle_nodes,  # Using handler
            "masters": self.cluster_handler.handle_masters,  # Using handler
            "health": self.cluster_handler.handle_health,  # Using handler
            "health-detail": self.cluster_handler.handle_health_detail,  # Using handler
            "indice": self.index_handler.handle_indice,  # Using handler
            "indice-add-metadata": self.index_handler.handle_indice_add_metadata,  # Using handler
            "indices": self.index_handler.handle_indices,  # Using handler
            "indices-analyze": self.index_handler.handle_indices_analyze,
            "indices-s3-estimate": self.index_handler.handle_indices_s3_estimate,
            "indices-watch-collect": self.index_handler.handle_indices_watch_collect,
            "create-index": self.index_handler.handle_create_index,  # Using handler
            "locations": self.utility_handler.handle_locations,  # Using handler
            "recovery": self.index_handler.handle_recovery,  # Using handler
            "rollover": self.lifecycle_handler.handle_rollover,  # Using handler
            "auto-rollover": self.lifecycle_handler.handle_auto_rollover,  # Using handler
            "exclude": self.allocation_handler.handle_exclude,  # Using handler
            "exclude-reset": self.allocation_handler.handle_exclude_reset,  # Using handler
            "cluster-settings": self.settings_handler.handle_settings,  # Using handler
            "set": self.settings_handler.handle_set,  # Using handler
            "dangling": self.dangling_handler.handle_dangling,  # Using handler
            "storage": self.storage_handler.handle_storage,  # Using handler
            "shards": self.storage_handler.handle_shards,  # Using storage handler (temp for testing)
            "shard-colocation": self.storage_handler.handle_shard_colocation,  # Using storage handler (temp for testing)
            "snapshots": self.snapshot_handler.handle_snapshots,  # Using handler
            "ilm": self.lifecycle_handler.handle_ilm,  # Using handler
            "datastreams": self.datastream_handler.handle_datastreams,  # Using datastream handler
            "cluster-check": self.utility_handler.handle_cluster_check,  # Using handler
            "set-replicas": self.utility_handler.handle_set_replicas,  # Using handler
            "help": self.help_handler.handle_help,  # Using handler
            "themes": self.themes_handler.handle_themes,  # Using handler
            "show-settings": self.utility_handler.handle_show_settings,  # Using handler
            # Password management commands
            "store-password": lambda: self.password_handler.handle_store_password(
                self.args
            ),
            "list-stored-passwords": lambda: self.password_handler.handle_list_passwords(
                self.args
            ),
            "remove-stored-password": lambda: self.password_handler.handle_remove_password(
                self.args
            ),
            "clear-session": lambda: self.password_handler.handle_clear_session(
                self.args
            ),
            "session-info": lambda: self.password_handler.handle_session_info(
                self.args
            ),
            "set-session-timeout": lambda: self.password_handler.handle_set_session_timeout(
                self.args
            ),
            "generate-master-key": lambda: self.password_handler.handle_generate_master_key(
                self.args
            ),
            "migrate-to-env-key": lambda: self.password_handler.handle_migrate_to_env_key(
                self.args
            ),
            "rotate-master-key": lambda: self.password_handler.handle_rotate_master_key(
                self.args
            ),
            # Template management commands
            "templates": self.template_handler.handle_templates,  # Using handler
            "template": self.template_handler.handle_template,  # Using handler
            "template-usage": self.template_handler.handle_template_usage,  # Using handler
            # Template modification commands
            "template-modify": self.template_handler.handle_template_modify,
            "template-backup": self.template_handler.handle_template_backup,
            "template-restore": self.template_handler.handle_template_restore,
            "template-create": self.template_handler.handle_template_create,
            "list-backups": self.template_handler.handle_list_backups,
            # Action sequence commands
            "action": self.action_handler.handle_action,
            "repositories": self.snapshot_handler.handle_repositories,
            "es-top": self.estop_handler.handle_es_top,
            "top": self.estop_handler.handle_es_top,
        }

        handler = command_handlers.get(self.args.command)
        if handler:
            if self.logger:
                self.logger.info(f"Executing command: {self.args.command}")
            handler()
        else:
            error_msg = f"Unknown command: {self.args.command}"
            if self.logger:
                self.logger.error(error_msg)
            print(error_msg)
