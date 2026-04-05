#!/usr/bin/env python3
"""
ESterm Theme Demo Script

This script demonstrates and tests the new ESterm theme system.
It showcases all themes with sample UI elements to verify everything works correctly.
"""

import sys
import os
from rich.console import Console

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from esterm_modules.theme_manager import EstermThemeManager
from esterm_modules.themed_terminal_ui import ThemedTerminalUI


class MockClusterManager:
    """Mock cluster manager for demo purposes."""

    def __init__(self, connected=True, status='green'):
        self._connected = connected
        self._status = status
        self._cluster_name = 'demo-cluster'

    def is_connected(self):
        return self._connected

    def get_current_cluster(self):
        return self._cluster_name if self._connected else None

    def get_cluster_info(self):
        if self._connected:
            return {
                'name': self._cluster_name,
                'status': self._status,
                'nodes': 5,
                'data_nodes': 3,
                'active_shards': 25,
                'cluster_name': 'Production Elasticsearch Cluster'
            }
        return None

    def get_available_clusters(self):
        return ['prod-cluster', 'staging-cluster', 'dev-cluster', 'test-cluster']


def demo_theme(theme_name: str, ui: ThemedTerminalUI, cluster_manager: MockClusterManager):
    """Demonstrate a specific theme with various UI elements."""
    console = ui.console

    # Switch to the theme
    success = ui.set_theme(theme_name)
    if not success:
        console.print(f"[red]Failed to set theme: {theme_name}[/red]")
        return

    console.print(f"\n{'='*60}")
    console.print(f"DEMONSTRATING THEME: {theme_name.upper()}")
    console.print(f"{'='*60}")

    # Banner demo
    console.print("\n1. BANNER DEMO:")
    ui.show_banner("3.0.1", "2025-01-15")

    # Status demo
    console.print("\n2. STATUS DEMO:")
    ui.show_status(cluster_manager)

    # Messages demo
    console.print("\n3. MESSAGES DEMO:")
    ui.show_success("Operation completed successfully!")
    ui.show_warning("This is a warning message")
    ui.show_error("This is an error message")
    ui.show_info("This is an informational message")

    # Prompt demo
    console.print("\n4. PROMPT DEMO:")
    prompt_connected = ui.get_prompt(cluster_manager)
    console.print(f"Connected prompt: {prompt_connected}")

    # Test with disconnected cluster
    cluster_manager._connected = False
    prompt_disconnected = ui.get_prompt(cluster_manager)
    console.print(f"Disconnected prompt: {prompt_disconnected}")

    # Test with warning status
    cluster_manager._connected = True
    cluster_manager._status = 'yellow'
    prompt_warning = ui.get_prompt(cluster_manager)
    console.print(f"Warning status prompt: {prompt_warning}")

    # Reset for next demo
    cluster_manager._connected = True
    cluster_manager._status = 'green'

    # Help demo (partial)
    console.print("\n5. HELP DEMO (partial):")
    from rich.text import Text
    help_text = Text()
    help_styles = ui.theme_manager.get_help_styles()

    help_text.append("Sample Help Content:\n", style=help_styles.get('title_style', 'bold'))
    help_text.append("Commands:\n", style=help_styles.get('section_header_style', 'bold'))
    help_text.append("  health", style=help_styles.get('command_style', 'bold'))
    help_text.append(" - Show cluster health\n", style=help_styles.get('description_style', 'white'))
    help_text.append("  Example: ", style=help_styles.get('description_style', 'white'))
    help_text.append("esterm> health", style=help_styles.get('example_style', 'cyan'))

    from rich.panel import Panel
    panel = Panel(
        help_text,
        title="Help Sample",
        border_style=ui.theme_manager.get_style('panels', 'border_style'),
        title_style=ui.theme_manager.get_style('panels', 'title_style'),
        padding=(1, 2)
    )
    console.print(panel)

    # Progress demo
    console.print("\n6. PROGRESS DEMO:")
    ui.show_progress("Loading cluster information")

    console.print(f"\n{'-'*60}")
    console.print(f"END OF {theme_name.upper()} THEME DEMO")
    console.print(f"{'-'*60}\n")


def main():
    """Main demo function."""
    console = Console()

    console.print("[bold blue]ESterm Theme System Demo[/bold blue]")
    console.print("[dim]Testing the new independent theme system for ESterm[/dim]\n")

    # Initialize components
    ui = ThemedTerminalUI(console)
    cluster_manager = MockClusterManager()

    # Show available themes
    console.print("[bold yellow]Available Themes:[/bold yellow]")
    ui.list_themes()

    # Test theme previews
    console.print("\n[bold yellow]Theme Previews:[/bold yellow]")
    available_themes = ui.theme_manager.get_available_themes()

    for theme_name in available_themes[:3]:  # Show first 3 previews
        ui.preview_theme(theme_name)

    # Interactive mode
    try:
        while True:
            console.print("\n[bold cyan]Demo Options:[/bold cyan]")
            console.print("1. Demo all themes")
            console.print("2. Demo specific theme")
            console.print("3. Show theme list")
            console.print("4. Preview theme")
            console.print("5. Exit")

            try:
                choice = input("\nEnter choice (1-5): ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if choice == '1':
                # Demo all themes
                for theme_name in available_themes:
                    demo_theme(theme_name, ui, cluster_manager)

                    try:
                        input("\nPress Enter to continue to next theme (or Ctrl+C to stop)...")
                    except (KeyboardInterrupt, EOFError):
                        break

            elif choice == '2':
                # Demo specific theme
                theme_name = input("Enter theme name: ").strip()
                if theme_name in available_themes:
                    demo_theme(theme_name, ui, cluster_manager)
                else:
                    console.print(f"[red]Theme '{theme_name}' not found[/red]")

            elif choice == '3':
                # Show theme list
                ui.list_themes()

            elif choice == '4':
                # Preview theme
                theme_name = input("Enter theme name to preview: ").strip()
                ui.preview_theme(theme_name)

            elif choice == '5':
                break

            else:
                console.print("[red]Invalid choice[/red]")

    except KeyboardInterrupt:
        pass

    console.print("\n[yellow]Demo completed![/yellow]")


if __name__ == '__main__':
    main()
