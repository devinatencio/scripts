"""
Location renderer for ESCMD.

This module handles all display logic for cluster location information,
extracting the presentation layer from command handlers for better
separation of concerns.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import json


class LocationsRenderer:
    """Handles rendering of cluster location information with rich formatting."""

    def __init__(self, console=None, theme_manager=None):
        """
        Initialize the locations renderer.

        Args:
            console: Rich Console instance (creates new one if None)
            theme_manager: Theme manager for styling (optional)
        """
        self.console = console or Console()
        self.theme_manager = theme_manager

    def render_locations_table(self, locations_data, styles=None):
        """
        Render the main locations table with all clusters grouped by environment.

        Args:
            locations_data: Dictionary containing location information
            styles: Theme styles dictionary (optional)
        """
        if not locations_data.get('has_locations'):
            self._render_no_locations(locations_data, styles)
            return

        # Set default styles if none provided
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        # Create the main table
        locations_table = self._create_locations_table(styles, panel_styles)

        # Populate the table with location data
        self._populate_locations_table(locations_table, locations_data, panel_styles)

        # Create summary text
        summary_text = self._create_summary_text(locations_data)

        # Wrap in a panel
        panel = Panel(
            locations_table,
            title=summary_text,
            title_align="left",
            border_style=styles.get('border_style', 'white'),
            padding=(1, 2)
        )

        self.console.print(panel)

    def render_location_details(self, location_details, styles=None):
        """
        Render detailed information for a single location.

        Args:
            location_details: Dictionary containing detailed location info
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        if not location_details.get('found'):
            self._render_location_not_found(location_details, panel_styles)
            return

        # Create details table
        details_table = Table.grid(padding=(0, 3))
        details_table.add_column(style=panel_styles.get('title', 'cyan'), no_wrap=True, min_width=15)
        details_table.add_column(style=panel_styles.get('info', 'white'))

        details_table.add_row("Location:", location_details['location_name'])
        details_table.add_row("Environment:", location_details.get('environment', 'Unknown'))
        details_table.add_row("Hostname:", location_details.get('hostname', 'N/A'))

        if location_details.get('hostname2'):
            details_table.add_row("Hostname2:", location_details['hostname2'])

        details_table.add_row("Port:", str(location_details.get('port', 9200)))

        # SSL info with colored indicators
        ssl_status = "✓ Enabled" if location_details.get('use_ssl') else "✗ Disabled"
        ssl_style = panel_styles.get('success', 'green') if location_details.get('use_ssl') else panel_styles.get('error', 'red')
        details_table.add_row("SSL:", Text(ssl_status, style=ssl_style))

        verify_status = "✓ Enabled" if location_details.get('verify_certs') else "✗ Disabled"
        verify_style = panel_styles.get('success', 'green') if location_details.get('verify_certs') else panel_styles.get('error', 'red')
        details_table.add_row("Cert Verify:", Text(verify_status, style=verify_style))

        if location_details.get('username'):
            details_table.add_row("Username:", location_details['username'])

        if location_details.get('is_default'):
            details_table.add_row("Default:", Text("★ Yes", style=panel_styles.get('success', 'bold green')))

        title = f"📍 {location_details['location_name']} Details"
        panel = Panel(
            details_table,
            title=title,
            border_style=panel_styles.get('secondary', 'cyan'),
            padding=(1, 2)
        )

        self.console.print(panel)

    def render_locations_summary(self, summary_data, styles=None):
        """
        Render a summary of environments and cluster statistics.

        Args:
            summary_data: Dictionary containing summary statistics
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        if summary_data['total_clusters'] == 0:
            self.console.print(f"[{panel_styles.get('warning', 'yellow')}]No clusters configured.[/{panel_styles.get('warning', 'yellow')}]")
            return

        # Create summary table
        summary_table = Table.grid(padding=(0, 3))
        summary_table.add_column(style=panel_styles.get('title', 'cyan'), no_wrap=True, min_width=20)
        summary_table.add_column(style=panel_styles.get('info', 'white'))

        summary_table.add_row("Total Environments:", str(summary_data['total_environments']))
        summary_table.add_row("Total Clusters:", str(summary_data['total_clusters']))
        summary_table.add_row("SSL Enabled:", f"{summary_data['ssl_enabled_count']}/{summary_data['total_clusters']}")
        summary_table.add_row("Cert Verification:", f"{summary_data['cert_verification_count']}/{summary_data['total_clusters']}")

        if summary_data.get('default_cluster'):
            summary_table.add_row("Default Cluster:", f"{summary_data['default_cluster']} ★")

        # Add environment breakdown
        summary_table.add_row("", "")  # Spacer
        summary_table.add_row("Environment Breakdown:", "")

        for env_name, env_info in summary_data['environments'].items():
            summary_table.add_row(f"  └─ {env_name.upper()}:", f"{env_info['cluster_count']} clusters")

        panel = Panel(
            summary_table,
            title="📊 Cluster Summary",
            border_style=panel_styles.get('secondary', 'cyan'),
            padding=(1, 2)
        )

        self.console.print(panel)

    def render_locations_list(self, locations_data, simple=False, styles=None):
        """
        Render a simple list of locations.

        Args:
            locations_data: Dictionary containing location information
            simple: If True, render minimal format
            styles: Theme styles dictionary (optional)
        """
        if not locations_data.get('has_locations'):
            self.console.print("[yellow]No locations configured.[/yellow]")
            return

        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        if simple:
            # Simple list format
            for env_name in locations_data['environment_names']:
                env_data = locations_data['environments'][env_name]
                self.console.print(f"[bold]{env_name.upper()}:[/bold]")
                for server in env_data['servers']:
                    marker = " ★" if server['is_default'] else ""
                    self.console.print(f"  • {server['location']}{marker}")
        else:
            # Formatted list with details
            for env_name in locations_data['environment_names']:
                env_data = locations_data['environments'][env_name]

                env_text = Text(f"🌍 {env_name.upper()}", style=panel_styles.get('success', 'bold green'))
                self.console.print(env_text)

                for server in env_data['servers']:
                    marker = " ★" if server['is_default'] else ""
                    ssl_indicator = " 🔒" if server['use_ssl'] else ""

                    server_text = Text(f"  📍 {server['location']}{marker}")
                    server_text.append(f" → {server['hostname']}:{server['port']}{ssl_indicator}",
                                     style=panel_styles.get('subtitle', 'dim'))
                    self.console.print(server_text)

    def render_search_results(self, search_results, search_term, styles=None):
        """
        Render search results for locations.

        Args:
            search_results: List of matching locations
            search_term: The search term used
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        if not search_results:
            self.console.print(f"[{panel_styles.get('warning', 'yellow')}]No locations found matching '{search_term}'[/{panel_styles.get('warning', 'yellow')}]")
            return

        # Create search results table
        results_table = Table(
            title=f"🔍 Search Results for '{search_term}'",
            title_style=panel_styles.get('title', 'bold cyan'),
            border_style=panel_styles.get('secondary', 'cyan'),
            show_header=True,
            header_style=panel_styles.get('title', 'bold cyan')
        )

        results_table.add_column("Location", style=panel_styles.get('title', 'cyan'))
        results_table.add_column("Environment", style=panel_styles.get('success', 'green'))
        results_table.add_column("Hostname", style=panel_styles.get('info', 'white'))
        results_table.add_column("Match", style=panel_styles.get('subtitle', 'dim'))

        for result in search_results:
            results_table.add_row(
                result['location'],
                result['environment'].upper(),
                result['hostname'],
                result['match_reason'].title()
            )

        self.console.print(results_table)

    def render_json_locations(self, locations_data):
        """
        Render locations information in JSON format.

        Args:
            locations_data: Dictionary containing location information
        """
        # Convert to JSON-friendly format
        json_data = {
            'total_environments': locations_data.get('total_environments', 0),
            'total_servers': locations_data.get('total_servers', 0),
            'default_cluster': locations_data.get('default_cluster'),
            'environments': {}
        }

        if locations_data.get('has_locations'):
            for env_name, env_data in locations_data['environments'].items():
                json_data['environments'][env_name] = {
                    'server_count': env_data['server_count'],
                    'servers': []
                }

                for server in env_data['servers']:
                    server_json = {
                        'location': server['location'],
                        'hostname': server['hostname'],
                        'hostname2': server['hostname2'],
                        'port': server['port'],
                        'use_ssl': server['use_ssl'],
                        'verify_certs': server['verify_certs'],
                        'username': server['username'],
                        'is_default': server['is_default']
                    }
                    json_data['environments'][env_name]['servers'].append(server_json)

        self.console.print_json(json.dumps(json_data, indent=2))

    def _create_locations_table(self, styles, panel_styles):
        """Create the main locations table with proper styling."""
        from display.style_system import StyleSystem
        ss = StyleSystem(self.theme_manager)

        # Map theme table_box setting to Rich box styles
        table_box_mapping = {
            'heavy': box.HEAVY,
            'rounded': box.ROUNDED,
            'simple': box.SIMPLE,
            'double': box.DOUBLE,
            'None': None,
            None: None
        }

        theme_box = styles.get('table_box')
        table_box = table_box_mapping.get(theme_box, box.ROUNDED)

        zebra = ss.get_zebra_style(1) or "on grey11"

        locations_table = Table(
            title="🌐 Elasticsearch Configured Clusters by Environment",
            title_style=styles.get('header_style', 'bold white'),
            border_style=styles.get('border_style', 'white'),
            box=table_box,
            expand=True,
        )

        # Add columns with theme styling
        locations_table.add_column("Environment", justify="left",
                                 style=panel_styles.get('success', 'bold green'),
                                 no_wrap=True, width=12)
        locations_table.add_column("Name", justify="left",
                                 style=panel_styles.get('title', 'cyan'),
                                 no_wrap=True, width=15)
        locations_table.add_column("Hostname", justify="left",
                                 style=panel_styles.get('info', 'white'), width=20)
        locations_table.add_column("Hostname2", justify="left",
                                 style=panel_styles.get('subtitle', 'dim white'), width=20)
        locations_table.add_column("Port", justify="center",
                                 style=panel_styles.get('success', 'green'), width=6)
        locations_table.add_column("SSL", justify="center",
                                 style=panel_styles.get('secondary', 'magenta'), width=6)
        locations_table.add_column("Verify", justify="center",
                                 style=panel_styles.get('secondary', 'magenta'), width=7)
        locations_table.add_column("Username", justify="left",
                                 style=panel_styles.get('warning', 'yellow'), width=25)

        return locations_table

    def _populate_locations_table(self, locations_table, locations_data, panel_styles):
        """Populate the locations table with data."""
        from display.style_system import StyleSystem
        zebra = StyleSystem(self.theme_manager).get_zebra_style(1) or "on grey11"
        zebra_styles = ["", zebra]

        for env_idx, env_name in enumerate(locations_data['environment_names']):
            env_data = locations_data['environments'][env_name]
            row_style = zebra_styles[env_idx % 2]
            env_displayed = False

            for server in env_data['servers']:
                # Display environment name only for the first server in each group
                env_display = env_name.upper() if not env_displayed else ""
                env_displayed = True

                # Add default marker to name
                if server['is_default']:
                    name_display = Text(f"{server['location']} ", style=panel_styles.get('title', 'cyan'))
                    name_display.append("★", style=panel_styles.get('success', 'bold green'))
                else:
                    name_display = Text(server['location'], style=panel_styles.get('title', 'cyan'))

                # Format boolean values for better readability
                use_ssl = "✓" if server['use_ssl'] else "✗"
                verify_certs = "✓" if server['verify_certs'] else "✗"

                # Color code SSL and verification status
                ssl_style = panel_styles.get('success', 'green') if server['use_ssl'] else panel_styles.get('error', 'red')
                verify_style = panel_styles.get('success', 'green') if server['verify_certs'] else panel_styles.get('error', 'red')

                locations_table.add_row(
                    Text(env_display, style=panel_styles.get('success', 'bold green')),
                    name_display,
                    server['hostname'],
                    server['hostname2'],
                    str(server['port']),
                    Text(use_ssl, style=ssl_style),
                    Text(verify_certs, style=verify_style),
                    server['username'],
                    style=row_style,
                )

    def _create_summary_text(self, locations_data):
        """Create summary text for the panel title."""
        env_count = locations_data['total_environments']
        server_count = locations_data['total_servers']
        default_cluster = locations_data.get('default_cluster')

        summary_text = f"📊 {env_count} environments • {server_count} clusters configured"
        if default_cluster:
            summary_text += f" • Default: {default_cluster} ★"

        return summary_text

    def _render_no_locations(self, locations_data, styles):
        """Render message when no locations are configured."""
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        warning_style = panel_styles.get('warning', 'yellow')
        error_message = locations_data.get('error', 'No cluster configurations found.')

        self.console.print(f"[{warning_style}]{error_message}[/{warning_style}]")

    def _render_location_not_found(self, location_details, panel_styles):
        """Render error message for location not found."""
        error_style = panel_styles.get('error', 'red')
        self.console.print(f"[{error_style}]{location_details.get('error', 'Location not found')}[/{error_style}]")

    def _get_default_styles(self):
        """Get default styling when no theme is available."""
        return {
            'header_style': 'bold white',
            'border_style': 'white',
            'table_box': 'rounded',
            'panel_styles': {
                'title': 'cyan',
                'info': 'white',
                'success': 'green',
                'warning': 'yellow',
                'error': 'red',
                'secondary': 'magenta',
                'subtitle': 'dim white'
            }
        }
