# Action Output Enhancements

## Overview

This document describes the enhancements made to improve the user experience of the `escmd action run` command output. These improvements focus on better formatting, readability, and providing appropriate levels of detail based on user preferences.

## Key Improvements

### 1. Enhanced Host List Formatting

**Problem:** Long comma-separated host lists were displayed on single lines, causing awkward wrapping and poor readability.

**Before:**
```
Original value:
sjc01-c01-ess05-*,sjc01-c02-ess04-*,sjc01-c02-ess05-*,sjc01-c02-ess06-*,sjc01-c02-ess01-*,sjc01-c02-ess02-*,sjc01-c02-ess03-*,sjc01-c01-ess07-*,sjc01-c01-ess11-*,sjc01-c01-ess20-*,sjc01-c01-ess42-*,sjc01-c01-ess50-*,server01-*
```

**After:**
```
Original value:
  sjc01-c01-ess05-*, sjc01-c02-ess04-*, sjc01-c02-ess05-*
  ... (6 more hosts) ...
  sjc01-c01-ess42-*, sjc01-c01-ess50-*, server01-*
```

### 2. Improved JSON Handling

**Enhancement:** Separate JSON configuration output from descriptive text for better readability.

- JSON output is now displayed in a separate panel titled "📋 Configuration Applied"
- JSON is only shown in non-compact mode to avoid clutter
- Better parsing to detect JSON at the end of command output

### 3. New Output Modes

Added three new command-line options to control output verbosity:

#### `--quiet` Mode
- Shows minimal output during execution
- Displays step names without detailed panels
- Shows final summary in compact format
- Example: `escmd action run add-host --param-host server01 --quiet`

#### `--summary-only` Mode  
- Shows only the final execution summary
- Skips all step-by-step output
- Perfect for scripting and automation
- Example: `escmd action run add-host --param-host server01 --summary-only`

#### Enhanced `--compact` Mode
- Existing mode now provides better formatted compact output
- Cleaner summary format
- Reduced visual noise while maintaining essential information

### 4. Better Step Descriptions

**Updated action definitions** with more descriptive step names and descriptions:

**Before:**
```yaml
- name: Add Exclusion to Template
  description: "Update the manual template to exclude the specified host"
```

**After:**
```yaml
- name: Update Index Template
  description: "Update manual template to exclude {{ host }}-* from new index allocation"
```

### 5. Enhanced Error Display

- Error output is now always shown (even in compact mode) but with better formatting
- Failed steps provide clearer feedback
- Improved error summary at the end of execution

## Usage Examples

### Standard Output (Default)
```bash
./escmd.py action run add-host --param-host server01
```
Shows full detailed output with panels, command details, and formatted results.

### Quiet Mode
```bash
./escmd.py action run add-host --param-host server01 --quiet
```
Output:
```
Executing action: add-host
Parameters: host=server01

Step 1/2: Update Index Template
✓ Step completed
Step 2/2: Apply Cluster Exclusion
✓ Step completed

✓ Action 'add-host' completed: 2/2 steps successful
```

### Summary Only Mode
```bash
./escmd.py action run add-host --param-host server01 --summary-only
```
Output:
```
✓ Action 'add-host' completed: 2/2 steps successful
```

### Compact Mode (Enhanced)
```bash
./escmd.py action run add-host --param-host server01 --compact
```
Shows condensed panels with essential information only.

## Technical Implementation

### Key Changes Made

1. **Enhanced Text Processing** (`_display_enhanced_text_output`)
   - Smart detection of host lists
   - Improved line wrapping and grouping
   - Better handling of long comma-separated values

2. **Separated JSON and Text Output**
   - JSON detection at end of command output
   - Separate display logic for structured vs. unstructured data
   - Conditional JSON display based on mode flags

3. **Mode-Aware Display Logic**
   - All display functions now check for quiet/summary modes
   - Progressive enhancement: summary < quiet < compact < full
   - Consistent formatting across all modes

4. **Improved Action Definitions**
   - More descriptive step names using parameter interpolation
   - Better action descriptions
   - Clearer parameter descriptions

## Benefits

1. **Better Readability**: Long host lists and configuration data are now properly formatted
2. **Flexible Output**: Users can choose the level of detail appropriate for their use case
3. **Script-Friendly**: `--summary-only` mode perfect for automation and CI/CD pipelines
4. **Reduced Clutter**: Less visual noise while maintaining essential information
5. **Enhanced UX**: Step names and descriptions provide clearer context about what's happening

## Future Enhancements

Potential areas for further improvement:

1. **Progress Indicators**: Add progress bars for long-running operations
2. **Timing Information**: Show execution time for each step
3. **Resource Usage**: Display impact metrics (e.g., "5 shards will be moved")
4. **Interactive Mode**: Allow users to review and approve each step
5. **Output Templates**: User-customizable output formats