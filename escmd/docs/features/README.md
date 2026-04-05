# ESCMD Features Documentation

This directory contains documentation for various ESCMD features and capabilities.

## 📋 Available Features

### 🚀 Enhanced Actions System (v3.3.0+)
- **[Enhanced Actions Guide](enhanced_actions_guide.md)** - Comprehensive guide to the new command chaining and data passing system
- **[Implementation Summary](enhanced_actions_implementation.md)** - Technical implementation details and migration guide
- **[ESterm Actions](esterm-actions.md)** - ESterm-specific action integration

### 🎨 User Interface & Experience
- **[Enhanced Prompts](enhanced-prompts.md)** - Interactive prompt system enhancements

### 📊 Data Management
- **[Index Metadata](index-metadata.md)** - Index metadata management features

## 🎯 Quick Start

### Enhanced Actions System
The Enhanced Actions System is the latest major feature that allows you to:
- Chain multiple commands together
- Pass data between command steps
- Extract values from JSON responses
- Execute conditional workflows
- Automate complex operations like rollover + cleanup

**Example: Rollover and Delete Old Index**
```yaml
- name: roll-igl
  description: "Rollover datastream and delete the old index"
  steps:
    - name: Rollover Indice
      action: rollover my-datastream --format json
      capture:
        old_index_name: "$.old_index"
        rollover_success: "$.rolled_over"
    - name: Delete Old Index
      action: indices --delete {{ old_index_name }}
      condition: "{{ rollover_success }}"
      confirm: true
```

**Usage:**
```bash
# Test the action
./escmd.py action run roll-igl --dry-run

# Execute the action
./escmd.py action run roll-igl
```

### Key Benefits
- **Automation**: Convert manual multi-step processes into single commands
- **Safety**: Built-in confirmations and conditional execution
- **Reliability**: Error handling and rollback capabilities
- **Flexibility**: Parameterized actions for reusability
- **Visibility**: Rich progress indicators and detailed logging

## 📚 Documentation Structure

```
docs/features/
├── README.md                           # This index file
├── enhanced_actions_guide.md           # Complete actions system guide
├── enhanced_actions_implementation.md  # Technical implementation details
├── esterm-actions.md                   # ESterm integration
├── enhanced-prompts.md                 # Interactive prompts
└── index-metadata.md                   # Index metadata features
```

## 🔗 Related Documentation

- **[Commands Documentation](../commands/)** - Individual command references
- **[Configuration Guide](../configuration/)** - System configuration
- **[Development Guide](../development/)** - Development and contribution
- **[Workflows](../workflows/)** - Common workflow examples

## 🆕 What's New in v3.3.0

- **Revolutionary Command Chaining**: Full data passing between steps
- **JSON Path Extraction**: Extract specific values using `$.field.path`
- **Variable Interpolation**: Use captured data with `{{ variable }}`
- **Conditional Execution**: Smart step execution based on results
- **Production Safety**: Confirmations, health checks, error recovery
- **Rich Documentation**: Comprehensive guides and examples

## 🚀 Getting Started

1. **Explore Actions**: `./escmd.py action list`
2. **View Details**: `./escmd.py action show <action-name>`
3. **Test Safely**: `./escmd.py action run <action-name> --dry-run`
4. **Execute**: `./escmd.py action run <action-name>`

## 💡 Pro Tips

- Always test actions with `--dry-run` first
- Use `--format json` for commands that need data extraction
- Include safety checks and confirmations for destructive operations
- Create parameterized actions for reusability across environments
- Check the comprehensive guide for advanced patterns and best practices

---

For the most up-to-date information, see the [Enhanced Actions Guide](enhanced_actions_guide.md).