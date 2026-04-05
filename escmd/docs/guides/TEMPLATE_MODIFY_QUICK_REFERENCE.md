# Template Modification Quick Reference

## Commands

### template-modify
Modify template fields using dot notation.

```bash
escmd template-modify <name> -f <field_path> -o <operation> -v <value> [options]
```

**Required:**
- `<name>`: Template name
- `-f, --field`: Field path in dot notation
- `-v, --value`: Value (except for delete operation)

**Options:**
- `-t, --type`: Template type (auto|legacy|composable|component) [default: auto]
- `-o, --operation`: Operation (set|append|remove|delete) [default: set]
- `--backup/--no-backup`: Control backup creation [default: backup enabled]
- `--backup-dir`: Custom backup directory
- `--dry-run`: Preview changes without applying

### template-backup
Create manual template backup.

```bash
escmd template-backup <name> [options]
```

### template-restore
Restore template from backup.

```bash
escmd template-restore --backup-file <path>
```

### list-backups
List available backups.

```bash
escmd list-backups [--name <template>] [--type <type>] [--format json|table]
```

## Operations

| Operation | Description | Example Use Case |
|-----------|-------------|------------------|
| `set` | Replace field value | Set replica count to 2 |
| `append` | Add to comma-separated list | Add hosts to exclusion list |
| `remove` | Remove from comma-separated list | Remove hosts from exclusion list |
| `delete` | Remove field entirely | Delete temporary settings |

## Common Use Cases

### Host Exclusion Management

**Current exclusion list:**
```
template.settings.index.routing.allocation.exclude._name
```

**Add hosts:**
```bash
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o append -v "new-host-*,another-host-*"
```

**Remove hosts:**
```bash
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o remove -v "old-host-*"
```

**Replace entire list:**
```bash
escmd template-modify manual_template -t component \
  -f "template.settings.index.routing.allocation.exclude._name" \
  -o set -v "host1-*,host2-*,host3-*"
```

### Index Settings

**Set replicas:**
```bash
escmd template-modify my_template -t component \
  -f "template.settings.index.number_of_replicas" \
  -o set -v "2"
```

**Set refresh interval:**
```bash
escmd template-modify my_template -t component \
  -f "template.settings.index.refresh_interval" \
  -o set -v "30s"
```

### Template Metadata

**Update description:**
```bash
escmd template-modify my_template -t component \
  -f "_meta.description" \
  -o set -v "Updated production template"
```

**Add version:**
```bash
escmd template-modify my_template -t component \
  -f "_meta.version" \
  -o set -v "2.1.0"
```

## Field Path Examples

| Template Type | Common Paths |
|---------------|--------------|
| Component | `template.settings.index.*` |
| Component | `template.mappings.properties.*` |
| Component | `_meta.*` |
| Composable | `template.settings.index.*` |
| Composable | `index_patterns` |
| Legacy | `settings.index.*` |
| Legacy | `mappings.properties.*` |

## Safety Features

- **Automatic backups** before modifications (can be disabled with `--no-backup`)
- **Dry run mode** with `--dry-run` to preview changes
- **Field validation** before applying changes
- **Template structure validation** after modifications
- **Backup/restore functionality** for recovery

## Backup Management

**Default backup location:** `~/.escmd/template_backups/`
**Filename format:** `{template}_{type}_{cluster}_{timestamp}.json`

**List backups:**
```bash
escmd list-backups
escmd list-backups --name manual_template
escmd list-backups --type component
```

**Manual backup:**
```bash
escmd template-backup manual_template -t component
```

**Restore:**
```bash
escmd template-restore --backup-file ~/.escmd/template_backups/manual_template_component_20231213_143022.json
```

## Best Practices

1. **Always test first:**
   ```bash
   escmd template-modify my_template ... --dry-run
   ```

2. **Verify changes:**
   ```bash
   escmd template my_template --format json
   ```

3. **Use specific host patterns:**
   ```bash
   # Good
   -v "sjc01-c01-ess05-*,sjc01-c02-ess04-*"
   
   # Avoid
   -v "*"
   ```

4. **Check template usage:**
   ```bash
   escmd template-usage
   ```

5. **Keep backups organized:**
   - Use `--backup-dir` for different environments
   - Document important changes
   - Clean up old backups periodically

## Error Handling

| Error | Solution |
|-------|----------|
| Template not found | Check name with `escmd templates` |
| Invalid field path | Check structure with `escmd template <name>` |
| Permission denied | Verify Elasticsearch permissions |
| Backup failed | Check directory permissions |

## Recovery

If something goes wrong:

1. **List recent backups:**
   ```bash
   escmd list-backups --name <template_name>
   ```

2. **Restore from backup:**
   ```bash
   escmd template-restore --backup-file <backup_path>
   ```

3. **Verify restoration:**
   ```bash
   escmd template <template_name>
   ```
