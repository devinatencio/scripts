#!/usr/bin/env python3
"""
ESCMD first-run setup wizard.

Configures the user's username in escmd.yml and securely stores their
password via ``escmd.py store-password``.  All visual output honours the
active theme from escmd.json / themes.yml.
"""

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from getpass import getpass

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.prompt import Prompt
from rich import box

from display.theme_manager import ThemeManager
from display.style_system import StyleSystem


USERNAME_REGEX = re.compile(r"^[a-z]+\.[a-z]+(?:[.-][a-z0-9]+)*$")


# ------------------------------------------------------------------
# Theme bootstrap
# ------------------------------------------------------------------

class _MinimalConfig:
    """Shim so ThemeManager can resolve the active theme without a full
    ConfigurationManager (YAML files may not exist yet during first-run)."""

    def __init__(self, theme_name: str = "rich"):
        self._theme = theme_name
        self.default_settings = {}

    def get_display_theme(self) -> str:
        return self._theme


def _load_theme_name(state_path: str = "escmd.json") -> str:
    """Read display_theme from escmd.json, falling back to 'rich'."""
    try:
        if os.path.exists(state_path):
            with open(state_path, "r") as fh:
                return json.load(fh).get("display_theme", "rich")
    except (json.JSONDecodeError, IOError):
        pass
    return "rich"


def _build_style_system() -> StyleSystem:
    cfg = _MinimalConfig(_load_theme_name())
    return StyleSystem(theme_manager=ThemeManager(configuration_manager=cfg))


# ------------------------------------------------------------------
# Style helpers
# ------------------------------------------------------------------

def _sem(ss: StyleSystem, key: str, fallback: str = "white") -> str:
    return ss.get_semantic_style(key) if ss else fallback


def _border(ss: StyleSystem) -> str:
    if ss and ss.theme_manager:
        return ss.theme_manager.get_themed_style("table_styles", "border_style", "white")
    return "white"


def _title_style(ss: StyleSystem) -> str:
    if ss and ss.theme_manager:
        return ss.theme_manager.get_themed_style("panel_styles", "title", "bold cyan")
    return "bold cyan"


def _muted(ss: StyleSystem) -> str:
    return _sem(ss, "muted", "dim white")


# ------------------------------------------------------------------
# Visual components
# ------------------------------------------------------------------

def _render_banner(console: Console, ss: StyleSystem) -> None:
    """Render a compact ASCII banner matching the app's version screen."""
    letters = [
        " ███████╗███████╗ ██████╗███╗   ███╗██████╗ ",
        " ██╔════╝██╔════╝██╔════╝████╗ ████║██╔══██╗",
        " █████╗  ███████╗██║     ██╔████╔██║██║  ██║",
        " ██╔══╝  ╚════██║██║     ██║╚██╔╝██║██║  ██║",
        " ███████╗███████║╚██████╗██║ ╚═╝ ██║██████╔╝",
        " ╚══════╝╚══════╝ ╚═════╝╚═╝     ╚═╝╚═════╝ ",
    ]
    c_info = f"bold {_sem(ss, 'info', 'cyan')}"
    c_primary = f"bold {_sem(ss, 'primary', 'blue')}"
    c_secondary = f"bold {_sem(ss, 'secondary', 'magenta')}"
    colours = [c_info, c_info, c_primary, c_primary, c_secondary, c_secondary]

    banner = Text()
    for line, colour in zip(letters, colours):
        banner.append(line + "\n", style=colour)
    console.print(Align.center(banner))

    subtitle_bg = _sem(ss, "primary", "dark_blue")
    console.print(
        Align.center(
            Text("⚡  First-Run Setup Wizard  ⚡", style=f"bold white on {subtitle_bg}")
        )
    )
    console.print()


def _render_welcome(console: Console, ss: StyleSystem) -> None:
    """Render the welcome info panel."""
    title_s = _title_style(ss)
    info_s = _sem(ss, "info", "cyan")
    muted_s = _muted(ss)

    grid = Table.grid(padding=(0, 2))
    grid.add_column(min_width=3)
    grid.add_column()
    grid.add_row(
        Text("📋", justify="center"),
        Text("Configure your username in escmd.yml", style=info_s),
    )
    grid.add_row(
        Text("🔐", justify="center"),
        Text("Securely store your RCOFFICE password", style=info_s),
    )
    grid.add_row(
        Text("✅", justify="center"),
        Text("Get ready to manage your Elasticsearch clusters", style=info_s),
    )

    console.print(
        Panel(
            grid,
            title=f"[{title_s}]🚀 Welcome[/{title_s}]",
            subtitle=f"[{muted_s}]This will only take a moment[/{muted_s}]",
            border_style=_border(ss),
            padding=(1, 3),
        )
    )
    console.print()


def _render_success(console: Console, ss: StyleSystem, username: str) -> None:
    """Render the success panel after setup completes."""
    success_s = _sem(ss, "success", "green")
    info_s = _sem(ss, "info", "cyan")
    muted_s = _muted(ss)
    title_s = _title_style(ss)
    primary_s = _sem(ss, "primary", "cyan")

    grid = Table.grid(padding=(0, 2))
    grid.add_column(min_width=3)
    grid.add_column()

    grid.add_row(
        Text("👤", justify="center"),
        Text.assemble(
            ("Username: ", muted_s),
            (username, f"bold {primary_s}"),
        ),
    )
    grid.add_row(
        Text("🔑", justify="center"),
        Text.assemble(
            ("Password stored for ", muted_s),
            ("'global'", f"bold {primary_s}"),
            (" environment", muted_s),
        ),
    )

    console.print(
        Panel(
            grid,
            title=f"[{title_s}]✅ Setup Complete[/{title_s}]",
            border_style=success_s,
            padding=(1, 3),
        )
    )

    # Next-steps footer
    console.print()
    footer = Text(justify="center")
    footer.append("💡 ", style=f"bold {_sem(ss, 'warning', 'yellow')}")
    footer.append("Next: ", style="bold white")
    footer.append("./escmd.py show-settings", style=f"bold {info_s}")
    footer.append("  ·  ", style=muted_s)
    footer.append("./escmd.py health", style=f"bold {info_s}")
    footer.append("  to verify your cluster", style=muted_s)
    console.print(Panel(Align.center(footer), border_style=muted_s, padding=(0, 1)))


# ------------------------------------------------------------------
# Interactive prompts
# ------------------------------------------------------------------

def ask_username(console: Console, ss: StyleSystem) -> str:
    info_s = _sem(ss, "info", "cyan")
    warning_s = _sem(ss, "warning", "yellow")
    while True:
        username = Prompt.ask(f"[{info_s}]👤 Enter your username (first_name.last_name)[/{info_s}]")
        if USERNAME_REGEX.match(username):
            return username
        console.print(
            Panel(
                Text(
                    "Username must be first_name.last_name format\n"
                    "(lowercase letters, dots and hyphens allowed)",
                    style=warning_s,
                ),
                title=f"[{_title_style(ss)}]⚠️  Invalid Username[/{_title_style(ss)}]",
                border_style=warning_s,
                padding=(1, 3),
            )
        )


def ask_password(console: Console, ss: StyleSystem) -> str:
    warning_s = _sem(ss, "warning", "yellow")
    while True:
        pw1 = getpass("🔐 Enter your RCOFFICE password: ")
        pw2 = getpass("🔐 Confirm your RCOFFICE password: ")
        if pw1 and pw1 == pw2:
            return pw1
        console.print(
            Panel(
                Text(
                    "Passwords did not match or were empty. Please try again.",
                    style=warning_s,
                ),
                title=f"[{_title_style(ss)}]⚠️  Password Mismatch[/{_title_style(ss)}]",
                border_style=warning_s,
                padding=(1, 3),
            )
        )


# ------------------------------------------------------------------
# Config / credential helpers (logic unchanged)
# ------------------------------------------------------------------

def replace_elastic_username_in_yaml(
    yaml_path: Path, username: str, console: Console
) -> None:
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")

    lines = yaml_path.read_text().splitlines()

    settings_index = None
    for i, line in enumerate(lines):
        if line.strip() == "settings:" and (line == line.lstrip()):
            settings_index = i
            break

    if settings_index is None:
        raise RuntimeError("Could not locate 'settings:' section in escmd.yml")

    elastic_line_index = None
    for i in range(settings_index + 1, len(lines)):
        stripped = lines[i].strip()
        if lines[i] == lines[i].lstrip() and stripped and not stripped.startswith("#"):
            break
        if re.match(r"^\s*elastic_username\s*:\s*", lines[i]):
            elastic_line_index = i
            break

    new_kv = f"  elastic_username: {username}"

    if elastic_line_index is not None:
        indent = len(lines[elastic_line_index]) - len(
            lines[elastic_line_index].lstrip(" ")
        )
        lines[elastic_line_index] = (" " * indent) + f"elastic_username: {username}"
    else:
        insert_at = settings_index + 1
        for i in range(settings_index + 1, len(lines)):
            if re.match(r"^\s*#\s*Elasticsearch Creds", lines[i]):
                insert_at = i + 1
                break
            stripped = lines[i].strip()
            if (
                lines[i] == lines[i].lstrip()
                and stripped
                and not stripped.startswith("#")
            ):
                insert_at = i
                break
        lines.insert(insert_at, new_kv)

    yaml_path.write_text("\n".join(lines) + "\n")


def store_password_with_escmd(
    project_root: Path, username: str, password: str, console: Console
) -> str:
    escmd_py = project_root / "escmd.py"
    if not escmd_py.exists():
        raise FileNotFoundError(f"escmd.py not found at {escmd_py}")

    try:
        result = subprocess.run(
            [sys.executable, str(escmd_py), "store-password", "--username", username],
            input=password,
            universal_newlines=True,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to execute escmd.py: {e}")

    if result.returncode != 0:
        err_output = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"store-password failed: {err_output}")

    return (result.stdout or "").strip()


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    console = Console()
    ss = _build_style_system()

    console.print()
    _render_banner(console, ss)
    _render_welcome(console, ss)

    username = ask_username(console, ss)
    password = ask_password(console, ss)

    project_root = Path(__file__).resolve().parent
    escmd_yml = project_root / "escmd.yml"

    replace_elastic_username_in_yaml(escmd_yml, username, console)
    store_password_with_escmd(project_root, username, password, console)

    console.print()
    _render_success(console, ss, username)
    console.print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        Console().print("\n[dim]Setup cancelled.[/dim]")
        sys.exit(130)
    except Exception as e:
        console = Console()
        try:
            ss = _build_style_system()
            error_s = _sem(ss, "error", "red")
            console.print(
                Panel(
                    Text(str(e), style=error_s),
                    title=f"[{_title_style(ss)}]❌ Error[/{_title_style(ss)}]",
                    border_style=error_s,
                    padding=(1, 3),
                )
            )
        except Exception:
            console.print(
                Panel(Text(str(e), style="red"), title="Error", border_style="red")
            )
        sys.exit(1)
