# Dangling Indices Metrics Feature

This document provides a quick start guide for the dangling indices metrics feature in escmd, including the new environment-specific auto-configuration introduced in v3.7.0.

## Overview

The `--metrics` flag for the `dangling` command allows you to automatically send dangling indices statistics to InfluxDB or VictoriaMetrics for monitoring and alerting purposes. As of v3.7.0, the system supports environment-specific auto-configuration that automatically selects the correct InfluxDB endpoint and database based on the `--env` parameter.

## Quick Start

### 1. Configure Metrics

Add metrics configuration to your `escmd.yml` file. As of v3.7.0, you can include environment-specific configurations:

```yaml
metrics:
  # Default configuration
  type: influxdb
  endpoint: http://localhost:8086
  database: escmd
  username: your_username
  password: your_password
  verify_ssl: true
  timeout: 10
  
  # Environment-specific configurations (v3.7.0+)
  environments:
    biz:
      endpoint: http://192.168.0.142:8086
      database: elk-stats
    lab:
      endpoint: http://influxdb.ops.example.com:8086
      database: elk-stats
    us:
      endpoint: http://na-metrics.int.example.com:8086
      database: elk-stats
```

### 2. Test Configuration (Dry Run)

Test your setup without sending actual data:

```bash
./escmd.py dangling --metrics --dry-run
```

This will show you exactly what would be sent to your metrics database:

```
elastic_dangling_deletion,cluster=prod-cluster-01 found=5i,deleted=0i,nodes_affected=2i 1634567890000000000
```

### 3. Send Real Metrics

Once you've validated the configuration, remove `--dry-run`:

```bash
./escmd.py dangling --metrics
```

## Usage Examples

### Single Cluster
```bash
./escmd.py dangling --metrics
```

### Environment-Wide (Auto-Configuration v3.7.0+)
```bash
# Automatically uses BIZ environment endpoint and database
./escmd.py dangling --env biz --metrics

# Automatically uses LAB environment endpoint and database  
./escmd.py dangling --env lab --metrics

# Falls back to default configuration for unknown environments
./escmd.py dangling --env production --metrics
```

### Cluster Group
```bash
./escmd.py dangling --group prod --metrics
```

### With Cleanup Operations
```bash
./escmd.py dangling --cleanup-all --metrics
```

## Cron Integration

Set up automated monitoring:

```bash
# Every 6 hours - check for dangling indices
0 */6 * * * /path/to/escmd.py dangling --metrics --locations prod-cluster

# Daily environment scan
0 2 * * * /path/to/escmd.py dangling --env production --metrics
```

## Metrics Format

**Measurement**: `elastic_dangling_deletion`

**Tags**:
- `cluster`: Elasticsearch cluster name
- `environment`: Environment name (when applicable)
- `operation`: Operation type (e.g., "cleanup_all")

**Fields**:
- `found`: Number of dangling indices found (integer)
- `deleted`: Number successfully deleted (integer) 
- `nodes_affected`: Number of nodes affected (integer)

## Configuration Options

### File-based (escmd.yml)

#### Basic Configuration
```yaml
metrics:
  type: influxdb          # influxdb, influxdb2, victoriametrics
  endpoint: http://localhost:8086
  database: escmd
  username: admin
  password: secret
  verify_ssl: true
  timeout: 10
```

#### Environment-Specific Configuration (v3.7.0+)
```yaml
metrics:
  # Base configuration (fallback)
  type: influxdb
  endpoint: http://localhost:8086
  database: escmd
  
  # Environment-specific overrides
  environments:
    biz:
      endpoint: http://192.168.0.142:8086
      database: elk-stats
    lab:
      endpoint: http://influxdb.ops.example.com:8086
      database: elk-stats
    ops:
      endpoint: http://influxdb.ops.example.com:8086
      database: elk-stats
    us:
      endpoint: http://na-metrics.int.example.com:8086
      database: elk-stats
    eu:
      endpoint: http://na-metrics.int.example.com:8086
      database: elk-stats
    in:
      endpoint: http://na-metrics.int.example.com:8086
      database: elk-stats
```

### Environment Variables
```bash
export ESCMD_METRICS_ENDPOINT="http://localhost:8086"
export ESCMD_METRICS_DATABASE="escmd"
export ESCMD_METRICS_USERNAME="admin"
export ESCMD_METRICS_PASSWORD="secret"
export ESCMD_METRICS_TYPE="influxdb"
```

## Supported Databases

- **InfluxDB v1.x**: Basic username/password auth
- **InfluxDB v2.x**: Token-based authentication
- **VictoriaMetrics**: HTTP endpoint compatible

## Testing

Run the test suite to validate your setup:

```bash
python3 test_dangling_metrics.py
```

Or run the interactive examples:

```bash
python3 examples/dangling_metrics_example.py
```

## Environment-Specific Features (v3.7.0+)

### Automatic Environment Detection
- **Zero Configuration**: Simply use `--env <environment>` and metrics automatically route to the correct endpoint
- **Fallback Behavior**: Unknown environments gracefully fall back to default configuration
- **Priority Resolution**: Environment variables → Environment config → Base config → Defaults

### Supported Environments
- `biz`: Routes to http://192.168.0.142:8086 with elk-stats database
- `lab`/`ops`: Routes to http://influxdb.ops.example.com:8086 with elk-stats database
- `us`/`eu`/`in`: Routes to http://na-metrics.int.example.com:8086 with elk-stats database

## Troubleshooting

### Common Issues

1. **"Metrics Configuration Error"**
   - Verify `metrics` section exists in escmd.yml
   - Check endpoint URL is reachable
   - For environment-specific configs, verify environment name matches exactly

2. **"Metrics Send Failed"** 
   - Test connectivity to metrics database
   - Verify authentication credentials
   - Check database logs
   - For environment configs, test the specific endpoint URL

3. **Environment Not Found (v3.7.0+)**
   - Check that environment name in `--env` matches configuration
   - Environment names are case-insensitive
   - Unknown environments fall back to default configuration

3. **SSL Issues**
   - Set `verify_ssl: false` for testing
   - Ensure certificates are properly configured

### Debug Mode

Enable detailed logging:

```bash
export ESCMD_LOG_LEVEL=DEBUG
./escmd.py dangling --metrics --dry-run
```

## Best Practices

1. **Always test with `--dry-run` first**
2. **Use environment variables for sensitive credentials**
3. **Monitor metrics database disk usage**
4. **Set up alerts for high dangling index counts**
5. **Create Grafana dashboards for visualization**

## Example Grafana Queries

### Current Dangling Indices by Cluster
```sql
SELECT last("found") FROM "elastic_dangling_deletion" 
WHERE $timeFilter GROUP BY "cluster"
```

### Cleanup Efficiency
```sql
SELECT mean("deleted") / mean("found") * 100 
FROM "elastic_dangling_deletion" 
WHERE $timeFilter AND "deleted" > 0
GROUP BY time(1d)
```

## Files Modified

This feature adds/modifies the following files:

- `cli/argument_parser.py` - Added `--metrics` flag
- `configuration_manager.py` - Added `get_metrics_config()` method
- `handlers/dangling_handler.py` - Integrated metrics functionality
- `metrics/dangling_metrics.py` - Core metrics handling (already existed)
- `escmd.yml` - Added metrics configuration section

## For More Information

See the complete documentation: `docs/dangling-metrics.md`
