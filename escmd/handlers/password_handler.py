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
from rich.prompt import Confirm
from rich.markup import escape


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
        state_file_path=None,
        config_manager=None,
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
        pm_path = state_file_path if state_file_path is not None else "escmd.json"
        self.password_manager = PasswordManager(pm_path)

        # Build theme manager — prefer a passed config_manager, then try config_file
        try:
            from display.theme_manager import ThemeManager
            from display.style_system import StyleSystem
            if config_manager is None and config_file:
                from configuration_manager import ConfigurationManager
                config_manager = ConfigurationManager(config_file_path=config_file)
            self._tm = ThemeManager(config_manager) if config_manager else None
            self._ss = StyleSystem(self._tm) if self._tm else None
        except Exception:
            self._tm = None
            self._ss = None

    def handle_store_password(self, args):
        """Handle store-password command"""
        environment = args.environment
        username = getattr(args, "username", None)
        storage_key = f"{environment}.{username}" if username else environment
        display_target = (
            f"[bold cyan]{escape(environment)}[/bold cyan]"
            + (f"  [dim](user: {escape(username)})[/dim]" if username else "")
        )

        # Check if password is being piped from stdin
        password = None
        if not sys.stdin.isatty():
            try:
                password = sys.stdin.read().strip()
                if password:
                    self.console.print(Panel(
                        f"🔑 Password read from stdin for {display_target}",
                        border_style="cyan",
                        padding=(0, 2),
                    ))
            except Exception as e:
                self.console.print(Panel(
                    f"[bold red]Error reading from stdin:[/bold red] {escape(str(e))}",
                    title="[bold red]✗ Error[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                ))
                return

        # If no password from stdin, prompt for it
        if not password:
            prompt_label = (
                f"Enter password for {environment}"
                + (f" (user: {username})" if username else "")
                + ""
            )
            password = getpass.getpass(prompt_label + ": ")

        if not password:
            self.console.print(Panel(
                "[bold yellow]Password cannot be empty.[/bold yellow]",
                title="[bold yellow]⚠ Cancelled[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            ))
            return

        try:
            self.password_manager.store_password(environment, password, username)
            self.console.print(Panel(
                f"[bold green]✓[/bold green] Password stored successfully for {display_target}\n\n"
                f"[dim]Key:[/dim] [cyan]{escape(storage_key)}[/cyan]",
                title="[bold green]✓ Password Stored[/bold green]",
                border_style="green",
                padding=(1, 2),
            ))

        except Exception as e:
            self.console.print(Panel(
                f"[red]{escape(str(e))}[/red]",
                title="[bold red]✗ Failed to Store Password[/bold red]",
                border_style="red",
                padding=(1, 2),
            ))

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
        username = getattr(args, "username", None)
        storage_key = f"{environment}.{username}" if username else environment
        try:
            # Check it exists first
            stored_keys = self.password_manager.list_stored_passwords(return_keys=True)
            if storage_key not in stored_keys:
                self.console.print(Panel(
                    f"[yellow]No stored password found for [bold]{escape(storage_key)}[/bold].[/yellow]\n\n"
                    f"[dim]Run [cyan]./escmd.py list-stored-passwords[/cyan] to see available entries.[/dim]",
                    title="[bold yellow]🔐 Password Not Found[/bold yellow]",
                    border_style="yellow",
                    padding=(1, 2),
                ))
                return

            assume_yes = bool(getattr(args, "yes", False))
            if not assume_yes and not Confirm.ask(f"\n  Remove stored password for [bold cyan]{escape(storage_key)}[/bold cyan]?"):
                self.console.print(Panel(
                    "[yellow]No changes were made.[/yellow]",
                    title="[bold yellow]🔐 Cancelled[/bold yellow]",
                    border_style="yellow",
                    padding=(1, 2),
                ))
                return

            self.console.print()
            if self.password_manager.remove_password(storage_key):
                self.console.print(Panel(
                    f"[green]Password for [bold]{escape(storage_key)}[/bold] removed successfully.[/green]",
                    title="[bold green]🔐 Password Removed[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                ))
        except Exception as e:
            self.console.print(Panel(
                f"[red]{escape(str(e))}[/red]",
                title="[bold red]❌ Failed to Remove Password[/bold red]",
                border_style="red",
                padding=(1, 2),
            ))

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
        from rich.text import Text
        from rich.align import Align

        key = Fernet.generate_key()
        key_str = key.decode("utf-8")

        # Key — centered, bold, high contrast
        key_text = Text(key_str, style="bold bright_yellow")
        self.console.print()
        self.console.print(Panel(
            Align.center(key_text),
            title="[bold bright_green]🔑  New Master Key[/bold bright_green]",
            border_style="bright_green",
            padding=(1, 6),
            subtitle="[dim]copy this before continuing[/dim]",
        ))

        if args.show_setup:
            self._show_key_setup_instructions(key_str)
        else:
            self._show_basic_key_instructions(key_str)

    def _show_basic_key_instructions(self, key_str):
        """Show basic instructions for setting up the master key."""
        from rich.text import Text

        steps = Table.grid(padding=(0, 2))
        steps.add_column(justify="right", style="bold cyan", width=3)
        steps.add_column()

        steps.add_row("1", Text.from_markup(
            f"[yellow]Step 1 — Export the key[/yellow]\n"
            f"[bright_cyan]export ESCMD_MASTER_KEY='{key_str}'[/bright_cyan]"
        ))
        steps.add_row("2", Text.from_markup(
            f"[yellow]Step 2 — Persist to your shell profile[/yellow]\n"
            f"[dim]echo 'export ESCMD_MASTER_KEY=\"{key_str}\"' >> ~/.zshrc[/dim]"
        ))
        steps.add_row("3", Text.from_markup(
            f"[yellow]Step 3 — Reload your shell[/yellow]\n"
            f"[bright_cyan]source ~/.zshrc[/bright_cyan]"
        ))
        steps.add_row("[green]✔[/green]", Text.from_markup(
            "[green]Remove any [bold]master_key[/bold] entries from escmd.yml[/green]"
        ))
        steps.add_row("[red]![/red]", Text.from_markup(
            "[red]Keep this key secure — anyone with it can decrypt your passwords[/red]"
        ))

        self.console.print(Panel(
            steps,
            title="[bold cyan]>> Setup Instructions[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        ))

    def _show_key_setup_instructions(self, key_str):
        """Show detailed setup instructions for different shells."""
        from rich.text import Text

        self._show_basic_key_instructions(key_str)

        # Shell table — themed
        ss, tm = self._theme()
        full_theme = tm.get_full_theme_data() if tm else {}
        table_styles = full_theme.get('table_styles', {})
        t_border      = table_styles.get('border_style', 'bright_blue')
        t_header      = table_styles.get('header_style', 'bold white on blue')
        title_style   = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        primary_style = ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan'
        success_style = ss._get_style('semantic', 'success', 'green') if ss else 'green'
        warning_style = ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'
        box_style     = ss.get_table_box() if ss else None

        shell_table = Table(
            border_style=t_border,
            header_style=t_header,
            show_lines=False,
            padding=(0, 1),
            expand=False,
            box=box_style,
        )
        shell_table.add_column("Shell",   style=f"bold {warning_style}", width=6,  no_wrap=True)
        shell_table.add_column("Profile", style=primary_style,           width=26, no_wrap=True)
        shell_table.add_column("Command", style=success_style)

        shell_table.add_row(
            "zsh",  "~/.zshrc",
            f"echo 'export ESCMD_MASTER_KEY=\"{key_str}\"' >> ~/.zshrc",
        )
        shell_table.add_row(
            "bash", "~/.bashrc",
            f"echo 'export ESCMD_MASTER_KEY=\"{key_str}\"' >> ~/.bashrc",
        )
        shell_table.add_row(
            "fish", "~/.config/fish/config.fish",
            f"echo 'set -x ESCMD_MASTER_KEY \"{key_str}\"' >> ~/.config/fish/config.fish",
        )

        self.console.print(Panel(
            shell_table,
            title=f"[{title_style}]🐚  Shell Profile Commands[/{title_style}]",
            border_style=t_border,
            padding=(1, 2),
        ))

        # Security DO / DON'T — table grid, full-width columns, readable text
        sec = Table.grid(padding=(0, 4), expand=True)
        sec.add_column(ratio=1)
        sec.add_column(ratio=1)

        do_col = Text.from_markup(
            "[bold bright_green]✅  DO[/bold bright_green]\n\n"
            "[green]• Store the key in your shell profile[/green]\n"
            "[green]• Back it up in a password manager[/green]\n"
            "[green]• Remove [bold]master_key[/bold] from escmd.yml[/green]\n"
            "[green]• Use a unique key per environment[/green]"
        )
        dont_col = Text.from_markup(
            "[bold bright_red]❌  DON'T[/bold bright_red]\n\n"
            "[red]• Share the key in chat or email[/red]\n"
            "[red]• Commit the key to version control[/red]\n"
            "[red]• Store it in plain text files[/red]\n"
            "[red]• Reuse the same key across systems[/red]"
        )
        sec.add_row(do_col, dont_col)

        self.console.print(Panel(
            sec,
            title="[bold red]🔒  Security Guidelines[/bold red]",
            border_style="red",
            padding=(1, 3),
        ))

    def handle_rotate_master_key(self, args):
        """Handle rotate-master-key: backup state file, new Fernet key, re-encrypt passwords."""
        assume_yes = bool(getattr(args, "yes", False))

        err, preview = self.password_manager.get_rotate_master_key_preview()
        if err:
            self._show_rotate_master_key_error(err)
            return

        if not assume_yes:
            self._show_rotate_master_key_confirmation(preview)
            while True:
                answer = self.console.input("\n[yellow]Proceed with master key rotation?[/yellow] [dim][y/n][/dim] ").strip().lower()
                if answer in ("y", "yes"):
                    break
                if answer in ("n", "no", ""):
                    self._show_rotate_master_key_cancelled()
                    return

        ok, msg, details = self.password_manager.rotate_master_key()
        if not ok:
            self._show_rotate_master_key_error(msg)
            return

        self._show_rotate_master_key_success(details)

    def _show_rotate_master_key_error(self, message: str) -> None:
        panel = Panel(
            escape(message),
            title="[bold red]🔐 Rotate master key — failed[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
        self.console.print(panel)

    def _show_rotate_master_key_cancelled(self) -> None:
        panel = Panel(
            "[yellow]No changes were made.[/yellow]",
            title="[bold yellow]Rotate master key — cancelled[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
        self.console.print(panel)

    def _show_rotate_master_key_confirmation(self, preview: dict) -> None:
        from rich.text import Text
        from rich.columns import Columns

        ss, tm = self._theme()
        full_theme = tm.get_full_theme_data() if tm else {}
        table_styles = full_theme.get('table_styles', {})
        border        = table_styles.get('border_style', 'bright_blue')
        header_style  = table_styles.get('header_style', 'bold white on blue')
        title_style   = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        primary_style = ss._get_style('semantic', 'primary',  'cyan')   if ss else 'cyan'
        warning_style = ss._get_style('semantic', 'warning',  'yellow') if ss else 'yellow'
        success_style = ss._get_style('semantic', 'success',  'green')  if ss else 'green'
        muted_style   = ss._get_style('semantic', 'muted',    'dim')    if ss else 'dim'
        box_style     = ss.get_table_box() if ss else None

        # Details grid
        details = Table(show_header=False, box=None, padding=(0, 2), expand=True)
        details.add_column(style=f"bold {warning_style}", min_width=24, no_wrap=True)
        details.add_column(style="white")
        details.add_row("State file",              preview["state_path"])
        details.add_row("Backup path",             preview["backup_path"])
        details.add_row("Stored password entries", str(preview["entry_count"]))
        details.add_row("Decrypt using",           preview["decrypt_key_source"])

        # Keys list
        keys = preview.get("storage_keys") or []
        keys_grid = Table(show_header=False, box=None, padding=(0, 2), expand=True)
        keys_grid.add_column(style=success_style)
        max_rows = 25
        for k in keys[:max_rows]:
            keys_grid.add_row(f"  {k}")
        if len(keys) > max_rows:
            keys_grid.add_row(f"  [{muted_style}]… and {len(keys) - max_rows} more[/{muted_style}]")

        # Compose everything into one panel
        body = Table(show_header=False, box=None, padding=(0, 0), expand=True)
        body.add_column()

        body.add_row(Text.from_markup(
            f"[{muted_style}]A new Fernet master key will be written to your state file.\n"
            f"All stored passwords will be re-encrypted with the new key.[/{muted_style}]"
        ))
        body.add_row("")
        body.add_row(Text.from_markup(f"[{title_style}]  Details[/{title_style}]"))
        body.add_row(details)

        if keys:
            body.add_row("")
            body.add_row(Text.from_markup(
                f"[{title_style}]  Entries to re-encrypt[/{title_style}] "
                f"[{muted_style}]({len(keys)})[/{muted_style}]"
            ))
            body.add_row(keys_grid)

        self.console.print()
        self.console.print(Panel(
            body,
            title=f"[{title_style}]🔐 Rotate master key[/{title_style}]",
            border_style=primary_style,
            padding=(1, 2),
        ))

    def _show_rotate_master_key_success(self, details: dict) -> None:
        result = Table(
            show_header=True,
            header_style="bold white on green",
            border_style="green",
            title="[bold green]Rotation complete[/bold green]",
        )
        result.add_column("Item", style="bold yellow", min_width=24)
        result.add_column("Value", style="white")

        result.add_row("Status", "[green]Success[/green]")
        result.add_row("State file", details["state_path"])
        result.add_row("Backup saved", details["backup_path"])
        result.add_row(
            "Entries re-encrypted",
            str(details["reencrypted_count"]),
        )
        result.add_row(
            "New master key",
            "[dim]Written to[/dim] [cyan]security.master_key[/cyan] [dim]in the state file[/dim]",
        )
        result.add_row("Session password cache", "[cyan]Cleared[/cyan]")

        self.console.print()
        success_panel = Panel(
            result,
            title="[bold green]🔐 Master key rotated[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(success_panel)

        if details.get("escmd_master_key_was_set"):
            warn = Table.grid(padding=(0, 1))
            warn.add_column(style="yellow")
            warn.add_row(
                "[bold]ESCMD_MASTER_KEY[/bold] is set in your environment. "
                "It still holds the [bold]old[/bold] key until you update it."
            )
            warn.add_row(
                "Either set it to the new value from [cyan]security.master_key[/cyan] in the state file, "
                "or [bold]unset[/bold] ESCMD_MASTER_KEY so the file key is used."
            )
            env_panel = Panel(
                warn,
                title="[bold yellow]🔶  Environment variable[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
            self.console.print()
            self.console.print(env_panel)

        keys = details.get("storage_keys") or []
        if keys:
            kt = Table(
                show_header=True,
                header_style="bold white on green",
                border_style="green",
                title="[bold green]Re-encrypted storage keys[/bold green]",
            )
            kt.add_column("Storage key", style="green")
            max_rows = 25
            for k in keys[:max_rows]:
                kt.add_row(k)
            if len(keys) > max_rows:
                kt.add_row(f"[dim]… and {len(keys) - max_rows} more[/dim]")
            self.console.print()
            self.console.print(kt)

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

    def _theme(self):
        """Return (style_system, theme_manager)."""
        ss = self._ss or getattr(self.es_client, 'style_system', None)
        tm = self._tm or getattr(self.es_client, 'theme_manager', None)
        return ss, tm

    def _show_no_passwords_panel(self):
        """Show a styled panel when no passwords are stored."""
        ss, tm = self._theme()
        border = tm.get_theme_styles().get('border_style', 'yellow') if tm else 'yellow'
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        warning_style = ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'
        primary_style = ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan'
        muted_style = ss._get_style('semantic', 'muted', 'dim') if ss else 'dim'

        from rich.table import Table as InnerTable
        from rich.text import Text
        msg_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        msg_table.add_column("Icon", justify="center", width=3)
        msg_table.add_column("Text")
        msg_table.add_row("📭", Text("No stored passwords found", style=warning_style))
        msg_table.add_row("", Text(""))
        msg_table.add_row("💡", Text("Add a password with:", style=muted_style))
        msg_table.add_row("", Text("./escmd.py store-password prod --username kibana_system", style=primary_style))
        msg_table.add_row("", Text("./escmd.py store-password global", style=primary_style))

        self.console.print(Panel(
            msg_table,
            title=f"[{title_style}]Stored Passwords[/{title_style}]",
            border_style=warning_style,
            padding=(1, 2),
        ))

    def _show_passwords_table(self, stored_keys, show_decrypted=False):
        """Show stored passwords in a table with theme colors."""
        from rich.table import Table
        from rich.text import Text

        ss, tm = self._theme()
        full_theme = tm.get_full_theme_data() if tm else {}
        table_styles = full_theme.get('table_styles', {})
        border = table_styles.get('border_style', 'bright_blue')
        header_style = table_styles.get('header_style', 'bold white on blue')
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        primary_style = ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan'
        success_style = ss._get_style('semantic', 'success', 'green') if ss else 'green'
        warning_style = ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'
        secondary_style = ss._get_style('semantic', 'secondary', 'magenta') if ss else 'magenta'
        box_style = ss.get_table_box() if ss else None
        zebra = ss.get_zebra_style(1) if ss else "on grey11"

        if show_decrypted:
            table = Table(
                title="Stored Password Environments",
                title_style=title_style,
                border_style=border,
                header_style=header_style,
                show_header=True,
                expand=True,
                show_edge=False,
                box=box_style,
            )
            table.add_column("Details", style="white", no_wrap=False)
        else:
            table = Table(
                title="Stored Password Environments",
                title_style=title_style,
                border_style=border,
                header_style=header_style,
                show_header=True,
                expand=True,
                box=box_style,
            )
            table.add_column("Environment", style=success_style, width=20)
            table.add_column("Username", style=warning_style, width=25)
            table.add_column("Type", style=secondary_style, width=12)

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
        for env_index, env in enumerate(sorted(env_groups.keys())):
            passwords = env_groups[env]
            env_row_style = zebra if env_index % 2 != 0 else ""

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
                            password_text = f"[bold red]🔓 Password:[/bold red]\n{decrypted_password}"
                        else:
                            password_text = (
                                "[dim red]🔓 Password: Failed to decrypt[/dim red]"
                            )
                    except Exception as e:
                        password_text = (
                            f"[dim red]🔓 Password: Decrypt error - {str(e)}[/dim red]"
                        )

                    if env_display:
                        content = (
                            f"{env_text}\n{user_text}\n{type_text}\n{password_text}"
                        )
                    else:
                        content = f"{user_text}\n{type_text}\n{password_text}"

                    table.add_row(content, style=env_row_style)
                else:
                    table.add_row(
                        Text(env_display, style=success_style),
                        Text(username_display, style=warning_style),
                        Text(type_display, style=secondary_style),
                        style=env_row_style,
                    )

        # Wrap in a panel
        panel = Panel(
            table,
            title=f"[{title_style}]Password Storage ({len(stored_keys)} entries)[/{title_style}]",
            border_style=border,
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
            ss, tm = self._theme()
            border = tm.get_theme_styles().get('border_style', 'green') if tm else 'green'
            success_style = ss._get_style('semantic', 'success', 'green') if ss else 'green'
            warning_style = ss._get_style('semantic', 'warning', 'yellow') if ss else 'yellow'
            info_style = ss._get_style('semantic', 'info', 'cyan') if ss else 'cyan'

            mins, secs = divmod(remaining, 60)
            time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

            from rich.text import Text
            line = Text()
            line.append("Session Cache Active", style=success_style)
            line.append(" • ", style="default")
            line.append(str(cached_count), style=warning_style)
            line.append(" passwords cached • ", style="default")
            line.append(time_str, style=info_style)
            line.append(" remaining", style="default")

            self.console.print(Panel(line, border_style=success_style, padding=(0, 2)))

    def _show_password_footer(self):
        """Show helpful commands footer."""
        ss, tm = self._theme()
        border = tm.get_theme_styles().get('border_style', 'white') if tm else 'white'
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
        primary_style = ss._get_style('semantic', 'primary', 'cyan') if ss else 'cyan'
        muted_style = ss._get_style('semantic', 'muted', 'dim') if ss else 'dim'

        from rich.table import Table as InnerTable
        from rich.text import Text
        footer_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        footer_table.add_column("Icon", justify="center", width=3)
        footer_table.add_column("Command", style=primary_style, no_wrap=True)
        footer_table.add_column("Description", style=muted_style)

        footer_table.add_row("+", "store-password <env> [--username <user>]", "Store new password")
        footer_table.add_row(">", "session-info", "Show cache status")
        footer_table.add_row("-", "clear-session", "Clear password cache")

        self.console.print(Panel(
            footer_table,
            title=f"[{title_style}]Quick Actions[/{title_style}]",
            border_style=border,
            padding=(0, 1),
        ))
