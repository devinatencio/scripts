# ILM Policy Creation Feature Implementation

## Overview

This document describes the implementation of the ILM policy creation feature added to the escmd utility. This feature allows users to create Index Lifecycle Management policies directly from the command line using JSON definitions.

## Implementation Summary

### 1. Command Line Interface (CLI)

**File**: `escmd/cli/argument_parser.py`

Added a new `create-policy` subcommand to the ILM command group with the following parameters:
- `policy_name`: Required - Name for the new ILM policy
- `policy_definition`: Optional - JSON policy definition (inline) or path to JSON file
- `--file`: Optional - Path to JSON file containing policy definition
- `--format`: Optional - Output format (json or table, default: table)

**Usage Examples**:
```bash
# From file (method 1)
./escmd.py -l dev ilm create-policy my-policy policy.json

# From file (method 2)
./escmd.py -l dev ilm create-policy my-policy --file policy.json

# Inline JSON
./escmd.py -l dev ilm create-policy test-policy '{"policy":{"phases":{...}}}'

# With JSON output
./escmd.py -l dev ilm create-policy my-policy policy.json --format json
```

### 2. Command Handler

**File**: `escmd/handlers/lifecycle_handler.py`

**Changes Made**:
- Added `create-policy` action to the main ILM handler switch statement
- Implemented `_handle_ilm_create_policy()` method with comprehensive functionality
- Added imports for `os` module
- Updated help system to include create-policy command and examples

**Key Features of the Handler**:
- **Multiple Input Methods**: Supports JSON files via direct path, --file flag, or inline JSON
- **Intelligent File Detection**: Distinguishes between file paths and inline JSON
- **Comprehensive Error Handling**: Handles missing files, invalid JSON, missing definitions
- **Rich Output Formatting**: Beautiful success panels showing policy details
- **Policy Validation**: Validates JSON structure before creation
- **Source Tracking**: Shows whether policy came from file or inline JSON

### 3. ES Client Integration

**File**: `escmd/esclient.py`

Added a delegation method `create_ilm_policy()` that forwards requests to the existing `SettingsCommands.create_ilm_policy()` method, maintaining consistency with the existing architecture.

### 4. Core Implementation

**File**: `escmd/commands/settings_commands.py`

The actual ILM policy creation is handled by the existing `create_ilm_policy()` method in `SettingsCommands`, which:
- Uses Elasticsearch's `ilm.put_lifecycle()` API
- Handles API response formatting
- Provides error handling for Elasticsearch API errors

## Technical Architecture

### Command Flow

1. **CLI Parsing** → `argument_parser.py` parses the create-policy command
2. **Command Routing** → `command_handler.py` routes to `lifecycle_handler`
3. **Handler Processing** → `lifecycle_handler.py` processes the request
4. **ES Client Call** → `esclient.py` delegates to settings commands
5. **API Execution** → `settings_commands.py` calls Elasticsearch API
6. **Response Formatting** → Results formatted and displayed to user

### Input Processing Logic

```python
def _handle_ilm_create_policy(self):
    # 1. Check for --file flag first
    if policy_file:
        load_from_file(policy_file)
    
    # 2. Check positional argument
    elif policy_definition:
        if is_file_path(policy_definition):
            load_from_file(policy_definition)
        else:
            parse_inline_json(policy_definition)
    
    # 3. Error if no definition provided
    else:
        show_usage_error()
```

### Error Handling Strategy

1. **File Not Found**: Clear message when JSON files don't exist
2. **Invalid JSON**: Detailed JSON parsing error messages
3. **Missing Definition**: Helpful usage examples
4. **API Errors**: Elasticsearch error messages passed through
5. **Validation Errors**: Policy structure validation

## Feature Capabilities

### Input Methods Supported

1. **Direct File Path**: `./escmd.py ilm create-policy name file.json`
2. **File Flag**: `./escmd.py ilm create-policy name --file file.json`
3. **Inline JSON**: `./escmd.py ilm create-policy name '{"policy":{...}}'`

### Output Formats

#### Table Format (Default)
- Rich formatted success panel
- Shows policy name, source, status, and phases
- Color-coded with emojis for visual appeal

#### JSON Format
- Machine-readable output
- Includes policy name, source, ES response, and status
- Suitable for automation and scripting

### Error Messages

- **File Not Found**: Specific error for missing policy files
- **Invalid JSON**: Detailed JSON syntax error reporting
- **Missing Definition**: Usage examples provided
- **Elasticsearch Errors**: Raw API error messages displayed

## Files Modified

1. **`escmd/cli/argument_parser.py`**
   - Added create-policy subcommand definition

2. **`escmd/handlers/lifecycle_handler.py`**
   - Added os import
   - Added create-policy handler case
   - Implemented _handle_ilm_create_policy() method
   - Updated help text with new command

3. **`escmd/esclient.py`**
   - Added create_ilm_policy() delegation method

## Example Policy Files Created

1. **`simple-ilm-policy.json`**: Basic 3-phase policy (hot → warm → delete)
2. **`example-ilm-policy.json`**: Comprehensive 4-phase policy with advanced settings

## Documentation Created

1. **`ILM_POLICY_CREATION.md`**: Complete user guide with examples
2. **`ILM_POLICY_CREATE_IMPLEMENTATION.md`**: This technical implementation document

## Testing Performed

### Successful Test Cases

1. ✅ Create policy from JSON file (direct path)
2. ✅ Create policy from JSON file (--file flag)
3. ✅ Create policy from inline JSON
4. ✅ JSON output format
5. ✅ Table output format (default)
6. ✅ Policy validation and creation in Elasticsearch
7. ✅ Help system integration
8. ✅ CLI help display

### Error Handling Test Cases

1. ✅ Invalid JSON syntax
2. ✅ Missing policy definition
3. ✅ Non-existent file paths
4. ✅ Invalid policy structure (ES validation)

## Integration Points

### Existing Systems Used

1. **Theme System**: Error panels use existing theme styling
2. **Rich Library**: Consistent with existing UI formatting  
3. **ES Client Architecture**: Follows delegation pattern
4. **Command Registry**: Integrates with existing command system
5. **Configuration Management**: Uses existing config system

### Backward Compatibility

- No breaking changes to existing functionality
- New command is purely additive
- Follows established patterns and conventions
- Maintains existing CLI argument structure

## Future Enhancement Opportunities

1. **Policy Templates**: Pre-built policy templates for common use cases
2. **Policy Validation**: Advanced validation beyond JSON structure
3. **Bulk Creation**: Create multiple policies from a directory
4. **Policy Import/Export**: Export existing policies for reuse
5. **Interactive Mode**: Guided policy creation wizard

## Dependencies

### Required Python Modules
- `json`: JSON parsing and validation
- `os`: File system operations
- `rich`: UI components (existing dependency)

### Elasticsearch API
- `ilm.put_lifecycle()`: Core API for policy creation
- Elasticsearch 6.6+ for ILM support

## Security Considerations

1. **File Access**: Only reads files, no write operations to policy files
2. **Input Validation**: JSON structure validation before API calls
3. **Error Information**: No sensitive data exposed in error messages
4. **API Security**: Uses existing ES authentication mechanisms

## Performance Impact

- **Minimal**: Single API call per policy creation
- **File I/O**: Only when reading policy files
- **JSON Parsing**: Standard library performance
- **UI Rendering**: Consistent with existing command performance

This implementation successfully adds comprehensive ILM policy creation capabilities to escmd while maintaining consistency with existing patterns and providing excellent user experience through rich formatting and helpful error handling.