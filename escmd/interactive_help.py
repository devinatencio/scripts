#!/usr/bin/env python3
"""
Enhanced Interactive Help System for ESterm
Provides rich, searchable, and categorized command help with examples.
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
import re

# Import Rich components
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.align import Align
from rich.layout import Layout
from rich.tree import Tree

# Optional advanced menu support
try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    from InquirerPy.separator import Separator
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False


class InteractiveHelpSystem:
    """Enhanced interactive help system for ESterm commands."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.commands = self._load_command_definitions()

    def _load_command_definitions(self) -> Dict:
        """Load comprehensive command definitions with examples and categories."""
        return {
            "cluster": {
                "category": "Cluster Management",
                "icon": "🌐",
                "commands": {
                    "health": {
                        "description": "Show cluster health status with detailed diagnostics",
                        "usage": "health [--format json|table] [--style dashboard|classic] [--quick]",
                        "examples": [
                            "health",
                            "health --format json",
                            "health --style dashboard",
                            "health --quick --compare production"
                        ],
                        "options": {
                            "--format": "Output format (json or table)",
                            "--style": "Display style (dashboard or classic)",
                            "--quick": "Skip additional diagnostics",
                            "--compare": "Compare with another cluster",
                            "--group": "Show health for cluster group"
                        }
                    },
                    "nodes": {
                        "description": "List all Elasticsearch nodes with detailed information",
                        "usage": "nodes [--format json|table|data]",
                        "examples": [
                            "nodes",
                            "nodes --format json",
                            "nodes --format data"
                        ],
                        "options": {
                            "--format": "Output format (json, table, or data)"
                        }
                    },
                    "masters": {
                        "description": "List master-eligible nodes",
                        "usage": "masters [--format json|table]",
                        "examples": [
                            "masters",
                            "masters --format json"
                        ]
                    },
                    "current-master": {
                        "description": "Show the current master node",
                        "usage": "current-master [--format json|table]",
                        "examples": [
                            "current-master",
                            "current-master --format json"
                        ]
                    },
                    "ping": {
                        "description": "Test Elasticsearch connection",
                        "usage": "ping [--format json|table]",
                        "examples": [
                            "ping",
                            "ping --format json"
                        ]
                    }
                }
            },
            "indices": {
                "category": "Index Management",
                "icon": "📚",
                "commands": {
                    "indices": {
                        "description": "List and manage Elasticsearch indices",
                        "usage": "indices [regex] [--format json|table] [--status green|yellow|red] [--cold] [--delete] [--pager]",
                        "examples": [
                            "indices",
                            "indices 'log-*'",
                            "indices --status red",
                            "indices --cold --pager",
                            "indices 'old-*' --delete"
                        ],
                        "options": {
                            "regex": "Filter indices by regex pattern",
                            "--format": "Output format",
                            "--status": "Filter by health status",
                            "--cold": "Show cold indices only",
                            "--delete": "Delete matching indices",
                            "--pager": "Use pager for long output"
                        }
                    },
                    "indice": {
                        "description": "Show detailed information about a single index",
                        "usage": "indice <index_name>",
                        "examples": [
                            "indice my-index-001",
                            "indice logstash-2023.12.01"
                        ]
                    },
                    "recovery": {
                        "description": "Show index recovery operations",
                        "usage": "recovery [--format json|table|data]",
                        "examples": [
                            "recovery",
                            "recovery --format json"
                        ]
                    }
                }
            },
            "allocation": {
                "category": "Shard Allocation",
                "icon": "🔀",
                "commands": {
                    "allocation": {
                        "description": "Manage shard allocation and routing",
                        "usage": "allocation <command> [options]",
                        "examples": [
                            "allocation show",
                            "allocation explain",
                            "allocation retry"
                        ],
                        "subcommands": {
                            "show": "Display current allocation state",
                            "explain": "Explain allocation decisions",
                            "retry": "Retry failed shard allocations"
                        }
                    },
                    "exclude": {
                        "description": "Exclude indices from specific nodes",
                        "usage": "exclude <index> --server <node>",
                        "examples": [
                            "exclude my-index --server node-1",
                            "exclude 'logs-*' --server node-2"
                        ]
                    },
                    "exclude-reset": {
                        "description": "Reset exclusion settings for an index",
                        "usage": "exclude-reset <index>",
                        "examples": [
                            "exclude-reset my-index",
                            "exclude-reset 'logs-*'"
                        ]
                    }
                }
            },
            "settings": {
                "category": "Cluster Settings",
                "icon": "🔩",
                "commands": {
                    "cluster-settings": {
                        "description": "Display cluster settings",
                        "usage": "cluster-settings [--format json|table]",
                        "examples": [
                            "cluster-settings",
                            "cluster-settings --format json"
                        ]
                    },
                    "set": {
                        "description": "Set cluster settings using dot notation",
                        "usage": "set <transient|persistent> <key> <value> [--dry-run] [--yes]",
                        "examples": [
                            "set transient cluster.routing.allocation.node_concurrent_recoveries 10",
                            "set persistent indices.recovery.max_bytes_per_sec 50mb",
                            "set transient cluster.routing.allocation.enable none --dry-run",
                            "set persistent cluster.max_shards_per_node null"
                        ],
                        "options": {
                            "--dry-run": "Preview changes without applying",
                            "--yes": "Skip confirmation prompt",
                            "--format": "Output format"
                        },
                        "notes": [
                            "Use 'null' as value to reset/remove a setting",
                            "Transient settings are lost on cluster restart",
                            "Persistent settings survive cluster restarts",
                            "Dot notation automatically creates nested structure"
                        ]
                    }
                }
            },
            "snapshots": {
                "category": "Backup & Restore",
                "icon": "💾",
                "commands": {
                    "snapshots": {
                        "description": "Manage Elasticsearch snapshots",
                        "usage": "snapshots <command> [options]",
                        "examples": [
                            "snapshots list",
                            "snapshots create my-backup",
                            "snapshots restore my-backup"
                        ]
                    }
                }
            },
            "ilm": {
                "category": "Index Lifecycle",
                "icon": "🔄",
                "commands": {
                    "ilm": {
                        "description": "Manage Index Lifecycle Management policies",
                        "usage": "ilm <command> [options]",
                        "examples": [
                            "ilm list",
                            "ilm show my-policy",
                            "ilm create my-policy policy.json"
                        ]
                    },
                    "rollover": {
                        "description": "Manually rollover a datastream",
                        "usage": "rollover <datastream>",
                        "examples": [
                            "rollover logs-datastream"
                        ]
                    }
                }
            },
            "utility": {
                "category": "Utilities",
                "icon": "🔧",
                "commands": {
                    "locations": {
                        "description": "Show available cluster locations",
                        "usage": "locations",
                        "examples": ["locations"]
                    },
                    "set-default": {
                        "description": "Set default cluster",
                        "usage": "set-default <cluster_name>",
                        "examples": [
                            "set-default production",
                            "set-default staging"
                        ]
                    },
                    "get-default": {
                        "description": "Show current default cluster",
                        "usage": "get-default",
                        "examples": ["get-default"]
                    },
                    "themes": {
                        "description": "Manage display themes",
                        "usage": "themes",
                        "examples": ["themes"]
                    },
                    "set-theme": {
                        "description": "Change active theme",
                        "usage": "set-theme <theme_name>",
                        "examples": [
                            "set-theme dark",
                            "set-theme light"
                        ]
                    }
                }
            }
        }

    def show_interactive_help(self):
        """Show the main interactive help interface."""
        if INQUIRER_AVAILABLE:
            self._show_advanced_help()
        else:
            self._show_basic_help()

    def _show_advanced_help(self):
        """Show advanced help with arrow key navigation."""
        try:
            # Create main menu choices
            choices = []
            choices.append(Choice("overview", "🏠 ESterm Overview"))
            choices.append(Choice("categories", "📂 Browse by Category"))
            choices.append(Choice("search", "🔍 Search Commands"))
            choices.append(Choice("examples", "💡 Common Examples"))
            choices.append(Choice("setup", "🔩 Setup & Configuration"))
            choices.append(Separator())
            choices.append(Choice("quit", "❌ Exit Help"))

            while True:
                selection = inquirer.select(
                    message="ESterm Interactive Help System",
                    choices=choices,
                    pointer="❯"
                ).execute()

                if selection == "quit":
                    break
                elif selection == "overview":
                    self._show_overview()
                elif selection == "categories":
                    self._browse_categories()
                elif selection == "search":
                    self._search_commands()
                elif selection == "examples":
                    self._show_examples()
                elif selection == "setup":
                    self._show_setup_help()

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Help system exited[/yellow]")

    def _show_basic_help(self):
        """Show basic help interface without arrow keys."""
        while True:
            self.console.print("\n" + "="*60)
            self.console.print(Panel.fit(
                "[bold blue]ESterm Interactive Help System[/bold blue]\n"
                "Enhanced command-line tool for Elasticsearch administration",
                title="🏠 Welcome",
                border_style="blue"
            ))

            options_table = Table(show_header=False, box=None, padding=(0, 2))
            options_table.add_column("Option", style="cyan", width=4)
            options_table.add_column("Description", style="white")

            options_table.add_row("1.", "ESterm Overview")
            options_table.add_row("2.", "Browse Commands by Category")
            options_table.add_row("3.", "Search Commands")
            options_table.add_row("4.", "Common Examples")
            options_table.add_row("5.", "Setup & Configuration")
            options_table.add_row("q.", "Exit Help")

            self.console.print(options_table)

            try:
                choice = Prompt.ask("\n[bold blue]Select option[/bold blue]", default="q")

                if choice.lower() == "q":
                    break
                elif choice == "1":
                    self._show_overview()
                elif choice == "2":
                    self._browse_categories_basic()
                elif choice == "3":
                    self._search_commands_basic()
                elif choice == "4":
                    self._show_examples()
                elif choice == "5":
                    self._show_setup_help()
                else:
                    self.console.print("[red]Invalid option. Please try again.[/red]")

            except KeyboardInterrupt:
                break

    def _show_overview(self):
        """Show ESterm overview."""
        overview = Text()
        overview.append("ESterm - Enhanced Elasticsearch Terminal\n\n", style="bold blue")
        overview.append("A powerful command-line interface for Elasticsearch cluster administration.\n\n", style="dim")

        overview.append("Key Features:\n", style="bold")
        overview.append("• 🌐 Multi-cluster management with easy switching\n")
        overview.append("• 📊 Rich formatted output with tables and colors\n")
        overview.append("• 🔩 Comprehensive cluster and index operations\n")
        overview.append("• 🔍 Advanced search and filtering capabilities\n")
        overview.append("• 💾 Snapshot and backup management\n")
        overview.append("• 🎨 Customizable themes and display options\n")
        overview.append("• 🔧 Interactive configuration and settings\n\n")

        overview.append("Getting Started:\n", style="bold")
        overview.append("1. Start ESterm: ", style="dim")
        overview.append("./esterm.py\n", style="cyan")
        overview.append("2. Select cluster from menu\n", style="dim")
        overview.append("3. Run commands: ", style="dim")
        overview.append("health", style="cyan")
        overview.append(", ", style="dim")
        overview.append("indices", style="cyan")
        overview.append(", ", style="dim")
        overview.append("nodes", style="cyan")
        overview.append("\n")
        overview.append("4. Get help: ", style="dim")
        overview.append("help <command>", style="cyan")

        panel = Panel(overview, title="🏠 ESterm Overview", border_style="blue", padding=(1, 2))
        self.console.print(panel)
        self._wait_for_input()

    def _browse_categories(self):
        """Browse commands by category using advanced menu."""
        categories = [(cat_data["category"], cat_data["icon"], cat_key)
                     for cat_key, cat_data in self.commands.items()]

        choices = [Choice(cat_key, f"{icon} {name}")
                  for name, icon, cat_key in categories]
        choices.append(Choice("back", "⬅️ Back to Main Menu"))

        selection = inquirer.select(
            message="Select Category",
            choices=choices,
            pointer="❯"
        ).execute()

        if selection != "back":
            self._show_category_commands(selection)

    def _browse_categories_basic(self):
        """Browse commands by category using basic interface."""
        self.console.print("\n[bold blue]Command Categories:[/bold blue]")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Number", style="cyan", width=4)
        table.add_column("Category", style="white")

        categories = list(self.commands.items())
        for i, (cat_key, cat_data) in enumerate(categories, 1):
            table.add_row(f"{i}.", f"{cat_data['icon']} {cat_data['category']}")

        self.console.print(table)

        try:
            choice = Prompt.ask("\n[bold blue]Select category number[/bold blue]", default="")
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(categories):
                    cat_key = categories[idx][0]
                    self._show_category_commands(cat_key)
        except (ValueError, KeyboardInterrupt):
            pass

    def _show_category_commands(self, category_key: str):
        """Show commands in a specific category."""
        cat_data = self.commands[category_key]

        self.console.print(f"\n[bold blue]{cat_data['icon']} {cat_data['category']} Commands:[/bold blue]")

        for cmd_name, cmd_data in cat_data["commands"].items():
            cmd_panel = self._create_command_panel(cmd_name, cmd_data)
            self.console.print(cmd_panel)

        self._wait_for_input()

    def _create_command_panel(self, cmd_name: str, cmd_data: Dict) -> Panel:
        """Create a formatted panel for a command."""
        content = Text()

        # Command description
        content.append(f"{cmd_data['description']}\n\n", style="white")

        # Usage
        content.append("Usage:\n", style="bold yellow")
        content.append(f"  {cmd_data['usage']}\n\n", style="cyan")

        # Examples
        if "examples" in cmd_data:
            content.append("Examples:\n", style="bold green")
            for example in cmd_data["examples"]:
                content.append(f"  $ {example}\n", style="dim cyan")
            content.append("\n")

        # Options
        if "options" in cmd_data:
            content.append("Options:\n", style="bold magenta")
            for option, desc in cmd_data["options"].items():
                content.append(f"  {option:<20} {desc}\n", style="dim")
            content.append("\n")

        # Notes
        if "notes" in cmd_data:
            content.append("Notes:\n", style="bold yellow")
            for note in cmd_data["notes"]:
                content.append(f"  • {note}\n", style="dim yellow")

        return Panel(content, title=f"[bold cyan]{cmd_name}[/bold cyan]",
                    border_style="cyan", padding=(1, 2))

    def _search_commands(self):
        """Search commands with advanced interface."""
        query = inquirer.text(
            message="Enter search term:",
            validate=lambda x: len(x.strip()) > 0
        ).execute()

        results = self._search_command_database(query)
        self._display_search_results(query, results)

    def _search_commands_basic(self):
        """Search commands with basic interface."""
        try:
            query = Prompt.ask("\n[bold blue]Enter search term[/bold blue]")
            if query.strip():
                results = self._search_command_database(query)
                self._display_search_results(query, results)
        except KeyboardInterrupt:
            pass

    def _search_command_database(self, query: str) -> List[Tuple[str, str, Dict]]:
        """Search through all commands and return matches."""
        results = []
        query_lower = query.lower()

        for cat_key, cat_data in self.commands.items():
            for cmd_name, cmd_data in cat_data["commands"].items():
                score = 0

                # Search in command name
                if query_lower in cmd_name.lower():
                    score += 10

                # Search in description
                if query_lower in cmd_data["description"].lower():
                    score += 5

                # Search in examples
                if "examples" in cmd_data:
                    for example in cmd_data["examples"]:
                        if query_lower in example.lower():
                            score += 3

                # Search in options
                if "options" in cmd_data:
                    for option, desc in cmd_data["options"].items():
                        if query_lower in option.lower() or query_lower in desc.lower():
                            score += 2

                if score > 0:
                    results.append((cmd_name, cat_data["category"], cmd_data, score))

        # Sort by relevance score
        results.sort(key=lambda x: x[3], reverse=True)
        return results

    def _display_search_results(self, query: str, results: List):
        """Display search results."""
        if not results:
            self.console.print(f"\n[yellow]No commands found matching '{query}'[/yellow]")
            self._wait_for_input()
            return

        self.console.print(f"\n[bold blue]Search results for '{query}':[/bold blue]")
        self.console.print(f"Found {len(results)} matching commands:\n")

        for cmd_name, category, cmd_data, score in results[:5]:  # Show top 5
            content = Text()
            content.append(f"{cmd_data['description']}\n", style="white")
            content.append(f"Category: {category}\n", style="dim")
            if "examples" in cmd_data and cmd_data["examples"]:
                content.append(f"Example: {cmd_data['examples'][0]}", style="cyan")

            panel = Panel(content, title=f"[bold cyan]{cmd_name}[/bold cyan]",
                         border_style="cyan", padding=(1, 1))
            self.console.print(panel)

        if len(results) > 5:
            self.console.print(f"\n[dim]... and {len(results) - 5} more results[/dim]")

        self._wait_for_input()

    def _show_examples(self):
        """Show common usage examples."""
        examples_text = Text()
        examples_text.append("Common ESterm Usage Patterns\n\n", style="bold blue")

        examples_text.append("🔍 Basic Monitoring:\n", style="bold yellow")
        examples_text.append("  health              # Quick cluster health check\n", style="cyan")
        examples_text.append("  health --style dashboard  # Detailed dashboard view\n", style="cyan")
        examples_text.append("  nodes               # List all nodes\n", style="cyan")
        examples_text.append("  indices             # List all indices\n\n", style="cyan")

        examples_text.append("📊 Index Management:\n", style="bold yellow")
        examples_text.append("  indices 'log-*'     # Filter indices by pattern\n", style="cyan")
        examples_text.append("  indices --status red   # Show only red indices\n", style="cyan")
        examples_text.append("  indice my-index-001    # Detailed index info\n", style="cyan")
        examples_text.append("  recovery            # Show recovery operations\n\n", style="cyan")

        examples_text.append("🔩 Settings Management:\n", style="bold yellow")
        examples_text.append("  cluster-settings    # Show current settings\n", style="cyan")
        examples_text.append("  set persistent cluster.max_shards_per_node 1000\n", style="cyan")
        examples_text.append("  set transient cluster.routing.allocation.enable none\n", style="cyan")
        examples_text.append("  set persistent indices.recovery.max_bytes_per_sec 50mb\n\n", style="cyan")

        examples_text.append("🔧 Maintenance Tasks:\n", style="bold yellow")
        examples_text.append("  allocation show     # Check shard allocation\n", style="cyan")
        examples_text.append("  exclude my-index --server node-1  # Exclude from node\n", style="cyan")
        examples_text.append("  snapshots list      # List available snapshots\n", style="cyan")
        examples_text.append("  ilm list           # Show ILM policies\n", style="cyan")

        panel = Panel(examples_text, title="💡 Common Examples",
                     border_style="yellow", padding=(1, 2))
        self.console.print(panel)
        self._wait_for_input()

    def _show_setup_help(self):
        """Show setup and configuration help."""
        setup_text = Text()
        setup_text.append("ESterm Setup & Configuration\n\n", style="bold blue")

        setup_text.append("📁 Configuration Files:\n", style="bold yellow")
        setup_text.append("  escmd.yml          # Main settings and passwords\n", style="cyan")
        setup_text.append("  elastic_servers.yml # Cluster definitions\n", style="cyan")
        setup_text.append("  themes.yml         # Display themes\n\n", style="cyan")

        setup_text.append("🌐 Cluster Configuration:\n", style="bold yellow")
        setup_text.append("  Add new clusters to elastic_servers.yml:\n", style="dim")
        setup_text.append("  production:\n", style="cyan")
        setup_text.append("    elastic_host: es-prod.example.com\n", style="cyan")
        setup_text.append("    elastic_port: 9200\n", style="cyan")
        setup_text.append("    use_ssl: true\n\n", style="cyan")

        setup_text.append("🎨 Themes:\n", style="bold yellow")
        setup_text.append("  themes              # List available themes\n", style="cyan")
        setup_text.append("  set-theme dark      # Switch to dark theme\n", style="cyan")
        setup_text.append("  set-theme light     # Switch to light theme\n\n", style="cyan")

        setup_text.append("🔐 Security:\n", style="bold yellow")
        setup_text.append("  store-password cluster-name  # Store encrypted password\n", style="cyan")
        setup_text.append("  list-stored-passwords        # List stored passwords\n", style="cyan")
        setup_text.append("  generate-master-key          # Generate encryption key\n", style="cyan")
        setup_text.append("  rotate-master-key            # New key + re-encrypt (backs up .old)\n", style="cyan")

        panel = Panel(setup_text, title="🔩 Setup & Configuration",
                     border_style="blue", padding=(1, 2))
        self.console.print(panel)
        self._wait_for_input()

    def _wait_for_input(self):
        """Wait for user input to continue."""
        try:
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="")
        except KeyboardInterrupt:
            pass

    def get_command_help(self, command: str) -> Optional[str]:
        """Get help for a specific command."""
        for cat_key, cat_data in self.commands.items():
            if command in cat_data["commands"]:
                cmd_data = cat_data["commands"][command]
                return self._format_command_help(command, cmd_data)
        return None

    def _format_command_help(self, cmd_name: str, cmd_data: Dict) -> str:
        """Format help text for a specific command."""
        help_text = f"\n{cmd_name}: {cmd_data['description']}\n\n"
        help_text += f"Usage: {cmd_data['usage']}\n\n"

        if "examples" in cmd_data:
            help_text += "Examples:\n"
            for example in cmd_data["examples"]:
                help_text += f"  $ {example}\n"
            help_text += "\n"

        if "options" in cmd_data:
            help_text += "Options:\n"
            for option, desc in cmd_data["options"].items():
                help_text += f"  {option:<20} {desc}\n"
            help_text += "\n"

        return help_text


def main():
    """Demo the interactive help system."""
    console = Console()
    help_system = InteractiveHelpSystem(console)
    help_system.show_interactive_help()


if __name__ == "__main__":
    main()
