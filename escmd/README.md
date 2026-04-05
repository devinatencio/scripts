# escmd.py

🚀 **Enhanced Elasticsearch Command Line Tool** - Making Elasticsearch operations more enjoyable and efficient.

![Version](https://img.shields.io/badge/version-3.8.4-blue)
![Python](https://img.shields.io/badge/python-3.6%2B-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## Overview

escmd is a comprehensive command-line utility that transforms how you interact with Elasticsearch clusters. With rich terminal output, comprehensive health monitoring, and powerful automation capabilities, escmd makes complex Elasticsearch operations simple and intuitive.

## 🌟 Key Features

- **🖥️ Interactive Terminal (ESTERM)** - Persistent shell-like interface for seamless cluster operations
- **🏥 Comprehensive Health Monitoring** - Multi-panel dashboards with real-time cluster insights
- **🔧 Dual-Mode Replica Management** - Integrated health-check fixing and standalone operations
- **📋 Advanced ILM Management** - Complete policy lifecycle (create, delete, track), error detection, and lifecycle analysis
- **⚠️ Smart Index Operations** - Dangling cleanup, freezing, and shard optimization
- **🎨 Rich Terminal Output** - Beautiful tables, panels, and progress indicators
- **🔍 Deep Cluster Analysis** - Shard colocation, allocation issues, and performance insights
- **🚀 Multi-Cluster Support** - Easy switching between environments with group monitoring
- **🤖 Automation Ready** - JSON output and script-friendly operations

## 🖥️ ESTERM - Interactive Terminal

**NEW!** Experience escmd through our interactive terminal for the best user experience:

```bash
# Start ESTERM interactive terminal
./esterm.py

# Or use the wrapper script
./esterm
```

ESTERM provides:
- **Persistent Cluster Connection** - Connect once, run multiple commands
- **Command History** - Full readline support with persistent history
- **Real-time Monitoring** - `watch health` with live updates
- **Multi-cluster Switching** - Easy `connect cluster` commands
- **All ESCMD Features** - Every command works without the `./escmd.py` prefix

**[📖 Complete ESTERM Guide →](docs/guides/ESTERM_GUIDE.md)**

## 🚀 Quick Start

### Installation

```escmd/requirements.txt#L1-10
# Install dependencies
pip3 install -r requirements.txt

# Make executable
chmod +x escmd.py

# Test installation
./escmd.py --help
```

### Basic Configuration

Create `elastic_servers.yml`:

```escmd/elastic_servers.yml#L1-20
settings:
  health_style: dashboard
  enable_paging: true

servers:
  - name: local
    hostname: localhost
    port: 9200
    use_ssl: false
    elastic_authentication: false

  - name: production
    hostname: prod-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: your-password
```

### Essential Commands

```escmd/escmd.py#L1-25
# Cluster health monitoring
./escmd.py health                    # Quick status check
./escmd.py health-detail             # Rich dashboard view
./escmd.py -l production health      # Specific cluster

# Comprehensive health analysis
./escmd.py cluster-check             # Full health assessment
./escmd.py cluster-check --fix-replicas 1  # Fix replica issues

# Index operations
./escmd.py indices                   # List all indices
./escmd.py indices --status red      # Filter unhealthy indices
./escmd.py indices "logs-*" --delete # Delete indices by pattern
./escmd.py dangling --cleanup-all --dry-run  # Preview cleanup
./escmd.py dangling --cleanup-all --batch 100  # Clean 100 indices at a time
./escmd.py set-replicas --no-replicas-only   # Fix replica counts

# ILM management
./escmd.py ilm status               # ILM overview
./escmd.py ilm policies             # List all policies
./escmd.py ilm errors               # Find ILM issues
./escmd.py ilm create-policy retention-policy policy.json  # Create new policy
./escmd.py ilm delete-policy old-policy  # Delete policy (with confirmation)
./escmd.py ilm remove-policy "temp-*" --dry-run  # Preview policy removal from indices
```

## 📚 Documentation

### 🖥️ Interactive Terminal
- **[ESTERM Guide](docs/ESTERM_GUIDE.md)** - Complete interactive terminal documentation

### 🛠️ Setup & Configuration
- **[Installation Guide](docs/configuration/installation.md)** - Complete setup instructions
- **[Cluster Setup](docs/configuration/cluster-setup.md)** - Configure your Elasticsearch clusters

### 📖 Command Reference
- **[Health Monitoring](docs/commands/health-monitoring.md)** - Cluster health dashboards and monitoring
- **[Node Operations](docs/commands/node-operations.md)** - Node management, connectivity testing, and basic cluster operations
- **[Cluster Check](docs/commands/cluster-check.md)** - Comprehensive health analysis and issue detection
- **[Replica Management](docs/commands/replica-management.md)** - Dual-mode replica count management
- **[Index Operations](docs/commands/index-operations.md)** - Index management, deletion, and dangling cleanup
- **[ILM Management](docs/commands/ilm-management.md)** - Index Lifecycle Management and policy operations
- **[Allocation Management](docs/commands/allocation-management.md)** - Shard allocation control and troubleshooting
- **[Snapshot Management](docs/commands/snapshot-management.md)** - Backup monitoring and snapshot analysis

### 🔄 Workflows & Examples
- **[Monitoring Workflows](docs/workflows/monitoring-workflows.md)** - Daily operations and automation

### 📋 Reference
- **[Complete Documentation Index](docs/README.md)** - Full documentation structure
- **[Troubleshooting Guide](docs/reference/troubleshooting.md)** - Common issues and solutions
- **[Changelog](docs/reference/changelog.md)** - Version history and updates

## 💡 Common Use Cases

### Daily Operations
```escmd/escmd.py#L130-138
# Morning health check routine
./escmd.py health --group production
./escmd.py cluster-check --fix-replicas 1 --dry-run

# Monitor specific issues
./escmd.py ilm errors
./escmd.py dangling
```

### Maintenance Tasks
```escmd/escmd.py#L140-150
# Pre-maintenance preparation
./escmd.py cluster-check > pre-maintenance-$(date +%Y%m%d).txt
./escmd.py set-replicas --pattern "critical-*" --count 2
./escmd.py allocation exclude add ess46     # Exclude node for maintenance

# Post-maintenance validation
./escmd.py health
./escmd.py cluster-check --show-details
./escmd.py allocation exclude remove ess46  # Re-enable node
./escmd.py snapshots list | head -5         # Check recent backups
```

### Automation & Monitoring
```escmd/escmd.py#L152-160
# Script-friendly health monitoring
./escmd.py health --format json | jq '.status'

# Automated replica management
./escmd.py cluster-check --fix-replicas 1 --force --format json

# ILM monitoring integration
./escmd.py ilm errors --format json | jq 'length'

# Automated policy management
./escmd.py ilm create-policy backup-policy policy.json --format json
./escmd.py ilm delete-policy old-policy --yes --format json
```

## 🔧 Advanced Features

### Multi-Cluster Management
```escmd/escmd.py#L164-170
# Compare clusters side-by-side
./escmd.py -l prod1 health --compare prod2

# Monitor cluster groups
./escmd.py health --group production
./escmd.py health --group staging
```

### Rich Output Formats
- **Dashboard Mode**: 6-panel visual health dashboard
- **Classic Mode**: Traditional table-based display
- **JSON Mode**: Machine-readable output for automation
- **ASCII Mode**: Maximum terminal compatibility

### Intelligent Operations
- **Dry-Run Mode**: Preview all operations before execution
- **Progress Tracking**: Real-time progress bars and status updates
- **Error Recovery**: Automatic retries and graceful error handling
- **Safety Checks**: Comprehensive validation and confirmation prompts

## 🎯 What's New in v3.7.0

### 🌍 **Environment-Specific Metrics Configuration**
- **Automatic Environment Detection** for metrics with `--env` parameter integration
- **Multi-Environment Support** for BIZ, LAB, OPS, US, EU, and IN with pre-configured endpoints
- **Zero-Configuration Operation** eliminates manual endpoint switching between environments
- **Seamless Integration** with all dangling command operations and cleanup workflows

### 📊 **Intelligent Endpoint Routing**
- **Environment-to-Database Mapping** automatically routes metrics to correct InfluxDB instances
- **Configuration Merging** with environment-specific overrides and intelligent fallbacks
- **Production-Ready Error Handling** with clear troubleshooting guidance
- **Backward Compatibility** maintains all existing metrics functionality

### 🚀 **Enhanced Operational Workflows**
```bash
./escmd.py dangling --env biz --metrics     # Auto-routes to BIZ InfluxDB
./escmd.py dangling --env lab --cleanup-all --metrics  # LAB environment
./escmd.py dangling --env us --batch 10 --metrics      # US environment
```

### ⚙️ **Extended Configuration Architecture**
- **Environment-Specific YAML Structure** in `metrics.environments` section
- **Priority-Based Resolution** with environment variables → environment config → defaults
- **Flexible Environment Addition** through simple YAML configuration updates
- **Complete Documentation** with usage examples and troubleshooting guides

[**See complete changelog →**](docs/reference/changelog.md)

## 🚦 Getting Help

### Quick Help
```escmd/escmd.py#L226-230
./escmd.py --help                    # Main help with command categories
./escmd.py health --help             # Specific command help
./escmd.py cluster-check --help      # Comprehensive health options
```

### Documentation Navigation
- **New to escmd?** Start with [Installation Guide](docs/configuration/installation.md)
- **Setting up clusters?** See [Cluster Setup](docs/configuration/cluster-setup.md)
- **Need to monitor health?** Check [Health Monitoring](docs/commands/health-monitoring.md)
- **Having issues?** Review [Troubleshooting Guide](docs/reference/troubleshooting.md)

### Support
- **Issues**: Report bugs and request features via GitHub issues
- **Documentation**: Complete documentation in the \`docs/\` directory
- **Examples**: Real-world workflows in [Monitoring Workflows](docs/workflows/monitoring-workflows.md)

## 🔗 Quick Links

| Category | Documentation |
|----------|---------------|
| **🛠️ Setup** | [Installation](docs/configuration/installation.md) • [Configuration](docs/configuration/cluster-setup.md) |
| **📖 Commands** | [Health](docs/commands/health-monitoring.md) • [Nodes](docs/commands/node-operations.md) • [Cluster Check](docs/commands/cluster-check.md) • [Cluster Settings](docs/commands/cluster-settings.md) • [Replicas](docs/commands/replica-management.md) • [Indices](docs/commands/index-operations.md) • [ILM](docs/commands/ilm-management.md) • [Allocation](docs/commands/allocation-management.md) • [Snapshots](docs/commands/snapshot-management.md) |
| **🔄 Workflows** | [Monitoring](docs/workflows/monitoring-workflows.md) |
| **📋 Reference** | [Troubleshooting](docs/reference/troubleshooting.md) • [Changelog](docs/reference/changelog.md) |

---

**escmd** - Making Elasticsearch operations simple, powerful, and enjoyable! 🎉
