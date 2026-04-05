# ESterm Enhanced Prompts

ESterm now features an advanced prompt system with theme-specific enhancements, connection indicators, and customizable display options. This guide covers all the new prompt features and how to configure them.

## Overview

The enhanced prompt system provides:
- **Connection Indicators**: Visual indicators for connection status (no stale health data)
- **Theme-Specific Formats**: Special prompt styles for cyberpunk and matrix themes
- **Extended Information**: Node counts, timestamps, and connection details
- **Customizable Display**: Configure what information to show

## Prompt Formats

### Standard Format (esterm)
```
🔗 esterm(production:5) 14:32:45> your_command
```

### Cyberpunk Theme Format
```
🔗 esterm >> [production:5] :: 14:32:45 >> your_command
```

### Matrix Theme Format
```
🔗 esterm@[production:5] $ your_command
```

### Simple Format
```
🔗 production> your_command
```

### Minimal Format
```
> your_command
```

## Connection Indicators

The prompt displays connection indicators (not health status to avoid stale data):

| Icon | Status | Meaning |
|------|---------|---------|
| 🔗 | Connected | Active connection to cluster |
| 🔌 | Disconnected | No active cluster connection |

**Note**: Health status is intentionally NOT shown in prompts to prevent displaying potentially stale information. Use dedicated commands like `get health` or `status` for real-time cluster health.

## Configuration Options

Configure the enhanced prompts in your `esterm_config.yml`:

```yaml
ui:
  prompt:
    format: esterm                 # esterm/simple/minimal/cyberpunk/matrix
    show_icons: true               # Show connection icons
    show_node_count: true          # Display cluster node count
    show_time: true                # Show current time
    enhanced_formats:
      cyberpunk: true              # Enable cyberpunk format
      matrix: true                 # Enable matrix format
```

### Configuration Details

#### `format` Options
- **esterm**: Default format with theme styling
- **simple**: Just cluster name and prompt
- **minimal**: Only the prompt symbol
- **cyberpunk**: Special cyberpunk-themed format (when using cyberpunk theme)
- **matrix**: Special matrix-themed format (when using matrix theme)

#### `show_icons`
Displays connection icons before the prompt:
- 🔗 **Connected**: Active cluster connection
- 🔌 **Disconnected**: No cluster connection

#### `show_node_count`
Shows the number of nodes in the cluster:
```
esterm(production:5)>  # 5 nodes in the production cluster
```

#### `show_time`
Displays current time in the prompt:
```
esterm(production) 14:32:45>
```

Time format varies by theme:
- **Cyberpunk**: `:: 14:32:45`
- **Matrix**: `[14:32:45]`  
- **Others**: `14:32:45`

## Theme-Specific Features

### Cyberpunk Theme
The cyberpunk theme offers a futuristic, neon-inspired prompt:

**Connected:**
```
🔗 esterm >> [production:5] :: 14:32:45 >> 
```

**Disconnected:**
```
🔌 esterm >> <OFFLINE> :: 14:32:45 >> 
```

**Features:**
- Neon-style `>>` separators
- Electric color scheme (bright magenta, cyan)
- `<OFFLINE>` indicator for disconnected state
- Time with `::` separator

### Matrix Theme
The matrix theme provides a classic terminal hacker aesthetic:

**Connected:**
```
🔗 esterm@[production:5] $ 
```

**Disconnected:**
```
🔌 esterm@OFFLINE $ 
```

**Features:**
- Unix-style `@` separator
- Green monochrome color scheme
- Terminal `$` prompt ending
- Bracket-enclosed cluster info

## Advanced Customization

### Theme-Specific Prompt Styles

Each theme can define additional prompt styling in `esterm_themes.yml`:

```yaml
cyberpunk:
  prompt:
    prompt_symbol_style: "bold bright_magenta"
    enhanced_separator_style: "bright_cyan"
    time_style: "bright_cyan"
    node_count_style: "bright_white"
    status_icon_style: "bright_yellow"
```

### Custom Connection Colors

Override connection colors per theme:

```yaml
ocean:
  prompt:
    connected_cluster_style: "sea_green1"      # Connected clusters
    disconnected_style: "salmon1"             # Disconnected state
```

## Examples

### Basic Usage

1. **Enable enhanced prompts:**
   ```yaml
   # esterm_config.yml
   ui:
     prompt:
       show_icons: true
       show_node_count: true
   ```

2. **Switch to cyberpunk theme with enhanced prompts:**
   ```bash
   theme cyberpunk
   # Prompt becomes: 🔗 esterm >> [production:5] >> 
   ```

3. **Enable time display:**
   ```yaml
   ui:
     prompt:
       show_time: true
   ```

### Theme Combinations

Different themes provide different enhanced experiences:

**Cyberpunk + Full Enhancement:**
```yaml
theme:
  current: cyberpunk
ui:
  prompt:
    format: cyberpunk
    show_icons: true
    show_node_count: true
    show_time: true
```
Result: `🔗 esterm >> [production:5] :: 14:32:45 >> `

**Matrix + Minimal Enhancement:**
```yaml  
theme:
  current: matrix
ui:
  prompt:
    format: matrix
    show_icons: true
    show_node_count: false
    show_time: false
```
Result: `🔗 esterm@[production] $ `

## Troubleshooting

### Icons Not Displaying
If connection icons don't appear:
1. Check your terminal supports Unicode
2. Verify `show_icons: true` in config
3. Try a different terminal emulator

### Colors Not Working
If colors don't display correctly:
1. Check terminal color support
2. Verify theme is loaded: `theme list`
3. Try the 'plain' theme for basic compatibility

### Custom Formats Not Working
If cyberpunk/matrix formats don't activate:
1. Ensure theme matches format (cyberpunk theme + cyberpunk format)
2. Check `enhanced_formats` are enabled in config
3. Restart esterm after configuration changes

### Getting Real-Time Health Information
Since health status is not shown in prompts (to prevent stale data):
1. Use `get health` for current cluster health
2. Use `status` for detailed cluster status
3. Use `get cluster stats` for cluster statistics
4. Use `monitor` for real-time monitoring

## Migration from Old Prompts

Old configuration will continue to work. To migrate:

1. **Old simple prompt users:**
   ```yaml
   # Old
   ui:
     prompt:
       format: simple
   
   # New - add enhancements
   ui:
     prompt:
       format: simple
       show_icons: true
   ```

2. **Theme switchers:**
   - No changes needed
   - Enhanced features activate automatically with compatible themes

## Performance Notes

Enhanced prompts have minimal performance impact:
- Connection icons: No performance cost
- Node count: Requires cluster info fetch (cached)
- Time display: Minimal CPU usage
- Theme-specific formats: No additional cost
- No health status checks: Eliminates potential network delays

For maximum performance on slow systems, use minimal format:
```yaml
ui:
  prompt:
    format: minimal
    show_icons: false
```

## API for Developers

### Adding Custom Prompt Formats

To add a new theme-specific prompt format:

1. **Add format method to `ThemedTerminalUI`:**
   ```python
   def _get_mytheme_prompt(self, cluster_display: str, status_icon: str) -> str:
       return f"{status_icon}[custom_style]{cluster_display}[/custom_style] >> "
   ```

2. **Update `get_prompt()` method:**
   ```python
   elif prompt_format == 'mytheme' and current_theme == 'mytheme':
       return self._get_mytheme_prompt(enhanced_cluster_display, status_icon)
   ```

3. **Define theme styles:**
   ```yaml
   mytheme:
     prompt:
       custom_style: "bold custom_color"
   ```

### Custom Connection Icons

You can customize connection icons by modifying the prompt methods:

```python
def _get_cyberpunk_prompt(self, cluster_display: str, time_display: str, connection_icon: str) -> str:
    # Use custom icons
    custom_icon = "🚀 " if connection_icon else ""
    prompt_base = f"{custom_icon}[bold bright_magenta]esterm[/bold bright_magenta] [bright_cyan]>>[/bright_cyan] [{cluster_display}]"
    
    if time_display:
        prompt_base += f" {time_display}"
    
    return f"{prompt_base} [bright_cyan]>>[/bright_cyan] "
```

This enhanced prompt system makes ESterm more visually informative while avoiding potentially misleading health status information. Users can rely on dedicated commands for real-time cluster health data while enjoying enhanced visual prompts for connection status and cluster identification.