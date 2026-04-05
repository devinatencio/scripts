# ILM Policy Creation Quick Reference

## Quick Commands

```bash
# Create from file
./escmd.py -l cluster ilm create-policy policy-name policy.json

# Create with --file flag
./escmd.py -l cluster ilm create-policy policy-name --file policy.json

# Create with inline JSON
./escmd.py -l cluster ilm create-policy policy-name '{"policy":{"phases":{...}}}'

# JSON output
./escmd.py -l cluster ilm create-policy policy-name policy.json --format json
```

## Basic Policy Template

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

## Advanced Policy Template

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

## Common Actions by Phase

### Hot Phase Actions
- `rollover`: Triggers on size/age/docs
- `set_priority`: Sets index priority (100)
- `unfollow`: Stop CCR following

### Warm Phase Actions
- `set_priority`: Lower priority (50)
- `allocate`: Change replicas/node requirements
- `forcemerge`: Merge segments
- `shrink`: Reduce primary shards

### Cold Phase Actions
- `set_priority`: Lowest priority (0)
- `allocate`: Move to cold nodes
- `freeze`: Minimize memory usage

### Delete Phase Actions
- `delete`: Permanently remove index
- `wait_for_snapshot`: Wait before deletion

## Rollover Triggers

```json
"rollover": {
  "max_size": "50gb",     // Size threshold
  "max_age": "30d",       // Age threshold
  "max_docs": 10000000    // Document count
}
```

## Allocation Examples

```json
"allocate": {
  "number_of_replicas": 0,
  "include": {
    "box_type": "warm"
  },
  "exclude": {
    "box_type": "hot"
  },
  "require": {
    "data": "warm"
  }
}
```

## Time Units
- `ms`: milliseconds
- `s`: seconds
- `m`: minutes
- `h`: hours
- `d`: days

## Size Units
- `b`: bytes
- `kb`: kilobytes
- `mb`: megabytes
- `gb`: gigabytes
- `tb`: terabytes
- `pb`: petabytes

## Error Troubleshooting

| Error | Solution |
|-------|----------|
| `Invalid JSON` | Check JSON syntax with validator |
| `File not found` | Verify file path exists |
| `action_request_validation_exception` | Check action is valid for ES version |
| `Missing policy definition` | Provide JSON via file or inline |

## Related Commands

```bash
# List policies
./escmd.py ilm policies

# View specific policy
./escmd.py ilm policy policy-name

# Apply policy to indices
./escmd.py ilm set-policy policy-name 'index-pattern*'

# Check policy status
./escmd.py ilm status

# Show policy help
./escmd.py help ilm
```

## Policy Testing Workflow

1. **Create** policy with descriptive name
2. **Verify** policy appears in policy list
3. **Test** on non-production indices first
4. **Monitor** using `ilm status` and `ilm errors`
5. **Apply** to production indices gradually

## Best Practices

- ✅ Start with simple policies
- ✅ Test on development clusters first
- ✅ Use descriptive policy names
- ✅ Document policy purposes
- ✅ Monitor policy performance
- ✅ Version control policy files
- ❌ Don't create overly complex policies initially
- ❌ Don't skip testing on non-production data
- ❌ Don't ignore ILM error monitoring

---

📖 **Full Documentation**: [ILM Policy Creation Guide](../guides/ilm-policy-creation.md)  
🔧 **Implementation Details**: [Technical Implementation](../development/ilm-policy-create-implementation.md)  
📋 **ILM Commands**: [ILM Management](../commands/ilm-management.md)