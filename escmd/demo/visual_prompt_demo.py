#!/usr/bin/env python3
"""
Visual ESterm Prompt Demo

This script demonstrates the enhanced prompt features with actual colors
displayed in the terminal, showing how the prompts will look when using
ESterm with different themes and configurations.
"""

import sys
import os
import time

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from rich.console import Console
from esterm_modules.themed_terminal_ui import ThemedTerminalUI


class MockClusterManager:
    """Mock cluster manager for demonstration."""

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


def print_colored_header(text, color_code="\033[1;96m"):
    """Print a colored header."""
    reset = "\033[0m"
    print(f"\n{color_code}{'=' * len(text)}{reset}")
    print(f"{color_code}{text}{reset}")
    print(f"{color_code}{'=' * len(text)}{reset}")


def demo_cyberpunk_theme():
    """Demonstrate cyberpunk theme prompts with actual colors."""
    print_colored_header("🔮 CYBERPUNK THEME PROMPTS", "\033[1;95m")

    console = Console()
    ui = ThemedTerminalUI(console)
    ui.set_theme('cyberpunk')

    # Override config for cyberpunk format
    original_config = ui.theme_manager.get_config_value
    def mock_config(key, default):
        config_map = {
            'ui.prompt.format': 'cyberpunk',
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': True,
            'ui.prompt.show_time': True
        }
        return config_map.get(key, original_config(key, default))

    ui.theme_manager.get_config_value = mock_config

    scenarios = [
        ("Healthy Production Cluster", MockClusterManager(True, "production", "green", 5)),
        ("Warning Staging Cluster", MockClusterManager(True, "staging", "yellow", 3)),
        ("Critical Dev Cluster", MockClusterManager(True, "dev", "red", 1)),
        ("Disconnected State", MockClusterManager(False))
    ]

    for desc, cluster in scenarios:
        rich_prompt = ui.get_prompt(cluster)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{desc}:\033[0m")
        print(f"{ansi_prompt}\033[2mstatus\033[0m")

    # Restore config
    ui.theme_manager.get_config_value = original_config


def demo_matrix_theme():
    """Demonstrate matrix theme prompts."""
    print_colored_header("🔋 MATRIX THEME PROMPTS", "\033[1;92m")

    console = Console()
    ui = ThemedTerminalUI(console)
    ui.set_theme('matrix')

    # Override config for matrix format
    original_config = ui.theme_manager.get_config_value
    def mock_config(key, default):
        config_map = {
            'ui.prompt.format': 'matrix',
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': True
        }
        return config_map.get(key, original_config(key, default))

    ui.theme_manager.get_config_value = mock_config

    scenarios = [
        ("Healthy Cluster", MockClusterManager(True, "mainframe", "green", 7)),
        ("Warning Cluster", MockClusterManager(True, "backup", "yellow", 2)),
        ("Critical Cluster", MockClusterManager(True, "emergency", "red", 1)),
        ("Offline", MockClusterManager(False))
    ]

    for desc, cluster in scenarios:
        rich_prompt = ui.get_prompt(cluster)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{desc}:\033[0m")
        print(f"{ansi_prompt}\033[2mget indices\033[0m")

    # Restore config
    ui.theme_manager.get_config_value = original_config


def demo_standard_themes():
    """Demonstrate other themes with enhanced features."""
    themes = [
        ('rich', 'Rich Colors', '\033[1;94m'),
        ('ocean', 'Ocean Blue', '\033[1;36m'),
        ('fire', 'Fire Orange', '\033[1;91m')
    ]

    for theme_name, theme_desc, color_code in themes:
        print_colored_header(f"🎨 {theme_desc.upper()} THEME", color_code)

        console = Console()
        ui = ThemedTerminalUI(console)
        ui.set_theme(theme_name)

        # Test with icons and node count
        original_config = ui.theme_manager.get_config_value
        def mock_config(key, default):
            if 'show_icons' in key:
                return True
            elif 'show_node_count' in key:
                return True
            return original_config(key, default)

        ui.theme_manager.get_config_value = mock_config

        # Show a few key scenarios
        scenarios = [
            ("Connected", MockClusterManager(True, "cluster", "green", 4)),
            ("Warning", MockClusterManager(True, "cluster", "yellow", 2)),
            ("Disconnected", MockClusterManager(False))
        ]

        for desc, cluster in scenarios:
            rich_prompt = ui.get_prompt(cluster)
            ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

            print(f"\n\033[2m{desc}:\033[0m")
            print(f"{ansi_prompt}\033[2mhelp\033[0m")

        # Restore config
        ui.theme_manager.get_config_value = original_config


def demo_configuration_examples():
    """Show how different configurations affect the prompts."""
    print_colored_header("🔩  CONFIGURATION EXAMPLES", "\033[1;93m")

    console = Console()
    ui = ThemedTerminalUI(console)
    ui.set_theme('cyberpunk')

    cluster = MockClusterManager(True, "production", "green", 8)

    configs = [
        ("Minimal Icons Only", {
            'ui.prompt.format': 'esterm',
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': False,
            'ui.prompt.show_time': False
        }),
        ("Full Enhanced", {
            'ui.prompt.format': 'esterm',
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': True,
            'ui.prompt.show_time': True
        }),
        ("Cyberpunk Style", {
            'ui.prompt.format': 'cyberpunk',
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': True,
            'ui.prompt.show_time': True
        })
    ]

    for desc, config in configs:
        original_config = ui.theme_manager.get_config_value
        def mock_config(key, default):
            return config.get(key, original_config(key, default))

        ui.theme_manager.get_config_value = mock_config

        rich_prompt = ui.get_prompt(cluster)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{desc}:\033[0m")
        print(f"{ansi_prompt}\033[2mget health\033[0m")

        # Restore config
        ui.theme_manager.get_config_value = original_config


def show_status_legend():
    """Show the status icon legend."""
    print_colored_header("📋 STATUS ICON LEGEND", "\033[1;97m")

    icons = [
        ("⚡", "Healthy Cluster", "Green status - all systems operational"),
        ("🔶", "Warning State", "Yellow status - attention needed"),
        ("💀", "Critical Issues", "Red status - immediate action required"),
        ("🔌", "Disconnected", "No active cluster connection"),
        ("❓", "Unknown Status", "Status could not be determined")
    ]

    for icon, name, description in icons:
        print(f"\n  {icon} \033[1m{name}\033[0m")
        print(f"     \033[2m{description}\033[0m")


def show_usage_tips():
    """Show usage tips and configuration guidance."""
    print_colored_header("💡 USAGE TIPS", "\033[1;94m")

    tips = [
        "Configuration File: Edit esterm_config.yml to customize your prompts",
        "Theme Switching: Use 'theme <name>' command to switch themes in ESterm",
        "Icon Support: Ensure your terminal supports Unicode for best icon display",
        "Color Support: Works best with terminals that support 256-color mode",
        "Cyberpunk Format: Automatically activates when using cyberpunk theme",
        "Matrix Format: Automatically activates when using matrix theme"
    ]

    for i, tip in enumerate(tips, 1):
        print(f"\n  \033[93m{i}.\033[0m {tip}")

    print(f"\n\033[2mExample configuration:\033[0m")
    print(f"\033[36m")
    print("ui:")
    print("  prompt:")
    print("    format: cyberpunk")
    print("    show_icons: true")
    print("    show_node_count: true")
    print("    show_time: true")
    print(f"\033[0m")


def interactive_demonstration():
    """Interactive demonstration allowing user to see live prompts."""
    print_colored_header("🎮 INTERACTIVE DEMO", "\033[1;91m")

    print("\033[2mThis shows you exactly how prompts look when typing commands.\033[0m")
    print("\033[2mPress Enter after each prompt to continue, or Ctrl+C to skip.\033[0m")

    console = Console()
    ui = ThemedTerminalUI(console)

    demos = [
        ('cyberpunk', 'cyberpunk', MockClusterManager(True, "production", "green", 5)),
        ('matrix', 'matrix', MockClusterManager(True, "mainframe", "green", 7)),
        ('cyberpunk', 'cyberpunk', MockClusterManager(False))
    ]

    for theme, format_type, cluster in demos:
        ui.set_theme(theme)

        original_config = ui.theme_manager.get_config_value
        def mock_config(key, default):
            config_map = {
                'ui.prompt.format': format_type,
                'ui.prompt.show_icons': True,
                'ui.prompt.show_node_count': True,
                'ui.prompt.show_time': True
            }
            return config_map.get(key, original_config(key, default))

        ui.theme_manager.get_config_value = mock_config

        rich_prompt = ui.get_prompt(cluster)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        state = "connected" if cluster.is_connected() else "disconnected"
        print(f"\n\033[2m{theme.title()} theme ({state}):\033[0m")

        try:
            user_input = input(ansi_prompt)
            if user_input.strip():
                print(f"\033[2mYou typed: {user_input}\033[0m")
        except (KeyboardInterrupt, EOFError):
            print("\n\033[2mSkipping interactive demo...\033[0m")
            break

        # Restore config
        ui.theme_manager.get_config_value = original_config


def main():
    """Run the complete visual demonstration."""
    # Print banner
    print("\033[2J\033[H")  # Clear screen and move cursor to top
    print("\033[1;96m" + "=" * 70 + "\033[0m")
    print("\033[1;96m" + "ESterm Enhanced Prompts - Visual Demo".center(70) + "\033[0m")
    print("\033[1;96m" + "=" * 70 + "\033[0m")
    print("\033[2mThis demo shows the new enhanced prompts with actual colors\033[0m")

    try:
        # Run all demonstrations
        demo_cyberpunk_theme()
        demo_matrix_theme()
        demo_standard_themes()
        demo_configuration_examples()
        show_status_legend()
        show_usage_tips()

        # Ask about interactive demo
        print(f"\n\033[93mWould you like to try the interactive demo? (y/n): \033[0m", end="")
        try:
            response = input()
            if response.lower().startswith('y'):
                interactive_demonstration()
        except (KeyboardInterrupt, EOFError):
            print("\n\033[2mSkipping interactive demo.\033[0m")

        # Final message
        print_colored_header("✨ DEMO COMPLETE", "\033[1;92m")
        print("\033[2mThe enhanced prompts are ready to use in your ESterm session!")
        print("Edit esterm_config.yml to customize your prompt preferences.\033[0m")

    except KeyboardInterrupt:
        print("\n\n\033[93mDemo interrupted. Enhanced prompts are still available!\033[0m")
    except Exception as e:
        print(f"\n\033[91mDemo error: {e}\033[0m")
        import traceback
        print(f"\033[2m{traceback.format_exc()}\033[0m")


if __name__ == "__main__":
    main()
