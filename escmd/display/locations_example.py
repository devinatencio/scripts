#!/usr/bin/env python3
"""
Example usage of the LocationsRenderer and LocationsDataCollector.

This demonstrates how to use the new renderer-based architecture
for displaying location/cluster information in different formats.
"""

from locations_renderer import LocationsRenderer
from locations_data import LocationsDataCollector
from rich.console import Console


def main():
    """Demonstrate different locations display formats."""

    print("=== Locations Renderer Examples ===\n")

    # Initialize components
    console = Console()
    data_collector = LocationsDataCollector()
    renderer = LocationsRenderer(console)

    # Mock configuration manager for examples
    mock_config = create_mock_configuration_manager()

    # Collect locations data
    locations_data = data_collector.collect_locations_data(mock_config)

    # Example 1: Full locations table display (default)
    print("1. Full Locations Table Display:")
    print("-" * 50)
    renderer.render_locations_table(locations_data)

    # Example 2: Simple locations list
    print("\n2. Simple Locations List:")
    print("-" * 50)
    renderer.render_locations_list(locations_data, simple=True)

    # Example 3: Detailed locations list
    print("\n3. Detailed Locations List:")
    print("-" * 50)
    renderer.render_locations_list(locations_data, simple=False)

    # Example 4: JSON locations display
    print("\n4. JSON Locations Display:")
    print("-" * 50)
    renderer.render_json_locations(locations_data)

    # Example 5: Single location details
    print("\n5. Single Location Details:")
    print("-" * 50)
    location_details = data_collector.get_location_details(mock_config, 'prod-east')
    renderer.render_location_details(location_details)

    # Example 6: Environment summary
    print("\n6. Environment Summary:")
    print("-" * 50)
    summary_data = data_collector.get_environment_summary(mock_config)
    renderer.render_locations_summary(summary_data)

    # Example 7: Search functionality
    print("\n7. Search Results:")
    print("-" * 50)
    search_results = data_collector.search_locations(mock_config, 'prod')
    renderer.render_search_results(search_results, 'prod')

    print("\n=== Examples Complete ===")


def demonstrate_error_handling():
    """Demonstrate error handling with locations renderer."""

    print("\n=== Error Handling Examples ===")
    console = Console()
    renderer = LocationsRenderer(console)
    data_collector = LocationsDataCollector()

    # Example with empty configuration
    empty_config = create_empty_configuration_manager()
    locations_data = data_collector.collect_locations_data(empty_config)

    print("\n1. No Locations Configured:")
    print("-" * 30)
    renderer.render_locations_table(locations_data)

    # Example with location not found
    print("\n2. Location Not Found:")
    print("-" * 30)
    mock_config = create_mock_configuration_manager()
    location_details = data_collector.get_location_details(mock_config, 'nonexistent')
    renderer.render_location_details(location_details)

    # Example with search no results
    print("\n3. Search No Results:")
    print("-" * 30)
    search_results = data_collector.search_locations(mock_config, 'xyz')
    renderer.render_search_results(search_results, 'xyz')


def demonstrate_advanced_features():
    """Demonstrate advanced features of the locations system."""

    print("\n=== Advanced Features ===")
    console = Console()
    data_collector = LocationsDataCollector()
    mock_config = create_mock_configuration_manager()

    # Configuration validation
    print("\n1. Configuration Validation:")
    print("-" * 35)
    for location_name in ['prod-east', 'dev-local', 'staging']:
        if location_name in mock_config.servers_dict:
            config = mock_config.servers_dict[location_name]
            validation = data_collector.validate_location_config(config)

            console.print(f"[bold]{location_name}:[/bold]")
            console.print(f"  Valid: {'✓' if validation['is_valid'] else '✗'}")
            console.print(f"  Score: {validation['score']}/100")

            if validation['missing_required']:
                console.print(f"  [red]Missing Required:[/red] {', '.join(validation['missing_required'])}")

            if validation['warnings']:
                console.print(f"  [yellow]Warnings:[/yellow]")
                for warning in validation['warnings']:
                    console.print(f"    • {warning}")
            console.print()

    # Available locations
    print("\n2. Available Locations:")
    print("-" * 30)
    locations = data_collector.get_available_locations(mock_config)
    for location in locations:
        console.print(f"  📍 {location}")


def create_mock_configuration_manager():
    """Create a mock configuration manager with sample data."""

    class MockConfigManager:
        def __init__(self):
            self.servers_dict = {
                'prod-east': {
                    'hostname': 'es-prod-east.company.com',
                    'hostname2': 'es-prod-east-2.company.com',
                    'port': 9200,
                    'env': 'production',
                    'use_ssl': True,
                    'verify_certs': True,
                    'elastic_username': 'prod_user'
                },
                'prod-west': {
                    'hostname': 'es-prod-west.company.com',
                    'port': 9200,
                    'env': 'production',
                    'use_ssl': True,
                    'verify_certs': True,
                    'elastic_username': 'prod_user'
                },
                'staging': {
                    'hostname': 'es-staging.company.com',
                    'port': 9200,
                    'env': 'staging',
                    'use_ssl': True,
                    'verify_certs': False,
                    'elastic_username': 'staging_user'
                },
                'dev-local': {
                    'hostname': 'localhost',
                    'port': 9200,
                    'env': 'development',
                    'use_ssl': False,
                    'verify_certs': False,
                    'elastic_username': ''
                }
            }
            self._default_cluster = 'prod-east'

        def get_default_cluster(self):
            return self._default_cluster

        def get_server_config(self, location_name):
            return self.servers_dict.get(location_name)

        def set_default_cluster(self, cluster_name):
            self._default_cluster = cluster_name

    return MockConfigManager()


def create_empty_configuration_manager():
    """Create a mock configuration manager with no data."""

    class EmptyConfigManager:
        def __init__(self):
            self.servers_dict = {}

        def get_default_cluster(self):
            return None

        def get_server_config(self, location_name):
            return None

    return EmptyConfigManager()


def performance_comparison():
    """Compare performance and demonstrate benefits of the renderer pattern."""

    import time

    print("\n=== Performance & Benefits Analysis ===")
    console = Console()

    # Timing test
    start_time = time.time()

    mock_config = create_mock_configuration_manager()
    data_collector = LocationsDataCollector()
    renderer = LocationsRenderer(console)

    # Collect data
    locations_data = data_collector.collect_locations_data(mock_config)

    # Simulate rendering (suppress output)
    renderer.console = Console(file=open('/dev/null', 'w'))
    renderer.render_locations_table(locations_data)

    end_time = time.time()
    processing_time = end_time - start_time

    console = Console()  # Reset console for output
    console.print(f"[blue]Processing time:[/blue] {processing_time:.4f} seconds")
    console.print()

    console.print("[bold green]✓ Renderer Pattern Benefits:[/bold green]")
    console.print("  🎯 [cyan]Separation of Concerns:[/cyan] Data collection ↔️ Presentation")
    console.print("  🔄 [cyan]Reusability:[/cyan] Multiple output formats from same data")
    console.print("  🧪 [cyan]Testability:[/cyan] Easy to unit test components separately")
    console.print("  🔧 [cyan]Maintainability:[/cyan] UI changes don't affect business logic")
    console.print("  🎨 [cyan]Flexibility:[/cyan] Easy to add new display formats")
    console.print("  📊 [cyan]Consistency:[/cyan] Uniform styling across the application")
    console.print()

    console.print("[bold yellow]💡 Data Collection Features:[/bold yellow]")
    console.print("  • Environment grouping and sorting")
    console.print("  • Default cluster identification")
    console.print("  • Configuration validation")
    console.print("  • Search functionality")
    console.print("  • Summary statistics")
    console.print()

    console.print("[bold magenta]🎨 Rendering Options:[/bold magenta]")
    console.print("  • Full table display with environment grouping")
    console.print("  • Simple list format")
    console.print("  • Detailed list with connection info")
    console.print("  • JSON output for automation")
    console.print("  • Single location details")
    console.print("  • Search results display")
    console.print("  • Environment summary statistics")


if __name__ == "__main__":
    main()
    demonstrate_error_handling()
    demonstrate_advanced_features()
    performance_comparison()
