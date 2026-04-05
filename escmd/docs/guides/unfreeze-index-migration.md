# Unfreeze Index Script Migration Guide

## Overview

The `unfreeze_index.py` script has been updated (v2.0.0) to integrate with the unified ESCMD configuration system. This allows it to work seamlessly with the main `escmd.py` application using shared configuration files and encrypted password management.

## Key Changes

### 1. Unified Configuration System
- **Before**: Used standalone `elastic_servers.yml` in the `unfreeze_index/` directory
- **After**: Uses the main `escmd.yml` and `elastic_servers.yml` files in the root directory
- **Benefit**: Single source of truth for all server configurations

### 2. Encrypted Password Management
- **Before**: Passwords stored in plain text in YAML files or prompted every time
- **After**: Integrates with the encrypted password storage system (`escmd.json`)
- **Benefit**: Secure password storage with session caching

### 3. Smart Location Matching
- **Before**: Required exact server names from configuration
- **After**: Intelligent matching with fallback logic:
  - First tries exact match (e.g., `server5` → `server5` if exists)
  - Then tries with `-c01` suffix (e.g., `server5` → `server14`)
- **Benefit**: More user-friendly location specification

### 4. Enhanced Error Handling
- **Before**: Basic error messages
- **After**: Detailed error messages with helpful suggestions for password issues
- **Benefit**: Better troubleshooting experience

## Migration Steps

### 1. Move the Script
The script has been moved from `unfreeze_index/unfreeze_index.py` to the main directory as `unfreeze_index.py`.

```bash
# Script is now located at:
./unfreeze_index.py
```

### 2. Store Passwords (if using authentication)
If your servers require authentication, you'll need to store encrypted passwords:

```bash
# Store password for a specific environment
./escmd.py store-password prod

# Store password for a specific server environment
./escmd.py store-password biz

# List stored passwords
./escmd.py list-stored-passwords
```

### 3. Verify Server Configuration
Ensure your servers are properly defined in `elastic_servers.yml`. The script will now look for servers by name with fallback logic.

Example configuration in `elastic_servers.yml`:
```yaml
servers:
- name: server14
  hostname: 192.168.0.89
  port: 9201
  use_ssl: true
  elastic_authentication: true
  config_password: prod  # References stored password
  
- name: server6
  hostname: 192.168.0.54
  port: 9200
  use_ssl: false
  elastic_authentication: false
```

## Usage Examples

### Basic Usage (Same as Before)
```bash
# Unfreeze indices for specific locations and components
./unfreeze_index.py -l server5,server6 -c filebeat,metricbeat -s 2024.12.01 -e 2024.12.07
```

### New Smart Location Matching
```bash
# These commands now work with fallback logic:

# If 'server5' doesn't exist, it will try 'server14'
./unfreeze_index.py -l server5 -c filebeat -d 2024.12.25

# If 'server15' doesn't exist, it will try 'server16'  
./unfreeze_index.py -l server15 -c metricbeat -d 2024.12.25

# Mixed exact and fallback matching
./unfreeze_index.py -l server5,server6,server1 -c filebeat -d 2024.12.25
```

### Password Management
```bash
# If you haven't stored passwords, the script will prompt with helpful messages
./unfreeze_index.py -l server5 -c filebeat -d 2024.12.25

# Or prompt for password interactively (bypasses stored passwords)
./unfreeze_index.py -l server5 -c filebeat -d 2024.12.25 -p
```

## Command Line Arguments

All existing arguments remain the same:

| Argument | Description | Required | Example |
|----------|-------------|----------|---------|
| `-l, --locations` | Comma-separated locations | Yes | `server5,server6` |
| `-c, --component` | Comma-separated components | Yes | `filebeat,metricbeat` |
| `-d, --date` | Specific date | No* | `2024.12.25` |
| `-s, --start` | Start date | No* | `2024.12.01` |
| `-e, --end` | End date | No* | `2024.12.07` |
| `-p, --password` | Prompt for password | No | (flag only) |

*Either `-d` or `-s` is required

## Port Scanning Behavior

The script maintains its original behavior of scanning multiple ports:
- 9200 (standard Elasticsearch port)
- 9201 (common secondary port)
- 9202 (common tertiary port) 
- 9203 (common quaternary port)

This happens regardless of the port specified in `elastic_servers.yml`, ensuring comprehensive index discovery.

## Troubleshooting

### Server Not Found Errors
```
ERROR: No server configuration found for location 'myserver' or 'myserver-c01'
```
**Solution**: Check that the server is defined in `elastic_servers.yml` with the correct name.

### Password Decryption Errors
```
Failed to decrypt password for 'prod'
```
**Solutions**:
1. Re-store the password: `./escmd.py store-password prod`
2. Check if `ESCMD_MASTER_KEY` environment variable is set correctly
3. Clear session and re-authenticate: `./escmd.py clear-session`

### Connection Errors
```
Error connecting to server5 on port 9201: ...
```
**Check**: Network connectivity, server status, and authentication credentials.

## Security Improvements

### Password Storage
- Passwords are now encrypted using Fernet symmetric encryption
- Master key can be stored in environment variable `ESCMD_MASTER_KEY` for enhanced security
- Session caching reduces password prompts

### Best Practices
1. **Environment Variable**: Set `ESCMD_MASTER_KEY` as an environment variable instead of storing in `escmd.json`
2. **Least Privilege**: Store separate passwords for different environments
3. **Session Management**: Use session timeouts to automatically clear cached passwords

## Backward Compatibility

### Breaking Changes
- Script location changed from `unfreeze_index/` to main directory
- Requires `configuration_manager.py` and `security/password_manager.py`
- Passwords must be stored using the new encrypted system

### Migration Path
1. Move to using the new script location
2. Store passwords using `./escmd.py store-password`
3. Verify server configurations in main `elastic_servers.yml`
4. Test with existing command-line arguments

## Integration with ESCMD Ecosystem

The updated script now shares:
- Configuration management with main ESCMD application
- Password encryption and session management
- Error handling patterns and user experience
- Logging and status reporting mechanisms

This integration provides a more cohesive and secure experience across all ESCMD tools.