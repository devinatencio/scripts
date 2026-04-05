"""
Help content for indice-add-metadata commands.
"""

from .base_help_content import BaseHelpContent


class IndiceAddMetadataHelpContent(BaseHelpContent):
    """Help content for indice-add-metadata commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for indice-add-metadata help."""
        return "indice-add-metadata"

    def get_topic_description(self) -> str:
        """Get the topic description for indice-add-metadata help."""
        return "Add custom metadata to indices"

    def show_help(self) -> None:
        """Show detailed help for indice-add-metadata commands."""
        help_styles, border_style = self._get_theme_styles()

        from rich.panel import Panel
        from rich.table import Table

        # Command overview
        overview_table = Table.grid(padding=(0, 3))
        overview_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=20)
        overview_table.add_column(style=help_styles.get('description', 'white'))

        overview_table.add_row("Command:", "indice-add-metadata")
        overview_table.add_row("Purpose:", "Add custom metadata to existing Elasticsearch indices")
        overview_table.add_row("Storage:", "Metadata stored in index mapping _meta field")
        overview_table.add_row("Persistence:", "Metadata survives cluster restarts and index operations")
        overview_table.add_row("Display:", "Appears in 'indice' command output as dedicated panel")

        # Syntax table
        syntax_table = Table.grid(padding=(0, 3))
        syntax_table.add_column(style=help_styles.get('command', 'bold green'), min_width=20)
        syntax_table.add_column(style=help_styles.get('description', 'white'))

        syntax_table.add_row("Basic Syntax:", "./escmd.py indice-add-metadata <index_name> '<json_metadata>'")
        syntax_table.add_row("Wrapped Format:", '\'{"_meta": {"key": "value"}}\'')
        syntax_table.add_row("Direct Format:", '\'{"key": "value"}\'')
        syntax_table.add_row("Both Supported:", "Either format produces the same result")

        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style=help_styles.get('example', 'bold green'), min_width=35)
        examples_table.add_column(style=help_styles.get('description', 'dim white'))

        examples_table.add_row("Basic metadata:", "./escmd.py indice-add-metadata myindex-1 '{\"user\": \"admin\", \"timestamp\": \"2025-09-11T11:23:45\"}'")
        examples_table.add_row("Backup tracking:", "./escmd.py indice-add-metadata restored-logs '{\"_meta\": {\"backup_source\": \"s3://backups\", \"restored_by\": \"admin\"}}'")
        examples_table.add_row("Project info:", "./escmd.py indice-add-metadata app-logs '{\"project\": \"web-analytics\", \"team\": \"data-eng\", \"env\": \"prod\"}'")
        examples_table.add_row("Data lineage:", "./escmd.py indice-add-metadata processed-data '{\"source\": \"kafka\", \"pipeline\": \"v2.1\", \"processed\": \"2025-09-11\"}'")
        examples_table.add_row("Multiple fields:", "./escmd.py indice-add-metadata logs-2024 '{\"creator\": \"john\", \"purpose\": \"testing\", \"expires\": \"2025-12-31\"}'")

        # Use cases and workflows
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style=help_styles.get('section_header', 'bold magenta'), min_width=32)
        usage_table.add_column(style=help_styles.get('description', 'dim cyan'))

        usage_table.add_row("🔄 Backup & Restore Tracking:", "Document backup sources and restoration details")
        usage_table.add_row("   Add Source:", "./escmd.py indice-add-metadata restored-index '{\"backup_date\": \"2025-09-10\", \"source\": \"s3://bucket\"}'")
        usage_table.add_row("   View Result:", "./escmd.py indice restored-index")
        usage_table.add_row("   Benefits:", "Track where data came from and when it was restored")
        usage_table.add_row("", "")
        usage_table.add_row("👥 Team & Project Management:", "Associate indices with teams and projects")
        usage_table.add_row("   Set Ownership:", "./escmd.py indice-add-metadata app-logs '{\"team\": \"backend\", \"contact\": \"admin@company.com\"}'")
        usage_table.add_row("   Add Project:", "./escmd.py indice-add-metadata app-logs '{\"project\": \"user-analytics\", \"environment\": \"production\"}'")
        usage_table.add_row("   Benefits:", "Clear ownership and responsibility for indices")
        usage_table.add_row("", "")
        usage_table.add_row("📈 Data Lifecycle Tracking:", "Document data processing and transformation history")
        usage_table.add_row("   Pipeline Info:", "./escmd.py indice-add-metadata etl-output '{\"pipeline\": \"daily-etl\", \"version\": \"v3.2\", \"run_id\": \"abc123\"}'")
        usage_table.add_row("   Quality Check:", "./escmd.py indice-add-metadata clean-data '{\"validation\": \"passed\", \"quality_score\": \"98.5\", \"checker\": \"data-team\"}'")
        usage_table.add_row("   Benefits:", "Complete audit trail for data transformations")
        usage_table.add_row("", "")
        usage_table.add_row("🔖 Operational Metadata:", "Add operational context and maintenance info")
        usage_table.add_row("   Maintenance:", "./escmd.py indice-add-metadata old-logs '{\"status\": \"archive\", \"last_accessed\": \"2025-08-15\", \"cleanup_date\": \"2025-12-31\"}'")
        usage_table.add_row("   Performance:", "./escmd.py indice-add-metadata hot-index '{\"sla\": \"high\", \"monitoring\": \"enabled\", \"alerts\": \"critical\"}'")
        usage_table.add_row("   Benefits:", "Operational context for maintenance and monitoring")

        # Features and behavior
        features_table = Table.grid(padding=(0, 3))
        features_table.add_column(style=help_styles.get('section_header', 'bold yellow'), min_width=32)
        features_table.add_column(style=help_styles.get('description', 'dim white'))

        features_table.add_row("✅ Metadata Merging:", "New metadata merges with existing metadata")
        features_table.add_row("   Behavior:", "Existing fields are updated, new fields are added")
        features_table.add_row("   Nested Objects:", "Deep merge of nested JSON structures")
        features_table.add_row("   Example:", "Add to existing metadata without losing previous data")
        features_table.add_row("", "")
        features_table.add_row("🎨 Rich Display:", "Metadata appears as formatted panel in index details")
        features_table.add_row("   Location:", "Between Settings panel and Shard distribution")
        features_table.add_row("   Format:", "Syntax-highlighted JSON with proper indentation")
        features_table.add_row("   Conditional:", "Panel only shows when metadata exists")
        features_table.add_row("", "")
        features_table.add_row("🔒 Validation & Errors:", "Comprehensive error handling and validation")
        features_table.add_row("   JSON Validation:", "Invalid JSON returns clear error messages")
        features_table.add_row("   Index Check:", "Verifies index exists before attempting update")
        features_table.add_row("   Permission Check:", "Requires 'manage' privilege on target index")

        # Display all sections using theme system
        self.console.print()
        self.console.print(Panel(
            overview_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]📝 Metadata Command Overview[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            syntax_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🔧 Command Syntax & Formats[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            examples_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🚀 Practical Examples[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            usage_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🎯 Use Cases & Workflows[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            features_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]✨ Features & Behavior[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
