#!/usr/bin/env python3
"""
Health Monitor Module for ESterm

Handles all health monitoring and watching functionality including:
- Continuous health monitoring with real-time updates
- Health data collection and formatting
- Watch mode with user controls (start/stop/pause)
- Health trend analysis and alerting
- Performance metrics and timing
"""

import time
import threading
import signal
import sys
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

# Import Rich components
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner


class HealthMonitor:
    """
    Health monitoring system for ESterm.

    Provides real-time cluster health monitoring with various display modes
    and interactive controls. Supports both continuous monitoring and
    one-time health checks with rich formatting and alerting capabilities.
    """

    def __init__(self, console: Console):
        """
        Initialize the Health Monitor.

        Args:
            console: Rich console instance for output
        """
        self.console = console
        self.monitoring_active = False
        self.stop_event = threading.Event()
        self.update_interval = 5.0
        self.max_samples = 50
        self.health_history = []

    def start_monitoring(self, cluster_manager, interval: float = 5.0, max_samples: int = 50) -> bool:
        """
        Start background health monitoring.

        Args:
            cluster_manager: ClusterManager instance
            interval: Update interval in seconds
            max_samples: Maximum number of samples to keep in history

        Returns:
            bool: True if monitoring started successfully
        """
        if self.monitoring_active:
            self.console.print("[yellow]Health monitoring already active[/yellow]")
            return False

        if not cluster_manager.is_connected():
            self.console.print("[red]No cluster connection available for monitoring[/red]")
            return False

        self.update_interval = interval
        self.max_samples = max_samples
        self.stop_event.clear()
        self.monitoring_active = True

        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_loop, args=(cluster_manager,), daemon=True)
        monitor_thread.start()

        self.console.print(f"[green]Health monitoring started (interval: {interval}s)[/green]")
        return True

    def stop_monitoring(self, silent=False):
        """Stop background health monitoring."""
        if not self.monitoring_active:
            if not silent:
                self.console.print("[yellow]Health monitoring not active[/yellow]")
            return

        self.stop_event.set()
        self.monitoring_active = False
        if not silent:
            self.console.print("[yellow]Health monitoring stopped[/yellow]")

    def pause_monitoring(self):
        """Pause or resume health monitoring."""
        if not self.monitoring_active:
            self.console.print("[yellow]Health monitoring not active[/yellow]")
            return

        if self.stop_event.is_set():
            self.stop_event.clear()
            self.console.print("[green]Health monitoring resumed[/green]")
        else:
            self.stop_event.set()
            self.console.print("[yellow]Health monitoring paused[/yellow]")

    def watch_health(self, cluster_manager, args: Optional[Any] = None):
        """Watch health command - continuously display health status."""
        if not cluster_manager.is_connected():
            self.console.print("[red]Error: Not connected to any cluster. Use 'connect <cluster>' first.[/red]")
            return

        # Parse interval from args, default to 10 seconds
        interval = 10
        if args and hasattr(args, 'interval'):
            interval = args.interval

        current_cluster = cluster_manager.get_current_cluster()
        self.console.print(f"[green]Starting health monitor (every {interval}s). Press Enter to stop.[/green]")
        self.console.print()

        # Print clean header
        self.console.print(f"\n[bold magenta]Health Monitor - {current_cluster}[/bold magenta]")
        self.console.print()

        count = 0
        stop_monitoring = threading.Event()

        def input_listener():
            """Listen for user input to stop monitoring."""
            try:
                input()  # Wait for Enter key
                stop_monitoring.set()
            except:
                stop_monitoring.set()

        # Start input listener thread
        listener_thread = threading.Thread(target=input_listener, daemon=True)
        listener_thread.start()

        try:
            while not stop_monitoring.is_set():
                try:
                    # Get health data
                    health_data = self._get_health_json(cluster_manager)
                    if health_data and 'error' not in health_data:
                        # Format timestamp
                        timestamp = time.strftime("%H:%M:%S")

                        # Format status with color
                        status = health_data.get('status', 'unknown').lower()
                        if status == 'green':
                            status_display = "[green]GRN[/green]"
                        elif status == 'yellow':
                            status_display = "[yellow]YLW[/yellow]"
                        elif status == 'red':
                            status_display = "[red]RED[/red]"
                        else:
                            status_display = "[dim]UNK[/dim]"

                        # Format unassigned shards with color
                        unassigned = health_data.get('unassigned_shards', 0)
                        if unassigned > 0:
                            unassigned_display = f"[red]{unassigned:,}[/red]"
                        else:
                            unassigned_display = f"[green]{unassigned}[/green]"

                        # Format relocating shards
                        relocating = health_data.get('relocating_shards', 0)
                        if relocating > 0:
                            relocating_display = f"[yellow]{relocating:,}[/yellow]"
                        else:
                            relocating_display = f"[green]{relocating}[/green]"

                        # Format initializing shards
                        initializing = health_data.get('initializing_shards', 0)
                        if initializing > 0:
                            initializing_display = f"[cyan]{initializing:,}[/cyan]"
                        else:
                            initializing_display = f"[green]{initializing}[/green]"

                        # Format active shards percentage
                        active_percent = health_data.get('active_shards_percent_as_number', 100.0)
                        if active_percent < 100.0:
                            percent_display = f"[red]{active_percent:.1f}%[/red]"
                        else:
                            percent_display = f"[green]{active_percent:.1f}%[/green]"

                        # Show header every 20 rows for long-running monitoring
                        show_header = (count == 0) or (count % 20 == 0)

                        # Add visual separator when reprinting header (except for first time)
                        if show_header and count > 0:
                            self.console.print()
                            self.console.print("[dim]" + "-" * 70 + "[/dim]")

                        # Create clean borderless table for each row
                        row_table = Table(show_header=show_header, header_style="bold dim", box=None, padding=(0, 1))
                        row_table.add_column("Time", style="dim", width=8)
                        row_table.add_column("Status", justify="center", width=8)
                        row_table.add_column("Primary", justify="right", width=8)
                        row_table.add_column("Relocating", justify="right", width=10)
                        row_table.add_column("Initializing", justify="right", width=12)
                        row_table.add_column("Unassigned", justify="right", width=10)
                        row_table.add_column("Active %", justify="right", width=8)

                        row_table.add_row(
                            timestamp,
                            status_display,
                            f"{health_data.get('active_primary_shards', 0):,}",
                            relocating_display,
                            initializing_display,
                            unassigned_display,
                            percent_display
                        )

                        self.console.print(row_table)
                        count += 1

                    else:
                        self.console.print(f"[red]{time.strftime('%H:%M:%S')} - Error getting health data[/red]")

                    # Sleep in small intervals to check for stop signal
                    for _ in range(interval * 10):  # 0.1 second intervals
                        if stop_monitoring.is_set():
                            break
                        time.sleep(0.1)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.console.print(f"[red]Error: {e}[/red]")
                    if stop_monitoring.is_set():
                        break
                    time.sleep(1)

        except KeyboardInterrupt:
            pass
        finally:
            stop_monitoring.set()
            self.console.print(f"\n[yellow]Health monitoring stopped after {count} samples.[/yellow]")

    def _interactive_health_watch(self, cluster_manager, interval: float, max_samples: int, stop_event: threading.Event):
        """
        Run interactive health watching with live updates.

        Args:
            cluster_manager: ClusterManager instance
            interval: Update interval in seconds
            max_samples: Maximum samples to track
            stop_event: Event to signal stop
        """
        health_history = []
        paused = False
        count = 0

        # Input listener thread
        def input_listener():
            """Listen for user input to control monitoring."""
            try:
                while not stop_event.is_set():
                    try:
                        if sys.stdin.isatty():
                            char = sys.stdin.read(1).lower()
                            if char == 'p':
                                nonlocal paused
                                paused = not paused
                            elif char == 's':
                                self._show_health_summary(health_history)
                            elif char == 'q':
                                stop_event.set()
                                break
                    except:
                        break
            except:
                pass

        # Start input listener
        input_thread = threading.Thread(target=input_listener, daemon=True)
        input_thread.start()

        # Main monitoring loop with Live display
        with Live(self._create_health_display(None, count, paused), console=self.console, refresh_per_second=2) as live:
            while not stop_event.is_set():
                if not paused:
                    # Get health data
                    health_data = self._get_health_data(cluster_manager)

                    if health_data:
                        # Add timestamp
                        health_data['timestamp'] = datetime.now()
                        health_history.append(health_data)

                        # Keep only recent samples
                        if len(health_history) > max_samples:
                            health_history.pop(0)

                        count += 1

                    # Update display
                    live.update(self._create_health_display(health_data, count, paused))

                # Wait for next update
                for _ in range(int(interval * 10)):  # Check stop event more frequently
                    if stop_event.is_set():
                        break
                    time.sleep(0.1)

        self.console.print(f"\n[yellow]Health monitoring stopped after {count} samples.[/yellow]")

    def _monitor_loop(self, cluster_manager):
        """
        Background monitoring loop.

        Args:
            cluster_manager: ClusterManager instance
        """
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Get health data
                health_data = self._get_health_data(cluster_manager)

                if health_data:
                    # Add timestamp
                    health_data['timestamp'] = datetime.now()
                    self.health_history.append(health_data)

                    # Keep only recent samples
                    if len(self.health_history) > self.max_samples:
                        self.health_history.pop(0)

                    # Check for alerts
                    self._check_health_alerts(health_data)

            except Exception as e:
                self.console.print(f"[red]Health monitoring error: {e}[/red]")

            # Wait for next update
            self.stop_event.wait(timeout=self.update_interval)

    def _get_health_json(self, cluster_manager):
        """Get health data in JSON format."""
        try:
            es_client = cluster_manager.get_current_client()
            if es_client:
                health = es_client.get_cluster_health()
                return health
            return None
        except Exception:
            return None

    def _get_health_data(self, cluster_manager) -> Optional[Dict[str, Any]]:
        """
        Get current health data from Elasticsearch.

        Args:
            cluster_manager: ClusterManager instance

        Returns:
            dict or None: Health data dictionary
        """
        try:
            # Clear performance cache to ensure real-time data
            try:
                from performance import default_cache
                default_cache.invalidate()  # Clear all cached data for real-time results
            except ImportError:
                # Performance module not available, continue without clearing cache
                pass

            es_client = cluster_manager.get_current_client()
            if not es_client:
                return None

            # Get cluster health
            health = es_client.es.cluster.health()
            if hasattr(health, 'body'):
                health_data = health.body
            else:
                health_data = dict(health)

            # Add additional metrics
            try:
                # Get node stats for additional metrics
                stats = es_client.es.nodes.stats(metric='os,jvm')
                if hasattr(stats, 'body'):
                    stats_data = stats.body
                else:
                    stats_data = dict(stats)

                # Extract useful metrics
                if 'nodes' in stats_data:
                    total_memory = 0
                    used_memory = 0
                    total_disk = 0
                    used_disk = 0

                    for node_id, node_stats in stats_data['nodes'].items():
                        if 'os' in node_stats:
                            if 'mem' in node_stats['os']:
                                total_memory += node_stats['os']['mem'].get('total_in_bytes', 0)
                                used_memory += node_stats['os']['mem'].get('used_in_bytes', 0)

                        if 'jvm' in node_stats:
                            if 'mem' in node_stats['jvm']:
                                heap_used = node_stats['jvm']['mem'].get('heap_used_in_bytes', 0)
                                heap_max = node_stats['jvm']['mem'].get('heap_max_in_bytes', 0)

                    health_data['memory_total'] = total_memory
                    health_data['memory_used'] = used_memory
                    health_data['memory_percent'] = (used_memory / total_memory * 100) if total_memory > 0 else 0

            except Exception:
                # Additional metrics are optional
                pass

            return health_data

        except Exception as e:
            return {'error': str(e), 'status': 'error'}

    def _create_health_display(self, health_data: Optional[Dict[str, Any]], count: int, paused: bool) -> Panel:
        """
        Create the live health display panel.

        Args:
            health_data: Current health data
            count: Sample count
            paused: Whether monitoring is paused

        Returns:
            Panel: Rich panel for display
        """
        if not health_data:
            content = Text("Waiting for health data...", style="dim")
        elif 'error' in health_data:
            content = Text(f"Error: {health_data['error']}", style="red")
        else:
            content = self._format_health_data(health_data)

        # Add status indicators
        status_text = Text()
        if paused:
            status_text.append("⏸️  PAUSED", style="yellow bold")
        else:
            status_text.append("🔄 MONITORING", style="green bold")

        status_text.append(f" | Samples: {count}", style="dim")

        if health_data and 'timestamp' in health_data:
            timestamp = health_data['timestamp'].strftime("%H:%M:%S")
            status_text.append(f" | Last: {timestamp}", style="dim")

        # Combine content
        full_content = Text()
        full_content.append_text(status_text)
        full_content.append("\n\n")
        full_content.append_text(content)

        return Panel(
            full_content,
            title="🏥 Cluster Health Monitor",
            border_style="green" if not paused else "yellow",
            padding=(1, 2)
        )

    def _format_health_data(self, health_data: Dict[str, Any]) -> Text:
        """
        Format health data for display.

        Args:
            health_data: Health data dictionary

        Returns:
            Text: Formatted health data
        """
        text = Text()

        # Status
        status = health_data.get('status', 'unknown').upper()
        status_color = self._get_status_color(status)
        text.append(f"Status: ", style="bold")
        text.append(f"{status}\n", style=status_color)

        # Cluster info
        cluster_name = health_data.get('cluster_name', 'Unknown')
        text.append(f"Cluster: ", style="bold")
        text.append(f"{cluster_name}\n", style="cyan")

        # Nodes
        active_nodes = health_data.get('number_of_nodes', 0)
        data_nodes = health_data.get('number_of_data_nodes', 0)
        text.append(f"Nodes: ", style="bold")
        text.append(f"{active_nodes} total, {data_nodes} data\n", style="white")

        # Shards
        active_shards = health_data.get('active_shards', 0)
        primary_shards = health_data.get('active_primary_shards', 0)
        relocating_shards = health_data.get('relocating_shards', 0)
        initializing_shards = health_data.get('initializing_shards', 0)
        unassigned_shards = health_data.get('unassigned_shards', 0)

        text.append(f"Shards: ", style="bold")
        text.append(f"{active_shards} active ({primary_shards} primary)\n", style="green")

        if relocating_shards > 0:
            text.append(f"        {relocating_shards} relocating\n", style="yellow")

        if initializing_shards > 0:
            text.append(f"        {initializing_shards} initializing\n", style="cyan")

        if unassigned_shards > 0:
            text.append(f"        {unassigned_shards} unassigned\n", style="red")

        # Active percentage
        active_percent = health_data.get('active_shards_percent_as_number', 100.0)
        percent_color = "green" if active_percent == 100.0 else "red"
        text.append(f"Active: ", style="bold")
        text.append(f"{active_percent:.1f}%\n", style=percent_color)

        return text

    def _show_health_summary(self, health_history: List[Dict[str, Any]]):
        """
        Show health summary statistics.

        Args:
            health_history: List of health data samples
        """
        if not health_history:
            self.console.print("[yellow]No health data available for summary[/yellow]")
            return

        # Create summary table
        table = Table(title="Health Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="white")
        table.add_column("Current", justify="right")
        table.add_column("Min", justify="right")
        table.add_column("Max", justify="right")
        table.add_column("Avg", justify="right")

        latest = health_history[-1]

        # Extract numeric metrics
        metrics = {
            'Nodes': 'number_of_nodes',
            'Data Nodes': 'number_of_data_nodes',
            'Active Shards': 'active_shards',
            'Primary Shards': 'active_primary_shards',
            'Relocating': 'relocating_shards',
            'Initializing': 'initializing_shards',
            'Unassigned': 'unassigned_shards',
            'Active %': 'active_shards_percent_as_number'
        }

        for metric_name, key in metrics.items():
            values = [h.get(key, 0) for h in health_history if key in h]
            if values:
                current = values[-1]
                min_val = min(values)
                max_val = max(values)
                avg_val = sum(values) / len(values)

                if key == 'active_shards_percent_as_number':
                    table.add_row(
                        metric_name,
                        f"{current:.1f}%",
                        f"{min_val:.1f}%",
                        f"{max_val:.1f}%",
                        f"{avg_val:.1f}%"
                    )
                else:
                    table.add_row(
                        metric_name,
                        f"{current:,}",
                        f"{min_val:,}",
                        f"{max_val:,}",
                        f"{avg_val:.0f}"
                    )

        self.console.print()
        self.console.print(table)
        self.console.print()

    def _check_health_alerts(self, health_data: Dict[str, Any]):
        """
        Check for health alerts and notifications.

        Args:
            health_data: Current health data
        """
        alerts = []

        # Check status
        status = health_data.get('status', '').lower()
        if status == 'red':
            alerts.append("🚨 Cluster status is RED")
        elif status == 'yellow':
            alerts.append("🔶  Cluster status is YELLOW")

        # Check unassigned shards
        unassigned = health_data.get('unassigned_shards', 0)
        if unassigned > 0:
            alerts.append(f"🔶  {unassigned} unassigned shards")

        # Print alerts
        for alert in alerts:
            self.console.print(f"[red]{alert}[/red]")

    def _get_status_color(self, status: str) -> str:
        """
        Get color for status display.

        Args:
            status: Health status string

        Returns:
            str: Color name for Rich formatting
        """
        status = status.lower()
        if status == 'green':
            return "green bold"
        elif status == 'yellow':
            return "yellow bold"
        elif status == 'red':
            return "red bold"
        else:
            return "dim"

    def get_latest_health(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest health data from history.

        Returns:
            dict or None: Latest health data
        """
        return self.health_history[-1] if self.health_history else None

    def get_health_history(self) -> List[Dict[str, Any]]:
        """
        Get complete health history.

        Returns:
            list: List of health data samples
        """
        return self.health_history.copy()

    def clear_history(self):
        """Clear health history."""
        self.health_history.clear()
