#!/usr/bin/env python3
"""
Preview of the proposed beautified show-settings output.

Run with:  python demo/show_settings_preview.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich import box


# ---------------------------------------------------------------------------
# Minimal stub so StyleSystem / ThemeManager helpers work standalone
# ---------------------------------------------------------------------------

class _StubThemeManager:
    def get_theme_styles(self):
        return {"border_style": "cyan", "header_style": "bold white"}

    def get_themed_style(self, category, key, fallback="white"):
        mapping = {
            ("panel_styles", "title"):    "bold cyan",
            ("panel_styles", "success"):  "bold green",
            ("panel_styles", "warning"):  "bold yellow",
            ("panel_styles", "error"):    "bold red",
            ("panel_styles", "secondary"):"magenta",
            ("panel_styles", "subtitle"): "dim white",
            ("panel_styles", "info"):     "white",
        }
        return mapping.get((category, key), fallback)


class _StubStyleSystem:
    def get_semantic_style(self, semantic):
        return {
            "success":   "bold green",
            "warning":   "bold yellow",
            "error":     "bold red",
            "info":      "cyan",
            "primary":   "bold cyan",
            "secondary": "magenta",
            "neutral":   "white",
            "muted":     "dim white",
        }.get(semantic, "white")


# ---------------------------------------------------------------------------
# Proposed beautified SettingsRenderer
# ---------------------------------------------------------------------------

class BeautifiedSettingsRenderer:
    """Proposed beautified renderer — preview only."""

    def __init__(self, console=None, theme_manager=None):
        self.console = console or Console()
        self.theme_manager = theme_manager or _StubThemeManager()
        self.style_system = _StubStyleSystem()

    # -- theme helpers (same pattern as ILMRenderer / SnapshotRenderer) ----

    def _border(self, fallback: str = "cyan") -> str:
        return self.theme_manager.get_theme_styles().get("border_style", fallback)

    def _title_style(self, fallback: str = "bold white") -> str:
        return self.theme_manager.get_themed_style("panel_styles", "title", fallback)

    def _sem(self, semantic: str, fallback: str = "white") -> str:
        return self.style_system.get_semantic_style(semantic)

    # -- public entry point ------------------------------------------------

    def render_settings_overview(self, settings_data):
        self.console.print()
        self._render_settings_table(settings_data)
        self.console.print()

        if settings_data.get("username_configuration"):
            self._render_username_configuration(settings_data)
            self.console.print()

        if settings_data.get("has_clusters"):
            self._render_clusters_table(settings_data)
            self.console.print()

            auth_clusters = [a for a in settings_data["authentication"] if a["has_auth"]]
            if auth_clusters:
                self._render_authentication_table(settings_data)
                self.console.print()

        self._render_file_info(settings_data)
        self.console.print()

    # -- settings table ----------------------------------------------------

    def _render_settings_table(self, settings_data):
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
        default_cluster = settings_data.get("default_cluster")
        dc_style = self._sem("success") if default_cluster else self._sem("warning")
        table.add_row(
            "Default Server",
            Text(default_cluster or "None", style=dc_style),
            "Currently active cluster",
        )

        descriptions = _setting_descriptions()
        settings = settings_data.get("settings", {})

        for key, value in settings.items():
            if key == "dangling_cleanup" and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    full_key = f"dangling_cleanup.{sub_key}"
                    table.add_row(full_key, _fmt_value(sub_value, self), descriptions.get(full_key, ""))
            else:
                table.add_row(key, _fmt_value(value, self), descriptions.get(key, "Configuration setting"))

        # Environment overrides
        for override_key, info in settings_data.get("environment_overrides", {}).items():
            table.add_row(
                f"{override_key} (override)",
                Text(info["value"], style=self._sem("warning")),
                f"Env var {info['variable']} active",
            )

        self.console.print(Panel(
            table,
            title=f"[{title}]📋 Configuration Settings[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))

    # -- clusters table ----------------------------------------------------

    def _render_clusters_table(self, settings_data):
        clusters = settings_data.get("clusters", [])
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
        table.add_column("Name",         style=self._sem("primary"),   no_wrap=True)
        table.add_column("Environment",  style=self._sem("secondary"),  no_wrap=True)
        table.add_column("Primary Host", style=self._sem("neutral"))
        table.add_column("Port",         style=self._sem("info"),       justify="right")
        table.add_column("SSL",          style=self._sem("warning"),    justify="center")
        table.add_column("Auth",         style=self._sem("error"),      justify="center")

        for cluster in clusters:
            if cluster["is_default"]:
                name = Text(f"★ {cluster['name']}", style=self._sem("success"))
            else:
                name = Text(cluster["name"], style=self._sem("neutral"))

            ssl_text  = Text("✓", style=self._sem("success"))  if cluster["use_ssl"]            else Text("✗", style=self._sem("muted"))
            auth_text = Text("✓", style=self._sem("success"))  if cluster["has_authentication"] else Text("✗", style=self._sem("muted"))

            table.add_row(
                name,
                cluster["environment"],
                cluster["hostname"],
                str(cluster["port"]),
                ssl_text,
                auth_text,
            )

        self.console.print(Panel(
            table,
            title=f"[{title}]🌐 Cluster Directory ({len(clusters)} configured)[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))

    # -- authentication table ----------------------------------------------

    def _render_authentication_table(self, settings_data):
        auth_data = [a for a in settings_data.get("authentication", []) if a["has_auth"]]
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
        table.add_column("Cluster",         style=self._sem("primary"),   no_wrap=True)
        table.add_column("Username Source", style=self._sem("neutral"))
        table.add_column("Username",        style=self._sem("secondary"))
        table.add_column("Password Source", style=self._sem("warning"))

        for auth in auth_data:
            if auth["is_default"]:
                cluster_name = Text(f"★ {auth['cluster_name']}", style=self._sem("success"))
            else:
                cluster_name = Text(auth["cluster_name"], style=self._sem("neutral"))

            table.add_row(
                cluster_name,
                auth["username_source"],
                auth["username"],
                auth["password_source"],
            )

        self.console.print(Panel(
            table,
            title=f"[{title}]🔐 Authentication Configuration[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))

    # -- username configuration --------------------------------------------

    def _render_username_configuration(self, settings_data):
        username_data = settings_data.get("username_configuration", {})
        if not username_data:
            return

        border = self._border()
        title  = self._title_style()

        # Current resolution table
        config_table = Table(show_header=True, header_style=title, box=box.SIMPLE_HEAD, expand=True)
        config_table.add_column("Setting",  style=self._sem("primary"),   no_wrap=True, width=22)
        config_table.add_column("Value",    style=self._sem("neutral"),   width=28)
        config_table.add_column("Status",   style=self._sem("secondary"))

        resolved = username_data.get("resolved_username")
        source   = username_data.get("active_source")
        status_text  = Text(f"✅ Active ({source})", style=self._sem("success")) if resolved else Text("❌ Not configured", style=self._sem("error"))
        config_table.add_row("Resolved Username", resolved or Text("Not set", style="dim"), status_text)

        json_u = username_data.get("json_username")
        config_table.add_row("JSON Config",   json_u or Text("Not set", style="dim"), "🎯 3rd Priority" if json_u else Text("Not configured", style="dim"))

        global_u = username_data.get("global_username")
        config_table.add_row("Global Config", global_u or Text("Not set", style="dim"), "📁 4th Priority" if global_u else Text("Not configured", style="dim"))

        # Priority order table
        priority_table = Table(show_header=True, header_style=title, box=box.SIMPLE_HEAD, expand=True)
        priority_table.add_column("Priority",    style=self._sem("warning"),   width=9)
        priority_table.add_column("Source",      style=self._sem("primary"),   width=22)
        priority_table.add_column("Description", style=self._sem("neutral"))
        priority_table.add_column("Status",      style=self._sem("secondary"), width=16)

        for p in username_data.get("priority_order", []):
            if p.get("active"):
                st = Text("🎯 Active", style=self._sem("success"))
            elif p.get("configured"):
                val = p.get("value", "")
                desc = p["description"] + (f" ({val})" if val else "")
                p = dict(p); p["description"] = desc
                st = Text("✅ Set", style=self._sem("info"))
            else:
                st = Text("Not set", style="dim")

            priority_table.add_row(str(p["level"]), p["source"], p["description"], st)

        group = Group(config_table, Text(""), priority_table)
        self.console.print(Panel(
            group,
            title=f"[{title}]🔑 Username Configuration[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))

    # -- file info ---------------------------------------------------------

    def _render_file_info(self, settings_data):
        """Render config file info as a proper panel instead of raw text."""
        files = settings_data.get("configuration_files", {}).get("files", [])
        if not files:
            return

        border = self._border("dim")
        title  = self._title_style()

        table = Table.grid(padding=(0, 3))
        table.add_column(style=self._sem("primary"),  no_wrap=True)
        table.add_column(style=self._sem("neutral"))
        table.add_column(style=self._sem("muted"))

        for f in files:
            icon = "💾" if f["type"] == "State File" else ("📂" if "Servers" in f["type"] else "📄")
            status_style = self._sem("success") if f["exists"] else self._sem("error")
            table.add_row(
                f"{icon} {f['type']}",
                f["path"],
                Text(f["status"], style=status_style),
            )

        self.console.print(Panel(
            table,
            title=f"[{title}]📁 Configuration Files[/{title}]",
            title_align="left",
            border_style=border,
            padding=(1, 2),
        ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_value(value, renderer) -> Text:
    if value is None:
        return Text("null", style="dim italic")
    if isinstance(value, bool):
        return Text(str(value).lower(), style=renderer._sem("success") if value else renderer._sem("muted"))
    if isinstance(value, (int, float)):
        return Text(str(value), style=renderer._sem("info"))
    return Text(str(value), style=renderer._sem("neutral"))


def _setting_descriptions():
    return {
        "box_style":                        "Rich table border style",
        "health_style":                     "Health command display mode",
        "classic_style":                    "Classic health display format",
        "enable_paging":                    "Auto-enable pager for long output",
        "paging_threshold":                 "Line count threshold for paging",
        "ilm_display_limit":                "Max ILM unmanaged indices before truncating",
        "show_legend_panels":               "Show legend panels in output",
        "ascii_mode":                       "Use plain text instead of Unicode",
        "display_theme":                    "Color theme (rich/plain)",
        "connection_timeout":               "ES connection timeout (seconds)",
        "read_timeout":                     "ES read timeout (seconds)",
        "flush_timeout":                    "ES flush command HTTP timeout (seconds)",
        "dangling_cleanup.max_retries":     "Max retries for dangling operations",
        "dangling_cleanup.retry_delay":     "Delay between retries (seconds)",
        "dangling_cleanup.timeout":         "Operation timeout (seconds)",
        "dangling_cleanup.default_log_level": "Default logging level",
        "dangling_cleanup.enable_progress_bar": "Show progress bars",
        "dangling_cleanup.confirmation_required": "Require user confirmation",
    }


# ---------------------------------------------------------------------------
# Mock data (mirrors the real SettingsDataCollector output)
# ---------------------------------------------------------------------------

def _mock_settings_data():
    return {
        "default_cluster": "prod-primary",
        "has_clusters": True,
        "total_clusters": 3,
        "settings": {
            "health_style":       "dashboard",
            "classic_style":      "panel",
            "enable_paging":      False,
            "paging_threshold":   50,
            "ilm_display_limit":  50,
            "show_legend_panels": False,
            "ascii_mode":         False,
            "display_theme":      "rich",
            "connection_timeout": 30,
            "read_timeout":       120,
            "flush_timeout":      600,
            "dangling_cleanup": {
                "max_retries":           3,
                "retry_delay":           5,
                "timeout":               60,
                "default_log_level":     "INFO",
                "enable_progress_bar":   True,
                "confirmation_required": True,
            },
        },
        "clusters": [
            {
                "name": "prod-primary",
                "is_default": True,
                "environment": "production",
                "hostname": "es-prod-1.company.com",
                "port": 9200,
                "use_ssl": True,
                "verify_certs": True,
                "has_authentication": True,
            },
            {
                "name": "staging",
                "is_default": False,
                "environment": "staging",
                "hostname": "es-staging.company.com",
                "port": 9200,
                "use_ssl": True,
                "verify_certs": False,
                "has_authentication": True,
            },
            {
                "name": "dev-local",
                "is_default": False,
                "environment": "development",
                "hostname": "localhost",
                "port": 9200,
                "use_ssl": False,
                "verify_certs": False,
                "has_authentication": False,
            },
        ],
        "authentication": [
            {
                "cluster_name": "prod-primary",
                "is_default": True,
                "username_source": "Cluster Config",
                "username": "prod_user",
                "password_source": "Encrypted Storage",
                "password_status": "🔒 Encrypted",
                "password_secure": True,
                "has_auth": True,
            },
            {
                "cluster_name": "staging",
                "is_default": False,
                "username_source": "JSON Config",
                "username": "staging_user",
                "password_source": "Encrypted Storage",
                "password_status": "🔒 Encrypted",
                "password_secure": True,
                "has_auth": True,
            },
        ],
        "username_configuration": {
            "json_username":         "staging_user",
            "global_username":       None,
            "environment_username":  None,
            "resolved_username":     "prod_user",
            "active_source":         "Server Config",
            "is_configured":         True,
            "priority_order": [
                {"level": 1, "source": "Server-level Config",  "description": "Username defined in individual cluster config", "active": True,  "configured": True,  "value": "prod_user"},
                {"level": 2, "source": "Environment Config",   "description": "Username from environment-specific settings",   "active": False, "configured": False, "value": None},
                {"level": 3, "source": "JSON Config",          "description": "Username from state file",                      "active": False, "configured": True,  "value": "staging_user"},
                {"level": 4, "source": "Global Config",        "description": "Username from YAML configuration file",         "active": False, "configured": False, "value": None},
            ],
        },
        "configuration_files": {
            "is_dual_file_mode": True,
            "files": [
                {"type": "Main Config",    "path": "~/escmd.yml",            "exists": True,  "status": "✅ Found", "description": "Main configuration settings"},
                {"type": "Servers Config", "path": "~/elastic_servers.yml",  "exists": True,  "status": "✅ Found", "description": "Cluster server definitions"},
                {"type": "State File",     "path": "~/escmd.json",           "exists": True,  "status": "✅ Found", "description": "JSON credential / state store"},
            ],
        },
        "environment_overrides": {},
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    console = Console()
    renderer = BeautifiedSettingsRenderer(console=console)
    renderer.render_settings_overview(_mock_settings_data())
