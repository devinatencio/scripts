# 🎨 ESCMD Theme Enhancement & Style Migration Guide

## Overview

This guide helps you migrate commands to use the new enhanced theme system and ensure consistent styling across all ESCMD features.

## Enhanced Theme System Components

### 1. StyleSystem (NEW)
- **Purpose**: Provides semantic styling utilities and standardized patterns
- **Location**: `display/style_system.py`
- **Key Features**:
  - Semantic color system (success, warning, error, info, etc.)
  - Standardized table and panel creation
  - Automatic status indicators and icons
  - Size and percentage formatting with semantic colors

### 2. ThemeManager (ENHANCED) 
- **Purpose**: Loads and manages theme configurations
- **Location**: `display/theme_manager.py`
- **Provides**: Theme loading, style caching, backward compatibility

### 3. PanelRenderer & TableRenderer (ENHANCED)
- **Purpose**: Create consistently styled UI components
- **Location**: `display/panel_renderer.py`, `display/table_renderer.py`

## Migration Patterns

### ❌ OLD: Hardcoded Colors
```python
# Don't do this anymore
table = Table(header_style="bold magenta", border_style="blue")
panel = Panel(content, title="[bold red]Error[/bold red]", border_style="red")
text = Text("Status: OK", style="green")
```

### ✅ NEW: Semantic Styling
```python
# Use semantic styling instead
from display.style_system import StyleSystem

style_system = StyleSystem(self.theme_manager)

# Semantic tables
table = style_system.create_standard_table("Data Overview", style_variant='dashboard')
style_system.add_themed_column(table, "Status", column_type='status')

# Semantic panels  
panel = style_system.create_success_panel(content, "Operation Complete")

# Semantic text
status_text = style_system.create_semantic_text("Connected", 'success')
status_with_icon = style_system.create_status_text("healthy")
```

## Step-by-Step Migration Process

### Step 1: Import Enhanced Styling
```python
from display.style_system import StyleSystem
# OR use existing theme_manager methods
```

### Step 2: Replace Hardcoded Colors

#### Tables:
```python
# OLD
table = Table(show_header=True, header_style="bold magenta", title="📊 Data")

# NEW  
table = style_system.create_standard_table("📊 Data", style_variant='dashboard')
```

#### Panels:
```python
# OLD
Panel(content, title="[bold cyan]Info[/bold cyan]", border_style="blue")

# NEW
style_system.create_info_panel(content, "Info")
```

#### Status Indicators:
```python
# OLD
if status == "green":
    Text("✅ Healthy", style="green bold")

# NEW
style_system.create_status_text(status)  # Automatic icon + semantic styling
```

### Step 3: Use Semantic Color System

Replace specific colors with semantic meanings:
- `green/red/yellow` → `success/error/warning`
- `blue/cyan` → `info/primary`
- `magenta/purple` → `secondary`
- `white/dim` → `neutral/muted`

### Step 4: Leverage Formatting Utilities

```python
# Size formatting with semantic colors
size_text = style_system.format_size(1073741824)  # "1.0 GB" with warning color

# Percentage with progress indicators  
progress = style_system.format_percentage(85.5)  # "🟡 85.5%" 

# Progress bars
bar = style_system.create_progress_bar(75, width=15)  # Visual progress bar
```

## Command-Specific Migration Examples

### Health Commands
```python
# Before: Mixed hardcoded styles
def _create_cluster_panel(self, health_data):
    table = Table(header_style="bold magenta")
    status_style = "green" if status == "green" else "red"
    
# After: Semantic styling
def _create_cluster_panel(self, health_data):
    table = self.style_system.create_standard_table("Cluster Status")
    status_text = self.style_system.create_status_text(health_data['status'])
```

### Node Commands  
```python
# Before: Hardcoded colors
Text(f"Master Node: {name}", style="bold yellow")

# After: Semantic styling
self.style_system.create_semantic_text(f"Master Node: {name}", 'primary')
```

### Snapshot Commands
```python
# Before: Manual color logic
if snapshot_status == "SUCCESS":
    style = "green"
elif snapshot_status == "FAILED": 
    style = "red"

# After: Automatic semantic styling
status_text = self.style_system.create_status_text(snapshot_status)
```

## New Theme Options

Enhanced themes now available:
- **rich** - Original colorful theme
- **plain** - Universal compatibility  
- **cyberpunk** - Neon aesthetic
- **ocean** - Professional oceanic colors
- **corporate** - Business professional theme
- **matrix** - Terminal/hacker aesthetic  
- **fire** - High-energy warm colors

Switch themes with:
```bash
python3 theme_switcher.py corporate
```

## Testing Your Migration

1. **Run style tests**:
   ```bash
   python3 test_display_components.py
   ```

2. **Test multiple themes**:
   ```bash
   python3 theme_switcher.py matrix
   ./escmd.py health
   
   python3 theme_switcher.py corporate  
   ./escmd.py nodes
   ```

3. **Check consistency**: All commands should have similar visual patterns and color usage

## Migration Checklist

For each command file:
- [ ] Import `StyleSystem` 
- [ ] Replace hardcoded colors with semantic equivalents
- [ ] Use standard table/panel creation methods
- [ ] Use semantic text creation for status indicators
- [ ] Test with multiple themes
- [ ] Verify consistent visual presentation

## Benefits After Migration

✅ **Consistency**: All commands have unified visual language  
✅ **Maintainability**: Easy to update styling across entire app  
✅ **Accessibility**: Better color semantics for different user needs  
✅ **Professionalism**: Polished, cohesive user experience  
✅ **Flexibility**: Easy theme switching and customization
