"""
Help content for es-top — live Elasticsearch cluster dashboard.
"""

from .base_help_content import BaseHelpContent


class EsTopHelpContent(BaseHelpContent):
    """Help for the es-top live terminal dashboard."""

    def get_topic_name(self) -> str:
        return "es-top"

    def get_topic_description(self) -> str:
        return "Live auto-refreshing Elasticsearch cluster dashboard (like Unix top)  [alias: top]"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("es-top",                    "Launch live dashboard (default cluster, 30s refresh)",          "./escmd.py es-top")
        commands_table.add_row("top",                       "Same — short alias",                                            "./escmd.py top")
        commands_table.add_row("es-top --interval SEC",     "Refresh interval in seconds (default: 30, minimum: 10)",        "./escmd.py es-top --interval 15")
        commands_table.add_row("es-top --top-nodes N",      "Number of nodes ranked by heap % (default: 5)",                 "./escmd.py es-top --top-nodes 10")
        commands_table.add_row("es-top --top-indices N",    "Number of active indices ranked by docs/sec (default: 10)",     "./escmd.py es-top --top-indices 20")
        commands_table.add_row("es-top --collect",          "Write index stats snapshots to disk each poll cycle",           "./escmd.py -l prod top --collect")
        commands_table.add_row("es-top --collect-dir PATH", "Directory for --collect snapshots",                             "")

        usage_table.add_row("📋 Overview:", "Full-screen auto-refreshing terminal dashboard")
        usage_table.add_row("   Modelled after:", "Unix top command")
        usage_table.add_row("   Panels:",         "Cluster health header, top nodes by JVM heap, index hot list")
        usage_table.add_row("   Index hot list:", "docs/sec, searches/sec, cumulative session totals since start")
        usage_table.add_row("   Exit:",           "Ctrl+C")
        usage_table.add_row("   Alias:",          "Both es-top and top are identical")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Dashboard Panels:", "")
        usage_table.add_row("   Cluster Header:", "Status pill (● GREEN/YELLOW/RED), cluster name, node counts, shard breakdown")
        usage_table.add_row("   Top Nodes:",      "JVM heap, CPU, disk as progress bars. Heap ≥70% → yellow, ≥85% → red")
        usage_table.add_row("   Index Hot List:", "Docs/sec and searches/sec (delta between polls), session totals")
        usage_table.add_row("   Hot Indicator:",  "🔥 = #1 by docs/sec, 🌡 = #2. Controlled by hot_indicator in escmd.yml")
        usage_table.add_row("", "")
        usage_table.add_row("⚙️  escmd.yml Configuration:", "CLI flags override config; config overrides built-in defaults")
        usage_table.add_row("   es_top.interval:",      "Default refresh interval (seconds)")
        usage_table.add_row("   es_top.top_nodes:",     "Default node panel row count")
        usage_table.add_row("   es_top.top_indices:",   "Default index hot list row count")
        usage_table.add_row("   es_top.hot_indicator:", "emoji | color | both | none")
        usage_table.add_row("", "")
        usage_table.add_row("📡 Collect + Analyze Workflow:", "Capture snapshots for offline analysis")
        usage_table.add_row("   Step 1 — collect:", "./escmd.py -l prod top --collect")
        usage_table.add_row("   Step 2 — exit:",    "Press Ctrl+C when done")
        usage_table.add_row("   Step 3 — analyze:", "./escmd.py -l prod indices-watch-report")
        usage_table.add_row("   Custom dir:",       "./escmd.py -l prod top --collect --collect-dir /tmp/run")
        usage_table.add_row("   Default path:",     "~/.escmd/index-watch/<cluster>/<UTC-date>/")

        self._display_help_panels(
            commands_table, examples_table,
            "📺 es-top — Live Cluster Dashboard", "",
            usage_table, "🎯 Dashboard & Workflow Guide"
        )
