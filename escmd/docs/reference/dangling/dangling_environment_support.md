# Dangling Command Environment Support

## Overview

The dangling command now supports the `--env {environment}` parameter, which allows you to run dangling index reports across all clusters within a specified environment. This feature works similarly to the existing `--group {group_name}` functionality but operates on environments instead of cluster groups.

## What are Environments?

Environments in ESCMD are defined by the `env` field in your server configurations. Each server can belong to an environment (e.g., "production", "development", "staging"), and the `--env` parameter allows you to operate on all servers within that environment simultaneously.

### Environment vs Cluster Groups

| Feature | Cluster Groups | Environments |
|---------|----------------|-------------|
| Definition | Explicitly defined in configuration | Automatically derived from server `env` fields |
| Configuration Location | `cluster_groups` section in `escmd.yml` | `env` field in each server config |
| Purpose | Logical grouping of related clusters | Environment-based grouping (prod, dev, staging) |
| Flexibility | Manual curation required | Automatic based on server environment tags |

## Configuration

### Server Configuration Example

In your `elastic_servers.yml` file, define environments using the `env` field:

```yaml
servers:
  - name: prod-api-cluster
    hostname: prod-api.company.com
    port: 9200
    env: production
    use_ssl: true

  - name: prod-web-cluster
    hostname: prod-web.company.com
    port: 9200
    env: production
    use_ssl: true

  - name: staging-cluster
    hostname: staging.company.com
    port: 9200
    env: staging
    use_ssl: false

  - name: dev-cluster1
    hostname: dev1.company.com
    port: 9200
    env: development
    use_ssl: false

  - name: dev-cluster2
    hostname: dev2.company.com
    port: 9200
    env: development
    use_ssl: false
```

## Usage

### Basic Environment Report

Generate a dangling indices report for all clusters in the "production" environment:

```bash
./escmd.py dangling --env production
```

### JSON Format Output

Get environment report in JSON format for automation/scripting:

```bash
./escmd.py dangling --env production --format json
```

### Available Environments

To see what environments are available in your configuration:

```bash
./escmd.py locations
```

This will show all configured servers grouped by environment.

## Command Syntax

```bash
./escmd.py dangling --env {environment_name} [options]
```

### Parameters

- `--env {environment_name}`: Specifies the environment to analyze
- `--format {json|table}`: Output format (default: table)

### Examples

```bash
# Analyze production environment
./escmd.py dangling --env production

# Analyze staging environment with JSON output
./escmd.py dangling --env staging --format json

# Analyze development environment
./escmd.py dangling --env development
```

## Report Output

The environment report provides:

### Summary Statistics
- Total clusters analyzed in the environment
- Total dangling indices found across all clusters
- Number of clusters with dangling indices
- Number of unique nodes affected
- Time range of dangling indices (oldest to newest)

### Cluster Breakdown
- Status of each cluster in the environment
- Number of dangling indices per cluster
- Affected nodes per cluster
- Error details for any failed cluster queries

### Detailed Dangling Indices
- Complete list of dangling indices across all environment clusters
- Index names, UUIDs, creation dates
- Node locations for each dangling index

### Recommendations
- Actionable next steps based on findings
- Specific commands for cleanup operations
- Safety recommendations for data protection

## Error Handling

### Environment Not Found
If you specify an environment that doesn't exist:

```
❌ Environment 'invalid-env' not found.
Available environments: production, staging, development
```

### Empty Environment
If an environment exists but has no servers:

```
❌ Environment 'production' has no members.
```

### Network/Connection Issues
If individual clusters in the environment are unreachable, the report will:
- Continue processing other clusters
- Mark failed clusters in the breakdown
- Provide error details in the output
- Include failure count in summary statistics

## Integration with Existing Features

The `--env` parameter works alongside existing dangling command features:

### Compatible Options
- `--format json|table`: Choose output format
- All standard dangling command flags work with environment reports

### Exclusive Options
The following options cannot be used together:
- `--env` and `--group` (mutually exclusive)
- `--env` and single index operations (`<uuid>`, `--delete`, etc.)

## Performance Considerations

### Parallel Processing
- Environment reports process clusters in parallel (up to 5 concurrent connections)
- Progress bar shows real-time collection status
- Timeout protection prevents hanging on unresponsive clusters

### Resource Usage
- Memory usage scales with number of dangling indices found
- Network bandwidth depends on cluster response sizes
- CPU usage is minimal during data collection phase

## Security Considerations

### Authentication
- Uses same authentication mechanism as individual cluster access
- Inherits SSL/TLS settings from each cluster configuration
- Respects per-cluster authentication settings

### Data Safety
- Read-only operation - no data is modified
- Safe to run in production environments
- Provides dry-run capabilities for cleanup operations

## Troubleshooting

### Common Issues

#### Environment Not Detected
**Problem**: Environment shows as not found despite being configured
**Solution**: Verify `env` field is correctly set in server configurations

```yaml
# Correct
- name: my-cluster
  hostname: cluster.example.com
  env: production

# Incorrect (missing env field)
- name: my-cluster  
  hostname: cluster.example.com
```

#### Partial Failures
**Problem**: Some clusters in environment fail to respond
**Solution**: Check network connectivity and authentication for failed clusters

#### Slow Performance
**Problem**: Environment report takes too long
**Solution**: 
- Check network latency to clusters
- Verify clusters are responsive
- Consider running reports during off-peak hours

## Advanced Usage

### Scripting and Automation

Environment reports work well in automated workflows:

```bash
#!/bin/bash
# Check all environments for dangling indices

for env in production staging development; do
    echo "Checking environment: $env"
    ./escmd.py dangling --env $env --format json > "dangling_report_${env}.json"
done
```

### Monitoring Integration

JSON output can be integrated with monitoring systems:

```bash
# Get production environment status
RESULT=$(./escmd.py dangling --env production --format json)
DANGLING_COUNT=$(echo "$RESULT" | jq '.summary.total_dangling_indices')

if [ "$DANGLING_COUNT" -gt 0 ]; then
    echo "ALERT: $DANGLING_COUNT dangling indices found in production"
    # Send alert to monitoring system
fi
```

## Related Commands

### Complementary Operations

After identifying issues with environment reports, use these commands for resolution:

```bash
# Individual cluster cleanup
./escmd.py --location cluster-name dangling --cleanup-all --dry-run

# Specific index deletion  
./escmd.py --location cluster-name dangling <uuid> --delete

# Health check after cleanup
./escmd.py --location cluster-name health
```

### Alternative Approaches

```bash
# Compare with cluster group reports
./escmd.py dangling --group my-group

# Individual cluster analysis
./escmd.py --location specific-cluster dangling

# Comprehensive health check
./escmd.py --location cluster-name cluster-check
```

## Version History

- **v1.0**: Initial implementation of `--env` parameter support
- **v1.0**: Added environment validation and error handling
- **v1.0**: Integrated with existing dangling report infrastructure
- **v1.0**: Added comprehensive help and documentation