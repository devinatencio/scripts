# Template List Operations Guide

This guide provides detailed information about using the `template-modify` command to work with comma-separated list fields in Elasticsearch templates, such as host exclusion lists.

## Overview

The `template-modify` command supports sophisticated list operations for fields that contain comma-separated values. This is particularly useful for managing host exclusion lists, node attributes, and other multi-value settings.

## List Operations

### append
Adds new values to a comma-separated list, automatically avoiding duplicates.

**Syntax:**
```bash
escmd template-modify <template> -f <field_path> -o append -v "value1,value2,..."
```

**Example:**
```bash
# Add hosts to exclusion list
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "host1-*,host2-*"
```

**Behavior:**
- Parses existing comma-separated values
- Adds new values that don't already exist
- Preserves existing values
- Returns properly formatted comma-separated string

### remove
Removes specific values from a comma-separated list.

**Syntax:**
```bash
escmd template-modify <template> -f <field_path> -o remove -v "value1,value2,..."
```

**Example:**
```bash
# Remove hosts from exclusion list (bring back online)
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o remove -v "old-host-*,maintenance-host-*"
```

**Behavior:**
- Parses existing comma-separated values
- Removes all instances of specified values
- Preserves remaining values
- Returns properly formatted comma-separated string

### set
Replaces the entire list with new values.

**Syntax:**
```bash
escmd template-modify <template> -f <field_path> -o set -v "value1,value2,..."
```

**Example:**
```bash
# Replace entire exclusion list
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o set -v "new-host1-*,new-host2-*,new-host3-*"
```

## Common Use Cases

### Host Exclusion Management

Host exclusion lists are used to prevent Elasticsearch from allocating shards to specific nodes, typically during maintenance.

**Current template structure:**
```json
{
  "template": {
    "settings": {
      "index": {
        "routing": {
          "allocation": {
            "exclude": {
              "_name": "sjc01-c01-ess05-*,sjc01-c02-ess04-*,sjc01-c02-ess05-*"
            }
          }
        }
      }
    }
  }
}
```

**Workflow Examples:**

1. **Before Maintenance - Add Hosts:**
```bash
# Preview the change first
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "sjc01-c01-ess99-*,sjc01-c02-ess99-*" --dry-run

# Apply the change
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "sjc01-c01-ess99-*,sjc01-c02-ess99-*"
```

2. **After Maintenance - Remove Hosts:**
```bash
# Bring hosts back online
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o remove -v "sjc01-c01-ess99-*,sjc01-c02-ess99-*"
```

3. **Emergency - Clear All Exclusions:**
```bash
# Remove all host exclusions
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o set -v ""
```

### Other List Field Examples

**Node attributes:**
```bash
# Add node attributes
escmd template-modify my_template -t component \
  -f "template.settings.index.routing.allocation.require.box_type" \
  -o append -v "hot,warm"
```

**Index patterns in composable templates:**
```bash
# Add new index patterns
escmd template-modify my_composable_template -t composable \
  -f "index_patterns" \
  -o append -v "new-logs-*,new-metrics-*"
```

## Detailed Behavior

### Duplicate Handling
The `append` operation automatically prevents duplicates:

```bash
# Current value: "host1-*,host2-*"
# Command: append "host2-*,host3-*"
# Result: "host1-*,host2-*,host3-*"  (host2-* not duplicated)
```

### Value Parsing
Values are parsed intelligently:

- **Whitespace trimming:** `"host1-*, host2-*"` → `["host1-*", "host2-*"]`
- **Empty value filtering:** `"host1-*,,host2-*"` → `["host1-*", "host2-*"]`
- **Consistent formatting:** Always outputs clean comma-separated format

### Type Detection
The system automatically detects list-like values:

- **JSON arrays:** `["value1", "value2"]` - treated as lists
- **Comma-separated strings:** `"value1,value2"` - treated as lists
- **Single strings without commas:** `"value"` - treated as single values

## Field Path Reference

### Component Templates
```
template.settings.index.routing.allocation.exclude._name
template.settings.index.routing.allocation.exclude._ip
template.settings.index.routing.allocation.require.box_type
template.settings.index.routing.allocation.include._tier_preference
_meta.excluded_hosts
_meta.maintenance_notes
```

### Composable Templates
```
index_patterns
template.settings.index.routing.allocation.exclude._name
template.settings.index.routing.allocation.require.box_type
_meta.pattern_list
```

### Legacy Templates
```
settings.index.routing.allocation.exclude._name
settings.index.routing.allocation.require.box_type
```

## Safety Features

### Automatic Backup
Every modification creates an automatic backup unless disabled:

```bash
# Backup is created automatically
escmd template-modify manual_template -f field -o append -v "value"

# Skip backup (not recommended)
escmd template-modify manual_template -f field -o append -v "value" --no-backup
```

### Dry Run Mode
Always test changes first with `--dry-run`:

```bash
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "test-host-*" --dry-run
```

**Dry run output shows:**
- Current field value
- Proposed new value
- Operation details
- No actual changes made

### Field Validation
The system validates:
- Template exists and is accessible
- Field path is valid for template type
- Operation is appropriate for field type
- Value format is correct

## Error Handling

### Common Errors and Solutions

**Template not found:**
```
Error: Template 'my_template' not found
Solution: Check template name with `escmd templates`
```

**Invalid field path:**
```
Error: Field 'invalid.path' not found in template
Solution: Check template structure with `escmd template my_template`
```

**Permission denied:**
```
Error: Permission denied accessing template
Solution: Check Elasticsearch user permissions
```

**Non-list field:**
```
Warning: Cannot remove from non-list value
Behavior: Operation is ignored, original value preserved
```

## Best Practices

### 1. Always Test First
```bash
# Test with dry-run
escmd template-modify my_template -f field -o append -v "value" --dry-run

# Apply if satisfied
escmd template-modify my_template -f field -o append -v "value"
```

### 2. Use Specific Values
```bash
# Good - specific host patterns
-v "sjc01-c01-ess05-*,sjc01-c02-ess04-*"

# Avoid - overly broad patterns
-v "*"
```

### 3. Verify Changes
```bash
# Check the template after modification
escmd template my_template --format json | jq '.template.settings.index.routing.allocation.exclude'
```

### 4. Document Changes
Keep track of modifications for troubleshooting:

```bash
# Add descriptive metadata when making changes
escmd template-modify manual_template -t component \
  -f "_meta.last_modification" \
  -o set -v "$(date): Added hosts for maintenance - ticket #12345"
```

### 5. Coordinate with Team
When modifying shared templates:
- Announce maintenance windows
- Use dry-run to show planned changes
- Keep backups accessible
- Document rollback procedures

## Recovery Procedures

### List Recent Backups
```bash
escmd list-backups --name manual_template --format table
```

### Restore from Backup
```bash
escmd template-restore --backup-file ~/.escmd/template_backups/manual_template_component_20231213_143022.json
```

### Verify Restoration
```bash
escmd template manual_template --format json
```

### Manual Rollback
If you know the previous value:

```bash
# Restore to known good state
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o set -v "sjc01-c01-ess05-*,sjc01-c02-ess04-*,sjc01-c02-ess05-*"
```

## Advanced Examples

### Batch Operations
```bash
# Multiple hosts in one command
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "rack1-host-*,rack2-host-*,rack3-host-*"
```

### Complex Field Paths
```bash
# Nested metadata lists
escmd template-modify my_template -t component \
  -f "_meta.monitoring.excluded_patterns" \
  -o append -v "system-*,audit-*"
```

### Cross-Environment Consistency
```bash
# Copy exclusion list from one template to another
EXCLUSIONS=$(escmd template source_template --format json | jq -r '.template.settings.index.routing.allocation.exclude._name')

escmd template-modify target_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o set -v "$EXCLUSIONS"
```

## Integration with Monitoring

### Check Impact
```bash
# See which indices are affected by template
escmd template-usage | grep manual_template

# Monitor allocation after changes
escmd allocation
```

### Automation
```bash
#!/bin/bash
# Maintenance script example

TEMPLATE="manual_template"
HOSTS="maintenance-rack-*"

echo "Adding hosts to exclusion list..."
escmd template-modify "$TEMPLATE" -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "$HOSTS"

echo "Waiting for shard movement..."
sleep 300

echo "Performing maintenance..."
# ... maintenance tasks ...

echo "Removing hosts from exclusion list..."
escmd template-modify "$TEMPLATE" -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o remove -v "$HOSTS"

echo "Maintenance complete!"
```

This guide provides comprehensive coverage of list operations in template modifications. For additional help, use `escmd help templates` or consult the other template documentation files.