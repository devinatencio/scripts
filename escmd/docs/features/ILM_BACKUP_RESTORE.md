# ILM Backup/Restore Feature - Summary

## Overview

New functionality has been added to escmd to support backing up, removing, and restoring ILM (Index Lifecycle Management) policies for Elasticsearch indices. This feature is useful for maintenance windows where you need to temporarily remove ILM policies and restore them later.

## What Was Added

### 1. New Commands

#### `ilm backup-policies`
Backs up ILM policies for a list of indices to a JSON file.

```bash
./escmd.py ilm backup-policies \
  --input-file indices.txt \
  --output-file backup.json
```

**Features:**
- Reads indices from a text file (one index per line) or JSON file
- Saves each index with its current ILM policy, phase, action, and step
- Continues processing even if some indices fail (errors recorded in output)
- Supports both table and JSON output formats

#### `ilm restore-policies`
Restores ILM policies from a backup JSON file.

```bash
./escmd.py ilm restore-policies \
  --input-file backup.json \
  [--dry-run]
```

**Features:**
- Reads backup JSON and applies policies to indices
- Skips indices that had no policy (unmanaged)
- Supports dry-run mode to preview changes
- Reports success/skip/error counts
- Continues processing all indices even if some fail

### 2. Enhanced Existing Commands

#### `ilm remove-policy`
Now supports both text files and JSON files (previously only JSON).

```bash
# Text file support (NEW)
./escmd.py ilm remove-policy --file indices.txt

# JSON file support (existing)
./escmd.py ilm remove-policy --file indices.json
```

#### `ilm set-policy`
Now supports both text files and JSON files (previously only JSON).

```bash
# Text file support (NEW)
./escmd.py ilm set-policy my-policy --file indices.txt

# JSON file support (existing)
./escmd.py ilm set-policy my-policy --file indices.json
```

## Input File Formats Supported

### Text File (Simple - One Index Per Line)
```
my-index-001
my-index-002
logs-2024.01.01
logs-2024.01.02
```

### JSON Array
```json
[
  "my-index-001",
  "my-index-002",
  "logs-2024.01.01"
]
```

### JSON Object
```json
{
  "indices": [
    "my-index-001",
    "my-index-002",
    "logs-2024.01.01"
  ]
}
```

## Complete Workflow Example

```bash
# Step 1: Create a list of indices for maintenance
cat > maintenance-indices.txt << EOF
logs-prod-2024.01.01
logs-prod-2024.01.02
metrics-prod-2024.01.01
EOF

# Step 2: Backup ILM policies
./escmd.py ilm backup-policies \
  --input-file maintenance-indices.txt \
  --output-file ilm-backup-20240115.json

# Step 3: Remove ILM policies (preview first)
./escmd.py ilm remove-policy --file maintenance-indices.txt --dry-run
./escmd.py ilm remove-policy --file maintenance-indices.txt --yes

# Step 4: Perform your maintenance operations
# ... (maintenance tasks) ...

# Step 5: Restore ILM policies (preview first)
./escmd.py ilm restore-policies --input-file ilm-backup-20240115.json --dry-run
./escmd.py ilm restore-policies --input-file ilm-backup-20240115.json

# Step 6: Verify
./escmd.py ilm errors
```

## Backup JSON Format

The backup file contains detailed information about each index:

```json
{
  "operation": "backup_policies",
  "timestamp": "2024-01-15T10:30:00.123456",
  "source_file": "maintenance-indices.txt",
  "indices": [
    {
      "index": "logs-prod-2024.01.01",
      "policy": "30-days-default",
      "managed": true,
      "phase": "hot",
      "action": "complete",
      "step": "complete"
    },
    {
      "index": "logs-prod-2024.01.02",
      "policy": "30-days-default",
      "managed": true,
      "phase": "warm",
      "action": "allocate",
      "step": "check-allocation"
    },
    {
      "index": "unmanaged-index",
      "policy": null,
      "managed": false,
      "phase": null,
      "action": null,
      "step": null
    }
  ]
}
```

## Files Modified/Created

### Modified Files:
1. **`escmd/handlers/lifecycle_handler.py`**
   - Added `_handle_ilm_backup_policies()` method
   - Added `_handle_ilm_restore_policies()` method
   - Added `_load_indices_from_file()` method (supports text and JSON)
   - Updated `_handle_ilm_remove_policy()` to use new file loader
   - Updated `_handle_ilm_set_policy()` to use new file loader
   - Updated `handle_ilm()` to route new commands
   - Updated `_show_ilm_help()` to include new commands
   - Added `from datetime import datetime` import

2. **`escmd/cli/argument_parser.py`**
   - Added `backup-policies` subcommand parser
   - Added `restore-policies` subcommand parser
   - Updated help text for `--file` argument in `remove-policy` and `set-policy`

3. **`escmd/docs/commands/ilm-management.md`**
   - Added backup-policies documentation section
   - Added restore-policies documentation section
   - Added complete backup/restore workflow examples
   - Updated quick reference with new commands

### Created Files:
1. **`escmd/examples/ilm/README.md`**
   - Comprehensive guide for backup/restore functionality
   - Workflow examples
   - Best practices
   - Troubleshooting guide
   - Automation examples

2. **`escmd/examples/ilm/sample-indices.txt`**
   - Example text file with indices

3. **`escmd/ILM_BACKUP_RESTORE_FEATURE.md`** (this file)
   - Summary of new functionality

## Command Reference

### backup-policies

```bash
./escmd.py ilm backup-policies \
  --input-file <file> \
  --output-file <file> \
  [--format json|table]
```

**Required Arguments:**
- `--input-file`: File with indices (one per line or JSON)
- `--output-file`: Output JSON file to save backup

**Optional Arguments:**
- `--format`: Output format for console (default: table)

### restore-policies

```bash
./escmd.py ilm restore-policies \
  --input-file <file> \
  [--dry-run] \
  [--format json|table]
```

**Required Arguments:**
- `--input-file`: Backup JSON file

**Optional Arguments:**
- `--dry-run`: Preview changes without executing
- `--format`: Output format for console (default: table)

## Error Handling

### Backup Command
- Continues processing all indices even if some fail
- Records errors in the backup JSON for failed indices
- Reports summary of success/error counts

### Restore Command
- Skips indices without policies (unmanaged)
- Continues processing even if some fail
- Reports detailed results for each index
- Shows summary with success/skip/error counts

## Use Cases

1. **Maintenance Windows**: Temporarily remove ILM policies during maintenance, restore afterward
2. **Policy Migration**: Backup current policies before migrating to new policy structure
3. **Disaster Recovery**: Keep backups of ILM configurations
4. **Testing**: Backup production policies, test changes, rollback if needed
5. **Compliance**: Document which indices had which policies at specific times
6. **Bulk Operations**: Easily manage ILM policies for many indices at once

## Testing the Feature

```bash
# Create test indices list
cat > test-indices.txt << EOF
.ds-logs-test-2024.01.01-000001
.ds-logs-test-2024.01.02-000001
EOF

# Test backup (should work even if indices don't exist - will show errors)
./escmd.py ilm backup-policies \
  --input-file test-indices.txt \
  --output-file test-backup.json

# Test restore dry-run
./escmd.py ilm restore-policies \
  --input-file test-backup.json \
  --dry-run

# Test remove with text file
./escmd.py ilm remove-policy --file test-indices.txt --dry-run

# Test set with text file
./escmd.py ilm set-policy my-policy --file test-indices.txt --dry-run
```

## Additional Resources

- **Examples**: See `examples/ilm/README.md` for detailed examples
- **Documentation**: See `docs/commands/ilm-management.md` for full ILM documentation
- **Sample Files**: See `examples/ilm/sample-indices.txt` for example input format

## Notes

- The feature maintains backward compatibility with existing JSON file formats
- Text file format is simpler and more convenient for most use cases
- Backup files include timestamps for tracking when backups were created
- All operations support dry-run mode for safe testing
- The implementation uses concurrent operations for better performance