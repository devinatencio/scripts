"""
Help content for indice-add-metadata commands.
"""

from .base_help_content import BaseHelpContent


class IndiceAddMetadataHelpContent(BaseHelpContent):
    """Help content for indice-add-metadata commands."""

    def get_topic_name(self) -> str:
        return "indice-add-metadata"

    def get_topic_description(self) -> str:
        return "Add custom metadata to indices"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row(
            "indice-add-metadata <index> '<json>'",
            "Add/merge metadata into the index _meta field",
            "./escmd.py indice-add-metadata myindex '{\"team\": \"ops\"}'",
        )
        commands_table.add_row(
            "Wrapped format",
            'Use {\"_meta\": {\"key\": \"value\"}} — same result',
            "",
        )
        commands_table.add_row(
            "Direct format",
            'Use {\"key\": \"value\"} directly — both accepted',
            "",
        )

        usage_table.add_row("🔄 Backup & Restore Tracking:", "Document backup sources and restoration details")
        usage_table.add_row("   Add Source:",  "./escmd.py indice-add-metadata restored-index '{\"backup_date\": \"2025-09-10\", \"source\": \"s3://bucket\"}'")
        usage_table.add_row("   View Result:", "./escmd.py indice restored-index")
        usage_table.add_row("   Benefits:",   "Track where data came from and when it was restored")
        usage_table.add_row("", "")
        usage_table.add_row("👥 Team & Project Management:", "Associate indices with teams and projects")
        usage_table.add_row("   Set Ownership:", "./escmd.py indice-add-metadata app-logs '{\"team\": \"backend\", \"contact\": \"admin@company.com\"}'")
        usage_table.add_row("   Add Project:",   "./escmd.py indice-add-metadata app-logs '{\"project\": \"user-analytics\", \"environment\": \"production\"}'")
        usage_table.add_row("   Benefits:",      "Clear ownership and responsibility for indices")
        usage_table.add_row("", "")
        usage_table.add_row("📈 Data Lifecycle Tracking:", "Document data processing and transformation history")
        usage_table.add_row("   Pipeline Info:", "./escmd.py indice-add-metadata etl-output '{\"pipeline\": \"daily-etl\", \"version\": \"v3.2\"}'")
        usage_table.add_row("   Quality Check:", "./escmd.py indice-add-metadata clean-data '{\"validation\": \"passed\", \"quality_score\": \"98.5\"}'")
        usage_table.add_row("   Benefits:",      "Complete audit trail for data transformations")
        usage_table.add_row("", "")
        usage_table.add_row("🔖 Operational Metadata:", "Add operational context and maintenance info")
        usage_table.add_row("   Maintenance:", "./escmd.py indice-add-metadata old-logs '{\"status\": \"archive\", \"cleanup_date\": \"2025-12-31\"}'")
        usage_table.add_row("   Performance:", "./escmd.py indice-add-metadata hot-index '{\"sla\": \"high\", \"monitoring\": \"enabled\"}'")
        usage_table.add_row("   Benefits:",    "Operational context for maintenance and monitoring")
        usage_table.add_row("", "")
        usage_table.add_row("✅ Metadata Merging:", "New metadata merges with existing metadata")
        usage_table.add_row("   Behavior:",       "Existing fields updated, new fields added")
        usage_table.add_row("   Nested Objects:", "Deep merge of nested JSON structures")
        usage_table.add_row("   Display:",        "Appears as formatted panel in ./escmd.py indice <name>")
        usage_table.add_row("", "")
        usage_table.add_row("🔒 Validation & Errors:", "Comprehensive error handling")
        usage_table.add_row("   JSON Validation:", "Invalid JSON returns clear error messages")
        usage_table.add_row("   Index Check:",     "Verifies index exists before attempting update")
        usage_table.add_row("   Permission Check:","Requires 'manage' privilege on target index")

        self._display_help_panels(
            commands_table, examples_table,
            "📝 indice-add-metadata Commands", "",
            usage_table, "🎯 Use Cases & Workflows"
        )
