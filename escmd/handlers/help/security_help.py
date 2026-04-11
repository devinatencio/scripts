"""
Help content for security commands.
"""

from .base_help_content import BaseHelpContent


class SecurityHelpContent(BaseHelpContent):
    """Help content for security commands."""

    def get_topic_name(self) -> str:
        """Get the topic name for security help."""
        return "security"

    def get_topic_description(self) -> str:
        """Get the topic description for security help."""
        return "Password management and security features"

    def show_help(self) -> None:
        """Show detailed help for security commands."""
        help_styles, border_style = self._get_theme_styles()

        from rich.panel import Panel
        from rich.table import Table

        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=40)
        commands_table.add_column(style=help_styles.get('description', 'white'))

        commands_table.add_row("store-password [environment]", "Store encrypted password for environment")
        commands_table.add_row("store-password [env] --username <user>", "Store password for specific user")
        commands_table.add_row("list-stored-passwords", "List all stored encrypted passwords")
        commands_table.add_row("list-stored-passwords --decrypt", "Show decrypted passwords (with security warning)")
        commands_table.add_row("remove-stored-password <environment>", "Remove stored password")
        commands_table.add_row("clear-session", "Clear current password session cache")
        commands_table.add_row("session-info", "Show current session information")
        commands_table.add_row("set-session-timeout <minutes>", "Set session timeout duration")
        commands_table.add_row("generate-master-key", "Generate new encryption master key")
        commands_table.add_row("generate-master-key --show-setup", "Show environment variable setup")
        commands_table.add_row("migrate-to-env-key", "Migrate file-based key to environment")
        commands_table.add_row(
            "rotate-master-key",
            "Back up escmd.json, new encryption key, re-encrypt all stored passwords",
        )

        # Basic usage examples
        basic_examples = Table.grid(padding=(0, 3))
        basic_examples.add_column(style=help_styles.get('example', 'bold green'), min_width=40)
        basic_examples.add_column(style=help_styles.get('description', 'dim white'))

        basic_examples.add_row("Store global password:", "./escmd.py store-password")
        basic_examples.add_row("Store for environment:", "./escmd.py store-password prod")
        basic_examples.add_row("Store for user:", "./escmd.py store-password prod --username kibana")
        basic_examples.add_row("List passwords:", "./escmd.py list-stored-passwords")
        basic_examples.add_row("Show decrypted:", "./escmd.py list-stored-passwords --decrypt")
        basic_examples.add_row("Check session:", "./escmd.py session-info")
        basic_examples.add_row("Clear cache:", "./escmd.py clear-session")

        # Advanced examples
        advanced_examples = Table.grid(padding=(0, 3))
        advanced_examples.add_column(style=help_styles.get('command', 'bold yellow'), min_width=40)
        advanced_examples.add_column(style=help_styles.get('description', 'dim white'))

        advanced_examples.add_row("Generate new master key:", "./escmd.py generate-master-key")
        advanced_examples.add_row("Setup environment key:", "./escmd.py generate-master-key --show-setup")
        advanced_examples.add_row("Migrate to env variable:", "./escmd.py migrate-to-env-key")
        advanced_examples.add_row("Rotate master key (backup + re-encrypt):", "./escmd.py rotate-master-key")
        advanced_examples.add_row("Set session timeout:", "./escmd.py set-session-timeout 120")

        # Configuration examples
        config_examples = Table.grid(padding=(0, 3))
        config_examples.add_column(style=help_styles.get('section_header', 'bold magenta'), min_width=40)
        config_examples.add_column(style=help_styles.get('description', 'dim white'))

        config_examples.add_row("Set global username:", "elastic_username: your.username")
        config_examples.add_row("Set environment variable:", "export ESCMD_MASTER_KEY='your_key'")
        config_examples.add_row("Use env password:", "use_env_password: true")
        config_examples.add_row("Config file location:", "~/.escmd/escmd.yml or ./escmd.yml")

        # Workflow examples
        workflow_examples = Table.grid(padding=(0, 3))
        workflow_examples.add_column(style=help_styles.get('command', 'bold cyan'), min_width=40)
        workflow_examples.add_column(style=help_styles.get('description', 'dim white'))

        workflow_examples.add_row("Single User Setup:", "1. Set elastic_username in config")
        workflow_examples.add_row("", "2. Run: ./escmd.py store-password")
        workflow_examples.add_row("", "3. All commands use encrypted password")
        workflow_examples.add_row("", "")
        workflow_examples.add_row("Multi-User Setup:", "1. Configure per-environment users")
        workflow_examples.add_row("", "2. Store: ./escmd.py store-password prod --username kibana")
        workflow_examples.add_row("", "3. Store: ./escmd.py store-password lab --username elastic")
        workflow_examples.add_row("", "4. ESCMD auto-selects correct password")

        # Password resolution priority
        priority_examples = Table.grid(padding=(0, 3))
        priority_examples.add_column(style=help_styles.get('command', 'bold blue'), min_width=40)
        priority_examples.add_column(style=help_styles.get('description', 'dim white'))

        priority_examples.add_row("1. environment.username", "prod.kibana_system (highest priority)")
        priority_examples.add_row("2. environment", "prod (environment fallback)")
        priority_examples.add_row("3. global.username", "global.devin.acosta (user fallback)")
        priority_examples.add_row("4. global", "global (global fallback)")
        priority_examples.add_row("5. explicit password", "elastic_password in config")
        priority_examples.add_row("6. environment variable", "use_env_password: true")

        # Security features
        security_features = Table.grid(padding=(0, 3))
        security_features.add_column(style=help_styles.get('section_header', 'bold red'), min_width=40)
        security_features.add_column(style=help_styles.get('description', 'dim white'))

        security_features.add_row("🔐 AES-128 encryption", "Fernet encryption with HMAC authentication")
        security_features.add_row("🔑 Master key options", "File-based or environment variable")
        security_features.add_row("💾 Session caching", "Passwords cached in memory (1 hour default)")
        security_features.add_row("🔄 Automatic expiry", "Sessions expire and require re-authentication")
        security_features.add_row("👥 Multi-user support", "Per-user, per-environment passwords")
        security_features.add_row("🔐 No disk storage", "Decrypted passwords never written to disk")

        # Troubleshooting
        troubleshooting = Table.grid(padding=(0, 3))
        troubleshooting.add_column(style=help_styles.get('command', 'bold bright_yellow'), min_width=40)
        troubleshooting.add_column(style=help_styles.get('description', 'dim white'))

        troubleshooting.add_row("Failed to decrypt password:", "1. Check ESCMD_MASTER_KEY")
        troubleshooting.add_row("", "2. Re-store password: ./escmd.py store-password")
        troubleshooting.add_row("", "3. Clear session: ./escmd.py clear-session")
        troubleshooting.add_row("Master key missing:", "Run: ./escmd.py generate-master-key")
        troubleshooting.add_row("Session expired:", "Re-run command to re-authenticate")
        troubleshooting.add_row("Wrong username/password:", "Check env/username in server config")

        # Display all sections using theme system
        self.console.print(Panel(
            commands_table,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🔐 Security Commands[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            basic_examples,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🚀 Basic Usage Examples[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            advanced_examples,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🔩 Advanced Management[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            config_examples,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]📝 Configuration Options[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            workflow_examples,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🔄 Recommended Workflows[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            priority_examples,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🎯 Password Resolution Priority[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            security_features,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🔐 Security Features[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
        self.console.print(Panel(
            troubleshooting,
            title=f"[{help_styles.get('section_header', 'bold cyan')}]🔧 Troubleshooting[/{help_styles.get('section_header', 'bold cyan')}]",
            border_style=border_style,
            padding=(1, 2)
        ))

        print()
