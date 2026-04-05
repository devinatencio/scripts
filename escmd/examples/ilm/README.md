# ILM Policy Backup and Restore

This directory contains examples and documentation for the ILM (Index Lifecycle Management) policy backup and restore functionality in escmd.

## Overview

The ILM backup/restore feature allows you to:
1. **Backup** ILM policies for a list of indices to a JSON file
2. **Remove** ILM policies from indices (using the backup as a reference)
3. **Restore** ILM policies from the backup JSON file

This is useful when you need to temporarily remove ILM policies from indices (e.g., during maintenance) and restore them later.

## Workflow

### 1. Backup ILM Policies

First, create a text file with the indices you want to backup (one index per line):

```bash
# Create indices list
cat > my-indices.txt << EOF
my-index-001
my-index-002
logs-2024.01.01
logs-2024.01.02
EOF
```

Then backup the ILM policies:

```bash
./escmd.py ilm backup-policies \
  --input-file my-indices.txt \
  --output-file ilm-backup.json
```

**Output:** Creates a JSON file containing each index and its current ILM policy:

```json
{
  "operation": "backup_policies",
  "timestamp": "2024-01-15T10:30:00.123456",
  "source_file": "my-indices.txt",
  "indices": [
    {
      "index": "my-index-001",
      "policy": "30-days-default",
      "managed": true,
      "phase": "hot",
      "action": "complete",
      "step": "complete"
    },
    {
      "index": "my-index-002",
      "policy": "logs-policy",
      "managed": true,
      "phase": "warm",
      "action": "allocate",
      "step": "check-allocation"
    }
  ]
}
```

### 2. Remove ILM Policies

Remove ILM policies from the indices using the text file:

```bash
# Preview what would be removed (dry run)
./escmd.py ilm remove-policy \
  --file my-indices.txt \
  --dry-run

# Actually remove the policies
./escmd.py ilm remove-policy \
  --file my-indices.txt \
  --yes
```

You can also remove policies by pattern:

```bash
./escmd.py ilm remove-policy "logs-2024.*" --yes
```

### 3. Restore ILM Policies

After maintenance is complete, restore the policies from the backup:

```bash
# Preview what would be restored (dry run)
./escmd.py ilm restore-policies \
  --input-file ilm-backup.json \
  --dry-run

# Actually restore the policies
./escmd.py ilm restore-policies \
  --input-file ilm-backup.json
```

## Input File Formats

### Text File (Simple)
One index name per line:
```
my-index-001
my-index-002
logs-2024.01.01
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

## Commands Reference

### backup-policies

Backup ILM policies for indices listed in a file.

```bash
./escmd.py ilm backup-policies \
  --input-file <input-file> \
  --output-file <output-file> \
  [--format json|table]
```

**Options:**
- `--input-file`: File containing list of indices (one per line or JSON format) - **Required**
- `--output-file`: Output JSON file to save the backup - **Required**
- `--format`: Output format for console display (default: table)

### restore-policies

Restore ILM policies from a backup JSON file.

```bash
./escmd.py ilm restore-policies \
  --input-file <backup-file> \
  [--dry-run] \
  [--format json|table]
```

**Options:**
- `--input-file`: Backup JSON file containing indices and their policies - **Required**
- `--dry-run`: Preview changes without executing
- `--format`: Output format (default: table)

### remove-policy

Remove ILM policies from indices (supports pattern or file).

```bash
# Using pattern
./escmd.py ilm remove-policy <pattern> [options]

# Using file
./escmd.py ilm remove-policy --file <file> [options]
```

**Options:**
- `--file`: File containing list of indices (one per line or JSON format)
- `--dry-run`: Preview changes without executing
- `--yes`: Skip confirmation prompts
- `--max-concurrent`: Maximum concurrent operations (default: 5)
- `--format`: Output format (default: table)

### set-policy

Set ILM policy for indices (supports pattern or file).

```bash
# Using pattern
./escmd.py ilm set-policy <policy-name> <pattern> [options]

# Using file
./escmd.py ilm set-policy <policy-name> --file <file> [options]
```

**Options:**
- `--file`: File containing list of indices (one per line or JSON format)
- `--dry-run`: Preview changes without executing
- `--yes`: Skip confirmation prompts
- `--max-concurrent`: Maximum concurrent operations (default: 5)
- `--format`: Output format (default: table)

## Complete Example

Here's a complete workflow for temporarily removing and restoring ILM policies:

```bash
# Step 1: Create indices list
cat > maintenance-indices.txt << EOF
logs-prod-2024.01.01
logs-prod-2024.01.02
logs-prod-2024.01.03
metrics-prod-2024.01.01
EOF

# Step 2: Backup current ILM policies
./escmd.py ilm backup-policies \
  --input-file maintenance-indices.txt \
  --output-file ilm-backup-$(date +%Y%m%d).json

# Step 3: Remove ILM policies (with preview)
./escmd.py ilm remove-policy \
  --file maintenance-indices.txt \
  --dry-run

# Step 4: Actually remove policies
./escmd.py ilm remove-policy \
  --file maintenance-indices.txt \
  --yes

# ... Perform maintenance tasks ...

# Step 5: Restore ILM policies (with preview)
./escmd.py ilm restore-policies \
  --input-file ilm-backup-$(date +%Y%m%d).json \
  --dry-run

# Step 6: Actually restore policies
./escmd.py ilm restore-policies \
  --input-file ilm-backup-$(date +%Y%m%d).json
```

## Error Handling

The backup command will continue processing even if some indices fail. The output JSON will include error information:

```json
{
  "index": "missing-index-001",
  "policy": null,
  "managed": false,
  "error": "index_not_found_exception"
}
```

The restore command will skip indices that have no policy in the backup:

```
⏭️  Skipped (no policy): 3 indices
```

## Best Practices

1. **Always use --dry-run first** to preview changes before applying them
2. **Keep backup files** - Name them with timestamps for easy tracking
3. **Verify backups** - Check the JSON output to ensure policies were captured correctly
4. **Test on non-production** - Test the workflow on development/staging first
5. **Use patterns carefully** - Regex patterns can match more indices than intended
6. **Document maintenance windows** - Keep backup files as documentation of when policies were changed

## Automation Example

Create a script for scheduled maintenance:

```bash
#!/bin/bash
set -e

INDICES_FILE="$1"
BACKUP_DIR="./ilm-backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/ilm-backup-${TIMESTAMP}.json"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Backup policies
echo "Backing up ILM policies..."
./escmd.py ilm backup-policies \
  --input-file "${INDICES_FILE}" \
  --output-file "${BACKUP_FILE}" \
  --format json

# Remove policies
echo "Removing ILM policies..."
./escmd.py ilm remove-policy \
  --file "${INDICES_FILE}" \
  --yes \
  --format json

# Store backup file path for later restoration
echo "${BACKUP_FILE}" > "${BACKUP_DIR}/last-backup.txt"
echo "Backup saved to: ${BACKUP_FILE}"
```

## Troubleshooting

**Q: The backup file shows "managed": false for some indices**
- A: These indices don't have an ILM policy assigned. They will be skipped during restore.

**Q: Restore fails with "policy not found"**
- A: The ILM policy from the backup doesn't exist on the cluster. Create the policy first or check for typos.

**Q: Can I edit the backup JSON manually?**
- A: Yes, you can modify the JSON to change which policies are restored or remove indices from restoration.

**Q: What happens if I restore to a different cluster?**
- A: The restore will work if the policies exist on the target cluster. If not, you'll get errors for missing policies.

## See Also

- [ILM Management Documentation](../../docs/commands/ilm-management.md)
- [Index Operations](../../docs/commands/index-operations.md)
- Main README: [../../README.md](../../README.md)