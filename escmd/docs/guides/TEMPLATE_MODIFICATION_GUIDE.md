# Template Modification Guide

This guide explains how to use the new template modification functionality in escmd to safely modify Elasticsearch templates.

## Overview

The template modification feature allows you to:
- Modify any field in Elasticsearch templates using dot notation
- Append or remove values from comma-separated lists (like host exclusion lists)
- Create automatic backups before modifications
- Perform dry-run operations to preview changes
- Restore templates from backups

## Supported Template Types

- **Component templates** (`_component_template` API)
- **Composable index templates** (`_index_template` API) 
- **Legacy index templates** (`_template` API)

## Commands

### 1. template-modify

Modify a field in a template using various operations.

**Syntax:**
```bash
escmd template-modify <template_name> [options]
```

**Required Arguments:**
- `template_name`: Name of the template to modify
- `--field, -f`: Field path in dot notation

**Options:**
- `--type, -t`: Template type (`auto`, `legacy`, `composable`, `component`) - default: `auto`
- `--operation, -o`: Operation to perform (`set`, `append`, `remove`, `delete`) - default: `set`
- `--value, -v`: Value for the operation
- `--backup`: Create backup before modification (default: true)
- `--no-backup`: Skip backup creation
- `--backup-dir`: Custom backup directory
- `--dry-run`: Preview changes without applying them

**Examples:**

```bash
# Append hosts to an exclusion list
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "sjc01-c01-ess99-*,sjc01-c02-ess99-*"

# Remove a specific host from exclusion list
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o remove -v "sjc01-c01-ess05-*"

# Set the entire exclusion list to new values
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o set -v "host1-*,host2-*,host3-*"

# Set a simple value
escmd template-modify my_template -t component \
  -f "template.settings.index.number_of_replicas" \
  -o set -v "2"

# Delete a field
escmd template-modify my_template -t component \
  -f "_meta.temporary_setting" \
  -o delete

# Preview changes without applying (dry run)
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "test-host-*" \
  --dry-run
```

### 2. template-backup

Create a manual backup of a template.

**Syntax:**
```bash
escmd template-backup <template_name> [options]
```

**Options:**
- `--type, -t`: Template type (default: `auto`)
- `--backup-dir`: Custom backup directory
- `--cluster`: Cluster name for backup metadata

**Example:**
```bash
escmd template-backup manual_template -t component --cluster prod-cluster
```

### 3. template-restore

Restore a template from a backup file.

**Syntax:**
```bash
escmd template-restore --backup-file <path_to_backup>
```

**Example:**
```bash
escmd template-restore --backup-file ~/.escmd/template_backups/manual_template_component_20231213_143022.json
```

### 4. list-backups

List available template backups.

**Syntax:**
```bash
escmd list-backups [options]
```

**Options:**
- `--name`: Filter by template name
- `--type`: Filter by template type
- `--backup-dir`: Custom backup directory
- `--format`: Output format (`table` or `json`)

**Examples:**
```bash
# List all backups
escmd list-backups

# List backups for a specific template
escmd list-backups --name manual_template

# List only component template backups
escmd list-backups --type component
```

## Operations

### set
Replace the field with the specified value. Creates the field if it doesn't exist.

### append
Add values to a comma-separated list. Avoids duplicates.
- Works with existing comma-separated strings
- If field doesn't exist, creates it with the specified value
- If field is not list-like, treats as `set` operation

### remove
Remove values from a comma-separated list.
- Only works with comma-separated strings
- Removes all occurrences of specified values
- If field is not list-like, leaves it unchanged

### delete
Remove the field entirely from the template.

## Field Path Syntax

Use dot notation to specify nested fields:

```
template.settings.index.routing.allocation.exclude._name
_meta.description
template.mappings.properties.timestamp.type
```

## Common Use Cases

### Managing Host Exclusions

Your primary use case - managing the allocation exclusion list:

```bash
# Current exclusion list
"template.settings.index.routing.allocation.exclude._name": "sjc01-c01-ess05-*,sjc01-c02-ess04-*,sjc01-c02-ess05-*"

# Add new hosts to exclude
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "sjc01-c01-ess99-*,sjc01-c02-ess99-*"

# Remove hosts from exclusion (making them available again)
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o remove -v "sjc01-c01-ess05-*,sjc01-c02-ess04-*"
```

### Updating Template Metadata

```bash
# Update template description
escmd template-modify my_template -t component \
  -f "_meta.description" \
  -o set -v "Updated template for production use"

# Add version information
escmd template-modify my_template -t component \
  -f "_meta.version" \
  -o set -v "2.1.0"
```

### Index Settings

```bash
# Update replica count
escmd template-modify my_template -t component \
  -f "template.settings.index.number_of_replicas" \
  -o set -v "2"

# Set refresh interval
escmd template-modify my_template -t component \
  -f "template.settings.index.refresh_interval" \
  -o set -v "30s"
```

## Safety Features

### Automatic Backups

- Backups are created automatically before any modification (unless `--no-backup` is used)
- Backup files include metadata (timestamp, cluster, template type)
- Backups are stored in `~/.escmd/template_backups/` by default
- Custom backup directory can be specified with `--backup-dir`

### Dry Run Mode

Use `--dry-run` to preview changes without applying them:

```bash
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "test-host-*" \
  --dry-run
```

This shows:
- Current field value
- Proposed new value
- Operation details
- Whether field exists

### Validation

The system validates:
- Template existence before modification
- Field path syntax
- Template structure after modification
- Successful update to Elasticsearch

## Backup Management

### Backup File Format

Backup files are JSON with metadata:

```json
{
  "metadata": {
    "template_name": "manual_template",
    "template_type": "component",
    "cluster_name": "prod-cluster",
    "backup_timestamp": "2023-12-13T14:30:22.123456",
    "escmd_version": "3.0.3",
    "backup_format_version": "1.0"
  },
  "template_data": {
    // Original template data
  }
}
```

### Backup Locations

Default: `~/.escmd/template_backups/`

Filename format: `{template_name}_{type}_{cluster}_{timestamp}.json`

Example: `manual_template_component_prod-cluster_20231213_143022.json`

## Error Handling

### Common Errors and Solutions

**Template not found:**
```
Error: Template 'my_template' not found
```
- Verify template name and type
- Use `escmd templates` to list available templates

**Invalid field path:**
```
Error: Field path validation failed: Path component 'settings' does not exist
```
- Check template structure with `escmd template <name>`
- Verify field path syntax

**Operation failed:**
```
Error: Template modification failed: [403] Forbidden
```
- Check Elasticsearch permissions
- Verify cluster connectivity

### Recovery

If a modification fails:

1. Check the error message for specific issues
2. Use `list-backups` to find recent backups
3. Restore from backup if needed:
   ```bash
   escmd template-restore --backup-file /path/to/backup.json
   ```

## Best Practices

1. **Always test with dry-run first:**
   ```bash
   escmd template-modify my_template ... --dry-run
   ```

2. **Use descriptive values for host patterns:**
   ```bash
   # Good: specific and clear
   -v "sjc01-c01-ess05-*,sjc01-c02-ess04-*"
   
   # Avoid: too broad
   -v "*"
   ```

3. **Keep backups organized:**
   - Use custom backup directories for different environments
   - Clean up old backups periodically
   - Document important changes

4. **Monitor template usage:**
   ```bash
   escmd template-usage
   ```
   This shows which templates are actively used by indices.

5. **Verify changes:**
   ```bash
   escmd template my_template --format json
   ```
   Check the template after modification to ensure changes were applied correctly.

## Troubleshooting

### Permission Issues

Ensure your Elasticsearch user has the necessary permissions:
- `cluster:admin/template/get`
- `cluster:admin/template/put` 
- `cluster:admin/template/delete` (for component templates)

### Backup Directory Issues

If you encounter backup directory errors:
```bash
# Create backup directory manually
mkdir -p ~/.escmd/template_backups

# Or use a custom directory
escmd template-modify my_template --backup-dir /custom/path ...
```

### Field Path Issues

For complex nested structures, use `escmd template <name> --format json` to see the exact field structure and construct the correct dot-notation path.

## Integration with Existing Workflows

The template modification commands integrate seamlessly with existing escmd functionality:

```bash
# 1. Check current templates
escmd templates --type component

# 2. Inspect specific template
escmd template manual_template -t component

# 3. Modify with backup
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "new-host-*"

# 4. Verify changes
escmd template manual_template -t component --format json

# 5. Check template usage
escmd template-usage
```

This provides a complete workflow for safe template management in production environments.