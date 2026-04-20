"""
Theme management for Elasticsearch command-line tool display.

This module centralizes all theme loading, caching, and style retrieval logic,
making it easy to manage themes across the entire application.
"""

import os
import yaml
from typing import Dict, Any, Optional


class ThemeManager:
    """
    Manages theme loading, caching, and style retrieval for the application.
    
    Supports:
    - Loading themes from themes.yml files
    - Built-in fallback themes
    - Style caching for performance
    - Backward compatibility with legacy theme configurations
    """
    
    def __init__(self, configuration_manager=None):
        """
        Initialize the theme manager.
        
        Args:
            configuration_manager: Configuration manager instance for accessing settings
        """
        self.configuration_manager = configuration_manager
        self._theme_cache = {}
        self._current_theme_name = None
        self._current_theme_data = None
        
    def get_theme_name(self) -> str:
        """Get the current theme name from configuration or default to 'rich'."""
        if self.configuration_manager:
            return self.configuration_manager.get_display_theme()
        return 'rich'
    
    def get_theme_styles(self) -> Dict[str, Any]:
        """
        Get styling configuration for table/display elements.
        
        This method provides backward compatibility with the original get_theme_styles function.
        
        Returns:
            dict: Style configuration with 'header_style', 'health_styles', 'status_styles', etc.
        """
        theme_name = self.get_theme_name()
        
        # Check cache first
        cache_key = f"{theme_name}_styles"
        if cache_key in self._theme_cache:
            return self._theme_cache[cache_key]
        
        # Load full theme data first
        full_theme_data = self.get_full_theme_data()
        
        # Extract and combine styles for backward compatibility
        styles = {}
        
        # Add table_styles to the root level for backward compatibility
        if 'table_styles' in full_theme_data:
            styles.update(full_theme_data['table_styles'])
        
        # Add other style categories at the root level
        for category in ['panel_styles', 'help_styles']:
            if category in full_theme_data:
                styles[category] = full_theme_data[category]
        
        # Cache the result
        self._theme_cache[cache_key] = styles
        return styles
    
    def get_full_theme_data(self) -> Dict[str, Any]:
        """
        Get complete theme data including all categories.
        
        Returns:
            dict: Complete theme configuration with table_styles, panel_styles, help_styles, etc.
        """
        theme_name = self.get_theme_name()
        
        # Check cache first
        cache_key = f"{theme_name}_full"
        if cache_key in self._theme_cache:
            return self._theme_cache[cache_key]
        
        # Try to load from themes file
        full_data = self._load_full_theme_from_file(theme_name)
        if full_data:
            self._theme_cache[cache_key] = full_data
            return full_data
            
        # Fallback to built-in theme
        full_data = self._get_builtin_full_theme(theme_name)
        self._theme_cache[cache_key] = full_data
        return full_data
    
    def get_themed_style(self, category: str, style_type: str, default: str = 'white') -> str:
        """
        Get themed style for specific UI elements.
        
        Supports dot-notation for nested keys, e.g. style_type='row_styles.zebra'
        will traverse into row_styles -> zebra within the category dict.
        
        Args:
            category: Style category ('panel_styles', 'help_styles', etc.)
            style_type: Specific style within category ('title', 'success', etc.)
            default: Default style if not found
            
        Returns:
            str: Style string for Rich formatting
        """
        full_theme = self.get_full_theme_data()
        category_data = full_theme.get(category, {})
        
        # Support dot-notation for nested keys (e.g. 'row_styles.zebra')
        parts = style_type.split('.')
        current = category_data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return default
            if current is None:
                return default
        
        return current if isinstance(current, str) else default
    
    def clear_cache(self):
        """Clear the theme cache to force reload on next access."""
        self._theme_cache.clear()
        self._current_theme_name = None
        self._current_theme_data = None
    
    def _load_theme_styles_from_file(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """Load theme styles from themes.yml file."""
        try:
            themes_file = self._get_themes_file_path()
            if not os.path.exists(themes_file):
                return None
                
            with open(themes_file, 'r') as f:
                themes_config = yaml.safe_load(f)
            
            themes_dict = themes_config.get('themes', {})
            if theme_name in themes_dict:
                theme_data = themes_dict[theme_name]
                # Return table_styles for backward compatibility
                if 'table_styles' in theme_data:
                    return theme_data['table_styles']
                else:
                    # Fallback to old flat structure
                    return theme_data
                    
        except Exception:
            pass
        return None
    
    def _load_full_theme_from_file(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """Load complete theme data from themes.yml file."""
        try:
            themes_file = self._get_themes_file_path()
            if not os.path.exists(themes_file):
                return None
                
            with open(themes_file, 'r') as f:
                themes_config = yaml.safe_load(f)
            
            themes_dict = themes_config.get('themes', {})
            if theme_name in themes_dict:
                return themes_dict[theme_name]
                
        except Exception:
            pass
        return None
    
    def _load_legacy_theme_styles(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """Load theme styles from legacy configuration."""
        if not self.configuration_manager or not hasattr(self.configuration_manager, 'default_settings'):
            return None
            
        theme_styles_config = self.configuration_manager.default_settings.get('theme_styles', {})
        if theme_name in theme_styles_config:
            return theme_styles_config[theme_name]
        return None
    
    def _get_themes_file_path(self) -> str:
        """Get the path to the themes.yml file."""
        themes_file = 'themes.yml'
        if self.configuration_manager:
            themes_file = self.configuration_manager.default_settings.get('themes_file', 'themes.yml')
        
        # Support relative and absolute paths
        if not os.path.isabs(themes_file):
            config_dir = '.'
            if self.configuration_manager:
                # Handle both dual-file and single-file modes
                if hasattr(self.configuration_manager, 'is_dual_file_mode') and self.configuration_manager.is_dual_file_mode:
                    # In dual-file mode, use the main config path
                    if hasattr(self.configuration_manager, 'main_config_path') and self.configuration_manager.main_config_path:
                        config_dir = os.path.dirname(self.configuration_manager.main_config_path)
                elif hasattr(self.configuration_manager, 'config_file_path') and self.configuration_manager.config_file_path:
                    # In single-file mode, use the config file path
                    config_dir = os.path.dirname(self.configuration_manager.config_file_path)
            candidate = os.path.join(config_dir, themes_file)

            # If not found via config paths, try the binary/script directory
            if not os.path.exists(candidate):
                try:
                    from utils import get_script_dir
                    candidate = os.path.join(get_script_dir(), themes_file)
                except Exception:
                    pass

            themes_file = candidate
        
        return themes_file
    
    def _get_builtin_theme_styles(self, theme_name: str) -> Dict[str, Any]:
        """Get built-in theme styles."""
        if theme_name == 'plain':
            return {
                'header_style': 'bold white',
                'border_style': 'black',
                'health_styles': {
                    'green': {'icon': 'bold', 'text': 'bold'},
                    'yellow': {'icon': 'bold', 'text': 'bold'}, 
                    'red': {'icon': 'bold', 'text': 'bold'}
                },
                'status_styles': {
                    'open': {'icon': 'bold', 'text': 'bold'},
                    'close': {'icon': 'bold', 'text': 'bold'}
                },
                'state_styles': {
                    'STARTED': {'icon': 'bold', 'text': 'bold'},
                    'INITIALIZING': {'icon': 'bold', 'text': 'bold'},
                    'RELOCATING': {'icon': 'bold', 'text': 'bold'},
                    'UNASSIGNED': {'icon': 'bold', 'text': 'bold'},
                    'default': {'icon': 'bold', 'text': 'bold'}
                },
                'type_styles': {
                    'primary': {'icon': 'bold', 'text': 'bold'},
                    'replica': {'icon': 'bold', 'text': 'bold'}
                },
                'panel_styles': {
                    'title': 'bold',
                    'subtitle': 'dim',
                    'success': 'bold',
                    'warning': 'bold',
                    'error': 'bold',
                    'info': 'bold',
                    'secondary': 'bold'
                },
                'help_styles': {
                    'title': 'bold',
                    'section_header': 'bold',
                    'command': 'bold',
                    'description': '',
                    'example': '',
                    'footer': 'dim'
                }
            }
        
        # Default to rich theme
        return {
            'header_style': 'bold white on dark_blue',
            'border_style': 'white',
            'health_styles': {
                'green': {'icon': 'green bold', 'text': 'green bold'},
                'yellow': {'icon': 'yellow bold', 'text': 'yellow bold'}, 
                'red': {'icon': 'red bold', 'text': 'red bold'}
            },
            'status_styles': {
                'open': {'icon': 'blue bold', 'text': 'blue bold'},
                'close': {'icon': 'red bold', 'text': 'red bold'}
            },
            'state_styles': {
                'STARTED': {'icon': 'green bold', 'text': 'green bold'},
                'INITIALIZING': {'icon': 'yellow bold', 'text': 'yellow bold'},
                'RELOCATING': {'icon': 'blue bold', 'text': 'blue bold'},
                'UNASSIGNED': {'icon': 'red bold', 'text': 'red bold'},
                'default': {'icon': 'bold', 'text': 'bold'}
            },
            'type_styles': {
                'primary': {'icon': 'gold1 bold', 'text': 'gold1 bold'},
                'replica': {'icon': 'cyan bold', 'text': 'cyan bold'}
            },
            'panel_styles': {
                'title': 'bold cyan',
                'subtitle': 'dim white',
                'success': 'green',
                'warning': 'yellow',
                'error': 'red',
                'info': 'blue',
                'secondary': 'magenta'
            },
            'help_styles': {
                'title': 'bold cyan',
                'section_header': 'bold yellow',
                'command': 'bold yellow',
                'description': 'white',
                'example': 'cyan',
                'footer': 'dim white'
            }
        }
    
    def _get_builtin_full_theme(self, theme_name: str) -> Dict[str, Any]:
        """Get built-in complete theme data."""
        styles = self._get_builtin_theme_styles(theme_name)
        
        # Extract panel_styles and help_styles if they exist in styles
        panel_styles = styles.pop('panel_styles', {})
        help_styles = styles.pop('help_styles', {})

        # Build semantic_styles from panel_styles so the semantic lookup works
        # even when falling back to the built-in theme (no themes.yml present)
        semantic_styles = {
            'primary':   panel_styles.get('title', 'cyan'),
            'secondary': panel_styles.get('secondary', 'magenta'),
            'success':   panel_styles.get('success', 'green'),
            'warning':   panel_styles.get('warning', 'yellow'),
            'error':     panel_styles.get('error', 'red'),
            'info':      panel_styles.get('info', 'blue'),
            'neutral':   styles.get('row_styles', {}).get('normal', 'white'),
            'muted':     panel_styles.get('subtitle', 'dim white'),
        }
        
        return {
            'table_styles': styles,
            'panel_styles': panel_styles,
            'help_styles': help_styles,
            'semantic_styles': semantic_styles,
        }


# Backward compatibility functions
def get_theme_styles(configuration_manager):
    """
    Backward compatibility function for existing code.
    
    Returns:
        dict: Style configuration
    """
    theme_manager = ThemeManager(configuration_manager)
    return theme_manager.get_theme_styles()


def get_full_theme_data(configuration_manager):
    """
    Backward compatibility function for existing code.
    
    Returns:
        dict: Complete theme configuration
    """
    theme_manager = ThemeManager(configuration_manager)
    return theme_manager.get_full_theme_data()
