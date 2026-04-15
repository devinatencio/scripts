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
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("store-password",                        "Store password for the 'global' environment",                    "./escmd.py store-password")
        commands_table.add_row("store-password <environment>",          "Store password for a named environment (e.g. prod, lab)",        "./escmd.py store-password prod")
        commands_table.add_row("store-password <env> --username <user>","Store password for a specific user in an environment",           "./escmd.py store-password prod --username kibana_system")
        commands_table.add_row("store-password --username <user>",      "Store password for a user in the global environment",            "")
        commands_table.add_row("list-stored-passwords",                 "List all stored encrypted passwords",                            "./escmd.py list-stored-passwords")
        commands_table.add_row("list-stored-passwords --decrypt",       "Show decrypted passwords (use with caution)",                    "")
        commands_table.add_row("remove-stored-password <environment>",  "Remove a stored password entry",                                 "")
        commands_table.add_row("generate-master-key",                   "Generate a new ESCMD_MASTER_KEY encryption key",                 "./escmd.py generate-master-key")
        commands_table.add_row("rotate-master-key",                     "Re-encrypt all stored passwords with a new master key",          "")

        usage_table.add_row("🚀 First-Time Setup:", "Get encrypted passwords working in 3 steps")
        usage_table.add_row("   Step 1 - Generate key:", "./escmd.py generate-master-key")
        usage_table.add_row("   Step 2 - Export key:",   "export ESCMD_MASTER_KEY='<key from step 1>'")
        usage_table.add_row("   Step 3 - Store password:","./escmd.py store-password")
        usage_table.add_row("   Add to shell profile:",  "Add the export line to ~/.bashrc or ~/.zshrc")
        usage_table.add_row("", "")
        usage_table.add_row("🏢 Multi-Environment Setup:", "Different passwords per cluster environment")
        usage_table.add_row("   Store prod password:", "./escmd.py store-password prod --username kibana_system")
        usage_table.add_row("   Store lab password:",  "./escmd.py store-password lab --username elastic")
        usage_table.add_row("   Store staging:",       "./escmd.py store-password staging --username kibana_system")
        usage_table.add_row("   Verify all stored:",   "./escmd.py list-stored-passwords")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 Password Resolution Order:", "How ESCMD selects the right password")
        usage_table.add_row("   1. env.username:", "prod.kibana_system  (most specific)")
        usage_table.add_row("   2. env:",          "prod")
        usage_table.add_row("   3. global.username:","global.elastic")
        usage_table.add_row("   4. global:",        "global  (least specific)")
        usage_table.add_row("   5. config file:",   "elastic_password in escmd.yml")
        usage_table.add_row("   6. env variable:",  "use_env_password: true in config")
        usage_table.add_row("", "")
        usage_table.add_row("🔐 Security Details:", "How passwords are protected")
        usage_table.add_row("   Encryption:",    "AES-128 via Fernet (HMAC authenticated)")
        usage_table.add_row("   Master key:",    "Set via ESCMD_MASTER_KEY environment variable")
        usage_table.add_row("   Storage:",       "Encrypted blob in ~/.escmd/escmd.json")
        usage_table.add_row("   Session cache:", "Decrypted in memory only, expires after 1 hour")
        usage_table.add_row("   Never on disk:", "Plaintext password is never written to disk")
        usage_table.add_row("", "")
        usage_table.add_row("🔧 Troubleshooting:", "")
        usage_table.add_row("   Decrypt fails:",    "Check ESCMD_MASTER_KEY is set correctly")
        usage_table.add_row("   Re-store password:","./escmd.py store-password <env>")
        usage_table.add_row("   Clear session:",    "./escmd.py clear-session")
        usage_table.add_row("   Key lost:",         "Generate new key and re-store all passwords")
        usage_table.add_row("   Full security help:","./escmd.py help security")

        self._display_help_panels(
            commands_table, examples_table,
            "🔐 store-password Commands", "",
            usage_table, "🎯 Setup Workflows & Security Details"
        )
