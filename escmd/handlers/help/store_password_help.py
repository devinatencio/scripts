"""
Help content for store-password command.
"""

from .base_help_content import BaseHelpContent


class StorePasswordHelpContent(BaseHelpContent):
    """Help content for store-password command."""

    def get_topic_name(self) -> str:
        return "store-password"

    def get_topic_description(self) -> str:
        return "Store an encrypted password for an environment or user"

    def show_help(self) -> None:
        """Show detailed help for store-password command."""
        help_styles, border_style = self._get_theme_styles()

        from rich.panel import Panel
        from rich.table import Table

        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style=help_styles.get('command', 'bold cyan'), min_width=44)
        commands_table.add_column(style=help_styles.get('description', 'white'))

        commands_table.add_row("store-password", "Store password for the 'global' environment (single-cluster setups)")
        commands_table.add_row("store-password <environment>", "Store password for a named environment (e.g. prod, lab)")
        commands_table.add_row("store-password <env> --username <user>", "Store password for a specific user in an environment")
        commands_table.add_row("store-password --username <user>", "Store password for a user in the global environment")
        commands_table.add_row("list-stored-passwords", "List all stored encrypted passwords")
        commands_table.add_row("list-stored-passwords --decrypt", "Show decrypted passwords (use with caution)")
        commands_table.add_row("remove-stored-password <environment>", "Remove a stored password entry")
        commands_table.add_row("generate-master-key", "Generate a new ESCMD_MASTER_KEY encryption key")
        commands_table.add_row("rotate-master-key", "Re-encrypt all stored passwords with a new master key")

        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style=help_styles.get('example', 'bold green'), min_width=44)
        examples_table.add_column(style=help_styles.get('description', 'dim white'))

        examples_table.add_row("Single cluster setup:", "./escmd.py store-password")
        examples_table.add_row("Store for prod env:", "./escmd.py store-password prod")
        examples_table.add_row("Store for lab env:", "./escmd.py store-password lab")
        examples_table.add_row("Store for specific user:", "./escmd.py store-password prod --username kibana_system")
        examples_table.add_row("Store global user:", "./escmd.py store-password --username elastic")
        examples_table.add_row("List stored passwords:", "./escmd.py list-stored-passwords")
        examples_table.add_row("Remove a password:", "./escmd.py remove-stored-password prod")
        examples_table.add_row("Generate master key:", "./escmd.py generate-master-key")
        examples_table.add_row("Rotate master key:", "./escmd.py rotate-master-key")

        # Setup workflow table
        setup_table = Table.grid(padding=(0, 3))
        setup_table.add_column(style=help_styles.get('section_header', 'bold magenta'), min_width=44)
        setup_table.add_column(style=help_styles.get('description', 'dim white'))

        setup_table.add_row("🚀 First-Time Setup:", "Get encrypted passwords working in 3 steps")
        setup_table.add_row("   Step 1 - Generate key:", "./escmd.py generate-master-key")
        setup_table.add_row("   Step 2 - Export key:", "export ESCMD_MASTER_KEY='<key from step 1>'")
        setup_table.add_row("   Step 3 - Store password:", "./escmd.py store-password")
        setup_table.add_row("   Add to shell profile:", "Add the export line to ~/.bashrc or ~/.zshrc")
        setup_table.add_row("", "")
        setup_table.add_row("🏢 Multi-Environment Setup:", "Different passwords per cluster environment")
        setup_table.add_row("   Store prod password:", "./escmd.py store-password prod --username kibana_system")
        setup_table.add_row("   Store lab password:", "./escmd.py store-password lab --username elastic")
        setup_table.add_row("   Store staging:", "./escmd.py store-password staging --username kibana_system")
        setup_table.add_row("   Verify all stored:", "./escmd.py list-stored-passwords")
        setup_table.add_row("", "")
        setup_table.add_row("🎯 Password Resolution Order:", "How ESCMD selects the right password")
        setup_table.add_row("   1. env.username", "prod.kibana_system  (most specific)")
        setup_table.add_row("   2. env", "prod")
        setup_table.add_row("   3. global.username", "global.elastic")
        setup_table.add_row("   4. global", "global  (least specific)")
        setup_table.add_row("   5. config file", "elastic_password in escmd.yml")
        setup_table.add_row("   6. env variable", "use_env_password: true in config")
        setup_table.add_row("", "")
        setup_table.add_row("🔐 Security Details:", "How passwords are protected")
        setup_table.add_row("   Encryption:", "AES-128 via Fernet (HMAC authenticated)")
        setup_table.add_row("   Master key:", "Set via ESCMD_MASTER_KEY environment variable")
        setup_table.add_row("   Storage:", "Encrypted blob in ~/.escmd/escmd.json")
        setup_table.add_row("   Session cache:", "Decrypted in memory only, expires after 1 hour")
        setup_table.add_row("   Never on disk:", "Plaintext password is never written to disk")
        setup_table.add_row("", "")
        setup_table.add_row("🔧 Troubleshooting:", "")
        setup_table.add_row("   Decrypt fails:", "Check ESCMD_MASTER_KEY is set correctly")
        setup_table.add_row("   Re-store password:", "./escmd.py store-password <env>")
        setup_table.add_row("   Clear session cache:", "./escmd.py clear-session")
        setup_table.add_row("   Key lost:", "Generate new key and re-store all passwords")
        setup_table.add_row("   See full security help:", "./escmd.py help security")

        self.console.print()
        self.console.print(Panel(
            commands_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🔐 store-password Commands[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
        self.console.print(Panel(
            examples_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🚀 store-password Examples[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
        self.console.print(Panel(
            setup_table,
            title=f"[{help_styles.get('header', 'bold magenta')}]🎯 Setup Workflows & Security Details[/{help_styles.get('header', 'bold magenta')}]",
            border_style=border_style,
            padding=(1, 2)
        ))
        print()
