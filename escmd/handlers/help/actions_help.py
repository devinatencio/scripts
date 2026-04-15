"""
Help content for Actions commands in escmd.

Provides detailed help and examples for action sequence management.
"""

from .base_help_content import BaseHelpContent


class ActionsHelp(BaseHelpContent):
    """Help content for Actions commands."""

    def __init__(self, theme_manager=None):
        super().__init__(theme_manager)

    def get_topic_name(self) -> str:
        return "actions"

    def get_topic_description(self) -> str:
        return "Action sequence management and execution"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("action list",                          "List all available actions",                                    "./escmd.py action list")
        commands_table.add_row("action show <name>",                   "Show details for a specific action",                           "./escmd.py action show add-host")
        commands_table.add_row("action run <name>",                    "Execute an action",                                            "./escmd.py action run health-check")
        commands_table.add_row("action run <name> --param-<n> <v>",   "Pass parameter to action",                                     "./escmd.py action run add-host --param-host server01")
        commands_table.add_row("action run <name> --dry-run",          "Preview commands without executing",                           "")
        commands_table.add_row("action run <name> --compact",          "Show minimal output",                                          "")
        commands_table.add_row("action run <name> --no-json",          "Disable automatic JSON formatting",                            "")
        commands_table.add_row("action run <name> --native-output",    "Show original escmd output format (auto-enabled in esterm)",   "")
        commands_table.add_row("action run <name> --max-lines N",      "Limit output to N lines",                                      "")

        usage_table.add_row("📋 Overview:", "Reusable sequences of escmd commands")
        usage_table.add_row("   Use cases:",    "Complex workflows, maintenance tasks, repetitive multi-step operations")
        usage_table.add_row("   Defined in:",   "actions.yml file in the escmd directory")
        usage_table.add_row("   Supports:",     "Parameter substitution, conditional steps, dry-run, JSON output, confirmations")
        usage_table.add_row("", "")
        usage_table.add_row("🚀 Parameter Types:", "")
        usage_table.add_row("   string:",  "Text values (default)")
        usage_table.add_row("   integer:", "Numeric values with validation")
        usage_table.add_row("   choice:",  "Predefined options with validation")
        usage_table.add_row("", "")
        usage_table.add_row("🔧 Conditional Steps & Templates:", "")
        usage_table.add_row("   Conditional execution:", "Steps run based on parameter values")
        usage_table.add_row("   Jinja2 syntax:",         "{{ param == \"value\" }}")
        usage_table.add_row("   Template variables:",    "{{ parameter_name }} in commands")
        usage_table.add_row("   Concatenation:",         "\"{{ host }}-*\"")
        usage_table.add_row("", "")
        usage_table.add_row("🔒 Safety Features:", "")
        usage_table.add_row("   confirm: true:", "Prompts before destructive operations")
        usage_table.add_row("   --dry-run:",     "Shows what would be executed without running")
        usage_table.add_row("   Validation:",    "Parameter validation with helpful error messages")
        usage_table.add_row("", "")
        usage_table.add_row("💡 Common Examples:", "")
        usage_table.add_row("   List all actions:",    "./escmd.py action list")
        usage_table.add_row("   Show action details:", "./escmd.py action show add-host")
        usage_table.add_row("   Dry run first:",       "./escmd.py action run add-host --param-host server01 --dry-run")
        usage_table.add_row("   Execute action:",      "./escmd.py action run add-host --param-host server01")
        usage_table.add_row("   Compact output:",      "./escmd.py action run health-check --compact")
        usage_table.add_row("", "")
        usage_table.add_row("💡 Best Practices:", "")
        usage_table.add_row("   1. Always test with --dry-run first",                "")
        usage_table.add_row("   2. Use descriptive action and step names",           "")
        usage_table.add_row("   3. Add confirmation prompts for destructive ops",    "")
        usage_table.add_row("   4. Define parameter types and mark required ones",   "")
        usage_table.add_row("   5. Group related actions in actions.yml",            "")

        self._display_help_panels(
            commands_table, examples_table,
            "🔧 Actions Commands", "",
            usage_table, "🎯 Workflows & Best Practices"
        )
