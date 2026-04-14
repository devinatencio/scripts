"""
Argument parser module for escmd.
Handles all command-line argument parsing and subcommand configuration.
"""

import argparse


def create_argument_parser():
    """Create and return the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description="Elasticsearch command-line tool", add_help=False
    )

    # Global arguments
    parser.add_argument(
        "-l",
        "--locations",
        help="Location (defaults to localhost)",
        type=str,
        default=None,
    )
    parser.add_argument(
        "-h", "--help", action="store_true", help="Show this help message and exit"
    )

    # Create subparsers
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    # Add all subcommands
    _add_help_command(subparsers)
    _add_basic_commands(subparsers)
    _add_allocation_commands(subparsers)
    _add_snapshot_commands(subparsers)
    _add_ilm_commands(subparsers)
    _add_utility_commands(subparsers)
    _add_password_commands(subparsers)
    _add_action_commands(subparsers)
    _add_estop_command(subparsers)

    return parser


def _add_help_command(subparsers):
    """Add global help command for major functionality."""
    help_parser = subparsers.add_parser(
        "help", help="Show detailed help for specific commands"
    )
    help_parser.add_argument(
        "topic",
        nargs="?",
        choices=[
            "indices",
            "indices-analyze",
            "indices-s3-estimate",
            "indices-watch-collect",
            "indices-watch-report",
            "ilm",
            "health",
            "nodes",
            "allocation",
            "snapshots",
            "repositories",
            "dangling",
            "shards",
            "exclude",
            "security",
            "freeze",
            "unfreeze",
            "indice-add-metadata",
            "templates",
            "template-backup",
            "template-modify",
            "template-restore",
            "store-password",
            "actions",
            "action",
            "es-top",
            "top",
        ],
        help="Command to show help for",
    )


def _add_basic_commands(subparsers):
    """Add basic node and cluster management commands."""

    # Health command - now simplified (previously health -q)
    health_parser = subparsers.add_parser("health", help="Show Basic Cluster Health")
    health_parser.add_argument(
        "--format",
        choices=["json", "table"],
        nargs="?",
        default="table",
        help="Output format (json or table)",
    )
    health_parser.add_argument(
        "--group", help="Show health for all clusters in a group (e.g., --group att)"
    )

    # Health Detail command - comprehensive health with all features (previously default health)
    health_detail_parser = subparsers.add_parser(
        "health-detail", help="Show Detailed Cluster Health Dashboard"
    )
    health_detail_parser.add_argument(
        "--format",
        choices=["json", "table"],
        nargs="?",
        default="table",
        help="Output format (json or table)",
    )
    health_detail_parser.add_argument(
        "--style",
        choices=["dashboard", "classic"],
        default=None,
        help="Display style (dashboard or classic table) - overrides config file setting",
    )
    health_detail_parser.add_argument(
        "--classic-style",
        choices=["table", "panel"],
        default=None,
        help="Classic display format (table or panel) - overrides config file setting",
    )
    health_detail_parser.add_argument(
        "--compare",
        help="Compare with another cluster (e.g., --compare production). Forces classic style.",
    )
    health_detail_parser.add_argument(
        "--group",
        help="Show health for all clusters in a group (e.g., --group att). Forces classic style.",
    )

    # Current master command
    current_master_parser = subparsers.add_parser(
        "current-master", help="List Current Master"
    )
    current_master_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    # Masters command
    masters_parser = subparsers.add_parser("masters", help="List ES Master nodes")
    masters_parser.add_argument(
        "--format",
        choices=["json", "table"],
        nargs="?",
        default="table",
        help="Output format (json or table)",
    )

    # Nodes command
    nodes_parser = subparsers.add_parser("nodes", help="List Elasticsearch nodes")
    nodes_parser.add_argument(
        "--format",
        choices=["data", "json", "table"],
        nargs="?",
        default="table",
        help="Output format (json or table)",
    )

    # Indices command
    indices_parser = subparsers.add_parser("indices", help="Indices")
    indices_parser.add_argument("--cold", action="store_true", default=False)
    indices_parser.add_argument("--delete", action="store_true", default=False)
    indices_parser.add_argument(
        "--format",
        choices=["json", "table"],
        nargs="?",
        default="table",
        help="List indices",
    )
    indices_parser.add_argument(
        "--status", choices=["green", "yellow", "red"], nargs="?", default=None
    )
    indices_parser.add_argument(
        "--pager",
        action="store_true",
        default=False,
        help="Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)",
    )
    indices_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Automatically answer yes to deletion confirmation prompts",
    )
    indices_parser.add_argument("regex", nargs="?", default=None, help="Regex")

    indices_analyze_parser = subparsers.add_parser(
        "indices-analyze",
        help="Find backing indices whose size/doc count diverges from sibling medians",
    )
    indices_analyze_parser.add_argument(
        "regex",
        nargs="?",
        default=None,
        help="Optional pattern to filter indices (same as indices)",
    )
    indices_analyze_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )
    indices_analyze_parser.add_argument(
        "--status",
        choices=["green", "yellow", "red"],
        default=None,
        help="Only include indices with this health",
    )
    indices_analyze_parser.add_argument(
        "--min-peers",
        type=int,
        default=1,
        metavar="N",
        help="Minimum other backing indices required in the series (default: 1)",
    )
    indices_analyze_parser.add_argument(
        "--min-ratio",
        type=float,
        default=5.0,
        metavar="R",
        help="Only show indices with doc count >= R times peer median (default: 5)",
    )
    indices_analyze_parser.add_argument(
        "--min-docs",
        type=int,
        default=1_000_000,
        metavar="N",
        dest="min_docs",
        help=(
            "Only show outliers with at least N documents on that index (default: 1000000). "
            "Use 0 to disable"
        ),
    )
    indices_analyze_parser.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="N",
        help="Limit output to top N rows by docs ratio (after sort)",
    )
    indices_analyze_parser.add_argument(
        "--within-days",
        type=int,
        default=None,
        metavar="N",
        dest="within_days",
        help=(
            "Only show outliers whose rollover date in the index name is within the last N "
            "calendar days (UTC, inclusive of cutoff day)"
        ),
    )
    indices_analyze_parser.add_argument(
        "--pager",
        action="store_true",
        default=False,
        help="Force pager for scrolling (auto-enabled based on config)",
    )

    indices_s3_estimate_parser = subparsers.add_parser(
        "indices-s3-estimate",
        help=(
            "Estimate monthly S3 storage cost from primary shard sizes for indices in a UTC window"
        ),
    )
    indices_s3_estimate_parser.add_argument(
        "regex",
        nargs="?",
        default=None,
        help="Optional pattern to filter indices (same as indices)",
    )
    indices_s3_estimate_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )
    indices_s3_estimate_parser.add_argument(
        "--status",
        choices=["green", "yellow", "red"],
        default=None,
        help="Only include indices with this health",
    )
    indices_s3_estimate_parser.add_argument(
        "--within-days",
        type=int,
        default=30,
        metavar="N",
        dest="within_days",
        help=(
            "Include indices whose rollover date in the name is on or after UTC today minus N "
            "calendar days (default: 30)"
        ),
    )
    indices_s3_estimate_parser.add_argument(
        "--buffer-percent",
        type=float,
        default=0.0,
        metavar="P",
        dest="buffer_percent",
        help="Scale total primary bytes by (1 + P/100) before pricing (default: 0)",
    )
    indices_s3_estimate_parser.add_argument(
        "--price-per-gib-month",
        type=float,
        required=True,
        metavar="USD",
        dest="price_per_gib_month",
        help="Storage class price in USD per gibibyte-month (1024^3 bytes), e.g. S3 Standard list price",
    )
    indices_s3_estimate_parser.add_argument(
        "--include-undated",
        action="store_true",
        default=False,
        dest="include_undated",
        help=(
            "Add pri.store.size for indices without YYYY.MM.DD in the name (can double-count vs "
            "dated series; use with care)"
        ),
    )

    indices_watch_collect_parser = subparsers.add_parser(
        "indices-watch-collect",
        help="Sample _cat index stats on an interval; writes JSON under ~/.escmd/index-watch/<cluster>/<date>/",
    )
    indices_watch_collect_parser.add_argument(
        "--output-dir",
        dest="collect_output_dir",
        default=None,
        metavar="PATH",
        help="Override output directory (default: ~/.escmd/index-watch/<cluster>/<UTC-date> or ESCMD_INDEX_WATCH_DIR)",
    )
    indices_watch_collect_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="SEC",
        help="Seconds between samples (default: 60)",
    )
    indices_watch_collect_parser.add_argument(
        "--duration",
        type=int,
        default=None,
        metavar="SEC",
        help="Stop after this many seconds (default: run until Ctrl+C)",
    )
    indices_watch_collect_parser.add_argument(
        "regex",
        nargs="?",
        default=None,
        help="Optional index pattern filter (same regex semantics as indices command)",
    )
    indices_watch_collect_parser.add_argument(
        "--status",
        choices=["green", "yellow", "red"],
        default=None,
        help="Only include indices with this health",
    )
    indices_watch_collect_parser.add_argument(
        "--retries",
        type=int,
        default=3,
        metavar="N",
        help="Retries per host for each sample (default: 3)",
    )
    indices_watch_collect_parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        metavar="SEC",
        help="Delay between retries (default: 2)",
    )

    indices_watch_collect_parser.add_argument(
        "--new-session",
        action="store_true",
        default=False,
        dest="new_session",
        help="Skip session picker; always create a fresh session directory",
    )
    indices_watch_collect_parser.add_argument(
        "--join-latest",
        action="store_true",
        default=False,
        dest="join_latest",
        help="Skip session picker; join the most recently started session (or create new if none exist)",
    )
    indices_watch_collect_parser.add_argument(
        "--label",
        default=None,
        dest="label",
        metavar="LABEL",
        help="Human-readable label appended to the session ID (e.g. 'load-test')",
    )

    indices_watch_report_parser = subparsers.add_parser(
        "indices-watch-report",
        help="Summarize collected samples (no ES connection); defaults to today's UTC date for -l / default cluster",
    )
    indices_watch_report_parser.add_argument(
        "--dir",
        dest="report_sample_dir",
        default=None,
        metavar="PATH",
        help="Sample directory (default: ~/.escmd/index-watch/<cluster>/<UTC-date>)",
    )
    indices_watch_report_parser.add_argument(
        "--cluster",
        default=None,
        metavar="NAME",
        help="Cluster slug for default path when -l is not used (overrides default cluster from state)",
    )
    indices_watch_report_parser.add_argument(
        "--date",
        default=None,
        metavar="YYYY-MM-DD",
        help="UTC date folder (default: today's UTC date)",
    )
    indices_watch_report_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )
    indices_watch_report_parser.add_argument(
        "--min-docs-delta",
        type=int,
        default=0,
        metavar="N",
        dest="min_docs_delta",
        help=(
            "Hide rows with doc increase below N (default: 0). "
            "Indices with no doc count change (Δ docs = 0) are always omitted."
        ),
    )
    indices_watch_report_parser.add_argument(
        "--hot-ratio",
        type=float,
        default=2.0,
        metavar="R",
        dest="hot_ratio",
        help="Mark HOT when docs/s >= R times leave-one-out peer median in the rollover series (default: 2)",
    )
    indices_watch_report_parser.add_argument(
        "--min-peers",
        type=int,
        default=1,
        metavar="N",
        dest="min_peers",
        help=(
            "Minimum other backing indices in the rollover group required for rate/med, "
            "docs/med, and HOT/⚠ (default: 1)"
        ),
    )
    indices_watch_report_parser.add_argument(
        "--docs-peer-ratio",
        type=float,
        default=5.0,
        metavar="R",
        dest="docs_peer_ratio",
        help=(
            "Flag ⚠ when last-sample doc count ≥ R × leave-one-out median peer doc count "
            "(same series). Use 0 to show docs/med without ⚠ (default: 5)"
        ),
    )
    indices_watch_report_parser.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="N",
        help="Show only top N rows by primary sort key (med docs/s or span docs/s)",
    )
    indices_watch_report_parser.add_argument(
        "--rate-stats",
        choices=["auto", "span", "intervals"],
        default="auto",
        dest="watch_rate_stats",
        help=(
            "auto: med/p90/max per-interval docs/s when ≥3 samples, else span docs/s only; "
            "span: one full-window docs/s column; "
            "intervals: med/p90/max (+ span/s) from adjacent-sample pairs"
        ),
    )
    indices_watch_report_parser.add_argument(
        "--session",
        default=None,
        dest="session_id",
        metavar="SESSION_ID",
        help="Load from the named session under the resolved date directory",
    )
    indices_watch_report_parser.add_argument(
        "--list-sessions",
        action="store_true",
        default=False,
        dest="list_sessions",
        help="Print available sessions for the resolved cluster and date, then exit",
    )

    # Indice command (single index)
    indice_parser = subparsers.add_parser("indice", help="Indice - Single One")
    indice_parser.add_argument("indice", nargs="?", default=None)

    # Indice add metadata command
    indice_add_metadata_parser = subparsers.add_parser(
        "indice-add-metadata", help="Add metadata to an index"
    )
    indice_add_metadata_parser.add_argument(
        "indice_name", help="Name of the index to add metadata to"
    )
    indice_add_metadata_parser.add_argument(
        "metadata_json", help="JSON string containing metadata to add"
    )

    # Create index command
    create_index_parser = subparsers.add_parser(
        "create-index", help="Create a new empty index with custom settings"
    )
    create_index_parser.add_argument("index_name", help="Name of the index to create")
    create_index_parser.add_argument(
        "--shards",
        "-s",
        type=int,
        default=1,
        help="Number of primary shards (default: 1)",
    )
    create_index_parser.add_argument(
        "--replicas",
        "-r",
        type=int,
        default=1,
        help="Number of replica shards (default: 1)",
    )
    create_index_parser.add_argument(
        "--settings", help="JSON string of custom index settings"
    )
    create_index_parser.add_argument(
        "--mappings", help="JSON string of custom index mappings"
    )
    create_index_parser.add_argument(
        "--format", choices=["json", "table"], default="table", help="Output format"
    )

    # Recovery command
    recovery_parser = subparsers.add_parser("recovery", help="List Recovery Jobs")
    recovery_parser.add_argument(
        "--format",
        choices=["data", "json", "table"],
        nargs="?",
        default="table",
        help="Output format (json or table)",
    )

    # Cluster Settings command
    cluster_settings_parser = subparsers.add_parser(
        "cluster-settings", help="Show Elasticsearch Cluster Settings"
    )
    cluster_settings_parser.add_argument(
        "--format",
        choices=["table", "json"],
        nargs="?",
        default="table",
        help="Output format (json or table)",
    )
    cluster_settings_parser.add_argument(
        "settings_cmd",
        choices=["display", "show"],
        nargs="?",
        default="display",
        help="Show Settings",
    )

    # Set cluster settings command
    set_parser = subparsers.add_parser(
        "set", help="Set Elasticsearch cluster settings using dot notation"
    )
    set_parser.add_argument(
        "setting_type",
        choices=["transient", "persistent"],
        help="Setting type: transient (resets after restart) or persistent (survives restart)",
    )
    set_parser.add_argument(
        "setting_key",
        help="Setting key in dot notation (e.g., cluster.routing.allocation.node_concurrent_recoveries)",
    )
    set_parser.add_argument(
        "setting_value", help='Setting value (use "null" to reset/remove a setting)'
    )
    set_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    set_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be set without actually applying the setting",
    )
    set_parser.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompt"
    )

    # Storage command
    storage_parser = subparsers.add_parser("storage", help="List ES Disk Usage")
    storage_parser.add_argument(
        "--format",
        choices=["data", "json", "table"],
        nargs="?",
        default="table",
        help="Output format (json or table)",
    )

    # Shards command
    shards_parser = subparsers.add_parser("shards", help="Show Shards")
    shards_parser.add_argument(
        "--format",
        choices=["data", "json", "table"],
        nargs="?",
        default="table",
        help="Output format (json or table)",
    )
    shards_parser.add_argument(
        "--server", "-s", nargs=1, default=None, help="Limit by server (ie: ess46)"
    )
    shards_parser.add_argument(
        "--limit", "-n", default=0, help="Limit by XX rows (ie: 10)"
    )
    shards_parser.add_argument(
        "--size", "-z", action="store_true", default=False, help="Sort by size"
    )
    shards_parser.add_argument(
        "--pager",
        action="store_true",
        default=False,
        help="Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)",
    )
    shards_parser.add_argument("regex", nargs="?", default=None, help="Regex")

    # Shard colocation command
    shard_colocation_parser = subparsers.add_parser(
        "shard-colocation",
        help="Find indices with primary and replica shards on the same host",
    )
    shard_colocation_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    shard_colocation_parser.add_argument(
        "--pager",
        action="store_true",
        default=False,
        help="Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)",
    )
    shard_colocation_parser.add_argument(
        "regex",
        nargs="?",
        default=None,
        help="Optional regex pattern to filter indices",
    )

    # Rollover commands
    rollover_parser = subparsers.add_parser(
        "rollover", help="Rollover Single Datastream"
    )
    rollover_parser.add_argument(
        "datastream", nargs="?", default=None, help="Datastream to match"
    )
    rollover_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    autorollover_parser = subparsers.add_parser(
        "auto-rollover", help="Rollover biggest shard"
    )
    autorollover_parser.add_argument(
        "host", nargs="?", default=None, help="Hostname (regex) to match."
    )

    # Ping command
    ping_parser = subparsers.add_parser("ping", help="Check ES Connection")
    ping_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    # Dangling indices command (complex arguments)
    dangling_parser = subparsers.add_parser(
        "dangling", help="List, analyze, and manage dangling indices"
    )
    dangling_parser.add_argument(
        "uuid", nargs="?", default=None, help="Index UUID to delete (optional)"
    )
    dangling_parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the specified dangling index by UUID",
    )
    dangling_parser.add_argument(
        "--cleanup-all",
        action="store_true",
        help="Automatically delete ALL found dangling indices",
    )
    dangling_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    dangling_parser.add_argument(
        "--max-retries", type=int, default=3, help="Maximum retry attempts (default: 3)"
    )
    dangling_parser.add_argument(
        "--retry-delay",
        type=int,
        default=5,
        help="Delay between retries in seconds (default: 5)",
    )
    dangling_parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Operation timeout in seconds (default: 60)",
    )
    dangling_parser.add_argument("--log-file", help="Path to log file (optional)")
    dangling_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    def positive_int(value):
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(
                f"Batch size must be a positive integer, got: {value}"
            )
        return ivalue

    dangling_parser.add_argument(
        "--batch",
        type=positive_int,
        default=None,
        help="Number of dangling indices to delete in this batch (must be positive)",
    )
    dangling_parser.add_argument(
        "--yes-i-really-mean-it",
        action="store_true",
        help="Skip confirmation prompt for deletion (use with extreme caution)",
    )
    dangling_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    dangling_parser.add_argument(
        "--group",
        type=str,
        default=None,
        help="Run dangling report across all clusters in the specified cluster group",
    )
    dangling_parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Run dangling report across all clusters in the specified environment",
    )
    dangling_parser.add_argument(
        "--metrics",
        action="store_true",
        help="Send dangling indices metrics to InfluxDB/VictoriaMetrics",
    )

    # Commands with specific arguments
    exclude_parser = subparsers.add_parser("exclude", help="Exclude Indice from Host")
    exclude_parser.add_argument(
        "indice", nargs="?", default=None, help="Indice to exclude"
    )
    exclude_parser.add_argument(
        "--server",
        "-s",
        nargs=1,
        default=None,
        help="Server to exclude (ie: aex10-c01-ess01-1)",
    )

    excludereset_parser = subparsers.add_parser(
        "exclude-reset", help="Remove Settings from Indice"
    )
    excludereset_parser.add_argument(
        "indice", nargs="?", default=None, help="Indice to reset"
    )

    flush_parser = subparsers.add_parser("flush", help="Perform Elasticsearch Flush")

    freeze_parser = subparsers.add_parser(
        "freeze", help="Freeze an Elasticsearch index"
    )
    freeze_parser.add_argument("pattern", help="Index name or regex pattern to freeze")
    freeze_parser.add_argument(
        "--regex", "-r", action="store_true", help="Treat pattern as regex"
    )
    freeze_parser.add_argument(
        "--exact",
        "-e",
        action="store_true",
        help="Force exact match (disable auto-regex detection)",
    )
    freeze_parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt"
    )

    unfreeze_parser = subparsers.add_parser(
        "unfreeze", help="Unfreeze an Elasticsearch index"
    )
    unfreeze_parser.add_argument(
        "pattern", help="Index name or regex pattern to unfreeze"
    )
    unfreeze_parser.add_argument(
        "--regex", "-r", action="store_true", help="Treat pattern as regex"
    )
    unfreeze_parser.add_argument(
        "--exact",
        "-e",
        action="store_true",
        help="Force exact match (disable auto-regex detection)",
    )
    unfreeze_parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt"
    )

    # Template commands
    templates_parser = subparsers.add_parser(
        "templates", help="List all Elasticsearch templates"
    )
    templates_parser.add_argument(
        "--type",
        choices=["all", "legacy", "composable", "component"],
        default="all",
        help="Type of templates to list (default: all)",
    )
    templates_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    templates_parser.add_argument(
        "--pager",
        action="store_true",
        default=False,
        help="Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)",
    )

    template_parser = subparsers.add_parser(
        "template", help="Show detailed information about a specific template"
    )
    template_parser.add_argument("name", help="Template name to inspect")
    template_parser.add_argument(
        "--type",
        choices=["auto", "legacy", "composable", "component"],
        default="auto",
        help="Template type (default: auto-detect)",
    )
    template_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    template_usage_parser = subparsers.add_parser(
        "template-usage", help="Analyze template usage across indices"
    )
    template_usage_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    template_usage_parser.add_argument(
        "--pager",
        action="store_true",
        default=False,
        help="Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)",
    )

    # Template modification commands
    template_modify_parser = subparsers.add_parser(
        "template-modify",
        help="Modify template fields with set/append/remove/delete operations",
    )
    template_modify_parser.add_argument("name", help="Template name to modify")
    template_modify_parser.add_argument(
        "--type",
        "-t",
        choices=["auto", "legacy", "composable", "component"],
        default="auto",
        help="Template type (default: auto-detect)",
    )
    template_modify_parser.add_argument(
        "--field",
        "-f",
        required=True,
        help="Field path in dot notation (e.g., template.settings.index.routing.allocation.exclude._name)",
    )
    template_modify_parser.add_argument(
        "--operation",
        "-o",
        choices=["set", "append", "remove", "delete"],
        default="set",
        help="Operation: set (replace), append (add to list), remove (from list), delete (field)",
    )
    template_modify_parser.add_argument(
        "--value",
        "-v",
        default="",
        help="Value for operation (comma-separated for list operations)",
    )
    template_modify_parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup before modification (default: true)",
    )
    template_modify_parser.add_argument(
        "--no-backup", dest="backup", action="store_false", help="Skip backup creation"
    )
    template_modify_parser.add_argument("--backup-dir", help="Custom backup directory")
    template_modify_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making modifications",
    )

    template_backup_parser = subparsers.add_parser(
        "template-backup", help="Create a backup of a template"
    )
    template_backup_parser.add_argument("name", help="Template name to backup")
    template_backup_parser.add_argument(
        "--type",
        "-t",
        choices=["auto", "legacy", "composable", "component"],
        default="auto",
        help="Template type (default: auto-detect)",
    )
    template_backup_parser.add_argument("--backup-dir", help="Custom backup directory")
    template_backup_parser.add_argument(
        "--cluster", help="Cluster name for backup metadata"
    )

    template_restore_parser = subparsers.add_parser(
        "template-restore", help="Restore a template from backup"
    )
    template_restore_parser.add_argument(
        "--backup-file", required=True, help="Path to the backup file to restore from"
    )

    list_backups_parser = subparsers.add_parser(
        "list-backups", help="List available template backups"
    )
    list_backups_parser.add_argument("--name", help="Filter by template name")
    list_backups_parser.add_argument(
        "--type",
        choices=["legacy", "composable", "component"],
        help="Filter by template type",
    )
    list_backups_parser.add_argument("--backup-dir", help="Custom backup directory")
    list_backups_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    template_create_parser = subparsers.add_parser(
        "template-create", help="Create templates from JSON file or inline definition"
    )
    template_create_parser.add_argument(
        "--file", "-f", help="JSON file containing template definitions"
    )
    template_create_parser.add_argument(
        "--name", "-n", help="Template name (for inline creation)"
    )
    template_create_parser.add_argument(
        "--type",
        "-t",
        choices=["component", "composable", "legacy"],
        default="component",
        help="Template type (default: component)",
    )
    template_create_parser.add_argument(
        "--definition", "-d", help="Inline JSON template definition"
    )
    template_create_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating templates",
    )
    template_create_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )


def _add_allocation_commands(subparsers):
    """Add allocation management commands."""
    allocation_parser = subparsers.add_parser(
        "allocation", help="Manage cluster allocation settings"
    )
    allocation_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    # Allocation subcommands
    allocation_subparsers = allocation_parser.add_subparsers(
        dest="allocation_action", help="Allocation actions"
    )

    # Enable, disable
    for action, help_text in [
        ("enable", "Enable shard allocation"),
        ("disable", "Disable shard allocation"),
    ]:
        action_parser = allocation_subparsers.add_parser(action, help=help_text)
        action_parser.add_argument(
            "--format",
            choices=["json", "table"],
            default="table",
            help="Output format (json or table)",
        )

    # Exclude management
    exclude_parser = allocation_subparsers.add_parser(
        "exclude", help="Manage node exclusions"
    )
    exclude_subparsers = exclude_parser.add_subparsers(
        dest="exclude_action", help="Exclude actions"
    )

    add_parser = exclude_subparsers.add_parser("add", help="Add node to exclusion list")
    add_parser.add_argument("hostname", help="Hostname to exclude")
    add_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    remove_parser = exclude_subparsers.add_parser(
        "remove", help="Remove node from exclusion list"
    )
    remove_parser.add_argument("hostname", help="Hostname to remove from exclusion")
    remove_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    reset_parser = exclude_subparsers.add_parser(
        "reset", help="Reset all node exclusions"
    )
    reset_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    reset_parser.add_argument(
        "--yes-i-really-mean-it",
        action="store_true",
        help="Skip confirmation prompt (use with extreme caution)",
    )

    # Explain allocation
    explain_parser = allocation_subparsers.add_parser(
        "explain", help="Explain allocation decisions for specific index/shard"
    )
    explain_parser.add_argument("index", help="Index name to explain allocation for")
    explain_parser.add_argument(
        "--shard", "-s", type=int, default=0, help="Shard number (default: 0)"
    )
    explain_parser.add_argument(
        "--primary",
        action="store_true",
        help="Explain primary shard (default: auto-detect)",
    )
    explain_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )


def _add_snapshot_commands(subparsers):
    """Add snapshot management commands."""

    # Standalone repositories command with subcommands
    repositories_parser = subparsers.add_parser(
        "repositories", help="Manage snapshot repositories"
    )
    repositories_subparsers = repositories_parser.add_subparsers(
        dest="repositories_action", help="Repository actions"
    )

    # List repositories (default action when no subcommand)
    list_repos_parser = repositories_subparsers.add_parser(
        "list", help="List all configured snapshot repositories"
    )
    list_repos_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    # Create repository
    create_repo_parser = repositories_subparsers.add_parser(
        "create", help="Create a new snapshot repository"
    )
    create_repo_parser.add_argument("name", help="Repository name")
    create_repo_parser.add_argument(
        "--type",
        choices=["s3", "gcs", "azure", "fs", "hdfs"],
        required=True,
        help="Repository type",
    )
    create_repo_parser.add_argument(
        "--location", help="Repository location (required for fs type)"
    )
    create_repo_parser.add_argument(
        "--bucket", help="Bucket name (required for s3, gcs, azure types)"
    )

    # Verify repository
    verify_repo_parser = repositories_subparsers.add_parser(
        "verify", help="Verify a snapshot repository works from all nodes"
    )
    verify_repo_parser.add_argument(
        "repository_name", help="Name of the repository to verify"
    )
    verify_repo_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    create_repo_parser.add_argument(
        "--base-path", help="Base path within the repository"
    )
    create_repo_parser.add_argument("--region", help="AWS region (for s3 type)")
    create_repo_parser.add_argument(
        "--storage-class", help="Storage class (for s3 type)"
    )
    create_repo_parser.add_argument(
        "--server-side-encryption",
        action="store_true",
        help="Enable server-side encryption (for s3 type)",
    )
    create_repo_parser.add_argument(
        "--compress",
        action="store_true",
        default=True,
        help="Enable compression (default: true)",
    )
    create_repo_parser.add_argument(
        "--readonly", action="store_true", help="Create as read-only repository"
    )
    create_repo_parser.add_argument("--chunk-size", help="Chunk size for large files")
    create_repo_parser.add_argument(
        "--max-restore-bytes-per-sec", help="Max restore speed in bytes/sec"
    )
    create_repo_parser.add_argument(
        "--max-snapshot-bytes-per-sec", help="Max snapshot speed in bytes/sec"
    )
    create_repo_parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify repository after creation (default: true)",
    )
    create_repo_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show configuration without creating repository",
    )
    create_repo_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompts"
    )

    # Backward compatibility: if no subcommand, default to list
    repositories_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table) - for backward compatibility",
    )
    snapshots_parser = subparsers.add_parser(
        "snapshots", help="Manage Elasticsearch snapshots"
    )
    snapshots_subparsers = snapshots_parser.add_subparsers(
        dest="snapshots_action", help="Snapshot actions"
    )

    # List snapshots
    list_parser = snapshots_subparsers.add_parser(
        "list", help="List all snapshots from configured repository"
    )
    list_parser.add_argument(
        "pattern",
        nargs="?",
        default=None,
        help="Optional regex pattern to filter snapshots",
    )
    list_parser.add_argument(
        "--format",
        choices=["json", "table"],
        nargs="?",
        default="table",
        help="Output format (json or table)",
    )
    list_parser.add_argument(
        "--pager",
        action="store_true",
        default=False,
        help="Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)",
    )
    list_parser.add_argument(
        "--mode",
        choices=["fast", "slow"],
        default="fast",
        help="Listing mode: 'fast' for minimal metadata (default), 'slow' for full metadata",
    )
    # Keep --fast and --slow for backward compatibility
    list_parser.add_argument(
        "--fast",
        action="store_const",
        dest="mode",
        const="fast",
        help="Use fast listing mode (minimal metadata) - same as --mode fast",
    )
    list_parser.add_argument(
        "--slow",
        action="store_const",
        dest="mode",
        const="slow",
        help="Use slow listing mode (full metadata) - same as --mode slow",
    )

    # Snapshot status
    status_parser = snapshots_subparsers.add_parser(
        "status", help="Show detailed status of a specific snapshot"
    )
    status_parser.add_argument(
        "snapshot_name", help="Name of the snapshot to check status for"
    )
    status_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    status_parser.add_argument(
        "--repository",
        help="Snapshot repository name (uses configured default if not specified)",
    )

    # Snapshot info
    info_parser = snapshots_subparsers.add_parser(
        "info", help="Show comprehensive information about a specific snapshot"
    )
    info_parser.add_argument(
        "snapshot_name", help="Name of the snapshot to get information for"
    )
    info_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    info_parser.add_argument(
        "--repository",
        help="Snapshot repository name (uses configured default if not specified)",
    )

    # Create snapshot
    create_parser = snapshots_subparsers.add_parser(
        "create", help="Create a snapshot of indices or datastreams"
    )
    create_parser.add_argument(
        "target", help="Index name, datastream name, or regex pattern to match"
    )
    create_parser.add_argument(
        "--type",
        choices=["index", "datastream", "auto"],
        default="auto",
        help="Type of target (auto-detects by default)",
    )
    create_parser.add_argument(
        "--repository",
        help="Snapshot repository name (uses configured default if not specified)",
    )
    create_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for snapshot completion before returning",
    )
    create_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be snapshotted without creating snapshots",
    )
    create_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompts"
    )

    # Delete snapshot
    delete_parser = snapshots_subparsers.add_parser(
        "delete", help="Delete a specific snapshot"
    )
    delete_parser.add_argument(
        "snapshot_name", help="Exact name of the snapshot to delete"
    )
    delete_parser.add_argument(
        "--repository",
        help="Snapshot repository name (uses configured default if not specified)",
    )
    delete_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt"
    )

    # List restored snapshots
    list_restored_parser = snapshots_subparsers.add_parser(
        "list-restored",
        help="List all restored snapshots/indices tracked in the system",
    )
    list_restored_parser.add_argument(
        "--index", help="Override the default restored snapshots tracking index name"
    )

    # Clear staged snapshots
    clear_staged_parser = snapshots_subparsers.add_parser(
        "clear-staged", help="Clear all pending restores (in INIT status)"
    )
    clear_staged_parser.add_argument(
        "--index", help="Override the default restored snapshots tracking index name"
    )
    clear_staged_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt"
    )

    # List repositories
    repositories_parser = snapshots_subparsers.add_parser(
        "repositories", help="List all configured snapshot repositories"
    )
    repositories_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )


def _add_ilm_commands(subparsers):
    """Add ILM (Index Lifecycle Management) commands."""
    ilm_parser = subparsers.add_parser(
        "ilm", help="Manage Index Lifecycle Management (ILM)"
    )
    ilm_subparsers = ilm_parser.add_subparsers(dest="ilm_action", help="ILM actions")

    # Basic ILM commands
    basic_ilm_commands = [
        ("status", "Show comprehensive ILM status and statistics"),
        ("policies", "List all ILM policies"),
        ("errors", "Show indices with ILM errors"),
    ]

    for action, help_text in basic_ilm_commands:
        parser = ilm_subparsers.add_parser(action, help=help_text)
        parser.add_argument(
            "--format",
            choices=["json", "table"],
            default="table",
            help="Output format (json or table)",
        )

    # Policy details
    policy_parser = ilm_subparsers.add_parser(
        "policy", help="Show detailed configuration for specific ILM policy"
    )
    policy_parser.add_argument("policy_name", help="Policy name to show details for")
    policy_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    policy_parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all indices using this policy (default shows first 15)",
    )

    # Explain ILM
    explain_parser = ilm_subparsers.add_parser(
        "explain", help="Show ILM status for specific index (not policy)"
    )
    explain_parser.add_argument(
        "index", help="Index name to explain (use actual index name, not policy name)"
    )
    explain_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    # Policy management
    remove_policy_parser = ilm_subparsers.add_parser(
        "remove-policy",
        help="Remove ILM policy from indices via regex pattern or file list",
    )
    remove_policy_parser.add_argument(
        "pattern",
        nargs="?",
        help="Regex pattern to match index names (not used with --file)",
    )
    remove_policy_parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without executing"
    )
    remove_policy_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    remove_policy_parser.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompts"
    )
    remove_policy_parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent operations (default: 5)",
    )
    remove_policy_parser.add_argument(
        "--file", help="File containing list of indices (one per line or JSON format)"
    )

    # Set policy
    set_policy_parser = ilm_subparsers.add_parser(
        "set-policy",
        help="Set ILM policy via regex pattern, file list, or --from-policy",
    )
    set_policy_parser.add_argument("policy_name", help="ILM policy name to apply")
    set_policy_parser.add_argument(
        "pattern",
        nargs="?",
        help="Regex pattern to match index names (not used with --file or --from-policy)",
    )
    set_policy_parser.add_argument(
        "--from-policy",
        metavar="POLICY",
        dest="from_policy",
        help="Use all indices that currently have this ILM policy (not with pattern or --file)",
    )
    set_policy_parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without executing"
    )
    set_policy_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    set_policy_parser.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompts"
    )
    set_policy_parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent operations (default: 5)",
    )
    set_policy_parser.add_argument(
        "--file", help="File containing list of indices (one per line or JSON format)"
    )

    # Create policy
    create_policy_parser = ilm_subparsers.add_parser(
        "create-policy", help="Create a new ILM policy"
    )
    create_policy_parser.add_argument("policy_name", help="Name for the new ILM policy")
    create_policy_parser.add_argument(
        "policy_definition",
        nargs="?",
        help="JSON policy definition (inline) or path to JSON file",
    )
    create_policy_parser.add_argument(
        "--file", help="Path to JSON file containing policy definition"
    )
    create_policy_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    # Delete policy
    delete_policy_parser = ilm_subparsers.add_parser(
        "delete-policy", help="Delete an ILM policy"
    )
    delete_policy_parser.add_argument(
        "policy_name", help="Name of the ILM policy to delete"
    )
    delete_policy_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    delete_policy_parser.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompts"
    )

    # Index patterns report
    index_patterns_parser = ilm_subparsers.add_parser(
        "index-patterns",
        help="Show unique index base patterns (date/sequence stripped) for an ILM policy",
    )
    index_patterns_parser.add_argument(
        "policy_name", help="ILM policy name to report on"
    )
    index_patterns_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    index_patterns_parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all patterns (default shows first 50)",
    )

    # Backup policies
    backup_policies_parser = ilm_subparsers.add_parser(
        "backup-policies",
        help="Backup ILM policies for indices listed in a file to JSON",
    )
    backup_policies_parser.add_argument(
        "--input-file",
        required=True,
        help="File containing list of indices (one per line or JSON format)",
    )
    backup_policies_parser.add_argument(
        "--output-file",
        required=True,
        help="Output JSON file to save the backup",
    )
    backup_policies_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )

    # Restore policies
    restore_policies_parser = ilm_subparsers.add_parser(
        "restore-policies",
        help="Restore ILM policies from a backup JSON file",
    )
    restore_policies_parser.add_argument(
        "--input-file",
        required=True,
        help="Backup JSON file containing indices and their policies",
    )
    restore_policies_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing",
    )
    restore_policies_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )


def _add_utility_commands(subparsers):
    """Add utility and configuration commands."""

    # Simple utility commands (without additional arguments)
    simple_commands = [
        ("locations", "Display All Configured Locations"),
        ("get-default", "Show Default Cluster configured"),
        ("version", "Show version information"),
        ("themes", "Display available themes with previews"),
        ("cluster-groups", "Display configured cluster groups"),
    ]

    for cmd_name, cmd_help in simple_commands:
        if cmd_name == "cluster-groups":
            # Add cluster-groups command with format option
            cluster_groups_parser = subparsers.add_parser(cmd_name, help=cmd_help)
            cluster_groups_parser.add_argument(
                "--format",
                choices=["table", "json"],
                default="table",
                help="Output format (table or json)",
            )
        else:
            subparsers.add_parser(cmd_name, help=cmd_help)

    # Set theme command
    set_theme_parser = subparsers.add_parser(
        "set-theme", help="Change the active theme"
    )
    set_theme_parser.add_argument("theme_name", help="Name of the theme to switch to")
    set_theme_parser.add_argument(
        "--preview", action="store_true", help="Show theme preview before switching"
    )
    set_theme_parser.add_argument(
        "--no-confirm", action="store_true", help="Skip confirmation prompt"
    )

    # Show-settings command with format option
    show_settings_parser = subparsers.add_parser(
        "show-settings", help="Show current configuration settings"
    )
    show_settings_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (table or json)",
    )

    # Set default cluster
    setdefault_parser = subparsers.add_parser(
        "set-default", help="Set Default Cluster to use for commands"
    )
    setdefault_parser.add_argument(
        "defaultcluster_cmd",
        nargs="?",
        default="default",
        help="Cluster name to set as default",
    )

    # Set elastic username
    set_username_parser = subparsers.add_parser(
        "set-username", help="Set default Elasticsearch username in JSON config"
    )
    set_username_parser.add_argument(
        "username", help='Username to set as default (use "clear" to remove)'
    )
    set_username_parser.add_argument(
        "--show-current", action="store_true", help="Show current username setting"
    )

    # Datastreams
    datastreams_parser = subparsers.add_parser(
        "datastreams", help="List datastreams or show datastream details"
    )
    datastreams_parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Datastream name to show details for (optional)",
    )
    datastreams_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    datastreams_parser.add_argument(
        "--delete", action="store_true", help="Delete the specified datastream"
    )

    # Cluster health check
    cluster_check_parser = subparsers.add_parser(
        "cluster-check", help="Perform comprehensive cluster health checks"
    )
    cluster_check_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )
    cluster_check_parser.add_argument(
        "--max-shard-size",
        type=int,
        default=50,
        help="Maximum shard size in GB to report (default: 50)",
    )
    cluster_check_parser.add_argument(
        "--show-details",
        action="store_true",
        help="Show detailed information for each issue found",
    )
    cluster_check_parser.add_argument(
        "--skip-ilm",
        action="store_true",
        help="Skip ILM checks (useful for older ES versions or clusters without ILM)",
    )
    cluster_check_parser.add_argument(
        "--fix-replicas",
        type=int,
        metavar="COUNT",
        help="Fix indices with no replicas by setting replica count to COUNT",
    )
    cluster_check_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview replica fixes without applying them (use with --fix-replicas)",
    )
    cluster_check_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts when fixing replicas (use with --fix-replicas)",
    )
    cluster_check_parser.add_argument(
        "--ilm-limit",
        type=int,
        metavar="COUNT",
        help="Maximum number of ILM unmanaged indices to show before truncating (overrides config setting)",
    )

    # Set replicas command
    set_replicas_parser = subparsers.add_parser(
        "set-replicas", help="Manage replica count for indices"
    )
    set_replicas_parser.add_argument(
        "--count", type=int, default=1, help="Target replica count (default: 1)"
    )
    set_replicas_parser.add_argument(
        "--indices", help="Comma-separated list of specific indices to update"
    )
    set_replicas_parser.add_argument(
        "--pattern", help='Pattern to match indices (e.g., "logs-*")'
    )
    set_replicas_parser.add_argument(
        "--no-replicas-only",
        action="store_true",
        help="Only update indices with 0 replicas",
    )
    set_replicas_parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    set_replicas_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompts"
    )
    set_replicas_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )


def _add_format_argument(parser):
    """Helper function to add format argument to parsers."""
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (json or table)",
    )


def _add_password_commands(subparsers):
    """Add password management commands."""

    # Store password command
    store_password_parser = subparsers.add_parser(
        "store-password",
        help="Store encrypted password for an environment and optionally a specific username",
    )
    store_password_parser.add_argument(
        "environment",
        nargs="?",
        default="global",
        help='Environment name (default: "global" for single-user setups)',
    )
    store_password_parser.add_argument(
        "--username",
        "-u",
        help="Username to associate with this password (e.g., kibana_system, devin.acosta)",
    )

    # List stored passwords command
    list_passwords_parser = subparsers.add_parser(
        "list-stored-passwords", help="List all stored password environments"
    )
    list_passwords_parser.add_argument(
        "--decrypt",
        action="store_true",
        help="Show decrypted passwords in the table (use with caution)",
    )

    # Remove stored password command
    remove_password_parser = subparsers.add_parser(
        "remove-stored-password", help="Remove stored password for an environment"
    )
    remove_password_parser.add_argument(
        "environment", help="Environment name to remove"
    )

    # Clear session command
    clear_session_parser = subparsers.add_parser(
        "clear-session", help="Clear the current session cache"
    )

    # Session info command
    session_info_parser = subparsers.add_parser(
        "session-info", help="Show current session cache information"
    )

    # Set session timeout command
    set_timeout_parser = subparsers.add_parser(
        "set-session-timeout", help="Set session cache timeout in minutes"
    )
    set_timeout_parser.add_argument("timeout", type=int, help="Timeout in minutes")

    # Generate master key command for environment variable setup
    generate_key_parser = subparsers.add_parser(
        "generate-master-key",
        help="Generate a master key for ESCMD_MASTER_KEY environment variable",
    )
    generate_key_parser.add_argument(
        "--show-setup",
        action="store_true",
        help="Show setup instructions for different shells",
    )

    # Migrate to environment variable
    migrate_key_parser = subparsers.add_parser(
        "migrate-to-env-key",
        help="Migrate from file-based master key to environment variable",
    )
    migrate_key_parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if environment variable is already set",
    )

    rotate_key_parser = subparsers.add_parser(
        "rotate-master-key",
        help="Back up state file, generate a new master key, and re-encrypt stored passwords",
    )
    rotate_key_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (non-interactive)",
    )


def _add_action_commands(subparsers):
    """Add action sequence management commands."""

    # Action parent parser
    action_parser = subparsers.add_parser(
        "action", help="Manage and execute action sequences"
    )
    action_subparsers = action_parser.add_subparsers(
        dest="action_cmd", help="Action command help"
    )

    # List actions command
    list_parser = action_subparsers.add_parser(
        "list", help="List all available actions"
    )

    # Show action details command
    show_parser = action_subparsers.add_parser(
        "show", help="Show details for a specific action"
    )
    show_parser.add_argument(
        "action_name", help="Name of the action to show details for"
    )

    # Run action command
    run_parser = action_subparsers.add_parser("run", help="Execute an action sequence")
    run_parser.add_argument("action_name", help="Name of the action to execute")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without actually running commands",
    )
    run_parser.add_argument(
        "--no-json",
        action="store_true",
        help="Disable automatic JSON formatting for command output",
    )
    run_parser.add_argument(
        "--native-output",
        action="store_true",
        help="Show original escmd output format (automatically enabled in esterm)",
    )
    run_parser.add_argument(
        "--compact",
        action="store_true",
        help="Show compact output without detailed formatting panels",
    )
    run_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Show only essential output and final summary",
    )
    run_parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Show only the final execution summary",
    )
    run_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Automatically answer yes to all confirmation prompts",
    )
    run_parser.add_argument(
        "--max-lines",
        type=int,
        default=15,
        help="Maximum lines to show in output panels (default: 15)",
    )

    # Dynamic parameter support - these will be added dynamically based on action definitions
    # For now, we'll support common parameter patterns
    run_parser.add_argument(
        "--param-host",
        dest="param_host",
        help="Host parameter for actions that require it",
    )
    run_parser.add_argument(
        "--param-index-pattern",
        dest="param_index_pattern",
        help="Index pattern parameter for actions that require it",
    )
    run_parser.add_argument(
        "--param-snapshot-name",
        dest="param_snapshot_name",
        help="Snapshot name parameter for actions that require it",
    )
    run_parser.add_argument(
        "--param-action",
        dest="param_action",
        help="Action parameter for actions that require it",
    )
    run_parser.add_argument(
        "--param-pattern",
        dest="param_pattern",
        help="Pattern parameter for actions that require it",
    )
    run_parser.add_argument(
        "--param-days",
        dest="param_days",
        type=int,
        help="Days parameter for actions that require it",
    )


def _add_estop_command(subparsers):
    """Add es-top live dashboard command (and 'top' alias)."""
    for name in ("es-top", "top"):
        estop_parser = subparsers.add_parser(
            name,
            help="Live Elasticsearch cluster dashboard (like Unix top)"
            + (" [alias for es-top]" if name == "top" else ""),
        )
        estop_parser.add_argument(
            "--interval",
            type=int,
            default=None,
            metavar="SEC",
            help="Refresh interval in seconds (default: 30, minimum: 10)",
        )
        estop_parser.add_argument(
            "--top-nodes",
            type=int,
            default=None,
            dest="top_nodes",
            metavar="N",
            help="Number of top nodes to display by heap usage (default: 5)",
        )
        estop_parser.add_argument(
            "--top-indices",
            type=int,
            default=None,
            dest="top_indices",
            metavar="N",
            help="Number of top active indices to display (default: 10)",
        )
        estop_parser.add_argument(
            "--collect",
            action="store_true",
            default=False,
            dest="collect",
            help=(
                "Write index stats snapshots to disk each poll cycle (same format as "
                "indices-watch-collect). Use indices-watch-report to analyze afterward."
            ),
        )
        estop_parser.add_argument(
            "--collect-dir",
            default=None,
            dest="collect_dir",
            metavar="PATH",
            help=(
                "Directory to write snapshots when --collect is set "
                "(default: ~/.escmd/index-watch/<cluster>/<UTC-date>/)"
            ),
        )
        estop_parser.add_argument(
            "--new-session",
            action="store_true",
            default=False,
            dest="new_session",
            help="Skip session picker; always create a fresh session directory (no effect without --collect)",
        )
        estop_parser.add_argument(
            "--join-latest",
            action="store_true",
            default=False,
            dest="join_latest",
            help="Skip session picker; join the most recently started session (no effect without --collect)",
        )
        estop_parser.add_argument(
            "--label",
            default=None,
            dest="label",
            metavar="LABEL",
            help="Human-readable label for the session ID (no effect without --collect)",
        )
