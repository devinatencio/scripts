#!/usr/bin/env python3
"""
Starship-Inspired ESterm Prompt Demo

This script demonstrates the new contextual cluster indicators inspired by
Starship's intelligent module system. Shows how different cluster types get
different icons and context-aware information display.

Features demonstrated:
- Contextual cluster icons based on environment type
- Environment context indicators (production warnings, etc.)
- Conditional node count display (only when meaningful)
- Git-style status indicators for cluster state
- Smart icon selection based on cluster naming patterns
"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from rich.console import Console
from esterm_modules.themed_terminal_ui import ThemedTerminalUI


class MockClusterManager:
    """Enhanced mock cluster manager for demonstration."""

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


def demo_contextual_indicators():
    """Demonstrate contextual cluster indicators."""
    print_colored_header("🎯 CONTEXTUAL CLUSTER INDICATORS", "\033[1;95m")

    console = Console()
    ui = ThemedTerminalUI(console)
    ui.set_theme('cyberpunk')

    # Override config for enhanced display
    original_config = ui.theme_manager.get_config_value
    def mock_config(key, default):
        return {
            'ui.prompt.format': 'cyberpunk',
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': True,
            'ui.prompt.show_time': False
        }.get(key, original_config(key, default))

    ui.theme_manager.get_config_value = mock_config

    # Different cluster types with contextual icons
    clusters = [
        ("production-cluster", 8, "🏢 Production (database icon)"),
        ("production-east", 12, "🏢 Production East (database icon)"),
        ("dev-environment", 2, "💻 Development (terminal icon)"),
        ("development-local", 1, "💻 Development Local (terminal icon)"),
        ("staging-env", 4, "🧪 Staging (beaker icon)"),
        ("qa-testing", 3, "🧪 QA Testing (beaker icon)"),
        ("localhost", 1, "🏠 Local (home icon)"),
        ("local-dev", 1, "🏠 Local Dev (home icon)"),
        ("aws-prod-cluster", 15, "☁️ AWS Production (cloud icon)"),
        ("gcp-analytics", 6, "🌐 Google Cloud (GCP icon)"),
        ("azure-backup", 4, "🔷 Azure (Azure icon)"),
        ("search-cluster", 5, "🔍 Generic Search (elasticsearch icon)")
    ]

    print("\033[2mDifferent cluster types get contextual icons automatically:\033[0m")

    for cluster_name, node_count, description in clusters:
        cluster_mgr = MockClusterManager(True, cluster_name, node_count)
        rich_prompt = ui.get_prompt(cluster_mgr)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{description}:\033[0m")
        print(f"{ansi_prompt}\033[2mget health\033[0m")

    ui.theme_manager.get_config_value = original_config


def demo_environment_context():
    """Demonstrate environment context indicators."""
    print_colored_header("🔶  ENVIRONMENT CONTEXT INDICATORS", "\033[1;93m")

    console = Console()
    ui = ThemedTerminalUI(console)
    ui.set_theme('rich')

    # Override config
    original_config = ui.theme_manager.get_config_value
    def mock_config(key, default):
        return {
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': True
        }.get(key, original_config(key, default))

    ui.theme_manager.get_config_value = mock_config

    environments = [
        ("prod-api-cluster", 10, "Production (! warning indicator)"),
        ("staging-web", 4, "Staging (~ staging indicator)"),
        ("dev-backend", 2, "Development (◦ dev indicator)"),
        ("test-cluster", 3, "Test (no special indicator)")
    ]

    print("\033[2mEnvironment context helps identify risk levels:\033[0m")

    for cluster_name, node_count, description in environments:
        cluster_mgr = MockClusterManager(True, cluster_name, node_count)
        rich_prompt = ui.get_prompt(cluster_mgr)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{description}:\033[0m")
        print(f"{ansi_prompt}\033[2mstatus\033[0m")

    ui.theme_manager.get_config_value = original_config


def demo_conditional_display():
    """Demonstrate conditional information display."""
    print_colored_header("🔧 CONDITIONAL DISPLAY LOGIC", "\033[1;92m")

    console = Console()
    ui = ThemedTerminalUI(console)
    ui.set_theme('matrix')

    original_config = ui.theme_manager.get_config_value
    def mock_config(key, default):
        return {
            'ui.prompt.format': 'matrix',
            'ui.prompt.show_icons': True,
            'ui.prompt.show_node_count': True
        }.get(key, original_config(key, default))

    ui.theme_manager.get_config_value = mock_config

    scenarios = [
        ("single-node", 1, "Single node - shows dot indicator"),
        ("small-cluster", 2, "2 nodes - no special indicator"),
        ("medium-cluster", 4, "4 nodes - shows + indicator"),
        ("large-cluster", 8, "8 nodes - shows + indicator")
    ]

    print("\033[2mNode count and indicators only show when meaningful:\033[0m")

    for cluster_name, node_count, description in scenarios:
        cluster_mgr = MockClusterManager(True, cluster_name, node_count)
        rich_prompt = ui.get_prompt(cluster_mgr)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{description}:\033[0m")
        print(f"{ansi_prompt}\033[2mget indices\033[0m")

    ui.theme_manager.get_config_value = original_config


def demo_theme_variations():
    """Show how different themes handle the contextual indicators."""
    print_colored_header("🎨 THEME VARIATIONS", "\033[1;94m")

    themes = ['cyberpunk', 'matrix', 'rich', 'ocean']
    cluster_mgr = MockClusterManager(True, "aws-production", 6)

    for theme_name in themes:
        console = Console()
        ui = ThemedTerminalUI(console)
        ui.set_theme(theme_name)

        original_config = ui.theme_manager.get_config_value
        def mock_config(key, default):
            config_map = {
                'ui.prompt.show_icons': True,
                'ui.prompt.show_node_count': True
            }
            if theme_name in ['cyberpunk', 'matrix']:
                config_map['ui.prompt.format'] = theme_name
            return config_map.get(key, original_config(key, default))

        ui.theme_manager.get_config_value = mock_config

        rich_prompt = ui.get_prompt(cluster_mgr)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2m{theme_name.title()} theme:\033[0m")
        print(f"{ansi_prompt}\033[2mget cluster stats\033[0m")

        ui.theme_manager.get_config_value = original_config


def show_icon_legend():
    """Show the new contextual icon legend."""
    print_colored_header("📋 CONTEXTUAL ICON LEGEND", "\033[1;97m")

    icons = [
        ("🏢", "Production Environments", "prod*, production*, live*, master*"),
        ("💻", "Development Environments", "dev*, develop*, test*, sandbox*"),
        ("🧪", "Staging Environments", "stage*, staging*, qa*, uat*"),
        ("🏠", "Local Environments", "local*, localhost, 127.0.0.1"),
        ("☁️", "AWS Clusters", "aws*, ec2*, amazon*"),
        ("🌐", "Google Cloud", "gcp*, google*, cloud*"),
        ("🔷", "Microsoft Azure", "azure*, microsoft*"),
        ("🔍", "Generic Clusters", "Everything else (elasticsearch icon)")
    ]

    print("\033[2mIcons are automatically chosen based on cluster name patterns:\033[0m")

    for icon, description, patterns in icons:
        print(f"\n  {icon} \033[1m{description}\033[0m")
        print(f"     \033[2m{patterns}\033[0m")

    print(f"\n\033[93mEnvironment Context Indicators:\033[0m")
    context_indicators = [
        ("!", "Production Warning", "red", "Reminds you you're in production"),
        ("~", "Staging Indicator", "yellow", "Shows staging environment"),
        ("◦", "Development Marker", "green", "Indicates dev environment")
    ]

    for symbol, name, color, description in context_indicators:
        print(f"\n  \033[{{'red': '91', 'yellow': '93', 'green': '92'}}[color]m{symbol}\033[0m \033[1m{name}\033[0m")
        print(f"     \033[2m{description}\033[0m")


def show_starship_inspiration():
    """Show what we learned from Starship."""
    print_colored_header("⭐ STARSHIP INSPIRATION", "\033[1;96m")

    principles = [
        ("Contextual Intelligence", "Icons and info adapt to what you're working with"),
        ("Conditional Display", "Only show information when it's relevant"),
        ("Visual Hierarchy", "Important info stands out, details are subtle"),
        ("Environment Awareness", "Different environments get different treatment"),
        ("Performance Focus", "Fast, efficient, no unnecessary operations"),
        ("Consistent Design", "Cohesive look across different contexts")
    ]

    print("\033[2mPrinciples adapted from Starship:\033[0m")

    for principle, description in principles:
        print(f"\n  \033[1m{principle}\033[0m")
        print(f"     \033[2m{description}\033[0m")

    print(f"\n\033[93mKey Improvements:\033[0m")
    improvements = [
        "Replaced generic 🔗 with contextual environment icons",
        "Added environment risk indicators (production warnings)",
        "Smart node count display (only when > 1 node)",
        "Git-style status indicators for cluster state",
        "Better visual hierarchy with subtle accent elements"
    ]

    for improvement in improvements:
        print(f"  • {improvement}")


def interactive_cluster_test():
    """Interactive test with different cluster types."""
    print_colored_header("🎮 INTERACTIVE CLUSTER TEST", "\033[1;91m")

    print("\033[2mTry different cluster names to see contextual icons:\033[0m")
    print("\033[2mPress Enter to continue with each, or Ctrl+C to skip.\033[0m")

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

    test_clusters = [
        ("my-production-api", 8),
        ("dev-local-test", 1),
        ("aws-staging-web", 4),
        ("gcp-analytics-prod", 12)
    ]

    for cluster_name, node_count in test_clusters:
        cluster_mgr = MockClusterManager(True, cluster_name, node_count)
        rich_prompt = ui.get_prompt(cluster_mgr)
        ansi_prompt = ui._convert_rich_to_ansi(rich_prompt)

        print(f"\n\033[2mCluster: {cluster_name} ({node_count} nodes)\033[0m")
        try:
            user_input = input(ansi_prompt)
            if user_input.strip():
                print(f"\033[2mYou typed: {user_input}\033[0m")
        except (KeyboardInterrupt, EOFError):
            print("\n\033[2mSkipping remaining tests...\033[0m")
            break

    ui.theme_manager.get_config_value = original_config


def main():
    """Run the Starship-inspired demonstration."""
    # Clear screen and show banner
    print("\033[2J\033[H")
    print("\033[1;96m" + "=" * 70 + "\033[0m")
    print("\033[1;96m" + "Starship-Inspired ESterm Prompts Demo".center(70) + "\033[0m")
    print("\033[1;96m" + "=" * 70 + "\033[0m")
    print("\033[2mContextual, intelligent prompts inspired by Starship\033[0m")

    try:
        demo_contextual_indicators()
        demo_environment_context()
        demo_conditional_display()
        demo_theme_variations()
        show_icon_legend()
        show_starship_inspiration()

        # Ask about interactive test
        print(f"\n\033[93mTry the interactive cluster test? (y/n): \033[0m", end="")
        try:
            response = input()
            if response.lower().startswith('y'):
                interactive_cluster_test()
        except (KeyboardInterrupt, EOFError):
            print("\n\033[2mSkipping interactive test.\033[0m")

        # Final message
        print_colored_header("🚀 STARSHIP-INSPIRED PROMPTS READY", "\033[1;92m")
        print("\033[2mContextual cluster indicators now provide intelligent,")
        print("environment-aware visual feedback in your ESterm prompts!")
        print("No more generic connection icons - each cluster type gets")
        print("appropriate visual treatment based on naming patterns.\033[0m")

    except KeyboardInterrupt:
        print("\n\n\033[93mDemo interrupted.\033[0m")
    except Exception as e:
        print(f"\n\033[91mDemo error: {e}\033[0m")
        import traceback
        print(f"\033[2m{traceback.format_exc()}\033[0m")


if __name__ == "__main__":
    main()
