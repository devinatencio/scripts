#!/usr/bin/env python3
"""
Action Handler for escmd - manages and executes action sequences.
"""

import os
import yaml
import re
from typing import Dict, List, Any, Optional, Tuple
from jinja2 import Environment, BaseLoader, Template
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.progress import track
import argparse
from datetime import datetime
import json
import re
from rich.json import JSON


class ActionManager:
    """Manages loading and parsing of action definitions."""

    def __init__(self, actions_file: str = None):
        """Initialize ActionManager with actions file path."""
        if actions_file is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            actions_file = os.path.join(script_dir, "actions.yml")

        self.actions_file = actions_file
        self.actions = {}
        self.jinja_env = Environment(loader=BaseLoader())
        self.load_actions()

    def load_actions(self):
        """Load actions from YAML file."""
        if not os.path.exists(self.actions_file):
            raise FileNotFoundError(f"Actions file not found: {self.actions_file}")

        try:
            with open(self.actions_file, "r") as f:
                data = yaml.safe_load(f)

            if not data or "actions" not in data:
                raise ValueError("Invalid actions file format - missing 'actions' key")

            # Convert list of actions to dictionary for easier lookup
            for action in data["actions"]:
                if "name" not in action:
                    raise ValueError("Action missing required 'name' field")

                self.actions[action["name"]] = action

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in actions file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading actions file: {e}")

    def get_action(self, name: str) -> Optional[Dict]:
        """Get action definition by name."""
        return self.actions.get(name)

    def list_actions(self) -> List[str]:
        """Get list of all action names."""
        return list(self.actions.keys())

    def validate_parameters(self, action: Dict, params: Dict) -> List[str]:
        """Validate parameters for an action. Returns list of errors."""
        errors = []
        action_params = action.get("parameters", [])

        # Check for required parameters
        for param_def in action_params:
            param_name = param_def["name"]
            if param_def.get("required", False) and param_name not in params:
                errors.append(f"Required parameter '{param_name}' is missing")

        # Validate parameter types
        for param_name, param_value in params.items():
            param_def = next(
                (p for p in action_params if p["name"] == param_name), None
            )
            if param_def:
                param_type = param_def.get("type", "string")
                if param_type == "integer":
                    try:
                        int(param_value)
                    except ValueError:
                        errors.append(f"Parameter '{param_name}' must be an integer")
                elif param_type == "choice":
                    choices = param_def.get("choices", [])
                    if param_value not in choices:
                        errors.append(
                            f"Parameter '{param_name}' must be one of: {choices}"
                        )

        return errors


class ActionHandler:
    """Handles execution of actions defined in actions.yml."""

    def __init__(
        self,
        es_client,
        args,
        console,
        config_file,
        location_config,
        current_location=None,
        logger=None,
    ):
        """Initialize ActionHandler."""
        self.es_client = es_client
        self.args = args
        self.console = console
        self.config_file = config_file
        self.location_config = location_config
        self.current_location = current_location
        self.logger = logger

        # Initialize a standalone style system for when es_client is None
        # (e.g. `action list` / `action show` which don't need a connection).
        # We replicate the same config/state file resolution the main app uses so
        # the user's active theme is respected.
        try:
            from display.theme_manager import ThemeManager
            from display.style_system import StyleSystem
            from configuration_manager import ConfigurationManager as CM
            import os as _os

            script_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            state_file = (
                _os.environ.get("ESCMD_STATE")
                or _os.environ.get("ESCMD_CONFIG")
                or _os.path.join(script_dir, "escmd.json")
            )
            main_cfg  = _os.environ.get("ESCMD_MAIN_CONFIG")
            srv_cfg   = _os.environ.get("ESCMD_SERVERS_CONFIG")
            legacy    = _os.environ.get("ELASTIC_SERVERS_CONFIG")

            if main_cfg or srv_cfg:
                _cm = CM(
                    state_file_path=state_file,
                    main_config_path=main_cfg or _os.path.join(script_dir, "escmd.yml"),
                    servers_config_path=srv_cfg or _os.path.join(script_dir, "elastic_servers.yml"),
                )
            elif legacy:
                _cm = CM(config_file_path=legacy, state_file_path=state_file)
            else:
                _cm = CM(state_file_path=state_file)

            self._theme_manager = ThemeManager(_cm)
            self._style_system = StyleSystem(self._theme_manager)
        except Exception:
            self._theme_manager = None
            self._style_system = None

        # Detect if we're running in esterm context
        self.in_esterm = self._detect_esterm_context()

        # Determine if we should use native output (original escmd formatting)
        self.use_native_output = getattr(args, "native_output", False) or self.in_esterm

        # Action output configuration from CLI args
        self.auto_format_json = (
            not getattr(args, "no_json", False) and not self.use_native_output
        )  # Skip JSON formatting for native output
        self.show_command_output = (
            not getattr(args, "compact", False) and not self.use_native_output
        )  # Skip panel formatting for native output
        self.max_output_lines = getattr(
            args, "max_lines", 15
        )  # Maximum lines to show in output panels

        # Initialize action manager
        try:
            self.action_manager = ActionManager()
        except Exception as e:
            self.console.print(f"[bold red]✗ Error loading actions:[/bold red] {e}")
            self.action_manager = None

    def _detect_esterm_context(self) -> bool:
        """Detect if we're running within esterm context."""
        import inspect
        import os

        # Check environment variable
        if os.environ.get("ESTERM_SESSION", False):
            return True

        # Check call stack for esterm modules
        try:
            for frame_info in inspect.stack():
                filename = frame_info.filename
                if "esterm_modules" in filename or "esterm.py" in filename:
                    return True
        except Exception:
            pass

        return False

    def _get_style_system(self):
        """Get style system — from es_client if available, otherwise the local fallback."""
        if self.es_client and hasattr(self.es_client, "style_system"):
            return self.es_client.style_system
        return self._style_system

    def _get_theme_styles(self):
        """Get theme styles — from es_client if available, otherwise the local fallback."""
        if self.es_client and hasattr(self.es_client, "theme_manager"):
            return self.es_client.theme_manager.get_theme_styles()
        return self._theme_manager.get_theme_styles() if self._theme_manager else {}

    def _sem(self, semantic_type: str, default: str = "white") -> str:
        """Shorthand to get a semantic style string."""
        ss = self._get_style_system()
        if ss:
            return ss.get_semantic_style(semantic_type)
        return default

    def _print_error(self, message: str):
        """Print a styled error panel with a fixed title and the message as subtitle."""
        error_style = self._sem("error", "red")
        desc_style = self._get_theme_styles().get("panel_styles", {}).get("description", "")

        self.console.print(Panel(
            Text(message, style=desc_style) if desc_style else message,
            title=f"[{error_style}]❌ Error[/{error_style}]",
            border_style=error_style,
            padding=(0, 2),
        ))

    def _print_warning(self, message: str):
        """Print a styled warning message."""
        error_style = self._sem("error", "red")
        warning_style = self._sem("warning", "yellow")
        self.console.print(f"[{warning_style}]⚠ {message}[/{warning_style}]")

    def _print_success(self, message: str):
        """Print a styled success message."""
        success_style = self._sem("success", "green")
        self.console.print(f"[{success_style}]✓ {message}[/{success_style}]")

    def _print_muted(self, message: str):
        """Print a muted/dim message."""
        muted_style = self._sem("muted", "dim white")
        self.console.print(f"[{muted_style}]{message}[/{muted_style}]")

    def handle_action(self):
        """Handle action commands."""
        if not self.action_manager:
            self._print_error("Actions system unavailable due to loading errors")
            return

        action_cmd = getattr(self.args, "action_cmd", None)

        if action_cmd is None:
            self._show_action_help()
        elif action_cmd == "list":
            self.handle_action_list()
        elif action_cmd == "show":
            self.handle_action_show()
        elif action_cmd == "run":
            self.handle_action_run()
        else:
            primary = self._sem("primary", "cyan")
            muted = self._sem("muted", "dim white")
            desc_style = self._get_theme_styles().get("panel_styles", {}).get("description", "")
            error_style = self._sem("error", "red")

            content = Text()
            content.append(f"'{action_cmd}' is not a valid subcommand.\n\n", style=desc_style)
            content.append("Available subcommands\n", style="bold")
            content.append("  list  ", style=primary)
            content.append("show all defined actions\n", style=muted)
            content.append("  show  ", style=primary)
            content.append("show details for a specific action\n", style=muted)
            content.append("  run   ", style=primary)
            content.append("execute an action", style=muted)

            self.console.print(Panel(
                content,
                title=f"[{error_style}]❌ Unknown subcommand[/{error_style}]",
                border_style=error_style,
                padding=(0, 1),
            ))

    def _show_action_help(self):
        """Display help screen for action commands."""
        from rich.table import Table

        ss = getattr(self.es_client, 'style_system', None)
        tm = getattr(self.es_client, 'theme_manager', None)

        if not ss or not tm:
            self.handle_action_list()
            return

        primary_style = ss.get_semantic_style("primary")
        success_style = ss.get_semantic_style("success")
        muted_style = ss._get_style('semantic', 'muted', 'dim')
        border_style = ss._get_style('table_styles', 'border_style', 'white')
        header_style = tm.get_theme_styles().get('header_style', 'bold white')
        title_style = tm.get_themed_style('panel_styles', 'title', 'bold white')
        box_style = ss.get_table_box()

        header_panel = Panel(
            Text("Run ./escmd.py action <command> [options]", style="bold white"),
            title=f"[{title_style}]🎬 Action Sequences[/{title_style}]",
            subtitle=Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]on any subcommand for full options[/dim]"),
            border_style=border_style,
            padding=(1, 2),
            expand=True,
        )

        table = Table(
            show_header=True,
            header_style=header_style,
            border_style=border_style,
            box=box_style,
            show_lines=False,
            expand=True,
        )
        table.add_column("Command / Option", style=primary_style, ratio=2)
        table.add_column("Description", style="white", ratio=3)
        table.add_column("Example", style=success_style, ratio=3)

        rows = [
            ("list", "List all available action sequences", "action list"),
            ("show <name>", "Show details for a specific action", "action show my-action"),
            ("run <name>", "Execute an action sequence", "action run my-action"),
        ]
        for i, (cmd, desc, ex) in enumerate(rows):
            table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

        table.add_row(
            Text("── Options ──", style=muted_style),
            Text("", style=muted_style),
            Text("", style=muted_style),
        )

        options = [
            ("--dry-run", "Preview action without executing", "action run my-action --dry-run"),
            ("--format json", "JSON output instead of table", "action list --format json"),
            ("--var key=value", "Pass variables to action", "action run my-action --var env=prod"),
        ]
        for i, (opt, desc, ex) in enumerate(options):
            table.add_row(
                Text(opt, style=ss._get_style('semantic', 'secondary', 'magenta')),
                desc,
                Text(f"./escmd.py {ex}", style=muted_style),
                style=ss.get_zebra_style(i) if ss else None,
            )

        self.console.print()
        self.console.print(header_panel)
        self.console.print()
        self.console.print(table)
        self.console.print()

    def handle_action_list(self):
        """List all available actions."""
        from rich.padding import Padding

        actions = self.action_manager.list_actions()

        if not actions:
            self._print_warning("No actions defined")
            return

        ss = self._get_style_system()
        primary = self._sem("primary", "cyan")
        muted = self._sem("muted", "dim white")
        border = self._get_theme_styles().get("border_style", "white")

        if ss:
            table = ss.create_standard_table()
            ss.add_themed_column(table, "Name", "name", no_wrap=True)
            ss.add_themed_column(table, "Description", "default")
            ss.add_themed_column(table, "Parameters", "default")
            ss.add_themed_column(table, "Steps", "count", justify="center")
        else:
            table = Table()
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description", style="white")
            table.add_column("Parameters", style="dim")
            table.add_column("Steps", style="dim", justify="center")

        has_required = False
        for action_name in sorted(actions):
            action = self.action_manager.get_action(action_name)
            description = action.get("description", "No description")
            steps = action.get("steps", [])

            params = action.get("parameters", [])
            param_parts = []
            for param in params:
                name = param["name"]
                if param.get("required", False):
                    name = f"*{name}"
                    has_required = True
                param_parts.append(name)

            param_str = ", ".join(param_parts) if param_parts else "—"
            step_count = str(len(steps)) if steps else "—"

            table.add_row(action_name, description, param_str, step_count)

        # Build hint line
        hint = Text()
        if has_required:
            hint.append("* required  ", style=muted)
        hint.append("action show <name>", style=muted)
        hint.append(" · ", style=muted)
        hint.append("action run <name>", style=muted)

        inner = Table.grid()
        inner.add_column()
        inner.add_row(table)
        inner.add_row(Padding(hint, (1, 0, 0, 0)))

        self.console.print(Panel(
            inner,
            title=f"[{primary}]⚡ Actions[/{primary}]",
            border_style=border,
            padding=(0, 1),
        ))

    def handle_action_show(self):
        """Show details for a specific action."""
        action_name = getattr(self.args, "action_name", None)
        if not action_name:
            self._print_error("Action name required for 'show' command")
            return

        action = self.action_manager.get_action(action_name)
        if not action:
            self._print_error(f"Action '{action_name}' not found")
            return

        ss = self._get_style_system()
        primary = self._sem("primary", "cyan")
        success = self._sem("success", "green")
        muted = self._sem("muted", "dim white")
        warning = self._sem("warning", "yellow")
        info = self._sem("info", "blue")

        content = Text()

        # Description
        description = action.get("description", "No description")
        content.append("Description\n", style="bold white")
        content.append(f"  {description}\n", style=muted)

        # Parameters
        params = action.get("parameters", [])
        content.append("\nParameters\n", style="bold white")
        if params:
            for param in params:
                name = param["name"]
                param_type = param.get("type", "string")
                required = param.get("required", False)
                param_desc = param.get("description", "No description")

                content.append(f"  • ", style=muted)
                content.append(name, style=primary)
                content.append(f"  [{param_type}]", style=muted)
                if required:
                    content.append("  required", style=warning)
                content.append(f"\n    {param_desc}\n", style=muted)

                if param_type == "choice" and "choices" in param:
                    choices_str = ", ".join(param["choices"])
                    content.append(f"    Choices: {choices_str}\n", style=info)
                if "default" in param:
                    content.append(f"    Default: {param['default']}\n", style=muted)
        else:
            content.append("  none\n", style=muted)

        # Steps
        steps = action.get("steps", [])
        if steps:
            content.append(f"\nSteps  ({len(steps)} total)\n", style="bold white")
            for i, step in enumerate(steps, 1):
                step_name = step.get("name", f"Step {i}")
                step_action = step.get("action", "No action defined")
                step_desc = step.get("description", "")

                content.append(f"  {i}. ", style=muted)
                content.append(f"{step_name}\n", style=success)
                content.append(f"     {step_action}\n", style=muted)
                if step_desc:
                    content.append(f"     {step_desc}\n", style=muted)

        border = self._get_theme_styles().get("border_style", "white")
        title_style = primary
        panel = Panel(
            content,
            title=f"[{title_style}]⚡ {action_name}[/{title_style}]",
            border_style=border,
            padding=(1, 2),
        )
        self.console.print(panel)

    def handle_action_run(self):
        """Run a specific action."""
        action_name = getattr(self.args, "action_name", None)
        if not action_name:
            self._print_error("Action name required for 'run' command")
            return

        action = self.action_manager.get_action(action_name)
        if not action:
            self._print_error(f"Action '{action_name}' not found")
            return

        # Get parameters from command line
        params = self._extract_parameters()

        # Validate parameters
        validation_errors = self.action_manager.validate_parameters(action, params)
        if validation_errors:
            error_style = self._sem("error", "red")
            desc_style = self._get_theme_styles().get("panel_styles", {}).get("description", "")
            error_text = Text()
            for i, err in enumerate(validation_errors):
                error_text.append(f"  • {err}", style=desc_style)
                if i < len(validation_errors) - 1:
                    error_text.append("\n")
            self.console.print(Panel(
                error_text,
                title=f"[{error_style}]❌ Parameter Validation Failed[/{error_style}]",
                border_style=error_style,
                padding=(0, 2),
            ))
            return

        # Check for dry run
        dry_run = getattr(self.args, "dry_run", False)

        # Execute action
        self._execute_action(action, params, dry_run)

    def _extract_parameters(self) -> Dict[str, str]:
        """Extract parameters from command line arguments."""
        params = {}

        # Look for parameter arguments (they should be in format --param-name value)
        for arg_name, arg_value in vars(self.args).items():
            if arg_name.startswith("param_") and arg_value is not None:
                param_name = arg_name[6:]  # Remove 'param_' prefix
                params[param_name] = str(arg_value)

        return params

    def _execute_action_json(
        self, action: Dict, params: Dict[str, str], dry_run: bool = False
    ):
        """Execute an action and emit a single JSON object with all steps to stdout."""
        import sys

        action_name = action["name"]
        steps = action.get("steps", [])
        step_variables: Dict[str, str] = {}
        step_results = []

        for i, step in enumerate(steps, 1):
            step_name = step.get("name", f"Step {i}")
            step_action = step.get("action", "")
            step_desc = step.get("description", "")

            record: Dict[str, Any] = {
                "step": i,
                "name": step_name,
                "description": step_desc,
            }

            # Evaluate condition
            condition = step.get("condition")
            if condition:
                try:
                    condition_result = Template(condition).render(**{**params, **step_variables})
                    if not self._evaluate_condition(condition_result):
                        record["status"] = "skipped"
                        record["reason"] = "condition not met"
                        step_results.append(record)
                        continue
                except Exception as e:
                    record["status"] = "error"
                    record["error"] = f"condition evaluation failed: {e}"
                    step_results.append(record)
                    continue

            # Render command
            try:
                rendered_command = Template(step_action).render(**{**params, **step_variables})
            except Exception as e:
                record["status"] = "error"
                record["error"] = f"command render failed: {e}"
                step_results.append(record)
                continue

            record["command"] = rendered_command

            if dry_run:
                record["status"] = "dry_run"
                step_results.append(record)
                continue

            # Execute
            success_flag, command_output = self._execute_command_with_output(rendered_command)

            if success_flag and command_output:
                self._process_step_output_capture(step, command_output, step_variables, i)

            record["status"] = "success" if success_flag else "failed"
            output = command_output.strip() if command_output else ""
            try:
                record["output"] = json.loads(output)
            except (json.JSONDecodeError, ValueError):
                record["output"] = output

            step_results.append(record)

        failed = [s for s in step_results if s.get("status") == "failed"]
        result = {
            "action": action_name,
            "total_steps": len(steps),
            "successful": len([s for s in step_results if s.get("status") == "success"]),
            "failed": len(failed),
            "status": "failed" if failed else ("dry_run" if dry_run else "success"),
            "steps": step_results,
        }
        sys.stdout.write(json.dumps(result, indent=2) + "\n")

    def _execute_action(
        self, action: Dict, params: Dict[str, str], dry_run: bool = False
    ):
        """Execute an action with given parameters."""
        # Delegate to JSON formatter when --format json is requested
        if getattr(self.args, "output_format", None) == "json":
            self._execute_action_json(action, params, dry_run)
            return

        action_name = action["name"]
        steps = action.get("steps", [])

        # Check for quiet/summary modes
        quiet_mode = getattr(self.args, "quiet", False)
        summary_only = getattr(self.args, "summary_only", False)

        # Semantic styles
        primary = self._sem("primary", "cyan")
        success = self._sem("success", "green")
        warning = self._sem("warning", "yellow")
        error_style = self._sem("error", "red")
        muted = self._sem("muted", "dim white")
        info = self._sem("info", "blue")
        border = self._get_theme_styles().get("border_style", "white")

        if not steps:
            if not summary_only:
                self._print_warning("Action has no steps to execute")
            return

        if not summary_only:
            description = action.get("description", "")
            header_text = Text()
            header_text.append(action_name, style=f"bold {primary}")
            if description:
                header_text.append(f"\n{description}", style=muted)
            if params:
                header_text.append("\n")
                for k, v in params.items():
                    header_text.append(f"  {k} ", style=muted)
                    header_text.append(v, style=f"bold {info}")
            if dry_run:
                header_text.append(f"\n\n  ⚠ DRY RUN — no commands will be executed", style=f"bold {warning}")
            self.console.print(Panel(
                header_text,
                title=f"[{primary}]⚡ Action[/{primary}]",
                border_style=border,
                padding=(0, 1),
            ))

        # Execute each step
        failed_steps = []
        step_variables = {}  # Store variables from step outputs

        if not summary_only:
            self.console.print()  # Add some space

        for i, step in enumerate(steps, 1):
            step_name = step.get("name", f"Step {i}")
            step_action = step.get("action", "")
            step_desc = step.get("description", "")

            # Check condition if present
            condition = step.get("condition")
            if condition:
                try:
                    template = Template(condition)
                    template_vars = {**params, **step_variables}
                    condition_result = template.render(**template_vars)
                    if not self._evaluate_condition(condition_result):
                        self._print_muted(f"  ↷ Skipping step {i}: {step_name} (condition not met)")
                        continue
                except Exception as e:
                    self._print_error(f"Error evaluating condition for step {i}: {e}")
                    failed_steps.append((i, step_name, str(e)))
                    continue

            # Render command with parameters and step variables
            try:
                template = Template(step_action)
                template_vars = {**params, **step_variables}
                rendered_command = template.render(**template_vars)
            except Exception as e:
                self._print_error(f"Error rendering command for step {i}: {e}")
                failed_steps.append((i, step_name, str(e)))
                continue

            # Create step header (unless in summary-only mode)
            if not summary_only:
                if quiet_mode:
                    step_label = Text()
                    step_label.append(f"Step {i}/{len(steps)}: ", style=muted)
                    step_label.append(step_name, style=f"bold {primary}")
                    self.console.print(step_label)
                else:
                    step_content = Text()
                    step_content.append(step_name, style=f"bold {primary}")
                    if step_desc:
                        step_content.append(f"\n{step_desc}", style=muted)
                    step_content.append("\n")
                    step_content.append("Command: ", style=muted)
                    step_content.append(rendered_command, style=info)

                    step_panel = Panel(
                        step_content,
                        title=f"[{muted}]Step {i}/{len(steps)}[/{muted}]",
                        border_style=border,
                        padding=(0, 1),
                    )
                    self.console.print(step_panel)

            if dry_run:
                if not summary_only:
                    self.console.print(f"  [{warning}]→ Would execute (dry run)[/{warning}]")
                    if not quiet_mode:
                        self.console.print()
                continue

            # Check for confirmation if required
            if step.get("confirm", False):
                if getattr(self.args, "yes", False):
                    self._print_muted("  → Auto-confirmed (--yes flag)")
                elif not Confirm.ask("Execute this step?", default=True):
                    self._print_muted("  → Skipped by user")
                    self.console.print()
                    continue

            # Execute the command
            success_flag, command_output = self._execute_command_with_output(
                rendered_command
            )

            # Process step output capture if specified
            if success_flag and command_output:
                self._process_step_output_capture(
                    step, command_output, step_variables, i
                )

            # Display results (unless in summary-only mode)
            if not summary_only:
                if success_flag:
                    if quiet_mode or getattr(self.args, "compact", False):
                        self._print_success("Step completed")
                    else:
                        self._print_success("Step completed successfully")
                        if command_output:
                            self._display_command_output(command_output, rendered_command)
                else:
                    self.console.print(f"[{error_style}]✗ Step failed[/{error_style}]")
                    if command_output:
                        self._display_text_output(command_output)

                if not quiet_mode:
                    self.console.print()

            if not success_flag:
                failed_steps.append((i, step_name, "Command execution failed"))

                if getattr(self.args, "yes", False):
                    self._print_muted("  → Auto-continuing (--yes flag)")
                elif not Confirm.ask(
                    "Step failed. Continue with remaining steps?", default=False
                ):
                    break

        # Summary
        total_steps = len(steps)
        failed_count = len(failed_steps)
        success_count = total_steps - failed_count

        if summary_only or quiet_mode or getattr(self.args, "compact", False):
            if failed_count == 0:
                status_icon = f"[{success}]✓[/{success}]"
            else:
                status_icon = f"[{error_style}]✗ ({failed_count} failed)[/{error_style}]"
            self.console.print(
                f"\n{status_icon} [{muted}]Action '{action_name}' completed:[/{muted}] "
                f"[{success}]{success_count}[/{success}]/[{muted}]{total_steps}[/{muted}] steps successful"
            )
        else:
            # Styled summary panel
            summary_text = Text()
            summary_text.append("Total steps:  ", style=muted)
            summary_text.append(f"{total_steps}\n", style="bold white")
            summary_text.append("Successful:   ", style=muted)
            summary_text.append(f"{success_count}\n", style=f"bold {success}")
            summary_text.append("Failed:       ", style=muted)
            failed_style = error_style if failed_count > 0 else muted
            summary_text.append(f"{failed_count}", style=f"bold {failed_style}")

            panel_type = "success" if failed_count == 0 else "error"
            icon = "✅" if failed_count == 0 else "❌"
            ss = self._get_style_system()
            if ss:
                summary_panel = getattr(ss, f"create_{panel_type}_panel")(
                    summary_text, f"{icon} Action Summary: {action_name}"
                )
            else:
                summary_panel = Panel(
                    summary_text,
                    title=f"{icon} Action Summary: {action_name}",
                    border_style=success if failed_count == 0 else error_style,
                    padding=(1, 2),
                )
            self.console.print(summary_panel)

        if failed_steps and not summary_only:
            failed_text = Text()
            for step_num, step_name, err in failed_steps:
                failed_text.append(f"  • Step {step_num}: ", style=muted)
                failed_text.append(step_name, style=f"bold {error_style}")
                failed_text.append(f" — {err}\n", style=error_style)
            ss = self._get_style_system()
            if ss:
                self.console.print(ss.create_error_panel(failed_text, "Failed Steps"))
            else:
                self.console.print(f"\n[{error_style}]Failed steps:[/{error_style}]")
                self.console.print(failed_text)

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a simple condition string."""
        # Simple evaluation for basic conditions
        # This could be expanded to support more complex logic
        if condition.lower() in ("true", "1", "yes"):
            return True
        elif condition.lower() in ("false", "0", "no", ""):
            return False

        # Try to evaluate as Python expression (be careful with security)
        try:
            # Only allow simple comparisons for security
            if any(op in condition for op in ["==", "!=", ">", "<", ">=", "<="]):
                # Simple whitelist approach for safety
                allowed_chars = set(
                    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'\"=!<> "
                )
                if all(c in allowed_chars for c in condition):
                    return eval(condition)
        except:
            pass

        return bool(condition)

    def _supports_json_format(self, command: str) -> bool:
        """Check if a command supports --format json option."""
        json_commands = [
            "health",
            "health-detail",
            "nodes",
            "indices",
            "allocation",
            "storage",
            "shards",
            "snapshots",
            "cluster-settings",
            "masters",
            "current-master",
            "ping",
            "recovery",
            "shard-colocation",
            "dangling",
            "templates",
            "rollover",
        ]

        command_parts = command.split()
        if command_parts:
            base_command = command_parts[0]
            return base_command in json_commands
        return False

    def _add_json_format_if_supported(self, command: str) -> str:
        """Add --format json to command if it supports it and doesn't already have format specified."""
        # Skip JSON formatting when using native output mode
        if (
            self.use_native_output
            or not self.auto_format_json
            or not self._supports_json_format(command)
        ):
            return command

        # Check if format is already specified
        if "--format" in command:
            return command

        # Add --format json
        return f"{command} --format json"

    def _display_command_output(self, output: str, original_command: str):
        """Display command output in a nice format."""
        # Skip output display in quiet or summary-only modes
        if getattr(self.args, "quiet", False) or getattr(
            self.args, "summary_only", False
        ):
            return

        # For native output mode, output was already displayed directly during execution
        if self.use_native_output:
            return

        # Skip if no output or empty output
        if not output or not output.strip():
            return

        # Skip if show_command_output is False (this handles compact mode)
        if not self.show_command_output:
            return

        # Check if output looks like JSON at the end
        lines = output.strip().split("\n")
        json_line = None
        text_lines = []

        # Look for JSON at the end of output
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line and self._is_json_output(line):
                json_line = line
                text_lines = lines[:i] + lines[i + 1 :]
                break

        if not json_line:
            text_lines = lines

        # Display text output first (if any meaningful content)
        if text_lines:
            self._display_enhanced_text_output(text_lines, original_command)

        # Display JSON separately if found
        if json_line:
            try:
                json_data = json.loads(json_line)
                if not getattr(self.args, "compact", False):
                    json_renderable = JSON(json.dumps(json_data, indent=2))
                    ss = self._get_style_system()
                    if ss:
                        result_panel = ss.create_success_panel(json_renderable, "Configuration Applied")
                    else:
                        result_panel = Panel(
                            json_renderable,
                            title="Configuration Applied",
                            border_style="dim green",
                            padding=(1, 1),
                        )
                    self.console.print(result_panel)
            except json.JSONDecodeError:
                pass

    def _is_json_output(self, output: str) -> bool:
        """Check if output appears to be JSON."""
        try:
            json.loads(output)
            return True
        except (json.JSONDecodeError, ValueError):
            return False

    def _display_text_output(self, output: str):
        """Display non-JSON output in a nice format."""
        lines = output.split("\n") if isinstance(output, str) else output
        self._display_enhanced_text_output(lines, "")

    def _display_enhanced_text_output(self, lines, original_command: str):
        """Enhanced text output display with better formatting."""
        cleaned_lines = []

        for line in lines:
            # Skip empty lines and progress indicators
            if line.strip() and not self._is_progress_line(line):
                cleaned_lines.append(line.rstrip())

        if not cleaned_lines:
            return

        # Enhanced processing for common patterns
        processed_lines = []
        i = 0
        while i < len(cleaned_lines):
            line = cleaned_lines[i]

            # Format host lists better
            if ("Original value:" in line or "New value:" in line) and i + 1 < len(
                cleaned_lines
            ):
                next_line = cleaned_lines[i + 1]
                if "," in next_line and len(next_line) > 80:
                    # Format as a nice list
                    hosts = [h.strip() for h in next_line.split(",")]
                    processed_lines.append(line)
                    if len(hosts) > 6:
                        # Show first few, count, and last few
                        processed_lines.append("  " + ", ".join(hosts[:3]))
                        processed_lines.append(
                            f"  ... ({len(hosts) - 6} more hosts) ..."
                        )
                        processed_lines.append("  " + ", ".join(hosts[-3:]))
                    else:
                        # Show all hosts, but nicely formatted
                        for j in range(0, len(hosts), 3):
                            group = hosts[j : j + 3]
                            processed_lines.append("  " + ", ".join(group))
                    i += 2  # Skip the next line as we processed it
                    continue

            processed_lines.append(line)
            i += 1

        # Show only the most relevant lines
        if len(processed_lines) > self.max_output_lines:
            mid_point = self.max_output_lines // 2
            display_lines = (
                processed_lines[:mid_point]
                + [
                    f"... ({len(processed_lines) - self.max_output_lines} more lines) ..."
                ]
                + processed_lines[-mid_point:]
            )
        else:
            display_lines = processed_lines

        if display_lines:
            output_text = "\n".join(display_lines)
            ss = self._get_style_system()
            if ss:
                result_panel = ss.create_info_panel(output_text, "Command Output")
            else:
                result_panel = Panel(
                    output_text, title="Command Output", border_style="cyan", padding=(1, 1)
                )
            self.console.print(result_panel)

    def _is_progress_line(self, line: str) -> bool:
        """Check if a line is a progress indicator or other noise."""
        noise_patterns = [
            r"^\s*━+",  # Progress bars
            r"^\s*\d+%",  # Percentage indicators
            r"Executing steps\.\.\.",  # Our own progress messages
            r"pyenv:",  # pyenv warnings
        ]

        for pattern in noise_patterns:
            if re.match(pattern, line):
                return True
        return False

    def _execute_command_with_output(self, command: str) -> Tuple[bool, str]:
        """Execute an escmd command and capture output."""
        try:
            # Add JSON format if supported (unless using native output)
            enhanced_command = self._add_json_format_if_supported(command)

            # Parse the command into parts
            command_parts = enhanced_command.split()
            if not command_parts:
                return False, ""

            # Import the CLI argument parser to properly parse commands
            from cli.argument_parser import create_argument_parser
            import shlex
            import io
            import sys
            from contextlib import redirect_stdout, redirect_stderr

            # Use shlex to properly split the command with quotes
            try:
                command_args = shlex.split(enhanced_command)
            except ValueError:
                # If shlex fails, fall back to simple split
                command_args = enhanced_command.split()

            # Create argument parser and parse the command
            parser = create_argument_parser()

            # Add the location argument if it exists
            if self.args.locations:
                command_args = ["-l", self.args.locations] + command_args

            try:
                parsed_args = parser.parse_args(command_args)
            except SystemExit:
                # Parser exits on error, catch and return False
                return False, f"Invalid command syntax: {enhanced_command}"

            # Import and create command handler
            from command_handler import CommandHandler

            # For native output mode, execute directly without capturing
            if self.use_native_output:
                try:
                    # Create a new command handler and execute
                    command_handler = CommandHandler(
                        self.es_client,
                        parsed_args,
                        self.console,
                        self.config_file,
                        self.location_config,
                        self.current_location,
                    )

                    # Execute the command directly (no output capture)
                    command_handler.execute()
                    return (
                        True,
                        "",
                    )  # Return empty string since output was displayed directly

                except Exception as e:
                    error_msg = f"Command execution error: {str(e)}"
                    return False, error_msg

            # For standard mode, capture output
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    # Create a new command handler and execute
                    command_handler = CommandHandler(
                        self.es_client,
                        parsed_args,
                        self.console,
                        self.config_file,
                        self.location_config,
                        self.current_location,
                    )

                    # Execute the command
                    command_handler.execute()

                # Get captured output
                stdout_output = stdout_capture.getvalue()
                stderr_output = stderr_capture.getvalue()

                # Combine outputs, prioritizing stdout
                combined_output = stdout_output
                if stderr_output and not stdout_output:
                    combined_output = stderr_output

                return True, combined_output

            except Exception as e:
                error_msg = f"Command execution error: {str(e)}"
                return False, error_msg

        except Exception as e:
            error_msg = f"Error executing command '{command}': {e}"
            return False, error_msg

    def _should_summarize_json(self, json_data) -> bool:
        """Determine if JSON output should be summarized instead of shown in full."""
        json_str = json.dumps(json_data)
        return len(json_str) > 2000 or json_str.count("\n") > 20

    def _create_json_summary(self, json_data, command: str) -> str:
        """Create a summary of JSON data based on command type."""
        summary_lines = []

        if isinstance(json_data, dict):
            if "status" in json_data:
                # Health-related commands
                summary_lines.append(
                    f"🏥 Cluster Status: [bold]{json_data.get('status', 'unknown').upper()}[/bold]"
                )
                if "number_of_nodes" in json_data:
                    summary_lines.append(
                        f"📊 Nodes: {json_data.get('number_of_nodes')}"
                    )
                if "active_primary_shards" in json_data:
                    summary_lines.append(
                        f"🟢 Active Primary Shards: {json_data.get('active_primary_shards')}"
                    )
                if "relocating_shards" in json_data:
                    summary_lines.append(
                        f"🔄 Relocating Shards: {json_data.get('relocating_shards')}"
                    )

            elif "cluster_name" in json_data:
                # Node information
                summary_lines.append(
                    f"🏛️  Cluster: [bold]{json_data.get('cluster_name')}[/bold]"
                )

            # Show first few key-value pairs for other data types
            if not summary_lines and isinstance(json_data, dict):
                for i, (key, value) in enumerate(json_data.items()):
                    if i >= 5:
                        summary_lines.append(
                            f"... and {len(json_data) - 5} more fields"
                        )
                        break
                    summary_lines.append(
                        f"• {key}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}"
                    )

        elif isinstance(json_data, list):
            summary_lines.append(f"📋 Total Items: [bold]{len(json_data)}[/bold]")
            if json_data and isinstance(json_data[0], dict):
                # Show sample of first item's keys
                sample_keys = list(json_data[0].keys())[:5]
                summary_lines.append(f"📝 Sample Fields: {', '.join(sample_keys)}")

        if not summary_lines:
            summary_lines = [f"📊 Data Type: {type(json_data).__name__}"]

        summary_lines.append(
            f"\n[{self._sem('muted', 'dim white')}]💡 Use --format table for detailed tabular view[/{self._sem('muted', 'dim white')}]"
        )
        return "\n".join(summary_lines)

    def _process_step_output_capture(
        self, step: Dict, command_output: str, step_variables: Dict, step_num: int
    ):
        """Process step output capture and extract variables."""
        capture_config = step.get("capture", step.get("output"))
        if not capture_config:
            return

        try:
            # Handle different capture formats
            if isinstance(capture_config, str):
                # Simple variable name - store entire output
                step_variables[capture_config] = command_output.strip()
            elif isinstance(capture_config, dict):
                # Advanced capture with extraction
                for var_name, extraction_config in capture_config.items():
                    if isinstance(extraction_config, str):
                        # JSONPath or regex extraction
                        if extraction_config.startswith("$."):
                            # JSONPath extraction
                            extracted_value = self._extract_json_path(
                                command_output, extraction_config
                            )
                        elif extraction_config.startswith("regex:"):
                            # Regex extraction
                            pattern = extraction_config[6:]  # Remove 'regex:' prefix
                            extracted_value = self._extract_regex(
                                command_output, pattern
                            )
                        else:
                            # Store the config value directly (literal)
                            extracted_value = extraction_config
                    elif isinstance(extraction_config, dict):
                        # Advanced extraction config
                        if "jsonpath" in extraction_config:
                            extracted_value = self._extract_json_path(
                                command_output, extraction_config["jsonpath"]
                            )
                        elif "regex" in extraction_config:
                            extracted_value = self._extract_regex(
                                command_output, extraction_config["regex"]
                            )
                            # Apply optional transform
                            if "transform" in extraction_config:
                                extracted_value = self._apply_transform(
                                    extracted_value, extraction_config["transform"]
                                )
                        else:
                            extracted_value = str(extraction_config)
                    else:
                        extracted_value = str(extraction_config)

                    step_variables[var_name] = extracted_value

                    # Debug output in verbose mode
                    if not getattr(self.args, "quiet", False):
                        self._print_muted(f"  → Captured {var_name}: {extracted_value}")

        except Exception as e:
            self._print_warning(f"Failed to capture step output: {e}")

    def _extract_json_path(self, output: str, jsonpath: str) -> str:
        """Extract value from JSON output using JSONPath-like syntax."""
        try:
            # Try to find JSON in the output
            json_data = None

            # First try parsing the entire output as JSON
            try:
                json_data = json.loads(output.strip())
            except json.JSONDecodeError:
                # Try to find JSON in individual lines
                for line in output.split("\n"):
                    line = line.strip()
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            json_data = json.loads(line)
                            break
                        except json.JSONDecodeError:
                            continue

            if json_data is None:
                return ""

            # Simple JSONPath implementation for basic cases
            # Remove leading $. if present
            path = jsonpath[2:] if jsonpath.startswith("$.") else jsonpath

            # Split path by dots
            parts = path.split(".")
            current = json_data

            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif isinstance(current, list) and part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return ""
                else:
                    return ""

            return str(current)

        except Exception as e:
            self._print_warning(f"JSONPath extraction failed: {e}")
            return ""

    def _extract_regex(self, output: str, pattern: str) -> str:
        """Extract value from output using regex."""
        try:
            match = re.search(pattern, output, re.MULTILINE | re.DOTALL)
            if match:
                # Return first group if available, otherwise full match
                return match.group(1) if match.groups() else match.group(0)
            return ""
        except Exception as e:
            self._print_warning(f"Regex extraction failed: {e}")
            return ""

    def _apply_transform(self, value: str, transform: str) -> str:
        """Apply transformation to extracted value."""
        try:
            if transform == "strip":
                return value.strip()
            elif transform == "lower":
                return value.lower()
            elif transform == "upper":
                return value.upper()
            elif transform.startswith("replace:"):
                # Format: replace:old:new
                parts = transform.split(":", 2)
                if len(parts) == 3:
                    return value.replace(parts[1], parts[2])
            elif transform.startswith("regex_replace:"):
                # Format: regex_replace:pattern:replacement
                parts = transform.split(":", 2)
                if len(parts) == 3:
                    return re.sub(parts[1], parts[2], value)
        except Exception as e:
            self._print_warning(f"Transform failed: {e}")

        return value

    def _execute_command(self, command: str) -> bool:
        """Execute an escmd command (legacy method - use _execute_command_with_output instead)."""
        success, _ = self._execute_command_with_output(command)
        return success
