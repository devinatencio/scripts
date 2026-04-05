# ESCMD Password Management

ESCMD now includes advanced password management with encryption and session caching to enhance security while maintaining usability.

## Overview

The password management system provides:
- **Encrypted Storage**: Passwords are encrypted using Fernet (AES 128 + HMAC SHA256)
- **Session Caching**: Decrypted passwords are cached in memory for the session duration
- **Multiple Environments**: Store different passwords for different environments (prod, lab, ops, etc.)
- **🆕 Multi-User Support**: Store different passwords for different users within the same environment
- **Backward Compatibility**: All existing authentication methods continue to work

## Password Resolution Priority

When ESCMD needs to authenticate with an Elasticsearch cluster, it tries to find passwords in this order:

1. **Direct password reference** (`elastic_password_ref`)
2. **🆕 Encrypted stored password** (new secure method)
   - **2a.** **Environment + Username combination** (e.g., `prod.kibana_system`, `lab.devin.acosta`)  
   - **2b.** Environment-specific (e.g., `prod`, `lab`)  
   - **2c.** **Global + Username combination** (e.g., `global.devin.acosta`)
   - **2d.** **Global password** (recommended for single-user setups)
   - **2e.** Default password (backward compatibility)
3. **Environment-based password** (`use_env_password=True`)
4. **Traditional explicit password** (`elastic_password`)
5. **Default password from settings** (`elastic_password` in settings section)

## Commands

### Store Password
```bash
# Store global password (recommended for single-user setups)
./escmd.py store-password

# Store password for specific environment  
./escmd.py store-password prod
./escmd.py store-password lab
./escmd.py store-password ops

# 🆕 Store password for specific user in an environment (multi-user support)
./escmd.py store-password prod --username kibana_system
./escmd.py store-password prod --username devin.acosta
./escmd.py store-password lab --username elastic
./escmd.py store-password global --username admin
```

The command will prompt you securely for the password (no echo to terminal).

**Recommended workflow for single users:**
1. Set `elastic_username: your.username` in escmd.yml settings
2. Run `./escmd.py store-password` (creates global encrypted password)
3. All commands automatically use your credentials across all clusters

**🆕 Recommended workflow for multi-user environments:**
1. Configure `env` and `elastic_username` in your elastic_servers.yml
2. Store passwords for each user: `./escmd.py store-password prod --username kibana_system`
3. ESCMD automatically matches environment + username for authentication

### List Stored Passwords
```bash
# Show all stored password environments
./escmd.py list-stored-passwords

# Show decrypted passwords (with security warning)
./escmd.py list-stored-passwords --decrypt
```

Example output (without --decrypt):
```
╭─────────────────────── Password Storage (6 entries) ────────────────────────╮
│                        Stored Password Environments                         │
│ ┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓ │
│ ┃ Environment           ┃ Username                     ┃ Type             ┃ │
│ ┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩ │
│ │ biz                   │ kibana_system                │ User             │ │
│ │ eu                    │ kibana_system                │ User             │ │
│ │ prod                  │ kibana_system                │ User             │ │
│ └───────────────────────┴──────────────────────────────┴──────────────────┘ │
╰─────────────────────────────────────────────────────────────────────────────╯
```

Example output (with --decrypt):
```bash
# Security warning is shown first
╭────────────────────── 🔐 Password Decryption Warning ───────────────────────╮
│                                                                             │
│  ⚠️  SECURITY WARNING ⚠️                                                      │
│                                                                             │
│  You are about to display decrypted passwords on screen!                    │
│  • Make sure no one else can see your terminal                              │
│  • Consider clearing your terminal history afterwards                       │
│  • Passwords will be shown in full without masking                          │
│                                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯

Continue with decryption? [y/n] (n): y

# Then the table with passwords is displayed
╭─────────────────────── Password Storage (6 entries) ────────────────────────╮
│                        Stored Password Environments                         │
│ ┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓ │
│ ┃ Environm… ┃ Username       ┃ Password                           ┃ Type  ┃ │
│ ┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩ │
│ │ biz       │ kibana_system  │ mySecretPassword123                │ User  │ │
│ │ eu        │ kibana_system  │ anotherPassword456                 │ User  │ │
│ │ prod      │ kibana_system  │ productionPass789                  │ User  │ │
│ └───────────┴────────────────┴────────────────────────────────────┴───────┘ │
╰─────────────────────────────────────────────────────────────────────────────╯
```

**Security Note**: The `--decrypt` flag will:
- Display a security warning before showing passwords
- Require user confirmation to proceed
- Show passwords in full without any masking
- Include passwords in a dedicated column between Username and Type

### Remove Stored Password
```bash
# Remove password for specific environment
./escmd.py remove-stored-password prod
```

### Session Management
```bash
# Show current session information
./escmd.py session-info

# Clear current session cache
./escmd.py clear-session

# Set session timeout (in seconds)
./escmd.py set-session-timeout 7200  # 2 hours
```

### 🆕 Master Key Management
```bash
# Generate a new master key for environment variable setup
./escmd.py generate-master-key --show-setup

# Migrate existing file-based key to environment variable
./escmd.py migrate-to-env-key

# Generate key without detailed instructions
./escmd.py generate-master-key
```

## Configuration Integration

### Method 1: Global Password (Recommended for Single Users)
```yaml
# In your escmd.yml settings section
settings:
  elastic_username: devin.acosta  # Your username for all clusters
  # ... other settings
```
```bash
# Store your global password once
./escmd.py store-password
```

**Result**: All clusters automatically use `devin.acosta` + your encrypted password

### Method 2: Multi-User Environments (🆕 New Feature)
For environments where different users access the same Elasticsearch clusters:

```yaml
# In your elastic_servers.yml
servers:
  - name: production-kibana
    hostname: prod-es-01.company.com
    port: 9200
    env: prod                    # Environment identifier
    elastic_username: kibana_system
    
  - name: production-admin  
    hostname: prod-es-01.company.com
    port: 9200
    env: prod                    # Same environment, different user
    elastic_username: devin.acosta
    
  - name: lab-kibana
    hostname: lab-es-01.company.com
    port: 9200
    env: lab
    elastic_username: kibana_system
```

```bash
# Store passwords for each user in each environment
./escmd.py store-password prod --username kibana_system
./escmd.py store-password prod --username devin.acosta
./escmd.py store-password lab --username kibana_system

# Optional: Store environment fallback (used if specific user not found)
./escmd.py store-password prod
./escmd.py store-password lab
```

**Result**: ESCMD automatically matches `env` + `elastic_username` to find the right password

### Method 3: Environment-Specific Passwords (Legacy)
```yaml
# In your elastic_servers.yml
servers:
  - name: production
    config_password: prod  # This will use encrypted "prod" password
    hostname: prod-es-01.company.com
    port: 9200
    use_ssl: true
    elastic_authentication: true
    elastic_username: kibana_system
```
```bash
./escmd.py store-password prod
```

### Method 4: Mixed Approach (Recommended for Complex Setups)
Store both global and environment-specific passwords, with multi-user support:
```bash
./escmd.py store-password                                    # Global fallback for all environments
./escmd.py store-password global --username devin.acosta    # Global password for specific user
./escmd.py store-password prod --username kibana_system     # Production kibana service user
./escmd.py store-password prod --username devin.acosta      # Production personal user
./escmd.py store-password lab --username elastic            # Lab environment elastic user
./escmd.py store-password lab                               # Lab environment fallback
```

**Password Resolution Example:**
- Server with `env: prod, elastic_username: kibana_system` → Uses `prod.kibana_system`
- Server with `env: lab, elastic_username: unknown_user` → Falls back to `lab` environment password
- Server with `env: staging, elastic_username: devin.acosta` → Falls back to `global.devin.acosta`
- Server with `env: new_env, elastic_username: any_user` → Falls back to `global` password

## Security Features

### Encryption
- **Algorithm**: Fernet (AES 128 in CBC mode + HMAC SHA256)
- **Key Management**: Master key stored in `escmd.json` or `ESCMD_MASTER_KEY` environment variable
- **Authentication**: Built-in message authentication prevents tampering

### Session Caching
- **Memory Only**: Decrypted passwords never touch disk during normal operation
- **Automatic Expiry**: Cache expires after configurable timeout (default: 1 hour)
- **Manual Control**: Clear cache manually with `clear-session` command

### Environment Variable Support
For enhanced security, set the master key as an environment variable:
```bash
# Generate a new key and get setup instructions
./escmd.py generate-master-key --show-setup

# Or migrate existing file-based key to environment variable
./escmd.py migrate-to-env-key
```

**Setting up the environment variable:**
```bash
# Set the environment variable (replace with your actual key)
export ESCMD_MASTER_KEY="your_base64_encoded_key_here"

# Add to your shell profile for persistence
echo 'export ESCMD_MASTER_KEY="your_key_here"' >> ~/.zshrc
source ~/.zshrc

# Remove master_key from escmd.yml (optional but recommended)
# Edit escmd.yml and delete the 'master_key' line from security section
```

**Security Benefits:**
- **🔐 Defense in Depth**: Even if `escmd.yml` is compromised, passwords remain secure
- **🚀 No File Storage**: Encryption key never stored on disk
- **🔄 Easy Rotation**: Change environment variable to rotate keys
- **👥 Team Security**: Different team members can use different keys

## Storage Format

Encrypted passwords are stored in `escmd.yml`:
```json
{
    "current_cluster": "dev",
    "display_theme": "cyberpunk",
    "security": {
        "master_key": "base64_encoded_encryption_key",
        "encrypted_passwords": {
            "global": "encrypted_global_password_data",
            "global.devin.acosta": "encrypted_user_global_password",
            "prod": "encrypted_prod_env_password_data",
            "prod.kibana_system": "encrypted_prod_kibana_password",
            "prod.devin.acosta": "encrypted_prod_devin_password",
            "lab.elastic": "encrypted_lab_elastic_password"
        }
    }
}
```

**Key Format:**
- `environment` - Environment-wide password (e.g., `prod`, `lab`)
- `environment.username` - User-specific password (e.g., `prod.kibana_system`)
- `global` - Global fallback password  
- `global.username` - Global user-specific password

## Migration from Plain Text

If you currently have passwords in your YAML configuration files:

1. **Store the password securely**:
   ```bash
   ./escmd.py store-password prod
   # Enter your current password when prompted
   ```

2. **Remove from YAML file**:
   ```yaml
   # Before
   elastic_password: "my_plain_text_password"
   
   # After (remove the line entirely)
   # Password will be automatically retrieved from encrypted storage
   ```

3. **Test the connection**:
   ```bash
   ./escmd.py health -l your_cluster
   ```

## Best Practices

### Security
1. **🥇 Use Environment Variables**: Set `ESCMD_MASTER_KEY` environment variable instead of storing in file
2. **🔄 Regular Key Rotation**: Periodically regenerate master key and re-encrypt passwords
3. **🔒 Secure Storage**: Ensure `escmd.yml` has appropriate file permissions (600)
4. **⏰ Session Management**: Use appropriate session timeouts for your security requirements
5. **👥 Team Isolation**: Use different master keys for different teams/environments

### Operational
1. **Backup**: Backup your `escmd.json` file (it contains encrypted passwords)
2. **Environment Separation**: Use different passwords for different environments
3. **Documentation**: Document which environments use which authentication method
4. **Testing**: Test password retrieval after storage to ensure encryption/decryption works

## Troubleshooting

### Common Issues

**"Failed to decrypt password"**
- Check if `ESCMD_MASTER_KEY` environment variable changed
- Verify `escmd.json` file integrity
- If master key was lost or regenerated, re-store passwords with `./escmd.py store-password`
- Use `./escmd.py list-stored-passwords` to see which passwords need to be re-stored

**"Generated new master encryption key and saved to escmd.json"**
- This happens when no master key is found (missing from both `escmd.json` and `ESCMD_MASTER_KEY`)
- If you see this unexpectedly, it means the original key was lost
- All existing encrypted passwords will need to be re-stored
- Consider setting up `ESCMD_MASTER_KEY` environment variable to prevent this in the future

**"No stored passwords found"**
- Run `./escmd.py list-stored-passwords` to verify storage
- Check file permissions on `escmd.yml`

**"Wrong username or password"** (Multi-user setups)
- Verify the username with `./escmd.py list-stored-passwords`
- Check that `env` and `elastic_username` are set correctly in your server configuration
- Test password resolution priority: `environment.username` → `environment` → `global.username` → `global`

**"Session cache not working"**
- Verify session hasn't expired with `./escmd.py session-info`
- Check if session timeout is appropriate for your workflow

### Debug Commands
```bash
# Show detailed session information
./escmd.py session-info

# List all authentication methods available
./escmd.py list-stored-passwords

# Test password storage and retrieval
python3 test_password_manager.py
```

## Implementation Details

### Fernet Encryption
- **Symmetric encryption**: Same key encrypts and decrypts
- **Authenticated encryption**: Prevents tampering with encrypted data
- **Time-based tokens**: Could be extended to include expiration timestamps
- **URL-safe base64**: Safe for JSON storage and transmission

### Session Caching Strategy
1. **First Access**: Password decrypted from storage and cached in memory
2. **Subsequent Access**: Password retrieved from memory cache
3. **Cache Expiry**: After timeout, password must be decrypted again from storage
4. **Manual Clear**: Cache can be cleared manually for security

This approach provides excellent security (passwords encrypted at rest) with great usability (no repeated password prompts during active sessions).
