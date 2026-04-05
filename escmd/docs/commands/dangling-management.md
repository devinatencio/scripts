# Enhanced Dangling Index Management Guide

## Overview

The `escmd.py dangling` command has been enhanced with advanced dangling index cleanup capabilities, including bulk operations, retry logic, dry-run functionality, and comprehensive logging.

## New Features

### 1. Bulk Cleanup Operations
- **Automatic cleanup**: Delete all dangling indices in a single operation
- **Progress tracking**: Real-time progress bars during bulk operations
- **Batch processing**: Efficient handling of multiple indices
- **Batch size control**: Process a specific number of indices per batch

### 2. Safety Features
- **Dry-run mode**: Preview operations without making changes
- **Confirmation prompts**: Require explicit confirmation for destructive operations
- **Pre-flight checks**: Validate cluster state before operations

### 3. Enhanced Reliability
- **Retry logic**: Automatic retry for transient failures
- **Error recovery**: Graceful handling of partial failures
- **Timeout management**: Configurable operation timeouts

### 4. Comprehensive Logging
- **Multi-destination logging**: Console and optional file logging
- **Structured output**: Detailed operation summaries
- **Error tracking**: Complete audit trail of operations

## Command Usage

### Basic Operations

#### List Dangling Indices
```bash
# Basic listing (unchanged)
./escmd.py --locations <cluster> dangling

# JSON format output
./escmd.py --locations <cluster> dangling --format json
```

#### Delete Single Index
```bash
# Interactive deletion (unchanged)
./escmd.py --locations <cluster> dangling <uuid> --delete

# Skip confirmation
./escmd.py --locations <cluster> dangling <uuid> --delete --yes-i-really-mean-it
```

### New Bulk Operations

#### Dry Run - Preview Changes
```bash
# See what would be deleted without making changes
./escmd.py --locations <cluster> dangling --cleanup-all --dry-run

# Dry run with custom retry settings
./escmd.py --locations <cluster> dangling --cleanup-all --dry-run --max-retries 5 --retry-delay 10
```

#### Cleanup All Dangling Indices
```bash
# Interactive cleanup (will prompt for confirmation)
./escmd.py --locations <cluster> dangling --cleanup-all

# Automatic cleanup (DANGEROUS - no prompts)
./escmd.py --locations <cluster> dangling --cleanup-all --yes-i-really-mean-it

# Cleanup with logging
./escmd.py --locations <cluster> dangling --cleanup-all --log-file /path/to/cleanup.log

# Batch processing - clean only 50 indices at a time
./escmd.py --locations <cluster> dangling --cleanup-all --batch 50

# Batch with dry-run to see what would be processed
./escmd.py --locations <cluster> dangling --cleanup-all --batch 100 --dry-run
```

### Advanced Configuration

#### Custom Retry Settings
```bash
# Custom retry and timeout settings
./escmd.py --locations <cluster> dangling --cleanup-all \\
  --max-retries 5 \\
  --retry-delay 10 \\
  --timeout 120
```

#### With Logging
```bash
# Enable detailed logging to file
./escmd.py --locations <cluster> dangling --cleanup-all \\
  --log-file /var/log/es-cleanup.log \\
  --max-retries 3

# Batch processing with custom settings
./escmd.py --locations <cluster> dangling --cleanup-all \\
  --batch 25 \\
  --max-retries 5 \\
  --retry-delay 10
```

## Configuration Settings

### Configuration File Settings

Add these settings to your `elastic_servers.yml`:

```yaml
settings:
  dangling_cleanup:
    max_retries: 3              # Default retry attempts
    retry_delay: 5              # Seconds between retries
    timeout: 60                 # Operation timeout
    default_log_level: INFO     # Logging level
    enable_progress_bar: true   # Show progress bars
    confirmation_required: true # Require confirmations
```

### Command Line Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--cleanup-all` | N/A | Delete all dangling indices |
| `--dry-run` | false | Preview operations without changes |
| `--max-retries` | 3 | Maximum retry attempts |
| `--retry-delay` | 5 | Seconds between retries |
| `--timeout` | 60 | Operation timeout in seconds |
| `--log-file` | None | Path to log file |
| `--batch` | None | Number of indices to process in this batch |
| `--yes-i-really-mean-it` | false | Skip confirmation prompts |
| `--format` | table | Output format (table or json) |

## Safety Guidelines

### Before Running Cleanup Operations

1. **Backup Important Data**
   ```bash
   # Create snapshots of important indices first
   ./escmd.py --locations <cluster> snapshots create-backup
   ```

2. **Verify Cluster Health**
   ```bash
   ./escmd.py --locations <cluster> health
   ```

3. **Review Dangling Indices**
   ```bash
   ./escmd.py --locations <cluster> dangling
   ```

4. **Test with Dry Run**
   ```bash
   ./escmd.py --locations <cluster> dangling --cleanup-all --dry-run
   ```

### Confirmation Process

When using `--cleanup-all` without `--yes-i-really-mean-it`:

1. **Index Summary**: Shows all indices to be deleted
2. **Warning Display**: Explains the destructive nature
3. **Explicit Confirmation**: Requires typing confirmation
4. **Progress Tracking**: Shows deletion progress
5. **Results Summary**: Reports success/failure statistics

## Error Handling

### Automatic Retry Logic

The system automatically handles:

- **Timeout exceptions**: Cluster event processing timeouts
- **Network issues**: Transient connection problems
- **Resource conflicts**: Temporary resource unavailability
- **Rate limiting**: API rate limit responses

### Error Recovery Strategies

1. **Incremental Backoff**: Increasing delay between retries
2. **Partial Success Handling**: Continue processing remaining indices
3. **Detailed Error Reporting**: Specific error messages and suggested actions
4. **Graceful Degradation**: Fallback to simpler operations when needed

### Common Error Scenarios

#### Index Already Gone
```
WARNING: Dangling index 'abc-123' was already cleaned up - skipping
```
**Action**: Continue processing (considered successful)

#### Timeout During Deletion
```
WARNING: Timeout deleting dangling index 'def-456' - may complete in background
```
**Action**: Marked as partial success, monitor cluster

#### Connection Issues
```
ERROR: Error deleting dangling index 'ghi-789' after 3 attempts: Connection timeout
```
**Action**: Manual intervention required

## Output Examples

### Dry Run Output
```
🧪 DRY RUN: Would Delete 3 Dangling Indices
┌──────────────────────────────────────┬──────────────────────┬────────────┐
│ Index UUID                           │ Creation Date        │ Node Count │
├──────────────────────────────────────┼──────────────────────┼────────────┤
│ a1b2c3d4-e5f6-7890-abcd-ef1234567890 │ 2025-08-15T10:30:25Z │ 2          │
│ b2c3d4e5-f6g7-8901-bcde-f23456789012 │ 2025-08-14T15:22:10Z │ 1          │
│ c3d4e5f6-g7h8-9012-cdef-345678901234 │ 2025-08-13T09:15:30Z │ 3          │
└──────────────────────────────────────┴──────────────────────┴────────────┘

⚠️ WARNING: This would PERMANENTLY DELETE all dangling indices!
```

### Cleanup Progress
```
🗑️ Deleting dangling indices...
██████████████████████████████████████████████████ 100% 3/3 [00:15<00:00]
```

### Results Summary
```
✅ Cleanup Completed Successfully
┌─────────────────┬───────┐
│ Total Processed │ 3     │
│ Successful      │ 3     │
│ Failed          │ 0     │
│ Duration        │ 00:15 │
└─────────────────┴───────┘
```

## Best Practices

### 1. Always Start with Dry Run
```bash
./escmd.py --locations prod dangling --cleanup-all --dry-run
```

### 2. Use Logging for Production
```bash
./escmd.py --locations prod dangling --cleanup-all \\
  --log-file /var/log/es-cleanup-$(date +%Y%m%d).log
```

### 3. Conservative Retry Settings
```bash
./escmd.py --locations prod dangling --cleanup-all \\
  --max-retries 5 --retry-delay 10 --timeout 120
```

### 4. Monitor Cluster During Operations
- Watch cluster health in another terminal
- Monitor node resource usage
- Check for any alerts or warnings

### 4. Document Operations
- Keep logs of all cleanup operations
- Record reasons for dangling indices
- Track patterns for prevention

### 5. Use Batch Processing for Large Cleanups
```bash
# For clusters with many dangling indices, process in batches
./escmd.py --locations prod dangling --cleanup-all --batch 50 --dry-run
# Then process the actual batch
./escmd.py --locations prod dangling --cleanup-all --batch 50
```

## Troubleshooting

### Common Issues

1. **Permission Errors**
   - Verify user has cluster admin privileges
   - Check authentication configuration

2. **Network Timeouts**
   - Increase timeout values
   - Check cluster load
   - Verify network connectivity

3. **Partial Failures**
   - Review error logs
   - Re-run for failed indices only
   - Consider manual intervention

4. **Configuration Issues**
   - Validate YAML syntax
   - Check server definitions
   - Verify password references

## Migration from Standalone Script

If migrating from the standalone `dangling_index_cleanup.py`:

### Command Mapping

| Old Command | New Command |
|-------------|-------------|
| `python3 dangling_index_cleanup.py -c config.yml -s server` | `./escmd.py --locations server dangling` |
| `python3 dangling_index_cleanup.py --dry-run` | `./escmd.py --locations server dangling --cleanup-all --dry-run` |
| `python3 dangling_index_cleanup.py --server prod` | `./escmd.py --locations prod dangling --cleanup-all` |

### Configuration Migration

1. **Server Settings**: Already compatible with `elastic_servers.yml`
2. **Password Management**: Already integrated
3. **Logging**: Enhanced with rich output formatting
4. **Error Handling**: Improved with better recovery

## Batch Processing

### Overview
The `--batch` parameter allows you to process dangling indices in smaller groups, which is especially useful for clusters with large numbers of dangling indices.

### Use Cases

#### Large Scale Cleanup
For clusters like `iad51` with 1,014 dangling indices:
```bash
# Process 100 indices at a time
./escmd.py --locations iad51 dangling --cleanup-all --batch 100 --dry-run
```

#### Gradual Cleanup
```bash
# Clean 50 indices, monitor cluster, then continue
./escmd.py --locations iad51 dangling --cleanup-all --batch 50
```

#### Resource Management
```bash
# Small batches during peak hours to minimize cluster impact
./escmd.py --locations prod dangling --cleanup-all --batch 25
```

### Batch Behavior
- Processes the **first** N indices found (sorted by UUID)
- Shows progress as "batch X/total"
- Remaining indices can be processed in subsequent runs
- Each batch operation is independent

### Example Workflow
```bash
# 1. Check total dangling indices
./escmd.py --locations iad51 dangling
# Output: Found 1,014 dangling indices

# 2. Process first batch of 100 (dry run)
./escmd.py --locations iad51 dangling --cleanup-all --batch 100 --dry-run

# 3. Process first batch of 100 (actual)
./escmd.py --locations iad51 dangling --cleanup-all --batch 100

# 4. Check remaining count
./escmd.py --locations iad51 dangling
# Output: Found 914 dangling indices

# 5. Continue with next batch
./escmd.py --locations iad51 dangling --cleanup-all --batch 100
```

## Integration Notes

- **Backward Compatibility**: All existing `dangling` functionality preserved
- **Configuration**: Uses existing `elastic_servers.yml` format
- **Authentication**: Leverages existing password management
- **Output**: Enhanced with Rich formatting library
- **Error Handling**: Comprehensive retry and recovery logic
- **Batch Processing**: New feature for large-scale operations
