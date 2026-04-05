"""
Password Handler Module

Handles password management commands for the ESCMD CLI tool.
Provides secure storage and retrieval of encrypted passwords.
"""

import getpass
import os
import sys
from handlers.base_handler import BaseHandler
from security.password_manager import PasswordManager
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


class PasswordCommands(BaseHandler):
    """Handler for password management commands."""

    def __init__(
        self,
        es_client,
        args,
        console,
        config_file,
        location_config,
        current_location,
        logger=None,
    ):
        """Initialize password handler with password manager."""
        super().__init__(
            es_client,
            args,
            console,
            config_file,
            location_config,
            current_location,
            logger,
        )
        self.password_manager = PasswordManager()

    def handle_store_password(self, args):
        """Handle store-password command"""
        environment = args.environment
        username = getattr(args, "username", None)

        # Check if password is being piped from stdin
        password = None
        if not sys.stdin.isatty():
            # Input is being piped, read from stdin
            try:
                password = sys.stdin.read().strip()
                if password:
                    print(
                        f"Password read from stdin for {environment}"
                        + (f" (user: {username})" if username else "")
                    )
            except Exception as e:
                print(f"Error reading from stdin: {e}")
                return

        # If no password from stdin, prompt for it
        if not password:
            password = getpass.getpass(
                f"Enter password for {environment}"
                + (f" (user: {username})" if username else "")
                + ": "
            )

        if not password:
            print("Password cannot be empty")
            return

        try:
            # Store the password
            self.password_manager.store_password(environment, password, username)

            # Construct the storage key for display
            storage_key = f"{environment}.{username}" if username else environment
            print(f"Password stored successfully for '{storage_key}'")

        except Exception as e:
            print(f"Failed to store password: {e}")
            import traceback

            traceback.print_exc()

    def handle_list_passwords(self, args):
        """Handle list-stored-passwords command with fancy styling"""
        try:
            stored_keys = self.password_manager.list_stored_passwords(return_keys=True)

            if not stored_keys:
                self._show_no_passwords_panel()
                return

            # Check if decrypt flag is set
            show_decrypted = getattr(args, "decrypt", False)

            # Show security warning if decryption is requested
            if show_decrypted:
                from rich.panel import Panel

                warning_panel = Panel(
                    "[bold red]🔶  SECURITY WARNING 🔶[/bold red]\n\n"
                    "[yellow]You are about to display decrypted passwords on screen![/yellow]\n"
                    "[dim]• Make sure no one else can see your terminal[/dim]\n"
                    "[dim]• Consider clearing your terminal history afterwards[/dim]\n"
                    "[dim]• Passwords will be shown in full without masking[/dim]",
                    title="[bold red]🔐 Password Decryption Warning[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
                self.console.print(warning_panel)

                from rich.prompt import Confirm

                if not Confirm.ask(
                    "\n[yellow]Continue with decryption?[/yellow]", default=False
                ):
                    self.console.print(
                        "[green]Operation cancelled for security.[/green]"
                    )
                    return

                self.console.print()  # Add spacing

            self._show_passwords_table(stored_keys, show_decrypted=show_decrypted)

        except Exception as e:
            self.console.print(f"[bold red]❌ Failed to list passwords:[/bold red] {e}")
            import traceback

            traceback.print_exc()

    def handle_remove_password(self, args):
        """Handle remove-stored-password command"""
        environment = args.environment
        if self.password_manager.remove_password(environment):
            print(f"Password for '{environment}' removed successfully")
        else:
            print(f"No password found for '{environment}'")

    def handle_clear_session(self, args):
        """Handle clear-session command"""
        self.password_manager.clear_session()
        print("Session cache cleared")

    def handle_session_info(self, args):
        """Handle session-info command with fancy styling"""
        session_info = self.password_manager.get_session_info()
        self._show_detailed_session_panel(session_info)

    def handle_set_session_timeout(self, args):
        """Handle set-session-timeout command"""
        try:
            timeout_minutes = int(args.timeout)
            timeout_seconds = timeout_minutes * 60

            if timeout_seconds <= 0:
                print("Timeout must be positive")
                return

            self.password_manager.set_session_timeout(timeout_seconds)
            print(f"Session timeout set to {timeout_minutes} minutes")

        except ValueError:
            print("Invalid timeout value. Please provide a number.")
        except Exception as e:
            print(f"Failed to set timeout: {e}")

    def handle_generate_master_key(self, args):
        """Handle generate-master-key command"""
        from cryptography.fernet import Fernet
        import base64

        # Generate a new key
        key = Fernet.generate_key()
        key_str = key.decode("utf-8")

        self.console.print("\n🔑 [bold green]New Master Key Generated![/bold green]")
        self.console.print(f"[yellow]{key_str}[/yellow]")

        if args.show_setup:
            self._show_key_setup_instructions(key_str)
        else:
            self._show_basic_key_instructions(key_str)

    def _show_basic_key_instructions(self, key_str):
        """Show basic instructions for setting up the master key."""
        panel = Panel(
            f"[bold white]🔐 Master Key Setup Instructions[/bold white]\n\n"
            f"[yellow]1. Set environment variable:[/yellow]\n"
            f"[cyan]export ESCMD_MASTER_KEY='{key_str}'[/cyan]\n\n"
            f"[yellow]2. Add to your shell profile:[/yellow]\n"
            f"[dim]echo 'export ESCMD_MASTER_KEY=\"{key_str}\"' >> ~/.zshrc[/dim]\n\n"
            f"[yellow]3. Restart terminal or run:[/yellow]\n"
            f"[cyan]source ~/.zshrc[/cyan]\n\n"
            f"[green]✅ After setup, remove any 'master_key' entries from escmd.yml[/green]\n"
            f"[red]🔶  Keep this key secure - anyone with it can decrypt your passwords![/red]",
            title="[bold cyan]🔑 Environment Variable Setup[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)

    def _show_key_setup_instructions(self, key_str):
        """Show detailed setup instructions for different shells."""

        # Basic setup
        self._show_basic_key_instructions(key_str)

        # Detailed shell instructions
        shell_instructions = Table(
            title="🐚 Shell-Specific Setup Instructions",
            border_style="blue",
            header_style="bold white on blue",
        )
        shell_instructions.add_column("Shell", style="bold yellow")
        shell_instructions.add_column("Profile File", style="cyan")
        shell_instructions.add_column("Command", style="green")

        shell_instructions.add_row(
            "zsh",
            "~/.zshrc",
            f"echo 'export ESCMD_MASTER_KEY=\"{key_str}\"' >> ~/.zshrc",
        )
        shell_instructions.add_row(
            "bash",
            "~/.bashrc",
            f"echo 'export ESCMD_MASTER_KEY=\"{key_str}\"' >> ~/.bashrc",
        )
        shell_instructions.add_row(
            "fish",
            "~/.config/fish/config.fish",
            f"echo 'set -x ESCMD_MASTER_KEY \"{key_str}\"' >> ~/.config/fish/config.fish",
        )

        self.console.print("\n")
        self.console.print(shell_instructions)

        # Security recommendations
        security_panel = Panel(
            "[bold red]🔒 Security Best Practices[/bold red]\n\n"
            "[yellow]✅ DO:[/yellow]\n"
            "• Set the environment variable in your shell profile\n"
            "• Keep the key backed up in a secure location (password manager)\n"
            "• Remove 'master_key' from escmd.yml after setting environment variable\n"
            "• Use different keys for different environments/teams\n\n"
            "[red]❌ DON'T:[/red]\n"
            "• Share the key in chat/email\n"
            "• Commit the key to version control\n"
            "• Store the key in plain text files\n"
            "• Use the same key across multiple systems",
            title="[bold red]🔐 Security Guidelines[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
        self.console.print("\n")
        self.console.print(security_panel)

    def handle_migrate_to_env_key(self, args):
        """Handle migrate-to-env-key command"""
        # Check if environment variable is already set
        current_env_key = os.environ.get("ESCMD_MASTER_KEY")
        if current_env_key and not args.force:
            self.console.print(
                "🟡 [yellow]ESCMD_MASTER_KEY environment variable is already set[/yellow]"
            )
            self.console.print("   [dim]Use --force to override[/dim]")
            return

        # Check if file has a master key
        config = self.password_manager._load_config()
        file_key = config.get("security", {}).get("master_key")

        if not file_key:
            self.console.print("❌ [red]No master key found in escmd.yml[/red]")
            self.console.print(
                "   [yellow]Run[/yellow] [cyan]./escmd.py generate-master-key[/cyan] [yellow]to create one[/yellow]"
            )
            return

        # Show the existing key and setup instructions
        self.console.print(
            "🔍 [bold green]Found existing master key in escmd.yml[/bold green]"
        )
        self.console.print(
            "🚀 [bold yellow]Setting up environment variable...[/bold yellow]\n"
        )

        self._show_basic_key_instructions(file_key)

        # Instructions for cleanup
        cleanup_panel = Panel(
            "[bold yellow]🧹 Cleanup Steps[/bold yellow]\n\n"
            "[yellow]After setting the environment variable:[/yellow]\n\n"
            "[cyan]1. Test that the environment variable works:[/cyan]\n"
            "[dim]   ./escmd.py session-info[/dim]\n\n"
            "[cyan]2. Remove the master_key from escmd.yml:[/cyan]\n"
            "[dim]   Edit escmd.yml and delete the 'master_key' line from the security section[/dim]\n\n"
            "[green]✅ Your passwords will remain encrypted and accessible![/green]",
            title="[bold green]🔄 Migration Complete[/bold green]",
            border_style="green",
            padding=(1, 2),
        )

        self.console.print("\n")
        self.console.print(cleanup_panel)

    def _show_session_panel(self, session_info):
        """Show session information in a panel."""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan")
        table.add_column(style="white")

        table.add_row(
            "Status:", "🟢 Active" if session_info["active"] else "🔴 Inactive"
        )
        table.add_row(
            "Cached Environments:", ", ".join(session_info["cached_environments"])
        )
        table.add_row("Remaining Time:", f"{session_info['remaining_time']} seconds")
        table.add_row("Session Timeout:", f"{session_info['timeout']} seconds")

        panel = Panel(
            table,
            title="[bold green]Session Cache Status[/bold green]",
            border_style="green",
        )
        self.console.print(panel)

    def _show_detailed_session_panel(self, session_info):
        """Show detailed session information with fancy styling."""
        if not session_info.get("active", False):
            # No active session
            panel = Panel(
                "[yellow]📝 No active session[/yellow]\n\n"
                "[dim]💡 Sessions are created when passwords are accessed[/dim]\n"
                "[dim]   Run any command that connects to Elasticsearch to start a session[/dim]",
                title="[bold yellow]💾 Session Cache Status[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
            self.console.print(panel)
            return

        # Active session - show details
        cached_envs = session_info.get("cached_environments", [])
        remaining = session_info.get("remaining_time", 0)
        timeout = session_info.get("timeout", 0)

        # Convert times to human readable
        def format_time(seconds):
            if seconds <= 0:
                return "Expired"
            mins, secs = divmod(int(seconds), 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                return f"{hours}h {mins}m {secs}s"
            elif mins > 0:
                return f"{mins}m {secs}s"
            else:
                return f"{secs}s"

        # Create session overview table
        overview = Table.grid(padding=(0, 2))
        overview.add_column(style="bold cyan", width=18)
        overview.add_column(style="white")

        overview.add_row("🟢 Status:", "[green]Active[/green]")
        overview.add_row("💾 Cached Passwords:", f"[yellow]{len(cached_envs)}[/yellow]")
        overview.add_row("🕐 Remaining Time:", f"[cyan]{format_time(remaining)}[/cyan]")
        overview.add_row("🔩 Session Timeout:", f"[white]{format_time(timeout)}[/white]")

        # Create cached passwords table
        if cached_envs:
            cached_table = Table(
                show_header=True,
                header_style="bold white on blue",
                border_style="blue",
                show_lines=False,
            )
            cached_table.add_column("🔑 Password Key", style="green")
            cached_table.add_column("🕒 Status", style="cyan")

            for env in sorted(cached_envs):
                cached_table.add_row(f"[green]{env}[/green]", "[cyan]Cached[/cyan]")

            content = overview
            content_with_cached = Table.grid(padding=(1, 0))
            content_with_cached.add_row(overview)
            content_with_cached.add_row("")
            content_with_cached.add_row("[bold white]Cached Passwords:[/bold white]")
            content_with_cached.add_row(cached_table)
        else:
            content_with_cached = overview

        panel = Panel(
            content_with_cached,
            title="[bold green]💾 Session Cache Status[/bold green]",
            border_style="green",
            padding=(1, 2),
        )

        self.console.print(panel)

    def _show_no_passwords_panel(self):
        """Show a styled panel when no passwords are stored."""
        panel = Panel(
            "[yellow]📝 No stored passwords found[/yellow]\n\n"
            "[dim]💡 Use[/dim] [bold cyan]store-password[/bold cyan] [dim]to add passwords:[/dim]\n"
            "[dim]   • [/dim][cyan]./escmd.py store-password prod --username kibana_system[/cyan]\n"
            "[dim]   • [/dim][cyan]./escmd.py store-password global[/cyan]",
            title="[bold yellow]🔐 Stored Passwords[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
        self.console.print(panel)

    def _show_passwords_table(self, stored_keys, show_decrypted=False):
        """Show stored passwords in a beautiful table with theme colors."""
        from rich.table import Table
        from rich.text import Text

        if show_decrypted:
            # When showing passwords, create a table without width constraints
            table = Table(
                title="Stored Password Environments",
                title_style="bold cyan",
                border_style="bright_blue",
                header_style="bold white on blue",
                show_header=True,
                show_lines=True,
                expand=True,
                show_edge=False,
            )

            # Single wide column for all content - no width limit
            table.add_column("Details", style="white", no_wrap=False)
        else:
            # Normal table without passwords
            table = Table(
                title="Stored Password Environments",
                title_style="bold cyan",
                border_style="bright_blue",
                header_style="bold white on blue",
                show_header=True,
                show_lines=True,
                expand=True,
            )

            table.add_column("Environment", style="bold green", width=20)
            table.add_column("Username", style="bold yellow", width=25)
            table.add_column("Type", style="bold magenta", width=12)

        # Group passwords by environment for better display
        env_groups = {}
        for key in sorted(stored_keys):
            if "." in key:
                env, username = key.split(".", 1)
                if env not in env_groups:
                    env_groups[env] = []
                env_groups[env].append(("user", username, key))
            else:
                # Environment-wide password
                if key not in env_groups:
                    env_groups[key] = []
                env_groups[key].append(("env", "-", key))

        # Check session cache for status
        session_info = self.password_manager.get_session_info()
        cached_keys = session_info.get("cached_environments", [])

        # Add rows to table
        for env in sorted(env_groups.keys()):
            passwords = env_groups[env]

            for i, (pwd_type, username, full_key) in enumerate(passwords):
                # Environment column - only show for first entry
                env_display = env if i == 0 else ""

                # Username
                if pwd_type == "user":
                    username_display = f"{username}"
                    type_display = "User"
                else:
                    username_display = "-"
                    type_display = "Global"

                if show_decrypted:
                    # Create formatted content for single column
                    env_text = (
                        f"[bold green]Environment:[/bold green] {env}"
                        if env_display
                        else ""
                    )
                    user_text = (
                        f"[bold yellow]Username:[/bold yellow] {username_display}"
                    )
                    type_text = f"[bold magenta]Type:[/bold magenta] {type_display}"

                    # Get password
                    try:
                        if pwd_type == "user":
                            decrypted_password = self.password_manager.get_password(
                                env, username
                            )
                        else:
                            decrypted_password = self.password_manager.get_password(env)

                        if decrypted_password:
                            # Ensure full password is displayed without truncation
                            password_text = f"[bold red]🔓 Password:[/bold red]\n{decrypted_password}"
                        else:
                            password_text = (
                                "[dim red]🔓 Password: Failed to decrypt[/dim red]"
                            )
                    except Exception as e:
                        password_text = (
                            f"[dim red]🔓 Password: Decrypt error - {str(e)}[/dim red]"
                        )

                    # Combine all info in one cell
                    if env_display:
                        content = (
                            f"{env_text}\n{user_text}\n{type_text}\n{password_text}"
                        )
                    else:
                        content = f"{user_text}\n{type_text}\n{password_text}"

                    table.add_row(content)
                else:
                    # Normal table layout
                    table.add_row(
                        f"[green]{env_display}[/green]",
                        f"[yellow]{username_display}[/yellow]",
                        f"[magenta]{type_display}[/magenta]",
                    )

        # Wrap in a panel
        panel = Panel(
            table,
            title=f"[bold cyan]Password Storage ({len(stored_keys)} entries)[/bold cyan]",
            border_style="bright_blue",
            padding=(0, 1),
        )

        self.console.print(panel)

        # Add session information if active
        if session_info.get("active", False):
            self._show_session_summary(session_info)

        # Add helpful footer
        self._show_password_footer()

    def _show_session_summary(self, session_info):
        """Show session cache summary."""
        remaining = session_info.get("remaining_time", 0)
        cached_count = len(session_info.get("cached_environments", []))

        if remaining > 0:
            mins, secs = divmod(remaining, 60)
            time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

            summary = Panel(
                f"[green]💾 Session Cache Active[/green] • "
                f"[yellow]{cached_count}[/yellow] passwords cached • "
                f"[cyan]{time_str}[/cyan] remaining",
                border_style="green",
                padding=(0, 2),
            )
            self.console.print(summary)

    def _show_password_footer(self):
        """Show helpful commands footer."""
        footer_text = (
            "[dim]💡 Available commands:[/dim]\n"
            "[cyan]  • store-password <env> [--username <user>][/cyan] [dim]- Store new password[/dim]\n"
            "[cyan]  • session-info[/cyan] [dim]- Show cache status[/dim]\n"
            "[cyan]  • clear-session[/cyan] [dim]- Clear password cache[/dim]"
        )

        footer = Panel(
            footer_text,
            title="[bold white]🚀 Quick Actions[/bold white]",
            border_style="dim white",
            padding=(0, 1),
        )
        self.console.print(footer)
