# Cluster Settings Management

View and manage Elasticsearch cluster-level settings with comprehensive display options and JSON output support.

## Quick Reference

```bash
# View cluster settings
./escmd.py cluster-settings                    # Display current cluster settings (default)
./escmd.py cluster-settings display            # Explicit display command
./escmd.py cluster-settings show               # Alternative display command
./escmd.py cluster-settings --format json     # JSON output for automation
```

## Overview

The cluster-settings command provides access to Elasticsearch cluster-level settings, including both persistent and transient settings. This command is essential for understanding cluster configuration, monitoring setting changes, and troubleshooting cluster behavior.

## Core Commands

### 📊 Display Cluster Settings

View current cluster settings in a formatted table:

```bash
./escmd.py cluster-settings                    # Default table format
./escmd.py cluster-settings display            # Explicit display command
./escmd.py cluster-settings show               # Alternative display command
```

**Information Displayed:**
- **Persistent Settings**: Settings that survive cluster restarts
- **Transient Settings**: Temporary settings that reset on restart
- **Default Values**: System defaults for unconfigured settings
- **Setting Categories**: Organized by functional area (allocation, routing, etc.)

### 🔧 JSON Output

Get cluster settings in JSON format for automation and scripting:

```bash
./escmd.py cluster-settings --format json     # Complete JSON output
./escmd.py cluster-settings display --format json  # Explicit JSON display
```

**JSON Structure:**
```json
{
  "persistent": {
    "cluster": {
      "routing": {
        "allocation": {
          "enable": "all"
        }
      }
    }
  },
  "transient": {
    "cluster": {
      "routing": {
        "allocation": {
          "exclude": {
            "_name": "node-01"
          }
        }
      }
    }
  }
}
```

## Common Settings Categories

### Allocation Settings
Control how shards are allocated across the cluster:
- `cluster.routing.allocation.enable`
- `cluster.routing.allocation.exclude.*`
- `cluster.routing.allocation.include.*`
- `cluster.routing.allocation.require.*`

### Recovery Settings
Manage shard recovery behavior:
- `cluster.routing.allocation.node_concurrent_recoveries`
- `cluster.routing.allocation.cluster_concurrent_rebalance`
- `indices.recovery.max_bytes_per_sec`

### Discovery Settings
Configure cluster discovery and membership:
- `discovery.zen.ping.timeout`
- `discovery.zen.fd.ping_timeout`
- `cluster.publish.timeout`

### Indexing Settings
Control indexing behavior cluster-wide:
- `indices.memory.index_buffer_size`
- `indices.store.throttle.max_bytes_per_sec`

## Usage Examples

### Basic Monitoring

```bash
# Quick cluster settings overview
./escmd.py cluster-settings

# Focus on allocation settings
./escmd.py cluster-settings | grep -i allocation

# Check for any transient settings
./escmd.py cluster-settings --format json | jq '.transient'
```

### Troubleshooting Workflows

```bash
# Check allocation settings during shard issues
./escmd.py cluster-settings | grep allocation

# Verify recovery settings during slow recoveries
./escmd.py cluster-settings | grep recovery

# Export settings for analysis
./escmd.py cluster-settings --format json > cluster-settings-$(date +%Y%m%d).json
```

### Automation Integration

```bash
# Check if allocation is disabled
ALLOCATION_STATUS=$(./escmd.py cluster-settings --format json | jq -r '.transient.cluster.routing.allocation.enable // "all"')
if [ "$ALLOCATION_STATUS" != "all" ]; then
  echo "WARNING: Allocation is disabled or restricted: $ALLOCATION_STATUS"
fi

# Monitor excluded nodes
EXCLUDED_NODES=$(./escmd.py cluster-settings --format json | jq -r '.transient.cluster.routing.allocation.exclude._name // "none"')
if [ "$EXCLUDED_NODES" != "none" ]; then
  echo "INFO: Nodes excluded from allocation: $EXCLUDED_NODES"
fi
```

## Command Options

### Basic Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `action` | choice | Action to perform (display, show) | `display` |
| `--format` | choice | Output format (table, json) | `table` |

### Action Types

| Action | Description | Usage |
|--------|-------------|-------|
| `display` | Show cluster settings in table format | `./escmd.py cluster-settings display` |
| `show` | Alternative to display command | `./escmd.py cluster-settings show` |

### Output Formats

| Format | Description | Best For |
|--------|-------------|----------|
| `table` | Human-readable formatted table | Interactive use, monitoring |
| `json` | Machine-readable JSON format | Automation, scripting, analysis |

## Integration with Other Commands

### Health Monitoring
```bash
# Comprehensive cluster check
./escmd.py health                    # Overall cluster health
./escmd.py cluster-settings          # Current settings
./escmd.py allocation display        # Allocation status
```

### Troubleshooting Allocation Issues
```bash
# Check allocation settings and status
./escmd.py cluster-settings | grep allocation
./escmd.py allocation display
./escmd.py health

# Investigate specific issues
./escmd.py allocation explain problematic-index
```

### Configuration Management
```bash
# Document current configuration
./escmd.py cluster-settings --format json > settings-backup.json
./escmd.py show-settings > tool-config.txt
```

## Best Practices

### Monitoring
1. **Regular Checks**: Review cluster settings periodically
2. **Change Tracking**: Export settings before making changes
3. **Documentation**: Keep records of setting changes and reasons
4. **Integration**: Include settings checks in monitoring workflows

### Troubleshooting
1. **Start with Settings**: Check cluster settings when investigating issues
2. **Compare Environments**: Use JSON output to compare settings across clusters
3. **Focus Areas**: Look at allocation, recovery, and discovery settings first
4. **Correlation**: Correlate settings with cluster behavior and performance

### Automation
1. **JSON Format**: Always use JSON output for automated processing
2. **Error Handling**: Check command exit codes in scripts
3. **Validation**: Validate JSON output before processing
4. **Logging**: Log settings changes for audit trails

## Related Commands

- [`allocation`](allocation-management.md) - Manage shard allocation settings
- [`health`](health-monitoring.md) - Monitor overall cluster health
- [`show-settings`](node-operations.md) - View escmd tool configuration
- [`nodes`](node-operations.md) - View node information and status

## Common Use Cases

### Daily Operations
```bash
# Morning cluster check
./escmd.py health
./escmd.py cluster-settings | head -20

# Quick allocation check
./escmd.py cluster-settings | grep -E "(allocation|exclude)"
```

### Maintenance Preparation
```bash
# Document current settings
./escmd.py cluster-settings --format json > pre-maintenance-settings.json

# Check for any temporary settings
./escmd.py cluster-settings | grep -i transient
```

### Issue Investigation
```bash
# Full settings export for analysis
./escmd.py cluster-settings --format json > issue-settings-$(date +%Y%m%d-%H%M).json

# Focus on problematic areas
./escmd.py cluster-settings | grep -E "(recovery|allocation|timeout)"
```

## Notes

- **Read-Only Operation**: This command only displays settings; use Elasticsearch APIs or other tools to modify settings
- **Permission Requirements**: Requires cluster monitoring permissions
- **Performance Impact**: Minimal impact on cluster performance
- **Real-Time Data**: Shows current settings as they exist in the cluster

---

*For setting modification, use Elasticsearch's cluster settings API or management tools like Kibana.*