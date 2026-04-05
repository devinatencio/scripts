# Actions Usage Examples

The Actions system in `escmd` allows you to define reusable sequences of commands that can be executed together. This is particularly useful for common administrative workflows, maintenance tasks, and complex operations that require multiple steps.

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [Action File Format](#action-file-format)
- [Command Examples](#command-examples)
- [Parameter Types](#parameter-types)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)

## Overview

Actions are defined in the `actions.yml` file and consist of:
- **Name**: Unique identifier for the action
- **Description**: Human-readable description of what the action does
- **Parameters**: Input parameters that customize the action behavior
- **Steps**: Sequential list of commands to execute

## Basic Usage

### List Available Actions
```bash
escmd action list
```

### Show Action Details
```bash
escmd action show add-host
```

### Run an Action
```bash
escmd action run add-host --param-host server01
```

### Dry Run (Preview Mode)
```bash
escmd action run add-host --param-host server01 --dry-run
```

## Action File Format

The `actions.yml` file uses the following structure:

```yaml
actions:
  - name: action-name
    description: "Description of what this action does"
    parameters:
      - name: parameter_name
        type: string|integer|choice
        description: "Parameter description"
        required: true|false
        default: default_value  # optional
        choices: [choice1, choice2]  # for choice type
    steps:
      - name: Step Name
        action: escmd command with {{ parameter }} placeholders
        description: "Step description"
        condition: "{{ parameter == 'value' }}"  # optional
        confirm: true|false  # optional, prompts user
```

## Command Examples

### 1. Host Management

**Add Host to Exclusions:**
```bash
escmd action run add-host --param-host server01
```

This action:
1. Updates templates to exclude the host
2. Adds allocation exclusion rules

**Remove Host from Exclusions:**
```bash
escmd action run remove-host --param-host server01
```

### 2. Index Management

**Rollover and Backup:**
```bash
escmd action run rollover-and-backup \
  --param-index-pattern "logs-*" \
  --param-snapshot-name "logs-backup-$(date +%Y%m%d)"
```

**Index Cleanup:**
```bash
escmd action run index-cleanup \
  --param-pattern "old-logs-*" \
  --param-days 30
```

### 3. Maintenance Mode

**Enable Maintenance Mode:**
```bash
escmd action run maintenance-mode --param-action enable
```

**Disable Maintenance Mode:**
```bash
escmd action run maintenance-mode --param-action disable
```

## Parameter Types

### String Parameters
```yaml
- name: hostname
  type: string
  description: "Server hostname"
  required: true
```
Usage: `--param-hostname web01`

### Integer Parameters
```yaml
- name: days
  type: integer
  description: "Number of days"
  required: true
  default: 30
```
Usage: `--param-days 7`

### Choice Parameters
```yaml
- name: action
  type: choice
  choices: ["enable", "disable"]
  description: "Action to perform"
  required: true
```
Usage: `--param-action enable`

## Advanced Features

### Conditional Steps

Steps can be executed conditionally based on parameter values:

```yaml
steps:
  - name: Enable Maintenance
    action: allocation exclude _name "data-*"
    condition: "{{ action == 'enable' }}"
  - name: Disable Maintenance
    action: allocation exclude-reset
    condition: "{{ action == 'disable' }}"
```

### Confirmation Prompts

Add user confirmation for destructive operations:

```yaml
steps:
  - name: Delete Old Indices
    action: indices --delete {{ pattern }}
    confirm: true
```

### Template Variables

Use Jinja2 template syntax for dynamic values:

```yaml
steps:
  - name: Create Snapshot
    action: snapshots create "backup-{{ pattern }}-{{ timestamp }}"
```

## Best Practices

### 1. Use Descriptive Names
```yaml
# Good
- name: rollover-and-backup-logs
  description: "Rollover log indices and create backup snapshots"

# Bad
- name: rab
  description: "Does stuff"
```

### 2. Validate Parameters
Always define parameter types and mark required parameters:

```yaml
parameters:
  - name: host
    type: string
    description: "Hostname without domain suffix"
    required: true
  - name: timeout
    type: integer
    description: "Operation timeout in seconds"
    default: 300
```

### 3. Add Safety Checks
Use dry-run mode and confirmation prompts for destructive operations:

```yaml
steps:
  - name: Delete Indices
    action: indices --delete {{ pattern }}
    confirm: true
    description: "⚠️  This will permanently delete matching indices"
```

### 4. Document Your Actions
Provide clear descriptions for actions and steps:

```yaml
- name: weekly-maintenance
  description: "Weekly maintenance routine: cleanup old indices, optimize templates, create backups"
  steps:
    - name: Clean Old Indices
      action: indices --delete "logs-*" --older-than 7d
      description: "Remove log indices older than 7 days"
    - name: Optimize Templates
      action: templates optimize
      description: "Apply template optimizations"
```

### 5. Use Meaningful Step Names
```yaml
# Good
steps:
  - name: Exclude Host from Allocation
    action: allocation exclude host "{{ host }}-*"
  - name: Wait for Shard Relocation
    action: shards --wait-for-relocating 0

# Bad
steps:
  - name: Step 1
    action: allocation exclude host "{{ host }}-*"
  - name: Step 2
    action: shards --wait-for-relocating 0
```

### 6. Group Related Actions
Organize your actions.yml file with comments:

```yaml
actions:
  # Host Management Actions
  - name: add-host
    # ... action definition
  
  - name: remove-host
    # ... action definition

  # Index Management Actions
  - name: rollover-indices
    # ... action definition
```

## Common Action Patterns

### 1. Host Maintenance Pattern
```yaml
- name: host-maintenance
  description: "Prepare host for maintenance by relocating shards"
  parameters:
    - name: host
      type: string
      required: true
  steps:
    - name: Exclude Host
      action: allocation exclude host "{{ host }}-*"
    - name: Wait for Relocation
      action: shards --wait-for-relocating 0
    - name: Verify No Shards
      action: shards --server {{ host }}
```

### 2. Index Lifecycle Pattern
```yaml
- name: index-lifecycle
  description: "Complete index lifecycle: create, populate, rollover, backup"
  parameters:
    - name: base_name
      type: string
      required: true
  steps:
    - name: Create Index
      action: create-index {{ base_name }}-000001
    - name: Configure ILM
      action: ilm apply {{ base_name }}-policy {{ base_name }}-*
    - name: Force Rollover
      action: rollover {{ base_name }}-*
    - name: Create Backup
      action: snapshots create {{ base_name }}-backup
```

### 3. Cluster Health Check Pattern
```yaml
- name: health-check
  description: "Comprehensive cluster health verification"
  steps:
    - name: Basic Health
      action: health
    - name: Node Status
      action: nodes --format table
    - name: Index Status
      action: indices --status red,yellow
    - name: Shard Analysis
      action: shards --size --limit 10
```

## Error Handling

When an action step fails:
1. The error is logged and displayed
2. You're prompted whether to continue with remaining steps
3. A summary shows successful and failed steps
4. Failed steps include error details

Use dry-run mode to validate actions before execution:
```bash
escmd action run complex-maintenance --dry-run
```

## Integration with Existing Commands

Actions can use any existing escmd command:
- `health`, `nodes`, `indices`
- `allocation`, `snapshots`, `ilm`
- `template-modify`, `cluster-settings`
- And many more!

The action system provides a powerful way to automate complex Elasticsearch administration tasks while maintaining safety through dry-run mode and confirmation prompts.