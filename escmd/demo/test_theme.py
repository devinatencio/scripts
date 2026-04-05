#!/usr/bin/env python3
"""
Test script to verify cyberpunk theme is being applied correctly in ESterm.
This will help diagnose theme color issues.
"""

import sys
import os

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from rich.console import Console
from esterm_modules.theme_manager import EstermThemeManager
from esterm_modules.themed_terminal_ui import ThemedTerminalUI


def test_theme_loading():
    """Test if theme manager loads cyberpunk theme correctly."""
    console = Console()
    theme_manager = EstermThemeManager(console)

    print("=== Theme Manager Test ===")
    print(f"Current theme: {theme_manager.get_current_theme()}")
    print(f"Available themes: {theme_manager.get_available_themes()}")

    # Test specific cyberpunk colors
    print(f"\n=== Cyberpunk Theme Colors ===")
    print(f"Banner title style: {theme_manager.get_style('banner', 'title_style')}")
    print(f"Banner border style: {theme_manager.get_style('banner', 'border_style')}")
    print(f"Prompt connected style: {theme_manager.get_style('prompt', 'connected_cluster_style')}")
    print(f"Status success style: {theme_manager.get_style('status', 'success_style')}")
    print(f"Message error style: {theme_manager.get_style('messages', 'error_style')}")


def test_themed_ui_display():
    """Test if themed UI displays colors correctly."""
    console = Console()
    ui = ThemedTerminalUI(console)

    print("\n=== Themed UI Display Test ===")

    # Test banner display
    print("Displaying banner with cyberpunk theme:")
    ui.show_banner("3.0.1", "09/06/2025")

    # Test status messages
    print("\nTesting status messages:")
    ui.show_success("This should be bright green (cyberpunk success)")
    ui.show_error("This should be bright red (cyberpunk error)")
    ui.show_warning("This should be bright yellow (cyberpunk warning)")
    ui.show_info("This should be bright cyan (cyberpunk info)")


def test_raw_rich_colors():
    """Test raw Rich colors to verify terminal support."""
    console = Console()

    print("\n=== Raw Rich Color Test ===")
    console.print("[bold bright_magenta]CYBERPUNK TITLE (should be bright magenta)[/bold bright_magenta]")
    console.print("[bright_cyan]Cyberpunk subtitle (should be bright cyan)[/bright_cyan]")
    console.print("[bright_green]Cyberpunk success (should be bright green)[/bright_green]")
    console.print("[bright_red]Cyberpunk error (should be bright red)[/bright_red]")
    console.print("[bright_yellow]Cyberpunk warning (should be bright yellow)[/bright_yellow]")

    # Test with panel
    from rich.panel import Panel
    from rich.text import Text

    panel_content = Text()
    panel_content.append("CYBERPUNK PANEL TEST\n", style="bold bright_magenta")
    panel_content.append("This panel should have bright magenta borders\n", style="bright_cyan")
    panel_content.append("and bright cyan text content", style="bright_white")

    panel = Panel.fit(
        panel_content,
        title="🔥 Cyberpunk Theme Test",
        border_style="bright_magenta",
        padding=(1, 2)
    )

    console.print(panel)


def test_config_verification():
    """Verify configuration is loading correctly."""
    import yaml

    print("\n=== Configuration Verification ===")

    # Check themes file
    themes_file = os.path.join(current_dir, 'esterm_themes.yml')
    if os.path.exists(themes_file):
        print("✓ esterm_themes.yml found")
        with open(themes_file, 'r') as f:
            themes_data = yaml.safe_load(f)
            if 'cyberpunk' in themes_data.get('esterm_themes', {}):
                print("✓ Cyberpunk theme found in themes file")
                cyberpunk_data = themes_data['esterm_themes']['cyberpunk']
                print(f"  - Banner title style: {cyberpunk_data['banner']['title_style']}")
                print(f"  - Border style: {cyberpunk_data['banner']['border_style']}")
            else:
                print("✗ Cyberpunk theme NOT found in themes file")
    else:
        print("✗ esterm_themes.yml NOT found")

    # Check config file
    config_file = os.path.join(current_dir, 'esterm_config.yml')
    if os.path.exists(config_file):
        print("✓ esterm_config.yml found")
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
            current_theme = config_data.get('theme', {}).get('current', 'unknown')
            print(f"  - Current theme setting: {current_theme}")
            if current_theme == 'cyberpunk':
                print("✓ Configuration is set to cyberpunk theme")
            else:
                print("✗ Configuration is NOT set to cyberpunk theme")
    else:
        print("✗ esterm_config.yml NOT found")


def main():
    """Run all theme tests."""
    print("🎨 ESterm Theme Verification Tool")
    print("=" * 50)

    test_config_verification()
    test_theme_loading()
    test_raw_rich_colors()
    test_themed_ui_display()

    print("\n" + "=" * 50)
    print("Theme test complete!")
    print("\nIf you see bright neon colors (magenta, cyan, green, etc.),")
    print("the cyberpunk theme is working correctly.")
    print("If colors appear dim or wrong, there may be a terminal compatibility issue.")


if __name__ == "__main__":
    main()
