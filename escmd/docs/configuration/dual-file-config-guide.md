# ESCMD Dual-File Configuration System

## Overview

ESCMD now supports a more robust dual-file configuration approach that separates concerns and improves maintainability, security, and operability.

## Configuration Modes

### 1. Dual-File Mode (Recommended)
- **`escmd.yml`**: Core settings, cluster groups, password management, and optional **`auth_profiles`** (named authentication presets)
- **`elastic_servers.yml`**: Server connection definitions only (may reference **`auth_profile`** instead of embedding **`elastic_username`**)

### 2. Single-File Mode (Backward Compatibility)
- **`elastic_servers.yml`**: Everything in one file (legacy approach)

### 3. Auto-Detection Mode
ESCMD automatically detects which mode to use:
- If `escmd.yml` exists → Dual-file mode
- Otherwise → Single-file mode with `elastic_servers.yml`

## File Structure

### `escmd.yml` (Main Configuration)
```yaml
# Core application settings
settings:
  health_style: dashboard
  classic_style: panel
  enable_paging: false
  paging_threshold: 50
  show_legend_panels: false
  ascii_mode: false
  themes_file: themes.yml
  connection_timeout: 30
  read_timeout: 120
  dangling_cleanup:
    max_retries: 3
    retry_delay: 5
    timeout: 60
    default_log_level: INFO
    enable_progress_bar: true
    confirmation_required: true

# Logical cluster groupings
cluster_groups:
  production:
    - server5
    - server6
  staging:
    - server7-v02
  ops:
    - server8
    - server9

# Centralized password management by environment
passwords:
  prod:
    kibana_system: "your-production-password-here"
  ops:
    kibana_system: "your-ops-password-here"
  lab:
    kibana_system: "your-lab-password-here"

# Optional: named auth presets (see "Auth profiles" below)
auth_profiles:
  kibana_service:
    elastic_username: kibana_system
  human_operator:
    elastic_username: alice.example
```

### `elastic_servers.yml` (Servers Only)
```yaml
servers:
- name: DEFAULT
  hostname: 127.0.0.1
  port: 9200
  use_ssl: false
  verify_certs: false

- name: server5
  env: prod
  hostname: server10.c01.example.com
  hostname2: server11.c01.example.com
  port: 9201
  use_ssl: true
  elastic_authentication: true
  auth_profile: kibana_service  # or elastic_username: kibana_system
  use_env_password: true  # Uses passwords.prod.kibana_system
  
- name: server8
  env: ops
  hostname: server12.elk.ops.example.com
  hostname2: server13.elk.ops.example.com
  port: 9200
  use_ssl: true
  elastic_authentication: true
  elastic_username: kibana_system
  elastic_password_ref: ops.kibana_system  # Direct reference

- name: server9
  env: lab
  hostname: lab-es.example.com
  port: 9200
  use_ssl: true
  elastic_authentication: true
  auth_profile: human_operator
  use_env_password: true
  # Resolved username comes from auth_profiles.human_operator.elastic_username;
  # password lookup uses passwords.lab.<that_username> when stored per user.
```

## Auth profiles

**Auth profiles** separate *which kind of account* a cluster needs from *your* username string. Shared **`elastic_servers.yml`** can list stable profile names; each person or team defines **`auth_profiles`** in **`escmd.yml`** (or a file pointed to by **`ESCMD_MAIN_CONFIG`**) so credentials stay local and portable.

### Defining profiles (main config only in dual-file mode)

In **`escmd.yml`**, add a top-level **`auth_profiles`** map. Each key is a profile name; each value is a mapping. Supported today:

| Field | Purpose |
|-------|---------|
| **`elastic_username`** | Username used for HTTP basic auth and for **`env` + username** password lookup |

Example:

```yaml
settings:
  elastic_username: kibana_system

auth_profiles:
  kibana_service:
    elastic_username: kibana_system
  human_operator:
    elastic_username: devin.acosta
```

### Using profiles on servers

On any server entry, set **`auth_profile: <name>`** and omit **`elastic_username`** (or set **`elastic_username`** only when you need an explicit override for that host). Per-server **`elastic_username`** always wins over **`auth_profile`**.

```yaml
servers:
  - name: metrics-prod
    env: prod
    hostname: es-prod.example.com
    port: 9200
    use_ssl: true
    elastic_authentication: true
    auth_profile: kibana_service
    use_env_password: true
```

### Username resolution order

1. **`elastic_username`** on the server entry
2. **`elastic_username`** from **`auth_profiles[auth_profile]`**
3. If **`passwords[env]`** is a dict with **exactly one** username key, that username (legacy shortcut)
4. **`elastic_username`** in **`escmd.json`**
5. **`settings.elastic_username`** in **`escmd.yml`**

### Single-file mode

In legacy single-file YAML, **`auth_profiles`** lives in the **same** file as **`servers:`** (alongside **`settings`**, **`passwords`**, etc.).

### Passwords and profiles

Stored and inline passwords are resolved using the **effective** username (after the order above). For example, **`use_env_password`** with **`env: prod`** and **`auth_profile: kibana_service`** still resolves **`passwords.prod.kibana_system`** when the profile maps to **`kibana_system`**.

### Troubleshooting profiles

- **`Unknown auth_profile '…'`** — Add the name under **`auth_profiles:`** in the **main** config, or fix a typo on the server entry. Dual-file mode does **not** read **`auth_profiles`** from **`elastic_servers.yml`**.
- **Wrong user after sharing **`elastic_servers.yml`**** — Expected: update only your **`escmd.yml`** (or **`ESCMD_MAIN_CONFIG`**) **`auth_profiles`** so the shared profile name maps to your account.

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ESCMD_MAIN_CONFIG` | Path to main configuration file | `escmd.yml` |
| `ESCMD_SERVERS_CONFIG` | Path to servers configuration file | `elastic_servers.yml` |
| `ELASTIC_SERVERS_CONFIG` | Legacy single-file path (backward compatibility) | `elastic_servers.yml` |
| `ESCMD_STATE` | Path to state file | `escmd.json` |

## Password Management

The dual-file approach supports three password resolution methods:

### 1. Environment-Based (Recommended)
```yaml
# In server configuration
env: prod
elastic_username: kibana_system
use_env_password: true

# References passwords.prod.kibana_system from escmd.yml
```

### 2. Direct Reference
```yaml
# In server configuration
elastic_password_ref: ops.kibana_system

# Directly references passwords.ops.kibana_system from escmd.yml
```

### 3. Explicit Password (Legacy)
```yaml
# In server configuration
elastic_password: "actual-password-here"

# Direct password specification (not recommended for production)
```

## Migration

### From Single-File to Dual-File

Use the included migration script:
```bash
# Preview migration
python3 migrate_config.py --dry-run

# Migrate with backup
python3 migrate_config.py --backup

# Custom source file
python3 migrate_config.py --source my_config.yml --backup
```

### Manual Migration Steps

1. **Create `escmd.yml`**:
   ```bash
   # Extract settings, cluster_groups, and passwords from elastic_servers.yml
   cp elastic_servers.yml elastic_servers.yml.backup
   ```

2. **Update `elastic_servers.yml`**:
   ```bash
   # Keep only the 'servers:' section
   # Remove settings, cluster_groups, passwords sections
   ```

3. **Test the configuration**:
   ```bash
   python3 test_dual_config.py
   python3 escmd.py show-settings
   ```

## Benefits

### Security
- **Isolated Password Management**: Passwords in dedicated config file
- **Role-Based Access**: Different teams can manage different files
- **Reduced Attack Surface**: Server list corruption can't expose passwords

### Operational
- **Change Isolation**: Server changes don't risk breaking core settings
- **Better Backup/Restore**: Can backup configurations independently
- **Easier Secret Rotation**: Update passwords without touching server definitions

### Maintenance
- **Separation of Concerns**: Each file has a single responsibility
- **Simpler Validation**: Easier to validate server configs vs settings
- **Cleaner Version Control**: Better diffs and easier review

## Testing

Test your configuration with the included test suite:
```bash
python3 test_dual_config.py
```

This will verify:
- Dual-file configuration loading
- Backward compatibility with single-file
- Auto-detection functionality
- Configuration data integrity

## Troubleshooting

### Configuration Not Loading
1. Check file permissions
2. Verify YAML syntax
3. Use `python3 escmd.py show-settings` to see current config
4. Run `python3 test_dual_config.py` for diagnostics

### Password Resolution Issues
1. Verify environment matches between server and password sections
2. Check the **effective** username matches stored keys (use **`show-settings`** / **`locations`**; remember **`auth_profile`** resolves to a username from **`auth_profiles`**)
3. Ensure `use_env_password: true` or proper `elastic_password_ref`

### Auth profile issues
1. Confirm **`auth_profiles`** is in **`escmd.yml`** (dual-file), not only in **`elastic_servers.yml`**
2. Verify **`auth_profile`** on the server matches a key under **`auth_profiles:`**
3. Remove or fix unknown profile names if you see **`Unknown auth_profile`** warnings

### Migration Issues
1. Use `--dry-run` first to preview changes
2. Always use `--backup` option
3. Test with `test_dual_config.py` after migration

## Best Practices

1. **Use Environment-Based Passwords**: Prefer `use_env_password: true` over explicit passwords
2. **Organize by Environment**: Group servers by environment (prod, ops, lab, etc.)
3. **Regular Backups**: Backup both configuration files regularly
4. **Version Control**: Keep configurations in version control with proper .gitignore for sensitive data
5. **Test Changes**: Always test configuration changes with the test suite

## Example Environment Variable Setup

```bash
# For custom file locations
export ESCMD_MAIN_CONFIG="/path/to/my-escmd.yml"
export ESCMD_SERVERS_CONFIG="/path/to/my-servers.yml"
export ESCMD_STATE="/path/to/my-state.json"

# For legacy single-file mode
export ELASTIC_SERVERS_CONFIG="/path/to/legacy-config.yml"
```
