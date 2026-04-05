# Dangling Indices Metrics Integration

This document describes how to use the `--metrics` flag with the `dangling` command to send dangling indices statistics to InfluxDB or VictoriaMetrics.

## Overview

The dangling metrics feature allows you to automatically collect and send dangling indices statistics to time-series databases for monitoring and alerting purposes. This is particularly useful for:

- Monitoring cluster health over time
- Setting up alerts for dangling indices
- Tracking cleanup operations
- Creating dashboards for operations teams

## Configuration

### Configuration File

Add a `metrics` section to your `escmd.yml` configuration file:

```yaml
# Metrics Configuration for InfluxDB/VictoriaMetrics
metrics:
  # Database type: influxdb, influxdb2, or victoriametrics
  type: influxdb
  # Database endpoint URL
  endpoint: http://localhost:8086
  # Database name (InfluxDB v1) or bucket (InfluxDB v2)
  database: escmd
  # Authentication credentials
  username: your_username
  password: your_password
  # Token for InfluxDB v2 authentication (alternative to username/password)
  token: your_token_here
  # Organization for InfluxDB v2
  org: your_org
  # Bucket for InfluxDB v2 (alternative to database)
  bucket: escmd
  # SSL verification
  verify_ssl: true
  # Request timeout in seconds
  timeout: 10
```

### Environment Variables

You can also configure metrics using environment variables (these take precedence over configuration file settings):

```bash
export ESCMD_METRICS_ENDPOINT="http://localhost:8086"
export ESCMD_METRICS_DATABASE="escmd"
export ESCMD_METRICS_USERNAME="your_username"
export ESCMD_METRICS_PASSWORD="your_password"
export ESCMD_METRICS_TOKEN="your_token"  # For InfluxDB v2
export ESCMD_METRICS_TYPE="influxdb"     # influxdb, influxdb2, victoriametrics
export ESCMD_METRICS_ORG="your_org"      # InfluxDB v2 only
export ESCMD_METRICS_BUCKET="escmd"      # InfluxDB v2 only
export ESCMD_METRICS_VERIFY_SSL="true"
```

## Usage

### Single Cluster Metrics

Send dangling indices metrics for the current cluster:

```bash
./escmd.py dangling --metrics
```

This will:
1. Scan for dangling indices
2. Count the found indices and affected nodes
3. Send metrics to the configured database
4. Display a confirmation message

### Dry Run Mode

Test your metrics configuration without actually sending data:

```bash
./escmd.py dangling --metrics --dry-run
```

This will show you exactly what would be sent to InfluxDB/VictoriaMetrics in line protocol format:

```
elastic_dangling_deletion,cluster=prod-cluster-01,environment=production found=5i,deleted=0i,nodes_affected=2i 1634567890000000000
```

### Cluster Group Metrics

Send metrics for all clusters in a group:

```bash
./escmd.py dangling --group prod --metrics
```

With dry-run to preview:

```bash
./escmd.py dangling --group prod --metrics --dry-run
```

### Environment Metrics

Send metrics for all clusters in an environment:

```bash
./escmd.py dangling --env production --metrics
```

With dry-run to preview:

```bash
./escmd.py dangling --env production --metrics --dry-run
```

### Cleanup with Metrics

Send metrics after performing cleanup operations:

```bash
./escmd.py dangling --cleanup-all --metrics
```

Preview cleanup metrics without performing actual cleanup:

```bash
./escmd.py dangling --cleanup-all --metrics --dry-run
```

Note: When using `--dry-run` with `--cleanup-all`, no actual cleanup is performed, but metrics are calculated based on what would be cleaned up.

## Metrics Format

The following metrics are sent to your time-series database:

### Measurement Name
```
elastic_dangling_deletion
```

### Tags
- `cluster`: Elasticsearch cluster name
- `environment`: Environment name (when using `--env`)
- `report_type`: Type of report ("cluster_group" or "environment")
- `operation`: Operation type ("cleanup_all" for cleanup operations)

### Fields
- `found`: Number of dangling indices found (integer)
- `deleted`: Number of dangling indices successfully deleted (integer)
- `nodes_affected`: Number of nodes affected by dangling indices (integer)

### Example Line Protocol
```
elastic_dangling_deletion,cluster=prod-cluster-01,environment=production found=5i,deleted=3i,nodes_affected=2i 1634567890000000000
```

## Supported Databases

### InfluxDB v1.x
```yaml
metrics:
  type: influxdb
  endpoint: http://localhost:8086
  database: escmd
  username: your_username
  password: your_password
```

### InfluxDB v2.x
```yaml
metrics:
  type: influxdb2
  endpoint: http://localhost:8086
  org: your_organization
  bucket: escmd
  token: your_api_token
```

### VictoriaMetrics
```yaml
metrics:
  type: victoriametrics
  endpoint: http://localhost:8428
  # No authentication typically required for VictoriaMetrics
```

## Cron Integration

You can set up automated metrics collection using cron:

```bash
# Check for dangling indices every hour and send metrics
0 * * * * /path/to/escmd/escmd.py dangling --metrics --locations prod-cluster

# Daily environment-wide scan
0 6 * * * /path/to/escmd/escmd.py dangling --env production --metrics

# Test your cron job with dry-run first
/path/to/escmd/escmd.py dangling --metrics --dry-run --locations prod-cluster
```

## Monitoring and Alerting

### Grafana Dashboard Query Examples

**Total dangling indices by cluster:**
```sql
SELECT last("found") FROM "elastic_dangling_deletion" 
WHERE $timeFilter 
GROUP BY "cluster"
```

**Nodes affected over time:**
```sql
SELECT mean("nodes_affected") FROM "elastic_dangling_deletion" 
WHERE $timeFilter 
GROUP BY time(1h), "cluster"
```

### Alert Examples

**High number of dangling indices:**
```sql
SELECT last("found") FROM "elastic_dangling_deletion" 
WHERE time >= now() - 1h 
GROUP BY "cluster"
HAVING last("found") > 10
```

**Cleanup efficiency:**
```sql
SELECT last("deleted") / last("found") * 100 as cleanup_rate 
FROM "elastic_dangling_deletion" 
WHERE time >= now() - 1d AND "deleted" > 0
GROUP BY "cluster"
```

## Troubleshooting

### Common Issues

**"Metrics Configuration Error"**
- Verify your configuration file has the `metrics` section
- Check that `endpoint` is specified
- Ensure the endpoint URL is reachable

**"Metrics Send Failed"**
- Check network connectivity to your metrics database
- Verify authentication credentials
- Check database logs for connection issues

**SSL Certificate Issues**
- Set `verify_ssl: false` for testing (not recommended for production)
- Ensure SSL certificates are properly configured

### Testing Configuration

#### Quick Dry-Run Test

The easiest way to test your configuration:

```bash
./escmd.py dangling --metrics --dry-run
```

This will validate your configuration and show you exactly what would be sent without actually sending it. Output shows clean line protocol format perfect for automation:

```
elastic_dangling_deletion,cluster=my-cluster found=3i,deleted=0i,nodes_affected=2i 1634567890000000000
```

#### Programmatic Test

Test your metrics configuration programmatically:

```python
from metrics.dangling_metrics import DanglingMetrics
from configuration_manager import ConfigurationManager

config_manager = ConfigurationManager()
metrics_handler = DanglingMetrics(config_manager=config_manager)

if metrics_handler.is_enabled():
    print("✅ Metrics configuration is valid")
    if metrics_handler.test_connection():
        print("✅ Connection to metrics database successful")
    else:
        print("❌ Failed to connect to metrics database")
else:
    print("❌ Metrics configuration is invalid or missing")
```

### Debug Mode

Enable debug logging to troubleshoot metrics issues:

```bash
export ESCMD_LOG_LEVEL=DEBUG
./escmd.py dangling --metrics --dry-run
```

For actual sending with debug:

```bash
export ESCMD_LOG_LEVEL=DEBUG
./escmd.py dangling --metrics
```

## Security Considerations

- Store sensitive credentials in environment variables rather than configuration files
- Use token-based authentication when available (InfluxDB v2)
- Enable SSL/TLS for production deployments
- Restrict network access to your metrics database
- Regularly rotate authentication credentials

## Performance Impact

- Metrics collection adds minimal overhead to dangling operations
- Network latency to metrics database may slightly increase execution time
- Failed metrics transmission does not affect the primary dangling operation
- Batch metrics are used for environment-wide operations to minimize database load

## Compatibility Requirements

### Python Version Compatibility

The metrics functionality is compatible with **Python 3.6 and later**. If you encounter an error like:

```
__init__() got an unexpected keyword argument 'cap'
```

This indicates you may be running Python 3.6 on your remote server. The error has been fixed in recent versions of ESCMD by using Python 3.6-compatible subprocess syntax.

### Remote Server Considerations

When running ESCMD with metrics on remote servers:

- Ensure Python 3.6+ is installed
- Verify network connectivity to your metrics database
- Consider firewall rules for metrics database access
- Test with `--dry-run` first to validate configuration

### Version Update

If you're experiencing subprocess-related errors, ensure you're using the latest version of ESCMD that includes Python 3.6 compatibility fixes.