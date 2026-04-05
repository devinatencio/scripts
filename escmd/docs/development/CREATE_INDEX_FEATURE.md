# Create Index Feature Documentation

## Overview

The `create-index` command allows you to easily create new empty Elasticsearch indices with customizable settings and mappings. This feature is fully integrated into both the direct `escmd.py` command-line interface and the interactive `esterm` terminal.

## Features

- ✅ Create empty indices with default settings (1 shard, 1 replica)
- ✅ Customize primary shard and replica counts
- ✅ Add custom index settings via JSON
- ✅ Add custom index mappings via JSON
- ✅ Automatic cache refresh after creation (shows immediately in `indices` command)
- ✅ Rich console output with progress feedback
- ✅ JSON and table output formats
- ✅ Comprehensive error handling and validation
- ✅ Integration with esterm's intelligent caching system

## Usage

### Command Line (escmd.py)

#### Basic Usage
```bash
# Create a simple index with default settings (1 shard, 1 replica)
./escmd.py create-index my-app-logs

# Specify custom shard and replica counts
./escmd.py create-index user-data --shards 3 --replicas 2

# Short form options
./escmd.py create-index metrics -s 2 -r 1
```

#### Advanced Usage
```bash
# Create index with custom settings
./escmd.py create-index high-performance-logs \
  --shards 5 \
  --replicas 1 \
  --settings '{"refresh_interval": "30s", "max_result_window": 50000}'

# Create index with custom mappings
./escmd.py create-index structured-events \
  --mappings '{"properties": {"timestamp": {"type": "date"}, "message": {"type": "text"}, "level": {"type": "keyword"}}}'

# Combine custom settings and mappings
./escmd.py create-index analytics-data \
  --shards 3 \
  --replicas 2 \
  --settings '{"number_of_routing_shards": 6, "codec": "best_compression"}' \
  --mappings '{"properties": {"user_id": {"type": "keyword"}, "event_time": {"type": "date"}, "metrics": {"type": "object"}}}'

# JSON output format
./escmd.py create-index api-logs --format json
```

### Interactive Terminal (esterm)

```bash
# Start esterm and connect to a cluster
./esterm
esterm(prod)> connect

# Create indices interactively
esterm(prod)> create-index my-new-index
esterm(prod)> create-index logs-2024 --shards 2 --replicas 1
esterm(prod)> create-index events -s 3 -r 2

# Verify creation
esterm(prod)> indices
esterm(prod)> indice my-new-index
```

## Command Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `index_name` | - | string | required | Name of the index to create |
| `--shards` | `-s` | integer | 1 | Number of primary shards |
| `--replicas` | `-r` | integer | 1 | Number of replica shards |
| `--settings` | - | JSON string | none | Custom index settings as JSON |
| `--mappings` | - | JSON string | none | Custom index mappings as JSON |
| `--format` | - | choice | table | Output format (table or json) |

## Output Examples

### Success (Table Format)
```
📋 Creating Index: my-app-logs
  Primary Shards: 1
  Replica Shards: 1

✅ Index 'my-app-logs' created successfully
  Cluster acknowledged: ✓
  Shards acknowledged: ✓

💡 Next steps:
  • View index: ./escmd.py indice my-app-logs
  • List indices: ./escmd.py indices
  • Add documents via your application or curl
```

### Success (JSON Format)
```json
{
  "success": true,
  "index": "my-app-logs",
  "acknowledged": true,
  "shards_acknowledged": true,
  "message": "Index 'my-app-logs' created successfully"
}
```

### Error Example
```
📋 Creating Index: existing-index
  Primary Shards: 1
  Replica Shards: 1

❌ Failed to create index 'existing-index': resource_already_exists_exception
  Error: index [existing-index/abc123] already exists
```

## Integration Details

### Cache Management
- **Automatic Refresh**: After successful index creation, the indices cache is automatically refreshed
- **Real-time Display**: New indices appear immediately when running `indices` command
- **ESterm Integration**: Works seamlessly with esterm's intelligent caching system

### Error Handling
- **Index Name Validation**: Ensures index name is provided and valid
- **JSON Validation**: Validates custom settings and mappings JSON
- **Elasticsearch Errors**: Properly handles and displays Elasticsearch API errors
- **Network Errors**: Graceful handling of connection issues

### Help System Integration
- **Command Documentation**: Full integration with escmd help system
- **Examples**: Comprehensive usage examples in help output
- **ESterm Help**: Available through esterm's built-in help system

## Technical Implementation

### Architecture
```
CLI Argument Parser → CommandHandler → IndexHandler → ElasticsearchClient → IndicesCommands → Elasticsearch API
```

### Key Components
1. **IndicesCommands.create_index()**: Core index creation logic
2. **ElasticsearchClient.create_index()**: Delegation and cache management
3. **IndexHandler.handle_create_index()**: User interface and validation
4. **Command routing**: Integration with escmd command system
5. **Cache refresh**: Automatic indices cache invalidation and refresh

### Files Modified
- `escmd/commands/indices_commands.py`: Added `create_index()` method
- `escmd/esclient.py`: Added delegation method with cache refresh
- `escmd/handlers/index_handler.py`: Added `handle_create_index()` method
- `escmd/cli/argument_parser.py`: Added `create-index` command definition
- `escmd/command_handler.py`: Added command routing
- `escmd/handlers/help_handler.py`: Added help documentation
- `escmd/esterm_modules/command_processor.py`: Added cache refresh trigger

## Common Use Cases

### Application Development
```bash
# Create development index
./escmd.py create-index app-logs-dev --shards 1 --replicas 0

# Create production index with high availability
./escmd.py create-index app-logs-prod --shards 3 --replicas 2
```

### Time-Series Data
```bash
# Create monthly log index
./escmd.py create-index logs-2024-01 \
  --settings '{"refresh_interval": "30s"}' \
  --mappings '{"properties": {"@timestamp": {"type": "date"}, "message": {"type": "text"}, "level": {"type": "keyword"}}}'
```

### Analytics and Metrics
```bash
# Create analytics index with optimized settings
./escmd.py create-index user-analytics \
  --shards 2 \
  --settings '{"codec": "best_compression", "max_result_window": 100000}' \
  --mappings '{"properties": {"user_id": {"type": "keyword"}, "event": {"type": "keyword"}, "timestamp": {"type": "date"}, "properties": {"type": "object"}}}'
```

### Testing and Development
```bash
# Quick test index
./escmd.py create-index test-index

# Multiple test indices
for i in {1..5}; do
  ./escmd.py create-index test-index-$i --shards 1 --replicas 0
done
```

## Best Practices

### Index Naming
- Use lowercase names
- Use hyphens instead of underscores
- Include environment prefixes (dev-, prod-, test-)
- Use date patterns for time-series data (logs-2024-01)

### Shard Configuration
- **Small datasets**: 1 shard, 1 replica
- **Medium datasets**: 2-3 shards, 1-2 replicas
- **Large datasets**: Calculate based on data volume and query patterns
- **Development/Testing**: 1 shard, 0 replicas

### Settings Recommendations
```json
{
  "refresh_interval": "30s",          // For write-heavy workloads
  "max_result_window": 50000,         // For deep pagination
  "codec": "best_compression",        // For storage optimization
  "number_of_routing_shards": 6       // For future resharding
}
```

### Mappings Best Practices
- Define explicit mappings for structured data
- Use `keyword` type for exact matches and aggregations
- Use `text` type for full-text search
- Always include timestamp fields as `date` type
- Consider using `dynamic: false` for strict schema control

## Troubleshooting

### Common Errors

**"Index name is required"**
- Ensure you provide the index name as the first argument

**"Invalid JSON in settings"**
- Validate your JSON syntax
- Use single quotes around the JSON string in bash

**"resource_already_exists_exception"**
- Index already exists, choose a different name
- Delete existing index first if needed: `./escmd.py indices existing-name --delete`

**"cluster_block_exception"**
- Cluster is in read-only mode or has blocks
- Check cluster health: `./escmd.py health`

### Debugging

```bash
# Check if index was created
./escmd.py indices | grep my-index

# View index details
./escmd.py indice my-index

# Check cluster health
./escmd.py health

# Use JSON output for detailed error info
./escmd.py create-index problematic-index --format json
```

## Version Information

- **Added in**: v3.0.1
- **Compatible with**: Elasticsearch 7.x, 8.x
- **Dependencies**: Rich console library, standard escmd dependencies
- **Python**: 3.7+

## Future Enhancements

- Template-based index creation
- Bulk index creation from configuration files
- Index lifecycle policy assignment during creation
- Integration with cluster templates and policies
- Dry-run mode for validation