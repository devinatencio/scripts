"""
Table rendering utilities for Elasticsearch command-line tool.

This module provides table creation and formatting capabilities using Rich,
with integrated theme support for consistent visual presentation.
"""

import sys
from typing import Any, Dict, List, Optional, Union
from rich.table import Table
from rich.console import Console
from rich.pager import Pager
from rich.text import Text
from rich import box


class TableRenderer:
    """
    Handles table creation and styling with theme integration.
    
    Provides methods for creating consistently styled tables across the application,
    with support for various data formats and display options.
    """
    
    def __init__(self, theme_manager=None, console=None):
        """
        Initialize the table renderer.
        
        Args:
            theme_manager: Theme manager for styling
            console: Rich console instance
        """
        self.theme_manager = theme_manager
        self.console = console or Console()
        self._default_box_style = box.SIMPLE
    
    def create_basic_table(self, 
                          title: Optional[str] = None,
                          box_style: Optional[Any] = None,
                          expand: bool = True,
                          show_header: bool = True,
                          **kwargs) -> Table:
        """
        Create a basic themed table.
        
        Args:
            title: Table title
            box_style: Box style for the table
            expand: Whether table should expand to full width
            show_header: Whether to show the header
            **kwargs: Additional Table arguments
            
        Returns:
            Table: Rich Table object
        """
        if box_style is None:
            box_style = self._get_box_style()
        
        # Apply theme to title
        if title:
            title_style = self._get_themed_style('table_styles', 'header_style', 'bold white')
            title = f"[{title_style}]{title}[/{title_style}]"
        
        return Table(
            title=title,
            box=box_style,
            expand=expand,
            show_header=show_header,
            **kwargs
        )
    
    def print_table_from_dict(self, title: str, data_dict: Dict[str, Any]) -> None:
        """
        Print a table from a dictionary of data.
        
        Args:
            title: Table title
            data_dict: Dictionary containing the data to display
        """
        if not data_dict:
            return
        
        table = self.create_basic_table(title=title)
        
        # Add columns
        table.add_column("Key", style="cyan", ratio=1)
        table.add_column("Value", style="white", ratio=2)
        
        # Add rows
        for key, value in data_dict.items():
            if isinstance(value, (dict, list)):
                value = str(value)
            table.add_row(str(key), str(value))
        
        self.console.print(table)
    
    def create_status_styled_cell(self, value: str, status_type: str = 'default') -> str:
        """
        Create a status-styled cell value.
        
        Args:
            value: The value to style
            status_type: Type of status for styling
            
        Returns:
            str: Styled cell value
        """
        # Get theme-based styling
        if status_type in ['green', 'yellow', 'red']:
            style_config = self._get_themed_style('table_styles', 'health_styles', {})
            if isinstance(style_config, dict) and status_type in style_config:
                text_style = style_config[status_type].get('text', 'white')
                return f"[{text_style}]{value}[/{text_style}]"
        
        return str(value)
    
    def create_state_styled_cell(self, value: str) -> str:
        """
        Create a state-styled cell value.
        
        Args:
            value: The state value to style
            
        Returns:
            str: Styled cell value
        """
        state_styles = self._get_themed_style('table_styles', 'state_styles', {})
        
        if isinstance(state_styles, dict):
            state_key = value.upper() if isinstance(value, str) else str(value).upper()
            
            if state_key in state_styles:
                style_config = state_styles[state_key]
                if isinstance(style_config, dict):
                    text_style = style_config.get('text', 'white')
                    return f"[{text_style}]{value}[/{text_style}]"
            elif 'default' in state_styles:
                style_config = state_styles['default']
                if isinstance(style_config, dict):
                    text_style = style_config.get('text', 'white')
                    return f"[{text_style}]{value}[/{text_style}]"
        
        return str(value)
    
    def format_bytes(self, size_in_bytes: Union[int, float]) -> str:
        """
        Format byte size into human-readable format.
        
        Args:
            size_in_bytes: Size in bytes
            
        Returns:
            str: Formatted size string
        """
        if size_in_bytes == 0:
            return "0B"

        negative = float(size_in_bytes) < 0
        size = abs(float(size_in_bytes))
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        out = f"{size:.2f}{units[unit_index]}"
        return f"-{out}" if negative else out
    
    def print_with_pager(self, content: Any, use_pager: bool = False) -> None:
        """
        Print content with optional pager support.
        
        Args:
            content: Content to print
            use_pager: Whether to use pager for large output
        """
        if use_pager and sys.stdout.isatty():
            with self.console.pager():
                self.console.print(content)
        else:
            self.console.print(content)
    
    def _get_themed_style(self, category: str, style_type: str, default: Any = None) -> Any:
        """Get themed style, with fallback if theme manager not available."""
        if self.theme_manager:
            if category == 'table_styles':
                theme_styles = self.theme_manager.get_theme_styles()
                return theme_styles.get(style_type, default)
            else:
                return self.theme_manager.get_themed_style(category, style_type, default)
        return default
    
    def _get_box_style(self) -> Any:
        """Get the box style from theme or use default."""
        # This will be enhanced when we have more theme data
        return self._default_box_style
    
    def get_state_color(self, state: str) -> str:
        """
        Get color for a given state.
        
        Args:
            state: State string
            
        Returns:
            str: Color name for the state
        """
        state_colors = {
            'green': 'green',
            'yellow': 'yellow', 
            'red': 'red',
            'STARTED': 'green',
            'INITIALIZING': 'yellow',
            'RELOCATING': 'blue',
            'UNASSIGNED': 'red',
            'open': 'blue',
            'close': 'red'
        }
        
        return state_colors.get(state, 'white')


# Backward compatibility - this will be populated as we migrate more methods
def print_table_from_dict(title, data_dict, theme_manager=None):
    """Backward compatibility function for existing code."""
    renderer = TableRenderer(theme_manager)
    renderer.print_table_from_dict(title, data_dict)
