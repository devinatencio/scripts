"""
Settings renderer for ESCMD.

This module handles all display logic for configuration settings information,
extracting the presentation layer from command handlers for better
separation of concerns.
"""

import json
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


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

        # Initialise style system if available
        self.style_system = None
        try:
            from display.style_system import StyleSystem
            if theme_manager:
                self.style_system = StyleSystem(theme_manager)
        except ImportError:
            pass

    # ------------------------------------------------------------------ #
    # Theme helpers (same pattern as ILMRenderer / SnapshotRenderer)      #
    # ------------------------------------------------------------------ #

    def _border(self, fallback: str = "cyan") -> str:
        """Return the theme border style."""
        if self.theme_manager:
            return self.theme_manager.get_theme_styles().get("border_style", fallback)
        return fallback

    def _title_style(self, fallback: str = "bold white") -> str:
        """Return the theme panel title style."""
        if self.theme_manager:
            return self.theme_manager.get_themed_style("panel_styles", "title", fallback)
        return fallback

    def _sem(self, semantic: str, fallback: str = "white") -> str:
        """Return a semantic style from the style system."""
        if self.style_system:
            return self.style_system.get_semantic_style(semantic)
        defaults = {
            "success":   "bold green",
            "warning":   "bold yellow",
            "error":     "bold red",
            "info":      "cyan",
            "primary":   "bold cyan",
            "secondary": "magenta",
            "neutral":   "white",
            "muted":     "dim white",
        }
        return defaults.get(semantic, fallback)

    def _fmt_value(self, value) -> Text:
        """Format a setting value with semantic colour."""
        if value is None:
            return Text("null", style="dim italic")
        if isinstance(value, bool):
            return Text(str(value).lower(), style=self._sem("success") if value else self._sem("muted"))
        if isinstance(value, (int, float)):
            return Text(str(value), style=self._sem("info"))
        return Text(str(value), style=self._sem("neutral"))

    # ------------------------------------------------------------------ #
    # Public entry point                                                   #
    # ------------------------------------------------------------------ #

    def render_settings_overview(self, settings_data, styles=None):
        """
        Render complete settings overview with all sections.
        """
        # --- Title panel (standard pattern) ---
        default_cluster = settings_data.get('default_cluster')
        num_settings = len(settings_data.get('settings', {}))
        num_clusters = len(settings_data.get('clusters', [])) if settings_data.get('has_clusters') else 0

        subtitle_rich = Text()
        subtitle_rich.append("Default: ", style="default")
        if default_cluster:
            subtitle_rich.append(default_cluster, style=self._sem("success"))
        else:
            subtitle_rich.append("None", style=self._sem("warning"))
        subtitle_rich.append(" | Settings: ", style="default")
        subtitle_rich.append(str(num_settings), style=self._sem("info"))
        subtitle_rich.append(" | Clusters: ", style="default")
        subtitle_rich.append(str(num_clusters), style=self._sem("primary"))

        if default_cluster:
            status_text = f"✅ Connected to {default_cluster}"
            body_style = "bold green"
        else:
            status_text = "🔶 No Default Cluster Configured"
            body_style = "bold yellow"

        ts = self._sem("primary")
        title_panel = Panel(
            Text(status_text, style=body_style, justify="center"),
            title=f"[{ts}]🔩 escmd Configuration[/{ts}]",
            subtitle=subtitle_rich,
            border_style=self._border(),
            padding=(1, 2)
        )

        self.console.print()
        self.console.print(title_panel)
        self.console.print()

        self.render_settings_table(settings_data)
        self.console.print()

        if settings_data.get('username_configuration'):
            self.render_username_configuration(settings_data)
            self.console.print()

        if settings_data.get('has_clusters'):
            self.render_clusters_table(settings_data)
            self.console.print()

            auth_clusters = [a for a in settings_data['authentication'] if a['has_auth']]
            if auth_clusters:
                self.render_authentication_table(settings_data)
                self.console.print()

        self.render_file_info(settings_data)

    # ------------------------------------------------------------------ #
    # Settings table                                                       #
    # ------------------------------------------------------------------ #

    def render_settings_table(self, settings_data, styles=None):
        """Render the main configuration settings table."""
        border = self._border()
        title  = self._title_style()

        table = Table(
            show_header=True,
            header_style=title,
            border_style=border,
            expand=True,
            box=box.SIMPLE_HEAD,
        )
        table.add_column("Setting",     style=self._sem("primary"),  no_wrap=True)
        table.add_column("Value",       style=self._sem("neutral"))
        table.add_column("Description", style=self._sem("muted"))

        # Default cluster row
        default_cluster = settings_data.get('default_cluster')
        table.add_row(
            "Default Server",
            Text(default_cluster or "None", style=self._sem("success") if default_cluster else self._sem("warning")),
            "Currently active cluster",
        )

        descriptions = self._get_setting_descriptions()
        for key, value in settings_data.get('settings', {}).items():
            if key == 'dangling_cleanup' and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    full_key = f"dangling_cleanup.{sub_key}"
                    table.add_row(full_key, self._fmt_value(sub_value), descriptions.get(full_key, ""))
            else:
                table.add_row(key, self._fmt_value(value), descriptions.get(key, "Configuration setting"))

        for override_key, info in settings_data.get('environment_overrides', {}).items():
            table.add_row(
                f"{override_key} (override)",
                Text(info['value'], style=self._sem("warning")),
                f"Env var {info['variable']} active",
            )

        self.console.print(Panel(
            table,
            title=f"[{title}]📋 Configuration Settings[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))

    # ------------------------------------------------------------------ #
    # Clusters table                                                       #
    # ------------------------------------------------------------------ #

    def render_clusters_table(self, settings_data, styles=None):
        """Render the clusters summary table."""
        clusters = settings_data.get('clusters', [])
        if not clusters:
            return

        border = self._border()
        title  = self._title_style()

        table = Table(
            show_header=True,
            header_style=title,
            border_style=border,
            expand=True,
            box=box.SIMPLE_HEAD,
        )
        table.add_column("Name",         style=self._sem("primary"),    no_wrap=True)
        table.add_column("Environment",  style=self._sem("secondary"),  no_wrap=True)
        table.add_column("Primary Host", style=self._sem("neutral"))
        table.add_column("Port",         style=self._sem("info"),        justify="right")
        table.add_column("SSL",          style=self._sem("warning"),     justify="center")
        table.add_column("Auth",         style=self._sem("error"),       justify="center")

        for cluster in clusters:
            name = (
                Text(f"★ {cluster['name']}", style=self._sem("success"))
                if cluster['is_default']
                else Text(cluster['name'], style=self._sem("neutral"))
            )
            ssl_text  = Text("✓", style=self._sem("success")) if cluster['use_ssl']            else Text("✗", style=self._sem("muted"))
            auth_text = Text("✓", style=self._sem("success")) if cluster['has_authentication'] else Text("✗", style=self._sem("muted"))

            table.add_row(name, cluster['environment'], cluster['hostname'], str(cluster['port']), ssl_text, auth_text)

        self.console.print(Panel(
            table,
            title=f"[{title}]🌐 Cluster Directory ({len(clusters)} configured)[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))

    # ------------------------------------------------------------------ #
    # Authentication table                                                 #
    # ------------------------------------------------------------------ #

    def render_authentication_table(self, settings_data, styles=None):
        """Render the authentication configuration table."""
        auth_data = [a for a in settings_data.get('authentication', []) if a['has_auth']]
        if not auth_data:
            return

        border = self._border()
        title  = self._title_style()

        table = Table(
            show_header=True,
            header_style=title,
            border_style=border,
            expand=True,
            box=box.SIMPLE_HEAD,
        )
        table.add_column("Cluster",         style=self._sem("primary"),    no_wrap=True)
        table.add_column("Username Source", style=self._sem("neutral"))
        table.add_column("Username",        style=self._sem("secondary"))
        table.add_column("Password Source", style=self._sem("warning"))

        for auth in auth_data:
            cluster_name = (
                Text(f"★ {auth['cluster_name']}", style=self._sem("success"))
                if auth['is_default']
                else Text(auth['cluster_name'], style=self._sem("neutral"))
            )
            table.add_row(cluster_name, auth['username_source'], auth['username'], auth['password_source'])

        self.console.print(Panel(
            table,
            title=f"[{title}]🔐 Authentication Configuration[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))

    # ------------------------------------------------------------------ #
    # Username configuration                                               #
    # ------------------------------------------------------------------ #

    def render_username_configuration(self, settings_data, styles=None):
        """Render the username configuration section."""
        username_data = settings_data.get('username_configuration', {})
        if not username_data:
            return

        border = self._border()
        title  = self._title_style()

        # Current resolution table
        config_table = Table(show_header=True, header_style=title, box=box.SIMPLE_HEAD, expand=True)
        config_table.add_column("Setting",  style=self._sem("primary"),   no_wrap=True, width=22)
        config_table.add_column("Value",    style=self._sem("neutral"),   width=28)
        config_table.add_column("Status",   style=self._sem("secondary"))

        resolved     = username_data.get('resolved_username')
        active_source = username_data.get('active_source')
        status_text  = (
            Text(f"✅ Active ({active_source})", style=self._sem("success"))
            if resolved
            else Text("❌ Not configured", style=self._sem("error"))
        )
        config_table.add_row("Resolved Username", resolved or Text("Not set", style="dim"), status_text)

        json_u = username_data.get('json_username')
        config_table.add_row(
            "JSON Config",
            json_u or Text("Not set", style="dim"),
            "🎯 3rd Priority" if json_u else Text("Not configured", style="dim"),
        )

        global_u = username_data.get('global_username')
        config_table.add_row(
            "Global Config",
            global_u or Text("Not set", style="dim"),
            "📁 4th Priority" if global_u else Text("Not configured", style="dim"),
        )

        # Priority order table
        priority_table = Table(show_header=True, header_style=title, box=box.SIMPLE_HEAD, expand=True)
        priority_table.add_column("Priority",    style=self._sem("warning"),   width=9)
        priority_table.add_column("Source",      style=self._sem("primary"),   width=22)
        priority_table.add_column("Description", style=self._sem("neutral"))
        priority_table.add_column("Status",      style=self._sem("secondary"), width=16)

        for p in username_data.get('priority_order', []):
            description = p['description']
            if p.get('active'):
                st = Text("🎯 Active", style=self._sem("success"))
            elif p.get('configured'):
                val = p.get('value')
                if val:
                    description += f" ({val})"
                st = Text("✅ Set", style=self._sem("info"))
            else:
                st = Text("Not set", style="dim")

            priority_table.add_row(str(p['level']), p['source'], description, st)

        self.console.print(Panel(
            Group(config_table, Text(""), priority_table),
            title=f"[{title}]🔑 Username Configuration[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))

    # ------------------------------------------------------------------ #
    # File info                                                            #
    # ------------------------------------------------------------------ #

    def render_file_info(self, settings_data, styles=None):
        """Render configuration file information as a panel."""
        files = settings_data.get('configuration_files', {}).get('files', [])
        if not files:
            return

        border = self._border("dim")
        title  = self._title_style()

        table = Table.grid(padding=(0, 3))
        table.add_column(style=self._sem("primary"),  no_wrap=True)
        table.add_column(style=self._sem("neutral"))
        table.add_column(style=self._sem("muted"))

        for f in files:
            icon = "💾" if f['type'] == 'State File' else ("📂" if "Servers" in f['type'] else "📄")
            status_style = self._sem("success") if f['exists'] else self._sem("error")
            table.add_row(f"{icon} {f['type']}", f['path'], Text(f['status'], style=status_style))

        self.console.print(Panel(
            table,
            title=f"[{title}]📁 Configuration Files[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))

    # ------------------------------------------------------------------ #
    # Security / validation / summary / JSON  (unchanged logic, updated   #
    # to use theme helpers)                                                #
    # ------------------------------------------------------------------ #

    def render_security_analysis(self, settings_data, security_analysis, styles=None):
        """Render security posture analysis."""
        border = self._border()
        title  = self._title_style()

        table = Table.grid(padding=(0, 3))
        table.add_column(style=self._sem("primary"),  no_wrap=True, min_width=20)
        table.add_column(style=self._sem("neutral"))

        total = security_analysis['total_clusters']
        table.add_row("Total Clusters:",   str(total))
        table.add_row("SSL Enabled:",      f"{security_analysis['ssl_enabled']}/{total}")
        table.add_row("SSL Verified:",     f"{security_analysis['ssl_verified']}/{total}")
        table.add_row("Auth Enabled:",     f"{security_analysis['auth_enabled']}/{total}")
        table.add_row("Secure Passwords:", f"{security_analysis['secure_passwords']}/{security_analysis['auth_enabled']}")

        score = security_analysis['security_score']
        score_style = self._sem("success") if score >= 80 else (self._sem("warning") if score >= 60 else self._sem("error"))
        table.add_row("Security Score:", Text(f"{score}/100", style=score_style))

        if security_analysis['recommendations']:
            table.add_row("", "")
            table.add_row("Recommendations:", "")
            for rec in security_analysis['recommendations']:
                table.add_row("", f"• {rec}")

        self.console.print(Panel(
            table,
            title=f"[{title}]🔐 Security Analysis[/{title}]",
            border_style=border,
            padding=(1, 2),
        ))

    def render_validation_results(self, validation_results, styles=None):
        """Render configuration validation results."""
        border = self._border()
        title  = self._title_style()

        status       = "✅ Valid" if validation_results['is_valid'] else "❌ Invalid"
        status_style = self._sem("success") if validation_results['is_valid'] else self._sem("error")

        table = Table.grid(padding=(0, 3))
        table.add_column(style=self._sem("primary"),  no_wrap=True, min_width=15)
        table.add_column(style=self._sem("neutral"))

        table.add_row("Status:", Text(status, style=status_style))
        table.add_row("Score:",  f"{validation_results['score']}/100")

        for error in validation_results.get('errors', []):
            table.add_row("", Text(f"❌ {error}", style=self._sem("error")))

        if validation_results.get('warnings'):
            table.add_row("", "")
            table.add_row("Warnings:", "")
            for warning in validation_results['warnings']:
                table.add_row("", Text(f"🔶 {warning}", style=self._sem("warning")))

        if validation_results.get('info'):
            table.add_row("", "")
            table.add_row("Info:", "")
            for info in validation_results['info']:
                table.add_row("", Text(f"🔵 {info}", style=self._sem("info")))

        self.console.print(Panel(
            table,
            title=f"[{title}]✅ Configuration Validation[/{title}]",
            border_style=border,
            padding=(1, 2),
        ))

    def render_settings_summary(self, settings_data, styles=None):
        """Render a compact settings summary."""
        border = self._border()
        title  = self._title_style()

        table = Table.grid(padding=(0, 3))
        table.add_column(style=self._sem("primary"),  no_wrap=True, min_width=15)
        table.add_column(style=self._sem("neutral"))

        table.add_row("Default Cluster:", settings_data.get('default_cluster', 'None'))
        table.add_row("Total Clusters:",  str(settings_data.get('total_clusters', 0)))

        file_info = settings_data.get('configuration_files', {})
        table.add_row("Config Mode:", "Dual File" if file_info.get('is_dual_file_mode') else "Single File")

        overrides = settings_data.get('environment_overrides', {})
        if overrides:
            table.add_row("Env Overrides:", str(len(overrides)))

        self.console.print(Panel(
            table,
            title=f"[{title}]📋 Settings Summary[/{title}]",
            border_style=border,
            padding=(1, 2),
        ))

    def render_json_settings(self, settings_data):
        """Render settings information in JSON format."""
        json_output = {
            'default_server': settings_data.get('default_cluster'),
            'settings':       settings_data.get('settings', {}),
            'servers':        {c['name']: c['raw_config'] for c in settings_data.get('clusters', [])},
        }
        self.console.print_json(json.dumps(json_output, indent=2))

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_setting_descriptions(self):
        """Get descriptions for configuration settings."""
        return {
            'box_style':                          'Rich table border style',
            'health_style':                       'Health command display mode',
            'classic_style':                      'Classic health display format',
            'enable_paging':                      'Auto-enable pager for long output',
            'paging_threshold':                   'Line count threshold for paging',
            'ilm_display_limit':                  'Max ILM unmanaged indices to show before truncating',
            'show_legend_panels':                 'Show legend panels in output',
            'ascii_mode':                         'Use plain text instead of Unicode',
            'display_theme':                      'Color theme (rich/plain) for universal compatibility',
            'connection_timeout':                 'ES connection timeout (seconds)',
            'read_timeout':                       'ES read timeout (seconds)',
            'flush_timeout':                      'ES flush command HTTP timeout (seconds)',
            'dangling_cleanup.max_retries':       'Max retries for dangling operations',
            'dangling_cleanup.retry_delay':       'Delay between retries (seconds)',
            'dangling_cleanup.timeout':           'Operation timeout (seconds)',
            'dangling_cleanup.default_log_level': 'Default logging level',
            'dangling_cleanup.enable_progress_bar':   'Show progress bars',
            'dangling_cleanup.confirmation_required': 'Require user confirmation',
        }

    def _get_default_styles(self):
        """Kept for backward compatibility — no longer used internally."""
        return {
            'header_style': 'bold white',
            'border_style': 'white',
            'panel_styles': {
                'title':    'cyan',
                'info':     'white',
                'success':  'green',
                'warning':  'yellow',
                'error':    'red',
                'secondary':'magenta',
                'subtitle': 'dim white',
            },
        }
