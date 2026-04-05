# Logging Feature

The escmd logging feature provides comprehensive file-based logging for command execution, particularly useful for cron jobs and automated monitoring tasks.

## Overview

The logging system automatically captures detailed information about command execution, including:

- Command start/completion timestamps
- Environment and configuration details
- Metrics operations and results
- Error messages and troubleshooting information
- Performance data and statistics

## Automatic Logging

Logging is automatically enabled for specific commands that are commonly used in automated environments:

- `dangling` - Dangling indices operations
- `storage` - Storage analysis
- `lifecycle` - ILM operations
- `cleanup` - Cleanup operations
- `repositories` - Repository management

## Log File Location

All log files are stored in the `logs/` directory within your escmd installation:

```
escmd/
├── logs/
│   ├── dangling_us_20250115.log
│   ├── dangling_prod_20250115.log
│   ├── storage_us_20250115.log
│   └── metrics_dangling_us_20250115.log
```

## Log File Naming Convention

Log files follow this naming pattern:
```
{command}_{environment}_{date}.log
```

Examples:
- `dangling_us_20250115.log` - Dangling command for 'us' environment
- `storage_prod_20250115.log` - Storage command for 'prod' environment
- `metrics_dangling_dev_20250115.log` - Metrics for dangling command

## Log Rotation

- **Maximum file size**: 10MB per log file
- **Backup count**: 5 rotated files are kept
- **Encoding**: UTF-8
- **Automatic cleanup**: Old logs beyond the backup count are automatically removed

## Command Line Options

### Log Level Control

Control the verbosity of logging with the `--log-level` option:

```bash
./escmd.py dangling --metrics --env us --log-level DEBUG
./escmd.py dangling --metrics --env us --log-level INFO     # Default
./escmd.py dangling --metrics --env us --log-level WARNING
./escmd.py dangling --metrics --env us --log-level ERROR
```

Available log levels:
- **DEBUG**: Detailed information for troubleshooting
- **INFO**: General operational information (default)
- **WARNING**: Warning messages about potential issues
- **ERROR**: Error messages
- **CRITICAL**: Critical error messages

### Custom Log File (Legacy)

For backward compatibility, you can specify a custom log file with the `--log-file` option:

```bash
./escmd.py dangling --log-file /path/to/custom.log
```

## Usage Examples for Cron Jobs

### Basic Metrics Collection

```bash
# Run dangling metrics every hour
0 * * * * cd /path/to/escmd && ./escmd.py dangling --metrics --env us
```

### Daily Cleanup with Debug Logging

```bash
# Run cleanup every day at 2 AM with debug logging
0 2 * * * cd /path/to/escmd && ./escmd.py dangling --cleanup-all --env prod --log-level DEBUG
```

### Multiple Environments

```bash
# Monitor multiple environments
0 * * * * cd /path/to/escmd && ./escmd.py dangling --metrics --env us
15 * * * * cd /path/to/escmd && ./escmd.py dangling --metrics --env eu
30 * * * * cd /path/to/escmd && ./escmd.py dangling --metrics --env prod
```

## Log Content Examples

### Successful Dangling Command Execution

```
2025-01-15 14:30:01,123 - INFO - Starting escmd command: dangling
2025-01-15 14:30:01,124 - INFO - Environment: us
2025-01-15 14:30:01,124 - INFO - Metrics reporting enabled
2025-01-15 14:30:01,125 - INFO - Starting dangling indices operation
2025-01-15 14:30:01,126 - INFO - Command arguments: cleanup_all=False, group=None, env=us, metrics=True
2025-01-15 14:30:01,234 - INFO - Retrieving dangling indices from cluster
2025-01-15 14:30:02,456 - INFO - Found 3 dangling indices
2025-01-15 14:30:02,457 - INFO - Cluster: production-us, Nodes: 12
2025-01-15 14:30:02,458 - INFO - Sending metrics: found=3, nodes_affected=2, dry_run=False
2025-01-15 14:30:02,789 - INFO - Metrics sent successfully: True
2025-01-15 14:30:02,790 - INFO - Command dangling completed successfully
```

### Error Example

```
2025-01-15 14:35:01,123 - INFO - Starting escmd command: dangling
2025-01-15 14:35:01,124 - INFO - Environment: prod
2025-01-15 14:35:01,456 - ERROR - Error retrieving dangling indices: Connection timeout
2025-01-15 14:35:01,457 - ERROR - Command dangling failed with error: Connection timeout
```

## Monitoring and Analysis

### View Latest Logs

```bash
# Follow the latest logs
tail -f logs/dangling_us_*.log

# View last 100 lines
tail -n 100 logs/dangling_us_20250115.log
```

### Search for Specific Information

```bash
# Find all errors
grep ERROR logs/*.log

# Find metrics operations
grep "Metrics sent" logs/*.log

# Find specific environment operations
grep "Environment: prod" logs/*.log

# Search for dangling indices found
grep "Found.*dangling indices" logs/*.log
```

### Log Analysis Commands

```bash
# Count errors by day
grep ERROR logs/*.log | cut -d' ' -f1 | sort | uniq -c

# Find most recent metrics results
grep "Metrics sent successfully" logs/dangling_*.log | tail -10

# Check for connection issues
grep -i "connection\|timeout\|refused" logs/*.log
```

## Troubleshooting

### Common Issues

1. **Logs Directory Not Created**
   - The logs directory is automatically created when logging is first used
   - Ensure escmd has write permissions to its installation directory

2. **Log Files Not Appearing**
   - Only specific commands (dangling, storage, etc.) create log files automatically
   - Commands like `version`, `help` don't generate logs by design

3. **Permission Errors**
   - Ensure the user running escmd has write access to the logs directory
   - Check filesystem permissions and disk space

### Environment Variables

You can control logging behavior with environment variables:

```bash
# Disable file logging entirely
export ESCMD_DISABLE_FILE_LOGGING=true

# Set default log level
export ESCMD_DEFAULT_LOG_LEVEL=DEBUG

# Custom logs directory
export ESCMD_LOGS_DIR=/custom/path/to/logs
```

## Integration with Monitoring Systems

### Log Shipping

You can easily integrate escmd logs with log shipping systems:

```bash
# Filebeat configuration example
filebeat.inputs:
- type: log
  paths:
    - /path/to/escmd/logs/*.log
  fields:
    application: escmd
    environment: production
```

### Alerting

Set up alerts based on log patterns:

```bash
# Alert on errors (example with simple monitoring script)
grep -q ERROR logs/dangling_prod_$(date +%Y%m%d).log && echo "ALERT: Errors found in escmd logs"

# Alert on failed metrics
grep -q "Metrics sent successfully: False" logs/*.log && echo "ALERT: Metrics delivery failed"
```

## Configuration

The logging system uses sensible defaults but can be customized by modifying the `logging_config.py` file:

- **File size limits**: Default 10MB, can be adjusted
- **Rotation count**: Default 5 files, can be modified  
- **Log format**: Can be customized for different outputs
- **Directory location**: Can be changed via configuration

For advanced configuration needs, edit the `LoggingConfig` class in `logging_config.py`.