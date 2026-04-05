# Template Creation Command Usage

The `template-create` command allows you to create Elasticsearch templates from JSON files or inline definitions. This command supports component templates, composable index templates, and legacy index templates.

## Usage

### Create Templates from JSON File

```bash
# Create component templates from JSON file
escmd template-create --file templates.json

# Dry run to validate without creating
escmd template-create --file templates.json --dry-run

# Show results in JSON format
escmd template-create --file templates.json --format json
```

### Create Single Template Inline

```bash
# Create a component template inline
escmd template-create --name my_template --type component --definition '{"template":{"settings":{"index.number_of_shards":1}}}'

# Create a composable template inline
escmd template-create --name my_index_template --type composable --definition '{"index_patterns":["logs-*"],"template":{"settings":{"index.number_of_shards":1}}}'
```

## JSON File Formats

### Component Templates (Recommended)

For component templates, use this format:

```json
{
  "component_templates": [
    {
      "name": "manual_template",
      "component_template": {
        "template": {
          "settings": {
            "index": {
              "routing": {
                "allocation": {
                  "exclude": {
                    "_name": "node1-*,node2-*"
                  }
                }
              }
            }
          }
        },
        "_meta": {
          "description": "Template for manual allocation exclusions",
          "version": 1
        }
      }
    }
  ]
}
```

### Composable Index Templates

For composable index templates:

```json
{
  "index_templates": [
    {
      "name": "logs_template",
      "index_template": {
        "index_patterns": ["logs-*"],
        "priority": 100,
        "template": {
          "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1
          },
          "mappings": {
            "properties": {
              "timestamp": {
                "type": "date"
              },
              "message": {
                "type": "text"
              }
            }
          }
        },
        "composed_of": ["component_template_1"],
        "_meta": {
          "description": "Template for log indices"
        }
      }
    }
  ]
}
```

### Legacy Templates

For legacy index templates:

```json
{
  "templates": {
    "legacy_template": {
      "index_patterns": ["old-logs-*"],
      "settings": {
        "number_of_shards": 1
      },
      "mappings": {
        "properties": {
          "message": {
            "type": "text"
          }
        }
      }
    }
  }
}
```

## Command Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--file` | `-f` | Path to JSON file containing templates | None |
| `--name` | `-n` | Template name (for inline creation) | None |
| `--type` | `-t` | Template type (component, composable, legacy) | component |
| `--definition` | `-d` | Inline JSON template definition | None |
| `--dry-run` | | Validate without creating templates | False |
| `--format` | | Output format (table, json) | table |

## Examples

### Example 1: Component Template for Node Allocation

Create a component template that excludes specific nodes:

```bash
# Save this to allocation_template.json
cat > allocation_template.json << 'EOF'
{
  "component_templates": [
    {
      "name": "exclude_weak_nodes",
      "component_template": {
        "template": {
          "settings": {
            "index": {
              "routing": {
                "allocation": {
                  "exclude": {
                    "_name": "weak-node-*"
                  }
                }
              }
            }
          }
        },
        "_meta": {
          "description": "Exclude weak nodes from allocation",
          "created_by": "admin",
          "version": 1
        }
      }
    }
  ]
}
EOF

# Create the template
escmd template-create --file allocation_template.json
```

### Example 2: Multiple Component Templates

Create multiple component templates at once:

```json
{
  "component_templates": [
    {
      "name": "common_settings",
      "component_template": {
        "template": {
          "settings": {
            "index": {
              "number_of_replicas": 1,
              "refresh_interval": "30s"
            }
          }
        }
      }
    },
    {
      "name": "log_mappings",
      "component_template": {
        "template": {
          "mappings": {
            "properties": {
              "@timestamp": {
                "type": "date"
              },
              "level": {
                "type": "keyword"
              },
              "message": {
                "type": "text",
                "analyzer": "standard"
              }
            }
          }
        }
      }
    }
  ]
}
```

### Example 3: Composable Template Using Components

```json
{
  "index_templates": [
    {
      "name": "application_logs",
      "index_template": {
        "index_patterns": ["app-logs-*"],
        "priority": 200,
        "composed_of": ["common_settings", "log_mappings"],
        "template": {
          "settings": {
            "index": {
              "lifecycle": {
                "name": "logs_policy"
              }
            }
          }
        },
        "_meta": {
          "description": "Template for application logs using component templates"
        }
      }
    }
  ]
}
```

## Validation and Error Handling

The command performs several validation checks:

1. **File Existence**: Validates that the JSON file exists
2. **JSON Syntax**: Ensures the JSON is well-formed
3. **Template Structure**: Validates the template structure
4. **Dry Run**: Use `--dry-run` to validate without creating

### Common Error Messages

- `File not found: /path/to/file.json` - The specified file doesn't exist
- `Invalid JSON format: ...` - The JSON syntax is incorrect
- `No valid template definitions found` - The JSON doesn't contain recognized template structures
- `Template creation not acknowledged by Elasticsearch` - ES didn't acknowledge the creation
- `Elasticsearch API error: ...` - ES returned an error during creation

## Best Practices

1. **Use Component Templates**: Prefer component templates for reusable settings and mappings
2. **Test with Dry Run**: Always test with `--dry-run` first
3. **Version Your Templates**: Use `_meta.version` for template versioning
4. **Document Templates**: Use `_meta.description` to document template purpose
5. **Backup Before Changes**: Consider backing up existing templates before modifications

## Integration with Other Commands

The template-create command works well with other escmd template commands:

```bash
# Create templates from file
escmd template-create --file my_templates.json

# List all templates to verify creation
escmd templates --type component

# View detailed information
escmd template my_component_template --type component

# Backup templates before modifications
escmd template-backup my_component_template --type component
```
