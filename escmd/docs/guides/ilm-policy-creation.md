# ILM Policy Creation Guide

This document explains how to create Index Lifecycle Management (ILM) policies using the escmd utility.

## Overview

The `ilm create-policy` command allows you to create ILM policies for managing the lifecycle of your Elasticsearch indices. You can provide policy definitions via:

- **Inline JSON**: Direct JSON string on the command line
- **JSON files**: Path to a file containing the policy definition
- **File flag**: Using the `--file` flag to specify the policy file

## Usage Syntax

```bash
./escmd.py [-l location] ilm create-policy <policy_name> [policy_definition]
./escmd.py [-l location] ilm create-policy <policy_name> --file <policy_file>
```

### Parameters

- `policy_name`: Name for the new ILM policy
- `policy_definition`: JSON policy definition (inline) or path to JSON file (optional)
- `--file`: Path to JSON file containing policy definition (optional)
- `--format`: Output format - `json` or `table` (default: table)

## Examples

### 1. Create Policy from File (Method 1)

```bash
./escmd.py -l dev ilm create-policy my-retention-policy policy.json
```

### 2. Create Policy from File (Method 2 - using --file flag)

```bash
./escmd.py -l dev ilm create-policy my-retention-policy --file policy.json
```

### 3. Create Policy with Inline JSON

```bash
./escmd.py -l dev ilm create-policy quick-delete-policy '{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "10gb"
          }
        }
      },
      "delete": {
        "min_age": "7d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}'
```

### 4. Get JSON Output

```bash
./escmd.py -l dev ilm create-policy test-policy policy.json --format json
```

## Policy Structure

ILM policies must follow the Elasticsearch ILM policy structure:

```json
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "50gb",
            "max_age": "30d"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "set_priority": {
            "priority": 50
          },
          "allocate": {
            "number_of_replicas": 1
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "set_priority": {
            "priority": 0
          },
          "allocate": {
            "number_of_replicas": 0
          }
        }
      },
      "delete": {
        "min_age": "365d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

## Available Phases

ILM policies can include the following phases:

### Hot Phase
- **Purpose**: Active data that is being written to and queried frequently
- **Common Actions**:
  - `rollover`: Create new index when size/age/doc count thresholds are met
  - `set_priority`: Set index priority for recovery
  - `unfollow`: Convert follower index to regular index (CCR)

### Warm Phase
- **Purpose**: Data that is queried less frequently and no longer being written to
- **Common Actions**:
  - `allocate`: Change replica count and node allocation
  - `set_priority`: Lower priority for recovery
  - `forcemerge`: Merge segments to reduce storage
  - `shrink`: Reduce number of primary shards

### Cold Phase
- **Purpose**: Data that is rarely queried but must be retained
- **Common Actions**:
  - `allocate`: Move to cheaper storage nodes
  - `set_priority`: Lowest priority for recovery
  - `freeze`: Make index read-only and minimize memory usage

### Frozen Phase
- **Purpose**: Data stored in searchable snapshots (requires Enterprise license)
- **Common Actions**:
  - `searchable_snapshot`: Move index to snapshot repository

### Delete Phase
- **Purpose**: Permanently delete old data
- **Common Actions**:
  - `delete`: Remove the index entirely
  - `wait_for_snapshot`: Wait for snapshot before deletion

## Example Policy Files

### Simple 30-Day Retention Policy

```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "10gb",
            "max_age": "7d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "allocate": {
            "number_of_replicas": 0
          }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

### Comprehensive Long-Term Retention Policy

```json
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "50gb",
            "max_age": "30d",
            "max_docs": 100000000
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "set_priority": {
            "priority": 50
          },
          "allocate": {
            "number_of_replicas": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "set_priority": {
            "priority": 0
          },
          "allocate": {
            "number_of_replicas": 0
          }
        }
      },
      "delete": {
        "min_age": "365d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

## Error Handling

The command provides helpful error messages for common issues:

### Invalid JSON
```
Invalid inline JSON: Expecting value: line 1 column 13 (char 12)
```

### Missing Policy Definition
```
Please provide either:
- Inline JSON: ./escmd.py ilm create-policy my-policy '{"policy":{...}}'
- File path: ./escmd.py ilm create-policy my-policy policy.json
- Or use --file flag: ./escmd.py ilm create-policy my-policy --file policy.json
```

### File Not Found
```
Policy file 'non-existent-file.json' not found.
```

## Success Output

### Table Format (Default)
```
╭─────────────────────────── 🎯 ILM Policy Created ───────────────────────────╮
│                                                                             │
│   Policy Name:  my-retention-policy                                         │
│   Source:       file: policy.json                                           │
│   Status:       ✓ Created Successfully                                      │
│   Phases:       hot, warm, cold, delete                                     │
│                                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯
```

### JSON Format
```json
{
  "policy_name": "my-retention-policy",
  "source": "file: policy.json",
  "result": {
    "acknowledged": true
  },
  "status": "created"
}
```

## Best Practices

1. **Start Simple**: Begin with basic hot/delete phases, then add complexity
2. **Test Policies**: Create policies on development clusters first
3. **Document Settings**: Keep policy definitions in version control
4. **Monitor Performance**: Watch how policies affect cluster performance
5. **Gradual Rollout**: Apply policies to test indices before production data

## Related Commands

- `ilm policies`: List all existing ILM policies
- `ilm policy <name>`: View detailed policy configuration
- `ilm set-policy <policy> <pattern>`: Apply policy to indices
- `ilm status`: Check overall ILM status
- `ilm explain <index>`: Check specific index ILM status

## See Also

- [Elasticsearch ILM Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-lifecycle-management.html)
- `./escmd.py ilm --help`: Command-line help
- `./escmd.py help`: General escmd help