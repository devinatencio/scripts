"""
Progress display utilities for Elasticsearch command-line tool.

This module provides progress bar and status display capabilities using Rich,
with theme integration for consistent visual presentation.
"""

from typing import Optional, Union
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.console import Console


class ProgressDisplay:
    """
    Handles progress bars and status displays with theme integration.
    
    Provides both static progress bars and interactive progress tracking
    for long-running operations.
    """
    
    def __init__(self, theme_manager=None, console=None):
        """
        Initialize the progress display.
        
        Args:
            theme_manager: Theme manager for styling
            console: Rich console instance
        """
        self.theme_manager = theme_manager
        self.console = console or Console()
    
    def show_progress_static(self, completion: Union[int, float], bar_width: int = 20) -> Progress:
        """
        Display a static progress bar with the given completion percentage.
        
        Uses theme-aware colors for the progress bar.
        
        Args:
            completion: Completion percentage (0 to 100)
            bar_width: Width of the progress bar
            
        Returns:
            Progress: Rich Progress object for rendering
        """
        # Determine theme-aware colors based on completion
        if completion >= 100:
            bar_color = self._get_themed_style('state_styles', 'success', 'green')
        elif completion >= 75:
            bar_color = self._get_themed_style('state_styles', 'warning', 'yellow')
        else:
            bar_color = self._get_themed_style('state_styles', 'error', 'red')
            
        unfinished_color = self._get_themed_style('state_styles', 'muted', 'white')
        
        # Create the progress bar components with custom width and theme colors
        progress = Progress(
            TextColumn(""),
            BarColumn(bar_width=bar_width, style=unfinished_color, complete_style=bar_color),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
        
        # Manually set up the progress bar without starting it
        task = progress.add_task("", total=100, completed=completion)
        
        return progress
    
    def create_text_progress_bar(self, percent: Union[int, float], width: int = 10) -> str:
        """
        Create a simple text-based progress bar with theme-aware styling.
        
        Args:
            percent: Completion percentage (0 to 100)
            width: Width of the progress bar in characters
            
        Returns:
            str: Text progress bar string with Rich markup
        """
        multiply_percent = int(percent)
        filled_width = int(width * multiply_percent / 100)
        empty_width = width - filled_width
        
        # Get theme-aware colors
        if self.theme_manager:
            filled_style = self._get_themed_style('state_styles', 'success', 'green')
            empty_style = self._get_themed_style('state_styles', 'muted', 'dim')
        else:
            filled_style = 'green'
            empty_style = 'dim'
        
        # Create Rich-formatted progress bar
        bar = f"[{filled_style}]{'█' * filled_width}[/{filled_style}][{empty_style}]{'░' * empty_width}[/{empty_style}]"
        return f"{bar} {percent:.2f}%"
    
    def create_recovery_progress(self, progress_dict: dict) -> Progress:
        """
        Create a progress display for recovery operations.
        
        Args:
            progress_dict: Dictionary containing progress information
            
        Returns:
            Progress: Rich Progress object for recovery display
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
        
        return progress
    
    def format_percentage_with_progress(self, 
                                      percent: Union[int, float], 
                                      show_bar: bool = True, 
                                      bar_width: int = 10) -> str:
        """
        Format a percentage value with optional progress bar.
        
        Args:
            percent: Percentage value
            show_bar: Whether to include a text progress bar
            bar_width: Width of the progress bar
            
        Returns:
            str: Formatted percentage string with optional progress bar
        """
        if show_bar:
            return self.create_text_progress_bar(percent, bar_width)
        else:
            return f"{percent:.2f}%"
    
    def create_status_indicator(self, status: str, percentage: Optional[float] = None) -> str:
        """
        Create a status indicator with optional percentage.
        
        Args:
            status: Status string
            percentage: Optional percentage value
            
        Returns:
            str: Formatted status indicator
        """
        # Get themed colors for different statuses
        status_colors = {
            'complete': 'green',
            'in_progress': 'yellow',
            'failed': 'red',
            'pending': 'blue',
            'unknown': 'white'
        }
        
        color = status_colors.get(status.lower(), 'white')
        
        if percentage is not None:
            return f"[{color}]{status} ({percentage:.1f}%)[/{color}]"
        else:
            return f"[{color}]{status}[/{color}]"
    
    def create_recovery_status_display(self, 
                                     stage: str, 
                                     percent: Optional[float] = None,
                                     bytes_recovered: Optional[int] = None,
                                     total_bytes: Optional[int] = None) -> str:
        """
        Create a formatted display for recovery status.
        
        Args:
            stage: Recovery stage
            percent: Completion percentage
            bytes_recovered: Bytes recovered so far
            total_bytes: Total bytes to recover
            
        Returns:
            str: Formatted recovery status display
        """
        # Map recovery stages to colors
        stage_colors = {
            'done': 'green',
            'index': 'blue',
            'start': 'yellow',
            'translog': 'cyan',
            'finalize': 'magenta',
            'init': 'white'
        }
        
        color = stage_colors.get(stage.lower(), 'white')
        
        if percent is not None:
            if percent == 100.0:
                return f"[green]✅ {stage.upper()} (100%)[/green]"
            else:
                progress_bar = self.create_text_progress_bar(percent, 8)
                return f"[{color}]{stage.upper()}[/{color}] {progress_bar}"
        else:
            return f"[{color}]{stage.upper()}[/{color}]"
    
    def _get_themed_style(self, category: str, style_type: str, default: str = 'white') -> str:
        """Get themed style, with fallback if theme manager not available."""
        if self.theme_manager:
            return self.theme_manager.get_themed_style(category, style_type, default)
        return default


# Backward compatibility functions
def show_progress_static(completion, bar_width=20):
    """Backward compatibility function for existing code."""
    progress_display = ProgressDisplay()
    return progress_display.show_progress_static(completion, bar_width)


def text_progress_bar(percent, width=10):
    """Backward compatibility function for existing code."""
    progress_display = ProgressDisplay()
    return progress_display.create_text_progress_bar(percent, width)
