"""
Secure password management for ESCMD.
Handles encryption, decryption, and session caching of passwords.
"""

import os
import json
import time
import base64
import getpass
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from rich.console import Console
from rich.prompt import Prompt, Confirm


class PasswordManager:
    """Manages encrypted password storage and session caching for ESCMD."""

    def __init__(self, config_file: str = "escmd.json"):
        self.config_file = config_file
        self.console = Console()

        # Session cache - stored in memory only
        self._session_cache: Dict[str, str] = {}
        self._cache_timestamp = time.time()
        self._session_timeout = 3600  # 1 hour default

        # Encryption components
        self._fernet = None
        self._master_key = None

        # Load existing configuration
        self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from escmd.json."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to escmd.json."""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def _get_master_key(self) -> str:
        """Get or create master encryption key."""
        # Try environment variable first (most secure)
        env_key = os.environ.get('ESCMD_MASTER_KEY')
        if env_key:
            return env_key

        # Try config file
        config = self._load_config()
        security_section = config.get('security', {})

        if 'master_key' in security_section:
            return security_section['master_key']

        # Generate new master key
        return self._generate_master_key()

    def _generate_master_key(self) -> str:
        """Generate a new master encryption key."""
        # Generate a random key
        key = Fernet.generate_key()
        key_str = key.decode('utf-8')

        # Save to config if not using environment variable
        if not os.environ.get('ESCMD_MASTER_KEY'):
            config = self._load_config()
            if 'security' not in config:
                config['security'] = {}

            # Check if there are existing encrypted passwords that will become invalid
            existing_passwords = config.get('security', {}).get('encrypted_passwords', {})

            config['security']['master_key'] = key_str
            self._save_config(config)

            self.console.print("🔑 [yellow]Generated new master encryption key and saved to escmd.json[/yellow]")

            if existing_passwords:
                self.console.print("🔶  [red]WARNING: Existing encrypted passwords will be INVALID with this new key![/red]")
                self.console.print(f"� [yellow]Found {len(existing_passwords)} encrypted passwords that need to be re-stored[/yellow]")
                self.console.print("🔄 [yellow]You will need to re-store your passwords with: ./escmd.py store-password[/yellow]")

            self.console.print("�💡 [cyan]For better security, run: ./escmd.py generate-master-key --show-setup[/cyan]")
            self.console.print("   [dim]This will help you set up ESCMD_MASTER_KEY environment variable[/dim]")

        return key_str

    def _get_fernet(self) -> Fernet:
        """Get initialized Fernet instance."""
        if self._fernet is None:
            master_key = self._get_master_key()
            # If master_key is from environment or newly generated, use it directly
            if len(master_key) == 44 and master_key.endswith('='):  # Standard Fernet key format
                key = master_key.encode('utf-8')
            else:
                # Derive key from password/passphrase
                key = self._derive_key_from_password(master_key)

            self._fernet = Fernet(key)

        return self._fernet

    def _derive_key_from_password(self, password: str, salt: bytes = None) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        if salt is None:
            salt = b'escmd_salt_2025'  # Static salt for simplicity, could be randomized

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        return key

    def _is_session_valid(self) -> bool:
        """Check if current session cache is still valid."""
        return (time.time() - self._cache_timestamp) < self._session_timeout

    def _clear_session_cache(self) -> None:
        """Clear the session cache."""
        self._session_cache.clear()
        self._cache_timestamp = time.time()

    def store_password(self, environment: str = "global", password: str = None, username: str = None) -> bool:
        """
        Store an encrypted password for an environment and optionally a specific username.

        Args:
            environment: Environment name (e.g., 'global', 'prod', 'lab', 'default')
                        Defaults to 'global' for single-user-across-all-clusters workflow
            password: Password to store (will prompt if not provided)
            username: Optional username to associate with this password (e.g., 'kibana_system', 'devin.acosta')
                     If provided, creates environment.username key (e.g., 'prod.kibana_system')

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Determine storage key
            if username:
                storage_key = f"{environment}.{username}"
                display_name = f"'{username}' in '{environment}' environment"
            else:
                storage_key = environment
                display_name = f"'{environment}' environment"

            # Get password if not provided
            if password is None:
                password = getpass.getpass(f"Enter password for {display_name}: ")

                # Confirm password
                confirm_password = getpass.getpass("Confirm password: ")
                if password != confirm_password:
                    self.console.print("❌ [red]Passwords don't match![/red]")
                    return False

            # Encrypt password
            fernet = self._get_fernet()
            encrypted_password = fernet.encrypt(password.encode('utf-8'))
            encrypted_b64 = base64.urlsafe_b64encode(encrypted_password).decode('utf-8')

            # Save to config
            config = self._load_config()
            if 'security' not in config:
                config['security'] = {}
            if 'encrypted_passwords' not in config['security']:
                config['security']['encrypted_passwords'] = {}

            config['security']['encrypted_passwords'][storage_key] = encrypted_b64
            self._save_config(config)

            # Add to session cache
            self._session_cache[storage_key] = password
            self._cache_timestamp = time.time()

            self.console.print(f"✅ [green]Password for {display_name} stored and encrypted successfully[/green]")

            # Show usage hint
            if username:
                self.console.print(f"💡 [cyan]Use with: servers that have env '{environment}' and elastic_username '{username}'[/cyan]")
            else:
                self.console.print(f"💡 [cyan]Use with: servers in '{environment}' environment or as global fallback[/cyan]")

            return True

        except Exception as e:
            self.console.print(f"❌ [red]Failed to store password: {e}[/red]")
            return False

    def get_password(self, environment: str = "global", username: str = None) -> Optional[str]:
        """
        Retrieve password for an environment and optionally a specific username.

        Args:
            environment: Environment name to get password for
                        Defaults to 'global' for single-user workflow
            username: Optional username to look for (tries environment.username first)

        Returns:
            str: Decrypted password or None if not found
        """
        try:
            # Priority order for password lookup:
            # 1. Specific environment.username (e.g., "prod.kibana_system")
            # 2. Environment only (e.g., "prod")
            # 3. Global environment
            # 4. Default environment (backward compatibility)

            lookup_keys = []

            # Add specific environment.username if username provided
            if username:
                lookup_keys.append(f"{environment}.{username}")

            # Add environment-only lookup
            lookup_keys.append(environment)

            # Add fallback lookups (only if not already added)
            if environment != "global":
                lookup_keys.append("global")
            if environment != "default":
                lookup_keys.append("default")

            # Check session cache first for all keys
            if self._is_session_valid():
                for key in lookup_keys:
                    if key in self._session_cache:
                        return self._session_cache[key]

            # Load from encrypted storage
            config = self._load_config()
            encrypted_passwords = config.get('security', {}).get('encrypted_passwords', {})

            # Try each lookup key in priority order
            for key in lookup_keys:
                if key in encrypted_passwords:
                    # Decrypt password
                    fernet = self._get_fernet()
                    encrypted_b64 = encrypted_passwords[key]
                    encrypted_password = base64.urlsafe_b64decode(encrypted_b64.encode('utf-8'))
                    decrypted_password = fernet.decrypt(encrypted_password).decode('utf-8')

                    # Cache in session with the original lookup key
                    self._session_cache[key] = decrypted_password
                    self._cache_timestamp = time.time()

                    return decrypted_password

            # No password found
            return None

        except Exception as e:
            lookup_desc = f"{environment}.{username}" if username else environment

            # Provide more helpful error messages based on the exception type
            if "InvalidToken" in str(type(e)) or "decrypt" in str(e).lower():
                self.console.print(f"🔶  [yellow]Failed to decrypt password for '{lookup_desc}'[/yellow]")
                self.console.print("💡 [cyan]This usually means the encryption key has changed. Try one of these solutions:[/cyan]")
                self.console.print("   [dim]1. Re-store the password: ./escmd.py store-password[/dim]")
                self.console.print("   [dim]2. If you have the original ESCMD_MASTER_KEY, set it as environment variable[/dim]")
                self.console.print("   [dim]3. Or clear all passwords and start fresh: ./escmd.py clear-session[/dim]")
            else:
                self.console.print(f"🔶  [yellow]Failed to decrypt password for '{lookup_desc}': {e}[/yellow]")
            return None

    def list_stored_passwords(self, return_keys: bool = False) -> list:
        """
        List all stored password environments.

        Args:
            return_keys: If True, return list of keys instead of printing

        Returns:
            list: List of stored password keys if return_keys=True, otherwise empty list
        """
        config = self._load_config()
        encrypted_passwords = config.get('security', {}).get('encrypted_passwords', {})

        if return_keys:
            return list(encrypted_passwords.keys())

        if not encrypted_passwords:
            self.console.print("📝 [yellow]No stored passwords found[/yellow]")
            return []

        self.console.print("🔐 [cyan]Stored password environments:[/cyan]")
        for env in encrypted_passwords.keys():
            # Check if in session cache
            cached = "💾" if env in self._session_cache and self._is_session_valid() else "  "
            self.console.print(f"  {cached} {env}")

        if self._session_cache and self._is_session_valid():
            remaining_time = int(self._session_timeout - (time.time() - self._cache_timestamp))
            self.console.print(f"\n💾 Session cache active ({remaining_time}s remaining)")

        return list(encrypted_passwords.keys())

    def remove_password(self, environment: str) -> bool:
        """
        Remove stored password for an environment.

        Args:
            environment: Environment name to remove

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            config = self._load_config()
            encrypted_passwords = config.get('security', {}).get('encrypted_passwords', {})

            if environment not in encrypted_passwords:
                self.console.print(f"🔶  [yellow]No stored password found for '{environment}'[/yellow]")
                return False

            # Confirm deletion
            if not Confirm.ask(f"Remove stored password for '{environment}'?"):
                self.console.print("❌ [red]Operation cancelled[/red]")
                return False

            # Remove from config
            del encrypted_passwords[environment]
            self._save_config(config)

            # Remove from session cache
            if environment in self._session_cache:
                del self._session_cache[environment]

            self.console.print(f"✅ [green]Password for '{environment}' removed successfully[/green]")
            return True

        except Exception as e:
            self.console.print(f"❌ [red]Failed to remove password: {e}[/red]")
            return False

    def clear_session(self) -> None:
        """Clear the current session cache."""
        self._clear_session_cache()
        self.console.print("🧹 [green]Session cache cleared[/green]")

    def set_session_timeout(self, timeout_seconds: int) -> None:
        """Set session timeout in seconds."""
        self._session_timeout = max(60, timeout_seconds)  # Minimum 1 minute
        self.console.print(f"🕐 [green]Session timeout set to {self._session_timeout} seconds[/green]")

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
        if not self._session_cache:
            return {"active": False}

        remaining_time = max(0, int(self._session_timeout - (time.time() - self._cache_timestamp)))
        return {
            "active": self._is_session_valid(),
            "cached_environments": list(self._session_cache.keys()),
            "remaining_time": remaining_time,
            "timeout": self._session_timeout
        }


# Global instance for easy access
password_manager = PasswordManager()
