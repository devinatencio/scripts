# Index Metadata Management

This feature allows you to add custom metadata to Elasticsearch indices and display it in the index details view.

## Overview

The index metadata feature provides:
- A command to add metadata to existing indices
- Display of metadata in the index details view
- Support for merging new metadata with existing metadata
- Proper error handling for invalid inputs

## Adding Metadata to an Index

### Command Syntax

```bash
./escmd.py indice-add-metadata <index_name> '<metadata_json>'
```

### Parameters

- `index_name`: The name of the index to add metadata to
- `metadata_json`: A JSON string containing the metadata to add

### Examples

#### Basic Usage

```bash
# Add metadata with _meta wrapper (recommended)
./escmd.py indice-add-metadata myindex-1 '{"_meta": {"timestamp": "2025-09-11T11:23:45", "user": "devin", "comment": "S3Snapshot Restored"}}'

# Add metadata directly (also supported)
./escmd.py indice-add-metadata myindex-1 '{"project": "backup-restore", "environment": "production", "team": "devops"}'
```

#### Common Use Cases

**Backup/Restore Tracking:**
```bash
./escmd.py indice-add-metadata restored-index '{"_meta": {"backup_source": "s3://my-backup-bucket", "restoration_date": "2025-12-15", "restored_by": "admin"}}'
```

**Project Management:**
```bash
./escmd.py indice-add-metadata logs-app '{"_meta": {"project": "web-analytics", "team": "data-engineering", "environment": "production"}}'
```

**Data Lineage:**
```bash
./escmd.py indice-add-metadata processed-data '{"_meta": {"source_system": "kafka", "processing_pipeline": "v2.1", "last_updated": "2025-09-11T10:30:00Z"}}'
```

## Viewing Metadata

When you display index details using the `indice` command, metadata will automatically appear in a dedicated panel:

```bash
./escmd.py indice myindex-1
```

### Display Layout

The index details view shows information in this order:
1. **Title Panel** - Index name and type
2. **Overview Panel** - Health, status, document count, etc.
3. **Settings Panel** - UUID, creation date, ILM policy, etc.
4. **📝 Metadata Panel** - Custom metadata (only shown if metadata exists)
5. **Shard Distribution Panels** - Totals, states, node distribution
6. **Detailed Shards Table** - Individual shard information

### Metadata Panel Features

- **JSON Syntax Highlighting**: Metadata is displayed with proper JSON formatting and colors
- **Conditional Display**: Panel only appears when metadata exists
- **Full Width**: Metadata panel spans the full width for better readability
- **Themed Styling**: Consistent with the overall application theme

## Metadata Merging

When adding metadata to an index that already has metadata:
- New fields are added to existing metadata
- Existing fields are updated with new values
- Nested objects are merged recursively
- Original metadata is preserved unless explicitly overwritten

### Example of Merging

**Existing metadata:**
```json
{
  "user": "admin",
  "timestamp": "2025-09-11T10:00:00"
}
```

**Adding new metadata:**
```bash
./escmd.py indice-add-metadata myindex '{"project": "analytics", "user": "devin"}'
```

**Result:**
```json
{
  "user": "devin",
  "timestamp": "2025-09-11T10:00:00",
  "project": "analytics"
}
```

## Technical Implementation

### Storage Method
- Metadata is stored in the Elasticsearch index mapping using the `_meta` field
- Uses the Elasticsearch PUT mapping API for updates
- Metadata persists with the index and survives cluster restarts

### Input Format Support
The command accepts two JSON formats:

1. **Wrapped format** (recommended):
   ```json
   {"_meta": {"key": "value"}}
   ```

2. **Direct format**:
   ```json
   {"key": "value"}
   ```

Both formats produce the same result in the index mapping.

## Error Handling

The command provides comprehensive error handling:

### Invalid JSON
```bash
./escmd.py indice-add-metadata myindex '{"invalid": json}'
```
Returns: JSON parse error with specific details

### Non-existent Index
```bash
./escmd.py indice-add-metadata non-existent '{"test": "value"}'
```
Returns: Index not found error

### Connection Issues
If Elasticsearch is unavailable, returns connection error with details

## Limitations

1. **Index Must Exist**: You cannot add metadata to non-existent indices
2. **Mapping Limitations**: Follows Elasticsearch mapping update restrictions
3. **Size Limits**: Subject to Elasticsearch mapping size limits
4. **Permissions**: Requires `manage` index privilege

## Best Practices

1. **Use Descriptive Keys**: Choose meaningful field names for metadata
   ```json
   {"backup_date": "2025-09-11", "source": "production"}
   ```

2. **Include Timestamps**: Always include when the metadata was added
   ```json
   {"timestamp": "2025-09-11T11:23:45Z", "operation": "restore"}
   ```

3. **Use Consistent Structure**: Maintain consistent metadata structure across indices
   ```json
   {
     "lifecycle": {
       "created": "2025-09-11T10:00:00Z",
       "last_modified": "2025-09-11T11:00:00Z"
     },
     "ownership": {
       "team": "data-eng",
       "contact": "admin@company.com"
     }
   }
   ```

4. **Document Your Schema**: Keep track of what metadata fields mean in your organization

## Getting Help

### Dedicated Help System

A comprehensive help system is available for the `indice-add-metadata` command:

```bash
# Get detailed help with examples and use cases
./escmd.py help indice-add-metadata

# Quick command syntax
./escmd.py indice-add-metadata --help
```

### Help Content Includes

- **Command Overview**: Purpose and storage mechanism
- **Syntax & Formats**: Both wrapped and direct JSON formats
- **Practical Examples**: Real-world use cases with proper JSON formatting
- **Use Cases & Workflows**: Detailed scenarios for different operational needs
- **Features & Behavior**: Information about merging, display, and validation

### Cross-Referenced Help

The metadata command is also referenced in related help topics:

```bash
# Index management help includes metadata examples
./escmd.py help indices

# General help lists metadata as available topic
./escmd.py help
```

## Integration with Other Features

- **Works with all index types**: Regular indices, data streams, system indices
- **Compatible with ILM**: Metadata persists through ILM phase transitions
- **Theme Support**: Metadata display follows the current theme settings
- **Export Friendly**: Metadata appears in JSON exports of index information
- **Help Integration**: Comprehensive help system with examples and workflows