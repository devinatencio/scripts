# Template Management Usage Examples

This document provides practical examples of how to use the new template functionality in ESCMD.

## Basic Usage

### List All Templates

```bash
# List all templates (legacy, composable, and component)
./escmd.py templates

# List only legacy templates
./escmd.py templates --type legacy

# List only composable templates  
./escmd.py templates --type composable

# List only component templates
./escmd.py templates --type component

# Get JSON output for automation
./escmd.py templates --format json
```

### View Template Details

```bash
# Auto-detect template type and show details
./escmd.py template my-logs-template

# Specify template type for faster lookup
./escmd.py template my-logs-template --type legacy
./escmd.py template my-metrics-template --type composable
./escmd.py template my-settings --type component

# Get JSON output for automation
./escmd.py template my-logs-template --format json
```

### Analyze Template Usage

```bash
# Show which templates are being used by indices
./escmd.py template-usage

# Get JSON output for scripting
./escmd.py template-usage --format json
```

## Real-World Examples

### Template Audit Script

```bash
#!/bin/bash
# audit_templates.sh - Complete template audit

echo "=== Template Overview ==="
./escmd.py templates

echo -e "\n=== Template Usage Analysis ==="
./escmd.py template-usage

echo -e "\n=== Unused Templates (Candidates for Cleanup) ==="
./escmd.py template-usage --format json | jq -r '.unused_templates[] | .name'

echo -e "\n=== Critical Template Details ==="
for template in $(./escmd.py templates --format json | jq -r '.composable_templates | keys[]' | grep -E "(logs|metrics|critical)"); do
    echo "--- $template ---"
    ./escmd.py template "$template" | head -20
    echo ""
done
```

### Template Backup

```bash
#!/bin/bash
# backup_templates.sh - Backup all templates

BACKUP_DIR="template-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backing up templates to $BACKUP_DIR..."

# Export all templates summary
./escmd.py templates --format json > "$BACKUP_DIR/all-templates-summary.json"

# Export detailed information for each template
echo "Exporting individual template details..."

# Get all template names from all types
ALL_TEMPLATES=$(./escmd.py templates --format json | jq -r '
  .legacy_templates | keys[] // empty,
  .composable_templates | keys[] // empty,
  .component_templates | keys[] // empty
' | grep -v "error")

for template in $ALL_TEMPLATES; do
    if [ ! -z "$template" ] && [ "$template" != "null" ]; then
        echo "  Backing up: $template"
        ./escmd.py template "$template" --format json > "$BACKUP_DIR/template-$template.json"
    fi
done

# Export usage analysis
./escmd.py template-usage --format json > "$BACKUP_DIR/template-usage.json"

echo "Template backup complete in $BACKUP_DIR"
ls -la "$BACKUP_DIR"
```

### Multi-Cluster Template Monitoring

```bash
#!/bin/bash
# monitor_templates.sh - Monitor templates across multiple clusters

CLUSTERS=("production" "staging" "development")

for cluster in "${CLUSTERS[@]}"; do
    echo "=== Templates in $cluster ==="
    
    # Get template count
    TOTAL=$(./escmd.py -l "$cluster" templates --format json 2>/dev/null | jq -r '.summary.total_count // 0')
    UNUSED=$(./escmd.py -l "$cluster" template-usage --format json 2>/dev/null | jq -r '.unused_templates | length // 0')
    
    echo "  Total templates: $TOTAL"
    echo "  Unused templates: $UNUSED"
    
    if [ "$UNUSED" -gt 0 ]; then
        echo "  ⚠️  Unused templates found in $cluster:"
        ./escmd.py -l "$cluster" template-usage --format json 2>/dev/null | jq -r '.unused_templates[] | "    - " + .name'
    fi
    
    echo ""
done
```

### Template Health Check

```bash
#!/bin/bash
# template_health.sh - Check template health and configuration

echo "🔍 Template Health Check"
echo "======================="

# Check for templates with high priorities that might conflict
echo "High Priority Templates (>500):"
./escmd.py templates --format json | jq -r '
  .composable_templates | 
  to_entries[] | 
  select(.value.index_template.priority > 500) | 
  "  " + .key + " (priority: " + (.value.index_template.priority | tostring) + ")"
'

# Check for overlapping index patterns
echo -e "\nChecking for potential pattern conflicts..."
./escmd.py template-usage --format json | jq -r '
  .templates_in_use | 
  to_entries[] | 
  "Template: " + .key + " | Patterns: " + (.value.patterns | join(", "))
'

# Show templates without any matching indices
echo -e "\nTemplates with no matching indices:"
./escmd.py template-usage --format json | jq -r '
  .unused_templates[] | 
  "  " + .name + " (" + .type + ") - Patterns: " + (.patterns | join(", "))
'
```

## Integration with Other ESCMD Commands

### Template and Index Analysis

```bash
# First, see what templates exist
./escmd.py templates

# Check which indices match a template pattern
./escmd.py indices "logs-*"

# Analyze template usage to see the relationship
./escmd.py template-usage

# Get details about a specific template
./escmd.py template logs-template
```

### Template Changes Impact Analysis

```bash
#!/bin/bash
# Before making template changes, analyze impact
TEMPLATE_NAME="$1"

if [ -z "$TEMPLATE_NAME" ]; then
    echo "Usage: $0 <template-name>"
    exit 1
fi

echo "Impact Analysis for Template: $TEMPLATE_NAME"
echo "============================================="

# Show current template configuration
echo "Current Template Configuration:"
./escmd.py template "$TEMPLATE_NAME"

echo -e "\nCurrently Matching Indices:"
./escmd.py template-usage --format json | jq -r "
  .templates_in_use[\"$TEMPLATE_NAME\"].matching_indices[]? // \"No matching indices found\"
"

echo -e "\nIndex Count Impact:"
MATCH_COUNT=$(./escmd.py template-usage --format json | jq -r ".templates_in_use[\"$TEMPLATE_NAME\"].match_count // 0")
echo "  $MATCH_COUNT indices would be affected by changes to this template"
```

## Automation Examples

### JSON Processing with jq

```bash
# Get count of each template type
./escmd.py templates --format json | jq '.summary'

# List all legacy templates
./escmd.py templates --format json | jq -r '.legacy_templates | keys[]'

# Find templates with specific settings
./escmd.py template my-template --format json | jq '.metadata.settings'

# Get unused templates for cleanup automation
UNUSED_TEMPLATES=$(./escmd.py template-usage --format json | jq -r '.unused_templates[] | .name')
echo "Unused templates: $UNUSED_TEMPLATES"
```

### Monitoring Integration

```bash
#!/bin/bash
# For monitoring systems like Nagios, Zabbix, etc.

# Check if template count exceeds threshold
MAX_UNUSED=5
UNUSED_COUNT=$(./escmd.py template-usage --format json | jq '.unused_templates | length')

if [ "$UNUSED_COUNT" -gt "$MAX_UNUSED" ]; then
    echo "CRITICAL: $UNUSED_COUNT unused templates found (threshold: $MAX_UNUSED)"
    exit 2
elif [ "$UNUSED_COUNT" -gt 2 ]; then
    echo "WARNING: $UNUSED_COUNT unused templates found"
    exit 1
else
    echo "OK: Template usage looks good ($UNUSED_COUNT unused templates)"
    exit 0
fi
```

## Tips and Best Practices

### 1. Regular Template Audits
Run template audits weekly to identify unused templates:
```bash
./escmd.py template-usage | grep "Unused templates"
```

### 2. Template Documentation
Use the `--format json` option to extract template metadata for documentation:
```bash
./escmd.py template my-template --format json | jq '.metadata._meta'
```

### 3. Performance Optimization
Use `--type` flag when you know the template type to speed up lookups:
```bash
./escmd.py template my-composable-template --type composable
```

### 4. Cluster Comparison
Compare template configurations across environments:
```bash
./escmd.py -l production template my-template --format json > prod-template.json
./escmd.py -l staging template my-template --format json > staging-template.json
diff prod-template.json staging-template.json
```

### 5. Backup Before Changes
Always backup templates before making changes:
```bash
./escmd.py template my-template --format json > my-template-backup.json
```

## Error Handling

### Common Issues and Solutions

**Template Not Found:**
```bash
# Check if template exists with different type
./escmd.py templates | grep my-template

# Use auto-detection
./escmd.py template my-template --type auto
```

**Connection Issues:**
```bash
# Test connection first
./escmd.py ping

# Specify cluster explicitly
./escmd.py -l my-cluster templates
```

**Permission Issues:**
```bash
# Check cluster health first
./escmd.py health

# Verify authentication
./escmd.py -l my-cluster ping
```

This completes the template functionality implementation for ESCMD! 🎉