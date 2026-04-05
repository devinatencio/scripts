#!/usr/bin/env python3
"""
ESterm Connection-Based Prompt Demo

This script demonstrates the enhanced prompt features focused on connection
status rather than potentially stale cluster health information.

Features demonstrated:
- Connection status indicators (connected/disconnected)
- Theme-specific prompt formats
- Node count display
- Time display options
- Visual enhancements without misleading health data
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

    def __init__(self, connected=True, cluster_name="production", node_count=5):
        self.connected = connected
        self.cluster_name = cluster_name
        self.node_count = node_count

    def is_connected(self):
        return self.connected

    def get_current_cluster(self):
        return self.cluster_name if self.connected else None

    def get_cluster_info(self):
        if not self.connected:
            return None
        return {
            'number_of_nodes': self.node_count
        }


def print_colored_header(text, color_code="\033[1;96m"):
    """Print a colored header."""
    reset = "\033[0m"
    print(f"\n{color_code}{'=' * len(text)}{reset}")
    print(f"{color_code}{text}{reset}")
    print(f"{color_code}{'=' * len(text)}{reset}")


def demo_cyberpunk_theme():
    """Demonstrate cyberpunk theme prompts."""
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
        ("Connected to Production Cluster", MockClusterManager(True, "production", 5)),
        ("Connected to Staging Cluster", MockClusterManager(True, "staging", 3)),
        ("Connected to Development Cluster", MockClusterManager(True, "dev", 1)),
        ("Disconnected State", MockClusterManager(False))
    ]

    print("\033[2mConnection-based prompts (no health status):\033[0m")

    for desc, cluster in scenarios:
        rich_prompt = ui.get_prompt(cluster)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{desc}:\033[0m")
        print(f"{ansi_prompt}\033[2mget cluster stats\033[0m")

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
        ("Connected to Mainframe", MockClusterManager(True, "mainframe", 7)),
        ("Connected to Backup System", MockClusterManager(True, "backup", 2)),
        ("Connected to Emergency Node", MockClusterManager(True, "emergency", 1)),
        ("System Offline", MockClusterManager(False))
    ]

    for desc, cluster in scenarios:
        rich_prompt = ui.get_prompt(cluster)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{desc}:\033[0m")
        print(f"{ansi_prompt}\033[2mget health\033[0m")

    # Restore config
    ui.theme_manager.get_config_value = original_config


def demo_configuration_options():
    """Show different configuration combinations."""
    print_colored_header("🔩  CONFIGURATION OPTIONS", "\033[1;93m")

    console = Console()
    ui = ThemedTerminalUI(console)
    ui.set_theme('cyberpunk')

    cluster = MockClusterManager(True, "production", 8)

    configs = [
        ("Basic Connection Only", {
            'ui.prompt.format': 'esterm',
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': False,
            'ui.prompt.show_time': False
        }),
        ("With Node Count", {
            'ui.prompt.format': 'esterm',
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': True,
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
        }),
        ("Minimal Style", {
            'ui.prompt.format': 'simple',
            'ui.prompt.show_icons': False,
            'ui.prompt.show_node_count': False,
            'ui.prompt.show_time': False
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
        print(f"{ansi_prompt}\033[2mstatus\033[0m")

        # Restore config
        ui.theme_manager.get_config_value = original_config


def demo_theme_comparison():
    """Compare prompts across different themes."""
    print_colored_header("🎨 THEME COMPARISON", "\033[1;94m")

    themes = [
        ('rich', 'Rich Colors'),
        ('cyberpunk', 'Cyberpunk Neon'),
        ('matrix', 'Matrix Terminal'),
        ('ocean', 'Ocean Blue'),
        ('fire', 'Fire Orange')
    ]

    cluster = MockClusterManager(True, "cluster", 4)

    for theme_name, theme_desc in themes:
        console = Console()
        ui = ThemedTerminalUI(console)
        ui.set_theme(theme_name)

        # Enable basic enhancements
        original_config = ui.theme_manager.get_config_value
        def mock_config(key, default):
            config_map = {
                'ui.prompt.show_icons': True,
                'ui.prompt.show_node_count': True
            }
            # Use theme-specific format if available
            if theme_name in ['cyberpunk', 'matrix']:
                config_map['ui.prompt.format'] = theme_name

            return config_map.get(key, original_config(key, default))

        ui.theme_manager.get_config_value = mock_config

        rich_prompt = ui.get_prompt(cluster)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{theme_desc}:\033[0m")
        print(f"{ansi_prompt}\033[2mget indices\033[0m")

        # Restore config
        ui.theme_manager.get_config_value = original_config


def show_connection_legend():
    """Show the connection icon legend."""
    print_colored_header("📋 CONNECTION INDICATORS", "\033[1;97m")

    indicators = [
        ("🔗", "Connected", "Active connection to cluster"),
        ("🔌", "Disconnected", "No active cluster connection"),
        ("cluster:5", "Node Count", "Shows number of nodes in cluster (optional)"),
        ("14:32:45", "Timestamp", "Current time display (optional)")
    ]

    for icon, name, description in indicators:
        print(f"\n  {icon} \033[1m{name}\033[0m")
        print(f"     \033[2m{description}\033[0m")

    print(f"\n\033[93mNote:\033[0m \033[2mHealth status is NOT shown in prompts to avoid")
    print(f"displaying potentially stale information. Use 'get health' or")
    print(f"'status' commands to check current cluster health.\033[0m")


def show_updated_usage():
    """Show updated usage instructions."""
    print_colored_header("💡 UPDATED USAGE GUIDE", "\033[1;94m")

    print("\033[1mKey Changes:\033[0m")
    print("  • Removed health status from prompts (prevents stale data)")
    print("  • Focus on connection status and cluster identity")
    print("  • Use dedicated commands for health information")

    print(f"\n\033[1mRecommended Configuration:\033[0m")
    print(f"\033[36m")
    print("ui:")
    print("  prompt:")
    print("    format: cyberpunk          # or matrix, esterm, simple")
    print("    show_icons: true           # Connection indicators")
    print("    show_node_count: true      # Cluster size info")
    print("    show_time: false           # Optional timestamp")
    print(f"\033[0m")

    print(f"\n\033[1mFor Real-time Health Information:\033[0m")
    commands = [
        "get health         # Current cluster health",
        "status             # Detailed cluster status",
        "get cluster stats  # Cluster statistics",
        "monitor           # Real-time monitoring"
    ]

    for command in commands:
        print(f"  \033[92m{command}\033[0m")


def main():
    """Run the updated demonstration."""
    # Clear screen and show banner
    print("\033[2J\033[H")
    print("\033[1;96m" + "=" * 70 + "\033[0m")
    print("\033[1;96m" + "ESterm Connection-Based Prompts Demo".center(70) + "\033[0m")
    print("\033[1;96m" + "=" * 70 + "\033[0m")
    print("\033[2mFocused on connection status, not potentially stale health data\033[0m")

    try:
        demo_cyberpunk_theme()
        demo_matrix_theme()
        demo_configuration_options()
        demo_theme_comparison()
        show_connection_legend()
        show_updated_usage()

        # Interactive test
        print(f"\n\033[93mTry an interactive prompt? (y/n): \033[0m", end="")
        try:
            response = input()
            if response.lower().startswith('y'):
                console = Console()
                ui = ThemedTerminalUI(console)
                ui.set_theme('cyberpunk')

                original_config = ui.theme_manager.get_config_value
                def mock_config(key, default):
                    return {
                        'ui.prompt.format': 'cyberpunk',
                        'ui.prompt.show_icons': True,
                        'ui.prompt.show_node_count': True,
                        'ui.prompt.show_time': True
                    }.get(key, original_config(key, default))

                ui.theme_manager.get_config_value = mock_config
                cluster = MockClusterManager(True, "production", 5)

                print(f"\n\033[2mCyberpunk theme interactive test:\033[0m")
                rich_prompt = ui.get_prompt(cluster)
                ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

                user_input = input(ansi_prompt)
                if user_input.strip():
                    print(f"\033[2mYou typed: {user_input}\033[0m")

                ui.theme_manager.get_config_value = original_config

        except (KeyboardInterrupt, EOFError):
            print("\n\033[2mSkipping interactive test.\033[0m")

        # Final message
        print_colored_header("✅ DEMO COMPLETE", "\033[1;92m")
        print("\033[2mConnection-based prompts are ready!")
        print("No more misleading health status in prompts.")
        print("Use dedicated commands for real-time cluster health information.\033[0m")

    except KeyboardInterrupt:
        print("\n\n\033[93mDemo interrupted.\033[0m")
    except Exception as e:
        print(f"\n\033[91mDemo error: {e}\033[0m")
        import traceback
        print(f"\033[2m{traceback.format_exc()}\033[0m")


if __name__ == "__main__":
    main()
