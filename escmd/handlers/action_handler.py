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
            self.console.print(f"[red]Error loading actions: {e}[/red]")
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

    def handle_action(self):
        """Handle action commands."""
        if not self.action_manager:
            self.console.print(
                "[red]Actions system unavailable due to loading errors[/red]"
            )
            return

        # Get subcommand
        action_cmd = getattr(self.args, "action_cmd", "list")

        if action_cmd == "list":
            self.handle_action_list()
        elif action_cmd == "show":
            self.handle_action_show()
        elif action_cmd == "run":
            self.handle_action_run()
        else:
            self.console.print(f"[red]Unknown action command: {action_cmd}[/red]")

    def handle_action_list(self):
        """List all available actions."""
        actions = self.action_manager.list_actions()

        if not actions:
            self.console.print("[yellow]No actions defined[/yellow]")
            return

        table = Table(title="Available Actions")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Parameters", style="dim")

        for action_name in sorted(actions):
            action = self.action_manager.get_action(action_name)
            description = action.get("description", "No description")

            # Format parameters
            params = action.get("parameters", [])
            param_names = []
            for param in params:
                name = param["name"]
                if param.get("required", False):
                    name = f"*{name}"
                param_names.append(name)

            param_str = ", ".join(param_names) if param_names else "none"

            table.add_row(action_name, description, param_str)

        self.console.print(table)

        if any(
            p.get("required", False)
            for action in [self.action_manager.get_action(name) for name in actions]
            for p in action.get("parameters", [])
        ):
            self.console.print("\n[dim]* indicates required parameter[/dim]")

    def handle_action_show(self):
        """Show details for a specific action."""
        action_name = getattr(self.args, "action_name", None)
        if not action_name:
            self.console.print("[red]Action name required for 'show' command[/red]")
            return

        action = self.action_manager.get_action(action_name)
        if not action:
            self.console.print(f"[red]Action '{action_name}' not found[/red]")
            return

        # Create action details panel
        content = []

        # Description
        description = action.get("description", "No description")
        content.append(f"[bold]Description:[/bold] {description}")

        # Parameters
        params = action.get("parameters", [])
        if params:
            content.append("\n[bold]Parameters:[/bold]")
            for param in params:
                name = param["name"]
                param_type = param.get("type", "string")
                required = " (required)" if param.get("required", False) else ""
                param_desc = param.get("description", "No description")

                content.append(
                    f"  • [cyan]{name}[/cyan] [{param_type}]{required}: {param_desc}"
                )

                # Show choices for choice type
                if param_type == "choice" and "choices" in param:
                    choices_str = ", ".join(param["choices"])
                    content.append(f"    Choices: {choices_str}")

                # Show default value
                if "default" in param:
                    content.append(f"    Default: {param['default']}")
        else:
            content.append("\n[bold]Parameters:[/bold] none")

        # Steps
        steps = action.get("steps", [])
        if steps:
            content.append(f"\n[bold]Steps ({len(steps)}):[/bold]")
            for i, step in enumerate(steps, 1):
                step_name = step.get("name", f"Step {i}")
                step_action = step.get("action", "No action defined")
                step_desc = step.get("description", "")

                content.append(f"  {i}. [green]{step_name}[/green]")
                content.append(f"     Command: [dim]{step_action}[/dim]")
                if step_desc:
                    content.append(f"     {step_desc}")

        panel_content = "\n".join(content)
        panel = Panel(
            panel_content, title=f"Action: {action_name}", border_style="blue"
        )
        self.console.print(panel)

    def handle_action_run(self):
        """Run a specific action."""
        action_name = getattr(self.args, "action_name", None)
        if not action_name:
            self.console.print("[red]Action name required for 'run' command[/red]")
            return

        action = self.action_manager.get_action(action_name)
        if not action:
            self.console.print(f"[red]Action '{action_name}' not found[/red]")
            return

        # Get parameters from command line
        params = self._extract_parameters()

        # Validate parameters
        validation_errors = self.action_manager.validate_parameters(action, params)
        if validation_errors:
            self.console.print("[red]Parameter validation errors:[/red]")
            for error in validation_errors:
                self.console.print(f"  • {error}")
            return

        # Check for dry run
        dry_run = getattr(self.args, "dry_run", False)

        if dry_run:
            self.console.print(
                f"[yellow]DRY RUN MODE - No commands will be executed[/yellow]"
            )

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

    def _execute_action(
        self, action: Dict, params: Dict[str, str], dry_run: bool = False
    ):
        """Execute an action with given parameters."""
        action_name = action["name"]
        steps = action.get("steps", [])

        # Check for quiet/summary modes
        quiet_mode = getattr(self.args, "quiet", False)
        summary_only = getattr(self.args, "summary_only", False)

        if not steps:
            if not summary_only:
                self.console.print("[yellow]Action has no steps to execute[/yellow]")
            return

        if not summary_only:
            self.console.print(
                f"\n[bold blue]Executing action: {action_name}[/bold blue]"
            )
            if params:
                param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
                self.console.print(f"[dim]Parameters: {param_str}[/dim]")

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
                    # Merge params and step_variables for template rendering
                    template_vars = {**params, **step_variables}
                    condition_result = template.render(**template_vars)
                    # Evaluate the condition (simple evaluation for now)
                    if not self._evaluate_condition(condition_result):
                        self.console.print(
                            f"[dim]Skipping step {i}: {step_name} (condition not met)[/dim]"
                        )
                        continue
                except Exception as e:
                    self.console.print(
                        f"[red]Error evaluating condition for step {i}: {e}[/red]"
                    )
                    failed_steps.append((i, step_name, str(e)))
                    continue

            # Render command with parameters and step variables
            try:
                template = Template(step_action)
                # Merge params and step_variables for template rendering
                template_vars = {**params, **step_variables}
                rendered_command = template.render(**template_vars)
            except Exception as e:
                self.console.print(
                    f"[red]Error rendering command for step {i}: {e}[/red]"
                )
                failed_steps.append((i, step_name, str(e)))
                continue

            # Create step header (unless in summary-only mode)
            if not summary_only:
                if quiet_mode:
                    self.console.print(f"[dim]Step {i}/{len(steps)}:[/dim] {step_name}")
                else:
                    step_panel = Panel(
                        f"[bold]{step_name}[/bold]\n"
                        + (f"[dim]{step_desc}[/dim]\n" if step_desc else "")
                        + f"[cyan]Command:[/cyan] {rendered_command}",
                        title=f"Step {i}/{len(steps)}",
                        border_style="blue",
                        padding=(0, 1),
                    )
                    self.console.print(step_panel)

            if dry_run:
                if not summary_only:
                    if quiet_mode:
                        self.console.print(
                            "[yellow]  → Would execute (dry run)[/yellow]"
                        )
                    else:
                        self.console.print(
                            "[yellow]  → Would execute (dry run)[/yellow]"
                        )
                        self.console.print()  # Add space between steps
                continue

            # Check for confirmation if required
            if step.get("confirm", False):
                # Skip confirmation if --yes flag is provided
                if getattr(self.args, "yes", False):
                    self.console.print("[dim]  → Auto-confirmed (--yes flag)[/dim]")
                elif not Confirm.ask(f"Execute this step?", default=True):
                    self.console.print("[yellow]  → Skipped by user[/yellow]")
                    self.console.print()  # Add space between steps
                    continue

            # Execute the command
            success, command_output = self._execute_command_with_output(
                rendered_command
            )

            # Process step output capture if specified
            if success and command_output:
                self._process_step_output_capture(
                    step, command_output, step_variables, i
                )

            # Display results (unless in summary-only mode)
            if not summary_only:
                if success:
                    if quiet_mode or getattr(self.args, "compact", False):
                        self.console.print("[green]✓ Step completed[/green]")
                    else:
                        self.console.print(
                            "[green]✓ Step completed successfully[/green]"
                        )
                        if command_output:
                            self._display_command_output(
                                command_output, rendered_command
                            )
                else:
                    self.console.print("[red]✗ Step failed[/red]")
                    if command_output:
                        # Show error output for failures, but format it nicely
                        self._display_text_output(command_output)

                if not quiet_mode:
                    self.console.print()  # Add space between steps

            if not success:
                failed_steps.append((i, step_name, "Command execution failed"))

                # Ask if user wants to continue
                if getattr(self.args, "yes", False):
                    self.console.print("[dim]  → Auto-continuing (--yes flag)[/dim]")
                elif not Confirm.ask(
                    "Step failed. Continue with remaining steps?", default=False
                ):
                    break

        # Summary
        total_steps = len(steps)
        failed_count = len(failed_steps)
        success_count = total_steps - failed_count

        # Enhanced summary with better formatting
        if summary_only or quiet_mode or getattr(self.args, "compact", False):
            status = (
                "[green]✓[/green]"
                if failed_count == 0
                else f"[red]✗ ({failed_count} failed)[/red]"
            )
            self.console.print(
                f"\n{status} Action '{action_name}' completed: {success_count}/{total_steps} steps successful"
            )
        else:
            self.console.print(f"\n[bold]Action execution summary:[/bold]")
            self.console.print(f"  • Total steps: {total_steps}")
            self.console.print(f"  • [green]Successful: {success_count}[/green]")
            self.console.print(f"  • [red]Failed: {failed_count}[/red]")

        if failed_steps and not summary_only:
            self.console.print("\n[red]Failed steps:[/red]")
            for step_num, step_name, error in failed_steps:
                self.console.print(f"  • Step {step_num}: {step_name} - {error}")

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
            "\n[dim]💡 Use --format table for detailed tabular view[/dim]"
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
                        self.console.print(
                            f"[dim]  → Captured {var_name}: {extracted_value}[/dim]"
                        )

        except Exception as e:
            self.console.print(
                f"[yellow]Warning: Failed to capture step output: {e}[/yellow]"
            )

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
            self.console.print(
                f"[yellow]Warning: JSONPath extraction failed: {e}[/yellow]"
            )
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
            self.console.print(
                f"[yellow]Warning: Regex extraction failed: {e}[/yellow]"
            )
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
            self.console.print(f"[yellow]Warning: Transform failed: {e}[/yellow]")

        return value

    def _execute_command(self, command: str) -> bool:
        """Execute an escmd command (legacy method - use _execute_command_with_output instead)."""
        success, _ = self._execute_command_with_output(command)
        return success
