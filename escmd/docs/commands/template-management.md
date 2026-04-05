# Template Management

**Elasticsearch Template Management Commands** - Comprehensive tools for managing index templates, composable templates, and component templates with rich theming and display.

## Overview

ESCMD provides comprehensive template management functionality supporting all three types of Elasticsearch templates with beautiful, themed display using the integrated renderer architecture:

- **🏛️ Legacy Index Templates** - Traditional templates using the `_template` API
- **🔧 Composable Index Templates** - Modern templates using the `_index_template` API (ES 7.8+)
- **🧩 Component Templates** - Reusable template components using the `_component_template` API

### Architecture Features

- **🎨 Theme Integration** - All displays use your configured ESCMD theme colors and styles
- **📊 Rich Tables** - Professionally formatted tables with color-coded status indicators
- **🎯 Smart Panels** - Organized information panels with contextual styling
- **⚡ Renderer System** - Uses dedicated `TemplateRenderer` for consistent display formatting

## Commands

### Template Modification

Modify template fields with sophisticated operations including list manipulation:

```bash
# Set a field value (replace entirely)
./escmd.py template-modify my-template -f "template.settings.index.number_of_replicas" -o set -v "2"

# Append values to a comma-separated list (avoids duplicates)
./escmd.py template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "host1-*,host2-*"

# Remove values from a comma-separated list
./escmd.py template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o remove -v "old-host-*,maintenance-host-*"

# Delete a field entirely
./escmd.py template-modify my-template -f "_meta.temporary_setting" -o delete

# Preview changes without applying (dry run)
./escmd.py template-modify my-template -f "field.path" -o append -v "value" --dry-run
```

**Available Operations:**
- **`set`** - Replace field value completely (default)
- **`append`** - Add values to comma-separated lists, preventing duplicates
- **`remove`** - Remove specific values from comma-separated lists
- **`delete`** - Remove field entirely from template

**Safety Features:**
- 🛡️ **Automatic backups** before modifications (disable with `--no-backup`)
- 🔍 **Dry run mode** with `--dry-run` to preview changes
- ✅ **Field validation** before applying changes
- 🏗️ **Template structure validation** after modifications
- 💾 **Backup/restore functionality** for recovery

**Common Use Cases:**
- **Host Exclusion Management** - Add/remove hosts from allocation exclusion lists during maintenance
- **Index Settings** - Modify replica counts, refresh intervals, routing settings
- **Template Metadata** - Update descriptions, versions, maintenance notes
- **List Management** - Any comma-separated field values

### Template Backup and Restore

Create manual backups and restore templates:

```bash
# Create backup
./escmd.py template-backup my-template -t component

# Restore from backup
./escmd.py template-restore --backup-file /path/to/backup.json

# List available backups
./escmd.py list-backups --name my-template
```

### List All Templates

Display comprehensive information about all templates in your cluster:

```bash
# List all template types
./escmd.py templates

# List only legacy templates
./escmd.py templates --type legacy

# List only composable templates
./escmd.py templates --type composable

# List only component templates
./escmd.py templates --type component

# JSON output for automation
./escmd.py templates --format json
```

**Features:**
- 📊 Summary statistics showing template counts by type
- 🔍 Detailed table view with key information for each template type
- 📋 Index patterns, priorities, and component relationships
- ✅ Configuration status (settings, mappings, aliases)

### Template Detail View

Get detailed information about a specific template:

```bash
# Auto-detect template type
./escmd.py template my-template

# Specify template type for faster lookup
./escmd.py template my-template --type composable
./escmd.py template my-template --type legacy
./escmd.py template my-template --type component

# JSON output for automation
./escmd.py template my-template --format json
```

**Features:**
- 🔍 Complete template configuration display
- 📑 Formatted JSON for settings, mappings, and aliases
- 🏷️ Template metadata (version, priority, patterns)
- 🔗 Component template relationships
- 💡 Template type auto-detection

### Template Usage Analysis

Analyze how templates are being used across your indices:

```bash
# Analyze template usage
./escmd.py template-usage

# JSON output for automation
./escmd.py template-usage --format json
```

**Features:**
- ✅ Templates currently in use with matching index counts
- ⚠️  Unused templates that might be candidates for cleanup
- 📊 Usage statistics and summary information
- 🔍 Index pattern matching analysis

## Template Types

### Legacy Index Templates

Traditional Elasticsearch templates that have been available since early versions:

```bash
# Example legacy template display
Name: logs-template
Index Patterns: logs-*, audit-*
Order: 10
Settings: ✓ (5)
Mappings: ✓ (12) 
Aliases: ✓ (2)
```

**Key Features:**
- Uses `order` field for precedence (higher wins)
- Single template definition
- Compatible with all Elasticsearch versions

### Composable Index Templates

Modern template system introduced in Elasticsearch 7.8+:

```bash
# Example composable template display
Name: logs-composable
Index Patterns: logs-2023-*, logs-2024-*
Priority: 200
Component Templates: logs-settings, logs-mappings
Data Stream: ✓
```

**Key Features:**
- Uses `priority` field for precedence (higher wins)
- Can compose multiple component templates
- Supports data streams
- More flexible and powerful than legacy templates

### Component Templates

Reusable template building blocks for composable templates:

```bash
# Example component template display
Name: logs-settings
Settings: ✓ (3)
Mappings: ✗
Aliases: ✗
Version: 1
```

**Key Features:**
- Reusable across multiple composable templates
- Contain only settings, mappings, or aliases
- Enable template modularization and reuse

## Output Formats

### Table Format (Default)

Rich, formatted tables with:
- Color-coded information
- Visual indicators (✓/✗) for configuration presence
- Organized by template type
- Summary panels with statistics

### JSON Format

Machine-readable output perfect for:
- Automation and scripting
- Integration with monitoring tools
- Detailed programmatic analysis
- Data export and backup

## Common Use Cases

### Daily Template Monitoring

```bash
# Quick template overview
./escmd.py templates

# Check for unused templates
./escmd.py template-usage

# Inspect specific template details
./escmd.py template critical-logs-template
```

### Template Troubleshooting

```bash
# Check if template exists and its type
./escmd.py template my-template

# Analyze template usage patterns
./escmd.py template-usage --format json | jq '.unused_templates'

# Verify template configuration
./escmd.py template my-template --format json | jq '.metadata.settings'
```

### Automation and Monitoring

```bash
# Export all templates for backup
./escmd.py templates --format json > templates-backup.json

# Monitor unused templates
./escmd.py template-usage --format json | jq '.unused_templates | length'

# Check template health across clusters
./escmd.py -l production templates --type composable --format json
```

## Best Practices

### Template Management

1. **Use Composable Templates** - For new implementations, prefer composable templates over legacy ones
2. **Leverage Component Templates** - Break down common configurations into reusable components
3. **Set Appropriate Priorities** - Use priority/order fields to ensure correct template precedence
4. **Regular Cleanup** - Use template usage analysis to identify and remove unused templates

### Monitoring

1. **Regular Usage Analysis** - Periodically check template usage to identify cleanup opportunities
2. **Template Versioning** - Use version fields to track template changes over time
3. **Pattern Validation** - Ensure index patterns don't overlap unexpectedly
4. **Documentation** - Use `_meta` fields to document template purposes

## Integration with Other Commands

Template management integrates seamlessly with other ESCMD features:

### With Index Operations
```bash
# Check which templates apply to specific indices
./escmd.py indices "logs-*" --format json
./escmd.py template-usage
```

### With Health Monitoring
```bash
# Template health as part of cluster check
./escmd.py cluster-check
./escmd.py templates --type all
```

### With Automation
```bash
# Template management in scripts
UNUSED_COUNT=$(./escmd.py template-usage --format json | jq '.unused_templates | length')
if [ "$UNUSED_COUNT" -gt 5 ]; then
    echo "Warning: $UNUSED_COUNT unused templates found"
fi
```

## Troubleshooting

### Template Not Found
- Use `./escmd.py templates` to list all available templates
- Check template name spelling and case sensitivity
- Verify cluster connectivity and permissions

### Performance Issues
- Use `--type` flag to limit scope when dealing with many templates
- Consider using `--format json` for automated processing
- Use paging options for large template lists

### Template Conflicts
- Use template usage analysis to identify overlapping patterns
- Check priority/order values for proper precedence
- Review composable template component relationships

## Template Modification Examples

### Host Exclusion Management

**Scenario**: Adding hosts to exclusion list for maintenance, then removing them afterwards.

```bash
# 1. Preview the change first (always recommended)
./escmd.py template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "sjc01-c01-ess99-*,sjc01-c02-ess99-*" --dry-run

# 2. Apply the change (backup created automatically)
./escmd.py template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "sjc01-c01-ess99-*,sjc01-c02-ess99-*"

# 3. After maintenance - bring hosts back online
./escmd.py template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o remove -v "sjc01-c01-ess99-*,sjc01-c02-ess99-*"
```

### Index Settings Management

```bash
# Set replica count
./escmd.py template-modify logs-template -t composable \
  -f "template.settings.index.number_of_replicas" \
  -o set -v "2"

# Set refresh interval
./escmd.py template-modify logs-template -t composable \
  -f "template.settings.index.refresh_interval" \
  -o set -v "30s"

# Update routing allocation requirements
./escmd.py template-modify logs-template -t composable \
  -f "template.settings.index.routing.allocation.require.box_type" \
  -o set -v "hot"
```

### Template Metadata Management

```bash
# Update template description
./escmd.py template-modify my-template -t component \
  -f "_meta.description" \
  -o set -v "Updated production template for 2024"

# Add version tracking
./escmd.py template-modify my-template -t component \
  -f "_meta.version" \
  -o set -v "2.1.0"

# Track maintenance notes
./escmd.py template-modify manual_template -t component \
  -f "_meta.last_maintenance" \
  -o set -v "$(date): Excluded hosts for rack maintenance - ticket #12345"
```

### Emergency Recovery

```bash
# Clear all host exclusions in emergency
./escmd.py template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o set -v ""

# Restore from recent backup if needed
./escmd.py list-backups --name manual_template
./escmd.py template-restore --backup-file ~/.escmd/template_backups/manual_template_component_20231213_143022.json
```

## Examples

### Complete Template Audit

```bash
#!/bin/bash
# Complete template audit script

echo "=== Template Overview ==="
./escmd.py templates

echo -e "\n=== Template Usage Analysis ==="
./escmd.py template-usage

echo -e "\n=== Unused Templates ==="
./escmd.py template-usage --format json | jq -r '.unused_templates[] | .name'

echo -e "\n=== Template Details for Critical Templates ==="
for template in $(./escmd.py templates --format json | jq -r '.composable_templates | keys[]' | grep -E "(logs|metrics|critical)"); do
    echo "--- $template ---"
    ./escmd.py template "$template"
done
```

### Template Backup

```bash
#!/bin/bash
# Backup all templates

BACKUP_DIR="template-backup-$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Export all templates
./escmd.py templates --format json > "$BACKUP_DIR/all-templates.json"

# Export individual template details
for template in $(./escmd.py templates --format json | jq -r '.legacy_templates | keys[], .composable_templates | keys[], .component_templates | keys[]'); do
    ./escmd.py template "$template" --format json > "$BACKUP_DIR/$template.json"
done

echo "Templates backed up to $BACKUP_DIR"
```

## Related Documentation

- **[Template Modification Guide](../guides/TEMPLATE_MODIFICATION_GUIDE.md)** - Complete guide to template modifications
- **[Template List Operations](../guides/TEMPLATE_LIST_OPERATIONS.md)** - Detailed guide for append/remove operations
- **[Template Quick Reference](../guides/TEMPLATE_MODIFY_QUICK_REFERENCE.md)** - Quick reference for template operations
- **[Index Management](index-operations.md)** - Managing indices that use templates
- **[Health Monitoring](health-monitoring.md)** - Including template health in cluster checks
- **[ILM Management](ilm-management.md)** - Templates with Index Lifecycle Management
- **[Cluster Settings](cluster-settings.md)** - Template-related cluster configurations

---

**Template Management** - Making Elasticsearch template operations simple, comprehensive, and powerful! 🎯