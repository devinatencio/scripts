# Quick Start: ILM Backup & Restore

This guide will get you started with the new ILM policy backup and restore functionality in 5 minutes.

## What You Need

1. A text file with your indices (one per line)
2. The escmd tool configured for your Elasticsearch cluster

## 3-Step Workflow

### Step 1: Backup ILM Policies

Create a file with your indices:

```bash
cat > my-indices.txt << EOF
logs-prod-2024.01.01
logs-prod-2024.01.02
metrics-prod-2024.01.01
EOF
```

Backup the policies:

```bash
./escmd.py ilm backup-policies \
  --input-file my-indices.txt \
  --output-file ilm-backup.json
```

**Output:**
```
✅ Successfully backed up: 3 indices
📁 Backup saved to: ilm-backup.json
```

### Step 2: Remove ILM Policies (Optional)

If you need to remove policies temporarily:

```bash
# Preview first
./escmd.py ilm remove-policy --file my-indices.txt --dry-run

# Actually remove
./escmd.py ilm remove-policy --file my-indices.txt --yes
```

### Step 3: Restore ILM Policies

When ready to restore:

```bash
# Preview first
./escmd.py ilm restore-policies --input-file ilm-backup.json --dry-run

# Actually restore
./escmd.py ilm restore-policies --input-file ilm-backup.json
```

**Output:**
```
✅ Successfully restored: 3 policies
📊 Total indices processed: 3
```

## That's It!

You now know how to:
- ✅ Backup ILM policies for specific indices
- ✅ Remove ILM policies when needed
- ✅ Restore ILM policies from backup

## Common Use Cases

### Maintenance Window
```bash
# Before maintenance
./escmd.py ilm backup-policies --input-file indices.txt --output-file backup.json
./escmd.py ilm remove-policy --file indices.txt --yes

# ... perform maintenance ...

# After maintenance
./escmd.py ilm restore-policies --input-file backup.json
```

### One-Liner for Daily Backups
```bash
# Backup with timestamp
./escmd.py ilm backup-policies \
  --input-file production-indices.txt \
  --output-file "ilm-backup-$(date +%Y%m%d-%H%M%S).json"
```

### Pattern-Based Removal (No File Needed)
```bash
# Remove policies by pattern
./escmd.py ilm remove-policy "temp-*" --dry-run
./escmd.py ilm remove-policy "temp-*" --yes
```

## Input File Formats

The `--input-file` for backup supports three formats:

**Text (Simplest):**
```
index-1
index-2
index-3
```

**JSON Array:**
```json
["index-1", "index-2", "index-3"]
```

**JSON Object:**
```json
{
  "indices": ["index-1", "index-2", "index-3"]
}
```

## Pro Tips

1. **Always use --dry-run first** to preview changes
2. **Include timestamps** in backup filenames: `backup-$(date +%Y%m%d).json`
3. **Keep backups** - they're small and useful for audit trails
4. **Verify after restore** with `./escmd.py ilm errors`

## What's in the Backup File?

The backup JSON contains:
- Timestamp of when backup was created
- Each index name
- Its ILM policy (if any)
- Current phase, action, and step
- Management status

Example:
```json
{
  "operation": "backup_policies",
  "timestamp": "2024-01-15T10:30:00.123456",
  "source_file": "my-indices.txt",
  "indices": [
    {
      "index": "logs-prod-2024.01.01",
      "policy": "30-days-default",
      "managed": true,
      "phase": "hot",
      "action": "complete",
      "step": "complete"
    }
  ]
}
```

## Need More Help?

- **Detailed Examples**: See `examples/ilm/README.md`
- **Full Documentation**: See `docs/commands/ilm-management.md`
- **Feature Summary**: See `ILM_BACKUP_RESTORE_FEATURE.md`

## Quick Reference Card

```bash
# Backup
./escmd.py ilm backup-policies --input-file <in> --output-file <out>

# Restore
./escmd.py ilm restore-policies --input-file <backup> [--dry-run]

# Remove (pattern)
./escmd.py ilm remove-policy "<pattern>" [--dry-run] [--yes]

# Remove (file)
./escmd.py ilm remove-policy --file <file> [--dry-run] [--yes]

# Set (pattern)
./escmd.py ilm set-policy <policy> "<pattern>" [--dry-run] [--yes]

# Set (file)
./escmd.py ilm set-policy <policy> --file <file> [--dry-run] [--yes]

# Check for errors
./escmd.py ilm errors
```

---

**Happy ILM Managing! 🚀**