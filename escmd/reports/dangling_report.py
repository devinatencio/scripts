#!/usr/bin/env python3
"""
DanglingReport - Multi-cluster dangling indices reporting system.

This module provides functionality to analyze dangling indices across
multiple clusters within a cluster group, aggregating data and presenting
comprehensive reports using Rich formatting with consistent theming.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import sys
import os

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)


class DanglingReport:
    """
    Multi-cluster dangling indices report generator.

    Analyzes dangling indices across all clusters in a cluster group,
    providing aggregated statistics and detailed breakdowns.
    """

    def __init__(
        self, configuration_manager, console=None, theme_styles=None, logger=None
    ):
        """
        Initialize the DanglingReport.

        Args:
            configuration_manager: ConfigurationManager instance
            console: Rich Console instance (optional)
            theme_styles: Theme styles dictionary (optional)
            logger: External logger instance (optional)
        """
        self.config_manager = configuration_manager
        self.console = console or Console()
        self.theme_styles = theme_styles or self._get_default_styles()
        self.logger = logger or self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the report generator."""
        logger = logging.getLogger("dangling_report")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # Use a single rotating log file for all dangling operations
            import os
            from logging.handlers import RotatingFileHandler

            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Single log file for all environments with rotation
            log_file = os.path.join(log_dir, "dangling.log")

            # 200MB max size, keep 1 backup file
            handler = RotatingFileHandler(
                log_file,
                maxBytes=200 * 1024 * 1024,  # 200MB
                backupCount=1,
                encoding="utf-8",
            )
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _get_default_styles(self) -> Dict[str, Any]:
        """Get default theme styles if none provided."""
        return {
            "border_style": "white",
            "header_style": "bold white",
            "panel_styles": {
                "success": "bold",
                "warning": "bold",
                "error": "bold",
                "info": "bold",
                "title": "bold white",
            },
            "health_styles": {
                "green": {"text": "bold", "icon": "bold"},
                "yellow": {"text": "bold", "icon": "bold"},
                "red": {"text": "bold", "icon": "bold"},
            },
        }

    def _get_health_style(self, health_type: str, style_part: str = "text") -> str:
        """Get health style color from theme."""
        health_styles = self.theme_styles.get("health_styles", {})
        return health_styles.get(health_type, {}).get(style_part, health_type)

    def _get_panel_style(self, panel_type: str) -> str:
        """Get panel style color from theme."""
        panel_styles = self.theme_styles.get("panel_styles", {})
        return panel_styles.get(panel_type, panel_type)

    def generate_cluster_group_report(
        self, group_name: str, format_type: str = "table"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive dangling indices report for a cluster group.

        Args:
            group_name: Name of the cluster group
            format_type: Output format ('table' or 'json')

        Returns:
            Dictionary containing report data and results
        """
        # Ensure theme styles are properly structured
        if not isinstance(self.theme_styles.get("panel_styles"), dict):
            self.theme_styles = self._get_default_styles()
        try:
            # Validate cluster group exists
            if not self.config_manager.is_cluster_group(group_name):
                available_groups = list(self.config_manager.get_cluster_groups().keys())
                error_msg = f"Cluster group '{group_name}' not found."
                if available_groups:
                    error_msg += f" Available groups: {', '.join(available_groups)}"

                if format_type == "json":
                    return {
                        "error": error_msg,
                        "available_groups": available_groups,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    self._show_error_panel("Group Not Found", error_msg)
                    return {"error": error_msg}

            # Get cluster members
            cluster_members = self.config_manager.get_cluster_group_members(group_name)
            if not cluster_members:
                error_msg = f"Cluster group '{group_name}' has no members."
                if format_type == "json":
                    return {
                        "error": error_msg,
                        "group_name": group_name,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    self._show_error_panel("Empty Group", error_msg)
                    return {"error": error_msg}

            # Collect data from all clusters
            report_data = self._collect_dangling_data(group_name, cluster_members)

            # Format and display results
            if format_type == "json":
                return self._format_json_report(report_data)
            else:
                return self._display_table_report(report_data)

        except Exception as e:
            self.logger.error(f"Error generating cluster group report: {e}")
            error_result = {
                "error": f"Report generation failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }

            if format_type != "json":
                self._show_error_panel("Report Generation Failed", str(e))

            return error_result

    def generate_environment_report(
        self, env_name: str, format_type: str = "table"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive dangling indices report for an environment.

        Args:
            env_name: Name of the environment
            format_type: Output format ('table' or 'json')

        Returns:
            Dictionary containing report data and results
        """
        # Ensure theme styles are properly structured
        if not isinstance(self.theme_styles.get("panel_styles"), dict):
            self.theme_styles = self._get_default_styles()
        try:
            # Validate environment exists
            if not self.config_manager.is_environment(env_name):
                available_environments = list(
                    self.config_manager.get_environments().keys()
                )
                error_msg = f"Environment '{env_name}' not found."
                if available_environments:
                    error_msg += (
                        f" Available environments: {', '.join(available_environments)}"
                    )

                if format_type == "json":
                    return {
                        "error": error_msg,
                        "available_environments": available_environments,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    self._show_error_panel("Environment Not Found", error_msg)
                    return {"error": error_msg}

            # Get environment members
            env_members = self.config_manager.get_environment_members(env_name)
            if not env_members:
                error_msg = f"Environment '{env_name}' has no members."
                if format_type == "json":
                    return {
                        "error": error_msg,
                        "env_name": env_name,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    self._show_error_panel("Empty Environment", error_msg)
                    return {"error": error_msg}

            # Collect data from all clusters in environment
            report_data = self._collect_dangling_data_for_environment(
                env_name, env_members
            )

            # Format and display results
            if format_type == "json":
                return self._format_json_report(report_data)
            else:
                return self._display_table_report(report_data)

        except Exception as e:
            self.logger.error(f"Error generating environment report: {e}")
            error_result = {
                "error": f"Report generation failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }

            if format_type != "json":
                self._show_error_panel("Report Generation Failed", str(e))

            return error_result

    def _collect_dangling_data_for_environment(
        self, env_name: str, env_members: List[str]
    ) -> Dict[str, Any]:
        """
        Collect dangling indices data from all clusters in an environment.

        Args:
            env_name: Name of the environment
            env_members: List of cluster names in the environment

        Returns:
            Dictionary containing collected data from all clusters
        """
        report_data = {
            "env_name": env_name,
            "cluster_count": len(env_members),
            "clusters": {},
            "summary": {
                "total_dangling": 0,
                "clusters_with_dangling": 0,
                "clusters_queried": 0,
                "clusters_failed": 0,
                "unique_nodes_affected": set(),
                "oldest_dangling": None,
                "newest_dangling": None,
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Use progress bar for data collection
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=False,
        ) as progress:
            task = progress.add_task(
                f"[{self._get_panel_style('info')}]Collecting dangling data from {len(env_members)} clusters in environment '{env_name}'...",
                total=len(env_members),
            )

            # Collect data from each cluster
            with ThreadPoolExecutor(max_workers=min(len(env_members), 5)) as executor:
                future_to_cluster = {
                    executor.submit(self._get_cluster_dangling_data, cluster): cluster
                    for cluster in env_members
                }

                for future in as_completed(future_to_cluster):
                    cluster = future_to_cluster[future]
                    try:
                        cluster_data = future.result(timeout=60)
                        report_data["clusters"][cluster] = cluster_data

                        # Update summary statistics
                        if cluster_data["status"] == "success":
                            report_data["summary"]["clusters_queried"] += 1
                            dangling_count = len(cluster_data["dangling_indices"])
                            report_data["summary"]["total_dangling"] += dangling_count

                            # Log cluster dangling count
                            if dangling_count > 0:
                                self.logger.info(
                                    f"Cluster '{cluster}': {dangling_count} dangling indices found"
                                )
                                report_data["summary"]["clusters_with_dangling"] += 1

                                # Track node information
                                for idx in cluster_data["dangling_indices"]:
                                    node_ids = idx.get("node_ids", [])
                                    report_data["summary"][
                                        "unique_nodes_affected"
                                    ].update(node_ids)

                                    # Track creation dates for oldest/newest
                                    creation_date = idx.get("creation_date_millis")
                                    if creation_date:
                                        if (
                                            report_data["summary"]["oldest_dangling"]
                                            is None
                                            or creation_date
                                            < report_data["summary"]["oldest_dangling"]
                                        ):
                                            report_data["summary"][
                                                "oldest_dangling"
                                            ] = creation_date
                                        if (
                                            report_data["summary"]["newest_dangling"]
                                            is None
                                            or creation_date
                                            > report_data["summary"]["newest_dangling"]
                                        ):
                                            report_data["summary"][
                                                "newest_dangling"
                                            ] = creation_date
                            else:
                                self.logger.info(
                                    f"Cluster '{cluster}': 0 dangling indices (clean)"
                                )
                        else:
                            self.logger.warning(
                                f"Cluster '{cluster}': query failed - {cluster_data.get('error', 'unknown error')}"
                            )
                            report_data["summary"]["clusters_failed"] += 1

                    except Exception as e:
                        self.logger.error(
                            f"Cluster '{cluster}': exception during data collection - {e}"
                        )
                        report_data["clusters"][cluster] = {
                            "status": "error",
                            "error": str(e),
                            "dangling_indices": [],
                            "cluster_info": {},
                        }
                        report_data["summary"]["clusters_failed"] += 1

                    finally:
                        progress.update(task, advance=1)

        # Convert set to count for JSON serialization
        report_data["summary"]["unique_nodes_affected"] = len(
            report_data["summary"]["unique_nodes_affected"]
        )

        # Log summary of environment scan
        total_clusters = (
            report_data["summary"]["clusters_queried"]
            + report_data["summary"]["clusters_failed"]
        )
        dangling_clusters = report_data["summary"]["clusters_with_dangling"]
        total_dangling = report_data["summary"]["total_dangling"]

        if total_dangling > 0:
            self.logger.warning(
                f"Environment '{env_name}' summary: {total_dangling} dangling indices found across {dangling_clusters}/{total_clusters} clusters"
            )
        else:
            self.logger.info(
                f"Environment '{env_name}' summary: All {total_clusters} clusters clean (0 dangling indices)"
            )

        return report_data

    def _collect_dangling_data(
        self, group_name: str, cluster_members: List[str]
    ) -> Dict[str, Any]:
        """
        Collect dangling indices data from all clusters in parallel.

        Args:
            group_name: Name of the cluster group
            cluster_members: List of cluster names in the group

        Returns:
            Dictionary containing collected data from all clusters
        """
        report_data = {
            "group_name": group_name,
            "cluster_count": len(cluster_members),
            "clusters": {},
            "summary": {
                "total_dangling": 0,
                "clusters_with_dangling": 0,
                "clusters_queried": 0,
                "clusters_failed": 0,
                "unique_nodes_affected": set(),
                "oldest_dangling": None,
                "newest_dangling": None,
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Use progress bar for data collection
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=False,
        ) as progress:
            task = progress.add_task(
                f"[{self._get_panel_style('info')}]Collecting dangling data from {len(cluster_members)} clusters...",
                total=len(cluster_members),
            )

            # Collect data from each cluster
            with ThreadPoolExecutor(
                max_workers=min(len(cluster_members), 5)
            ) as executor:
                future_to_cluster = {
                    executor.submit(self._get_cluster_dangling_data, cluster): cluster
                    for cluster in cluster_members
                }

                for future in as_completed(future_to_cluster):
                    cluster = future_to_cluster[future]
                    try:
                        cluster_data = future.result(timeout=60)
                        report_data["clusters"][cluster] = cluster_data

                        # Update summary statistics
                        if cluster_data["status"] == "success":
                            report_data["summary"]["clusters_queried"] += 1
                            dangling_count = len(cluster_data["dangling_indices"])
                            report_data["summary"]["total_dangling"] += dangling_count

                            if dangling_count > 0:
                                report_data["summary"]["clusters_with_dangling"] += 1

                                # Track node information
                                for idx in cluster_data["dangling_indices"]:
                                    node_ids = idx.get("node_ids", [])
                                    report_data["summary"][
                                        "unique_nodes_affected"
                                    ].update(node_ids)

                                    # Track creation dates for oldest/newest
                                    creation_date = idx.get("creation_date_millis")
                                    if creation_date:
                                        if (
                                            report_data["summary"]["oldest_dangling"]
                                            is None
                                            or creation_date
                                            < report_data["summary"]["oldest_dangling"]
                                        ):
                                            report_data["summary"][
                                                "oldest_dangling"
                                            ] = creation_date
                                        if (
                                            report_data["summary"]["newest_dangling"]
                                            is None
                                            or creation_date
                                            > report_data["summary"]["newest_dangling"]
                                        ):
                                            report_data["summary"][
                                                "newest_dangling"
                                            ] = creation_date
                        else:
                            report_data["summary"]["clusters_failed"] += 1

                    except Exception as e:
                        self.logger.error(
                            f"Error collecting data from cluster {cluster}: {e}"
                        )
                        report_data["clusters"][cluster] = {
                            "status": "error",
                            "error": str(e),
                            "dangling_indices": [],
                            "cluster_info": {},
                        }
                        report_data["summary"]["clusters_failed"] += 1

                    finally:
                        progress.update(task, advance=1)

        # Convert set to count for JSON serialization
        report_data["summary"]["unique_nodes_affected"] = len(
            report_data["summary"]["unique_nodes_affected"]
        )

        return report_data

    def _get_cluster_dangling_data(self, cluster_name: str) -> Dict[str, Any]:
        """
        Get dangling indices data from a single cluster using subprocess.

        Args:
            cluster_name: Name of the cluster to query

        Returns:
            Dictionary containing cluster's dangling data
        """
        try:
            # Build the command to get dangling data in JSON format
            cmd = [
                sys.executable,
                "escmd.py",
                "--location",
                cluster_name,
                "dangling",
                "--format",
                "json",
            ]

            # Execute the command
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=60,
                cwd=os.path.dirname(os.path.abspath(__file__ + "/../")),
            )

            if result.returncode == 0:
                # Parse JSON output
                data = json.loads(result.stdout.strip())
                dangling_indices = data.get("dangling_indices", [])

                # Get additional cluster info if available
                cluster_info = self._extract_cluster_info(result.stderr)

                return {
                    "status": "success",
                    "dangling_indices": dangling_indices,
                    "cluster_info": cluster_info,
                    "query_time": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr.strip()
                    or result.stdout.strip()
                    or "Unknown error",
                    "dangling_indices": [],
                    "cluster_info": {},
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Query timeout (60s)",
                "dangling_indices": [],
                "cluster_info": {},
            }
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "error": f"Invalid JSON response: {str(e)}",
                "dangling_indices": [],
                "cluster_info": {},
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "dangling_indices": [],
                "cluster_info": {},
            }

    def _extract_cluster_info(self, stderr_output: str) -> Dict[str, Any]:
        """
        Extract cluster information from stderr output if available.

        Args:
            stderr_output: Standard error output from the command

        Returns:
            Dictionary with extracted cluster information
        """
        # Basic implementation - can be enhanced based on actual stderr format
        info = {}

        if stderr_output:
            lines = stderr_output.split("\n")
            for line in lines:
                if "Cluster:" in line:
                    info["cluster_name"] = line.split("Cluster:")[-1].strip()
                elif "Nodes:" in line:
                    try:
                        info["node_count"] = int(line.split("Nodes:")[-1].strip())
                    except (ValueError, IndexError):
                        pass

        return info

    def _format_json_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the report data for JSON output.

        Args:
            report_data: Raw report data

        Returns:
            Formatted JSON report
        """
        # Convert datetime objects and other non-serializable data
        # Handle both group and environment reports
        if "group_name" in report_data:
            formatted_data = {
                "report_type": "cluster_group_dangling_analysis",
                "group_name": report_data["group_name"],
                "timestamp": report_data["timestamp"],
            }
        elif "env_name" in report_data:
            formatted_data = {
                "report_type": "environment_dangling_analysis",
                "env_name": report_data["env_name"],
                "timestamp": report_data["timestamp"],
            }
        else:
            formatted_data = {
                "report_type": "dangling_analysis",
                "timestamp": report_data["timestamp"],
            }

        # Add common summary data
        formatted_data.update(
            {
                "summary": {
                    "cluster_count": report_data["cluster_count"],
                    "clusters_queried_successfully": report_data["summary"][
                        "clusters_queried"
                    ],
                    "clusters_failed": report_data["summary"]["clusters_failed"],
                    "total_dangling_indices": report_data["summary"]["total_dangling"],
                    "clusters_with_dangling": report_data["summary"][
                        "clusters_with_dangling"
                    ],
                    "unique_nodes_affected": report_data["summary"][
                        "unique_nodes_affected"
                    ],
                    "oldest_dangling_timestamp": report_data["summary"][
                        "oldest_dangling"
                    ],
                    "newest_dangling_timestamp": report_data["summary"][
                        "newest_dangling"
                    ],
                },
                "clusters": {},
            }
        )

        # Add detailed cluster data
        for cluster_name, cluster_data in report_data["clusters"].items():
            formatted_data["clusters"][cluster_name] = {
                "status": cluster_data["status"],
                "dangling_count": len(cluster_data["dangling_indices"]),
                "dangling_indices": cluster_data["dangling_indices"],
                "cluster_info": cluster_data.get("cluster_info", {}),
                "query_time": cluster_data.get("query_time"),
                "error": cluster_data.get("error"),
            }

        return formatted_data

    def _display_table_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Display dangling report in table format to console.

        Args:
            report_data: Dictionary containing report data

        Returns:
            Dictionary with display results
        """
        try:
            # Display title panel - handle both group and environment reports
            if "group_name" in report_data:
                title_text = (
                    f"🔍 Cluster Group Dangling Analysis: {report_data['group_name']}"
                )
            elif "env_name" in report_data:
                title_text = (
                    f"🔍 Environment Dangling Analysis: {report_data['env_name']}"
                )
            else:
                title_text = "🔍 Dangling Indices Analysis"
            title_panel = Panel(
                Text(
                    title_text,
                    style=f"bold {self._get_panel_style('title')}",
                    justify="center",
                ),
                subtitle=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                border_style=self.theme_styles.get("border_style", "cyan"),
                padding=(1, 2),
            )

            self.console.print()
            self.console.print(title_panel)
            self.console.print()

            # Display summary statistics
            self._display_summary_panel(report_data["summary"])

            # Display cluster breakdown
            self._display_cluster_breakdown(report_data["clusters"])

            # Display detailed dangling indices if any found
            if report_data["summary"]["total_dangling"] > 0:
                self._display_dangling_details(report_data["clusters"])

            # Display recommendations
            self._display_recommendations(report_data["summary"])

            return {
                "displayed": True,
                "summary": report_data["summary"],
                "timestamp": report_data["timestamp"],
            }

        except Exception as e:
            self.logger.error(f"Error displaying table report: {e}")
            self._show_error_panel("Display Error", str(e))
            return {"error": str(e), "displayed": False}

    def _display_summary_panel(self, summary: Dict[str, Any]) -> None:
        """Display summary statistics panel."""
        summary_table = Table(
            show_header=False, box=None, padding=(0, 1), width=None, expand=False
        )
        summary_table.add_column(
            "Label",
            style=self.theme_styles.get("header_style", "bold white"),
            no_wrap=True,
            min_width=18,
        )
        summary_table.add_column("Icon", justify="center", width=4)
        summary_table.add_column(
            "Value", style=self._get_panel_style("info"), min_width=12
        )
        summary_table.add_column("Details", style="dim white", min_width=30)

        # Determine status icon based on dangling count
        status_icon = "✅" if summary["total_dangling"] == 0 else "🔶"

        summary_table.add_row(
            "Overall Status:",
            status_icon,
            "Clean" if summary["total_dangling"] == 0 else "Issues Found",
            f"{summary['total_dangling']} dangling indices",
        )

        summary_table.add_row(
            "Clusters Analyzed:",
            "🔍",
            str(summary["clusters_queried"]),
            f"{summary['clusters_failed']} failed"
            if summary["clusters_failed"] > 0
            else "All successful",
        )

        summary_table.add_row(
            "Clusters Affected:",
            "🚨",
            str(summary["clusters_with_dangling"]),
            f"out of {summary['clusters_queried']} total",
        )

        summary_table.add_row(
            "Nodes Affected:",
            "💻",
            str(summary["unique_nodes_affected"]),
            "unique nodes with dangling indices",
        )

        # Add time range if available
        if summary["oldest_dangling"] and summary["newest_dangling"]:
            oldest_date = datetime.fromtimestamp(summary["oldest_dangling"] / 1000)
            newest_date = datetime.fromtimestamp(summary["newest_dangling"] / 1000)

            summary_table.add_row(
                "Time Range:",
                "📅",
                f"{oldest_date.strftime('%Y-%m-%d')} to {newest_date.strftime('%Y-%m-%d')}",
                "oldest to newest dangling index",
            )

        summary_panel = Panel(
            Align.center(summary_table),
            title="[bold white]📊 Summary Statistics[/bold white]",
            border_style=self.theme_styles.get("border_style", "cyan"),
            padding=(1, 2),
            width=None,
            expand=False,
        )

        self.console.print(summary_panel, justify="center")
        self.console.print()

    def _display_cluster_breakdown(self, clusters: Dict[str, Any]) -> None:
        """Display per-cluster breakdown table."""
        breakdown_table = Table(
            show_header=True,
            header_style=self.theme_styles.get("header_style", "bold white"),
            width=None,
            expand=True,
        )
        breakdown_table.add_column(
            "🏗️  Cluster",
            style=f"bold {self._get_panel_style('info')}",
            no_wrap=True,
            min_width=15,
        )
        breakdown_table.add_column("📊 Status", justify="center", min_width=12)
        breakdown_table.add_column(
            "🔶  Dangling",
            justify="center",
            style=self._get_health_style("yellow"),
            min_width=12,
        )
        breakdown_table.add_column(
            "💻  Nodes",
            justify="center",
            style=self._get_panel_style("info"),
            min_width=10,
        )
        breakdown_table.add_column("📝 Details", style="dim white", min_width=25)

        # Sort clusters by dangling count (descending) then by name
        sorted_clusters = sorted(
            clusters.items(), key=lambda x: (-len(x[1]["dangling_indices"]), x[0])
        )

        for cluster_name, cluster_data in sorted_clusters:
            if cluster_data["status"] == "success":
                dangling_count = len(cluster_data["dangling_indices"])
                status_text = "✅ OK" if dangling_count == 0 else "🔶 Issues"
                status_color = (
                    self._get_health_style("green")
                    if dangling_count == 0
                    else self._get_health_style("yellow")
                )

                # Count unique nodes affected in this cluster
                affected_nodes = set()
                for idx in cluster_data["dangling_indices"]:
                    affected_nodes.update(idx.get("node_ids", []))

                details = (
                    "Clean"
                    if dangling_count == 0
                    else f"{len(affected_nodes)} nodes affected"
                )

                breakdown_table.add_row(
                    cluster_name,
                    f"[{status_color}]{status_text}[/{status_color}]",
                    str(dangling_count) if dangling_count > 0 else "-",
                    str(len(affected_nodes)) if affected_nodes else "-",
                    details,
                )
            else:
                breakdown_table.add_row(
                    cluster_name,
                    f"[{self._get_health_style('red')}]❌ Error[/{self._get_health_style('red')}]",
                    "-",
                    "-",
                    cluster_data.get("error", "Unknown error")[:50] + "...",
                )

        breakdown_panel = Panel(
            breakdown_table,
            title="[bold white]🏗️ Cluster Breakdown[/bold white]",
            border_style=self.theme_styles.get("border_style", "cyan"),
            padding=(1, 2),
            expand=True,
        )

        self.console.print(breakdown_panel)
        self.console.print()

    def _display_dangling_details(self, clusters: Dict[str, Any]) -> None:
        """Display detailed information about dangling indices."""
        # Create a consolidated table of all dangling indices
        details_table = Table(
            show_header=True,
            header_style=self.theme_styles.get("header_style", "bold white"),
            width=None,
            expand=True,
        )
        details_table.add_column(
            "🏗️ Cluster", style=f"bold {self._get_panel_style('info')}", min_width=15
        )
        details_table.add_column(
            "📄 Index Name", style=self._get_health_style("yellow"), min_width=25
        )
        details_table.add_column("🔑 UUID", style="dim white", min_width=15)
        details_table.add_column(
            "📅 Created", style=self._get_health_style("green"), min_width=16
        )
        details_table.add_column(
            "💻 Nodes", style=self._get_panel_style("info"), min_width=15
        )

        # Collect and sort all dangling indices
        all_dangling = []
        for cluster_name, cluster_data in clusters.items():
            if cluster_data["status"] == "success":
                for idx in cluster_data["dangling_indices"]:
                    all_dangling.append({"cluster": cluster_name, "data": idx})

        # Sort by creation date (newest first)
        all_dangling.sort(
            key=lambda x: x["data"].get("creation_date_millis", 0), reverse=True
        )

        # Display up to 20 most recent entries
        display_count = min(len(all_dangling), 20)
        for i, item in enumerate(all_dangling[:display_count]):
            cluster_name = item["cluster"]
            idx_data = item["data"]

            # Format creation date
            creation_date = "Unknown"
            if idx_data.get("creation_date_millis"):
                try:
                    dt = datetime.fromtimestamp(idx_data["creation_date_millis"] / 1000)
                    creation_date = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    creation_date = "Invalid"

            # Format node list
            nodes = idx_data.get("node_ids", [])
            node_text = f"{len(nodes)} nodes" if nodes else "No nodes"
            if len(nodes) <= 3:
                node_text = ", ".join(nodes) if nodes else "None"

            details_table.add_row(
                cluster_name,
                idx_data.get("index_name", "Unknown")[:30],
                idx_data.get("index_uuid", "Unknown")[:12] + "...",
                creation_date,
                node_text,
            )

        title_suffix = (
            f" (showing {display_count} of {len(all_dangling)})"
            if len(all_dangling) > 20
            else f" ({len(all_dangling)} total)"
        )

        details_panel = Panel(
            details_table,
            title=f"[bold white]🔍 Dangling Indices Details{title_suffix}[/bold white]",
            border_style=self._get_health_style("yellow"),
            padding=(1, 2),
            expand=True,
        )

        self.console.print(details_panel)
        self.console.print()

    def _display_recommendations(self, summary: Dict[str, Any]) -> None:
        """Display recommendations based on the analysis."""
        recommendations_table = Table(show_header=False, box=None, padding=(0, 1))
        recommendations_table.add_column("Icon", width=4)
        recommendations_table.add_column(
            "Recommendation", style=self._get_panel_style("info")
        )

        if summary["total_dangling"] == 0:
            recommendations_table.add_row(
                "🎉", "Excellent! No dangling indices found across the cluster group."
            )
            recommendations_table.add_row(
                "🔄", "Continue regular monitoring to maintain cluster health."
            )
            panel_style = self._get_health_style("green")
            title = "✅ All Clear"
        else:
            recommendations_table.add_row(
                "🚨",
                f"Found {summary['total_dangling']} dangling indices across {summary['clusters_with_dangling']} clusters.",
            )
            recommendations_table.add_row(
                "🔍", "Review each dangling index before deletion to avoid data loss."
            )
            recommendations_table.add_row(
                "🧰",
                "Use 'escmd.py --location <cluster> dangling <uuid> --delete' for targeted cleanup.",
            )
            recommendations_table.add_row(
                "⚡",
                "For bulk cleanup: 'escmd.py --location <cluster> dangling --cleanup-all --dry-run' first.",
            )
            panel_style = self._get_health_style("yellow")
            title = "🔶 Action Required"

        recommendations_panel = Panel(
            recommendations_table,
            title=f"[bold white]{title}[/bold white]",
            border_style=panel_style,
            padding=(1, 2),
            expand=True,
        )

        self.console.print(recommendations_panel)
        self.console.print()

    def _show_error_panel(self, title: str, message: str) -> None:
        """Display an error panel."""
        error_panel = Panel(
            Text(message, style=self._get_health_style("red")),
            title=f"[bold {self._get_health_style('red')}]❌ {title}[/bold {self._get_health_style('red')}]",
            border_style=self._get_health_style("red"),
            padding=(1, 2),
        )

        self.console.print()
        self.console.print(error_panel)
        self.console.print()
