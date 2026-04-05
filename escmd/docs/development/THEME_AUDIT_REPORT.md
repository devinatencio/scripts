# 🎨 ESCMD Theme Consistency Audit Report
============================================================

## 📊 Summary
- **Total Files Analyzed**: 46
- **Files with Issues**: 42
- **Files Using Semantic Styling**: 4
- **Average Migration Score**: 46.1/100

## 🚨 Priority Migration List
Files that most urgently need theme migration:

### handlers/utility_handler.py (Score: 0/100)
**Hardcoded Colors:**
- Line 76: `"[bold blue]📊 Checking indices with no replicas..."`
- Line 76: `"[bold blue]📊 Checking indices with no replicas..."`
- Line 205: `"blue"`

**Hardcoded Styles:**
- Line 202 (Panel style): `blue`

### handlers/cluster_handler.py (Score: 0/100)
**Hardcoded Colors:**
- Line 378: `"[bold blue]Gathering cluster health data..."`
- Line 428: `"[bold blue]Gathering cluster health data..."`
- Line 431: `"[bold blue]Getting basic health info..."`

### handlers/snapshot_handler.py (Score: 0/100)
**Hardcoded Colors:**
- Line 348: `"{total_indices:,}", style=self.es_client.style_system._get_style('semantic', 'primary', 'bright_magenta'`
- Line 345: `"{total_snapshots} of {original_count}", style=self.es_client.style_system._get_style('semantic', 'secondary', 'bright_blue'`
- Line 470: `"bright_blue"`

**Hardcoded Styles:**
- Line 952 (Panel style): `red`
- Line 974 (Panel style): `green`
- Line 980 (Panel style): `red`

### handlers/password_handler.py (Score: 0/100)
**Hardcoded Colors:**
- Line 148: `"blue"`
- Line 149: `"bold white on blue"`
- Line 300: `"bold white on blue"`

**Hardcoded Styles:**
- Line 123 (Panel style): `cyan`
- Line 219 (Panel style): `green`
- Line 246 (Panel style): `green`

### handlers/health_handler.py (Score: 0/100)
**Hardcoded Colors:**
- Line 130: `'header_style', 'bold blue'`
- Line 224: `"bright_yellow"`
- Line 1134: `"bright_yellow"`

**Hardcoded Styles:**
- Line 908 (Panel style): `green`
- Line 928 (Panel style): `bright_blue`
- Line 938 (Panel style): `bright_blue`

### handlers/allocation_handler.py (Score: 0/100)
**Hardcoded Colors:**
- Line 114: `"ℹ️  Info", " No hosts are currently excluded from allocation.\nNothing to reset.", message_style="bold white", panel_style="blue"`
- Line 186: `"Info", "ℹ️ No hosts are currently excluded from allocation", message_style="bold white", panel_style="blue"`
- Line 191: `"Info", f"ℹ️ Host '{hostname}' is not in the exclusion list.\n\nCurrently excluded hosts:\n• {chr(10).join(['• ' + host for host in current_exclusions])}", message_style="bold white", panel_style="blue"`

### handlers/lifecycle_handler.py (Score: 0/100)
**Hardcoded Colors:**
- Line 98: `"blue"`
- Line 135: `"blue"`
- Line 497: `"blue"`

**Hardcoded Styles:**
- Line 25 (Panel style): `bold red`
- Line 43 (Panel style): `bold cyan`
- Line 76 (Panel style): `green`

### handlers/themes_handler.py (Score: 0/100)
**Hardcoded Colors:**
- Line 57: `'ocean': '🌊 Oceanic theme with blue and cyan tones'`
- Line 148: `'panel_styles', {}).get('info', 'blue'`
- Line 269: `'header_style', 'bold white'`

**Hardcoded Styles:**
- Line 136 (Column style): `bold yellow`
- Line 137 (Column style): `cyan`
- Line 165 (Column style): `white`

### handlers/help_handler.py (Score: 0/100)
**Hardcoded Colors:**
- Line 768: `'command', 'bold blue'`
- Line 657: `'section_header': 'bold bright_yellow'`
- Line 658: `'command': 'bright_yellow bold'`

**Hardcoded Styles:**
- Line 252 (Column style): `bold cyan`
- Line 253 (Column style): `white`
- Line 264 (Column style): `bold green`

### display/table_renderer.py (Score: 0/100)
**Hardcoded Colors:**
- Line 213: `'RELOCATING': 'blue'`
- Line 215: `'open': 'blue'`
- Line 61: `'table_styles', 'header_style', 'bold white'`

**Hardcoded Styles:**
- Line 86 (Column style): `cyan`
- Line 87 (Column style): `white`

## ✅ Best Practices Examples
Files that demonstrate good semantic styling:

### commands/allocation_commands.py (Score: 100/100)
Uses: primary, error, info

### commands/settings_commands.py (Score: 100/100)
Uses: error

### commands/snapshot_commands.py (Score: 100/100)
Uses: warning, error, info

### commands/utility_commands.py (Score: 100/100)
Uses: error

### commands/cluster_commands.py (Score: 100/100)
Uses: error, info

## 📁 Progress by Directory

**Commands**: 12/12 files migrated (avg score: 95.8)
**Handlers**: 7/20 files migrated (avg score: 42.5)
**Display**: 1/14 files migrated (avg score: 8.6)

## 🔧 Quick Migration Tips

1. **Replace hardcoded colors with semantic equivalents:**
   - `'green'` → `style_system.get_semantic_style('success')`
   - `'red'` → `style_system.get_semantic_style('error')`
   - `'yellow'` → `style_system.get_semantic_style('warning')`

2. **Use standard component creation:**
   - `Panel(...)` → `style_system.create_info_panel(...)`
   - `Table(...)` → `style_system.create_standard_table(...)`

3. **Import StyleSystem in command files:**
   ```python
   from display.style_system import StyleSystem
   # Available as self.style_system in BaseCommand subclasses
   ```