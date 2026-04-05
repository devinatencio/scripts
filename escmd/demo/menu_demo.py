#!/usr/bin/env python3
"""
Demo script to showcase the enhanced interactive cluster menu functionality.
This demonstrates the improvements made to esterm's cluster selection interface.
"""

import os
import sys

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Rich components
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Optional advanced menu support
try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False

from rich.table import Table
from rich.prompt import Prompt


class MenuDemo:
    """Demo class to showcase enhanced cluster menu functionality."""

    def __init__(self):
        self.console = Console()

    def show_demo(self):
        """Show the menu demo."""
        self.console.print(Panel.fit(
            "[bold blue]Enhanced ESterm Cluster Selection Demo[/bold blue]\n\n"
            "This demo shows the improved cluster selection interface\n"
            "that replaces the old numbered list with a more interactive menu.",
            title="🚀 ESterm Enhancement Demo",
            border_style="blue"
        ))

        # Sample cluster data
        sample_clusters = [
            "production-cluster",
            "staging-cluster",
            "development-cluster",
            "testing-cluster",
            "analytics-cluster"
        ]

        if INQUIRER_AVAILABLE:
            self.console.print("\n[green]✓ InquirerPy is available - attempting advanced menu[/green]")
            try:
                # Check if we're in a proper terminal
                if hasattr(sys, 'stdin') and sys.stdin.isatty():
                    selected = self._demo_inquirer_menu(sample_clusters)
                else:
                    self.console.print("[yellow]! Not running in terminal - showing Rich fallback menu[/yellow]")
                    selected = self._demo_rich_menu(sample_clusters)
            except Exception as e:
                self.console.print(f"[yellow]! InquirerPy failed ({str(e)[:50]}...) - showing Rich fallback menu[/yellow]")
                selected = self._demo_rich_menu(sample_clusters)
        else:
            self.console.print("\n[yellow]! InquirerPy not available - showing Rich fallback menu[/yellow]")
            self.console.print("[dim]Install with: pip install InquirerPy[/dim]\n")
            selected = self._demo_rich_menu(sample_clusters)

        if selected:
            self.console.print(f"\n[green]✓ You selected: [bold]{selected}[/bold][/green]")
            self._show_connection_simulation(selected)
        else:
            self.console.print("\n[yellow]No cluster selected - would continue without connection[/yellow]")

    def _demo_inquirer_menu(self, clusters):
        """Demo the advanced InquirerPy menu."""
        self.console.print("\n[bold blue]🚀 Advanced Menu (InquirerPy):[/bold blue]")
        self.console.print("[dim]Use arrow keys to navigate, Enter to select[/dim]\n")

        try:
            choices = [
                Choice(cluster, name=f"🌐 {cluster}")
                for cluster in clusters
            ]
            choices.append(Choice(None, name="⏩ Skip cluster selection"))

            selected = inquirer.select(
                message="Select Elasticsearch Cluster:",
                choices=choices,
                default=clusters[0] if clusters else None,
                pointer="❯"
            ).execute()

            return selected

        except KeyboardInterrupt:
            return None
        except Exception as e:
            self.console.print(f"[red]InquirerPy menu failed: {e}[/red]")
            return None

    def _demo_rich_menu(self, clusters):
        """Demo the Rich-based menu (fallback)."""
        self.console.print("\n[bold blue]🔐  Fallback Menu (Rich only):[/bold blue]")
        self.console.print("[dim]Enhanced table format with multiple input methods[/dim]\n")
        self.console.print("[bold blue]🌐 Available Elasticsearch Clusters:[/bold blue]")

        # Create a nicely formatted table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Number", style="bold cyan", width=4)
        table.add_column("Cluster", style="white")

        for i, cluster in enumerate(clusters, 1):
            table.add_row(f"{i}.", cluster)

        self.console.print(table)

        self.console.print("\n[dim]Options:[/dim]")
        self.console.print(f"  • [cyan]Enter number[/cyan] (1-{len(clusters)}) to select cluster")
        self.console.print("  • [cyan]Enter cluster name[/cyan] directly")
        self.console.print("  • [cyan]Press Enter[/cyan] to skip cluster selection")
        self.console.print("  • [cyan]Type 'q'[/cyan] to quit")

        while True:
            try:
                choice = Prompt.ask(
                    "\n[bold blue]Select cluster[/bold blue]",
                    default=""
                )

                if not choice.strip():
                    return None

                if choice.lower() == 'q':
                    return None

                # Check if it's a number
                if choice.isdigit():
                    cluster_index = int(choice) - 1
                    if 0 <= cluster_index < len(clusters):
                        return clusters[cluster_index]
                    else:
                        self.console.print(f"[red]Invalid number. Please enter 1-{len(clusters)}[/red]")
                        continue

                # Check if it's a cluster name
                if choice in clusters:
                    return choice
                else:
                    self.console.print(f"[red]Cluster '{choice}' not found.[/red]")
                    continue

            except KeyboardInterrupt:
                return None

    def _show_connection_simulation(self, cluster_name):
        """Simulate the connection process."""
        self.console.print(f"\n[blue]Connecting to {cluster_name}...[/blue]")

        # Show what would happen next
        info_text = Text()
        info_text.append("Next steps in ESterm:\n", style="bold")
        info_text.append("• Load cluster configuration\n", style="dim")
        info_text.append("• Establish Elasticsearch connection\n", style="dim")
        info_text.append("• Initialize command context\n", style="dim")
        info_text.append("• Start interactive terminal session\n", style="dim")

        panel = Panel(
            info_text,
            title="Connection Process",
            border_style="green",
            padding=(1, 2)
        )

        self.console.print(panel)

    def show_comparison(self):
        """Show before/after comparison."""
        self.console.print(Panel.fit(
            "[bold red]BEFORE[/bold red] - Old numbered list:\n\n"
            "Available Clusters:\n"
            "  1. production-cluster\n"
            "  2. staging-cluster\n"
            "  3. development-cluster\n\n"
            "Options:\n"
            "  • Enter number to connect to cluster\n"
            "  • Enter cluster name directly\n"
            "  • Press Enter to continue without connecting\n\n"
            "[bold green]AFTER[/bold green] - Enhanced interface:\n"
            "• 🌐 Rich formatted cluster table\n"
            "• ❯ Arrow key navigation (with InquirerPy)\n"
            "• 🎨 Color-coded options and feedback\n"
            "• ⚡ Better user experience\n"
            "• 🔄 Graceful fallback for compatibility",
            title="📊 Enhancement Comparison",
            border_style="cyan"
        ))


def main():
    """Main demo function."""
    demo = MenuDemo()

    try:
        demo.show_comparison()
        demo.console.print("\n" + "="*60 + "\n")
        demo.show_demo()

        # Show both menu types for comparison
        demo.console.print("\n" + "="*60 + "\n")
        demo.console.print("[bold cyan]📋 Showing Rich fallback menu for comparison:[/bold cyan]")
        rich_selected = demo._demo_rich_menu([
            "example-cluster-1",
            "example-cluster-2",
            "example-cluster-3"
        ])

        if rich_selected:
            demo.console.print(f"\n[green]✓ Rich menu selection: [bold]{rich_selected}[/bold][/green]")
        else:
            demo.console.print("\n[yellow]Rich menu: No selection made[/yellow]")

    except KeyboardInterrupt:
        demo.console.print("\n\n[yellow]Demo interrupted by user[/yellow]")

    demo.console.print("\n[dim]Demo completed! The enhanced menu is now integrated into esterm.py[/dim]")


if __name__ == "__main__":
    main()
