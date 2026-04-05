# Enhanced Actions System Guide

The ESCMD Enhanced Actions System allows you to create sophisticated workflows that chain commands together, capture outputs, extract specific values, and pass data between steps. This is perfect for complex operations like rolling over indices and then deleting the old ones.

## Table of Contents
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [YAML Syntax](#yaml-syntax)
- [Output Capture](#output-capture)
- [JSON Path Extraction](#json-path-extraction)
- [Variable Interpolation](#variable-interpolation)
- [Conditional Execution](#conditional-execution)
- [Complete Examples](#complete-examples)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

Your original use case of rolling over an index and then deleting the old one is now easily achievable:

```yaml
- name: roll-igl
  description: "Rollover datastream and delete the old index"
  steps:
    - name: Rollover Indice
      action: rollover rehydrated_ams02-c01-logs-igl-main --format json
      description: "Rollover the datastream and capture the old index name"
      capture:
        old_index_name: "$.old_index"
        new_index_name: "$.new_index"
        rollover_success: "$.rolled_over"
    - name: Delete Old Index
      action: indices --delete {{ old_index_name }}
      description: "Delete the old index that was rolled over"
      condition: "{{ rollover_success }}"
      confirm: true
```

Run it with:
```bash
./escmd.py action run roll-igl
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Output Capture** | Store step outputs in variables for reuse |
| **JSON Extraction** | Extract specific values from JSON responses |
| **Variable Interpolation** | Use captured data in subsequent commands |
| **Conditional Execution** | Run steps based on previous results |
| **Safety Confirmations** | Built-in prompts for destructive operations |
| **Dry Run Mode** | Test actions without executing commands |
| **Parameter Support** | Create reusable parameterized actions |
| **Error Handling** | Graceful failure handling and reporting |

## YAML Syntax

### Basic Action Structure

```yaml
- name: action-name
  description: "What this action does"
  parameters:  # Optional
    - name: param_name
      type: string|integer|choice
      description: "Parameter description"
      required: true|false
      default: value
  steps:
    - name: Step Name
      action: command to execute
      description: "Step description"
      capture: # Optional - capture output
        variable_name: extraction_rule
      condition: "{{ condition_expression }}"  # Optional
      confirm: true|false  # Optional
```

### Step Properties

| Property | Required | Description |
|----------|----------|-------------|
| `name` | Yes | Human-readable step name |
| `action` | Yes | ESCMD command to execute |
| `description` | No | Detailed step description |
| `capture` | No | Output capture configuration |
| `condition` | No | When to execute this step |
| `confirm` | No | Require user confirmation |

## Output Capture

### Simple Capture
Store entire command output:
```yaml
capture: output_variable
```

### Advanced Capture
Extract specific values:
```yaml
capture:
  old_index: "$.old_index"
  new_index: "$.new_index"
  success: "$.rolled_over"
```

### Capture Methods

| Method | Syntax | Example |
|--------|--------|---------|
| JSONPath | `$.field.subfield` | `"$.old_index"` |
| Regex | `regex:pattern` | `"regex:Index: (.*)"` |
| Literal | `"literal value"` | `"completed"` |

## JSON Path Extraction

JSONPath allows you to extract specific values from JSON responses:

### Common Patterns

```yaml
# Basic field extraction
old_index: "$.old_index"

# Nested field extraction  
max_age: "$.conditions.max_age"

# Array element extraction
first_node: "$.nodes.0.name"

# Multiple extractions
capture:
  cluster_name: "$.cluster_name"
  node_count: "$.number_of_nodes"
  status: "$.status"
```

### Sample JSON and Extractions

Given this rollover response:
```json
{
  "acknowledged": true,
  "old_index": ".ds-logs-2025.01.15-000020",
  "new_index": ".ds-logs-2025.01.16-000021",
  "rolled_over": true,
  "conditions": {
    "max_age": "1d",
    "max_docs": 1000000
  }
}
```

You can extract:
```yaml
capture:
  old_index: "$.old_index"           # → .ds-logs-2025.01.15-000020
  new_index: "$.new_index"           # → .ds-logs-2025.01.16-000021
  success: "$.rolled_over"           # → true
  max_age: "$.conditions.max_age"    # → 1d
```

## Variable Interpolation

Use captured variables in subsequent steps with Jinja2 template syntax:

```yaml
# Capture in step 1
- name: Get Info
  action: rollover my-datastream --format json
  capture:
    old_index: "$.old_index"

# Use in step 2  
- name: Delete Old
  action: indices --delete {{ old_index }}
```

### Available Variables

- **Parameters**: `{{ param_name }}`
- **Captured Variables**: `{{ variable_name }}`
- **Built-in Variables**: Access to standard template functions

## Conditional Execution

Control when steps execute based on previous results:

### Simple Conditions
```yaml
condition: "{{ success }}"                    # Execute if success is truthy
condition: "{{ status == 'green' }}"          # Execute if status is green
condition: "{{ node_count > 3 }}"             # Execute if more than 3 nodes
```

### Complex Conditions
```yaml
condition: "{{ rolled_over == 'true' and dry_run != 'true' }}"
```

### Condition Examples

| Condition | When It Runs |
|-----------|--------------|
| `"{{ success }}"` | When success variable is true/non-empty |
| `"{{ status == 'green' }}"` | When status equals 'green' |
| `"{{ count > 5 }}"` | When count is greater than 5 |
| `"{{ not dry_run }}"` | When dry_run is false/empty |

## Complete Examples

### 1. Basic Rollover and Delete

```yaml
- name: simple-rollover
  description: "Rollover and delete old index"
  steps:
    - name: Rollover
      action: rollover my-datastream --format json
      capture:
        old_index: "$.old_index"
        success: "$.rolled_over"
    - name: Delete
      action: indices --delete {{ old_index }}
      condition: "{{ success }}"
      confirm: true
```

### 2. Safe Rollover with Health Checks

```yaml
- name: safe-rollover
  description: "Rollover with comprehensive safety checks"
  steps:
    - name: Pre-check Health
      action: health --format json
      capture:
        cluster_status: "$.status"
    - name: Rollover
      action: rollover my-datastream --format json
      condition: "{{ cluster_status == 'green' or cluster_status == 'yellow' }}"
      capture:
        old_index: "$.old_index"
        new_index: "$.new_index"
        success: "$.rolled_over"
    - name: Verify New Index
      action: indices {{ new_index }} --format json
      condition: "{{ success }}"
    - name: Delete Old Index
      action: indices --delete {{ old_index }}
      condition: "{{ success and old_index }}"
      confirm: true
    - name: Post-check Health
      action: health --format json
      condition: "{{ success }}"
```

### 3. Parameterized Rollover

```yaml
- name: param-rollover
  description: "Parameterized rollover for any datastream"
  parameters:
    - name: datastream
      type: string
      description: "Datastream name to rollover"
      required: true
    - name: delete_old
      type: string
      description: "Delete old index (yes/no)"
      default: "yes"
  steps:
    - name: Rollover
      action: rollover {{ datastream }} --format json
      capture:
        old_index: "$.old_index"
        success: "$.rolled_over"
    - name: Delete Old
      action: indices --delete {{ old_index }}
      condition: "{{ success and delete_old == 'yes' }}"
      confirm: true
```

### 4. Bulk Operations

```yaml
- name: cleanup-old-indices
  description: "Clean up indices older than specified days"
  parameters:
    - name: pattern
      type: string
      description: "Index pattern to match"
      required: true
    - name: days
      type: integer
      description: "Days old to delete"
      default: 30
  steps:
    - name: List Indices
      action: indices {{ pattern }} --format json
      capture:
        indices_data: "$.indices"
    - name: Health Check
      action: health --format json
      capture:
        status: "$.status"
    - name: Delete Old Indices
      action: indices --delete {{ pattern }} --older-than {{ days }}
      condition: "{{ status == 'green' }}"
      confirm: true
```

## Usage Examples

### Command Line Usage

```bash
# List all actions
./escmd.py action list

# Show action details
./escmd.py action show roll-igl

# Run action with dry-run (test mode)
./escmd.py action run roll-igl --dry-run

# Run action
./escmd.py action run roll-igl

# Run parameterized action
./escmd.py action run param-rollover \
  --param-datastream my-logs \
  --param-delete_old yes

# Run quietly (minimal output)
./escmd.py action run roll-igl --quiet

# Run with native output (no panels)
./escmd.py action run roll-igl --native-output
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Test without executing commands |
| `--quiet` | Minimal output |
| `--native-output` | Use original ESCMD formatting |
| `--param-name value` | Set parameter value |

## Best Practices

### 1. Always Use --format json for Data Extraction
```yaml
# Good
action: rollover my-datastream --format json

# Bad (can't extract structured data)
action: rollover my-datastream
```

### 2. Include Safety Checks
```yaml
# Always check cluster health before destructive operations
- name: Health Check
  action: health --format json
  capture:
    status: "$.status"

- name: Dangerous Operation  
  action: indices --delete {{ index }}
  condition: "{{ status != 'red' }}"
  confirm: true
```

### 3. Use Descriptive Names
```yaml
# Good
- name: rollover-and-cleanup
  steps:
    - name: Rollover Datastream to New Index
    - name: Delete Previous Index

# Bad  
- name: task1
  steps:
    - name: step1
    - name: step2
```

### 4. Handle Errors Gracefully
```yaml
# Include conditions to prevent execution on failure
- name: Cleanup
  action: indices --delete {{ old_index }}
  condition: "{{ rollover_success and old_index }}"
```

### 5. Use Parameters for Reusability
```yaml
# Create reusable actions with parameters instead of hardcoding values
parameters:
  - name: datastream
    type: string
    required: true
```

## Troubleshooting

### Common Issues

**1. Variable Not Found**
```
Error: variable 'old_index' not found
```
- **Solution**: Ensure the capture step succeeded and the JSONPath is correct
- **Debug**: Run with `--dry-run` to see captured variables

**2. JSONPath Extraction Failed**  
```
Warning: JSONPath extraction failed
```
- **Solution**: Verify the command returns JSON with `--format json`
- **Debug**: Check the exact JSON structure returned

**3. Condition Always False**
```
Skipping step: condition not met
```
- **Solution**: Check condition syntax and variable values
- **Debug**: Use simple conditions like `"{{ variable }}"` first

**4. Command Not Found**
```
Invalid command syntax
```
- **Solution**: Test the command manually first
- **Debug**: Ensure all variables are properly interpolated

### Debugging Tips

1. **Use Dry Run Mode**
   ```bash
   ./escmd.py action run my-action --dry-run
   ```

2. **Check Variable Capture**
   - Look for "Captured variable:" messages in output
   - Run individual commands manually to see JSON structure

3. **Test JSONPath Extraction**
   ```bash
   # Test the rollover command manually
   ./escmd.py rollover my-datastream --format json
   ```

4. **Simplify Complex Actions**
   - Start with simple capture/use patterns
   - Add complexity gradually

5. **Use Descriptive Conditions**
   ```yaml
   # Instead of complex conditions, use intermediate steps
   - name: Check Rollover Success
     condition: "{{ rolled_over == true }}"
   ```

### Getting Help

- Run `./escmd.py action --help` for CLI help
- Use `action show <action-name>` to see action details  
- Test individual commands before adding to actions
- Check the action YAML syntax carefully

## Migration from Simple Actions

### Before (Simple Action)
```yaml
- name: roll-igl
  steps:
    - name: Rollover Indice
      action: rollover rehydrated_ams02-c01-logs-igl-main
```

### After (Enhanced Action)
```yaml
- name: roll-igl
  description: "Rollover datastream and delete the old index"
  steps:
    - name: Rollover Indice
      action: rollover rehydrated_ams02-c01-logs-igl-main --format json
      description: "Rollover the datastream and capture the old index name"
      capture:
        old_index_name: "$.old_index"
        rollover_success: "$.rolled_over"
    - name: Delete Old Index
      action: indices --delete {{ old_index_name }}
      description: "Delete the old index that was rolled over"
      condition: "{{ rollover_success }}"
      confirm: true
```

The enhanced system is backward compatible - existing simple actions continue to work unchanged.

---

For more examples and advanced usage, see the `actions.yml` file in your ESCMD installation.