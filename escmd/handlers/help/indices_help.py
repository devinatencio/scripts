"""
Help content for indices commands.
"""

from .base_help_content import BaseHelpContent


class IndicesHelpContent(BaseHelpContent):
    """Help content for indices commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for indices help."""
        return "indices"

    def get_topic_description(self) -> str:
        """Get the topic description for indices help."""
        return "Index management operations and examples"

    def show_help(self) -> None:
        """Show detailed help for indices commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table = self._create_usage_table()

        # Add commands (from original)
        commands_table.add_row("indices", "List and filter indices with various options")
        commands_table.add_row(
            "indices-analyze",
            "Find backing indices with doc/size far above sibling medians (rollover series)",
        )
        commands_table.add_row(
            "indices-s3-estimate",
            "Estimate monthly S3 cost from primary sizes (rollover date window, optional buffer)",
        )
        commands_table.add_row(
            "indices-watch-collect",
            "Sample index stats on an interval to ~/.escmd/index-watch/<cluster>/<UTC-date>/",
        )
        commands_table.add_row(
            "indices-watch-report",
            "Summarize collected samples (docs/s, HOT); no ES connection required",
        )
        commands_table.add_row("indice <name>", "Show detailed information for single index")
        commands_table.add_row("indice-add-metadata <index> <json>", "Add custom metadata to an index")
        commands_table.add_row("shards", "View shard distribution across nodes")
        commands_table.add_row("shard-colocation", "Find primary/replica shards on same host")
        commands_table.add_row("freeze <index>", "Freeze an index to reduce memory usage")
        commands_table.add_row("unfreeze <pattern>", "Unfreeze indices (supports regex with -r)")
        commands_table.add_row("flush <index>", "Force flush index to disk")

        # Add examples (from original)
        examples_table.add_row("List all indices:", "./escmd.py indices")
        examples_table.add_row("Filter by pattern:", "./escmd.py indices 'logs-*'")
        examples_table.add_row(
            "Traffic outliers (default ≥5x):", "./escmd.py indices-analyze k_fluent_bit"
        )
        examples_table.add_row(
            "Lower threshold:", "./escmd.py indices-analyze k_fluent_bit --min-ratio 2"
        )
        examples_table.add_row(
            "Include small indices:",
            "./escmd.py indices-analyze k_fluent_bit --min-docs 0",
        )
        examples_table.add_row(
            "Recent outliers only:",
            "./escmd.py indices-analyze k_fluent_bit --within-days 7",
        )
        examples_table.add_row(
            "Full help for analyze:",
            "./escmd.py help indices-analyze",
        )
        examples_table.add_row(
            "S3 cost estimate (30d, example price):",
            "./escmd.py indices-s3-estimate --price-per-gib-month 0.023",
        )
        examples_table.add_row(
            "S3 estimate help:",
            "./escmd.py help indices-s3-estimate",
        )
        examples_table.add_row(
            "Watch ingest 5m / 30s:",
            "./escmd.py -l mycluster indices-watch-collect --interval 30 --duration 300",
        )
        examples_table.add_row(
            "Report today (UTC) for -l cluster:",
            "./escmd.py -l mycluster indices-watch-report",
        )
        examples_table.add_row(
            "Report offline / prior day:",
            "./escmd.py indices-watch-report --cluster mycluster --date 2026-03-29",
        )
        examples_table.add_row(
            "Full help for watch collect:",
            "./escmd.py help indices-watch-collect",
        )
        examples_table.add_row(
            "Full help for watch report:",
            "./escmd.py help indices-watch-report",
        )
        examples_table.add_row("Delete indices:", "./escmd.py indices 'logs-*' --delete")
        examples_table.add_row("Show red indices:", "./escmd.py indices --status red")
        examples_table.add_row("Index details:", "./escmd.py indice myindex-001")
        examples_table.add_row("Add metadata:", "./escmd.py indice-add-metadata myindex '{\"team\": \"backend\"}'")
        examples_table.add_row("Create empty index:", "./escmd.py create-index my-new-index")
        examples_table.add_row("Create with settings:", "./escmd.py create-index logs-2024 -s 3 -r 1")
        examples_table.add_row("Shard distribution:", "./escmd.py shards")
        examples_table.add_row("Check colocation:", "./escmd.py shard-colocation")
        examples_table.add_row("Freeze index:", "./escmd.py freeze myindex-001")
        examples_table.add_row("Unfreeze single:", "./escmd.py unfreeze myindex-001")
        examples_table.add_row("Unfreeze pattern:", "./escmd.py unfreeze 'logs-*' -r")
        examples_table.add_row("JSON output:", "./escmd.py indices --format json")

        # Add usage patterns (from original)
        usage_table.add_row("🔍 Daily Health Check:", "Monitor index health by checking for red/yellow status indices")
        usage_table.add_row("   Command:", "./escmd.py indices --status red")
        usage_table.add_row("🆕 Create New Index:", "Create empty indices for applications or testing")
        usage_table.add_row("   Command:", "./escmd.py create-index my-app-logs -s 2 -r 1")
        usage_table.add_row("   Follow-up:", "./escmd.py indice <problematic-index>")
        usage_table.add_row("   Purpose:", "Detailed analysis of problematic indices")
        usage_table.add_row("", "")
        usage_table.add_row("📂 Space Management:", "Identify large indices consuming disk space")
        usage_table.add_row("   Command:", "./escmd.py indices")
        usage_table.add_row("   Action:", "Sort by size column to find largest indices")
        usage_table.add_row("   Next Steps:", "Consider ILM policies or manual cleanup for large indices")
        usage_table.add_row("", "")
        usage_table.add_row("⚡ Performance Issues:", "Check shard distribution and colocation problems")
        usage_table.add_row("   Step 1:", "./escmd.py shards (--size or -z)")
        usage_table.add_row("   Purpose:", "See largest shards affecting performance")
        usage_table.add_row("   Step 2:", "./escmd.py shard-colocation")
        usage_table.add_row("   Purpose:", "Find problematic shard distribution")
        usage_table.add_row("", "")
        usage_table.add_row("🧹 Maintenance Tasks:", "Freeze/unfreeze indices to manage memory usage")
        usage_table.add_row("   Find Old:", "./escmd.py indices 'logs-2024-*'")
        usage_table.add_row("   Freeze:", "./escmd.py freeze <old-index-name>")
        usage_table.add_row("   Unfreeze Single:", "./escmd.py unfreeze <index-name>")
        usage_table.add_row("   Unfreeze Multiple:", "./escmd.py unfreeze 'temp-*' -r")
        usage_table.add_row("   Benefit:", "Manage memory usage for data lifecycle")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Automation Scripts:", "JSON output for scripting and monitoring")
        usage_table.add_row("   Command:", "./escmd.py indices --format json")
        usage_table.add_row("   Filter:", "| jq '.[] | select(.status == \"red\")'")
        usage_table.add_row("   Use Case:", "Parse output for alerting systems and dashboards")
        usage_table.add_row("", "")
        usage_table.add_row("📝 Index Documentation:", "Add metadata for tracking and documentation")
        usage_table.add_row("   Add Tags:", "./escmd.py indice-add-metadata myindex '{\"team\": \"backend\", \"project\": \"api\"}'")
        usage_table.add_row("   View Metadata:", "./escmd.py indice myindex")
        usage_table.add_row("   Get Help:", "./escmd.py help indice-add-metadata")
        usage_table.add_row("   Benefit:", "Document ownership, purpose, and operational context")

        # Display help panels
        self._display_help_panels(
            commands_table, examples_table,
            "📊 Index Management Commands", "🚀 Index Examples",
            usage_table, "🎯 Typical Use Cases & Workflows"
        )
