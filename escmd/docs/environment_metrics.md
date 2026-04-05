# Environment-Specific Metrics Configuration

This document describes the environment-specific metrics configuration feature introduced in ESCMD v3.7.0 that allows ESCMD to automatically select the correct InfluxDB endpoint and database based on the `--env` parameter.

## Overview

The environment-specific metrics configuration feature enables automatic detection of the correct metrics database settings when using the `--metrics` flag with different environments. This eliminates the need to manually configure different endpoints for different environments.

## Configuration

The metrics configuration is defined in the `escmd.yml` file under the `metrics` section. The configuration includes both default settings and environment-specific overrides.

### Structure

```yaml
metrics:
  # Default/fallback configuration
  type: influxdb
  endpoint: http://localhost:8086
  database: escmd
  username:
  password:
  token:
  org:
  bucket:
  verify_ssl: true
  timeout: 10

  # Environment-specific configurations
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

## Environment Mappings

Based on the environment table provided, the following mappings are configured:

| Environment | Location/Type | InfluxDB Endpoint | Database |
|-------------|---------------|-------------------|----------|
| biz | BIZ | http://192.168.0.142:8086 | elk-stats |
| lab | LAB | http://influxdb.ops.example.com:8086 | elk-stats |
| ops | OPS | http://influxdb.ops.example.com:8086 | elk-stats |
| us | US | http://na-metrics.int.example.com:8086 | elk-stats |
| eu | EU | http://na-metrics.int.example.com:8086 | elk-stats |
| in | IN | http://na-metrics.int.example.com:8086 | elk-stats |

## Usage

### Basic Usage

To use environment-specific metrics with the dangling command:

```bash
# For BIZ environment - uses http://192.168.0.142:8086
./escmd.py dangling --env biz --metrics

# For LAB environment - uses http://influxdb.ops.example.com:8086
./escmd.py dangling --env lab --metrics

# For US environment - uses http://na-metrics.int.example.com:8086
./escmd.py dangling --env us --metrics
```

### Without Environment

If no `--env` parameter is specified, the default configuration is used:

```bash
# Uses default endpoint: http://localhost:8086
./escmd.py dangling --metrics
```

### With Cleanup Operations

The environment-specific configuration also works with cleanup operations:

```bash
# Cleanup dangling indices in BIZ environment and send metrics
./escmd.py dangling --env biz --cleanup-all --metrics --dry-run

# Cleanup specific dangling index in LAB environment
./escmd.py dangling --env lab --delete <uuid> --metrics
```

## How It Works

1. **Environment Detection**: When the `--env` parameter is provided, the system extracts the environment name from the command arguments.

2. **Configuration Resolution**: The configuration manager looks up the environment-specific settings in the `metrics.environments` section of `escmd.yml`.

3. **Configuration Merging**: If an environment-specific configuration is found, it's merged with the base metrics configuration. Environment-specific settings override the base settings.

4. **Fallback Behavior**: If no environment-specific configuration exists for the specified environment, the system falls back to the default metrics configuration.

5. **Metrics Client Creation**: The merged configuration is used to create the appropriate metrics client for sending data to InfluxDB.

## Configuration Priority

The configuration resolution follows this priority order:

1. **Environment Variables**: `ESCMD_METRICS_*` environment variables (highest priority)
2. **Environment-Specific Config**: Settings from `metrics.environments.<env>` in `escmd.yml`
3. **Default Config**: Base settings from `metrics` section in `escmd.yml`
4. **System Defaults**: Hard-coded defaults (lowest priority)

## Adding New Environments

To add a new environment configuration:

1. Add a new entry under `metrics.environments` in `escmd.yml`:

```yaml
metrics:
  # ... existing configuration ...
  environments:
    # ... existing environments ...
    new_env:
      endpoint: http://your-influxdb-server:8086
      database: your-database-name
      # Optional: override other settings
      username: your-username
      password: your-password
```

2. The new environment will be automatically available for use:

```bash
./escmd.py dangling --env new_env --metrics
```

## Troubleshooting

### Configuration Issues

If you encounter configuration errors:

1. **Check Environment Name**: Ensure the environment name matches exactly (case-insensitive) with the configuration.

2. **Validate YAML Syntax**: Ensure the `escmd.yml` file has valid YAML syntax.

3. **Check Required Fields**: Ensure at least the `endpoint` field is configured for each environment.

### Testing Configuration

You can verify your environment configuration by checking the logs when running commands with metrics enabled. The system will log which endpoint and database it's connecting to.

### Debug Mode

Enable debug logging to see detailed configuration resolution:

```bash
./escmd.py dangling --env biz --metrics --log-level DEBUG
```

## Security Considerations

- Store sensitive credentials (usernames, passwords, tokens) securely
- Consider using environment variables for credentials instead of storing them in the YAML file
- Ensure InfluxDB endpoints are accessible from your network
- Use HTTPS endpoints when possible for secure communication

## Examples

### Complete Command Examples

```bash
# List dangling indices in BIZ environment and send metrics
./escmd.py dangling --env biz --metrics

# Dry-run cleanup in LAB environment with metrics
./escmd.py dangling --env lab --cleanup-all --dry-run --metrics

# Delete specific dangling index in US environment
./escmd.py dangling <uuid> --env us --delete --metrics

# Batch cleanup with metrics in EU environment
./escmd.py dangling --env eu --cleanup-all --batch 10 --metrics
```

### Environment Variable Override

You can still override configuration using environment variables:

```bash
# Override endpoint for a specific run
ESCMD_METRICS_ENDPOINT=http://custom-server:8086 \
./escmd.py dangling --env biz --metrics
```

This feature provides seamless integration with multiple InfluxDB environments while maintaining backward compatibility with existing configurations.

## Version Information

This environment-specific metrics configuration feature was introduced in ESCMD v3.7.0 (October 29, 2025) and is available in all subsequent versions.