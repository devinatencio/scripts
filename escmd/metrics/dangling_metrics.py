"""
Dangling metrics handler for InfluxDB and VictoriaMetrics integration.

This module provides specific functionality for sending dangling indices metrics
to time-series databases, including processing environment-wide statistics.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
from .metrics_client import MetricsClient


class DanglingMetrics:
    """
    Handler for dangling indices metrics collection and transmission.

    Formats and sends dangling statistics in the format:
    elastic_dangling_deletion,cluster={} found={}, deleted={}, nodes_affected={}
    """

    def __init__(
        self,
        metrics_client: Optional[MetricsClient] = None,
        config_manager: Optional[Any] = None,
        environment: Optional[str] = None,
    ):
        """
        Initialize the dangling metrics handler.

        Args:
            metrics_client: Pre-configured MetricsClient instance
            config_manager: Configuration manager for getting metrics settings
            environment: Environment name for environment-specific configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.environment = environment
        self.metrics_client = metrics_client or self._create_metrics_client()

    def _create_metrics_client(self) -> Optional[MetricsClient]:
        """
        Create a metrics client based on configuration or environment variables.

        Returns:
            MetricsClient instance or None if not configured
        """
        try:
            # Check environment variables first
            endpoint = os.environ.get("ESCMD_METRICS_ENDPOINT")
            database = os.environ.get("ESCMD_METRICS_DATABASE", "escmd")
            username = os.environ.get("ESCMD_METRICS_USERNAME")
            password = os.environ.get("ESCMD_METRICS_PASSWORD")
            token = os.environ.get("ESCMD_METRICS_TOKEN")
            metrics_type = os.environ.get("ESCMD_METRICS_TYPE", "influxdb").lower()
            org = os.environ.get("ESCMD_METRICS_ORG")
            bucket = os.environ.get("ESCMD_METRICS_BUCKET")
            verify_ssl = (
                os.environ.get("ESCMD_METRICS_VERIFY_SSL", "true").lower() == "true"
            )

            # Check configuration manager if available
            if self.config_manager and not endpoint:
                try:
                    metrics_config = self.config_manager.get_metrics_config(
                        self.environment
                    )
                    if metrics_config:
                        endpoint = metrics_config.get("endpoint")
                        database = metrics_config.get("database", database)
                        username = metrics_config.get("username")
                        password = metrics_config.get("password")
                        token = metrics_config.get("token")
                        metrics_type = metrics_config.get("type", metrics_type)
                        org = metrics_config.get("org")
                        bucket = metrics_config.get("bucket")
                        verify_ssl = metrics_config.get("verify_ssl", verify_ssl)
                except (AttributeError, KeyError):
                    # Configuration manager doesn't have metrics config method
                    pass

            if not endpoint:
                self.logger.debug("No metrics endpoint configured")
                return None

            return MetricsClient(
                endpoint=endpoint,
                database=database,
                username=username,
                password=password,
                token=token,
                metrics_type=metrics_type,
                org=org,
                bucket=bucket,
                verify_ssl=verify_ssl,
            )

        except Exception as e:
            self.logger.error(f"Failed to create metrics client: {str(e)}")
            return None

    def send_dangling_metric(
        self,
        cluster_name: str,
        found: int,
        deleted: int = 0,
        nodes_affected: int = 0,
        environment: Optional[str] = None,
        additional_tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[int] = None,
        dry_run: bool = False,
    ) -> bool:
        """
        Send a dangling indices metric for a single cluster.

        Args:
            cluster_name: Name of the cluster
            found: Number of dangling indices found
            deleted: Number of dangling indices deleted
            nodes_affected: Number of nodes affected by dangling indices
            environment: Environment name (optional)
            additional_tags: Additional tags to include (optional)
            timestamp: Unix timestamp in nanoseconds (optional)
            dry_run: If True, only print what would be sent without sending

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.metrics_client:
            self.logger.warning("No metrics client available, skipping metric")
            return False

        try:
            # Build tags
            tags = {"cluster": cluster_name}
            if environment:
                tags["environment"] = environment
            if additional_tags:
                tags.update(additional_tags)

            # Build fields
            fields = {
                "found": found,
                "deleted": deleted,
                "nodes_affected": nodes_affected,
            }

            if dry_run:
                # Format the line protocol for display
                line_protocol = self.metrics_client._format_line_protocol(
                    measurement="elastic_dangling_deletion",
                    tags=tags,
                    fields=fields,
                    timestamp=timestamp,
                )

                print(line_protocol)

                self.logger.info(
                    f"Dry run - would send dangling metric for cluster {cluster_name}: "
                    f"found={found}, deleted={deleted}, nodes_affected={nodes_affected}"
                )
                return True
            else:
                success = self.metrics_client.send_metric(
                    measurement="elastic_dangling_deletion",
                    tags=tags,
                    fields=fields,
                    timestamp=timestamp,
                )

                if success:
                    database_type = (
                        "VictoriaMetrics"
                        if self.metrics_client.metrics_type == "victoriametrics"
                        else "InfluxDB"
                    )
                    self.logger.info(
                        f"Successfully inserted 1 record into {database_type} for cluster {cluster_name}: "
                        f"found={found}, deleted={deleted}, nodes_affected={nodes_affected}"
                    )
                else:
                    self.logger.error(
                        f"Failed to send dangling metric for cluster {cluster_name}"
                    )

                return success

        except Exception as e:
            self.logger.error(
                f"Error sending dangling metric for cluster {cluster_name}: {str(e)}"
            )
            return False

    def send_environment_metrics(
        self,
        environment_name: str,
        cluster_data: Dict[str, Dict[str, Any]],
        additional_tags: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, bool]:
        """
        Send dangling metrics for all clusters in an environment.

        Args:
            environment_name: Name of the environment
            cluster_data: Dictionary mapping cluster names to their dangling data
            additional_tags: Additional tags to include for all metrics
            dry_run: If True, only print what would be sent without sending

        Returns:
            Dict[str, bool]: Dictionary mapping cluster names to success status
        """
        results = {}

        if not self.metrics_client:
            self.logger.warning(
                "No metrics client available, skipping environment metrics"
            )
            return {cluster: False for cluster in cluster_data.keys()}

        timestamp = int(
            datetime.now().timestamp() * 1000000000
        )  # Current time in nanoseconds

        for cluster_name, data in cluster_data.items():
            try:
                if data.get("status") != "success":
                    self.logger.warning(
                        f"Skipping metrics for cluster {cluster_name} due to error status"
                    )
                    results[cluster_name] = False
                    continue

                # Extract metrics from cluster data
                dangling_indices = data.get("dangling_indices", [])
                found = len(dangling_indices)
                deleted = 0  # No deletion in report mode

                # Count unique nodes affected
                nodes_affected = set()
                for index in dangling_indices:
                    node_ids = index.get("node_ids", [])
                    nodes_affected.update(node_ids)

                nodes_affected_count = len(nodes_affected)

                # Send metric for this cluster
                success = self.send_dangling_metric(
                    cluster_name=cluster_name,
                    found=found,
                    deleted=deleted,
                    nodes_affected=nodes_affected_count,
                    environment=environment_name,
                    additional_tags=additional_tags,
                    timestamp=timestamp,
                    dry_run=dry_run,
                )

                results[cluster_name] = success

            except Exception as e:
                self.logger.error(
                    f"Error processing metrics for cluster {cluster_name}: {str(e)}"
                )
                results[cluster_name] = False

        # Log summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        database_type = (
            "VictoriaMetrics"
            if self.metrics_client
            and self.metrics_client.metrics_type == "victoriametrics"
            else "InfluxDB"
        )
        self.logger.info(
            f"Successfully inserted {successful} records into {database_type} for {successful}/{total} clusters in environment {environment_name}"
        )

        return results

    def send_cleanup_metrics(
        self,
        cleanup_results: Dict[str, Dict[str, Any]],
        environment: Optional[str] = None,
        additional_tags: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, bool]:
        """
        Send metrics after a cleanup operation across multiple clusters.

        Args:
            cleanup_results: Dictionary mapping cluster names to cleanup results
            environment: Environment name (optional)
            additional_tags: Additional tags to include
            dry_run: If True, only print what would be sent without sending

        Returns:
            Dict[str, bool]: Dictionary mapping cluster names to success status
        """
        results = {}

        if not self.metrics_client:
            self.logger.warning("No metrics client available, skipping cleanup metrics")
            return {cluster: False for cluster in cleanup_results.keys()}

        timestamp = int(datetime.now().timestamp() * 1000000000)

        for cluster_name, cleanup_data in cleanup_results.items():
            try:
                found = cleanup_data.get("found", 0)
                deleted = cleanup_data.get("deleted", 0)
                nodes_affected = cleanup_data.get("nodes_affected", 0)

                success = self.send_dangling_metric(
                    cluster_name=cluster_name,
                    found=found,
                    deleted=deleted,
                    nodes_affected=nodes_affected,
                    environment=environment,
                    additional_tags=additional_tags,
                    timestamp=timestamp,
                    dry_run=dry_run,
                )

                results[cluster_name] = success

            except Exception as e:
                self.logger.error(
                    f"Error sending cleanup metrics for cluster {cluster_name}: {str(e)}"
                )
                results[cluster_name] = False

        return results

    def is_enabled(self) -> bool:
        """
        Check if metrics collection is enabled.

        Returns:
            bool: True if metrics client is available and configured
        """
        return self.metrics_client is not None

    def test_connection(self) -> bool:
        """
        Test the connection to the metrics database.

        Returns:
            bool: True if connection test is successful
        """
        if not self.metrics_client:
            return False

        return self.metrics_client.test_connection()

    def send_batch_metrics(
        self, metrics_data: List[Dict[str, Any]], dry_run: bool = False
    ) -> bool:
        """
        Send multiple dangling metrics in a single batch.

        Args:
            metrics_data: List of metric dictionaries, each containing:
                         - cluster_name: str
                         - found: int
                         - deleted: int
                         - nodes_affected: int
                         - environment: str (optional)
                         - additional_tags: Dict[str, str] (optional)
                         - timestamp: int (optional)
            dry_run: If True, only print what would be sent without sending

        Returns:
            bool: True if all metrics sent successfully
        """
        if not self.metrics_client:
            self.logger.warning("No metrics client available, skipping batch metrics")
            return False

        try:
            batch_timestamp = int(datetime.now().timestamp() * 1000000000)
            metrics = []

            for data in metrics_data:
                cluster_name = data.get("cluster_name")
                if not cluster_name:
                    continue

                # Build tags
                tags = {"cluster": cluster_name}
                if data.get("environment"):
                    tags["environment"] = data["environment"]
                if data.get("additional_tags"):
                    tags.update(data["additional_tags"])

                # Build fields
                fields = {
                    "found": data.get("found", 0),
                    "deleted": data.get("deleted", 0),
                    "nodes_affected": data.get("nodes_affected", 0),
                }

                metrics.append(
                    {
                        "measurement": "elastic_dangling_deletion",
                        "tags": tags,
                        "fields": fields,
                        "timestamp": data.get("timestamp", batch_timestamp),
                    }
                )

            if not metrics:
                self.logger.warning("No valid metrics to send in batch")
                return False

            if dry_run:
                for metric in metrics:
                    line_protocol = self.metrics_client._format_line_protocol(
                        measurement=metric["measurement"],
                        tags=metric["tags"],
                        fields=metric["fields"],
                        timestamp=metric["timestamp"],
                    )
                    print(line_protocol)

                self.logger.info(
                    f"Dry run - would send batch of {len(metrics)} dangling metrics"
                )
                return True
            else:
                success = self.metrics_client.send_metrics(metrics)

                if success:
                    database_type = (
                        "VictoriaMetrics"
                        if self.metrics_client.metrics_type == "victoriametrics"
                        else "InfluxDB"
                    )
                    self.logger.info(
                        f"Successfully inserted {len(metrics)} records into {database_type} (batch operation)"
                    )
                else:
                    self.logger.error(
                        f"Failed to send batch of {len(metrics)} dangling metrics"
                    )

                return success

        except Exception as e:
            self.logger.error(f"Error sending batch metrics: {str(e)}")
            return False
