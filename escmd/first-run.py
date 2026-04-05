#!/usr/bin/env python3
import os
import re
import sys
import subprocess
from pathlib import Path
from getpass import getpass

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt


USERNAME_REGEX = re.compile(r"^[a-z]+\.[a-z]+(?:[.-][a-z0-9]+)*$")


def ask_username(console: Console) -> str:
    while True:
        username = Prompt.ask("Enter your username (first_name.last_name)")
        if USERNAME_REGEX.match(username):
            return username
        console.print(
            Panel.fit(
                Text(
                    "Username must be in first_name.last_name format (lowercase letters, dots/hyphens allowed).",
                    style="yellow",
                ),
                title="Invalid username",
                border_style="red",
            )
        )


def ask_password(console: Console) -> str:
    while True:
        pw1 = getpass("Enter your RCOFFICE password: ")
        pw2 = getpass("Confirm your RCOFFICE password: ")
        if pw1 and pw1 == pw2:
            return pw1
        console.print(
            Panel.fit(
                Text(
                    "Passwords did not match or were empty. Please try again.",
                    style="yellow",
                ),
                title="Password mismatch",
                border_style="red",
            )
        )


def replace_elastic_username_in_yaml(
    yaml_path: Path, username: str, console: Console
) -> None:
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")

    lines = yaml_path.read_text().splitlines()

    settings_index = None
    for i, line in enumerate(lines):
        # Top-level settings: must not be indented
        if line.strip() == "settings:" and (line == line.lstrip()):
            settings_index = i
            break

    if settings_index is None:
        raise RuntimeError("Could not locate 'settings:' section in escmd.yml")

    # Find existing elastic_username line within settings block
    elastic_line_index = None
    for i in range(settings_index + 1, len(lines)):
        stripped = lines[i].strip()
        # Stop when we reach a new top-level key (non-empty, not comment, no leading spaces)
        if lines[i] == lines[i].lstrip() and stripped and not stripped.startswith("#"):
            break
        if re.match(r"^\s*elastic_username\s*:\s*", lines[i]):
            elastic_line_index = i
            break

    new_kv = f"  elastic_username: {username}"

    if elastic_line_index is not None:
        # Preserve original indentation of the line being replaced
        indent = len(lines[elastic_line_index]) - len(
            lines[elastic_line_index].lstrip(" ")
        )
        new_line = (" " * indent) + f"elastic_username: {username}"
        lines[elastic_line_index] = new_line
    else:
        # Insert after a helpful comment if present, else right after 'settings:'
        insert_at = settings_index + 1
        for i in range(settings_index + 1, len(lines)):
            if re.match(r"^\s*#\s*Elasticsearch Creds", lines[i]):
                insert_at = i + 1
                break
            # Stop if new top-level begins
            stripped = lines[i].strip()
            if (
                lines[i] == lines[i].lstrip()
                and stripped
                and not stripped.startswith("#")
            ):
                insert_at = i
                break
        lines.insert(insert_at, new_kv)

    # Join with newline and ensure trailing newline
    content = "\n".join(lines) + "\n"
    yaml_path.write_text(content)


def store_password_with_escmd(
    project_root: Path, username: str, password: str, console: Console
) -> str:
    escmd_py = project_root / "escmd.py"
    if not escmd_py.exists():
        raise FileNotFoundError(f"escmd.py not found at {escmd_py}")

    # Pipe password to stdin of escmd.py store-password (defaults to environment 'global')
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

    # Return the output instead of printing it
    return (result.stdout or "").strip()


def main() -> None:
    console = Console()

    console.print(
        Panel.fit(
            Text(
                "Welcome to ESCMD first-run setup\n\n"
                "This will configure your username and securely store your password.",
                style="bold white",
            ),
            title="ESCMD First Run",
            border_style="magenta",
        )
    )

    username = ask_username(console)
    password = ask_password(console)

    project_root = Path(__file__).resolve().parent
    escmd_yml = project_root / "escmd.yml"

    # Perform setup tasks silently
    replace_elastic_username_in_yaml(escmd_yml, username, console)
    password_output = store_password_with_escmd(
        project_root, username, password, console
    )

    # Show consolidated success message
    console.print()
    console.print(
        Panel.fit(
            Text(
                f"✅ Configuration updated successfully!\n\n"
                f"• Username set to: {username}\n"
                f"• Password stored securely for 'global' environment\n\n"
                f"Next steps:\n"
                f"  • Run ./escmd.py show-settings to verify configuration\n"
                f"  • Use ./escmd.py health to check your default cluster",
                style="green",
            ),
            title="Setup Complete",
            border_style="green",
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        Console().print(
            Panel.fit(Text(str(e), style="red"), title="Error", border_style="red")
        )
        sys.exit(1)
