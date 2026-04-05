# ILM S3-Snapshot Integration Documentation

## Overview

The cluster-check command now integrates with the custom S3-Snapshot ILM utility to provide better visibility into index management. Instead of showing all unmanaged indices as "No ILM policy attached", the system now distinguishes between truly unmanaged indices and those managed by the custom S3-Snapshot utility.

## Features

### Enhanced ILM Issues Display

The ILM Issues section now displays information in **three separate tables** for better clarity:

1. **❌ ILM Errors** - Indices with actual ILM errors
2. **⚠️ Unmanaged Indices** - Indices with no ILM policy and not managed by S3-Snapshot
3. **✅ S3-Managed Indices** - Indices managed by the custom S3-Snapshot utility

### Updated Counts

- **Managed Count**: Now includes both native ILM-managed indices AND S3-Snapshot managed indices
- **Unmanaged Count**: Only includes truly unmanaged indices (excludes S3-managed ones)
- **Summary Status**: Reflects the proper categorization of indices

## How It Works

### Detection Logic

The system determines if an index is managed by the S3-Snapshot utility through two methods:

1. **System Indices**: Automatically recognizes core S3-Snapshot system indices:
   - `rc_snapshots`
   - `rc_snapshots_ilm`
   - `rc_snapshots_ilm_failed`
   - `rc_snapshots_history`

2. **Restored Indices**: Queries the `rc_snapshots` index (configurable via `restored_snapshots_index` setting) for documents with `index_name` matching the index in question

**Optimization**: All indices from `rc_snapshots` are cached in memory during the check to avoid repeated queries, improving performance when checking multiple indices.

If an index is found via either method, it's marked as "S3-Snapshot managed", otherwise "No ILM policy attached".

### Configuration

The system uses the `restored_snapshots_index` setting from your configuration:

```yaml
settings:
  restored_snapshots_index: rc_snapshots  # Default
```

## Example Output

### Before (Single Mixed Table)
```
🔍 ILM Issues (0 errors, 15 unmanaged)
┌─────────────────────┬─────────────────────────┬────────┬───────┬────────┐
│ Index               │ Issue                   │ Policy │ Phase │ Action │
├─────────────────────┼─────────────────────────┼────────┼───────┼────────┤
│ restored-logs-001   │ ⚠️  No ILM policy      │   -    │   -   │   -    │
│ restored-logs-002   │ ⚠️  S3-Snapshot managed│   -    │   -   │   -    │
│ temp-index-001      │ ⚠️  No ILM policy      │   -    │   -   │   -    │
└─────────────────────┴─────────────────────────┴────────┴───────┴────────┘
```

### After (Separate Tables)
```
📋 Summary
🔍 ILM Status: ⚠️ 2 indices unmanaged, ✅ 1 S3-managed

⚠️ Unmanaged Indices (2 indices)
┌─────────────────────┬─────────────────────────┐
│ Index               │ Status                  │
├─────────────────────┼─────────────────────────┤
│ restored-logs-001   │ No ILM policy attached  │
│ temp-index-001      │ No ILM policy attached  │
└─────────────────────┴─────────────────────────┘

✅ S3-Managed Indices (5 indices) - alphabetically sorted
┌─────────────────────┬─────────────────────────┐
│ Index               │ Management              │
├─────────────────────┼─────────────────────────┤
│ rc_snapshots        │ S3-Snapshot managed     │
│ rc_snapshots_history│ S3-Snapshot managed     │
│ rc_snapshots_ilm    │ S3-Snapshot managed     │
│ restored-logs-002   │ S3-Snapshot managed     │
│ ...                 │ 1 more S3-managed       │
└─────────────────────┴─────────────────────────┘
```

## Commands

### Basic Usage
```bash
# Run cluster check with new ILM display
./escmd.py cluster-check

# Show detailed information (bypasses display limits)
./escmd.py cluster-check --show-details

# JSON output (includes categorization)
./escmd.py cluster-check --format json
```

### Configuration Options
```bash
# Set custom ILM display limit
./escmd.py cluster-check --ilm-limit 50

# Skip ILM checks entirely
./escmd.py cluster-check --skip-ilm
```

## Benefits

### Operational Clarity
- **Reduced Noise**: S3-managed indices no longer appear as "unmanaged"
- **Better Visibility**: Clear distinction between different management types
- **Accurate Counts**: Proper categorization in summary statistics

### Decision Making
- **Focus on Issues**: Quickly identify truly unmanaged indices that need attention
- **Confidence**: Know which indices are properly managed by your S3 utility
- **Compliance**: Better understanding of your index management coverage

## Technical Implementation

### Files Modified
- `escmd/commands/ilm_commands.py` - Added caching system and S3 management detection
- `escmd/handlers/health_handler.py` - Updated display logic with separate tables

### Key Methods Added
- `_get_rc_snapshots_indices_cache()` - Efficient caching of all rc_snapshots indices
- `_is_index_managed_by_s3()` - Comprehensive S3 management detection
- `_clear_rc_snapshots_cache()` - Cache cleanup after checks

### Error Handling
- Gracefully handles missing `rc_snapshots` index
- Falls back to standard behavior if queries fail
- No impact on existing functionality if S3 utility is not in use

### Performance
- **Single Query Optimization**: All rc_snapshots indices cached in one query per check
- **System Index Recognition**: Instant identification of core S3-Snapshot indices
- **Memory Efficient**: Cache automatically cleared after each check
- **Alphabetical Sorting**: Efficient in-memory sorting for better readability
- **Minimal Overhead**: Significant performance improvement over per-index queries

## Troubleshooting

### Common Issues

**Q: S3-managed indices still show as "No ILM policy attached"**
A: Check that:
- The `rc_snapshots` index exists and is accessible
- Documents in `rc_snapshots` have an `index_name` field
- The field contains the exact index names

**Q: Getting connection errors to rc_snapshots index**
A: Verify:
- Index permissions allow read access
- The `restored_snapshots_index` configuration is correct
- The Elasticsearch cluster is accessible

**Q: Performance impact during cluster-check**
A: The optimized system makes only one query to rc_snapshots per check (cached for all indices). Performance improvements include:
- Single bulk query replaces multiple individual queries
- System indices recognized instantly without queries
- Cache cleared after each check to ensure fresh data
- If performance is still a concern, use `--skip-ilm` to bypass ILM checks entirely

### Debug Commands
```bash
# Test ILM functionality specifically
./escmd.py ilm status

# Check if rc_snapshots index exists
./escmd.py indices | grep rc_snapshots

# View rc_snapshots structure
./escmd.py snapshots list-restored
```

## Migration Notes

### Backward Compatibility
- Existing configurations continue to work unchanged
- Old display format available if S3 integration is not detected
- No breaking changes to command-line interfaces

### Upgrade Path
1. Update to the new version
2. Verify `restored_snapshots_index` configuration
3. Run `./escmd.py cluster-check` to see new display
4. Adjust `ilm_limit` settings if needed

---

*This feature enhances the cluster-check command to provide better visibility into your complete index management strategy, including both native Elasticsearch ILM and custom S3-Snapshot utilities.*