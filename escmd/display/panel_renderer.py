"""
Panel rendering utilities for Elasticsearch command-line tool.

This module provides panel creation and styling capabilities using Rich,
with integrated theme support for consistent visual presentation.
"""

from typing import Any, Optional, Union
from rich.panel import Panel
from rich.text import Text
from rich.console import Console


class PanelRenderer:
    """
    Handles panel creation and styling with theme integration.
    
    Provides methods for creating consistently styled panels and message boxes
    across the application.
    """
    
    def __init__(self, theme_manager=None, console=None):
        """
        Initialize the panel renderer.
        
        Args:
            theme_manager: Theme manager for styling
            console: Rich console instance
        """
        self.theme_manager = theme_manager
        self.console = console or Console()
        self._default_border_style = 'white'
    
    def create_themed_panel(self, 
                          content: Any, 
                          title: Optional[str] = None, 
                          subtitle: Optional[str] = None, 
                          title_style: str = 'title', 
                          border_style: Optional[str] = None, 
                          **kwargs) -> Panel:
        """
        Create a themed panel with consistent styling.
        
        Args:
            content: Panel content
            title: Panel title
            subtitle: Panel subtitle  
            title_style: Style type for title ('title', 'success', 'error', etc.)
            border_style: Override border style
            **kwargs: Additional Panel arguments
            
        Returns:
            Panel: Themed Rich panel
        """
        # Use theme-based border style if not overridden
        if border_style is None:
            border_style = self._get_border_style()
            
        # Apply theme to title if it's a string
        if title and isinstance(title, str):
            title_color = self._get_themed_style('panel_styles', title_style, 'bold white')
            title = f"[{title_color}]{title}[/{title_color}]"
            
        return Panel(content, title=title, subtitle=subtitle, border_style=border_style, **kwargs)
    
    # Map raw color names to semantic style keys so callers that pass
    # panel_style="red" or border_style="green" get theme-appropriate colors.
    _COLOR_TO_SEMANTIC = {
        "red": "error",
        "bold red": "error",
        "bright_red": "error",
        "green": "success",
        "bold green": "success",
        "bright_green": "success",
        "dim green": "success",
        "yellow": "warning",
        "bold yellow": "warning",
        "bright_yellow": "warning",
        "blue": "info",
        "bold blue": "info",
        "bright_blue": "info",
        "cyan": "info",
        "bold cyan": "info",
        "magenta": "secondary",
        "bold magenta": "secondary",
    }

    def _resolve_semantic_color(self, raw_color: str) -> str:
        """Resolve a raw color name to a theme-aware semantic color.
        
        If the raw color maps to a known semantic role (e.g. 'red' → 'error'),
        the theme's semantic style is returned. Otherwise the raw color is
        returned unchanged so explicit/unusual colors still work.
        """
        semantic_key = self._COLOR_TO_SEMANTIC.get(raw_color)
        if semantic_key:
            return self._get_themed_style('semantic_styles', semantic_key, raw_color)
        return raw_color

    def show_message_box(self, 
                        title: str, 
                        message: str, 
                        message_style: str = "bold white", 
                        panel_style: str = "white", 
                        border_style: Optional[str] = None, 
                        width: Optional[int] = None, 
                        theme_style: Optional[str] = None) -> None:
        """
        Display a message in a formatted box with theme support.
        
        Args:
            title: The title of the message box
            message: The message to display
            message_style: The style for the message text
            panel_style: The style for the panel background (for compatibility)
            border_style: The border style/color (overrides panel_style if provided)
            width: Panel width (auto-sizing if None)
            theme_style: Theme style type ('success', 'error', 'warning', 'info')
        """
        # Apply theme-based styling if theme_style is provided
        if theme_style:
            theme_color = self._get_themed_style('panel_styles', theme_style, panel_style)
            if theme_color:
                message_style = theme_color
                border_style = self._get_border_style()

        # Resolve message_style through the theme when it's a known color
        message_style = self._resolve_message_style(message_style)

        # Handle backward compatibility: convert panel_style to border_style if needed
        if border_style is None:
            border_style = self._resolve_semantic_color(panel_style) if panel_style else self._get_border_style()
            if panel_style == "white on blue":
                border_style = self._resolve_semantic_color("blue")
            elif panel_style == "white":
                border_style = self._get_border_style()
        else:
            border_style = self._resolve_semantic_color(border_style)
        
        message_text = Text(f"{message}", style=message_style, justify="center")
        
        # Apply themed title styling
        title_style_color = self._get_themed_style('panel_styles', 'title', 'bold white')
        title = f"[{title_style_color}]{title}[/{title_style_color}]"
        
        panel_kwargs = {
            "title": title,
            "border_style": border_style,
            "padding": (1, 2)
        }
        
        if width:
            panel_kwargs["width"] = width
        
        panel = Panel(message_text, **panel_kwargs)
        self.console.print()
        self.console.print(panel, markup=True)

    def _resolve_message_style(self, style: str) -> str:
        """Resolve message_style, preserving 'bold' prefix with themed color."""
        if style.startswith("bold "):
            base = style[5:]  # strip 'bold '
            semantic_key = self._COLOR_TO_SEMANTIC.get(base)
            if semantic_key:
                themed = self._get_themed_style('semantic_styles', semantic_key, base)
                return f"bold {themed}"
        else:
            semantic_key = self._COLOR_TO_SEMANTIC.get(style)
            if semantic_key:
                return self._get_themed_style('semantic_styles', semantic_key, style)
        return style
    
    def create_status_panel(self, 
                          content: Any, 
                          status: str, 
                          title: Optional[str] = None, 
                          **kwargs) -> Panel:
        """
        Create a panel with status-based styling.
        
        Args:
            content: Panel content
            status: Status type ('success', 'error', 'warning', 'info')
            title: Panel title
            **kwargs: Additional Panel arguments
            
        Returns:
            Panel: Status-styled Rich panel
        """
        # Map status to semantic theme colors with hardcoded fallbacks
        fallback_colors = {
            'success': 'green',
            'error': 'red',
            'warning': 'yellow',
            'info': 'blue',
            'secondary': 'magenta'
        }
        
        fallback = fallback_colors.get(status, 'white')
        border_style = self._get_themed_style('semantic_styles', status, fallback)
        title_style = status
        
        return self.create_themed_panel(
            content, 
            title=title, 
            title_style=title_style, 
            border_style=border_style, 
            **kwargs
        )
    
    def create_info_panel(self, content: Any, title: str = "Information", **kwargs) -> Panel:
        """Create an information panel."""
        return self.create_status_panel(content, 'info', title, **kwargs)
    
    def create_success_panel(self, content: Any, title: str = "Success", **kwargs) -> Panel:
        """Create a success panel."""
        return self.create_status_panel(content, 'success', title, **kwargs)
    
    def create_error_panel(self, content: Any, title: str = "Error", **kwargs) -> Panel:
        """Create an error panel."""
        return self.create_status_panel(content, 'error', title, **kwargs)
    
    def create_warning_panel(self, content: Any, title: str = "Warning", **kwargs) -> Panel:
        """Create a warning panel."""
        return self.create_status_panel(content, 'warning', title, **kwargs)
    
    def _get_themed_style(self, category: str, style_type: str, default: str = 'white') -> str:
        """Get themed style, with fallback if theme manager not available."""
        if self.theme_manager:
            return self.theme_manager.get_themed_style(category, style_type, default)
        return default
    
    def _get_border_style(self) -> str:
        """Get the default border style from theme or fallback."""
        if self.theme_manager:
            theme_styles = self.theme_manager.get_theme_styles()
            return theme_styles.get('border_style', self._default_border_style)
        return self._default_border_style
