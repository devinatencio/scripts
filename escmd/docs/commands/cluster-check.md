# Comprehensive Cluster Health Checks

Advanced cluster health monitoring with ILM error detection, replica validation, shard size monitoring, and integrated fixing capabilities.

## Quick Reference

```bash
# Basic health checks
./escmd.py cluster-check                      # Complete health assessment
./escmd.py cluster-check --show-details       # Extended information
./escmd.py cluster-check --format json        # JSON output

# Integrated replica fixing
./escmd.py cluster-check --fix-replicas 1 --dry-run  # Preview fixes
./escmd.py cluster-check --fix-replicas 1             # Execute fixes

# Configuration options
./escmd.py cluster-check --max-shard-size 100        # Custom shard threshold
./escmd.py cluster-check --skip-ilm                  # Skip ILM checks
./escmd.py cluster-check --ilm-limit 20              # Show more ILM unmanaged indices
```

## Overview

The `cluster-check` command provides comprehensive cluster health monitoring that goes beyond basic status checks. It performs deep analysis of:

- **ILM (Index Lifecycle Management)** errors and policy compliance
- **Replica configuration** validation and redundancy analysis
- **Shard size monitoring** with configurable thresholds
- **Coverage analysis** showing managed vs unmanaged indices

## Core Health Checks

### 🔍 ILM Error Detection

Identifies indices with Index Lifecycle Management errors and policy issues:

```bash
./escmd.py cluster-check                    # Shows ILM errors in health report
./escmd.py cluster-check --skip-ilm         # Skip ILM checks entirely
./escmd.py cluster-check --show-details     # Extended ILM error information
./escmd.py cluster-check --ilm-limit 25     # Show up to 25 unmanaged indices
```

**What It Detects:**
- **Step Errors**: Indices stuck in ERROR state during ILM execution
- **Policy Failures**: Misconfigured or failed ILM policies
- **Unmanaged Indices**: Indices without any ILM policy attached
- **Coverage Analysis**: Overview of managed vs unmanaged index counts

**Error Information Displayed:**
- **Index Name**: Full index name without truncation
- **Policy Name**: Associated ILM policy
- **Current Phase**: hot, warm, cold, frozen, delete
- **Current Action**: rollover, shrink, allocate, delete, etc.
- **Error Reason**: Detailed error message with retry counts
- **Step Information**: Current step and failure details

### 🔄 Replica Validation

Monitors replica configuration for data redundancy and availability:

```bash
./escmd.py cluster-check                    # Shows indices with 0 replicas
./escmd.py cluster-check --show-details     # Extended replica information
```

**What It Detects:**
- **Zero Replicas**: Indices with no replica shards (data loss risk)
- **Replica Configuration**: Current primary and replica shard counts
- **Redundancy Analysis**: Identifies potential single points of failure

**Information Displayed:**
- **Index Name**: Complete index identification
- **Shard Count**: Number of primary shards
- **Replica Count**: Current replica configuration
- **Risk Assessment**: Data loss risk indicators

### 📏 Shard Size Monitoring

Tracks shard sizes to identify performance and storage issues:

```bash
./escmd.py cluster-check                        # Default 50GB threshold
./escmd.py cluster-check --max-shard-size 100   # Custom 100GB threshold
./escmd.py cluster-check --show-details         # Detailed shard information
```

**What It Monitors:**
- **Large Shards**: Shards exceeding configurable size thresholds
- **Performance Impact**: Oversized shards affecting query performance
- **Storage Efficiency**: Suboptimal shard distribution patterns

**Threshold Configuration:**
- **Default**: 50GB per shard
- **Configurable**: Use `--max-shard-size N` for custom thresholds
- **Per-Environment**: Different thresholds for different cluster types

## Integrated Replica Fixing

### 🔧 Seamless Health-to-Fix Workflow

The cluster-check command can automatically fix replica issues discovered during health assessment:

```bash
# Discovery and planning
./escmd.py cluster-check --fix-replicas 1 --dry-run

# Execute fixes for discovered issues
./escmd.py cluster-check --fix-replicas 1

# Automation-friendly execution
./escmd.py cluster-check --fix-replicas 1 --force --format json
```

### Integrated Fixing Features

**Automatic Targeting:**
- **Smart Discovery**: Uses health check results to identify indices needing fixes
- **Precise Targeting**: Only targets indices with 0 replicas found during assessment
- **Context Preservation**: Maintains complete health check information during fixing

**Safety Features:**
- **Dry-Run Mode**: Preview all changes with `--dry-run` before execution
- **Confirmation Prompts**: Interactive confirmation before making changes
- **Force Mode**: Skip prompts for automation with `--force`
- **Validation**: Pre-flight checks ensure indices exist and are accessible

**Professional Integration:**
- **Seamless Flow**: Health assessment → Issue identification → Automated fixing
- **Visual Progression**: Clear workflow indicators and section transitions
- **Complete Context**: Full health report followed by focused fixing results

### Workflow Example

```bash
# 1. Assess cluster health and identify issues
./escmd.py -l production cluster-check

# 2. Plan replica fixes with dry-run
./escmd.py -l production cluster-check --fix-replicas 1 --dry-run

# 3. Execute fixes with confirmation
./escmd.py -l production cluster-check --fix-replicas 1

# 4. Verify changes took effect
./escmd.py -l production cluster-check
```

## Output Formats

### 📊 Rich Formatted Output (Default)

Professional multi-panel dashboard with:

**Summary Panel:**
- **ILM Status**: Error count and unmanaged index count
- **Replica Status**: Indices without replicas
- **Shard Status**: Large shards exceeding thresholds
- **Overall Health**: Color-coded status indicators

**ILM Coverage Overview:**
- **Total Indices**: Complete index count from ILM API
- **Successfully Managed**: Indices with working ILM policies
- **In Error State**: Indices with ILM failures
- **Without ILM Policy**: Unmanaged indices needing governance

**Detailed Tables:**
- **ILM Errors**: Full-width table with complete index names, policies, phases, actions, and error reasons
- **Unmanaged Indices**: Indices without ILM policies for governance review
- **No Replica Indices**: Indices at risk of data loss
- **Large Shards**: Performance optimization opportunities

**Recommendations Panel:**
- **Actionable Suggestions**: Based on detected issues
- **Best Practices**: Guidance for cluster optimization
- **Priority Actions**: Critical issues requiring immediate attention

### 📄 JSON Output

Machine-readable format for automation and monitoring:

```bash
./escmd.py cluster-check --format json > health-report.json
```

**JSON Structure:**
```json
{
  "cluster_name": "production-cluster",
  "timestamp": "2025-08-27T13:21:49",
  "checks": {
    "ilm_results": {
      "errors": [...],
      "no_policy": [...],
      "total_indices": 1982,
      "managed_count": 1930,
      "error_count": 3,
      "unmanaged_count": 49
    },
    "no_replica_indices": [...],
    "large_shards": [...]
  },
  "parameters": {
    "max_shard_size_gb": 50,
    "skip_ilm": false
  }
}
```

## Configuration Options

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--format` | Output format: `table` or `json` | `table` |
| `--max-shard-size` | Shard size threshold in GB | `50` |
| `--show-details` | Extended information display | `false` |
| `--skip-ilm` | Skip ILM checks entirely | `false` |
| `--ilm-limit` | Max unmanaged indices to show before truncating | `10` (config) |
| `--fix-replicas` | Set replica count for 0-replica indices | None |
| `--dry-run` | Preview replica fixes without applying | `false` |
| `--force` | Skip confirmation prompts | `false` |

### Configuration File Settings

The cluster-check command respects configuration settings in `escmd.yml`:

```yaml
settings:
  ilm_display_limit: 15  # Default: 10, show up to 15 unmanaged indices
```

**Configuration Options:**
- `ilm_display_limit`: Controls how many unmanaged ILM indices are displayed before showing "X more unmanaged" message
- Default value: `10`
- Command-line override: `--ilm-limit` argument takes precedence over config file setting

### Use Cases

#### 🔧 Daily Operations
```bash
# Morning cluster health check
./escmd.py cluster-check

# Weekly detailed review with extended ILM list
./escmd.py cluster-check --show-details --ilm-limit 50
```

#### 🤖 Automation & Monitoring
```bash
# Automated monitoring script
./escmd.py cluster-check --format json > /var/log/cluster-health.json

# Parse specific metrics
jq '.checks.ilm_results.error_count' /var/log/cluster-health.json
```

#### 🚨 Issue Resolution
```bash
# Comprehensive issue assessment with full ILM listing
./escmd.py cluster-check --show-details --ilm-limit 100

# Fix replica issues immediately
./escmd.py cluster-check --fix-replicas 1 --dry-run
./escmd.py cluster-check --fix-replicas 1
```

#### 📋 Governance & Compliance
```bash
# ILM policy coverage analysis
./escmd.py cluster-check --format json | jq '.checks.ilm_results'

# Replica compliance monitoring
./escmd.py cluster-check | grep -A10 "No Replicas"
```

## Best Practices

### Regular Monitoring
1. **Daily Health Checks**: Run cluster-check as part of daily operations
2. **Automated Monitoring**: Use JSON output for monitoring system integration
3. **Trend Analysis**: Track metrics over time to identify patterns

### Issue Resolution
1. **Prioritize Critical Issues**: Address replica and ILM errors first
2. **Use Dry-Run**: Always preview changes before execution
3. **Validate Fixes**: Re-run cluster-check after making changes

### Performance Optimization
1. **Monitor Shard Sizes**: Adjust `--max-shard-size` based on cluster characteristics
2. **ILM Policy Review**: Address unmanaged indices for better lifecycle management
3. **Replica Strategy**: Ensure appropriate replica counts for data redundancy

## Troubleshooting

### ILM API Issues
- **405 Method Not Allowed**: Use `--skip-ilm` for older Elasticsearch versions
- **Authentication Errors**: Verify ILM API access permissions
- **Timeout Issues**: Check cluster performance and API responsiveness

### Performance Considerations
- **Large Clusters**: Consider using `--skip-ilm` for very large clusters during peak hours
- **Network Latency**: Monitor execution time and adjust timeout settings if needed
- **API Load**: Spread cluster-check executions across different times for multiple clusters

### JSON Output Issues
- **Control Characters**: JSON output automatically sanitizes problematic characters
- **Large Output**: Use `jq` or similar tools to process large JSON responses
- **Encoding**: Ensure proper UTF-8 encoding for international cluster names

## Related Commands

- [`health`](health-monitoring.md) - Basic cluster health monitoring
- [`set-replicas`](replica-management.md) - Standalone replica management
- [`ilm`](ilm-management.md) - Index Lifecycle Management operations
- [`indices`](index-operations.md) - Index listing and management
