# Repository Verification Feature

## Overview

The Repository Verification feature provides a dedicated command to test snapshot repository connectivity across all nodes in an Elasticsearch cluster. This proactive testing capability helps identify repository access issues before they cause backup failures.

## Command Syntax

```bash
./escmd.py repositories verify <repository_name> [--format {table,json}]
```

## Key Features

### 🔍 **Multi-Node Verification**
- Tests repository accessibility from every node in the cluster
- Ensures all nodes can successfully connect to the repository
- Identifies potential network, permission, or configuration issues

### 📊 **Enhanced Display**
- **Alphabetical Sorting**: Nodes displayed in alphabetical order for easy scanning
- **Rich Table Format**: Clean, organized display with node names, IDs, and status
- **JSON Output**: Machine-readable format for automation and monitoring
- **Status Indicators**: Clear visual feedback with checkmarks and colors

### 🎯 **Professional Output**
```
✓ Repository Verification Results
┌────────────────────────┬────────────────────────┬────────────┐
│ Node Name              │ Node ID                │   Status   │
├────────────────────────┼────────────────────────┼────────────┤
│ es-master-01           │ ABC123...              │ ✓ Verified │
│ es-master-02           │ DEF456...              │ ✓ Verified │
│ es-data-01             │ GHI789...              │ ✓ Verified │
│ es-data-02             │ JKL012...              │ ✓ Verified │
└────────────────────────┴────────────────────────┴────────────┘

Summary: Repository 's3_repo' successfully verified on all 4 nodes
```

## Usage Examples

### Basic Verification
```bash
# Verify S3 repository
./escmd.py repositories verify s3_repo

# Verify filesystem repository  
./escmd.py repositories verify fs_backup_repo

# Verify with specific cluster
./escmd.py -l production repositories verify backup-repo
```

### JSON Output for Automation
```bash
# Get JSON results for monitoring systems
./escmd.py repositories verify s3_repo --format json

# Example JSON output
{
  "nodes": {
    "rFMpDktVTpiyKjTpDQiatg": {"name": "es-master-01"},
    "mo_qkfqyRuOj4qCWx1z2GQ": {"name": "es-master-02"},
    "B2Eo0qPCQkCX8QZwv0T-tg": {"name": "es-data-01"}
  }
}
```

### Integration with Monitoring
```bash
#!/bin/bash
# Monitor repository health
REPO_STATUS=$(./escmd.py repositories verify s3_repo --format json)
NODE_COUNT=$(echo "$REPO_STATUS" | jq '.nodes | length')

if [ "$NODE_COUNT" -eq 0 ]; then
    echo "CRITICAL: Repository verification failed"
    exit 2
else
    echo "OK: Repository verified on $NODE_COUNT nodes"
    exit 0
fi
```

## Technical Implementation

### REST API Integration
- Uses Elasticsearch's `POST _snapshot/<repo_name>/_verify` endpoint
- Returns list of nodes that successfully accessed the repository
- Handles API response format differences across Elasticsearch versions

### Error Handling
- **Missing Repository**: Clear error message for non-existent repositories
- **Connection Issues**: Network and authentication error reporting
- **Partial Failures**: Detailed reporting when some nodes fail verification

### Node Sorting Algorithm
```python
# Nodes sorted alphabetically by name for consistent, readable output
sorted_nodes = sorted(
    nodes.items(), 
    key=lambda item: item[1].get("name", "Unknown")
)
```

## Operational Benefits

### Pre-Backup Validation
- **Proactive Testing**: Identify issues before backup operations
- **Cluster-Wide Coverage**: Ensure all nodes can access repository
- **Early Warning System**: Prevent backup failures before they occur

### Troubleshooting Support
- **Clear Diagnostics**: Visual indication of which nodes have issues
- **Node-Level Detail**: Specific information about connectivity problems  
- **Consistent Output**: Reliable format for scripts and automation

### Monitoring Integration
- **JSON Format**: Perfect for monitoring systems (Nagios, Prometheus, etc.)
- **Exit Codes**: Standard success/failure codes for shell scripts
- **Log-Friendly**: Clean output suitable for log aggregation

## Integration Workflows

### Daily Repository Health Check
```bash
#!/bin/bash
# Daily repository verification script
for repo in $(./escmd.py repositories list --format json | jq -r 'keys[]'); do
    echo "Verifying repository: $repo"
    if ./escmd.py repositories verify "$repo" > /dev/null 2>&1; then
        echo "✅ $repo: OK"
    else
        echo "❌ $repo: FAILED"
        # Send alert to monitoring system
        curl -X POST "$ALERT_WEBHOOK" -d "repo=$repo&status=failed"
    fi
done
```

### Pre-Snapshot Validation
```bash
#!/bin/bash
# Validate repository before creating snapshot
REPO_NAME="s3_backup"

echo "Verifying repository connectivity..."
if ./escmd.py repositories verify "$REPO_NAME"; then
    echo "Repository verified, creating snapshot..."
    ./escmd.py snapshots create "daily-backup-$(date +%Y%m%d)"
else
    echo "Repository verification failed, aborting snapshot"
    exit 1
fi
```

### Automated Monitoring
```bash
#!/bin/bash
# Nagios/Icinga monitoring check
REPO_NAME="$1"
RESULT=$(./escmd.py repositories verify "$REPO_NAME" --format json 2>&1)

if echo "$RESULT" | jq -e '.nodes | length > 0' > /dev/null 2>&1; then
    NODE_COUNT=$(echo "$RESULT" | jq '.nodes | length')
    echo "OK - Repository '$REPO_NAME' verified on $NODE_COUNT nodes"
    exit 0
else
    echo "CRITICAL - Repository '$REPO_NAME' verification failed"
    exit 2
fi
```

## Best Practices

### Regular Verification Schedule
- **Daily Checks**: Automated verification of critical repositories
- **Pre-Backup**: Always verify before important backup operations  
- **Post-Configuration**: Test after repository configuration changes
- **Cluster Changes**: Verify when adding/removing nodes

### Monitoring Integration
- **Threshold Alerts**: Alert when verification fails on any node
- **Trend Monitoring**: Track verification success rates over time
- **Dashboard Integration**: Include repository health in monitoring dashboards
- **SLA Compliance**: Use for backup SLA monitoring and reporting

### Troubleshooting Workflow
1. **Verify Repository**: Use `repositories verify` to test connectivity
2. **Check Configuration**: Review repository settings with `repositories list --format json`
3. **Network Testing**: Verify network access to repository location
4. **Permission Validation**: Confirm authentication and access permissions
5. **Node-Specific Issues**: Identify which specific nodes have problems

## Error Scenarios and Solutions

### Repository Not Found
```bash
./escmd.py repositories verify nonexistent_repo
# Error: Failed to verify repository: NotFoundError(404, 'repository_missing_exception', '[nonexistent_repo] missing')
```
**Solution**: Check repository name spelling and ensure repository exists

### Network Connectivity Issues
```bash
./escmd.py repositories verify s3_repo
# Error: Failed to verify repository: ConnectionError(...)
```
**Solution**: Verify network access, firewall rules, and repository endpoint

### Permission Problems
```bash
./escmd.py repositories verify s3_repo
# Shows some nodes successful, others failed
```
**Solution**: Check IAM permissions, access keys, and security group rules

## Command Reference

### Basic Commands
| Command | Description | Example |
|---------|-------------|---------|
| `repositories verify <repo>` | Verify repository connectivity | `repositories verify s3_repo` |
| `repositories verify <repo> --format json` | Get JSON output | `repositories verify s3_repo --format json` |
| `repositories list` | List all repositories | `repositories list` |
| `repositories help` | Show help information | `repositories --help` |

### Advanced Usage
| Pattern | Description | Example |
|---------|-------------|---------|
| Cluster-specific | Verify on specific cluster | `./escmd.py -l prod repositories verify backup` |
| Automation-ready | JSON output for scripts | `./escmd.py repositories verify repo --format json \| jq '.nodes'` |
| Error checking | Shell script error handling | `if ./escmd.py repositories verify repo; then echo "OK"; fi` |

## Related Commands

- [`repositories list`](../commands/snapshot-management.md#repository-management) - List all configured repositories
- [`repositories create`](../commands/snapshot-management.md#repository-management) - Create new repositories
- [`snapshots list`](../commands/snapshot-management.md#list-snapshots) - List snapshots in repositories
- [`health`](../commands/health-monitoring.md) - Overall cluster health including backup status

## Version History

- **v3.6.0**: Initial release with full verification functionality
- **v3.6.0**: Added alphabetical node sorting for improved readability
- **v3.6.0**: Comprehensive documentation and example scripts