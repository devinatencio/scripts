# Dangling Indices Cluster Group Reports

This document describes the new cluster group reporting functionality for dangling indices in ESCMD.

## Overview

The dangling cluster group report feature allows you to analyze dangling indices across multiple clusters within a defined cluster group. This provides a comprehensive view of dangling indices across your entire infrastructure, making it easier to identify and manage orphaned index data.

## Features

- **Multi-cluster Analysis**: Query dangling indices across all clusters in a group simultaneously
- **Parallel Processing**: Efficient data collection using concurrent requests
- **Rich Formatting**: Beautiful table output with consistent theming
- **JSON Export**: Machine-readable output for automation and integration
- **Comprehensive Statistics**: Aggregated metrics and detailed breakdowns
- **Error Handling**: Robust handling of connection failures and timeouts

## Prerequisites

1. **Cluster Groups Configuration**: You must have cluster groups defined in your `escmd.yml` or `elastic_servers.yml` file
2. **DanglingReport Module**: The new `reports.dangling_report` module must be available
3. **Individual Cluster Access**: Each cluster in the group must be accessible via ESCMD

## Configuration

### Setting Up Cluster Groups

Add cluster groups to your configuration file:

```yaml
cluster_groups:
  development:
    description: "Development environment clusters"
    clusters:
      - dev-es-01
      - dev-es-02
      
  production:
    description: "Production environment clusters"  
    clusters:
      - prod-east-01
      - prod-east-02
      - prod-west-01
      - prod-west-02
```

### Verify Configuration

Check your cluster groups are properly configured:

```bash
./escmd.py cluster-groups
```

## Usage

### Basic Syntax

```bash
./escmd.py dangling --group <group_name> [--format <json|table>]
```

### Examples

#### Table Format Report (Default)

```bash
# Generate report for development environment
./escmd.py dangling --group development

# Generate report for production environment  
./escmd.py dangling --group production
```

#### JSON Format Report

```bash
# Export production dangling data as JSON
./escmd.py dangling --group production --format json

# Export for automation/monitoring
./escmd.py dangling --group development --format json > dev_dangling_report.json
```

#### Using in ESterm

```
> dangling --group development
> dangling --group production --format json
```

## Report Structure

### Table Format Output

The table format provides a comprehensive visual report including:

1. **Title Panel**: Group name and generation timestamp
2. **Summary Statistics**: Overall status, affected clusters, nodes, and time ranges
3. **Cluster Breakdown**: Per-cluster status and dangling counts
4. **Detailed Indices**: Information about specific dangling indices (if any found)
5. **Recommendations**: Actionable next steps based on findings

### JSON Format Output

```json
{
  "report_type": "cluster_group_dangling_analysis",
  "group_name": "production",
  "timestamp": "2025-01-01T12:00:00.000Z",
  "summary": {
    "cluster_count": 4,
    "clusters_queried_successfully": 4,
    "clusters_failed": 0,
    "total_dangling_indices": 3,
    "clusters_with_dangling": 2,
    "unique_nodes_affected": 5,
    "oldest_dangling_timestamp": 1640995200000,
    "newest_dangling_timestamp": 1641081600000
  },
  "clusters": {
    "prod-east-01": {
      "status": "success",
      "dangling_count": 2,
      "dangling_indices": [...],
      "cluster_info": {...}
    },
    "prod-east-02": {
      "status": "success", 
      "dangling_count": 0,
      "dangling_indices": [],
      "cluster_info": {...}
    }
  }
}
```

## Understanding the Output

### Status Indicators

- **✅ OK**: No dangling indices found
- **⚠️ Issues**: Dangling indices detected
- **❌ Error**: Connection or query failure

### Summary Metrics

- **Overall Status**: Clean (no dangling) or Issues Found
- **Clusters Analyzed**: Successfully queried vs failed
- **Clusters Affected**: Number with dangling indices
- **Nodes Affected**: Unique nodes containing dangling data
- **Time Range**: Creation date range of dangling indices

### Recommendations

The report provides contextual recommendations:

- **Clean Clusters**: Maintenance and monitoring suggestions
- **Affected Clusters**: Cleanup commands and safety guidelines
- **Failed Queries**: Troubleshooting steps

## Performance Considerations

- **Parallel Processing**: Up to 5 clusters queried simultaneously
- **Timeout Handling**: 60-second timeout per cluster
- **Progress Tracking**: Real-time progress indication
- **Error Resilience**: Continues processing despite individual cluster failures

## Integration with Existing Workflows

### Monitoring Scripts

```bash
#!/bin/bash
# Daily dangling indices check
./escmd.py dangling --group production --format json > daily_dangling_$(date +%Y%m%d).json

# Check if any dangling indices found
if [ $(jq '.summary.total_dangling_indices' daily_dangling_$(date +%Y%m%d).json) -gt 0 ]; then
    echo "WARNING: Dangling indices detected in production"
    # Send alert or notification
fi
```

### Automated Cleanup

```bash
# Generate report and identify affected clusters
./escmd.py dangling --group development --format json | \
  jq -r '.clusters | to_entries[] | select(.value.dangling_count > 0) | .key' | \
  while read cluster; do
    echo "Processing dangling indices in $cluster"
    ./escmd.py --location "$cluster" dangling --cleanup-all --dry-run
  done
```

## Troubleshooting

### Common Issues

1. **Group Not Found**
   - Verify cluster group exists: `./escmd.py cluster-groups`
   - Check configuration file syntax

2. **Connection Failures**
   - Individual cluster connectivity issues
   - Check network access and authentication

3. **Import Errors**
   - Ensure `reports` module is properly installed
   - Verify Python path includes ESCMD directory

4. **Timeout Issues**
   - Large clusters may take longer to respond
   - Network latency can cause timeouts

### Debug Information

For detailed debugging, check the logs and error messages in the output. The system provides comprehensive error reporting for each cluster query.

## API Reference

### DanglingReport Class

```python
from reports import DanglingReport

# Initialize report generator
report = DanglingReport(
    configuration_manager=config_manager,
    console=console,
    theme_styles=theme_styles
)

# Generate report
result = report.generate_cluster_group_report(
    group_name='production',
    format_type='json'
)
```

### Key Methods

- `generate_cluster_group_report()`: Main report generation method
- `_collect_dangling_data()`: Parallel data collection
- `_get_cluster_dangling_data()`: Single cluster data retrieval
- `_format_json_report()`: JSON output formatting
- `_display_table_report()`: Rich table display

## Future Enhancements

Potential improvements for future versions:

- **Historical Tracking**: Track dangling indices over time
- **Alerting Integration**: Built-in notification systems
- **Custom Filtering**: Filter by index patterns or age
- **Bulk Operations**: Multi-cluster cleanup operations
- **Performance Optimization**: Caching and incremental updates

## Related Commands

- `./escmd.py cluster-groups`: View available cluster groups
- `./escmd.py dangling`: Single cluster dangling analysis
- `./escmd.py health --group <name>`: Multi-cluster health reports
- `./escmd.py --location <cluster> dangling --cleanup-all`: Cleanup operations

## Support

For issues or questions about cluster group dangling reports:

1. Check this documentation
2. Verify cluster group configuration
3. Test individual cluster connectivity
4. Review error messages and logs
5. Consult the main ESCMD documentation