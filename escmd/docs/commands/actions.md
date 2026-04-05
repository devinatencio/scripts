# Actions Command

The `action` command allows you to define and execute reusable sequences of commands that can be executed together. This is particularly useful for common administrative workflows, maintenance tasks, and complex operations that require multiple steps.

## Overview

Actions are powerful automation tools that enable you to:
- **Standardize workflows**: Define consistent procedures for common tasks
- **Reduce errors**: Pre-defined, tested command sequences
- **Save time**: Execute multiple commands with a single action
- **Parameterize operations**: Use variables to customize behavior
- **Ensure safety**: Built-in dry-run and confirmation features

## Command Syntax

```bash
escmd action <subcommand> [options]
```

### Subcommands

- `list` - List all available actions
- `show <action_name>` - Show details for a specific action
- `run <action_name>` - Execute an action sequence

## Usage Examples

### List Available Actions
```bash
escmd action list
```

### Show Action Details
```bash
escmd action show add-host
escmd action show maintenance-mode
```

### Execute Actions
```bash
# Basic execution
escmd action run health-check

# With parameters
escmd action run add-host --param-host server01

# Dry run (preview mode)
escmd action run add-host --param-host server01 --dry-run

# Quiet mode (minimal output)
escmd action run maintenance-mode --param-action enable --quiet

# Summary only (for scripts)
escmd action run rollover-logs --param-pattern "logs-*" --summary-only
```

## Action Parameters

Actions can accept parameters to customize their behavior:

```bash
# String parameters
escmd action run add-host --param-host web01

# Multiple parameters
escmd action run rollover-and-backup \
  --param-index-pattern "application-logs-*" \
  --param-snapshot-name "backup-$(date +%Y%m%d)"

# Choice parameters
escmd action run maintenance-mode --param-action enable
escmd action run maintenance-mode --param-action disable
```

## Output Control Options

### Standard Mode (Default)
Full detailed output with formatted panels and comprehensive information.

### Quiet Mode
```bash
escmd action run add-host --param-host server01 --quiet
```
Shows minimal output during execution while maintaining clarity.

### Summary Only Mode
```bash
escmd action run add-host --param-host server01 --summary-only
```
Perfect for scripting - shows only final execution summary.

### Compact Mode
```bash
escmd action run add-host --param-host server01 --compact
```
Reduced visual elements while maintaining essential information.

### Dry Run Mode
```bash
escmd action run add-host --param-host server01 --dry-run
```
Preview what will be executed without making any changes.

## Common Action Types

### Host Management
- `add-host` - Add a host to exclusion lists
- `remove-host` - Remove a host from exclusions
- `host-maintenance` - Prepare host for maintenance

### Index Operations
- `rollover-indices` - Rollover datastream indices
- `index-cleanup` - Remove old indices based on age
- `force-merge` - Optimize index segments

### Cluster Maintenance
- `maintenance-mode` - Enable/disable cluster maintenance mode
- `health-check` - Comprehensive cluster health verification
- `rebalance-cluster` - Optimize shard distribution

### Template Management
- `update-templates` - Apply template changes across environments
- `template-backup` - Create template backups

## ESterm Integration

Actions are fully integrated with ESterm (interactive mode):

```bash
# In ESterm
esterm(◦production)> action list
esterm(◦production)> action show add-host  
esterm(◦production)> action run add-host --param-host server01
```

Benefits in ESterm:
- **Context aware**: Automatically uses current cluster connection
- **No reconnection**: Leverages existing session
- **Interactive feedback**: Real-time progress in terminal

## Safety Features

### Confirmation Prompts
Some actions include confirmation prompts for destructive operations:
```
⚠️  This action will permanently delete indices matching 'old-logs-*'
Continue? [y/N]:
```

### Dry Run Validation
Always test actions with `--dry-run` before execution:
```bash
escmd action run dangerous-cleanup --param-pattern "old-*" --dry-run
```

### Error Handling
- Actions stop on first error by default
- Clear error messages with suggested fixes
- Graceful rollback capabilities where possible

## Best Practices

### 1. Use Dry Run First
```bash
# Always preview before executing
escmd action run my-action --param-host server01 --dry-run
# Then execute
escmd action run my-action --param-host server01
```

### 2. Validate Parameters
Use `action show` to verify required parameters:
```bash
escmd action show add-host
```

### 3. Choose Appropriate Output Mode
- **Interactive use**: Standard mode (default)
- **Scripts/CI**: `--summary-only` mode
- **Debugging**: `--verbose` or standard mode
- **Minimal noise**: `--quiet` mode

### 4. Monitor Long-Running Actions
For operations that may take time, monitor progress:
```bash
# In another terminal, check cluster status
escmd health-detail
```

## Troubleshooting

### Action Not Found
```bash
escmd action show nonexistent-action
# Error: Action 'nonexistent-action' not found
```
**Solution**: Use `escmd action list` to see available actions

### Missing Parameters
```bash
escmd action run add-host
# Error: Required parameter 'host' not provided
```
**Solution**: Add required parameters: `--param-host server01`

### Connection Issues
```bash
escmd action run health-check
# Error: Unable to connect to cluster
```
**Solution**: Check cluster connectivity and configuration

### Action Execution Failures
- Review error messages carefully
- Use `--dry-run` to validate before execution
- Check cluster health and resources
- Verify permissions and authentication

## Related Documentation

- **Usage Examples**: See [Actions Usage Guide](../guides/actions-usage-guide.md) for detailed examples
- **Command Reference**: See [Actions Command Reference](../reference/actions-command-reference.md) for syntax details
- **ESterm Integration**: See [ESterm Actions](../features/esterm-actions.md) for interactive usage
- **Creating Actions**: See action definition examples in the main `actions.yml` file

## File Locations

- **Action definitions**: `actions.yml` (in project root)
- **Action handler**: `handlers/action_handler.py`
- **Template backups**: `backups/templates/` (created as needed)

The actions system provides a powerful way to automate complex Elasticsearch administration tasks while maintaining safety through validation, dry-run capabilities, and comprehensive error handling.