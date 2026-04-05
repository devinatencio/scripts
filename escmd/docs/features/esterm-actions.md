# ESterm Action Integration

## Overview

This document describes the integration of the action system into ESterm, allowing users to execute predefined action sequences directly from within the interactive terminal environment.

## Features Added

### 1. Action Command Support

ESterm now supports the `action` command with the following subcommands:

- `action list` - List all available actions
- `action show <action_name>` - Show details for a specific action
- `action run <action_name> [options]` - Execute an action sequence

### 2. Full Argument Parsing

The integration uses the same argument parser as the main escmd application, ensuring:
- Consistent argument handling between CLI and interactive modes
- All action options are supported (--dry-run, --quiet, --summary-only, etc.)
- Parameter passing works identically (--param-name value)
- Error messages and validation are consistent

### 3. Cluster Context Integration

Actions executed within ESterm automatically use:
- The currently connected cluster
- Current location configuration
- Proper authentication context
- Real-time cache management

## Usage Examples

### List Available Actions
```
esterm(◦production)>
➤ action list
```

### Show Action Details
```
esterm(◦production)>
➤ action show add-host
```

### Execute Actions
```
esterm(◦production)>
➤ action run health-check

esterm(◦production)>
➤ action run add-host --param-host server01

esterm(◦production)>
➤ action run add-host --param-host server01 --dry-run

esterm(◦production)>
➤ action run add-host --param-host server01 --quiet

esterm(◦production)>
➤ action run maintenance-mode --param-action enable --summary-only
```

## Implementation Details

### Command Processing Flow

1. **Command Recognition**: The `action` command is recognized as a built-in command
2. **Subcommand Routing**: Subcommands (list/show/run) are routed to appropriate handlers
3. **Argument Parsing**: Uses the real escmd argument parser for consistency
4. **Context Injection**: Current cluster connection and configuration are injected
5. **Execution**: ActionHandler executes with full escmd context

### Code Integration Points

#### 1. Command Processor (`esterm_modules/command_processor.py`)

- Added `action` to `builtin_commands` set
- Added `_handle_action_command()` method for routing subcommands
- Added `_execute_action_list()`, `_execute_action_show()`, `_execute_action_run()` methods
- Integrated proper argument parsing using existing `argument_parser`

#### 2. Help System (`esterm_modules/help_system.py`)

- Added action command description to built-in help
- Added comprehensive help examples for action usage
- Integrated action into command suggestion system

### Error Handling

The integration includes robust error handling for:

- **Connection Requirements**: Actions that require cluster connections validate connectivity
- **Argument Parsing**: Invalid arguments are caught and reported clearly
- **Action Execution**: Action failures are handled gracefully without crashing esterm
- **Debug Mode**: Enhanced error reporting when `ESTERM_DEBUG` is enabled

### Connection Validation

Action execution requires an active cluster connection:

```
esterm(◦disconnected)>
➤ action run health-check
[red]Action execution requires an active cluster connection.[/red]
[dim]Use 'connect' to connect to a cluster first.[/dim]
```

## Benefits

### 1. Seamless Integration
- Actions work identically in both CLI and interactive modes
- No learning curve for users familiar with escmd actions
- Consistent output formatting and behavior

### 2. Context Awareness
- Actions automatically use the current cluster connection
- No need to specify cluster information repeatedly
- Leverages existing esterm session state

### 3. Enhanced Productivity
- Execute complex multi-step operations from within esterm
- Combine actions with other esterm commands in workflows
- Real-time feedback and monitoring capabilities

### 4. Safety Features
- Dry-run support for testing actions safely
- Clear indication of what will be executed
- Graceful error handling and recovery

## Troubleshooting

### Action Not Found
```
esterm(◦production)>
➤ action show nonexistent-action
[red]Action 'nonexistent-action' not found[/red]
```

**Solution**: Use `action list` to see available actions

### Connection Required
```
esterm(◦disconnected)>
➤ action run health-check
[red]Action execution requires an active cluster connection.[/red]
```

**Solution**: Use `connect` command to establish cluster connection

### Invalid Arguments
```
esterm(◦production)>
➤ action run add-host --invalid-option
[red]Invalid arguments for action 'add-host'[/red]
```

**Solution**: Use `action show add-host` to see valid parameters and options

### Debug Mode
Enable debug mode for detailed error information:
```bash
export ESTERM_DEBUG=1
```

## Future Enhancements

### Planned Features
1. **Action History**: Track executed actions within esterm session
2. **Action Favorites**: Quick access to frequently used actions
3. **Action Scheduling**: Schedule actions to run at specific times
4. **Action Chaining**: Chain multiple actions together
5. **Custom Action Creation**: Create actions interactively within esterm

### Integration Opportunities
1. **Health Monitoring**: Integrate actions with health monitoring system
2. **Theme Integration**: Action output respects esterm themes
3. **Performance Metrics**: Track action execution performance
4. **Session Logging**: Include action execution in session logs

## Migration Notes

- Existing esterm sessions are not affected
- No configuration changes required
- All existing commands continue to work as before
- Action functionality is additive and non-breaking

This integration brings the full power of the escmd action system into the interactive esterm environment, providing a seamless and powerful cluster management experience.