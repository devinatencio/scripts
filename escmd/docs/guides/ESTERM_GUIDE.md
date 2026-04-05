# ESTERM - Interactive Elasticsearch Terminal

## Overview

**ESTERM** is an interactive terminal wrapper for ESCMD that provides a persistent, shell-like interface for managing Elasticsearch clusters. Instead of running individual `./escmd.py` commands each time, you can load a cluster context once and run multiple commands in an interactive session.

## Features

- 🔄 **Persistent Cluster Connection**: Connect once, run multiple commands
- 🎯 **Auto-cluster Detection**: Automatically connects to your default cluster
- 🎨 **Rich Terminal Interface**: Beautiful, themed output using Rich
- 📚 **Command History**: Readline support with persistent command history
- ⚡ **Full ESCMD Compatibility**: All regular ESCMD commands work seamlessly
- 🔍 **Built-in Help**: Interactive help system and status commands
- 🎪 **Multi-cluster Support**: Easy switching between different clusters

## Usage

### Starting ESTERM

```escmd/esterm.py#L1-5
# Start with auto-connection to default cluster
esterm

# Start without auto-connection
python3 esterm.py
```

### Connection Flow

When you start ESTERM, it will:
1. Show available clusters from your configuration
2. Auto-connect to your default cluster (if configured)
3. Prompt you to select a cluster if no default is set
4. Display connection status and cluster health

### Example Session

```escmd/esterm.py#L10-25
╭────────────────────── 🔍 Welcome to ESterm ───────────────────────╮
│                                                                   │
│  ESterm - Interactive Elasticsearch Terminal                      │
│  Version 3.0.1 (09/08/2025)                                       │
│                                                                   │
│  Enhanced with Rich formatting and interactive cluster selection  │
│  Type 'help' for commands or 'connect' to select a cluster        │
│  [Current theme: Cyberpunk Neon (cyberpunk)]                      │
│                                                                   │
╰───────────────────────────────────────────────────────────────────╯
Attempting to connect to default cluster: aex20-rlip
✓ Connected to cluster: aex20-glip
<esterm(aex20-glip)>
➤ 
```
### Typical Commands

```escmd/esterm.py#L30-45
➤ health
[Shows beautiful cluster health display]

dev > indices myapp-*
[Shows filtered indices matching pattern]

➤ nodes
[Shows cluster nodes]

➤ connect aex10
✓ Connected to cluster: aex10
<esterm(aex10)>
➤ 

production > exit
Goodbye!
```

## Built-in Commands

### Connection Management
- **`cls`** - Clear Screen
- **`connect [cluster]`** - Connect to a specific cluster
- **`disconnect`** - Disconnect from current cluster.
- **`status`** - Show current connection and cluster status

### Navigation & Help
- **`help`** or **`?`** - Show available commands and usage
- **`clear`** - Clear screen and redisplay banner
- **`theme`** - Show Themes Available
- **`exit`** or **`quit`** - Exit ESTERM



## ESCMD Commands

All regular ESCMD commands work without the `./escmd.py` prefix:

### Cluster Management

```escmd/esterm.py#L50-60
health                    # Cluster health overview
health --format json      # Health in JSON format
watch health              # Monitor cluster health continuously (Enter to stop)
watch health 5            # Monitor cluster health every 5 seconds (Enter to stop)
nodes                    # Show cluster nodes  
allocation               # Shard allocation status
cluster-settings         # Cluster settings
ping                     # Test cluster connectivity
```

### Index Management

```escmd/esterm.py#L62-70
indices                  # List all indices
indices myapp-*          # Filter indices by pattern
indices --format json    # Indices in JSON format
indices --status red     # Filter by health status
indice myindex           # Detailed info for specific index
recovery                 # Index recovery status
```

### Advanced Operations

```escmd/esterm.py#L72-80
snapshots               # List snapshots
ilm                     # Index Lifecycle Management
datastreams             # List data streams
dangling                # Find dangling indices
storage                 # Storage information
shards                  # Shard details
```

### Argument Support

ESTERM supports all the same arguments as regular ESCMD:

```escmd/esterm.py#L82-95
# Format options
indices --json                    # JSON output
health --format table            # Table format (default)

# Filtering options  
indices --status green           # Filter by status
nodes --detailed                 # Detailed information
health --timeout 30s            # Custom timeout

# Boolean flags
allocation --human               # Human readable sizes
indices --count                  # Show count only
recovery --verbose              # Verbose output
```

## Command History & Keyboard Shortcuts

ESTERM maintains command history using readline:

- **↑/↓ arrows**: Navigate through command history
- **Ctrl+R**: Reverse search through history
- **Tab**: Command completion (basic)
- **Ctrl+C**: Interrupt current operation (stays in esterm)
- **Ctrl+D**: Exit esterm entirely
- **Enter**: Stop monitoring commands (like `watch health`)
- **History file**: `~/.esterm_history` (persistent across sessions)

### Important: Stopping Commands vs Exiting
- **Ctrl+C**: Interrupts current operation but keeps you in esterm
- **Enter**: Stops monitoring commands and returns to prompt
- **Ctrl+D**: Exits esterm entirely

## Prompt Indicators

The prompt shows your current cluster and its health status:

```escmd/esterm.py#L110-114
dev >                    # Connected to 'dev' cluster (green)
production >             # Connected to 'production' cluster  
esterm >                 # Not connected to any cluster
```

Health status colors:
- **Green**: Cluster healthy
- **Yellow**: Cluster degraded  
- **Red**: Cluster has issues
- **Dim**: Connection issues

## Configuration

ESTERM uses the same configuration files as ESCMD:

- **`elastic_servers.yml`** - Server definitions
- **`escmd.yml`** - Main configuration  
- **`escmd.json`** - Default cluster state

### Example Configuration

```escmd/elastic_servers.yml#L1-15
# elastic_servers.yml
servers:
  - name: dev
    hostname: dev-es.company.com
    port: 9200
    use_ssl: true
    username: elastic
    
  - name: production  
    hostname: prod-es.company.com
    port: 9200
    use_ssl: true
    username: elastic
```

## Tips & Best Practices

### 1. **Use Pattern Matching**

```escmd/esterm.py#L120-125
# Find indices by pattern
indices logs-*
indices *-2024-*
indices app-prod-*
```

### 2. **Combine with Output Formatting**

```escmd/esterm.py#L127-133
# Get JSON for scripting
indices myapp-* --json

# Human readable sizes
allocation --human
storage --human
```

### 3. **Quick Health Checks**

```escmd/esterm.py#L135-145
# Quick status check
status

# Detailed health
health

# Monitor health continuously (Enter to stop)
watch health

# Node information
nodes
```

### 4. **Real-time Monitoring**

```escmd/esterm.py#L147-155
# Continuous health monitoring (default 10s interval, Enter to stop)
watch health

# Custom interval monitoring
watch health 5              # Monitor every 5 seconds
watch health 30             # Monitor every 30 seconds

# Stop monitoring by pressing Enter (NOT Ctrl+C which exits esterm)
```

### 5. **Compare Environments**
### 5. **Multi-cluster Workflows**

```escmd/esterm.py#L157-165
# Check production
connect production
health
indices --status red

# Compare with staging
connect staging  
health
indices --status red
```

### 6. **Use Tab Completion**
Start typing commands and use Tab for basic completion.

## Troubleshooting

### Connection Issues

If you see connection errors:

1. **Check cluster availability:**
   ```escmd/escmd.py#L167-170
   # In regular terminal
   ./escmd.py health -l production
   ```

2. **Verify configuration:**
   ```escmd/escmd.py#L172-175
   # Check available locations
   ./escmd.py locations
   ```

3. **Test credentials:**
   ```escmd/escmd.py#L177-180
   # Test with debug
   ./escmd.py health --debug
   ```

### Command Errors

If commands fail in ESTERM:

1. **Try the same command with regular ESCMD:**
   ```escmd/escmd.py#L182-185
   ./escmd.py indices mypattern
   ```

2. **Use debug mode:**
   ```escmd/esterm.py#L187-190
   dev > indices mypattern --debug
   ```

3. **Check cluster connectivity:**
   ```escmd/esterm.py#L192-197
   dev > status
   dev > health
   dev > watch health    # Press Enter to stop monitoring
   ```

### Missing Commands

If a command isn't recognized:

1. **Check available commands:**
   ```escmd/esterm.py#L199-202
   dev > help
   ```

2. **Verify command syntax:**
   ```escmd/escmd.py#L204-207
   # Try with regular escmd first
   ./escmd.py your-command --help
   ```

## Comparison: ESTERM vs Regular ESCMD

| Aspect | Regular ESCMD | ESTERM |
|--------|---------------|---------|
| **Usage** | `./escmd.py health -l dev` | `health` (after connecting) |
| **Connection** | Per command | Persistent session |
| **Context** | Must specify cluster each time | Remembers current cluster |
| **History** | Shell history only | Dedicated command history |
| **Switching** | Change `-l` parameter | `connect cluster` command |
| **Speed** | Slower (reconnect each time) | Faster (persistent connection) |
| **Scripting** | Better for scripts | Better for interactive use |

## Advanced Features

### Session Management

ESTERM maintains session state:
- Current cluster connection
- Command history
- Connection status

### Error Handling

Robust error handling for:
- Network connectivity issues
- Cluster unavailability  
- Invalid commands
- Authentication problems

### Rich Output

All output uses Rich formatting:
- Colored tables and panels
- Progress indicators
- Status symbols and icons
- Themed displays

## Development

### Architecture

ESTERM is built on top of ESCMD's existing infrastructure:

- **`ElasticsearchClient`**: Reuses existing client
- **`CommandHandler`**: Leverages current command routing
- **`ConfigurationManager`**: Uses same configuration system
- **Rich Console**: Enhanced terminal experience

### Extending ESTERM

To add new built-in commands:

1. Add to `_parse_command()` method
2. Implement in `_execute_builtin_command()`
3. Update help text in `_show_help()`

### MockArgs Implementation

ESTERM creates MockArgs objects to simulate argparse results, ensuring compatibility with existing command handlers.

## License

ESTERM follows the same license as ESCMD.

---

**Happy Elasticsearch management with ESTERM!** 🔍✨
