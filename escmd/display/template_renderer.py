"""
Template rendering utilities for Elasticsearch command-line tool.

This module provides template-related display capabilities including:
- Template listing tables with proper theming and styled headers
- Detailed template information panels
- Template usage analysis displays
- Support for legacy, composable, and component templates
- Full theme integration for consistent styling
"""

import json
from typing import Any, Dict, List, Optional, Set, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich import box


class TemplateRenderer:
    """
    Handles template-related display rendering with Rich formatting and theme integration.

    This renderer follows the established ESCMD architecture for display components,
    providing consistent theming and formatting for template operations.
    """

    def __init__(self, theme_manager=None, table_renderer=None, panel_renderer=None, console=None):
        """
        Initialize the template renderer.

        Args:
            theme_manager: Theme manager for styling
            table_renderer: Table renderer instance for themed tables
            panel_renderer: Panel renderer instance for themed panels
            console: Rich console instance
        """
        self.theme_manager = theme_manager
        self.table_renderer = table_renderer
        self.panel_renderer = panel_renderer
        self.console = console or Console()

        # Initialize style system if theme manager is available
        self.style_system = None
        if theme_manager:
            try:
                from .style_system import StyleSystem
                self.style_system = StyleSystem(theme_manager)
            except ImportError:
                pass

    def get_themed_style(self, category: str, key: str, default: str) -> str:
        """Get themed style or return default."""
        if self.theme_manager:
            return self.theme_manager.get_themed_style(category, key, default)
        return default

    def print_templates_table(self, templates_data: Dict[str, Any], template_type: str = 'all') -> None:
        """
        Print formatted table of templates with theme support.

        Args:
            templates_data: Template data from template commands
            template_type: Type of templates being displayed
        """
        try:
            if 'error' in templates_data:
                error_text = Text(f"Error: {templates_data['error']}", style="bold red")
                error_panel = self._create_themed_panel(error_text, "🔶 Template Error", "error")
                self.console.print(error_panel)
                return

            # Create and display summary panel
            self._print_template_summary(templates_data.get('summary', {}), template_type)

            # Create tables for each template type
            if template_type in ['all', 'legacy'] and templates_data.get('legacy_templates'):
                legacy_table = self._create_legacy_templates_table(templates_data['legacy_templates'])
                if legacy_table:
                    self.console.print(legacy_table)
                    self.console.print()

            if template_type in ['all', 'composable'] and templates_data.get('composable_templates'):
                composable_table = self._create_composable_templates_table(templates_data['composable_templates'])
                if composable_table:
                    self.console.print(composable_table)
                    self.console.print()

            if template_type in ['all', 'component'] and templates_data.get('component_templates'):
                component_table = self._create_component_templates_table(templates_data['component_templates'])
                if component_table:
                    self.console.print(component_table)
                    self.console.print()

            # Show message if no templates found
            if not self._has_templates(templates_data, template_type):
                self._show_no_templates_message(template_type)

        except Exception as e:
            error_text = Text(f"Error displaying templates: {str(e)}", style="bold red")
            error_panel = self._create_themed_panel(error_text, "🔶 Display Error", "error")
            self.console.print(error_panel)

    def print_template_detail(self, template_data: Dict[str, Any]) -> None:
        """
        Print detailed information about a specific template with theme support.

        Args:
            template_data: Detailed template information
        """
        try:
            if 'error' in template_data:
                error_text = Text(f"Error: {template_data['error']}", style="bold red")
                error_panel = self._create_themed_panel(error_text, "🔶 Template Error", "error")
                self.console.print(error_panel)
                return

            if not template_data.get('found'):
                self._show_template_not_found(template_data.get('name', 'unknown'))
                return

            # Create header panel
            self._print_template_header(template_data)

            # Create detail panels
            metadata = template_data.get('metadata', {})
            panels = []

            # Basic info panel
            basic_info_panel = self._create_basic_info_panel(template_data, metadata)
            if basic_info_panel:
                panels.append(basic_info_panel)

            # Configuration panel
            config_panel = self._create_template_config_panel(metadata)
            if config_panel:
                panels.append(config_panel)

            # Settings panel
            if metadata.get('settings'):
                settings_panel = self._create_json_panel(
                    metadata['settings'],
                    "🔩 Settings"
                )
                panels.append(settings_panel)

            # Mappings panel
            if metadata.get('mappings'):
                mappings_panel = self._create_json_panel(
                    metadata['mappings'],
                    "📋 Mappings"
                )
                panels.append(mappings_panel)

            # Aliases panel
            if metadata.get('aliases'):
                aliases_panel = self._create_json_panel(
                    metadata['aliases'],
                    "🔗 Aliases"
                )
                panels.append(aliases_panel)

            # Display panels
            self._display_panels(panels)

        except Exception as e:
            error_text = Text(f"Error displaying template details: {str(e)}", style="bold red")
            error_panel = self._create_themed_panel(error_text, "🔶 Display Error", "error")
            self.console.print(error_panel)

    def print_template_usage(self, usage_data: Dict[str, Any]) -> None:
        """
        Print template usage analysis with theme support.

        Args:
            usage_data: Template usage analysis data
        """
        try:
            if 'error' in usage_data:
                error_text = Text(f"Error: {usage_data['error']}", style="bold red")
                error_panel = self._create_themed_panel(error_text, "🔶 Usage Analysis Error", "error")
                self.console.print(error_panel)
                return

            # Templates in use table
            templates_in_use = usage_data.get('templates_in_use', {})
            if templates_in_use:
                usage_table = self._create_usage_table(templates_in_use)
                self.console.print(usage_table)
                self.console.print()

            # Unused templates table
            unused_templates = usage_data.get('unused_templates', [])
            if unused_templates:
                unused_table = self._create_unused_templates_table(unused_templates)
                self.console.print(unused_table)
                self.console.print()

            # Usage summary
            self._print_usage_summary(templates_in_use, unused_templates)

        except Exception as e:
            error_text = Text(f"Error displaying template usage: {str(e)}", style="bold red")
            error_panel = self._create_themed_panel(error_text, "🔶 Display Error", "error")
            self.console.print(error_panel)

    def _print_template_summary(self, summary: Dict[str, Any], template_type: str) -> None:
        """Create and display template summary panel."""
        summary_text = Text()

        if template_type == 'all':
            # Use semantic styling for consistent theming
            total_style = self.get_themed_style('semantic_styles', 'primary', 'bold cyan')
            legacy_style = self.get_themed_style('semantic_styles', 'warning', 'yellow')
            composable_style = self.get_themed_style('semantic_styles', 'success', 'green')
            component_style = self.get_themed_style('semantic_styles', 'info', 'blue')

            summary_text.append(f"📋 Total Templates: {summary.get('total_count', 0)}\n", style=total_style)
            summary_text.append(f"  • Legacy: {summary.get('legacy_count', 0)}\n", style=legacy_style)
            summary_text.append(f"  • Composable: {summary.get('composable_count', 0)}\n", style=composable_style)
            summary_text.append(f"  • Component: {summary.get('component_count', 0)}", style=component_style)
        else:
            type_name = template_type.replace('_', ' ').title()
            count_key = f"{template_type}_count"
            header_style = self.get_themed_style('semantic_styles', 'primary', 'bold cyan')
            summary_text.append(f"📋 {type_name} Templates: {summary.get(count_key, 0)}", style=header_style)

        # Use StyleSystem panel creation if available
        if self.style_system:
            summary_panel = self.style_system.create_info_panel(
                summary_text,
                "📊 Template Summary"
            )
        else:
            summary_panel = self._create_themed_panel(
                summary_text,
                "📊 Template Summary",
                "info"
            )
        self.console.print(summary_panel)

    def _create_legacy_templates_table(self, legacy_templates: Dict[str, Any]) -> Optional[Table]:
        """Create themed table for legacy templates."""
        if 'error' in legacy_templates or not legacy_templates:
            return None

        # Use StyleSystem for consistent theming if available
        if self.style_system:
            table = self.style_system.create_standard_table(
                title="🏛️  Legacy Index Templates"
            )
        elif self.table_renderer:
            table = self.table_renderer.create_basic_table(
                title="🏛️  Legacy Index Templates",
                show_header=True
            )
        else:
            # Fallback with proper themed styles
            header_style = self.get_themed_style('table_styles', 'header_style', 'bold white')
            border_style = self.get_themed_style('table_styles', 'border_style', 'white')
            table = Table(
                title=f"[{self.get_themed_style('panel_styles', 'info', 'bright_cyan')}]🏛️  Legacy Index Templates[/{self.get_themed_style('panel_styles', 'info', 'bright_cyan')}]",
                box=box.HEAVY if border_style != 'black' else box.SIMPLE,
                show_header=True,
                header_style=header_style,
                border_style=border_style,
                expand=True
            )

        # Use semantic styling for columns
        if self.style_system:
            self.style_system.add_themed_column(table, "Name", "name", no_wrap=True)
            self.style_system.add_themed_column(table, "Index Patterns", "default")
            self.style_system.add_themed_column(table, "Order", "count", justify="right")
            self.style_system.add_themed_column(table, "Settings", "status", justify="center")
            self.style_system.add_themed_column(table, "Mappings", "status", justify="center")
            self.style_system.add_themed_column(table, "Aliases", "status", justify="center")
        else:
            # Fallback with semantic theme colors
            table.add_column("Name", style=self.get_themed_style('semantic_styles', 'primary', 'cyan'), no_wrap=True)
            table.add_column("Index Patterns", style=self.get_themed_style('semantic_styles', 'success', 'green'))
            table.add_column("Order", justify="right", style=self.get_themed_style('semantic_styles', 'secondary', 'magenta'))
            table.add_column("Settings", justify="center", style=self.get_themed_style('semantic_styles', 'info', 'blue'))
            table.add_column("Mappings", justify="center", style=self.get_themed_style('semantic_styles', 'info', 'blue'))
            table.add_column("Aliases", justify="center", style=self.get_themed_style('semantic_styles', 'info', 'blue'))

        # Sort templates alphabetically by name for consistent display
        sorted_templates = sorted(legacy_templates.items()) if legacy_templates else []

        for name, template in sorted_templates:
            if name == 'error':
                continue

            patterns = ', '.join(template.get('index_patterns', []))
            order = str(template.get('order', 0))

            settings_count = len(template.get('settings', {}))
            mappings_count = len(template.get('mappings', {}))
            aliases_count = len(template.get('aliases', {}))

            # Use semantic styling for status indicators
            success_style = self.get_themed_style('semantic_styles', 'success', 'green')
            error_style = self.get_themed_style('semantic_styles', 'error', 'red')

            settings_display = f"[{success_style}]✓ ({settings_count})[/{success_style}]" if settings_count > 0 else f"[{error_style}]✗[/{error_style}]"
            mappings_display = f"[{success_style}]✓ ({mappings_count})[/{success_style}]" if mappings_count > 0 else f"[{error_style}]✗[/{error_style}]"
            aliases_display = f"[{success_style}]✓ ({aliases_count})[/{success_style}]" if aliases_count > 0 else f"[{error_style}]✗[/{error_style}]"

            table.add_row(
                name,
                patterns,
                order,
                settings_display,
                mappings_display,
                aliases_display
            )

        return table

    def _create_composable_templates_table(self, composable_templates: Dict[str, Any]) -> Optional[Table]:
        """Create themed table for composable templates."""
        if 'error' in composable_templates or not composable_templates:
            return None

        # Use StyleSystem for consistent theming if available
        if self.style_system:
            table = self.style_system.create_standard_table(
                title="🔧 Composable Index Templates"
            )
        elif self.table_renderer:
            table = self.table_renderer.create_basic_table(
                title="🔧 Composable Index Templates",
                show_header=True
            )
        else:
            # Fallback with proper themed styles
            header_style = self.get_themed_style('table_styles', 'header_style', 'bold white')
            border_style = self.get_themed_style('table_styles', 'border_style', 'white')
            table = Table(
                title=f"[{self.get_themed_style('panel_styles', 'info', 'bright_cyan')}]🔧 Composable Index Templates[/{self.get_themed_style('panel_styles', 'info', 'bright_cyan')}]",
                box=box.HEAVY if border_style != 'black' else box.SIMPLE,
                show_header=True,
                header_style=header_style,
                border_style=border_style,
                expand=True
            )

        # Use semantic styling for columns
        if self.style_system:
            self.style_system.add_themed_column(table, "Name", "name", no_wrap=True)
            self.style_system.add_themed_column(table, "Index Patterns", "default")
            self.style_system.add_themed_column(table, "Priority", "count", justify="right")
            self.style_system.add_themed_column(table, "Component Templates", "warning")
            self.style_system.add_themed_column(table, "Data Stream", "status", justify="center")
        else:
            # Fallback with semantic theme colors
            table.add_column("Name", style=self.get_themed_style('semantic_styles', 'primary', 'cyan'), no_wrap=True)
            table.add_column("Index Patterns", style=self.get_themed_style('semantic_styles', 'success', 'green'))
            table.add_column("Priority", justify="right", style=self.get_themed_style('semantic_styles', 'secondary', 'magenta'))
            table.add_column("Component Templates", style=self.get_themed_style('semantic_styles', 'warning', 'yellow'))
            table.add_column("Data Stream", justify="center", style=self.get_themed_style('semantic_styles', 'info', 'blue'))

        # Sort templates alphabetically by name for consistent display
        sorted_templates = sorted(composable_templates.items()) if composable_templates else []

        for name, template in sorted_templates:
            if name == 'error':
                continue

            index_template = template.get('index_template', {})
            patterns = ', '.join(index_template.get('index_patterns', []))
            priority = str(index_template.get('priority', 0))
            composed_of = ', '.join(index_template.get('composed_of', []))

            # Use semantic styling for status indicators
            success_style = self.get_themed_style('semantic_styles', 'success', 'green')
            error_style = self.get_themed_style('semantic_styles', 'error', 'red')

            data_stream = f"[{success_style}]✓[/{success_style}]" if index_template.get('data_stream') else f"[{error_style}]✗[/{error_style}]"

            table.add_row(
                name,
                patterns,
                priority,
                composed_of or "None",
                data_stream
            )

        return table

    def _create_component_templates_table(self, component_templates: Dict[str, Any]) -> Optional[Table]:
        """Create themed table for component templates."""
        if 'error' in component_templates or not component_templates:
            return None

        # Use StyleSystem for consistent theming if available
        if self.style_system:
            table = self.style_system.create_standard_table(
                title="🧩 Component Templates"
            )
        elif self.table_renderer:
            table = self.table_renderer.create_basic_table(
                title="🧩 Component Templates",
                show_header=True
            )
        else:
            # Fallback with proper themed styles
            header_style = self.get_themed_style('table_styles', 'header_style', 'bold white')
            border_style = self.get_themed_style('table_styles', 'border_style', 'white')
            table = Table(
                title=f"[{self.get_themed_style('panel_styles', 'info', 'bright_cyan')}]🧩 Component Templates[/{self.get_themed_style('panel_styles', 'info', 'bright_cyan')}]",
                box=box.HEAVY if border_style != 'black' else box.SIMPLE,
                show_header=True,
                header_style=header_style,
                border_style=border_style,
                expand=True
            )

        # Use semantic styling for columns
        if self.style_system:
            self.style_system.add_themed_column(table, "Name", "name", no_wrap=True)
            self.style_system.add_themed_column(table, "Settings", "status", justify="center")
            self.style_system.add_themed_column(table, "Mappings", "status", justify="center")
            self.style_system.add_themed_column(table, "Aliases", "status", justify="center")
            self.style_system.add_themed_column(table, "Version", "count", justify="right")
        else:
            # Fallback with semantic theme colors
            table.add_column("Name", style=self.get_themed_style('semantic_styles', 'primary', 'cyan'), no_wrap=True)
            table.add_column("Settings", justify="center", style=self.get_themed_style('semantic_styles', 'info', 'blue'))
            table.add_column("Mappings", justify="center", style=self.get_themed_style('semantic_styles', 'info', 'blue'))
            table.add_column("Aliases", justify="center", style=self.get_themed_style('semantic_styles', 'info', 'blue'))
            table.add_column("Version", justify="right", style=self.get_themed_style('semantic_styles', 'secondary', 'magenta'))

        for name, template in component_templates.items():
            if name == 'error':
                continue

            component_template = template.get('component_template', {})
            template_def = component_template.get('template', {})

            settings_count = len(template_def.get('settings', {}))
            mappings_count = len(template_def.get('mappings', {}))
            aliases_count = len(template_def.get('aliases', {}))
            version = component_template.get('version', 'N/A')

            # Use semantic styling for status indicators
            success_style = self.get_themed_style('semantic_styles', 'success', 'green')
            error_style = self.get_themed_style('semantic_styles', 'error', 'red')

            settings_display = f"[{success_style}]✓ ({settings_count})[/{success_style}]" if settings_count > 0 else f"[{error_style}]✗[/{error_style}]"
            mappings_display = f"[{success_style}]✓ ({mappings_count})[/{success_style}]" if mappings_count > 0 else f"[{error_style}]✗[/{error_style}]"
            aliases_display = f"[{success_style}]✓ ({aliases_count})[/{success_style}]" if aliases_count > 0 else f"[{error_style}]✗[/{error_style}]"

            table.add_row(
                name,
                settings_display,
                mappings_display,
                aliases_display,
                str(version)
            )

        return table

    def _create_usage_table(self, templates_in_use: Dict[str, Any]) -> Table:
        """Create themed table for templates in use."""
        # Use StyleSystem for consistent theming if available
        if self.style_system:
            table = self.style_system.create_standard_table(
                title="✅ Templates In Use"
            )
        elif self.table_renderer:
            table = self.table_renderer.create_basic_table(
                title="✅ Templates In Use",
                show_header=True
            )
        else:
            # Fallback with proper themed styles
            header_style = self.get_themed_style('table_styles', 'header_style', 'bold white')
            border_style = self.get_themed_style('table_styles', 'border_style', 'white')
            table = Table(
                title=f"[{self.get_themed_style('panel_styles', 'success', 'green')}]✅ Templates In Use[/{self.get_themed_style('panel_styles', 'success', 'green')}]",
                box=box.HEAVY if border_style != 'black' else box.SIMPLE,
                show_header=True,
                header_style=header_style,
                border_style=border_style,
                expand=True
            )

        # Use semantic styling for columns
        if self.style_system:
            self.style_system.add_themed_column(table, "Template", "name", no_wrap=True)
            self.style_system.add_themed_column(table, "Type", "warning")
            self.style_system.add_themed_column(table, "Patterns", "default")
            self.style_system.add_themed_column(table, "Matching Indices", "count", justify="right")
        else:
            # Fallback with semantic theme colors
            table.add_column("Template", style=self.get_themed_style('semantic_styles', 'primary', 'cyan'), no_wrap=True)
            table.add_column("Type", style=self.get_themed_style('semantic_styles', 'warning', 'yellow'))
            table.add_column("Patterns", style=self.get_themed_style('semantic_styles', 'success', 'green'))
            table.add_column("Matching Indices", justify="right", style=self.get_themed_style('semantic_styles', 'info', 'blue'))

        for template_name, info in templates_in_use.items():
            patterns = ', '.join(info['patterns'])
            match_count = info['match_count']
            template_type = info['type'].title()

            table.add_row(
                template_name,
                template_type,
                patterns,
                str(match_count)
            )

        return table

    def _create_unused_templates_table(self, unused_templates: List[Dict[str, Any]]) -> Table:
        """Create themed table for unused templates."""
        # Use StyleSystem for consistent theming if available
        if self.style_system:
            table = self.style_system.create_standard_table(
                title="🔶 Unused Templates"
            )
        elif self.table_renderer:
            table = self.table_renderer.create_basic_table(
                title="🔶 Unused Templates",
                show_header=True
            )
        else:
            # Fallback with proper themed styles
            header_style = self.get_themed_style('table_styles', 'header_style', 'bold white')
            border_style = self.get_themed_style('table_styles', 'border_style', 'white')
            table = Table(
                title=f"[{self.get_themed_style('panel_styles', 'warning', 'yellow')}]🔶 Unused Templates[/{self.get_themed_style('panel_styles', 'warning', 'yellow')}]",
                box=box.HEAVY if border_style != 'black' else box.SIMPLE,
                show_header=True,
                header_style=header_style,
                border_style=border_style,
                expand=True
            )

        # Use semantic styling for columns
        if self.style_system:
            self.style_system.add_themed_column(table, "Template", "name", no_wrap=True)
            self.style_system.add_themed_column(table, "Type", "warning")
            self.style_system.add_themed_column(table, "Patterns", "default")
        else:
            # Fallback with semantic theme colors
            table.add_column("Template", style=self.get_themed_style('semantic_styles', 'primary', 'cyan'), no_wrap=True)
            table.add_column("Type", style=self.get_themed_style('semantic_styles', 'warning', 'yellow'))
            table.add_column("Patterns", style=self.get_themed_style('semantic_styles', 'success', 'green'))

        for template_info in unused_templates:
            patterns = ', '.join(template_info['patterns'])
            template_type = template_info['type'].title()

            table.add_row(
                template_info['name'],
                template_type,
                patterns
            )

        return table

    def _print_template_header(self, template_data: Dict[str, Any]) -> None:
        """Create and display template header panel matching indices command style."""
        template_name = template_data.get('name', 'Unknown')
        template_type_display = template_data.get('type', 'unknown').title()
        template_type = template_data.get('type', 'unknown')
        type_emoji = {"legacy": "🏛️", "composable": "🔧", "component": "🧩"}.get(template_type, "📄")

        # Create centered title similar to indices command
        template_title = f"{type_emoji} {template_type_display} Template: {template_name}"

        # Get cluster info for subtitle
        cluster_info = "Template Configuration Details"
        try:
            # Try to get cluster info if available from context
            if hasattr(self, 'cluster_name') and hasattr(self, 'cluster_version'):
                cluster_info = f"Cluster: {self.cluster_name} (v{self.cluster_version})"
        except:
            pass

        # Use style system if available for consistent styling
        if self.style_system:
            title_panel = Panel(
                self.style_system.create_semantic_text(template_title, "primary", justify="center"),
                subtitle=cluster_info,
                border_style=self.style_system._get_style('table_styles', 'border_style', 'bright_magenta'),
                padding=(1, 2)
            )
        else:
            # Fallback to basic styling
            from rich.text import Text
            header_text = Text(template_title, justify="center")
            title_panel = Panel(
                header_text,
                subtitle=cluster_info,
                border_style=self.get_themed_style('panel_styles', 'info_style', 'cyan'),
                padding=(1, 2)
            )

        self.console.print(title_panel)

    def _create_basic_info_panel(self, template_data: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[Panel]:
        """Create basic information panel for template."""
        info_text = Text()
        template_type = template_data.get('type', 'unknown')

        key_style = self.get_themed_style('table_styles', 'key_style', 'bold')
        value_style = self.get_themed_style('table_styles', 'value_style', 'green')
        number_style = self.get_themed_style('table_styles', 'number_style', 'magenta')
        component_style = self.get_themed_style('table_styles', 'warning_style', 'yellow')
        accent_style = self.get_themed_style('table_styles', 'accent_style', 'blue')

        if template_type == 'legacy':
            patterns = metadata.get('index_patterns', [])
            order = metadata.get('order', 0)

            info_text.append("Index Patterns: ", style=key_style)
            info_text.append(f"{', '.join(patterns) if patterns else 'None'}\n", style=value_style)
            info_text.append("Order: ", style=key_style)
            info_text.append(f"{order}\n", style=number_style)

        elif template_type == 'composable':
            patterns = metadata.get('index_patterns', [])
            priority = metadata.get('priority', 0)
            composed_of = metadata.get('composed_of', [])

            info_text.append("Index Patterns: ", style=key_style)
            info_text.append(f"{', '.join(patterns) if patterns else 'None'}\n", style=value_style)
            info_text.append("Priority: ", style=key_style)
            info_text.append(f"{priority}\n", style=number_style)
            info_text.append("Component Templates: ", style=key_style)
            info_text.append(f"{', '.join(composed_of) if composed_of else 'None'}\n", style=component_style)

            if metadata.get('data_stream'):
                info_text.append("Data Stream: ", style=key_style)
                info_text.append("Enabled\n", style=accent_style)

        version = metadata.get('version')
        if version:
            info_text.append("Version: ", style=key_style)
            info_text.append(f"{version}", style="dim")

        return self._create_themed_panel(
            info_text,
            "ℹ️  Basic Information",
            "info"
        )

    def _create_template_config_panel(self, metadata: Dict[str, Any]) -> Optional[Panel]:
        """Create template configuration panel."""
        config_text = Text()

        key_style = self.get_themed_style('table_styles', 'key_style', 'bold')
        success_style = self.get_themed_style('table_styles', 'success_style', 'green')
        dim_style = self.get_themed_style('table_styles', 'dim_style', 'dim')

        settings_count = len(metadata.get('settings', {}))
        mappings_count = len(metadata.get('mappings', {}))
        aliases_count = len(metadata.get('aliases', {}))

        config_text.append("Settings: ", style=key_style)
        if settings_count > 0:
            config_text.append(f"✓ {settings_count} configuration(s)\n", style=success_style)
        else:
            config_text.append("None\n", style=dim_style)

        config_text.append("Mappings: ", style=key_style)
        if mappings_count > 0:
            config_text.append(f"✓ {mappings_count} field(s)\n", style=success_style)
        else:
            config_text.append("None\n", style=dim_style)

        config_text.append("Aliases: ", style=key_style)
        if aliases_count > 0:
            config_text.append(f"✓ {aliases_count} alias(es)", style=success_style)
        else:
            config_text.append("None", style=dim_style)

        return self._create_themed_panel(
            config_text,
            "🔧 Template Configuration",
            "success"
        )

    def _create_json_panel(self, data: Any, title: str, border_style: Optional[str] = None) -> Panel:
        """Create a panel with Rich JSON syntax highlighting and theme colors."""
        try:
            from rich.syntax import Syntax

            # Get console width for better formatting
            console_width = getattr(self.console, 'size', None)
            if console_width:
                # Account for panel padding and borders (roughly 6 characters)
                max_width = max(40, console_width.width - 6)
            else:
                max_width = 120  # Reasonable default

            # Create JSON string with smart formatting for long lines
            json_str = self._format_json_with_wrapping(data, max_width)

            # Get theme-appropriate syntax highlighting theme
            syntax_theme = "monokai"
            if self.theme_manager:
                # Try to match syntax theme to current theme
                try:
                    current_theme = getattr(self.theme_manager, 'current_theme', 'default')
                    if 'dark' in str(current_theme).lower():
                        syntax_theme = "monokai"
                    elif 'light' in str(current_theme).lower():
                        syntax_theme = "github-light"
                    else:
                        syntax_theme = "native"
                except:
                    syntax_theme = "monokai"  # Safe fallback

            # Create Rich syntax-highlighted JSON with word wrapping
            syntax_json = Syntax(
                json_str,
                "json",
                theme=syntax_theme,
                line_numbers=False,
                background_color="default",
                word_wrap=True,
                code_width=max_width
            )

            # Use StyleSystem panel creation if available
            if self.style_system:
                return self.style_system.create_info_panel(syntax_json, title, "📄")
            else:
                return self._create_themed_panel(
                    syntax_json,
                    title,
                    "info"
                )

        except ImportError:
            # Fallback to plain text JSON if Rich Syntax is not available
            json_text = Text()

            # Get console width for better formatting
            console_width = getattr(self.console, 'size', None)
            if console_width:
                max_width = max(40, console_width.width - 6)
            else:
                max_width = 120

            # Format JSON with smart wrapping
            formatted_json = self._format_json_with_wrapping(data, max_width)

            dim_style = self.get_themed_style('panel_styles', 'subtitle', 'dim')
            json_text.append(formatted_json, style=dim_style)

            # Use StyleSystem panel creation if available
            if self.style_system:
                return self.style_system.create_info_panel(json_text, title, "📄")
            else:
                return self._create_themed_panel(
                    json_text,
                    title,
                    "info"
                )

    def _format_json_with_wrapping(self, data: Any, max_width: int) -> str:
        """
        Format JSON with intelligent line wrapping at commas for better readability.

        Args:
            data: Data to format as JSON
            max_width: Maximum line width before wrapping

        Returns:
            str: Formatted JSON string with smart line breaks
        """
        # Start with standard JSON formatting
        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        lines = json_str.split('\n')
        formatted_lines = []

        for line in lines:
            if len(line) > max_width and ',' in line and '"' in line:
                # This is likely a long string value with commas (like server names)
                # Find the value part (after the colon)
                if ':' in line:
                    key_part, value_part = line.split(':', 1)
                    value_part = value_part.strip()

                    # Check if it's a quoted string value
                    if value_part.startswith('"') and value_part.endswith('"'):
                        # Extract the string content
                        string_content = value_part[1:-1]  # Remove quotes

                        # Split at commas and format nicely
                        if ',' in string_content:
                            formatted_lines.extend(
                                self._format_long_string_value(key_part, string_content, max_width)
                            )
                            continue

                # Fallback: split at commas if no special handling worked
                if ',' in line:
                    indent = len(line) - len(line.lstrip())
                    indent_str = ' ' * indent
                    parts = line.split(',')
                    current_line = parts[0]

                    for part in parts[1:]:
                        test_line = current_line + ',' + part
                        if len(test_line) > max_width:
                            formatted_lines.append(current_line + ',')
                            current_line = indent_str + part.strip()
                        else:
                            current_line = test_line

                    formatted_lines.append(current_line)
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    def _format_long_string_value(self, key_part: str, string_content: str, max_width: int) -> List[str]:
        """
        Format a long comma-separated string value with proper comma placement.

        Args:
            key_part: The JSON key part (e.g., '            "_name"')
            string_content: The string content without quotes
            max_width: Maximum line width

        Returns:
            List[str]: Formatted lines with inline comma style
        """
        items = [item.strip() for item in string_content.split(',')]
        indent = len(key_part)

        result_lines = []
        result_lines.append(key_part + ': "' + items[0] + ',')

        # Add middle items with commas
        for item in items[1:-1]:
            result_lines.append(' ' * (indent + 4) + item + ',')

        # Add last item without trailing comma but close quote
        if len(items) > 1:
            result_lines.append(' ' * (indent + 4) + items[-1] + '"')
        else:
            # Single item case - fix the line we already added
            result_lines[-1] = key_part + ': "' + items[0] + '"'

        return result_lines

    def _print_usage_summary(self, templates_in_use: Dict[str, Any], unused_templates: List[Dict[str, Any]]) -> None:
        """Create and display usage summary panel."""
        summary_text = Text()

        # Use semantic styling for consistent theming
        success_style = self.get_themed_style('semantic_styles', 'success', 'bold green')
        warning_style = self.get_themed_style('semantic_styles', 'warning', 'bold yellow')

        summary_text.append(f"📊 Templates in use: {len(templates_in_use)}\n", style=success_style)
        summary_text.append(f"🔶 Unused templates: {len(unused_templates)}", style=warning_style)

        # Use StyleSystem panel creation if available
        if self.style_system:
            summary_panel = self.style_system.create_info_panel(
                summary_text,
                "📈 Usage Summary"
            )
        else:
            summary_panel = self._create_themed_panel(
                summary_text,
                "📈 Usage Summary",
                "info"
            )
        self.console.print(summary_panel)

    def _show_no_templates_message(self, template_type: str) -> None:
        """Display message when no templates are found."""
        no_templates_text = Text()
        warning_style = self.get_themed_style('semantic_styles', 'warning', 'dim yellow')
        muted_style = self.get_themed_style('panel_styles', 'subtitle', 'dim')

        no_templates_text.append("No templates found", style=warning_style)
        if template_type != 'all':
            no_templates_text.append(f" of type '{template_type}'", style=muted_style)

        # Use StyleSystem panel creation if available
        if self.style_system:
            panel = self.style_system.create_info_panel(
                no_templates_text,
                "ℹ️  Templates"
            )
        else:
            panel = self._create_themed_panel(
                no_templates_text,
                "ℹ️  Templates",
                "info"
            )
        self.console.print(panel)

    def _show_template_not_found(self, template_name: str) -> None:
        """Display message when a specific template is not found."""
        warning_style = self.get_themed_style('semantic_styles', 'warning', 'yellow')
        not_found_text = Text(f"Template '{template_name}' not found", style=warning_style)

        # Use StyleSystem panel creation if available
        if self.style_system:
            panel = self.style_system.create_warning_panel(
                not_found_text,
                "🔶 Template Not Found"
            )
        else:
            panel = self._create_themed_panel(
                not_found_text,
                "🔶 Template Not Found",
                "warning"
            )
        self.console.print(panel)

    def _create_themed_panel(self, content: Any, title: Optional[str] = None,
                           theme_style: Optional[str] = None, border_style: Optional[str] = None) -> Panel:
        """Create a themed panel using the panel renderer if available."""
        if self.panel_renderer:
            return self.panel_renderer.create_themed_panel(
                content, title=title, title_style=theme_style, border_style=border_style
            )
        else:
            # Fallback panel creation with proper semantic styling
            if border_style is None:
                # Map theme styles to proper semantic styles
                border_style = self.get_themed_style('table_styles', 'border_style', 'white')

            # Apply title styling if provided
            if title and theme_style:
                title_color = self.get_themed_style('semantic_styles', theme_style, 'cyan')
                title = f"[{title_color}]{title}[/{title_color}]"

            return Panel(content, title=title, border_style=border_style, padding=(1, 2))

    def _display_panels(self, panels: List[Panel]) -> None:
        """Display panels in an organized layout."""
        if len(panels) > 2:
            # Display in pairs for better layout
            for i in range(0, len(panels), 2):
                if i + 1 < len(panels):
                    self.console.print(Columns([panels[i], panels[i+1]], expand=True))
                else:
                    self.console.print(panels[i])
        else:
            # Stack panels vertically
            for panel in panels:
                self.console.print(panel)

    def _has_templates(self, templates_data: Dict[str, Any], template_type: str) -> bool:
        """Check if templates data contains any templates of the specified type."""
        if template_type == 'all':
            return (
                bool(templates_data.get('legacy_templates')) or
                bool(templates_data.get('composable_templates')) or
                bool(templates_data.get('component_templates'))
            )
        elif template_type == 'legacy':
            return bool(templates_data.get('legacy_templates'))
        elif template_type == 'composable':
            return bool(templates_data.get('composable_templates'))
        elif template_type == 'component':
            return bool(templates_data.get('component_templates'))

        return False
