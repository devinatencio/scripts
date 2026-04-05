#!/usr/bin/env python3
"""
ESterm Prompt Enhancement Demo

This script demonstrates the new enhanced prompt features including:
- Status icons for cluster health
- Enhanced cyberpunk and matrix themed prompts
- Time display options
- Node count display
- Various prompt formats

Run this demo to see how the new prompt system works.
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from rich.console import Console
from esterm_modules.theme_manager import EstermThemeManager
from esterm_modules.themed_terminal_ui import ThemedTerminalUI


class MockClusterManager:
    """Mock cluster manager for demonstration purposes."""

    def __init__(self, connected=True, cluster_name="production", status="green", node_count=5):
        self.connected = connected
        self.cluster_name = cluster_name
        self.status = status
        self.node_count = node_count

    def is_connected(self):
        return self.connected

    def get_current_cluster(self):
        return self.cluster_name if self.connected else None

    def get_cluster_info(self):
        if not self.connected:
            return None
        return {
            'status': self.status,
            'number_of_nodes': self.node_count
        }


def demo_prompt_enhancements():
    """Demonstrate the enhanced prompt features."""
    console = Console()

    # Print demo header
    console.print("\n" + "=" * 70)
    console.print("[bold bright_magenta]ESterm Prompt Enhancement Demo[/bold bright_magenta]", justify="center")
    console.print("=" * 70 + "\n")

    # Available themes for demo
    themes_to_demo = ['rich', 'cyberpunk', 'matrix', 'ocean', 'fire']

    for theme_name in themes_to_demo:
        console.print(f"\n[bold cyan]Theme: {theme_name.upper()}[/bold cyan]")
        console.print("-" * 50)

        # Create themed UI
        terminal_ui = ThemedTerminalUI(console)
        terminal_ui.set_theme(theme_name)

        # Demo different scenarios
        scenarios = [
            ("Healthy Cluster", MockClusterManager(True, "production", "green", 5)),
            ("Warning Cluster", MockClusterManager(True, "staging", "yellow", 3)),
            ("Critical Cluster", MockClusterManager(True, "dev", "red", 1)),
            ("Disconnected", MockClusterManager(False))
        ]

        for scenario_name, mock_cluster in scenarios:
            console.print(f"\n  [dim]{scenario_name}:[/dim]")

            # Test different prompt formats
            formats = ['esterm', 'simple']

            # Add theme-specific formats
            if theme_name == 'cyberpunk':
                formats.append('cyberpunk')
            elif theme_name == 'matrix':
                formats.append('matrix')

            for format_type in formats:
                # Temporarily set format
                original_config = terminal_ui.theme_manager.get_config_value('ui.prompt.format', 'esterm')
                terminal_ui.theme_manager.get_config_value = lambda key, default: format_type if key == 'ui.prompt.format' else (
                    True if 'show_icons' in key else (
                        True if 'show_node_count' in key else (
                            True if 'show_time' in key and theme_name == 'cyberpunk' else default
                        )
                    )
                )

                prompt = terminal_ui.get_prompt(mock_cluster)
                console.print(f"    [{format_type:>10}] {prompt}", end="")
                console.print("[dim]your_command_here[/dim]")


def demo_configuration_options():
    """Demonstrate configuration options for prompts."""
    console = Console()

    console.print("\n" + "=" * 70)
    console.print("[bold bright_cyan]Configuration Options Demo[/bold bright_cyan]", justify="center")
    console.print("=" * 70)

    console.print("\n[bold]Available Configuration Options:[/bold]")

    config_options = [
        ("ui.prompt.format", "esterm/simple/minimal/cyberpunk/matrix", "Prompt format style"),
        ("ui.prompt.show_status_colors", "true/false", "Color-code cluster status"),
        ("ui.prompt.show_icons", "true/false", "Show status icons (⚡🔶💀🔌)"),
        ("ui.prompt.show_node_count", "true/false", "Display cluster node count"),
        ("ui.prompt.show_time", "true/false", "Show current time in prompt"),
    ]

    for option, values, description in config_options:
        console.print(f"  [cyan]{option:<30}[/cyan] [yellow]{values:<25}[/yellow] {description}")

    console.print("\n[bold]Example Enhanced Prompts:[/bold]")

    examples = [
        ("Cyberpunk Theme", "⚡ esterm >> [production:5] :: 14:32:45 >> "),
        ("Matrix Theme", "⚡ esterm@[production:5] $ "),
        ("Standard Enhanced", "⚡ esterm(production:5) 14:32:45> "),
        ("Simple with Icons", "⚡ production> "),
        ("Disconnected Cyberpunk", "🔌 esterm >> <OFFLINE> :: 14:32:45 >> ")
    ]

    for name, example in examples:
        console.print(f"  [dim]{name}:[/dim] {example}[dim]your_command[/dim]")


def demo_theme_specific_features():
    """Demonstrate theme-specific prompt features."""
    console = Console()

    console.print("\n" + "=" * 70)
    console.print("[bold bright_green]Theme-Specific Features[/bold bright_green]", justify="center")
    console.print("=" * 70)

    features = {
        "cyberpunk": [
            "Neon-style separators (>>)",
            "Electric color scheme",
            "Time display with :: separator",
            "Offline state with <OFFLINE> indicator",
            "Status icons with enhanced visibility"
        ],
        "matrix": [
            "Terminal-style @ separator",
            "Green monochrome scheme",
            "Unix-like $ prompt ending",
            "Bracket-enclosed time display",
            "Classic hacker aesthetic"
        ],
        "ocean": [
            "Sea-inspired color palette",
            "Calm, professional appearance",
            "Subtle status indicators",
            "Blue-themed separators"
        ]
    }

    for theme, feature_list in features.items():
        console.print(f"\n[bold]{theme.upper()} Theme:[/bold]")
        for feature in feature_list:
            console.print(f"  • {feature}")


def show_usage_instructions():
    """Show instructions for using the new prompt features."""
    console = Console()

    console.print("\n" + "=" * 70)
    console.print("[bold bright_yellow]Usage Instructions[/bold bright_yellow]", justify="center")
    console.print("=" * 70)

    console.print("\n[bold]To enable enhanced prompts in your esterm_config.yml:[/bold]")

    yaml_config = """
ui:
  prompt:
    format: cyberpunk              # or matrix, esterm, simple, minimal
    show_status_colors: true       # Color-code cluster health
    show_icons: true               # Show status icons
    show_node_count: true          # Display cluster node count
    show_time: true                # Show current time
    enhanced_formats:
      cyberpunk: true              # Enable cyberpunk format
      matrix: true                 # Enable matrix format
"""

    console.print(f"[dim]{yaml_config.strip()}[/dim]")

    console.print("\n[bold]Commands to try:[/bold]")
    commands = [
        "theme cyberpunk    # Switch to cyberpunk theme",
        "theme matrix       # Switch to matrix theme  ",
        "status            # View cluster status with enhanced display",
        "help themes       # Get help on theme system"
    ]

    for command in commands:
        console.print(f"  [green]{command}[/green]")


def main():
    """Main demo function."""
    console = Console()

    try:
        # Show the main demo
        demo_prompt_enhancements()
        demo_configuration_options()
        demo_theme_specific_features()
        show_usage_instructions()

        console.print("\n" + "=" * 70)
        console.print("[bold bright_magenta]Demo Complete![/bold bright_magenta]", justify="center")
        console.print("[dim]Try these enhancements in your esterm session![/dim]", justify="center")
        console.print("=" * 70 + "\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted.[/yellow]")
    except Exception as e:
        console.print(f"[red]Demo error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


if __name__ == "__main__":
    main()
