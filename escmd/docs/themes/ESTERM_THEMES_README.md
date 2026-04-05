# ESterm Theme System

**Independent theme system for ESterm interactive terminal**

ESterm now features its own comprehensive theme system that is completely separate from ESCMD's theme system. This allows you to customize the appearance of the ESterm interactive terminal without affecting ESCMD command output.

## 🎨 Features

- **8 Built-in Themes**: Rich variety from professional to fun
- **Complete Independence**: No interference with ESCMD themes
- **Real-time Switching**: Change themes instantly without restart
- **Theme Previews**: Preview themes before switching
- **Configuration Management**: Persistent theme preferences
- **Accessibility Support**: Plain theme for maximum compatibility

## 🚀 Quick Start

### Viewing Available Themes

```bash
# Inside ESterm interactive session
esterm> theme
```

This displays all available themes with descriptions:

```
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Theme       ┃ Name              ┃ Description        ┃ Best For          ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ → rich      │ Rich Colors       │ Vibrant colors     │ High-contrast     │
│   plain     │ Plain Text        │ Minimal colors     │ Accessibility     │
│   cyberpunk │ Cyberpunk Neon    │ Electric colors    │ Dark terminals    │
│   ocean     │ Ocean Blue        │ Sea-inspired       │ Professional      │
│   fire      │ Fire Orange       │ Warm colors        │ High-energy       │
│   matrix    │ Matrix Green      │ Terminal green     │ Retro computing   │
│   midnight  │ Midnight Soft     │ Soft colors        │ Late-night coding │
│   corporate │ Corporate Pro     │ Professional       │ Business use      │
└─────────────┴───────────────────┴────────────────────┴───────────────────┘
```

### Switching Themes

```bash
# Switch to a specific theme
esterm> theme cyberpunk
Theme changed to 'cyberpunk'

# Preview a theme without switching
esterm> theme preview ocean
```

### Current Theme Info

Your current theme is always shown in:
- Welcome banner (if enabled in config)
- Status command output
- Theme list (marked with →)

## 📋 Available Themes

### `rich` (Default)
**Vibrant colors for modern terminals**
- Bright blues, greens, and cyans
- High contrast for readability
- Best for: Color displays, modern terminals

### `plain`
**Minimal colors, maximum compatibility**
- Bold text instead of colors
- High accessibility
- Best for: Screen readers, low-color terminals

### `cyberpunk`
**Electric bright colors**
- Neon magentas, cyans, and yellows
- Futuristic aesthetic
- Best for: Dark terminals, sci-fi themes

### `ocean`
**Blues and sea-inspired colors**
- Deep blues, teals, and sea greens
- Calm, professional appearance
- Best for: Professional environments

### `fire`
**Warm oranges and reds**
- Orange, red, and yellow palette
- High-energy appearance
- Best for: Active work sessions

### `matrix`
**Classic terminal green theme**
- Various shades of green
- Retro computing aesthetic
- Best for: Nostalgia, terminal purists

### `midnight`
**Soft colors for dark environments**
- Muted purples, blues, and silvers
- Easy on the eyes
- Best for: Late-night coding, dark themes

### `corporate`
**Professional grays and blues**
- Business-appropriate colors
- Clean, formal appearance
- Best for: Corporate environments

## 🛠 Configuration

ESterm theme system uses `esterm_config.yml` for persistent settings:

```yaml
# Theme Configuration
theme:
  current: "rich"           # Currently active theme
  auto_detect: true         # Auto-detect terminal capabilities
  fallback: "plain"         # Fallback if current theme fails

# UI Settings
ui:
  show_banner: true                    # Show welcome banner
  show_theme_in_banner: true           # Show theme name in banner
  
  prompt:
    show_status_colors: true           # Color cluster status in prompt
    format: "esterm"                   # Prompt format (esterm/simple/minimal)
  
  messages:
    use_panels: true                   # Use Rich panels for messages
    show_icons: true                   # Show icons (✓, ⚠️, etc.)
```

### Configuration Options

| Setting | Values | Description |
|---------|--------|-------------|
| `theme.current` | theme name | Active theme |
| `theme.auto_detect` | true/false | Detect terminal capabilities |
| `theme.fallback` | theme name | Fallback theme |
| `ui.show_banner` | true/false | Show welcome banner |
| `ui.show_theme_in_banner` | true/false | Show theme in banner |
| `ui.prompt.show_status_colors` | true/false | Color cluster status |
| `ui.prompt.format` | esterm/simple/minimal | Prompt style |
| `ui.messages.use_panels` | true/false | Use Rich panels |
| `ui.messages.show_icons` | true/false | Show message icons |

## 🎯 Theme Components

Each theme customizes these UI elements:

### Banner
- Title styling
- Version and subtitle colors
- Welcome message appearance
- Border styling

### Prompts
- Connected cluster colors (green/blue)
- Disconnected status (red)
- Warning status (yellow)
- Prompt symbol styling

### Status Displays
- Label and value colors
- Success/warning/error states
- Information styling
- Panel borders

### Messages
- Success messages (✓)
- Warning messages (⚠️)
- Error messages (⚠️)
- Information messages (ℹ️)
- Progress indicators

### Help System
- Command names
- Descriptions
- Examples
- Section headers

## 🔧 Advanced Usage

### Theme Previews

Preview any theme without switching:

```bash
esterm> theme preview cyberpunk
```

This shows:
- Theme name and description
- Sample colored elements
- Use case recommendations

### Programmatic Access

Themes can be accessed programmatically:

```python
from esterm_modules.theme_manager import EstermThemeManager

# Initialize theme manager
theme_manager = EstermThemeManager()

# Get available themes
themes = theme_manager.get_available_themes()

# Switch theme
theme_manager.set_theme('cyberpunk')

# Get theme info
info = theme_manager.get_theme_info('ocean')

# Get specific styles
style = theme_manager.get_style('banner', 'title_style')
```

## 🔀 Independence from ESCMD

**Important**: ESterm themes are completely independent from ESCMD themes:

- ✅ **ESterm UI**: Banners, prompts, status, messages, help
- ❌ **ESCMD Output**: Tables, health displays, JSON formatting

This means:
1. Changing ESterm theme does **NOT** affect ESCMD command output
2. ESCMD themes work normally and independently
3. You can use different themes for ESterm UI and ESCMD output
4. No conflicts or interference between the two systems

## 📁 File Structure

```
escmd/
├── esterm_themes.yml          # Theme definitions
├── esterm_config.yml          # Configuration file
├── esterm_modules/
│   ├── theme_manager.py       # Theme management
│   ├── themed_terminal_ui.py  # Themed UI components
│   └── terminal_session.py    # Updated session manager
└── ESTERM_THEMES_README.md    # This file
```

## 🚨 Troubleshooting

### Theme Not Loading
```bash
# Check available themes
esterm> theme

# Try fallback theme
esterm> theme plain

# Check config file exists
ls esterm_config.yml
```

### Colors Not Showing
- Verify terminal supports colors
- Try `plain` theme for compatibility
- Check `theme.auto_detect` setting

### Theme Resets on Restart
- Check `esterm_config.yml` permissions
- Verify theme name is spelled correctly
- Check config file syntax

### Config File Missing
ESterm will create default config on first theme change:
```bash
esterm> theme cyberpunk
# This creates esterm_config.yml with current selection
```

## 🎨 Creating Custom Themes

While not directly supported in v1.0, you can:

1. **Modify existing themes** in `esterm_themes.yml`
2. **Copy and rename** theme sections
3. **Adjust colors** to your preference

Example custom theme section:
```yaml
my_custom_theme:
  banner:
    title_style: "bold purple"
    subtitle_style: "dim white"
    version_style: "bright_blue"
    welcome_style: "green"
    border_style: "purple"
  
  prompt:
    connected_cluster_style: "bright_green"
    disconnected_style: "bright_red"
    warning_cluster_style: "yellow"
    prompt_symbol_style: "bold purple"
  
  # ... more sections
```

## 📊 Demo and Testing

Test the theme system:

```bash
# Run theme demo
python3 esterm_theme_demo.py

# Run theme tests  
python3 test_esterm_themes.py

# Start ESterm normally
python3 esterm.py
```

## 🤝 Integration

The theme system integrates seamlessly with:
- ✅ **ESterm Interactive Terminal**
- ✅ **Cluster connection status**
- ✅ **Help system**
- ✅ **Status displays**
- ✅ **Error handling**
- ❌ **ESCMD command output** (by design)

## 📝 Version History

- **v1.0.0**: Initial release with 8 themes
- Independent from ESCMD theme system
- Configuration file support
- Real-time theme switching
- Theme previews

---

**ESterm Theme System** - Making your Elasticsearch terminal experience beautiful and personalized! 🎨✨