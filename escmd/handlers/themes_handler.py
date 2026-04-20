"""
Themes handler for listing and previewing available themes.
"""

import os
import yaml
from handlers.base_handler import BaseHandler
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich.columns import Columns
from rich.markup import escape


class ThemesHandler(BaseHandler):
    """Handler for themes command."""

    def _load_theme_manager(self, config_manager):
        """Return (ThemeManager, StyleSystem) or (None, None)."""
        try:
            from display.theme_manager import ThemeManager
            from display.style_system import StyleSystem
            tm = ThemeManager(config_manager)
            ss = StyleSystem(tm)
            return tm, ss
        except Exception:
            return None, None

    def _theme_styles(self, tm, ss):
        """Extract the common style tokens from theme/style objects."""
        full_theme   = tm.get_full_theme_data() if tm else {}
        ts           = full_theme.get('table_styles', {})
        border       = ts.get('border_style',  'bright_blue')
        header       = ts.get('header_style',  'bold white on blue')
        title_style  = tm.get_themed_style('panel_styles', 'title',   'bold white') if tm else 'bold white'
        primary      = ss._get_style('semantic', 'primary',  'cyan')   if ss else 'cyan'
        success      = ss._get_style('semantic', 'success',  'green')  if ss else 'green'
        warning      = ss._get_style('semantic', 'warning',  'yellow') if ss else 'yellow'
        muted        = ss._get_style('semantic', 'muted',    'dim')    if ss else 'dim'
        box_style    = ss.get_table_box() if ss else None
        return border, header, title_style, primary, success, warning, muted, box_style

    def handle_themes(self):
        """Handle themes command - display all available themes with previews."""
        console = Console()

        from configuration_manager import ConfigurationManager
        config_manager = ConfigurationManager(
            self.config_file,
            os.path.join(os.path.dirname(self.config_file), 'escmd.json'),
        )
        tm, ss = self._load_theme_manager(config_manager)
        border, header, title_style, primary, success, warning, muted, box_style = \
            self._theme_styles(tm, ss)

        current_theme = config_manager.get_display_theme()

        # Load themes.yml
        themes_file = config_manager.default_settings.get('themes_file', 'themes.yml')
        if not os.path.isabs(themes_file):
            from utils import get_script_dir
            themes_file = os.path.join(get_script_dir(), themes_file)

        try:
            with open(themes_file, 'r') as f:
                themes_config = yaml.safe_load(f)
            available_themes = themes_config.get('themes', {})
        except (FileNotFoundError, yaml.YAMLError):
            available_themes = {}

        full_theme_data = tm.get_full_theme_data() if tm else {}
        if current_theme and current_theme not in available_themes:
            available_themes[current_theme] = full_theme_data

        theme_descriptions = {
            'rich':       'Colorful — optimized for dark terminals',
            'plain':      'Minimal — universal compatibility',
            'cyberpunk':  'High-contrast neon with bright colors',
            'ocean':      'Oceanic blues and cyan tones',
            'midnight':   'Dark theme with muted colors',
            'fire':       'Warm orange and red highlights',
            'nord':       'Arctic slate blues and muted greens',
            'solarized':  'Precision teal and warm tones',
        }

        if not available_themes:
            console.print(Panel(
                f"[{warning}]No themes found in themes.yml[/{warning}]",
                title=f"[{title_style}]🎨 Themes[/{title_style}]",
                border_style=warning,
                padding=(1, 2),
            ))
            return

        # Header panel
        console.print()
        console.print(Panel(
            Text.from_markup(
                f"[{primary}]{len(available_themes)} themes available[/{primary}]   "
                f"[{muted}]Active:[/{muted}] [{success}]{escape(current_theme or 'none')}[/{success}]\n\n"
                f"[{muted}]./escmd.py set-theme <name>   ./escmd.py set-theme <name> --preview[/{muted}]"
            ),
            title=f"[{title_style}]🎨 Color Themes[/{title_style}]",
            border_style=border,
            padding=(1, 3),
        ))
        console.print()

        # Theme cards — 2 per row
        theme_panels = []
        for theme_name, theme_data in available_themes.items():
            ts_t   = theme_data.get('table_styles', {})
            ps_t   = theme_data.get('panel_styles', {})
            is_active = theme_name == current_theme

            b_col  = ts_t.get('border_style', 'white')
            ok_col = ps_t.get('success', 'green')
            wn_col = ps_t.get('warning', 'yellow')
            er_col = ps_t.get('error', 'red')
            pr_col = ps_t.get('primary', ps_t.get('title', 'cyan'))

            swatch = Table(show_header=False, box=None, padding=(0, 1))
            swatch.add_column(style=f"bold {muted}", width=8,  no_wrap=True)
            swatch.add_column(width=12, no_wrap=True)
            swatch.add_column(width=20, no_wrap=True, style=muted)

            swatch.add_row("Border",  f"[{b_col}]██████████[/{b_col}]",  b_col)
            swatch.add_row("Primary", f"[{pr_col}]██████████[/{pr_col}]", pr_col)
            swatch.add_row("Success", f"[{ok_col}]██████████[/{ok_col}]", ok_col)
            swatch.add_row("Warning", f"[{wn_col}]██████████[/{wn_col}]", wn_col)
            swatch.add_row("Error",   f"[{er_col}]██████████[/{er_col}]", er_col)

            desc = theme_descriptions.get(theme_name, f"Custom theme")
            card_title = (
                f"[bold {ok_col}]🎯 {theme_name.upper()} ✔ active[/bold {ok_col}]"
                if is_active else
                f"[bold]{theme_name.upper()}[/bold]"
            )

            theme_panels.append(Panel(
                swatch,
                title=card_title,
                subtitle=f"[{muted}]{escape(desc)}[/{muted}]",
                border_style=b_col if is_active else muted,
                padding=(1, 2),
                expand=True,
            ))

        for i in range(0, len(theme_panels), 2):
            if i + 1 < len(theme_panels):
                console.print(Columns([theme_panels[i], theme_panels[i + 1]], expand=True))
            else:
                console.print(theme_panels[i])
            console.print()

        # Usage table
        usage = Table(show_header=False, box=None, padding=(0, 2))
        usage.add_column(style=f"bold {warning}", no_wrap=True, width=20)
        usage.add_column(style=primary)

        usage.add_row("Switch theme",   "./escmd.py set-theme <name>")
        usage.add_row("Preview first",  "./escmd.py set-theme <name> --preview")
        usage.add_row("Skip confirm",   "./escmd.py set-theme <name> --no-confirm")

        console.print(Panel(
            usage,
            title=f"[{title_style}]Usage[/{title_style}]",
            border_style=border,
            padding=(1, 2),
        ))
        console.print()

    def handle_set_theme(self):
        """Handle set-theme command - switch to a different theme."""
        console = Console()
        theme_name = self.args.theme_name
        preview    = getattr(self.args, 'preview', False)
        no_confirm = getattr(self.args, 'no_confirm', False)

        from configuration_manager import ConfigurationManager
        config_manager = ConfigurationManager(
            self.config_file,
            os.path.join(os.path.dirname(self.config_file), 'escmd.json'),
        )
        tm, ss = self._load_theme_manager(config_manager)
        border, header, title_style, primary, success, warning, muted, box_style = \
            self._theme_styles(tm, ss)

        themes_file = config_manager.default_settings.get('themes_file', 'themes.yml')
        if not os.path.isabs(themes_file):
            from utils import get_script_dir
            themes_file = os.path.join(get_script_dir(), themes_file)

        try:
            with open(themes_file, 'r') as f:
                themes_config = yaml.safe_load(f)
            available_themes = themes_config.get('themes', {})
        except (FileNotFoundError, yaml.YAMLError):
            console.print(Panel(
                f"[red]Could not load themes from [bold]{escape(themes_file)}[/bold][/red]",
                title=f"[{title_style}]❌ Set Theme[/{title_style}]",
                border_style="red",
                padding=(1, 2),
            ))
            return

        if theme_name not in available_themes:
            console.print(Panel(
                f"[red]Theme [bold]{escape(theme_name)}[/bold] not found.[/red]\n\n"
                f"[{muted}]Available:[/{muted}] [{primary}]{', '.join(available_themes.keys())}[/{primary}]",
                title=f"[{title_style}]❌ Set Theme[/{title_style}]",
                border_style="red",
                padding=(1, 2),
            ))
            return

        current_theme = config_manager.get_display_theme()
        if current_theme == theme_name:
            console.print(Panel(
                f"[{success}]Theme [bold]{escape(theme_name)}[/bold] is already active.[/{success}]",
                title=f"[{title_style}]🎨 Set Theme[/{title_style}]",
                border_style=success,
                padding=(1, 2),
            ))
            return

        if preview:
            self._show_theme_preview(theme_name, available_themes[theme_name], muted)

        if not no_confirm:
            while True:
                answer = console.input(
                    f"\n  Switch from [{success}]{escape(current_theme or 'none')}[/{success}] "
                    f"to [{primary}]{escape(theme_name)}[/{primary}]? [{muted}][y/n][/{muted}] "
                ).strip().lower()
                if answer in ('y', 'yes'):
                    break
                if answer in ('n', 'no', ''):
                    console.print(Panel(
                        f"[{warning}]No changes made.[/{warning}]",
                        title=f"[{title_style}]🎨 Set Theme — Cancelled[/{title_style}]",
                        border_style=warning,
                        padding=(1, 2),
                    ))
                    return

        if config_manager.set_display_theme(theme_name):
            console.print(Panel(
                f"[{success}]Theme switched to [bold]{escape(theme_name)}[/bold].[/{success}]\n"
                f"[{muted}]Active on next command.[/{muted}]",
                title=f"[{title_style}]🎨 Theme Updated[/{title_style}]",
                border_style=success,
                padding=(1, 2),
            ))
        else:
            console.print(Panel(
                f"[red]Failed to set theme [bold]{escape(theme_name)}[/bold].[/red]",
                title=f"[{title_style}]❌ Set Theme[/{title_style}]",
                border_style="red",
                padding=(1, 2),
            ))

    def _show_theme_preview(self, theme_name, theme_data, muted='dim'):
        """Show a preview of the theme."""
        console = Console()

        ts = theme_data.get('table_styles', {})
        ps = theme_data.get('panel_styles', {})

        b_col  = ts.get('border_style', 'white')
        ok_col = ps.get('success', 'green')
        wn_col = ps.get('warning', 'yellow')
        er_col = ps.get('error', 'red')
        pr_col = ps.get('primary', ps.get('title', 'cyan'))

        swatch = Table(show_header=False, box=None, padding=(0, 1))
        swatch.add_column(style=f"bold {muted}", width=8,  no_wrap=True)
        swatch.add_column(width=12, no_wrap=True)
        swatch.add_column(width=20, no_wrap=True, style=muted)

        swatch.add_row("Border",  f"[{b_col}]██████████[/{b_col}]",  b_col)
        swatch.add_row("Primary", f"[{pr_col}]██████████[/{pr_col}]", pr_col)
        swatch.add_row("Success", f"[{ok_col}]██████████[/{ok_col}]", ok_col)
        swatch.add_row("Warning", f"[{wn_col}]██████████[/{wn_col}]", wn_col)
        swatch.add_row("Error",   f"[{er_col}]██████████[/{er_col}]", er_col)

        console.print(Panel(
            swatch,
            title=f"[bold]🎨 {escape(theme_name.title())} Preview[/bold]",
            border_style=b_col,
            padding=(1, 2),
        ))
