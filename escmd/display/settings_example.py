#!/usr/bin/env python3
"""
Example usage of the SettingsRenderer and SettingsDataCollector.

This demonstrates how to use the new renderer-based architecture
for displaying configuration settings in different formats.
"""

from settings_renderer import SettingsRenderer
from settings_data import SettingsDataCollector
from rich.console import Console


def main():
    """Demonstrate different settings display formats."""

    print("=== Settings Renderer Examples ===\n")

    # Initialize components
    console = Console()
    data_collector = SettingsDataCollector()
    renderer = SettingsRenderer(console)

    # Mock configuration manager for examples
    mock_config = create_mock_configuration_manager()

    # Collect settings data
    settings_data = data_collector.collect_settings_data(mock_config)

    # Example 1: Full settings overview (default)
    print("1. Full Settings Overview:")
    print("-" * 50)
    renderer.render_settings_overview(settings_data)

    # Example 2: Settings table only
    print("\n2. Settings Table Only:")
    print("-" * 50)
    renderer.render_settings_table(settings_data)

    # Example 3: Clusters table only
    print("\n3. Clusters Table Only:")
    print("-" * 50)
    renderer.render_clusters_table(settings_data)

    # Example 4: Authentication table only
    print("\n4. Authentication Table Only:")
    print("-" * 50)
    renderer.render_authentication_table(settings_data)

    # Example 5: Settings summary
    print("\n5. Settings Summary:")
    print("-" * 50)
    renderer.render_settings_summary(settings_data)

    # Example 6: JSON settings display
    print("\n6. JSON Settings Display:")
    print("-" * 50)
    renderer.render_json_settings(settings_data)

    print("\n=== Examples Complete ===")


def demonstrate_advanced_features():
    """Demonstrate advanced features of the settings system."""

    print("\n=== Advanced Features ===")
    console = Console()
    data_collector = SettingsDataCollector()
    renderer = SettingsRenderer(console)
    mock_config = create_mock_configuration_manager()

    # Security analysis
    print("\n1. Security Analysis:")
    print("-" * 30)
    settings_data = data_collector.collect_settings_data(mock_config)
    security_analysis = data_collector.analyze_security_posture(settings_data)
    renderer.render_security_analysis(settings_data, security_analysis)

    # Configuration validation
    print("\n2. Configuration Validation:")
    print("-" * 35)
    validation_results = data_collector.validate_configuration(mock_config)
    renderer.render_validation_results(validation_results)

    # File information
    print("\n3. Configuration Files:")
    print("-" * 30)
    renderer.render_file_info(settings_data)

    # Environment overrides
    print("\n4. Environment Overrides:")
    print("-" * 30)
    overrides = settings_data.get('environment_overrides', {})
    if overrides:
        for key, info in overrides.items():
            console.print(f"[yellow]{info['variable']}[/yellow] = {info['value']} ({info['description']})")
    else:
        console.print("[dim]No environment overrides detected[/dim]")


def demonstrate_error_handling():
    """Demonstrate error handling with settings renderer."""

    print("\n=== Error Handling Examples ===")
    console = Console()
    renderer = SettingsRenderer(console)
    data_collector = SettingsDataCollector()

    # Example with empty configuration
    print("\n1. Empty Configuration:")
    print("-" * 30)
    empty_config = create_empty_configuration_manager()
    settings_data = data_collector.collect_settings_data(empty_config)
    renderer.render_settings_overview(settings_data)

    # Example with missing files
    print("\n2. Missing Configuration Files:")
    print("-" * 40)
    broken_config = create_broken_configuration_manager()
    validation_results = data_collector.validate_configuration(broken_config)
    renderer.render_validation_results(validation_results)

    # Example with insecure configuration
    print("\n3. Insecure Configuration:")
    print("-" * 35)
    insecure_config = create_insecure_configuration_manager()
    settings_data = data_collector.collect_settings_data(insecure_config)
    security_analysis = data_collector.analyze_security_posture(settings_data)
    renderer.render_security_analysis(settings_data, security_analysis)


def create_mock_configuration_manager():
    """Create a mock configuration manager with sample data."""

    class MockConfigManager:
        def __init__(self):
            self.default_settings = {
                'health_style': 'dashboard',
                'classic_style': 'panel',
                'enable_paging': False,
                'paging_threshold': 50,
                'ilm_display_limit': 50,
                'show_legend_panels': False,
                'ascii_mode': False,
                'display_theme': 'rich',
                'connection_timeout': 30,
                'read_timeout': 120,
                'flush_timeout': 600,
                'dangling_cleanup': {
                    'max_retries': 3,
                    'retry_delay': 5,
                    'timeout': 60,
                    'default_log_level': 'INFO',
                    'enable_progress_bar': True,
                    'confirmation_required': True
                }
            }

            self.servers_dict = {
                'prod-primary': {
                    'hostname': 'es-prod-1.company.com',
                    'port': 9200,
                    'env': 'production',
                    'use_ssl': True,
                    'verify_certs': True,
                    'elastic_authentication': True,
                    'elastic_username': 'prod_user'
                },
                'staging': {
                    'hostname': 'es-staging.company.com',
                    'port': 9200,
                    'env': 'staging',
                    'use_ssl': True,
                    'verify_certs': False,
                    'elastic_authentication': True,
                    'elastic_username': 'staging_user'
                },
                'dev-local': {
                    'hostname': 'localhost',
                    'port': 9200,
                    'env': 'development',
                    'use_ssl': False,
                    'verify_certs': False,
                    'elastic_authentication': False
                }
            }

            self._default_cluster = 'prod-primary'
            self.is_dual_file_mode = True
            self.main_config_path = '/path/to/escmd.yml'
            self.servers_config_path = '/path/to/elastic_servers.yml'

        def get_default_cluster(self):
            return self._default_cluster

        def get_server_config(self, location_name):
            return self.servers_dict.get(location_name)

    return MockConfigManager()


def create_empty_configuration_manager():
    """Create a mock configuration manager with minimal data."""

    class EmptyConfigManager:
        def __init__(self):
            self.default_settings = {}
            self.servers_dict = {}
            self._default_cluster = None
            self.is_dual_file_mode = False
            self.config_file_path = '/path/to/escmd.yml'

        def get_default_cluster(self):
            return self._default_cluster

        def get_server_config(self, location_name):
            return None

    return EmptyConfigManager()


def create_broken_configuration_manager():
    """Create a configuration manager with missing files."""

    class BrokenConfigManager:
        def __init__(self):
            self.default_settings = {'ascii_mode': False}
            self.servers_dict = {
                'broken-cluster': {
                    'port': 9200,
                    'env': 'test'
                    # Missing hostname
                }
            }
            self._default_cluster = None  # No default set
            self.is_dual_file_mode = True
            self.main_config_path = '/nonexistent/escmd.yml'
            self.servers_config_path = '/nonexistent/servers.yml'

        def get_default_cluster(self):
            return self._default_cluster

        def get_server_config(self, location_name):
            return self.servers_dict.get(location_name)

    return BrokenConfigManager()


def create_insecure_configuration_manager():
    """Create a configuration manager with security issues."""

    class InsecureConfigManager:
        def __init__(self):
            self.default_settings = {'connection_timeout': 30}
            self.servers_dict = {
                'insecure-prod': {
                    'hostname': 'prod.example.com',
                    'port': 9200,
                    'env': 'production',
                    'use_ssl': False,  # No SSL
                    'verify_certs': False,
                    'elastic_authentication': True,
                    'elastic_username': 'admin',
                    'elastic_password': 'plaintext123'  # Plaintext password
                },
                'no-auth': {
                    'hostname': 'open.example.com',
                    'port': 9200,
                    'env': 'production',
                    'use_ssl': True,
                    'verify_certs': False,  # SSL but no cert verification
                    'elastic_authentication': False  # No authentication
                }
            }
            self._default_cluster = 'insecure-prod'
            self.is_dual_file_mode = True
            self.main_config_path = '/path/to/escmd.yml'
            self.servers_config_path = '/path/to/servers.yml'

        def get_default_cluster(self):
            return self._default_cluster

        def get_server_config(self, location_name):
            return self.servers_dict.get(location_name)

    return InsecureConfigManager()


def performance_analysis():
    """Analyze performance and demonstrate benefits of the renderer pattern."""

    import time

    print("\n=== Performance & Benefits Analysis ===")
    console = Console()

    # Timing test
    start_time = time.time()

    mock_config = create_mock_configuration_manager()
    data_collector = SettingsDataCollector()
    renderer = SettingsRenderer(console)

    # Collect data
    settings_data = data_collector.collect_settings_data(mock_config)

    # Simulate rendering (suppress output)
    renderer.console = Console(file=open('/dev/null', 'w'))
    renderer.render_settings_overview(settings_data)

    end_time = time.time()
    processing_time = end_time - start_time

    console = Console()  # Reset console for output
    console.print(f"[blue]Processing time:[/blue] {processing_time:.4f} seconds")
    console.print()

    console.print("[bold green]✓ Settings Renderer Pattern Benefits:[/bold green]")
    console.print("  🎯 [cyan]Separation of Concerns:[/cyan] Data collection ↔️ Presentation")
    console.print("  🔄 [cyan]Multiple Formats:[/cyan] Overview, tables, summary, JSON")
    console.print("  🧪 [cyan]Testability:[/cyan] Easy to unit test components separately")
    console.print("  🔧 [cyan]Maintainability:[/cyan] UI changes don't affect business logic")
    console.print("  🔐 [cyan]Security Analysis:[/cyan] Built-in configuration security scoring")
    console.print("  ✅ [cyan]Validation:[/cyan] Comprehensive configuration validation")
    console.print()

    console.print("[bold yellow]💡 Data Collection Features:[/bold yellow]")
    console.print("  • Configuration settings with descriptions")
    console.print("  • Cluster information and authentication")
    console.print("  • Environment variable overrides")
    console.print("  • File existence checking")
    console.print("  • Security posture analysis")
    console.print("  • Configuration validation")
    console.print()

    console.print("[bold magenta]🎨 Rendering Options:[/bold magenta]")
    console.print("  • Complete settings overview")
    console.print("  • Individual component tables")
    console.print("  • Compact summary display")
    console.print("  • JSON output for automation")
    console.print("  • Security analysis visualization")
    console.print("  • Validation results display")
    console.print("  • File status information")


if __name__ == "__main__":
    main()
    demonstrate_advanced_features()
    demonstrate_error_handling()
    performance_analysis()
