"""
Settings renderer for ESCMD.

This module handles all display logic for configuration settings information,
extracting the presentation layer from command handlers for better
separation of concerns.
"""

import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


class SettingsRenderer:
    """Handles rendering of configuration settings with rich formatting."""

    def __init__(self, console=None, theme_manager=None):
        """
        Initialize the settings renderer.

        Args:
            console: Rich Console instance (creates new one if None)
            theme_manager: Theme manager for styling (optional)
        """
        self.console = console or Console()
        self.theme_manager = theme_manager

    def render_settings_overview(self, settings_data, styles=None):
        """
        Render complete settings overview with all sections.

        Args:
            settings_data: Dictionary containing settings information
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()

        # Render main settings table
        self.render_settings_table(settings_data, styles)
        self.console.print()

        # Render username configuration section
        if settings_data.get('username_configuration'):
            self.render_username_configuration(settings_data, styles)
            self.console.print()

        # Render clusters if any exist
        if settings_data.get('has_clusters'):
            self.render_clusters_table(settings_data, styles)
            self.console.print()

            # Render authentication info if there are auth-enabled clusters
            auth_clusters = [auth for auth in settings_data['authentication'] if auth['has_auth']]
            if auth_clusters:
                self.render_authentication_table(settings_data, styles)
                self.console.print()

        # Render configuration file info
        self.render_file_info(settings_data, styles)

    def render_settings_table(self, settings_data, styles=None):
        """
        Render the main configuration settings table.

        Args:
            settings_data: Dictionary containing settings information
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        # Main Settings Table
        settings_table = Table(
            title="🔩 Configuration Settings",
            title_style=styles.get('header_style', 'bold white'),
            border_style=styles.get('border_style', 'white'),
            expand=True
        )
        settings_table.add_column("Setting", style=panel_styles.get('title', 'cyan'), no_wrap=True)
        settings_table.add_column("Value", style=panel_styles.get('info', 'white'))
        settings_table.add_column("Description", style=panel_styles.get('subtitle', 'dim white'))

        # Add default server info
        default_cluster = settings_data.get('default_cluster')
        default_value = Text(
            default_cluster or "None",
            style=panel_styles.get('success' if default_cluster else 'warning',
                                  'green' if default_cluster else 'yellow')
        )
        settings_table.add_row(
            "Default Server",
            default_value,
            "Currently active cluster"
        )

        # Add all settings
        setting_descriptions = self._get_setting_descriptions()
        settings = settings_data.get('settings', {})

        for key, value in settings.items():
            if key == 'dangling_cleanup':
                # Special handling for nested dangling_cleanup settings
                for sub_key, sub_value in value.items():
                    setting_name = f"dangling_cleanup.{sub_key}"
                    description = setting_descriptions.get(setting_name, 'Dangling cleanup setting')
                    settings_table.add_row(setting_name, str(sub_value), description)
            else:
                description = setting_descriptions.get(key, 'Configuration setting')
                settings_table.add_row(key, str(value), description)

        # Add environment overrides
        overrides = settings_data.get('environment_overrides', {})
        for override_key, override_info in overrides.items():
            override_value = Text(override_info['value'], style=panel_styles.get('warning', 'yellow'))
            settings_table.add_row(
                f"{override_key} (override)",
                override_value,
                f"Environment variable {override_info['variable']} active"
            )

        # Wrap in panel
        settings_panel = Panel(
            settings_table,
            title="📋 Configuration Settings",
            title_align="left",
            border_style=styles.get('border_style', 'white'),
            padding=(1, 2)
        )

        self.console.print(settings_panel)

    def render_clusters_table(self, settings_data, styles=None):
        """
        Render the clusters summary table.

        Args:
            settings_data: Dictionary containing settings information
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        clusters = settings_data.get('clusters', [])
        if not clusters:
            return

        # Clusters Summary Table
        clusters_table = Table(
            title=f"🌐 Configured Clusters ({len(clusters)} total)",
            title_style=styles.get('header_style', 'bold white'),
            border_style=styles.get('border_style', 'white'),
            expand=True
        )
        clusters_table.add_column("Name", style=panel_styles.get('title', 'cyan'), no_wrap=True)
        clusters_table.add_column("Environment", style=panel_styles.get('secondary', 'magenta'), no_wrap=True)
        clusters_table.add_column("Primary Host", style=panel_styles.get('info', 'white'))
        clusters_table.add_column("Port", style=panel_styles.get('success', 'green'), justify="right")
        clusters_table.add_column("SSL", style=panel_styles.get('warning', 'yellow'), justify="center")
        clusters_table.add_column("Auth", style=panel_styles.get('error', 'red'), justify="center")

        for cluster in clusters:
            # Add default marker to name if it's the default
            if cluster['is_default']:
                name_text = Text(f"{cluster['name']} 🏆", style=panel_styles.get('success', 'bold green'))
            else:
                name_text = Text(cluster['name'], style=panel_styles.get('info', 'white'))

            clusters_table.add_row(
                name_text,
                cluster['environment'],
                cluster['hostname'],
                str(cluster['port']),
                "Yes" if cluster['use_ssl'] else "No",
                "Yes" if cluster['has_authentication'] else "No"
            )

        # Wrap in panel
        clusters_panel = Panel(
            clusters_table,
            title=f"📂 Cluster Directory ({len(clusters)} configured)",
            title_align="left",
            border_style=styles.get('border_style', 'white'),
            padding=(1, 2)
        )

        self.console.print(clusters_panel)

    def render_authentication_table(self, settings_data, styles=None):
        """
        Render the authentication configuration table.

        Args:
            settings_data: Dictionary containing settings information
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        auth_data = settings_data.get('authentication', [])
        if not auth_data:
            return

        # Authentication Information Table
        auth_table = Table(
            title="🔐 Authentication Configuration",
            title_style=styles.get('header_style', 'bold white'),
            border_style=styles.get('border_style', 'white'),
            expand=True
        )
        auth_table.add_column("Cluster", style=panel_styles.get('title', 'cyan'), no_wrap=True)
        auth_table.add_column("Username Source", style=panel_styles.get('info', 'white'))
        auth_table.add_column("Username", style=panel_styles.get('secondary', 'magenta'))
        auth_table.add_column("Password Source", style=panel_styles.get('warning', 'yellow'))

        for auth in auth_data:
            # Color code the cluster name if it's the default
            if auth['is_default']:
                cluster_name = Text(f"{auth['cluster_name']} 🏆", style=panel_styles.get('success', 'bold green'))
            else:
                cluster_name = Text(auth['cluster_name'], style=panel_styles.get('info', 'white'))

            auth_table.add_row(
                cluster_name,
                auth['username_source'],
                auth['username'],
                auth['password_source']
            )

        # Wrap in panel
        auth_panel = Panel(
            auth_table,
            title="🔐 Authentication Configuration",
            title_align="left",
            border_style=styles.get('border_style', 'white'),
            padding=(1, 2)
        )

        self.console.print(auth_panel)

    def render_username_configuration(self, settings_data, styles=None):
        """
        Render the username configuration section.

        Args:
            settings_data: Dictionary containing settings information
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        username_data = settings_data.get('username_configuration', {})
        if not username_data:
            return

        from rich.table import Table
        from rich.text import Text
        from rich.panel import Panel

        # Current Username Configuration Table
        config_table = Table(
            title="🔑 Current Username Configuration",
            title_style=styles.get('header_style', 'bold white'),
            border_style=styles.get('border_style', 'white'),
            expand=True
        )
        config_table.add_column("Setting", style=panel_styles.get('title', 'cyan'), no_wrap=True, width=20)
        config_table.add_column("Value", style=panel_styles.get('info', 'white'), width=25)
        config_table.add_column("Status", style=panel_styles.get('secondary', 'magenta'))

        # Add current configuration rows
        resolved_username = username_data.get('resolved_username')
        active_source = username_data.get('active_source')

        if resolved_username:
            status_text = f"✅ Active ({active_source})"
            status_style = panel_styles.get('success', 'green')
        else:
            status_text = "❌ Not configured"
            status_style = panel_styles.get('error', 'red')

        config_table.add_row(
            "Resolved Username",
            resolved_username or Text("Not set", style="dim"),
            Text(status_text, style=status_style)
        )

        json_username = username_data.get('json_username')
        config_table.add_row(
            "JSON Config",
            json_username or Text("Not set", style="dim"),
            "🎯 3rd Priority" if json_username else Text("Not configured", style="dim")
        )

        global_username = username_data.get('global_username')
        config_table.add_row(
            "Global Config",
            global_username or Text("Not set", style="dim"),
            "📁 4th Priority" if global_username else Text("Not configured", style="dim")
        )

        # Priority Order Table
        priority_table = Table(
            title="🎯 Username Resolution Priority Order",
            title_style=styles.get('header_style', 'bold white'),
            border_style=styles.get('border_style', 'white'),
            expand=True
        )
        priority_table.add_column("Priority", style=panel_styles.get('warning', 'yellow'), width=8)
        priority_table.add_column("Source", style=panel_styles.get('title', 'cyan'), width=20)
        priority_table.add_column("Description", style=panel_styles.get('info', 'white'))
        priority_table.add_column("Status", style=panel_styles.get('secondary', 'magenta'), width=15)

        for priority_info in username_data.get('priority_order', []):
            level = priority_info['level']
            source = priority_info['source']
            description = priority_info['description']
            is_active = priority_info.get('active', False)
            is_configured = priority_info.get('configured', False)
            value = priority_info.get('value')

            # Determine status
            if is_active:
                status_text = f"🎯 Active"
                status_style = panel_styles.get('success', 'green')
            elif is_configured:
                status_text = f"✅ Set"
                status_style = panel_styles.get('info', 'white')
                if value:
                    description += f" ({value})"
            else:
                status_text = "Not set"
                status_style = "dim"

            priority_table.add_row(
                f"{level}",
                source,
                description,
                Text(status_text, style=status_style)
            )

        # Combine tables in a panel
        from rich.columns import Columns
        from rich.console import Group

        tables_group = Group(config_table, "", priority_table)

        username_panel = Panel(
            tables_group,
            title="🔑 Username Configuration",
            title_align="left",
            border_style=styles.get('border_style', 'white'),
            padding=(1, 2)
        )

        self.console.print(username_panel)

    def render_file_info(self, settings_data, styles=None):
        """
        Render configuration file information.

        Args:
            settings_data: Dictionary containing settings information
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})
        info_style = panel_styles.get('subtitle', 'dim white')

        file_info = settings_data.get('configuration_files', {})
        files = file_info.get('files', [])

        for file_data in files:
            icon = "📄" if file_data['type'] == 'Configuration' else "📂" if 'Servers' in file_data['type'] else "📄"
            self.console.print(f"[{info_style}]{icon} {file_data['type']}: {file_data['path']} ({file_data['status']})[/{info_style}]")

    def render_security_analysis(self, settings_data, security_analysis, styles=None):
        """
        Render security posture analysis.

        Args:
            settings_data: Dictionary containing settings information
            security_analysis: Security analysis results
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        # Security Analysis Table
        security_table = Table.grid(padding=(0, 3))
        security_table.add_column(style=panel_styles.get('title', 'cyan'), no_wrap=True, min_width=20)
        security_table.add_column(style=panel_styles.get('info', 'white'))

        security_table.add_row("Total Clusters:", str(security_analysis['total_clusters']))
        security_table.add_row("SSL Enabled:", f"{security_analysis['ssl_enabled']}/{security_analysis['total_clusters']}")
        security_table.add_row("SSL Verified:", f"{security_analysis['ssl_verified']}/{security_analysis['total_clusters']}")
        security_table.add_row("Auth Enabled:", f"{security_analysis['auth_enabled']}/{security_analysis['total_clusters']}")
        security_table.add_row("Secure Passwords:", f"{security_analysis['secure_passwords']}/{security_analysis['auth_enabled']}")

        # Security score with color coding
        score = security_analysis['security_score']
        if score >= 80:
            score_color = panel_styles.get('success', 'green')
        elif score >= 60:
            score_color = panel_styles.get('warning', 'yellow')
        else:
            score_color = panel_styles.get('error', 'red')

        score_text = Text(f"{score}/100", style=score_color)
        security_table.add_row("Security Score:", score_text)

        # Recommendations
        if security_analysis['recommendations']:
            security_table.add_row("", "")
            security_table.add_row("Recommendations:", "")
            for rec in security_analysis['recommendations']:
                security_table.add_row("", f"• {rec}")

        security_panel = Panel(
            security_table,
            title="🔐 Security Analysis",
            border_style=panel_styles.get('secondary', 'cyan'),
            padding=(1, 2)
        )

        self.console.print(security_panel)

    def render_validation_results(self, validation_results, styles=None):
        """
        Render configuration validation results.

        Args:
            validation_results: Validation results dictionary
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        # Validation status
        status = "✅ Valid" if validation_results['is_valid'] else "❌ Invalid"
        status_style = panel_styles.get('success', 'green') if validation_results['is_valid'] else panel_styles.get('error', 'red')

        validation_table = Table.grid(padding=(0, 3))
        validation_table.add_column(style=panel_styles.get('title', 'cyan'), no_wrap=True, min_width=15)
        validation_table.add_column(style=panel_styles.get('info', 'white'))

        validation_table.add_row("Status:", Text(status, style=status_style))
        validation_table.add_row("Score:", f"{validation_results['score']}/100")

        if validation_results['errors']:
            validation_table.add_row("", "")
            validation_table.add_row("Errors:", "")
            for error in validation_results['errors']:
                validation_table.add_row("", Text(f"❌ {error}", style=panel_styles.get('error', 'red')))

        if validation_results['warnings']:
            validation_table.add_row("", "")
            validation_table.add_row("Warnings:", "")
            for warning in validation_results['warnings']:
                validation_table.add_row("", Text(f"🔶 {warning}", style=panel_styles.get('warning', 'yellow')))

        if validation_results['info']:
            validation_table.add_row("", "")
            validation_table.add_row("Info:", "")
            for info in validation_results['info']:
                validation_table.add_row("", Text(f"🔵 {info}", style=panel_styles.get('info', 'blue')))

        validation_panel = Panel(
            validation_table,
            title="✅ Configuration Validation",
            border_style=panel_styles.get('secondary', 'cyan'),
            padding=(1, 2)
        )

        self.console.print(validation_panel)

    def render_settings_summary(self, settings_data, styles=None):
        """
        Render a compact settings summary.

        Args:
            settings_data: Dictionary containing settings information
            styles: Theme styles dictionary (optional)
        """
        styles = styles or self._get_default_styles()
        panel_styles = styles.get('panel_styles', {})

        summary_table = Table.grid(padding=(0, 3))
        summary_table.add_column(style=panel_styles.get('title', 'cyan'), no_wrap=True, min_width=15)
        summary_table.add_column(style=panel_styles.get('info', 'white'))

        # Key metrics
        summary_table.add_row("Default Cluster:", settings_data.get('default_cluster', 'None'))
        summary_table.add_row("Total Clusters:", str(settings_data.get('total_clusters', 0)))

        # File mode
        file_info = settings_data.get('configuration_files', {})
        mode = "Dual File" if file_info.get('is_dual_file_mode') else "Single File"
        summary_table.add_row("Config Mode:", mode)

        # Environment overrides
        overrides = settings_data.get('environment_overrides', {})
        if overrides:
            summary_table.add_row("Env Overrides:", str(len(overrides)))

        summary_panel = Panel(
            summary_table,
            title="📋 Settings Summary",
            border_style=panel_styles.get('secondary', 'cyan'),
            padding=(1, 2)
        )

        self.console.print(summary_panel)

    def render_json_settings(self, settings_data):
        """
        Render settings information in JSON format.

        Args:
            settings_data: Dictionary containing settings information
        """
        # Create JSON-friendly output
        json_output = {
            'default_server': settings_data.get('default_cluster'),
            'settings': settings_data.get('settings', {}),
            'servers': {}
        }

        # Add server information
        for cluster in settings_data.get('clusters', []):
            json_output['servers'][cluster['name']] = cluster['raw_config']

        self.console.print_json(json.dumps(json_output, indent=2))

    def _get_setting_descriptions(self):
        """Get descriptions for configuration settings."""
        return {
            'box_style': 'Rich table border style',
            'health_style': 'Health command display mode',
            'classic_style': 'Classic health display format',
            'enable_paging': 'Auto-enable pager for long output',
            'paging_threshold': 'Line count threshold for paging',
            'ilm_display_limit': 'Max ILM unmanaged indices to show before truncating',
            'show_legend_panels': 'Show legend panels in output',
            'ascii_mode': 'Use plain text instead of Unicode',
            'display_theme': 'Color theme (rich/plain) for universal compatibility',
            'connection_timeout': 'ES connection timeout (seconds)',
            'read_timeout': 'ES read timeout (seconds)',
            'flush_timeout': 'ES flush command HTTP timeout (seconds)',
            'dangling_cleanup.max_retries': 'Max retries for dangling operations',
            'dangling_cleanup.retry_delay': 'Delay between retries (seconds)',
            'dangling_cleanup.timeout': 'Operation timeout (seconds)',
            'dangling_cleanup.default_log_level': 'Default logging level',
            'dangling_cleanup.enable_progress_bar': 'Show progress bars',
            'dangling_cleanup.confirmation_required': 'Require user confirmation'
        }

    def _get_default_styles(self):
        """Get default styling when no theme is available."""
        return {
            'header_style': 'bold white',
            'border_style': 'white',
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
