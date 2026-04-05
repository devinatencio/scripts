"""
Help content for exclude commands.
"""

from .base_help_content import BaseHelpContent


class ExcludeHelpContent(BaseHelpContent):
    """Help content for exclude commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for exclude help."""
        return "exclude"

    def get_topic_description(self) -> str:
        """Get the topic description for exclude help."""
        return "Index exclusion from specific hosts"

    def show_help(self) -> None:
        """Show detailed help for exclude commands."""
        # Create tables
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table = self._create_usage_table()

        # Add commands (exact from original)
        commands_table.add_row("🚫 exclude <index> --server <host>", "Exclude specific index from specific host")
        commands_table.add_row("🔄 exclude-reset <index>", "Reset exclusion settings for specific index")
        commands_table.add_row("", "")
        commands_table.add_row("🔀 allocation exclude add <host>", "Exclude entire node from all allocations")
        commands_table.add_row("🔀 allocation exclude remove <host>", "Remove node from cluster exclusion list")
        commands_table.add_row("🔀 allocation exclude reset", "Reset all cluster-level exclusions")

        # Add examples (exact from original)
        examples_table.add_row("Index exclusion:", "./escmd.py exclude .ds-logs-2025.04.03-000732 -s node-1")
        examples_table.add_row("Reset index exclusion:", "./escmd.py exclude-reset .ds-logs-2025.04.03-000732")
        examples_table.add_row("", "")
        examples_table.add_row("Cluster node exclusion:", "./escmd.py allocation exclude add node-1")
        examples_table.add_row("Remove node exclusion:", "./escmd.py allocation exclude remove node-1")
        examples_table.add_row("Reset all exclusions:", "./escmd.py allocation exclude reset")

        # Add usage patterns (exact from original)
        usage_table.add_row("📍 INDEX-LEVEL EXCLUSION:", "Exclude specific index from specific host")
        usage_table.add_row("   Command:", "./escmd.py exclude <index-name> --server <hostname>")
        usage_table.add_row("   Purpose:", "Prevent ONE index from allocating on ONE host")
        usage_table.add_row("   Scope:", "Affects only the specified index")
        usage_table.add_row("   Use Case:", "Host has issues but only affecting specific index")
        usage_table.add_row("   Example:", "./escmd.py exclude .ds-aex10-logs-2025.04.03-000732 -s aex10-c01-ess01-1")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 INDEX EXCLUSION RESET:", "Remove exclusion for specific index")
        usage_table.add_row("   Command:", "./escmd.py exclude-reset <index-name>")
        usage_table.add_row("   Purpose:", "Allow index to allocate on previously excluded host")
        usage_table.add_row("   Example:", "./escmd.py exclude-reset .ds-aex10-logs-2025.04.03-000732")
        usage_table.add_row("", "")
        usage_table.add_row("🏢 CLUSTER-LEVEL EXCLUSION:", "Exclude entire node from all allocations")
        usage_table.add_row("   Command:", "./escmd.py allocation exclude add <hostname>")
        usage_table.add_row("   Purpose:", "Prevent ALL shards from allocating on node")
        usage_table.add_row("   Scope:", "Affects ALL indices in cluster")
        usage_table.add_row("   Use Case:", "Node maintenance, hardware issues, decommissioning")
        usage_table.add_row("   Example:", "./escmd.py allocation exclude add node-1")
        usage_table.add_row("", "")
        usage_table.add_row("🔓 CLUSTER EXCLUSION REMOVAL:", "Remove node from exclusion list")
        usage_table.add_row("   Command:", "./escmd.py allocation exclude remove <hostname>")
        usage_table.add_row("   Purpose:", "Allow node to receive shards again")
        usage_table.add_row("   Example:", "./escmd.py allocation exclude remove node-1")
        usage_table.add_row("", "")
        usage_table.add_row("🔶  DANGER: RESET ALL EXCLUSIONS:", "Reset all cluster-level exclusions")
        usage_table.add_row("   Command:", "./escmd.py allocation exclude reset")
        usage_table.add_row("   Safety:", "Requires typing 'RESET' to confirm")
        usage_table.add_row("   Bypass Safety:", "./escmd.py allocation exclude reset --yes-i-really-mean-it")
        usage_table.add_row("   Warning:", "Use bypass flag with EXTREME caution!")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 CHOOSING THE RIGHT COMMAND:", "Index-level vs Cluster-level")
        usage_table.add_row("   Index-level:", "Use when problem is specific to one index")
        usage_table.add_row("   Cluster-level:", "Use when entire node needs to be excluded")
        usage_table.add_row("   Recovery:", "Index-level: exclude-reset, Cluster-level: exclude remove")
        usage_table.add_row("", "")
        usage_table.add_row("🔧 TECHNICAL DETAILS:", "How exclusions work")
        usage_table.add_row("   Index Setting:", "index.routing.allocation.exclude._name")
        usage_table.add_row("   Cluster Setting:", "cluster.routing.allocation.exclude._name")
        usage_table.add_row("   Effect:", "Elasticsearch moves shards away from excluded hosts")
        usage_table.add_row("   Duration:", "Exclusions persist until manually removed")

        # Display help panels
        self._display_help_panels(
            commands_table, examples_table,
            "🚫 Exclude Commands (Index & Cluster Level)", "🚀 Exclude Examples",
            usage_table, "🎯 Exclude Workflows & Safety Guide"
        )
