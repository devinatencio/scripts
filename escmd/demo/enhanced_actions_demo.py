#!/usr/bin/env python3
"""
Demo script showing the enhanced action system with output capture and JSON extraction.
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path so we can import escmd modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from handlers.action_handler import ActionHandler, ActionManager
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import argparse

console = Console()


def demo_rollover_action():
    """Demonstrate the enhanced rollover action with output capture."""

    console.print(
        "\n[bold blue]Enhanced Actions Demo: Rollover with Output Capture[/bold blue]\n"
    )

    # Show the action configuration
    action_manager = ActionManager()
    roll_action = action_manager.get_action("roll-igl")

    if not roll_action:
        console.print("[red]Error: roll-igl action not found in actions.yml[/red]")
        return

    # Display action configuration
    console.print("[bold]Action Configuration:[/bold]")
    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column("Property", style="bold cyan")
    config_table.add_column("Value", style="white")

    config_table.add_row("Name", roll_action["name"])
    config_table.add_row("Description", roll_action.get("description", "N/A"))
    config_table.add_row("Steps", str(len(roll_action.get("steps", []))))

    console.print(config_table)
    console.print()

    # Show step details
    console.print("[bold]Step Details:[/bold]")
    for i, step in enumerate(roll_action.get("steps", []), 1):
        step_panel = Panel(
            f"[bold]{step.get('name', f'Step {i}')}[/bold]\n"
            f"[cyan]Command:[/cyan] {step.get('action', '')}\n"
            f"[dim]{step.get('description', '')}[/dim]\n"
            + (
                f"[yellow]Capture:[/yellow] {step.get('capture', 'None')}\n"
                if step.get("capture")
                else ""
            )
            + (
                f"[green]Condition:[/green] {step.get('condition', 'Always')}"
                if step.get("condition")
                else "[green]Condition:[/green] Always"
            ),
            title=f"Step {i}",
            border_style="blue",
        )
        console.print(step_panel)

    console.print()


def demo_json_extraction():
    """Demonstrate JSON path extraction capabilities."""

    console.print("\n[bold blue]JSON Extraction Demo[/bold blue]\n")

    # Sample rollover response
    sample_response = {
        "acknowledged": True,
        "shards_acknowledged": True,
        "old_index": ".ds-rehydrated_ams02-c01-logs-igl-main-2025.09.24-000020",
        "new_index": ".ds-rehydrated_ams02-c01-logs-igl-main-2025.09.25-000022",
        "rolled_over": True,
        "dry_run": False,
        "conditions": {"max_age": "30d", "max_docs": 1000000},
    }

    console.print("[bold]Sample Rollover Response:[/bold]")
    console.print(json.dumps(sample_response, indent=2))
    console.print()

    # Create a mock action handler to test extraction
    mock_args = argparse.Namespace(quiet=False)
    handler = ActionHandler(None, mock_args, console, None, None, None)

    # Test different JSONPath extractions
    test_cases = [
        ("$.old_index", "Extract old index name"),
        ("$.new_index", "Extract new index name"),
        ("$.rolled_over", "Check if rollover succeeded"),
        ("$.dry_run", "Check if it was a dry run"),
        ("$.conditions.max_age", "Extract max age condition"),
    ]

    console.print("[bold]JSONPath Extraction Examples:[/bold]")
    extraction_table = Table()
    extraction_table.add_column("JSONPath", style="cyan")
    extraction_table.add_column("Description", style="white")
    extraction_table.add_column("Extracted Value", style="green")

    sample_json_str = json.dumps(sample_response)

    for jsonpath, description in test_cases:
        extracted = handler._extract_json_path(sample_json_str, jsonpath)
        extraction_table.add_row(jsonpath, description, str(extracted))

    console.print(extraction_table)
    console.print()


def demo_action_yaml_syntax():
    """Show the YAML syntax for enhanced actions."""

    console.print("\n[bold blue]Enhanced Action YAML Syntax[/bold blue]\n")

    yaml_example = """# Enhanced action with output capture and chaining
- name: roll-igl
  description: "Rollover datastream and delete the old index"
  steps:
    - name: Rollover Indice
      action: rollover rehydrated_ams02-c01-logs-igl-main --format json
      description: "Rollover the datastream and capture the old index name"
      capture:
        old_index_name: "$.old_index"
        new_index_name: "$.new_index"
        rollover_success: "$.rolled_over"
    - name: Delete Old Index
      action: indices --delete {{ old_index_name }}
      description: "Delete the old index that was rolled over"
      condition: "{{ rollover_success }}"
      confirm: true"""

    console.print("[bold]YAML Configuration:[/bold]")
    yaml_panel = Panel(yaml_example, title="actions.yml", border_style="green")
    console.print(yaml_panel)
    console.print()


def demo_usage_examples():
    """Show usage examples for the enhanced actions."""

    console.print("\n[bold blue]Usage Examples[/bold blue]\n")

    examples = [
        ("List all actions", "action list"),
        ("Show action details", "action show roll-igl"),
        ("Run action (dry run)", "action run roll-igl --dry-run"),
        ("Run action", "action run roll-igl"),
        (
            "Run with parameters",
            "action run roll-with-params --param-datastream my-datastream --param-delete_old yes",
        ),
        ("Run quietly", "action run roll-igl --quiet"),
        ("Run with confirmation", "action run roll-igl-safe"),
    ]

    examples_table = Table()
    examples_table.add_column("Description", style="bold cyan")
    examples_table.add_column("Command", style="green")

    for description, command in examples:
        examples_table.add_row(description, f"./escmd.py {command}")

    console.print(examples_table)
    console.print()


def demo_feature_summary():
    """Summarize the new features."""

    console.print("\n[bold blue]New Features Summary[/bold blue]\n")

    features = [
        ("Output Capture", "Store step outputs in variables using 'capture' directive"),
        (
            "JSON Extraction",
            "Extract values from JSON responses using JSONPath ($.field.subfield)",
        ),
        (
            "Variable Interpolation",
            "Use captured variables in subsequent steps with {{ variable }}",
        ),
        ("Conditional Execution", "Run steps conditionally based on previous results"),
        ("Regex Extraction", "Extract values using regex patterns (regex:pattern)"),
        ("Data Transformation", "Apply transforms like strip, lower, upper, replace"),
        ("Safety Features", "Built-in confirmation prompts and error handling"),
        ("Parameterized Actions", "Create reusable actions with parameters"),
    ]

    features_table = Table()
    features_table.add_column("Feature", style="bold magenta")
    features_table.add_column("Description", style="white")

    for feature, description in features:
        features_table.add_row(feature, description)

    console.print(features_table)
    console.print()


def main():
    """Main demo function."""
    console.print("[bold green]ESCMD Enhanced Actions System Demo[/bold green]")
    console.print("=" * 50)

    demo_rollover_action()
    demo_json_extraction()
    demo_action_yaml_syntax()
    demo_usage_examples()
    demo_feature_summary()

    console.print("\n[bold green]Demo completed![/bold green]")
    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. Try running: [cyan]./escmd.py action list[/cyan]")
    console.print(
        "2. View action details: [cyan]./escmd.py action show roll-igl[/cyan]"
    )
    console.print(
        "3. Test with dry run: [cyan]./escmd.py action run roll-igl --dry-run[/cyan]"
    )
    console.print("4. Execute the action: [cyan]./escmd.py action run roll-igl[/cyan]")


if __name__ == "__main__":
    main()
