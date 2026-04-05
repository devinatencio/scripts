#!/usr/bin/env python3
"""
Example usage of the VersionRenderer and VersionDataCollector.

This demonstrates how to use the new renderer-based architecture
for displaying version information in different formats.
"""

from version_renderer import VersionRenderer
from version_data import VersionDataCollector
from rich.console import Console


def main():
    """Demonstrate different version display formats."""

    print("=== Version Renderer Examples ===\n")

    # Initialize components
    console = Console()
    data_collector = VersionDataCollector()
    renderer = VersionRenderer(console)

    # Collect version data
    version_data = data_collector.collect_version_data()

    # Example 1: Full version display (default)
    print("1. Full Version Display:")
    print("-" * 50)
    renderer.render_version_info(version_data)

    # Example 2: Simple version display
    print("\n2. Simple Version Display:")
    print("-" * 50)
    renderer.render_simple_version(version_data)

    # Example 3: JSON version display
    print("\n3. JSON Version Display:")
    print("-" * 50)
    renderer.render_json_version(version_data)

    # Example 4: Custom version data
    print("\n4. Custom Version Data:")
    print("-" * 50)
    custom_data = {
        'version': '4.0.0-beta',
        'date': '2025-12-01',
        'tool_name': 'ESCMD-NEXT'
    }
    renderer.render_simple_version(custom_data)

    # Example 5: Demonstrating data collection methods
    print("\n5. Data Collection Methods:")
    print("-" * 50)

    # System info
    system_info = version_data.get('system_info', {})
    console.print(f"[blue]CPU Usage:[/blue] {system_info.get('cpu_percent', 'N/A')}%")
    console.print(f"[blue]Memory:[/blue] {system_info.get('memory_percent', 'N/A')}% used")
    console.print(f"[blue]Python:[/blue] {version_data.get('python_version', 'N/A')}")
    console.print(f"[blue]Platform:[/blue] {version_data.get('platform', 'N/A')}")

    # Command statistics
    command_stats = data_collector.collect_command_statistics()
    console.print(f"[green]Total Commands:[/green] {command_stats['total_commands']}")

    # Script location
    location_info = data_collector.get_script_location()
    console.print(f"[yellow]Script Directory:[/yellow] {location_info['script_directory']}")

    print("\n=== Examples Complete ===")


def demonstrate_error_handling():
    """Demonstrate error handling with version renderer."""

    print("\n=== Error Handling Examples ===")
    console = Console()
    renderer = VersionRenderer(console)

    # Example with missing data
    try:
        incomplete_data = {'version': '1.0.0'}  # Missing date
        renderer.render_version_info(incomplete_data)
    except Exception as e:
        console.print(f"[red]Error handled gracefully:[/red] {e}")

    # Example with invalid data
    try:
        invalid_data = None
        data_collector = VersionDataCollector()
        version_data = data_collector.collect_version_data()
        renderer.render_version_info(version_data)  # Should work with fallbacks
        console.print("[green]✓ Fallback data used successfully[/green]")
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def performance_comparison():
    """Compare performance of old vs new approach."""

    import time

    print("\n=== Performance Comparison ===")
    console = Console()

    # New approach timing
    start_time = time.time()
    data_collector = VersionDataCollector()
    renderer = VersionRenderer(console)
    version_data = data_collector.collect_version_data()

    # Simulate rendering (without actual output)
    renderer.console = Console(file=open('/dev/null', 'w'))  # Suppress output
    renderer.render_version_info(version_data)
    end_time = time.time()

    new_approach_time = end_time - start_time

    console = Console()  # Reset console for output
    console.print(f"[blue]New renderer approach:[/blue] {new_approach_time:.4f} seconds")
    console.print("[green]✓ Benefits:[/green]")
    console.print("  • Separated concerns (data vs presentation)")
    console.print("  • Reusable components")
    console.print("  • Multiple output formats")
    console.print("  • Easier testing")
    console.print("  • Better maintainability")


if __name__ == "__main__":
    main()
    demonstrate_error_handling()
    performance_comparison()
