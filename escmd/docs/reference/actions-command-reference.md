# Actions Command Reference

This is a quick reference guide for the correct command syntax to use in your `actions.yml` file. Use this to ensure your action steps have the proper command format.

## Table of Contents

- [Allocation Commands](#allocation-commands)
- [Index Management](#index-management)
- [Template Commands](#template-commands)
- [Health & Monitoring](#health--monitoring)
- [Snapshot Commands](#snapshot-commands)
- [Node Management](#node-management)
- [Cluster Settings](#cluster-settings)
- [Common Patterns](#common-patterns)

## Allocation Commands

### Exclude Nodes
```yaml
# Add node to exclusion list
action: allocation exclude add "{{ hostname }}"
action: allocation exclude add "{{ host }}-*"

# Remove node from exclusion list  
action: allocation exclude remove "{{ hostname }}"
action: allocation exclude remove "{{ host }}-*"

# Reset all exclusions
action: allocation exclude reset

# Reset with force (skips confirmation)
action: allocation exclude reset --yes-i-really-mean-it
```

### Enable/Disable Allocation
```yaml
# Enable shard allocation
action: allocation enable

# Disable shard allocation
action: allocation disable
```

### Allocation Explanations
```yaml
# Explain allocation for an index
action: allocation explain "{{ index_name }}"
```

## Index Management

### List and View Indices
```yaml
# List all indices
action: indices

# List with specific format
action: indices --format json
action: indices --format table

# Filter by pattern
action: indices "{{ pattern }}"

# Filter by status
action: indices --status red
action: indices --status yellow
action: indices --status green

# Show specific index details
action: indice "{{ index_name }}"
```

### Index Operations
```yaml
# Delete indices (DESTRUCTIVE!)
action: indices --delete "{{ pattern }}"

# Create new index
action: create-index "{{ index_name }}"
action: create-index "{{ index_name }}" --shards 3 --replicas 1

# Flush indices
action: flush "{{ pattern }}"

# Freeze index
action: freeze "{{ index_name }}"

# Unfreeze index
action: unfreeze "{{ index_name }}"
```

### Recovery
```yaml
# Show recovery status
action: recovery
action: recovery --format json
```

## Template Commands

### List Templates
```yaml
# Show all templates
action: templates

# Show specific template
action: template "{{ template_name }}"

# Show template usage
action: template-usage "{{ template_name }}"
```

### Modify Templates
```yaml
# Append value to template field
action: template-modify {{ template_name }} -t component -f "{{ field_path }}" -o append -v "{{ value }}"

# Set template field value
action: template-modify {{ template_name }} -t component -f "{{ field_path }}" -o set -v "{{ value }}"

# Remove field from template
action: template-modify {{ template_name }} -t component -f "{{ field_path }}" -o remove

# Common field paths:
# - template.settings.index.routing.allocation.exclude._name
# - template.settings.index.number_of_shards
# - template.settings.index.number_of_replicas
```

### Template Backup/Restore
```yaml
# Backup template
action: template-backup "{{ template_name }}"

# Restore template
action: template-restore "{{ template_name }}" "{{ backup_name }}"

# List backups
action: list-backups
```

## Health & Monitoring

### Cluster Health
```yaml
# Basic health check
action: health
action: health --format json

# Detailed health dashboard
action: health-detail
action: health-detail --style dashboard
action: health-detail --style classic

# Compare clusters
action: health-detail --compare "{{ other_cluster }}"
```

### Node Information
```yaml
# List all nodes
action: nodes
action: nodes --format json

# Show master nodes
action: masters

# Show current master
action: current-master
```

### Storage and Shards
```yaml
# Show storage usage
action: storage
action: storage --format json

# Show shard information
action: shards
action: shards --format json
action: shards --server "{{ hostname }}"
action: shards --size --limit 10

# Show shard colocation issues
action: shard-colocation
action: shard-colocation "{{ pattern }}"
```

## Snapshot Commands

### Basic Snapshots
```yaml
# List snapshots
action: snapshots

# Create snapshot
action: snapshots create "{{ snapshot_name }}"

# Delete snapshot (use with caution)
action: snapshots delete "{{ snapshot_name }}"
```

## Node Management

### Ping and Connectivity
```yaml
# Test connection
action: ping
action: ping --format json
```

## Cluster Settings

### View Settings
```yaml
# Show cluster settings
action: cluster-settings
action: cluster-settings --format json
```

### Modify Settings
```yaml
# Set persistent setting
action: set persistent "{{ setting_key }}" "{{ setting_value }}"

# Set transient setting
action: set transient "{{ setting_key }}" "{{ setting_value }}"

# Reset setting (use "null" as value)
action: set persistent "{{ setting_key }}" "null"

# With dry-run
action: set persistent "{{ setting_key }}" "{{ setting_value }}" --dry-run

# Skip confirmation
action: set persistent "{{ setting_key }}" "{{ setting_value }}" --yes

# Common settings:
# - cluster.routing.allocation.node_concurrent_recoveries
# - cluster.routing.allocation.cluster_concurrent_rebalance
# - indices.recovery.max_bytes_per_sec
```

## Rollover and ILM

### Rollover Operations
```yaml
# Rollover datastream
action: rollover "{{ datastream_name }}"

# Auto-rollover biggest shard on host
action: auto-rollover "{{ host_pattern }}"
```

### ILM Management
```yaml
# Show ILM policies
action: ilm

# Apply ILM policy
action: ilm apply "{{ policy_name }}" "{{ index_pattern }}"
```

## Common Patterns

### Host Maintenance Pattern
```yaml
steps:
  - name: Exclude Host
    action: allocation exclude add "{{ host }}-*"
  - name: Wait for Relocation
    action: shards --server "{{ host }}"
  - name: Verify Health
    action: health
```

### Index Cleanup Pattern
```yaml
steps:
  - name: List Target Indices
    action: indices "{{ pattern }}"
  - name: Delete Old Indices
    action: indices --delete "{{ pattern }}"
    confirm: true
```

### Template Update Pattern
```yaml
steps:
  - name: Backup Template
    action: template-backup "{{ template_name }}"
  - name: Update Template
    action: template-modify {{ template_name }} -t component -f "{{ field }}" -o set -v "{{ value }}"
  - name: Verify Template
    action: template "{{ template_name }}"
```

### Maintenance Mode Pattern
```yaml
steps:
  - name: Disable Allocation
    action: allocation disable
  - name: Exclude Data Nodes
    action: allocation exclude add "data-*"
    condition: "{{ mode == 'enable' }}"
  - name: Reset Exclusions
    action: allocation exclude reset
    condition: "{{ mode == 'disable' }}"
  - name: Enable Allocation
    action: allocation enable
    condition: "{{ mode == 'disable' }}"
```

## Parameter Substitution

Use Jinja2 template syntax for parameters:

```yaml
# Basic substitution
action: indices "{{ pattern }}"

# String concatenation
action: allocation exclude add "{{ host }}-*"

# Conditional values
action: set {{ type }} "cluster.routing.allocation.enable" "{{ state }}"

# Date/time formatting (if supported)
action: snapshots create "backup-{{ date | strftime('%Y%m%d') }}"
```

## Error Prevention Tips

1. **Always use quotes** around parameters that might contain spaces or special characters
2. **Use dry-run mode** to test actions before execution
3. **Add confirmation prompts** for destructive operations using `confirm: true`
4. **Validate templates exist** before using template-modify commands
5. **Check node names** before using exclude commands
6. **Use meaningful step names** for better error reporting

## Common Mistakes

❌ **Wrong:**
```yaml
action: allocation exclude host "{{ host }}"  # Wrong subcommand
action: template-modify manuel_template       # Wrong template name
action: allocation exclude-reset             # Wrong syntax
```

✅ **Correct:**
```yaml
action: allocation exclude add "{{ host }}"   # Correct subcommand
action: template-modify manual_template       # Correct template name
action: allocation exclude reset              # Correct syntax
```

## Testing Your Actions

Always test new actions with dry-run mode:

```bash
# Test before executing
escmd action run my-action --param-name value --dry-run

# Execute after verification
escmd action run my-action --param-name value
```

This reference should help you avoid syntax errors when creating your action definitions!