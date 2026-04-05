#!/usr/bin/env python3
"""
Interactive Terminal for ESCMD - Elasticsearch Command Line Tool
Provides a persistent terminal session with loaded cluster context.

This is the main entry point that creates and runs a TerminalSession
using the modular esterm_modules package.
"""

import sys
import os
import importlib.metadata

# Check for minimum rich version before any other imports
def _check_rich_version():
    MIN_RICH = (14, 3, 3)
    try:
        raw = importlib.metadata.version("rich")
        parts = tuple(int(x) for x in raw.split(".")[:3])
        if parts >= MIN_RICH:
            return
    except Exception:
        raw = "not found"
        parts = (0, 0, 0)

    try:
        from rich.console import Console
        from rich.panel import Panel
        Console().print(Panel(
            f"Installed: [yellow]rich {raw}[/yellow]\n"
            f"Required:  [green]rich {'.'.join(str(x) for x in MIN_RICH)}+[/green]\n\n"
            "Upgrade with:\n\n  [bold cyan]pip install --upgrade rich[/bold cyan]",
            title="[bold red] Dependency Error[/bold red]",
            border_style="red",
        ))
    except Exception:
        print(f"ERROR: rich {'.'.join(str(x) for x in MIN_RICH)}+ is required "
              f"(found: {raw}). Run: pip install --upgrade rich")
    sys.exit(1)

_check_rich_version()

# Add the current directory to the Python path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from esterm_modules import TerminalSession

# Version information — single source of truth is version.py
from version import VERSION, DATE


def main():
    """Main entry point for ESterm interactive terminal."""
    try:
        # Create and run the terminal session
        session = TerminalSession(version=VERSION, date=DATE)
        session.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
