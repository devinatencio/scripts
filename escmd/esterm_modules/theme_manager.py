#!/usr/bin/env python3
"""
ESterm Theme Manager

Independent theme system for ESterm interactive terminal.
This is completely separate from ESCMD's theme system and only affects ESterm UI elements.

Features:
- Load themes from esterm_themes.yml
- Cache theme data for performance
- Provide theme switching capabilities
- Support for different UI element categories (banner, prompt, status, messages, etc.)
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from rich.console import Console


class EstermThemeManager:
    """
    Manages theme loading and styling for ESterm interactive terminal.

    This class is completely independent from ESCMD's theme system and only
    handles styling for ESterm-specific UI elements.
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the ESterm theme manager.

        Args:
            console: Rich Console instance for output
        """
        self.console = console or Console()
        self._theme_cache = {}
        self._current_theme_name = None
        self._themes_file_path = None
        self._config_file_path = None
        self._config_data = None

        # Initialize with default theme
        self._load_themes_file()
        self._load_config_file()

    def _load_themes_file(self):
        """Load the esterm themes configuration file."""
        # Get the directory where this module is located
        module_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to the escmd directory
        escmd_dir = os.path.dirname(module_dir)
        # Look for esterm_themes.yml
        self._themes_file_path = os.path.join(escmd_dir, 'esterm_themes.yml')

        if not os.path.exists(self._themes_file_path):
            # Fallback to current directory
            self._themes_file_path = 'esterm_themes.yml'

    def _load_config_file(self):
        """Load the esterm configuration file."""
        # Get the directory where this module is located
        module_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to the escmd directory
        escmd_dir = os.path.dirname(module_dir)
        # Look for esterm_config.yml
        self._config_file_path = os.path.join(escmd_dir, 'esterm_config.yml')

        if not os.path.exists(self._config_file_path):
            # Fallback to current directory
            self._config_file_path = 'esterm_config.yml'

    def get_current_theme(self) -> str:
        """Get the name of the current theme."""
        if self._current_theme_name is None:
            self._current_theme_name = self._get_configured_theme()
        return self._current_theme_name

    def set_theme(self, theme_name: str) -> bool:
        """
        Set the current theme.

        Args:
            theme_name: Name of the theme to set

        Returns:
            bool: True if theme was successfully set, False otherwise
        """
        available_themes = self.get_available_themes()
        if theme_name not in available_themes:
            return False

        self._current_theme_name = theme_name
        # Clear cache to force reload
        self._theme_cache.clear()

        # Save theme preference to config
        self._save_theme_preference(theme_name)
        return True

    def get_available_themes(self) -> List[str]:
        """
        Get list of available theme names.

        Returns:
            List[str]: List of available theme names
        """
        themes_data = self._load_themes_data()
        if themes_data and 'esterm_themes' in themes_data:
            return list(themes_data['esterm_themes'].keys())
        return ['rich']  # Fallback default

    def get_theme_info(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """
        Get theme metadata information.

        Args:
            theme_name: Name of theme to get info for (current theme if None)

        Returns:
            Dict[str, str]: Theme metadata
        """
        if theme_name is None:
            theme_name = self.get_current_theme()

        themes_data = self._load_themes_data()
        if themes_data and 'theme_info' in themes_data:
            return themes_data['theme_info'].get(theme_name, {
                'name': theme_name.title(),
                'description': f'{theme_name} theme',
                'best_for': 'General use'
            })

        return {
            'name': theme_name.title(),
            'description': f'{theme_name} theme',
            'best_for': 'General use'
        }

    def get_style(self, category: str, style_type: str, default: str = 'white') -> str:
        """
        Get a specific style from the current theme.

        Args:
            category: Style category ('banner', 'prompt', 'status', etc.)
            style_type: Specific style within category ('title_style', 'error_style', etc.)
            default: Default style if not found

        Returns:
            str: Rich style string
        """
        theme_name = self.get_current_theme()
        cache_key = f"{theme_name}_{category}_{style_type}"

        if cache_key in self._theme_cache:
            return self._theme_cache[cache_key]

        theme_data = self._get_theme_data(theme_name)
        style = theme_data.get(category, {}).get(style_type, default)

        self._theme_cache[cache_key] = style
        return style

    def get_banner_styles(self) -> Dict[str, str]:
        """Get all banner-related styles."""
        return self._get_category_styles('banner')

    def get_prompt_styles(self) -> Dict[str, str]:
        """Get all prompt-related styles."""
        return self._get_category_styles('prompt')

    def get_status_styles(self) -> Dict[str, str]:
        """Get all status-related styles."""
        return self._get_category_styles('status')

    def get_message_styles(self) -> Dict[str, str]:
        """Get all message-related styles."""
        return self._get_category_styles('messages')

    def get_panel_styles(self) -> Dict[str, str]:
        """Get all panel-related styles."""
        return self._get_category_styles('panels')

    def get_help_styles(self) -> Dict[str, str]:
        """Get all help-related styles."""
        return self._get_category_styles('help')

    def preview_theme(self, theme_name: str):
        """
        Display a preview of the specified theme.

        Args:
            theme_name: Name of the theme to preview
        """
        if theme_name not in self.get_available_themes():
            self.console.print(f"[red]Theme '{theme_name}' not found[/red]")
            return

        # Temporarily switch to the theme for preview
        original_theme = self.get_current_theme()
        self.set_theme(theme_name)

        try:
            # Get theme info
            theme_info = self.get_theme_info(theme_name)

            # Create preview panel
            from rich.panel import Panel
            from rich.text import Text

            preview_text = Text()
            preview_text.append(f"Theme: {theme_info['name']}\n", style=self.get_style('banner', 'title_style'))
            preview_text.append(f"Description: {theme_info['description']}\n", style=self.get_style('banner', 'subtitle_style'))
            preview_text.append(f"Best for: {theme_info['best_for']}\n\n", style=self.get_style('status', 'info_style'))

            preview_text.append("Sample Elements:\n", style=self.get_style('help', 'section_header_style'))
            preview_text.append("• Success message", style=self.get_style('messages', 'success_style'))
            preview_text.append(" | ")
            preview_text.append("Warning message", style=self.get_style('messages', 'warning_style'))
            preview_text.append(" | ")
            preview_text.append("Error message\n", style=self.get_style('messages', 'error_style'))

            preview_text.append("• Connected cluster", style=self.get_style('prompt', 'connected_cluster_style'))
            preview_text.append(" | ")
            preview_text.append("Disconnected", style=self.get_style('prompt', 'disconnected_style'))
            preview_text.append(" | ")
            preview_text.append("Warning status\n", style=self.get_style('prompt', 'warning_cluster_style'))

            preview_text.append("• Command example", style=self.get_style('help', 'command_style'))
            preview_text.append(" - Description text", style=self.get_style('help', 'description_style'))

            panel = Panel(
                preview_text,
                title=f"🎨 Theme Preview: {theme_name}",
                border_style=self.get_style('panels', 'border_style'),
                padding=(1, 2)
            )

            self.console.print(panel)

        finally:
            # Restore original theme
            self.set_theme(original_theme)

    def list_themes(self):
        """Display a list of all available themes with descriptions."""
        from rich.table import Table
        from rich.panel import Panel

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Theme", style="bold")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Best For", style="dim")

        current_theme = self.get_current_theme()
        for theme_name in sorted(self.get_available_themes()):
            theme_info = self.get_theme_info(theme_name)
            marker = "→ " if theme_name == current_theme else "  "

            table.add_row(
                f"{marker}{theme_name}",
                theme_info.get('name', theme_name.title()),
                theme_info.get('description', 'No description'),
                theme_info.get('best_for', 'General use')
            )

        panel = Panel(
            table,
            title="🎨 Available ESterm Themes",
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print(panel)

    def _get_category_styles(self, category: str) -> Dict[str, str]:
        """Get all styles for a specific category."""
        theme_name = self.get_current_theme()
        theme_data = self._get_theme_data(theme_name)
        return theme_data.get(category, {})

    def _get_theme_data(self, theme_name: str) -> Dict[str, Any]:
        """Get complete theme data for a specific theme."""
        cache_key = f"theme_data_{theme_name}"
        if cache_key in self._theme_cache:
            return self._theme_cache[cache_key]

        themes_data = self._load_themes_data()
        if themes_data and 'esterm_themes' in themes_data:
            theme_data = themes_data['esterm_themes'].get(theme_name, {})
        else:
            theme_data = self._get_builtin_theme_data(theme_name)

        self._theme_cache[cache_key] = theme_data
        return theme_data

    def _load_themes_data(self) -> Optional[Dict[str, Any]]:
        """Load themes data from the YAML file."""
        try:
            if os.path.exists(self._themes_file_path):
                with open(self._themes_file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load themes file: {e}[/yellow]")
        return None

    def _get_configured_theme(self) -> str:
        """Get the configured theme name from config file or default."""
        config_data = self._load_config_data()
        if config_data and 'theme' in config_data and 'current' in config_data['theme']:
            configured_theme = config_data['theme']['current']
            # Validate that the theme exists
            if configured_theme in self.get_available_themes():
                return configured_theme

        # Fallback to themes file default
        themes_data = self._load_themes_data()
        if themes_data:
            return themes_data.get('default_theme', 'rich')
        return 'rich'

    def _load_config_data(self) -> Optional[Dict[str, Any]]:
        """Load configuration data from the YAML file."""
        try:
            if os.path.exists(self._config_file_path):
                with open(self._config_file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load config file: {e}[/yellow]")
        return None

    def _save_theme_preference(self, theme_name: str):
        """Save the current theme preference to config file."""
        try:
            config_data = self._load_config_data() or {}

            # Ensure theme section exists
            if 'theme' not in config_data:
                config_data['theme'] = {}

            # Update current theme
            config_data['theme']['current'] = theme_name

            # Write back to file
            with open(self._config_file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config_data, f, default_flow_style=False, indent=2)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save theme preference: {e}[/yellow]")

    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key_path: Path to the config value (e.g., 'ui.prompt.show_status_colors')
            default: Default value if key not found

        Returns:
            Any: Configuration value or default
        """
        config_data = self._load_config_data()
        if not config_data:
            return default

        keys = key_path.split('.')
        current = config_data

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def should_show_banner(self) -> bool:
        """Check if banner should be shown based on config."""
        return self.get_config_value('ui.show_banner', True)

    def should_show_theme_in_banner(self) -> bool:
        """Check if theme name should be shown in banner."""
        return self.get_config_value('ui.show_theme_in_banner', True)

    def get_fallback_theme(self) -> str:
        """Get the fallback theme name from config."""
        return self.get_config_value('theme.fallback', 'plain')

    def _get_builtin_theme_data(self, theme_name: str) -> Dict[str, Any]:
        """Get built-in theme data as fallback."""
        if theme_name == 'plain':
            return {
                'banner': {
                    'title_style': 'bold white',
                    'subtitle_style': 'white',
                    'version_style': 'bold',
                    'welcome_style': 'white',
                    'border_style': 'white'
                },
                'prompt': {
                    'connected_cluster_style': 'bold',
                    'disconnected_style': 'bold',
                    'warning_cluster_style': 'bold',
                    'prompt_symbol_style': 'bold'
                },
                'status': {
                    'title_style': 'bold',
                    'label_style': 'bold',
                    'value_style': 'white',
                    'success_style': 'bold',
                    'warning_style': 'bold',
                    'error_style': 'bold',
                    'info_style': 'bold',
                    'border_style': 'white'
                },
                'messages': {
                    'success_style': 'bold',
                    'error_style': 'bold',
                    'warning_style': 'bold',
                    'info_style': 'bold',
                    'progress_style': 'bold'
                },
                'panels': {
                    'title_style': 'bold',
                    'subtitle_style': 'white',
                    'border_style': 'white',
                    'content_style': 'white'
                },
                'help': {
                    'title_style': 'bold',
                    'section_header_style': 'bold',
                    'command_style': 'bold',
                    'description_style': 'white',
                    'example_style': 'white',
                    'footer_style': 'white'
                }
            }

        # Default to 'rich' theme
        return {
            'banner': {
                'title_style': 'bold bright_blue',
                'subtitle_style': 'dim cyan',
                'version_style': 'bright_green',
                'welcome_style': 'green',
                'border_style': 'blue'
            },
            'prompt': {
                'connected_cluster_style': 'green',
                'disconnected_style': 'red',
                'warning_cluster_style': 'yellow',
                'prompt_symbol_style': 'bold blue'
            },
            'status': {
                'title_style': 'bold cyan',
                'label_style': 'bold white',
                'value_style': 'cyan',
                'success_style': 'green',
                'warning_style': 'yellow',
                'error_style': 'red',
                'info_style': 'blue',
                'border_style': 'cyan'
            },
            'messages': {
                'success_style': 'green',
                'error_style': 'red',
                'warning_style': 'yellow',
                'info_style': 'blue',
                'progress_style': 'blue'
            },
            'panels': {
                'title_style': 'bold cyan',
                'subtitle_style': 'dim white',
                'border_style': 'blue',
                'content_style': 'white'
            },
            'help': {
                'title_style': 'bold cyan',
                'section_header_style': 'bold yellow',
                'command_style': 'bold green',
                'description_style': 'white',
                'example_style': 'cyan',
                'footer_style': 'dim white'
            }
        }

    def clear_cache(self):
        """Clear the theme cache to force reload."""
        self._theme_cache.clear()
