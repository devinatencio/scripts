#!/usr/bin/env python3
"""
Administration tool for ElasticSearch, simplifies admin tasks.
"""

import os
import getpass
import sys
import importlib.metadata

# Check for minimum rich version before any other imports
def _check_rich_version():
    MIN_RICH = (14, 3, 3)
    try:
        raw = importlib.metadata.version("rich")
        parts = tuple(int(x) for x in raw.split(".")[:3])
        if parts >= MIN_RICH:
            return
    except Exception:
        raw = "not found"

    try:
        from rich.console import Console
        from rich.panel import Panel
        Console().print(Panel(
            f"Installed: [yellow]rich {raw}[/yellow]\n"
            f"Required:  [green]rich {'.'.join(str(x) for x in MIN_RICH)}+[/green]\n\n"
            "Upgrade with:\n\n  [bold cyan]pip install --upgrade rich[/bold cyan]",
            title="[bold red] Dependency Error[/bold red]",
            border_style="red",
        ))
    except Exception:
        print(f"ERROR: rich {'.'.join(str(x) for x in MIN_RICH)}+ is required "
              f"(found: {raw}). Run: pip install --upgrade rich")
    sys.exit(1)

_check_rich_version()

# Import Rich components
from rich import print
from rich.console import Console
from rich.panel import Panel

# Import core modules
from esclient import ElasticsearchClient
from command_handler import CommandHandler
from configuration_manager import ConfigurationManager
from handlers.password_handler import PasswordCommands
from error_handling import ConnectionError
from logging_config import get_logging_config

# Import new CLI modules
from cli import (
    create_argument_parser,
    show_custom_help,
    handle_version,
    handle_locations,
    handle_get_default,
    handle_set_default,
    handle_show_settings,
    handle_cluster_groups,
)
from cli.special_commands import show_welcome_screen

# Version information — single source of truth is version.py
from version import VERSION, DATE

# Commands that don't require Elasticsearch connection
NO_CONNECTION_COMMANDS = {
    "version",
    "locations",
    "get-default",
    "set-default",
    "set-username",
    "show-settings",
    "help",
    "themes",
    "set-theme",
    "store-password",
    "list-stored-passwords",
    "remove-stored-password",
    "clear-session",
    "session-info",
    "set-session-timeout",
    "generate-master-key",
    "migrate-to-env-key",
    "rotate-master-key",
    "indices-watch-report",
    "indices-watch-sessions",
    "list-backups",
    "cluster-groups"
}


def should_skip_default_cluster_connection(args):
    """
    Determine if we should skip default cluster connection validation.

    This applies to:
    1. Commands that explicitly don't need connection
    2. Environment-scoped commands that operate across multiple clusters
    3. Group-scoped commands that operate across multiple clusters

    Args:
        args: Parsed command line arguments

    Returns:
        bool: True if default cluster connection should be skipped
    """
    # Check if it's a no-connection command
    if hasattr(args, "command") and args.command in NO_CONNECTION_COMMANDS:
        return True

    # Check if it's an environment or group scoped command
    # These commands create their own connections to individual clusters
    if hasattr(args, "env") and args.env:
        return True

    if hasattr(args, "group") and args.group:
        return True

    return False


# Commands that don't need index preprocessing
NO_PREPROCESS_COMMANDS = {
    "health",
    "set-default",
    "get-default",
    "show-settings",
    "version",
    "dangling",
    "indices-watch-collect",
}


def handle_help_command(args, console):
    """
    Handle the help command without requiring Elasticsearch connection.

    Args:
        args: Parsed command line arguments
        console: Rich console instance
    """
    # Import here to avoid circular imports
    from handlers.help_handler import HelpHandler
    from configuration_manager import ConfigurationManager
    from display.theme_manager import ThemeManager

    # Initialize configuration manager to get theme settings
    try:
        # Use the same configuration initialization as the main flow
        config_manager = initialize_configuration()

        # Create theme manager
        theme_manager = ThemeManager(config_manager)

        # Create a mock es_client object with just the theme_manager
        class MockESClient:
            def __init__(self, theme_manager):
                self.theme_manager = theme_manager

        mock_es_client = MockESClient(theme_manager)

        # Create help handler with mock es_client that has theme_manager
        help_handler = HelpHandler(mock_es_client, args, console, None, None, None)
        help_handler.handle_help()

    except Exception as e:
        # Fallback to basic help handler if configuration fails
        help_handler = HelpHandler(None, args, console, None, None, None)
        help_handler.handle_help()


def handle_set_theme_command(args, config_manager, console):
    """
    Handle the set-theme command without requiring Elasticsearch connection.

    Args:
        args: Parsed command line arguments with theme_name
        config_manager: Configuration manager instance
        console: Rich console instance
    """
    # Import here to avoid circular imports
    from handlers.themes_handler import ThemesHandler

    # Determine the correct config file path based on configuration mode
    if config_manager.is_dual_file_mode:
        config_file = config_manager.main_config_path
    else:
        config_file = config_manager.config_file_path

    # Create a minimal themes handler without ES client
    # We pass None for es_client since set-theme doesn't use it
    themes_handler = ThemesHandler(None, args, console, config_file, None, None)
    themes_handler.handle_set_theme()


def handle_themes_command(args, config_manager, console):
    """
    Handle the themes command without requiring Elasticsearch connection.

    Args:
        args: Parsed command line arguments
        config_manager: Configuration manager instance
        console: Rich console instance
    """
    # Import here to avoid circular imports
    from handlers.themes_handler import ThemesHandler

    # Determine the correct config file path based on configuration mode
    if config_manager.is_dual_file_mode:
        config_file = config_manager.main_config_path
    else:
        config_file = config_manager.config_file_path

    # Create a minimal themes handler without ES client
    # We pass None for es_client since themes doesn't use it
    themes_handler = ThemesHandler(None, args, console, config_file, None, None)
    themes_handler.handle_themes()


def should_use_ascii_mode(config_manager):
    """
    Check if ASCII mode should be used by checking environment variable first, then configuration.

    Args:
        config_manager: Configuration manager instance

    Returns:
        bool: True if ASCII mode should be used
    """
    # Environment variable takes precedence
    env_ascii = os.environ.get("ESCMD_ASCII_MODE", "").lower() in ("true", "1", "yes")
    if env_ascii:
        return True

    # Fall back to configuration file setting
    return config_manager.get_ascii_mode()


def initialize_configuration():
    """
    Initialize configuration manager with support for dual-file configuration.

    The configuration system now supports two modes:
    1. Dual-file mode (recommended): escmd.yml for settings/passwords, elastic_servers.yml for servers
    2. Single-file mode (backward compatibility): elastic_servers.yml contains everything

    Environment variable overrides:
    - ESCMD_MAIN_CONFIG: Path to main configuration file (escmd.yml)
    - ESCMD_SERVERS_CONFIG: Path to servers configuration file
    - ELASTIC_SERVERS_CONFIG: Legacy single-file path (backward compatibility)
    - ESCMD_STATE: Path to state file
    """
    script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

    # Check for dual-file configuration environment variables
    main_config_file = os.environ.get("ESCMD_MAIN_CONFIG")
    servers_config_file = os.environ.get("ESCMD_SERVERS_CONFIG")

    # Check for legacy single-file configuration
    legacy_config_file = os.environ.get("ELASTIC_SERVERS_CONFIG")

    # State file configuration
    state_file = os.environ.get("ESCMD_STATE")
    if not state_file:
        state_file = os.environ.get("ESCMD_CONFIG")  # Backward compatibility
        if not state_file:
            state_file = os.path.join(script_directory, "escmd.json")

    # Determine configuration mode
    if main_config_file or servers_config_file:
        # Explicit dual-file mode via environment variables
        if not main_config_file:
            main_config_file = os.path.join(script_directory, "escmd.yml")
        if not servers_config_file:
            servers_config_file = os.path.join(script_directory, "elastic_servers.yml")

        return ConfigurationManager(
            state_file_path=state_file,
            main_config_path=main_config_file,
            servers_config_path=servers_config_file,
        )
    elif legacy_config_file:
        # Explicit single-file mode via environment variable
        return ConfigurationManager(
            config_file_path=legacy_config_file, state_file_path=state_file
        )
    else:
        # Auto-detection mode: Let ConfigurationManager decide
        # It will try dual-file first, fallback to single-file
        return ConfigurationManager(state_file_path=state_file)


def handle_special_commands(args, config_manager, console):
    """
    Handle commands that don't require Elasticsearch connection.

    Args:
        args: Parsed command line arguments
        config_manager: Configuration manager instance
        console: Rich console instance

    Returns:
        bool: True if command was handled (should exit), False otherwise
    """
    command = args.command

    if command == "version":
        handle_version(VERSION, DATE, config_manager)
        return True

    elif command == "locations":
        handle_locations(config_manager)
        return True

    elif command == "get-default":
        handle_get_default(config_manager)
        return True

    elif command == "set-default":
        location = getattr(args, "defaultcluster_cmd", "default")
        handle_set_default(location, config_manager)
        return True

    elif command == "show-settings":
        format_output = getattr(args, "format", None)
        handle_show_settings(config_manager, format_output)
        return True
    elif command == "cluster-groups":
        format_output = getattr(args, "format", None)
        handle_cluster_groups(config_manager, format_output)
        return True

    elif command == "help":
        handle_help_command(args, console)
        return True

    elif command == "set-theme":
        handle_set_theme_command(args, config_manager, console)
        return True

    elif command == "indices-watch-report":
        from processors.indices_watch import run_indices_watch_report

        run_indices_watch_report(args, console, config_manager)
        return True

    elif command == "indices-watch-sessions":
        from processors.indices_watch import run_indices_watch_sessions

        run_indices_watch_sessions(args, console, config_manager)
        return True

    elif command == "themes":
        handle_themes_command(args, config_manager, console)
        return True

    elif command == "set-username":
        from cli.special_commands import handle_set_username

        handle_set_username(args, config_manager)
        return True

    # Password management commands that don't need ES connection
    elif command in (
        "store-password",
        "list-stored-passwords",
        "remove-stored-password",
        "clear-session",
        "session-info",
        "set-session-timeout",
        "generate-master-key",
        "migrate-to-env-key",
        "rotate-master-key",
    ):
        # Create password handler without ES client
        state_file_path = getattr(config_manager, "state_file_path", None)
        password_handler = PasswordCommands(
            None, args, console, None, None, None, None,
            state_file_path=state_file_path,
            config_manager=config_manager
        )

        if command == "store-password":
            password_handler.handle_store_password(args)
        elif command == "list-stored-passwords":
            password_handler.handle_list_passwords(args)
        elif command == "remove-stored-password":
            password_handler.handle_remove_password(args)
        elif command == "clear-session":
            password_handler.handle_clear_session(args)
        elif command == "session-info":
            password_handler.handle_session_info(args)
        elif command == "set-session-timeout":
            password_handler.handle_set_session_timeout(args)
        elif command == "generate-master-key":
            password_handler.handle_generate_master_key(args)
        elif command == "migrate-to-env-key":
            password_handler.handle_migrate_to_env_key(args)
        elif command == "rotate-master-key":
            password_handler.handle_rotate_master_key(args)

        return True

    # Handle action commands that don't need ES connection (list and show)
    elif command in ("actions", "action"):
        action_cmd = getattr(args, "action_cmd", "list")
        if action_cmd in ("list", "show"):
            from handlers.action_handler import ActionHandler

            # Create action handler without ES client for non-connection commands
            action_handler = ActionHandler(None, args, console, None, None, None)
            action_handler.handle_action()
            return True

        # 'run' command needs ES connection, so don't handle here
        return False

    return False


def get_elasticsearch_config(args, config_manager, console):
    """
    Get Elasticsearch configuration and validate.

    Args:
        args: Parsed command line arguments
        config_manager: Configuration manager instance
        console: Rich console instance

    Returns:
        dict: Location configuration
    """
    # Determine which location to use
    es_location = (
        args.locations if args.locations else config_manager.get_default_cluster()
    )
    location_config = config_manager.get_server_config_by_location(es_location)

    if not location_config:
        error_text = f"Location: {es_location} not found.\nPlease check your elastic_settings.yml config file."

        # Use theme-aware error styling
        from display import ThemeManager

        theme_manager = ThemeManager(config_manager)
        from display.style_system import StyleSystem

        style_system = StyleSystem(theme_manager)

        error_panel = Panel.fit(
            style_system.create_semantic_text(error_text, "white"),
            title=style_system.create_semantic_text("🔶  Configuration Error", "error"),
            border_style=style_system.get_semantic_style("error"),
            padding=(1, 2),
        )
        console.print(error_panel)
        # Raise exception instead of sys.exit(1) to allow graceful handling
        raise ValueError(f"Location: {es_location} not found")

    return location_config, es_location


def create_elasticsearch_client(
    location_config, config_manager, args, skip_connection_test=False
):
    """
    Create and configure Elasticsearch client.

    Args:
        location_config: Location-specific configuration
        config_manager: Configuration manager instance
        args: Parsed command line arguments
        skip_connection_test: If True, skip connection validation

    Returns:
        ElasticsearchClient: Configured ES client
    """
    # Extract configuration values
    elastic_host = location_config["elastic_host"]
    elastic_host2 = location_config["elastic_host2"]
    elastic_port = location_config["elastic_port"]
    elastic_use_ssl = location_config["use_ssl"]
    elastic_username = location_config["elastic_username"]
    elastic_password = location_config["elastic_password"]
    elastic_authentication = location_config.get("elastic_authentication", False)
    elastic_verify_certs = location_config.get("verify_certs", False)

    # Get timeout configuration (allow per-server override)
    elastic_read_timeout = location_config.get(
        "read_timeout", config_manager.get_read_timeout()
    )
    location_config["read_timeout"] = int(elastic_read_timeout)

    # Prompt for password if needed
    if elastic_authentication and (
        elastic_password is None or elastic_password == "None"
    ):
        elastic_password = getpass.getpass(prompt="Enter your Password: ")
        # Update the location_config with the prompted password so it gets passed to the client
        location_config["elastic_password"] = elastic_password

    # Determine if index preprocessing is needed
    preprocess_indices = args.command not in NO_PREPROCESS_COMMANDS

    # Add the server config from location_config to config_manager for the new client
    config_manager.server_config = location_config
    config_manager.preprocess_indices = preprocess_indices

    # Create client with new simplified interface
    return ElasticsearchClient(
        config_manager, skip_connection_test=skip_connection_test
    )


def main():
    """Main entry point for escmd."""
    # Initialize console
    console = Console()

    # Rewrite `action <name>` → `action run <name>` when <name> is not a known subcommand.
    # This lets users type `action add-host` instead of `action run add-host`, and also
    # prevents argparse from printing its own ugly error for unrecognised subcommands.
    _ACTION_SUBCMDS = {"list", "show", "run", "-h", "--help"}
    try:
        _ai = sys.argv.index("actions")
        _after = sys.argv[_ai + 1] if _ai + 1 < len(sys.argv) else None
        if _after is not None and not _after.startswith("-") and _after not in _ACTION_SUBCMDS:
            sys.argv.insert(_ai + 1, "run")
    except ValueError:
        pass

    # Also support the old "action" (singular) shorthand
    try:
        _ai = sys.argv.index("action")
        _after = sys.argv[_ai + 1] if _ai + 1 < len(sys.argv) else None
        if _after is not None and not _after.startswith("-") and _after not in _ACTION_SUBCMDS:
            sys.argv.insert(_ai + 1, "run")
    except ValueError:
        pass

    # Create argument parser
    parser = create_argument_parser()

    # Parse arguments
    args = parser.parse_args()

    # Set up logging configuration
    script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
    logging_config = get_logging_config(script_directory)

    # Determine if this is a command that should log to file (like for cron jobs)
    commands_to_log = ["dangling", "storage", "lifecycle", "cleanup", "repositories"]
    should_log_to_file = hasattr(args, "command") and args.command in commands_to_log

    logger = None
    if should_log_to_file:
        # Set up command-specific logging for cron jobs
        env = getattr(args, "env", None)
        log_level = getattr(args, "log_level", "INFO")
        logger = logging_config.setup_command_logging(
            command=args.command, env=env, log_level=log_level
        )
        logger.info(f"Starting escmd command: {args.command}")
        if env:
            logger.info(f"Environment: {env}")
        if hasattr(args, "metrics") and args.metrics:
            logger.info("Metrics reporting enabled")

    # Handle help display
    if args.help:
        # Initialize configuration for themed help
        config_manager = initialize_configuration()
        show_custom_help(config_manager)
        sys.exit(0)

    # Handle case with no command
    if not args.command:
        show_welcome_screen(console, VERSION, DATE)
        sys.exit(0)

    # Initialize configuration
    config_manager = initialize_configuration()

    # Handle special commands that don't need ES connection
    if handle_special_commands(args, config_manager, console):
        sys.exit(0)

    # Check if we should skip default cluster connection validation
    skip_default_connection = should_skip_default_cluster_connection(args)

    if skip_default_connection:
        # For environment/group commands, create a minimal config to satisfy ES client initialization
        # The actual connections will be made by the individual command handlers
        location_config = {
            "elastic_host": "localhost",
            "elastic_host2": None,
            "elastic_host3": None,
            "elastic_port": 9200,
            "use_ssl": False,
            "elastic_username": None,
            "elastic_password": None,
            "elastic_authentication": False,
            "verify_certs": False,
            "read_timeout": config_manager.get_read_timeout(),
        }
        es_location = "environment-scoped"
        config_file = config_manager.config_file_path
    else:
        # Get Elasticsearch configuration
        try:
            location_config, es_location = get_elasticsearch_config(
                args, config_manager, console
            )
            config_file = config_manager.config_file_path
        except ValueError:
            # Configuration error already displayed by get_elasticsearch_config, exit gracefully
            sys.exit(1)

    # Create Elasticsearch client
    try:
        es_client = create_elasticsearch_client(
            location_config,
            config_manager,
            args,
            skip_connection_test=skip_default_connection,
        )
    except ConnectionError as e:
        if not skip_default_connection:
            # Connection error already displayed by the client, exit gracefully
            sys.exit(1)
        else:
            # This shouldn't happen for skip_default_connection=True, but handle gracefully
            console.print(
                Panel.fit(
                    f"[bold white]Unexpected connection error:[/bold white]\n{str(e)}",
                    title="[bold red]⚡ Connection Error[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            sys.exit(1)
    except Exception as e:
        console.print(
            Panel.fit(
                f"[bold white]An unexpected error occurred:[/bold white]\n{str(e)}",
                title="[bold red]✗ Unexpected Error[/bold red]",
                border_style="red",
                padding=(1, 2),
            )
        )
        sys.exit(1)

    # Create and execute command handler
    command_handler = CommandHandler(
        es_client, args, console, config_file, location_config, es_location, logger
    )

    try:
        command_handler.execute()
        if logger:
            logger.info(f"Command {args.command} completed successfully")
    except Exception as e:
        if logger:
            logger.error(f"Command {args.command} failed with error: {str(e)}")
        console.print(
            Panel.fit(
                f"[bold white]Command:[/bold white] [cyan]{args.command}[/cyan]\n"
                f"[bold white]Error:[/bold white]   {str(e)}",
                title="[bold red]✗ Command Failed[/bold red]",
                border_style="red",
                padding=(1, 2),
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
