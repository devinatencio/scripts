"""
Help content for template-modify command.
"""

from .base_help_content import BaseHelpContent


class TemplateModifyHelpContent(BaseHelpContent):
    """Help content for template-modify command."""

    def get_topic_name(self) -> str:
        return "template-modify"

    def get_topic_description(self) -> str:
        return "Modify template fields with set/append/remove/delete operations"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("template-modify <name> -f <field> -v <value>",          "Set a field value (default operation)",                          "./escmd.py template-modify my-template -f template.settings.index.number_of_replicas -v 2")
        commands_table.add_row("template-modify <name> -f <field> -o set -v <value>",   "Explicitly replace field value",                                "")
        commands_table.add_row("template-modify <name> -f <field> -o append -v <value>","Append value(s) to a comma-separated list",                     "")
        commands_table.add_row("template-modify <name> -f <field> -o remove -v <value>","Remove value(s) from a comma-separated list",                   "")
        commands_table.add_row("template-modify <name> -f <field> -o delete",           "Delete the field entirely",                                     "")
        commands_table.add_row("template-modify <name> ... --dry-run",                  "Preview changes without applying them",                         "")
        commands_table.add_row("template-modify <name> ... --no-backup",                "Skip automatic backup before modifying",                        "")
        commands_table.add_row("template-modify <name> ... --backup-dir <path>",        "Save backup to a custom directory",                             "")
        commands_table.add_row("template-modify <name> ... --type <type>",              "Specify template type (auto/legacy/composable/component)",      "")

        usage_table.add_row("🔩 Available Operations:", "")
        usage_table.add_row("   set:",    "Replace the field value entirely (default). Works for strings, numbers, and lists.")
        usage_table.add_row("   append:", "Add one or more values to a comma-separated list field. Skips duplicates.")
        usage_table.add_row("   remove:", "Remove one or more values from a comma-separated list field.")
        usage_table.add_row("   delete:", "Remove the field key entirely from the template definition.")
        usage_table.add_row("", "")
        usage_table.add_row("📍 Field Path Notation:", "Use dot notation to navigate the template JSON")
        usage_table.add_row("   Composable replicas:", "template.settings.index.number_of_replicas")
        usage_table.add_row("   Composable shards:",   "template.settings.index.number_of_shards")
        usage_table.add_row("   Allocation exclude:",  "template.settings.index.routing.allocation.exclude._name")
        usage_table.add_row("   Refresh interval:",    "template.settings.index.refresh_interval")
        usage_table.add_row("   Legacy replicas:",     "settings.index.number_of_replicas")
        usage_table.add_row("   Priority:",            "priority")
        usage_table.add_row("   Index patterns:",      "index_patterns")
        usage_table.add_row("", "")
        usage_table.add_row("🔒 Safety Features:", "Built-in safeguards for safe modifications")
        usage_table.add_row("   Auto-backup:", "Backup created before every change (default)")
        usage_table.add_row("   Dry run:",     "Use --dry-run to preview without applying")
        usage_table.add_row("   Restore path:","./escmd.py template-restore --backup-file <path>")
        usage_table.add_row("", "")
        usage_table.add_row("💡 Append/Remove Tips:", "For comma-separated list fields")
        usage_table.add_row("   Multiple values:", "Separate with commas: -v 'host1-*,host2-*'")
        usage_table.add_row("   No duplicates:",   "append skips values already in the list")
        usage_table.add_row("   Partial remove:",  "remove only removes the specified values")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Common Examples:", "")
        usage_table.add_row("   Set replica count:",    "./escmd.py template-modify my-template -f template.settings.index.number_of_replicas -v 2")
        usage_table.add_row("   Dry run first:",        "./escmd.py template-modify my-template -f template.settings.index.number_of_replicas -v 2 --dry-run")
        usage_table.add_row("   Append host exclusion:","./escmd.py template-modify my-template -f template.settings.index.routing.allocation.exclude._name -o append -v 'ess01-*'")
        usage_table.add_row("   Remove host exclusion:","./escmd.py template-modify my-template -f template.settings.index.routing.allocation.exclude._name -o remove -v 'ess01-*'")
        usage_table.add_row("   Delete a field:",       "./escmd.py template-modify my-template -f template.settings.index.routing -o delete")
        usage_table.add_row("   No backup:",            "./escmd.py template-modify my-template -f settings.index.refresh_interval -v '30s' --no-backup")

        self._display_help_panels(
            commands_table, examples_table,
            "🔧 template-modify Commands & Flags", "",
            usage_table, "🎯 Operations, Field Paths & Safety"
        )
