"""
Help content for security commands.
"""

from .base_help_content import BaseHelpContent


class SecurityHelpContent(BaseHelpContent):
    """Help content for security commands."""

    def get_topic_name(self) -> str:
        return "security"

    def get_topic_description(self) -> str:
        return "Password management and security features"

    def show_help(self) -> None:
        commands_table = self._create_commands_table()
        examples_table = self._create_examples_table()
        usage_table    = self._create_usage_table()

        commands_table.add_row("store-password [environment]",           "Store encrypted password for environment",                       "./escmd.py store-password prod")
        commands_table.add_row("store-password [env] --username <user>", "Store password for specific user",                              "./escmd.py store-password prod --username kibana")
        commands_table.add_row("list-stored-passwords",                  "List all stored encrypted passwords",                           "./escmd.py list-stored-passwords")
        commands_table.add_row("list-stored-passwords --decrypt",        "Show decrypted passwords (with security warning)",              "")
        commands_table.add_row("remove-stored-password <environment>",   "Remove stored password",                                        "")
        commands_table.add_row("clear-session",                          "Clear current password session cache",                          "")
        commands_table.add_row("session-info",                           "Show current session information",                              "")
        commands_table.add_row("set-session-timeout <minutes>",          "Set session timeout duration",                                  "")
        commands_table.add_row("generate-master-key",                    "Generate new encryption master key",                            "./escmd.py generate-master-key")
        commands_table.add_row("generate-master-key --show-setup",       "Show environment variable setup",                               "")
        commands_table.add_row("migrate-to-env-key",                     "Migrate file-based key to environment",                         "")
        commands_table.add_row("rotate-master-key",                      "Back up escmd.json, new encryption key, re-encrypt all passwords","")

        usage_table.add_row("🔑 Single User Setup:", "")
        usage_table.add_row("   Step 1:", "Set elastic_username in config")
        usage_table.add_row("   Step 2:", "./escmd.py store-password")
        usage_table.add_row("   Step 3:", "All commands use the encrypted password")
        usage_table.add_row("", "")
        usage_table.add_row("👥 Multi-User Setup:", "")
        usage_table.add_row("   Step 1:", "Configure per-environment users in config")
        usage_table.add_row("   Step 2:", "./escmd.py store-password prod --username kibana")
        usage_table.add_row("   Step 3:", "./escmd.py store-password lab --username elastic")
        usage_table.add_row("   Step 4:", "ESCMD auto-selects the correct password")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 Password Resolution Priority:", "")
        usage_table.add_row("   1. environment.username:", "prod.kibana_system (highest priority)")
        usage_table.add_row("   2. environment:",          "prod (environment fallback)")
        usage_table.add_row("   3. global.username:",      "global.username (user fallback)")
        usage_table.add_row("   4. global:",               "global (global fallback)")
        usage_table.add_row("   5. explicit password:",    "elastic_password in config")
        usage_table.add_row("   6. environment variable:", "use_env_password: true")
        usage_table.add_row("", "")
        usage_table.add_row("🔐 Security Features:", "")
        usage_table.add_row("   AES-128 encryption:", "Fernet encryption with HMAC authentication")
        usage_table.add_row("   Master key options:", "File-based or environment variable")
        usage_table.add_row("   Session caching:",    "Passwords cached in memory (1 hour default)")
        usage_table.add_row("   Automatic expiry:",   "Sessions expire and require re-authentication")
        usage_table.add_row("   Multi-user support:", "Per-user, per-environment passwords")
        usage_table.add_row("   No disk storage:",    "Decrypted passwords never written to disk")
        usage_table.add_row("", "")
        usage_table.add_row("📝 Configuration Options:", "")
        usage_table.add_row("   Global username:",         "elastic_username: your.username")
        usage_table.add_row("   Environment variable:",    "export ESCMD_MASTER_KEY='your_key'")
        usage_table.add_row("   Use env password:",        "use_env_password: true")
        usage_table.add_row("   Config file location:",    "~/.escmd/escmd.yml or ./escmd.yml")
        usage_table.add_row("", "")
        usage_table.add_row("🔧 Troubleshooting:", "")
        usage_table.add_row("   Failed to decrypt:",    "Check ESCMD_MASTER_KEY is set correctly")
        usage_table.add_row("   Re-store password:",    "./escmd.py store-password")
        usage_table.add_row("   Clear session:",        "./escmd.py clear-session")
        usage_table.add_row("   Master key missing:",   "./escmd.py generate-master-key")
        usage_table.add_row("   Session expired:",      "Re-run command to re-authenticate")
        usage_table.add_row("   Wrong credentials:",    "Check env/username in server config")

        self._display_help_panels(
            commands_table, examples_table,
            "🔐 Security Commands", "",
            usage_table, "🎯 Workflows & Security Details"
        )
