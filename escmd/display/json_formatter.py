"""
JSON formatting utilities for Elasticsearch command-line tool.

This module provides JSON formatting capabilities that handle both terminal
and pipe/redirect scenarios appropriately.
"""

import json
import sys
from typing import Any, Optional


class JSONFormatter:
    """
    Handles JSON formatting with Rich syntax highlighting for terminal output
    and plain JSON for pipe/redirect scenarios.
    """
    
    def __init__(self, theme_manager=None):
        """
        Initialize the JSON formatter.
        
        Args:
            theme_manager: Optional theme manager for styling
        """
        self.theme_manager = theme_manager
    
    def format_json(self, data: Any, indent: int = 2, syntax_theme: str = "monokai") -> None:
        """
        Format and print JSON data with appropriate styling.
        
        Args:
            data: Data to serialize to JSON
            indent: Indentation level for pretty printing (default: 2)
            syntax_theme: Theme for syntax highlighting (default: "monokai")
        """
        if sys.stdout.isatty():
            self._print_formatted_json(data, indent, syntax_theme)
        else:
            self._print_plain_json(data)
    
    def _print_formatted_json(self, data: Any, indent: int, syntax_theme: str) -> None:
        """Print JSON with Rich syntax highlighting for terminal output."""
        try:
            from rich.syntax import Syntax
            from rich.console import Console
            
            json_str = json.dumps(data, indent=indent, ensure_ascii=False)
            syntax = Syntax(json_str, "json", theme=syntax_theme, line_numbers=False)
            
            # Create a fresh console instance to avoid any global state issues
            console = Console(file=sys.stdout, force_terminal=True)
            console.print(syntax)
            
        except ImportError:
            # Fallback to plain JSON if Rich is not available
            self._print_plain_json(data, indent)
    
    def _print_plain_json(self, data: Any, indent: Optional[int] = None) -> None:
        """Print plain JSON for pipe/redirect compatibility."""
        if indent:
            json.dump(data, sys.stdout, indent=indent, ensure_ascii=False)
        else:
            json.dump(data, sys.stdout, separators=(',', ':'), ensure_ascii=False)
        sys.stdout.write('\n')
    
    def to_json_string(self, data: Any, indent: int = 2) -> str:
        """
        Convert data to JSON string.
        
        Args:
            data: Data to serialize
            indent: Indentation level
            
        Returns:
            str: JSON string representation
        """
        return json.dumps(data, indent=indent, ensure_ascii=False)
    
    def to_compact_json_string(self, data: Any) -> str:
        """
        Convert data to compact JSON string (no formatting).
        
        Args:
            data: Data to serialize
            
        Returns:
            str: Compact JSON string representation
        """
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    
    def print_json_as_table(self, json_data: dict, console=None) -> None:
        """
        Prints a JSON object as a pretty table using the rich module.

        Args:
            json_data (dict): Dictionary representing JSON key-value pairs.
            console: Optional console instance to use for printing
        """
        from rich.table import Table
        from rich.console import Console
        
        if console is None:
            console = Console()
            
        table = Table(title="JSON Data", show_header=True, header_style="bold magenta")

        table.add_column("Key", style="cyan", justify="left")
        table.add_column("Value", style="green", justify="left")

        for key, value in json_data.items():
            table.add_row(str(key), str(value))

        console.print(table)


# Convenience function for backward compatibility
def pretty_print_json(data, indent=2):
    """
    Backward compatibility function for existing code.
    
    Args:
        data: Data to serialize to JSON
        indent: Indentation level for pretty printing (default: 2)
    """
    formatter = JSONFormatter()
    formatter.format_json(data, indent)
