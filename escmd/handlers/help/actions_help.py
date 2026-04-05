"""
Help content for Actions commands in escmd.

Provides detailed help and examples for action sequence management.
"""

from .base_help_content import BaseHelpContent
from rich.panel import Panel


class ActionsHelp(BaseHelpContent):
    """Help content for Actions commands."""

    def __init__(self, theme_manager=None):
        """Initialize actions help with theme manager."""
        super().__init__(theme_manager)
        self.command_name = "Actions"
        self.command_description = "Manage and execute action sequences"

    def get_topic_name(self) -> str:
        """Get the topic name for actions help."""
        return "actions"

    def get_topic_description(self) -> str:
        """Get the topic description for actions help."""
        return "Action sequence management and execution"

    def show_help(self) -> None:
        """Show actions help content."""
        sections = self._get_sections()

        for section in sections:
            title = section['title']
            content = section['content']

            # Create panel for each section
            panel_content = '\n'.join(content)
            panel = Panel(
                panel_content,
                title=title,
                border_style="blue",
                padding=(1, 1)
            )
            self.console.print(panel)
            self.console.print()

    def _get_sections(self):
        """Get help sections for actions."""
        return [
            self._create_overview_section(),
            self._create_commands_section(),
            self._create_examples_section(),
            self._create_advanced_section(),
            self._create_tips_section()
        ]

    def _create_overview_section(self):
        """Create overview section."""
        return {
            'title': '📋 Overview',
            'content': [
                'Actions allow you to define reusable sequences of escmd commands that can be',
                'executed together. This is useful for complex workflows, maintenance tasks,',
                'and repetitive operations that require multiple steps.',
                '',
                'Actions are defined in the actions.yml file and support:',
                '• Parameter substitution with validation',
                '• Conditional step execution',
                '• Dry-run mode for safe testing',
                '• JSON output formatting',
                '• User confirmation prompts'
            ]
        }

    def _create_commands_section(self):
        """Create commands section."""
        return {
            'title': '🔧 Commands',
            'content': [
                self._format_command('escmd action list', 'List all available actions'),
                self._format_command('escmd action show <name>', 'Show details for a specific action'),
                self._format_command('escmd action run <name> [options]', 'Execute an action'),
                '',
                'Run Options:',
                self._format_option('--param-<name> <value>', 'Pass parameter to action'),
                self._format_option('--dry-run', 'Preview commands without executing'),
                self._format_option('--compact', 'Show minimal output'),
                self._format_option('--no-json', 'Disable automatic JSON formatting'),
                self._format_option('--native-output', 'Show original escmd output format (auto-enabled in esterm)'),
                self._format_option('--max-lines N', 'Limit output to N lines')
            ]
        }

    def _create_examples_section(self):
        """Create examples section."""
        return {
            'title': '💡 Examples',
            'content': [
                self._format_example('List all actions:', 'escmd action list'),
                '',
                self._format_example('Show action details:', 'escmd action show add-host'),
                '',
                self._format_example('Run action with dry-run:',
                    'escmd action run add-host --param-host server01 --dry-run'),
                '',
                self._format_example('Execute action:',
                    'escmd action run add-host --param-host server01'),
                '',
                self._format_example('Run with compact output:',
                    'escmd action run health-check --compact'),
                '',
                self._format_example('Show original escmd output:',
                    'escmd action run health-check --native-output'),
                '',
                self._format_example('Multiple parameters:',
                    'escmd action run rollover-and-backup \\'),
                '  --param-index-pattern "logs-*" \\',
                '  --param-snapshot-name "backup-$(date +%Y%m%d)"'
            ]
        }

    def _create_advanced_section(self):
        """Create advanced features section."""
        return {
            'title': '🚀 Advanced Features',
            'content': [
                'Parameter Types:',
                '• string - Text values (default)',
                '• integer - Numeric values with validation',
                '• choice - Predefined options with validation',
                '',
                'Conditional Steps:',
                '• Steps can be executed based on parameter values',
                '• Use Jinja2 template syntax: {{ param == "value" }}',
                '',
                'Template Variables:',
                '• Actions support Jinja2 templating in commands',
                '• Variables: {{ parameter_name }}',
                '• Concatenation: "{{ host }}-*"',
                '',
                'Safety Features:',
                '• confirm: true - Prompts before destructive operations',
                '• --dry-run - Shows what would be executed',
                '• Parameter validation with helpful error messages'
            ]
        }

    def _create_tips_section(self):
        """Create tips and best practices section."""
        return {
            'title': '💡 Tips & Best Practices',
            'content': [
                '1. Always test with --dry-run first',
                '2. Use descriptive action and step names',
                '3. Add confirmation prompts for destructive operations',
                '4. Define parameter types and mark required ones',
                '5. Use meaningful descriptions for actions and steps',
                '6. Group related actions in your actions.yml file',
                '',
                'Action File Location:',
                '• Default: ./actions.yml in escmd directory',
                '• Actions are automatically discovered and loaded',
                '',
                'Output Formats:',
                '• Commands that support --format json get it automatically',
                '• JSON output is pretty-printed in panels',
                '• Large outputs are summarized intelligently',
                '',
                'For more details, see:',
                '• ACTIONS_USAGE_EXAMPLES.md - Comprehensive examples',
                '• ACTIONS_COMMAND_REFERENCE.md - Command syntax reference'
            ]
        }

    def _format_command(self, command, description):
        """Format a command with description."""
        styled_command = self._style_code(command)
        return f'{styled_command}\n    {description}'

    def _format_option(self, option, description):
        """Format an option with description."""
        styled_option = self._style_code(option)
        return f'  {styled_option}  {description}'

    def _format_example(self, title, command):
        """Format an example with title and command."""
        styled_command = self._style_code(command)
        return f'{title}\n  {styled_command}'

    def _style_code(self, text):
        """Apply code styling to text."""
        if self.theme_manager:
            try:
                return f"[{self.theme_manager.get_style('code')}]{text}[/]"
            except:
                pass
        return text
