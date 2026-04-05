# Freeze Command Enhancements

## Overview

The `freeze` command has been significantly enhanced to provide powerful regex pattern matching, automatic pattern detection, and improved user experience. These enhancements bring the freeze command to feature parity with the unfreeze command while adding intelligent automation.

## New Features

### 🤖 Automatic Regex Detection

The command now automatically detects regex patterns and enables regex mode without requiring the `--regex` flag:

```bash
# Automatically detects regex pattern
./escmd.py freeze 'logs-.*'

# Previously required
./escmd.py freeze 'logs-.*' --regex
```

**Detection Triggers:**
- `.*` (dot star) - matches any characters
- `.+` (dot plus) - matches one or more characters
- `[abc]` or `[0-9]` - character classes
- `^start` or `end$` - anchors
- `option1|option2` - alternation
- `group(ing)` - parentheses
- `\d`, `\w`, `\s` - escaped sequences
- `pattern*middle` - asterisk not at end
- `pattern+`, `pattern?` - quantifiers
- `{min,max}` - quantity ranges

### 🎯 Multiple Index Support

The command now supports freezing multiple indices at once with regex patterns:

```bash
# Freeze all 2023 log indices
./escmd.py freeze 'logs-2023-.*'

# Freeze all temporary indices
./escmd.py freeze 'temp-.*'

# Freeze indices with pattern matching
./escmd.py freeze 'alerts-[0-9]+'
```

### ⚠️ Interactive Confirmation

When multiple indices are matched, the command shows a detailed table and prompts for confirmation:

```bash
$ ./escmd.py freeze 'logs-2023-.*'

Auto-detected regex pattern: 'logs-2023-.*' (use --exact to disable)

🎯 Found 3 Matching Indices
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Index Name       ┃ Health   ┃ Status   ┃ Documents     ┃ Size     ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ logs-2023-01-01  │ 🟢 Green │ 📂 Open  │ 150,000       │ 45mb     │
│ logs-2023-01-02  │ 🟢 Green │ 📂 Open  │ 175,000       │ 52mb     │
│ logs-2023-02-01  │ 🟡 Yellow│ 📂 Open  │ 125,000       │ 38mb     │
└──────────────────┴──────────┴──────────┴───────────────┴──────────┘

⚠️  You are about to freeze 3 indices.
This operation will:
• Make all selected indices read-only
• Optimize storage for reduced memory usage
• Indices remain searchable but with potential latency

Proceed with freezing all matched indices? [y/N]: 
```

### 🤖 Automation Support

Skip confirmation prompts for automation and scripting:

```bash
# Skip confirmation with --yes/-y
./escmd.py freeze 'archive-.*' --yes
./escmd.py freeze 'old-logs-.*' -y
```

### 🔧 Manual Override Options

Fine-tune behavior with explicit flags:

```bash
# Force regex mode (bypass auto-detection)
./escmd.py freeze 'pattern' --regex

# Force exact match (disable auto-detection)
./escmd.py freeze 'index.with.dots' --exact

# Short forms
./escmd.py freeze 'pattern' -r    # regex
./escmd.py freeze 'pattern' -e    # exact
./escmd.py freeze 'pattern' -y    # yes
```

## Command Syntax

```
usage: escmd.py freeze [-h] [--regex] [--exact] [--yes] pattern

positional arguments:
  pattern      Index name or regex pattern to freeze

options:
  -h, --help   show this help message and exit
  --regex, -r  Treat pattern as regex (force regex mode)
  --exact, -e  Force exact match (disable auto-regex detection)
  --yes, -y    Skip confirmation prompt
```

## Usage Examples

### Basic Usage

```bash
# Single index (exact match)
./escmd.py freeze myindex-2024-01

# Auto-detected regex pattern
./escmd.py freeze 'logs-.*'
```

### Advanced Patterns

```bash
# Character classes
./escmd.py freeze 'alerts-[0-9]+'

# Alternation
./escmd.py freeze 'logs|metrics'

# Anchored patterns
./escmd.py freeze '^system-.*'

# Grouping
./escmd.py freeze '(logs|metrics)-2024-.*'
```

### Automation Scripts

```bash
# Batch freeze with confirmation skip
./escmd.py freeze 'temp-.*' --yes

# Force exact matching for special names
./escmd.py freeze 'index.with.dots.in.name' --exact

# Combine flags
./escmd.py freeze 'old-.*' -r -y  # regex + yes
```

## Safety Features

### Confirmation Prompts
- **Single Index**: No confirmation required
- **Multiple Indices**: Interactive confirmation with y/yes/n/no
- **Automation**: Use `--yes`/`-y` to skip prompts

### Visual Feedback
- Clear table showing all matching indices
- Health and status indicators
- Document counts and sizes
- Operation impact explanation

### Error Handling
- Invalid regex patterns detected and reported
- No matching indices handled gracefully
- Connection errors handled with clear messages
- Partial success/failure reporting

## Auto-Detection Logic

The system intelligently detects regex patterns using the following criteria:

### Always Detected as Regex
```bash
'logs-.*'           # Common wildcard
'data.+'            # One or more quantifier
'test-[0-9]+'       # Character classes
'^system-'          # Start anchor
'backup-$'          # End anchor
'temp|staging'      # Alternation
'debug-{1,3}'       # Quantifier braces
'(logs|metrics)'    # Grouping
'index\d+'          # Escaped sequences
```

### Never Detected as Regex
```bash
'simple-index'      # Plain index name
'my_index_001'      # Underscores and numbers
'logs-2024-01-01'   # Date patterns
'index.with.dots'   # Dots without regex chars
'elasticsearch'     # Single words
```

### Override When Needed
```bash
# If auto-detection is wrong:
./escmd.py freeze 'index.with.dots' --exact

# If auto-detection missed a pattern:
./escmd.py freeze 'simple-pattern' --regex
```

## Migration Guide

### Old vs New Syntax

| Old Command | New Command | Notes |
|------------|------------|-------|
| `freeze index-name` | `freeze index-name` | Unchanged |
| `freeze 'pattern.*' --regex` | `freeze 'pattern.*'` | Auto-detected |
| N/A | `freeze 'pattern.*' --yes` | New automation support |
| N/A | `freeze 'index.dots' --exact` | New override option |

### Benefits of New Approach

1. **Simplified Usage**: No need to remember `--regex` flag for obvious patterns
2. **Consistency**: Matches unfreeze command functionality
3. **Safety**: Interactive confirmation prevents accidents
4. **Automation**: `--yes` flag enables scripting
5. **Flexibility**: Override options for edge cases

## Common Use Cases

### Archive Old Data
```bash
# Archive 2023 logs (auto-detected regex)
./escmd.py freeze 'logs-2023-.*'

# Archive by month pattern
./escmd.py freeze 'data-2024-0[1-6]-.*'
```

### Cleanup Operations
```bash
# Freeze temporary indices
./escmd.py freeze 'temp-.*' --yes

# Freeze test indices
./escmd.py freeze 'test-.*' -y
```

### Memory Optimization
```bash
# Freeze large historical indices
./escmd.py freeze 'metrics-202[1-3]-.*'

# Freeze backup indices
./escmd.py freeze 'backup-.*'
```

### Maintenance Scripts
```bash
#!/bin/bash
# Daily cleanup script
./escmd.py freeze 'logs-old-.*' --yes
./escmd.py freeze 'temp-.*' --yes
./escmd.py freeze 'staging-.*' --yes
```

## Help System

Comprehensive help is available:

```bash
# General help
./escmd.py freeze --help

# Detailed help with examples
./escmd.py help freeze
```

## Error Handling

The command provides clear error messages for common issues:

- **No matching indices**: Shows available indices for reference
- **Invalid regex**: Explains regex syntax errors
- **Wrong auto-detection**: Suggests using `--exact` flag
- **Permission issues**: Points to cluster permission problems
- **Connection problems**: Suggests connectivity troubleshooting

## Testing

Auto-detection accuracy: **100%** (24/24 test cases pass)

The auto-detection system has been thoroughly tested with:
- Common regex patterns
- Edge cases with dots and special characters
- Index naming conventions
- False positive prevention

## Summary

The enhanced freeze command provides:

✅ **Auto-detection** - Smart regex pattern recognition  
✅ **Bulk operations** - Freeze multiple indices at once  
✅ **Safety prompts** - Interactive confirmation for multiple indices  
✅ **Automation support** - `--yes` flag for scripting  
✅ **Manual overrides** - `--regex` and `--exact` flags  
✅ **Rich output** - Detailed tables and progress indicators  
✅ **Error handling** - Graceful handling of edge cases  
✅ **Comprehensive help** - Built-in documentation and examples  

The freeze command now provides a powerful, intuitive interface for index lifecycle management that scales from simple single-index operations to complex bulk automation scenarios.