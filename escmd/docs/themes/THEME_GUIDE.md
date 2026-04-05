# 🎨 Display Theme Configuration Guide

## Overview

The `escmd` tool now supports configurable display themes to ensure optimal readability across different terminal backgrounds and environments.

## Available Themes

### 🌈 Rich Theme (Default)
- **Best for**: Dark terminal backgrounds
- **Features**: Colorful headers with blue backgrounds, colored status indicators
- **Configuration**: `display_theme: rich`

### ⚪ Plain Theme  
- **Best for**: Light terminal backgrounds, universal compatibility
- **Features**: Bold text without colors, works on any background
- **Configuration**: `display_theme: plain`

## Configuration

### In elastic_servers.yml

```yaml
settings:
  # Theme Options: 'rich' (colorful, dark backgrounds) or 'plain' (universal)
  display_theme: rich  # or 'plain'
  
  # Other settings...
  box_style: SQUARE_DOUBLE_HEAD
  health_style: dashboard
```

### Per-Cluster Override

```yaml
servers:
  - name: production-light
    hostname: prod-es.company.com
    display_theme: plain  # Override for this specific cluster
    # ... other settings
```

## Visual Differences

| Element | Rich Theme | Plain Theme |
|---------|------------|-------------|
| Borders | `white` | `black` |
| Headers | `bold white on dark_blue` | `bold white` |
| Health Green | `green bold` | `bold` |
| Health Yellow | `yellow bold` | `bold` |  
| Health Red | `red bold` | `bold` |
| State Started | `green bold` | `bold` |
| Type Primary | `gold1 bold` | `bold` |

## Benefits

### Rich Theme
- ✅ Beautiful colored output for dark terminals
- ✅ Quick visual identification of status
- ✅ Professional blue headers with consistent white borders
- ❌ May be hard to read on light backgrounds

### Plain Theme  
- ✅ Works on any terminal background
- ✅ High contrast with black borders for light terminals
- ✅ Maintains meaningful shapes (◉◐○◆◇■□)
- ✅ Universal compatibility
- ❌ Less visually distinctive

## Migration Guide

### From Previous Versions
If you were using the colorful theme and experiencing visibility issues:

1. **Edit your `elastic_servers.yml`**:
   ```yaml
   settings:
     display_theme: plain  # Add this line
   ```

2. **Test the change**:
   ```bash
   ./escmd.py indices
   ./escmd.py shards
   ```

### Recommendation by Terminal
- **Dark backgrounds**: Use `rich` theme
- **Light backgrounds**: Use `plain` theme  
- **Mixed environments**: Use `plain` theme for consistency

## Implementation Details

The theme system automatically applies consistent styling across:
- Indices table (health, status indicators)
- Shards table (state, type indicators) 
- All detailed shard information views
- Table headers and borders
- Panel borders (white for rich theme, black for plain theme)

Meaningful shapes are preserved in both themes:
- **Health/State**: ◉ (healthy/started), ◐ (warning/initializing), ○ (critical/unassigned)
- **Status**: ◆ (open), ◇ (closed)  
- **Type**: ■ (primary), □ (replica)

## Verification

Check your current theme setting:
```bash
./escmd.py show-settings
```

Look for the `display_theme` entry in the output.
