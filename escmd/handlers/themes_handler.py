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


class ThemesHandler(BaseHandler):
    """Handler for themes command."""
    
    def handle_themes(self):
        """Handle themes command - display all available themes with previews."""
        from rich.columns import Columns
        
        console = Console()
        
        # Get current theme and full theme data
        from esclient import get_theme_styles, get_full_theme_data
        from configuration_manager import ConfigurationManager
        config_manager = ConfigurationManager(self.config_file, os.path.join(os.path.dirname(self.config_file), 'escmd.json'))
        current_styles = get_theme_styles(config_manager)
        full_theme_data = get_full_theme_data(config_manager)
        current_theme = config_manager.get_display_theme()
        
        # Load all themes from themes.yml
     
        themes_file = config_manager.default_settings.get('themes_file', 'themes.yml')
        if not os.path.isabs(themes_file):
            config_dir = os.path.dirname(config_manager.config_file_path)
            themes_file = os.path.join(config_dir, themes_file)
        
        try:
            with open(themes_file, 'r') as f:
                themes_config = yaml.safe_load(f)
            available_themes = themes_config.get('themes', {})
        except (FileNotFoundError, yaml.YAMLError):
            available_themes = {}
        
        # Check if current theme is a manual/custom theme not in themes.yml
        if current_theme and current_theme not in available_themes:
            # Add the current manual theme to our display list
            available_themes[current_theme] = full_theme_data
        
        # Theme descriptions
        theme_descriptions = {
            'rich': '🌈 Colorful theme optimized for dark terminals',
            'plain': '⚪ Minimal theme with universal compatibility', 
            'cyberpunk': '🔮 High-contrast neon theme with bright colors',
            'ocean': '🌊 Oceanic theme with blue and cyan tones',
            'midnight': '🌙 Dark theme with muted colors',
            'fire': '🔥 Warm theme with orange and red highlights'
        }
        
        if not available_themes:
            console.print("[yellow]🔶 No themes found in themes.yml[/yellow]")
            return
        
        # Title panel
        title_panel = Panel(
            Text("🎨 Available Color Themes", style=current_styles.get('panel_styles', {}).get('title', 'bold cyan'), justify="center"),
            subtitle=f"Current theme: {current_theme} | Total themes: {len(available_themes)}",
            border_style=current_styles['border_style'],
            padding=(1, 2)
        )
        
        print()
        console.print(title_panel)
        print()
        
        # Create theme preview panels
        theme_panels = []
        for theme_name, theme_data in available_themes.items():
            # Create preview table showing key colors
            preview_table = Table(show_header=False, box=None, padding=(0, 3))
            preview_table.add_column("Element", style="bold", width=18)  # Increased from 16
            preview_table.add_column("Preview", width=28)  # Increased significantly for more screen usage
            
            table_styles = theme_data.get('table_styles', {})
            panel_styles = theme_data.get('panel_styles', {})
            
            # Show key color samples
            border_color = table_styles.get('border_style', 'white')
            success_color = panel_styles.get('success', 'green')
            warning_color = panel_styles.get('warning', 'yellow')
            error_color = panel_styles.get('error', 'red')
            
            preview_table.add_row("Border:", f"[{border_color}]████████████[/{border_color}]")
            preview_table.add_row("Success:", f"[{success_color}]████████████[/{success_color}]")
            preview_table.add_row("Warning:", f"[{warning_color}]████████████[/{warning_color}]")
            preview_table.add_row("Error:", f"[{error_color}]████████████[/{error_color}]")
            
            # Theme status indicator
            status_indicator = "🎯 ACTIVE" if theme_name == current_theme else "     "
            
            # Theme panel - handle custom themes
            if theme_name in theme_descriptions:
                description = theme_descriptions[theme_name]
            else:
                description = f"🔧 Custom {theme_name} theme (manually configured)"
            
            panel_title = f"{status_indicator} {theme_name.upper()}"
            
            # Add empty row for better spacing
            preview_table.add_row("", "")
            
            theme_panel = Panel(
                preview_table,
                title=panel_title,
                subtitle=description,
                border_style=border_color if theme_name == current_theme else current_styles['border_style'],
                padding=(2, 3),  # Increased horizontal padding for more breathing room
                expand=True,     # Changed to True to fill available space
                height=12,       # Increased height slightly
                # Removed fixed width to allow expansion
            )
            theme_panels.append(theme_panel)
        
        # Display themes in a grid (2 columns)
        for i in range(0, len(theme_panels), 2):
            if i + 1 < len(theme_panels):
                console.print(Columns([theme_panels[i], theme_panels[i+1]], expand=True))
            else:
                console.print(theme_panels[i])
            print()
        
        # Usage instructions panel
        usage_table = Table(show_header=False, box=None, padding=(0, 1))
        usage_table.add_column("Action", style="bold yellow", width=20)
        usage_table.add_column("Command", style="cyan")
        
        usage_table.add_row("Switch Theme:", "./escmd.py set-theme <theme_name>")
        usage_table.add_row("Preview Theme:", "./escmd.py set-theme <theme_name> --preview")
        usage_table.add_row("Quick Switch:", "./escmd.py set-theme <theme_name> --no-confirm")
        usage_table.add_row("Test Theme:", "./escmd.py health (or any command)")
        usage_table.add_row("List Themes:", "./escmd.py themes")
        
        usage_panel = Panel(
            usage_table,
            title="🚀 How to Switch Themes",
            border_style=current_styles.get('panel_styles', {}).get('info', 'blue'),
            padding=(1, 2)
        )
        
        console.print(usage_panel)
        print()
        
        # Theme categories info - handle case when es_client is None
        if self.es_client and hasattr(self.es_client, 'style_system'):
            table_box = self.es_client.style_system.get_table_box()
        else:
            # Default to box.HEAVY when no ES client available
            from rich import box
            table_box = box.HEAVY
            
        categories_table = Table(show_header=True, header_style=current_styles['header_style'], box=table_box)
        categories_table.add_column("Theme Type", style="bold")
        categories_table.add_column("Recommended For", style="white")
        categories_table.add_column("Terminal Background")
        
        categories_table.add_row("Rich/Colorful", "Dark terminals, full color support", "Dark")
        categories_table.add_row("Plain/Minimal", "Light terminals, compatibility mode", "Light") 
        categories_table.add_row("Specialty", "Personal preference, specific aesthetics", "Varies")
        
        categories_panel = Panel(
            categories_table,
            title="📋 Theme Categories",
            border_style=current_styles['border_style'],
            padding=(1, 2)
        )
        
        console.print(categories_panel)

    def handle_set_theme(self):
        """Handle set-theme command - switch to a different theme."""
        from configuration_manager import ConfigurationManager
        import yaml
        
        console = Console()
        theme_name = self.args.theme_name
        preview = getattr(self.args, 'preview', False)
        no_confirm = getattr(self.args, 'no_confirm', False)
        
        # Load available themes
        config_manager = ConfigurationManager(self.config_file, os.path.join(os.path.dirname(self.config_file), 'escmd.json'))
        themes_file = config_manager.default_settings.get('themes_file', 'themes.yml')
        if not os.path.isabs(themes_file):
            config_dir = os.path.dirname(config_manager.config_file_path)
            themes_file = os.path.join(config_dir, themes_file)
        
        try:
            with open(themes_file, 'r') as f:
                themes_config = yaml.safe_load(f)
            available_themes = themes_config.get('themes', {})
        except (FileNotFoundError, yaml.YAMLError):
            console.print(Panel.fit(f"❌ Could not load themes from {themes_file}", style="bold red"))
            return
        
        # Validate theme name
        if theme_name not in available_themes:
            console.print(Panel.fit(f"❌ Theme '{theme_name}' not found", style="bold red"))
            console.print(f"\n[bold]Available themes:[/bold] {', '.join(available_themes.keys())}")
            return
        
        # Get current theme
        current_theme = config_manager.get_display_theme()
        
        if current_theme == theme_name:
            console.print(Panel.fit(f"✅ Theme '{theme_name}' is already active", style="bold green"))
            return
        
        # Show preview if requested
        if preview:
            self._show_theme_preview(theme_name, available_themes[theme_name])
            if not no_confirm:
                response = input(f"\nSwitch to '{theme_name}' theme? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    console.print("Theme change cancelled.")
                    return
        elif not no_confirm:
            response = input(f"Switch from '{current_theme}' to '{theme_name}'? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                console.print("Theme change cancelled.")
                return
        
        # Set the new theme
        success = config_manager.set_display_theme(theme_name)
        
        if success:
            console.print(Panel.fit(f"✅ Theme switched to '{theme_name}'", style="bold green"))
            console.print(f"[dim]New theme will be active for new commands[/dim]")
        else:
            console.print(Panel.fit(f"❌ Failed to set theme '{theme_name}'", style="bold red"))

    def _show_theme_preview(self, theme_name, theme_data):
        """Show a preview of the theme."""
        console = Console()
        
        # Extract colors from the theme structure
        table_styles = theme_data.get('table_styles', {})
        panel_styles = theme_data.get('panel_styles', {})
        health_styles = theme_data.get('table_styles', {}).get('health_styles', {})
        
        # Get key colors from theme
        border_style = table_styles.get('border_style', 'white')
        primary_style = panel_styles.get('success', 'green')
        warning_style = health_styles.get('yellow', {}).get('text', 'yellow')
        error_style = health_styles.get('red', {}).get('text', 'red')
        success_style = health_styles.get('green', {}).get('text', 'green')
        
        # Preview using Rich markup for better color display
        preview_lines = [f"[bold]🎨 {theme_name.title()} Theme Preview[/bold]\n"]
        
        # Show colors with Rich markup
        preview_lines.append(f"[{border_style}]● Border & Primary: Theme border styling[/{border_style}]")
        preview_lines.append(f"[{success_style}]● Success: Operation completed successfully[/{success_style}]")
        preview_lines.append(f"[{warning_style}]● Warning: Please check configuration[/{warning_style}]")
        preview_lines.append(f"[{error_style}]● Error: Connection failed[/{error_style}]")
        
        # Add table sample
        preview_lines.append("")
        header_style = table_styles.get('header_style', 'bold white')
        # Simplify header style for preview (remove 'on color' parts that cause markup issues)
        header_display = header_style.split(' on ')[0] if ' on ' in header_style else header_style
        preview_lines.append(f"[{header_display}]Sample Table Header[/{header_display}]")
        preview_lines.append(f"[{table_styles.get('border_style', 'white')}]├─────────────────────────┤[/{table_styles.get('border_style', 'white')}]")
        
        # Join the lines
        preview_text = "\n".join(preview_lines)
        
        panel = Panel(
            preview_text,
            title=f"[bold]🎨 {theme_name.title()} Preview[/bold]",
            border_style=border_style,
            padding=(1, 2)
        )
        
        console.print(panel)
