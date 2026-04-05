"""
Base command class for esclient command extraction.

This module provides a foundation for extracting command processing logic
from the monolithic ElasticsearchClient class into focused, testable modules.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from rich.console import Console


class BaseCommand(ABC):
    """
    Abstract base class for all commands extracted from ElasticsearchClient.
    
    This class provides a common interface and shared functionality for command processors.
    Each command class handles a specific set of related operations (e.g., indices, nodes, cluster).
    """
    
    def __init__(self, es_client, console: Console = None):
        """
        Initialize the base command with Elasticsearch client.
        
        Args:
            es_client: The ElasticsearchClient instance
            console: Rich console for output (optional)
        """
        self.es_client = es_client
        self.console = console or Console()
        
        # Initialize styling systems if available
        self.theme_manager = getattr(es_client, 'theme_manager', None)
        self.style_system = None
        
        if self.theme_manager:
            try:
                from display.style_system import StyleSystem
                self.style_system = StyleSystem(self.theme_manager)
            except ImportError:
                # Fallback if StyleSystem not available
                pass
        
    @abstractmethod
    def get_command_group(self) -> str:
        """
        Get the command group name (e.g., 'indices', 'nodes', 'cluster').
        
        Returns:
            str: The command group identifier
        """
        pass
    
    def _format_json_output(self, data: Dict[str, Any]) -> str:
        """
        Format data for JSON output using the client's JSON formatter.
        
        Args:
            data: Data to format
            
        Returns:
            str: Formatted JSON string
        """
        return self.es_client.json_formatter.format_json(data)
    
    def _create_themed_panel(self, content, title: str = None, **kwargs):
        """
        Create a themed panel using the client's panel renderer.
        
        Args:
            content: Panel content
            title: Panel title
            **kwargs: Additional panel arguments
            
        Returns:
            Rich panel object
        """
        return self.es_client.panel_renderer.create_themed_panel(
            content, title=title, **kwargs
        )
    
    def _create_themed_table(self, title: str = None, **kwargs):
        """
        Create a themed table using the client's table renderer.
        
        Args:
            title: Table title
            **kwargs: Additional table arguments
            
        Returns:
            Rich table object
        """
        return self.es_client.table_renderer.create_basic_table(
            title=title, **kwargs
        )
    
    def _show_progress(self, description: str, total: int = None):
        """
        Show progress indicator using the client's progress display.
        
        Args:
            description: Progress description
            total: Total steps (optional)
            
        Returns:
            Progress context manager
        """
        return self.es_client.progress_display.show_progress_static(
            description, total
        )
    
    def _get_themed_style(self, category: str, style_type: str, default: str = 'white') -> str:
        """
        Get themed style from the client's theme manager.
        
        Args:
            category: Style category
            style_type: Specific style type
            default: Default style if not found
            
        Returns:
            str: Style string
        """
        return self.es_client.theme_manager.get_themed_style(
            category, style_type, default
        )


class CommandRegistry:
    """
    Registry for managing command instances and delegation.
    
    This class helps coordinate between the main ElasticsearchClient and
    the extracted command processors.
    """
    
    def __init__(self, es_client):
        """
        Initialize the command registry.
        
        Args:
            es_client: The main ElasticsearchClient instance
        """
        self.es_client = es_client
        self.commands: Dict[str, BaseCommand] = {}
    
    def register_command(self, command: BaseCommand):
        """
        Register a command processor.
        
        Args:
            command: Command instance to register
        """
        group = command.get_command_group()
        self.commands[group] = command
    
    def get_command(self, group: str) -> Optional[BaseCommand]:
        """
        Get a command processor by group name.
        
        Args:
            group: Command group name
            
        Returns:
            BaseCommand instance or None if not found
        """
        return self.commands.get(group)
    
    def delegate_method(self, group: str, method_name: str, *args, **kwargs) -> Any:
        """
        Delegate a method call to the appropriate command processor.
        
        Args:
            group: Command group name
            method_name: Method to call
            *args: Method arguments
            **kwargs: Method keyword arguments
            
        Returns:
            Method result
            
        Raises:
            AttributeError: If command group or method not found
        """
        command = self.get_command(group)
        if not command:
            raise AttributeError(f"Command group '{group}' not found")
        
        if not hasattr(command, method_name):
            raise AttributeError(f"Method '{method_name}' not found in {group} command")
        
        method = getattr(command, method_name)
        return method(*args, **kwargs)


# Backward compatibility functions
def create_command_registry(es_client) -> CommandRegistry:
    """Create and initialize a command registry for backward compatibility."""
    return CommandRegistry(es_client)
