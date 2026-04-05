# 🎨 Custom Themes Guide - YAML Configuration

## Overview

The `escmd` tool now supports **fully customizable themes** defined in your `elastic_servers.yml` configuration file! Create unlimited custom themes with complete control over colors, borders, and styling.

## How It Works

1. **Define themes** in the `theme_styles` section of your YAML config
2. **Select theme** by setting `display_theme` to any theme name
3. **Instant activation** - no restart required!

## Built-in Themes

### 🌈 Rich Theme
- **Purpose**: Beautiful colorful display for dark terminal backgrounds
- **Borders**: White for professional appearance
- **Headers**: Blue backgrounds with white text
- **Status**: Full color coding (green, yellow, red, blue, etc.)

### ⚪ Plain Theme  
- **Purpose**: Universal compatibility for light terminal backgrounds
- **Borders**: Black for maximum contrast
- **Headers**: Simple bold white text
- **Status**: All bold styling without colors

### 🚀 Cyberpunk Theme
- **Purpose**: Futuristic neon theme for terminal warriors
- **Borders**: Bright magenta for that cyberpunk feel
- **Headers**: Bright white on dark magenta backgrounds  
- **Status**: Bright neon colors (bright_green, bright_yellow, etc.)

## Creating Custom Themes

### Basic Configuration Structure

```yaml
settings:
  display_theme: my_custom_theme  # Your theme name

  theme_styles:
    my_custom_theme:
      border_style: blue          # Any Rich color name
      header_style: bold yellow   # Header styling
      health_styles:
        green:
          icon: green bold        # Icon style  
          text: green bold        # Text style
        yellow:
          icon: yellow bold
          text: yellow bold
        red:
          icon: red bold
          text: red bold
      status_styles:
        open:
          icon: blue bold
          text: blue bold
        close:
          icon: red bold
          text: red bold
      state_styles:
        STARTED:
          icon: green bold
          text: green bold
        INITIALIZING:
          icon: yellow bold
          text: yellow bold
        RELOCATING:
          icon: blue bold
          text: blue bold
        UNASSIGNED:
          icon: red bold
          text: red bold
        default:
          icon: bold
          text: bold
      type_styles:
        primary:
          icon: gold1 bold
          text: gold1 bold
        replica:
          icon: cyan bold
          text: cyan bold
```

### Available Rich Colors

You can use any of these Rich color names:

**Basic Colors:**
- `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`

**Bright Colors:**  
- `bright_black`, `bright_red`, `bright_green`, `bright_yellow`
- `bright_blue`, `bright_magenta`, `bright_cyan`, `bright_white`

**Extended Colors:**
- `gold1`, `gold3`, `orange1`, `orange3`, `dark_orange`
- `deep_pink1`, `deep_pink2`, `purple`, `blue1`, `blue3`
- `dark_green`, `dark_cyan`, `dark_red`, `dark_magenta`

**Style Modifiers:**
- `bold`, `dim`, `italic`, `underline`, `strike`, `reverse`

**Background Colors:**
- `on black`, `on red`, `on dark_blue`, etc.
- Example: `bold white on dark_blue`

## Example Custom Themes

### 🌊 Ocean Theme
```yaml
ocean:
  border_style: deep_sky_blue1
  header_style: bold white on navy_blue
  health_styles:
    green: 
      icon: sea_green1 bold
      text: sea_green1 bold
    yellow:
      icon: gold1 bold  
      text: gold1 bold
    red:
      icon: indian_red1 bold
      text: indian_red1 bold
  # ... (continue with other styles)
```

### 🌙 Midnight Theme
```yaml
midnight:
  border_style: slate_blue1
  header_style: bold silver on grey11
  health_styles:
    green:
      icon: pale_green1 bold
      text: pale_green1 bold
    yellow:
      icon: khaki1 bold
      text: khaki1 bold
    red:
      icon: light_coral bold
      text: light_coral bold
  # ... (continue with other styles)
```

### 🔥 Fire Theme
```yaml
fire:
  border_style: orange_red1
  header_style: bold yellow on dark_red
  health_styles:
    green:
      icon: chartreuse1 bold
      text: chartreuse1 bold
    yellow:
      icon: yellow1 bold
      text: yellow1 bold  
    red:
      icon: red1 bold
      text: red1 bold
  # ... (continue with other styles)
```

## Theme Properties Reference

### Required Properties
- `border_style`: Color for panel borders
- `header_style`: Style for table headers  
- `health_styles`: Styles for health indicators (green/yellow/red)
- `status_styles`: Styles for status indicators (open/close)
- `state_styles`: Styles for shard states (STARTED/INITIALIZING/etc.)
- `type_styles`: Styles for shard types (primary/replica)

### Health States
- `green`: Healthy indices/started shards
- `yellow`: Warning indices/initializing shards  
- `red`: Critical indices/unassigned shards

### Status Types
- `open`: Open indices
- `close`: Closed indices

### Shard States
- `STARTED`: Running shards
- `INITIALIZING`: Starting shards
- `RELOCATING`: Moving shards
- `UNASSIGNED`: Unassigned shards
- `default`: Fallback for unknown states

### Shard Types
- `primary`: Primary shards
- `replica`: Replica shards

## Testing Your Theme

1. **Edit Configuration**:
   ```bash
   vim elastic_servers.yml
   # Change display_theme to your theme name
   ```

2. **Test Immediately**:
   ```bash
   ./escmd.py indices
   ./escmd.py shards
   ```

3. **Validate Settings**:
   ```bash
   ./escmd.py show-settings | grep display_theme
   ```

## Advanced Features

### Per-Cluster Themes
```yaml
servers:
  - name: production
    hostname: prod-es.company.com
    display_theme: plain  # Override global theme for this cluster
```

### Fallback Behavior
- If custom theme not found → Falls back to built-in theme
- If YAML malformed → Uses built-in default
- Always graceful degradation

### Theme Inheritance
You can create themes that build on existing ones:
```yaml
my_rich_variant:
  # Copy all settings from rich theme, then override specific items
  border_style: gold1
  header_style: bold black on gold1
  # ... only specify what you want to change
```

## Troubleshooting

### Theme Not Working?
1. Check YAML syntax: `python3 -c "import yaml; yaml.safe_load(open('elastic_servers.yml'))"`
2. Verify theme name matches exactly
3. Ensure all required properties are defined
4. Check for typos in color names

### Colors Not Displaying?
1. Verify your terminal supports colors
2. Try basic colors first (`red`, `green`, `blue`)  
3. Test with built-in themes to confirm setup

### Need Help?
```bash
# Check current configuration
./escmd.py show-settings

# Validate theme loading
python3 -c "from esclient import get_theme_styles; from configuration_manager import ConfigurationManager; print(get_theme_styles(ConfigurationManager('elastic_servers.yml', 'escmd.json')))"
```

## Best Practices

1. **Start Simple**: Begin with basic colors, then add complexity
2. **Test Contrast**: Ensure text is readable on your terminal background
3. **Consistent Palette**: Use related colors for a cohesive look
4. **Document Themes**: Add comments explaining your color choices
5. **Share Themes**: Copy theme configs to share with team members

## Example Complete Configuration

```yaml
settings:
  display_theme: cyberpunk

  theme_styles:
    cyberpunk:
      border_style: bright_magenta
      header_style: bold bright_white on dark_magenta
      health_styles:
        green: 
          icon: bright_green bold
          text: bright_green bold
        yellow:
          icon: bright_yellow bold
          text: bright_yellow bold
        red:
          icon: bright_red bold
          text: bright_red bold
      status_styles:
        open:
          icon: bright_cyan bold
          text: bright_cyan bold
        close:
          icon: bright_red bold
          text: bright_red bold
      state_styles:
        STARTED:
          icon: bright_green bold
          text: bright_green bold
        INITIALIZING:
          icon: bright_yellow bold
          text: bright_yellow bold
        RELOCATING:
          icon: bright_blue bold
          text: bright_blue bold
        UNASSIGNED:
          icon: bright_red bold
          text: bright_red bold
        default:
          icon: bright_white bold
          text: bright_white bold
      type_styles:
        primary:
          icon: bright_magenta bold
          text: bright_magenta bold
        replica:
          icon: bright_cyan bold
          text: bright_cyan bold
```

Happy theming! 🎨
