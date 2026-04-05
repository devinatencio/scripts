# Actions Output Enhancements

This document describes the enhanced output formatting and presentation features added to the escmd actions system.

## Overview

The actions system has been significantly enhanced to provide cleaner, more readable output when executing command sequences. These improvements make it easier to understand what's happening during action execution and provide better visibility into command results.

## Key Enhancements

### 1. 🎨 Visual Presentation Improvements

**Before:** Raw command output mixed with execution logs
```
Step 1: Add Exclusion to Template
Update the manuel template to exclude the specified host
Command: template-modify manuel_template -t component -f "template.settings.index.routing.allocation.exclude._name" -o append -v "server01-*"
✗ Template modification failed: Template 'manuel_template' not found
```

**After:** Clean, organized panels with proper formatting
```
╭─────────────────────────────────── Step 1/2 ───────────────────────────────────╮
│ Add Exclusion to Template                                                      │
│ Update the manual template to exclude the specified host                       │
│ Command: template-modify manual_template -t component -f                       │
│ "template.settings.index.routing.allocation.exclude._name" -o append -v        │
│ "server01-*"                                                                   │
╰────────────────────────────────────────────────────────────────────────────────╯
✓ Step completed successfully
```

### 2. 🔄 Automatic JSON Formatting

Commands that support `--format json` are automatically enhanced:

- **Health commands** → Pretty-printed JSON with intelligent summaries
- **Node listings** → Structured JSON output with key highlights  
- **Index operations** → Clean JSON results with relevant metrics
- **Allocation commands** → Formatted status information

**Example Enhancement:**
```yaml
# Your action definition
steps:
  - name: Check Cluster Health
    action: health
```

**Automatic transformation:**
- Original command: `health`
- Enhanced command: `health --format json`
- Result: Pretty-printed JSON in a styled panel

### 3. 📊 Intelligent Output Summarization

Large JSON outputs are automatically summarized to show the most relevant information:

**For Health Commands:**
```
╭─────────────────────────── 📊 Command Results Summary ───────────────────────────╮
│ 🏥 Cluster Status: GREEN                                                       │
│ 📊 Nodes: 12                                                                   │
│ 🟢 Active Primary Shards: 1,247                                                │
│ 🔄 Relocating Shards: 0                                                        │
│                                                                                │
│ 💡 Use --format table for detailed tabular view                                │
╰────────────────────────────────────────────────────────────────────────────────╯
```

**For List Commands:**
```
╭─────────────────────────── 📊 Command Results Summary ───────────────────────────╮
│ 📋 Total Items: 1,247                                                          │
│ 📝 Sample Fields: index, status, health, pri, rep                              │
│                                                                                │
│ 💡 Use --format table for detailed tabular view                                │
╰────────────────────────────────────────────────────────────────────────────────╯
```

### 4. 🎛️ Output Control Options

New CLI options provide fine-grained control over output formatting:

```bash
# Disable automatic JSON formatting
escmd action run my-action --no-json

# Compact output (minimal visual elements)
escmd action run my-action --compact

# Control output length
escmd action run my-action --max-lines 20

# Combine options
escmd action run my-action --compact --no-json --max-lines 10
```

### 5. 📋 Better Step Organization

Each step now displays in a clean, organized format:

- **Step counter** (e.g., "Step 1/3") 
- **Step name** and description in separate lines
- **Command preview** with proper line wrapping
- **Execution status** with clear success/failure indicators
- **Results display** in formatted panels

### 6. 🚨 Enhanced Error Handling

Errors are now displayed more clearly:

```
╭─────────────────────────────────── Step 2/2 ───────────────────────────────────╮
│ Add Allocation Exclusion for Host                                              │
│ Add allocation exclusion rule for the host                                     │
│ Command: allocation exclude add "server01-*"                                   │
╰────────────────────────────────────────────────────────────────────────────────╯
✗ Step failed

╭───────────────────────────── 📄 Command Output ─────────────────────────────────╮
│ Error: Invalid hostname format "server01-*"                                   │
│ Expected: hostname without wildcards                                           │
│ Use 'allocation exclude add server01' instead                                  │
╰────────────────────────────────────────────────────────────────────────────────╯
```

## Supported Commands with Auto-JSON

The following commands automatically get `--format json` added:

- `health`, `health-detail`
- `nodes`, `masters`, `current-master` 
- `indices`, `storage`, `shards`
- `allocation`, `snapshots`
- `cluster-settings`, `recovery`
- `shard-colocation`, `dangling`
- `templates`, `rollover`

## Configuration Options

### Per-Action Configuration

Control output behavior in the ActionHandler:

```python
# In action_handler.py - these are set from CLI args
self.auto_format_json = not getattr(args, 'no_json', False)
self.show_command_output = not getattr(args, 'compact', False) 
self.max_output_lines = getattr(args, 'max_lines', 15)
```

### Global Behavior

- **JSON Formatting:** Enabled by default for supported commands
- **Output Panels:** Shown by default unless `--compact` is used
- **Line Limits:** Default 15 lines, configurable with `--max-lines`
- **Progress Indicators:** Clean progress bars replaced step-by-step execution

## Examples

### Basic Usage
```bash
# Standard execution with enhanced output
escmd action run health-check

# Dry run with clean preview
escmd action run add-host --param-host web01 --dry-run

# Compact mode for CI/scripting
escmd action run maintenance-mode --param-action enable --compact
```

### Advanced Usage
```bash
# Custom output control
escmd action run complex-deployment \
  --param-environment prod \
  --param-version 2.1.0 \
  --max-lines 25 \
  --no-json

# Multiple parameters with clean output
escmd action run rollover-and-backup \
  --param-index-pattern "application-logs-*" \
  --param-snapshot-name "backup-$(date +%Y%m%d-%H%M)" \
  --compact
```

## Implementation Details

### JSON Detection and Parsing

- Commands are analyzed to determine JSON support
- Output is parsed and validated as JSON
- Fallback to text formatting if JSON parsing fails
- Smart summarization for large data sets

### Panel Rendering

- Rich library panels for consistent formatting
- Color-coded status indicators (✓ success, ✗ failure)
- Proper text wrapping and padding
- Theme-aware styling integration

### Output Capture

- Clean separation of stdout/stderr
- Progress indicator filtering
- Noise reduction (removes pyenv warnings, etc.)
- Preserved formatting for important messages

## Best Practices

1. **Use dry-run first** - Always preview with `--dry-run` before execution
2. **Leverage auto-JSON** - Let the system format output automatically  
3. **Use compact mode for scripts** - `--compact` for automated environments
4. **Control output length** - Use `--max-lines` for very verbose commands
5. **Review summaries** - JSON summaries highlight the most important data

## Troubleshooting

### Common Issues

**Q: JSON formatting isn't working**
A: Check if the command supports `--format json`. Use `--no-json` to disable if needed.

**Q: Output is too verbose**  
A: Use `--compact` or reduce `--max-lines` (default is 15).

**Q: Missing command output**
A: The system filters noise automatically. Use `--no-json` to see raw output.

**Q: Styling looks broken**
A: Ensure you have Rich library >= 13.9.4 and a compatible terminal.

## Future Enhancements

Planned improvements include:

- Custom output templates per action type
- Integration with external formatting tools
- Configurable summarization rules
- Export capabilities (JSON, CSV, etc.)
- Real-time streaming for long-running commands

The enhanced output system makes escmd actions more professional, readable, and suitable for both interactive use and automation scenarios.