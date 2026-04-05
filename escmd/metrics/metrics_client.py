"""
Base metrics client for sending data to InfluxDB and VictoriaMetrics.

This module provides a unified interface for sending metrics data to time-series databases
like InfluxDB and VictoriaMetrics. It supports both InfluxDB line protocol and HTTP-based
metric submission.
"""

import requests
import time
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin
import logging
from datetime import datetime


class MetricsClient:
    """
    A client for sending metrics to InfluxDB and VictoriaMetrics.

    Supports both InfluxDB line protocol and VictoriaMetrics write format.
    """

    def __init__(
        self,
        endpoint: str,
        database: str = None,
        username: str = None,
        password: str = None,
        token: str = None,
        timeout: int = 10,
        verify_ssl: bool = True,
        metrics_type: str = "influxdb",
        org: str = None,
        bucket: str = None,
    ):
        """
        Initialize the metrics client.

        Args:
            endpoint: The base URL of the metrics database (e.g., 'http://localhost:8086')
            database: Database name (InfluxDB v1) or measurement name
            username: Username for authentication
            password: Password for authentication
            token: Token for InfluxDB v2 authentication
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            metrics_type: Type of metrics backend ('influxdb', 'influxdb2', 'victoriametrics')
            org: Organization for InfluxDB v2
            bucket: Bucket for InfluxDB v2
        """
        self.endpoint = endpoint.rstrip("/")
        self.database = database
        self.username = username
        self.password = password
        self.token = token
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.metrics_type = metrics_type.lower()
        self.org = org
        self.bucket = bucket

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Setup session
        self.session = requests.Session()
        self.session.verify = verify_ssl

        # Configure authentication
        if self.token:
            self.session.headers.update({"Authorization": f"Token {self.token}"})
        elif self.username and self.password:
            self.session.auth = (self.username, self.password)

    def send_metric(
        self,
        measurement: str,
        tags: Dict[str, str] = None,
        fields: Dict[str, Union[str, int, float, bool]] = None,
        timestamp: Optional[int] = None,
    ) -> bool:
        """
        Send a single metric to the database.

        Args:
            measurement: The measurement name
            tags: Dictionary of tag key-value pairs
            fields: Dictionary of field key-value pairs
            timestamp: Unix timestamp in nanoseconds (optional, defaults to current time)

        Returns:
            bool: True if successful, False otherwise
        """
        if not fields:
            self.logger.warning("No fields provided for metric, skipping")
            return False

        # Generate line protocol format
        line = self._format_line_protocol(measurement, tags, fields, timestamp)

        return self._send_lines([line])

    def send_metrics(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Send multiple metrics to the database.

        Args:
            metrics: List of metric dictionaries, each containing:
                     - measurement: str
                     - tags: Dict[str, str] (optional)
                     - fields: Dict[str, Union[str, int, float, bool]]
                     - timestamp: int (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        lines = []
        for metric in metrics:
            measurement = metric.get("measurement")
            tags = metric.get("tags", {})
            fields = metric.get("fields", {})
            timestamp = metric.get("timestamp")

            if not measurement or not fields:
                self.logger.warning(f"Skipping invalid metric: {metric}")
                continue

            line = self._format_line_protocol(measurement, tags, fields, timestamp)
            lines.append(line)

        if not lines:
            self.logger.warning("No valid metrics to send")
            return False

        return self._send_lines(lines)

    def _format_line_protocol(
        self,
        measurement: str,
        tags: Dict[str, str] = None,
        fields: Dict[str, Union[str, int, float, bool]] = None,
        timestamp: Optional[int] = None,
    ) -> str:
        """
        Format a metric in InfluxDB line protocol format.

        Returns:
            str: Line protocol formatted string
        """
        # Escape measurement name
        measurement = self._escape_measurement(measurement)

        # Format tags
        tag_string = ""
        if tags:
            tag_pairs = []
            for key, value in sorted(tags.items()):
                key = self._escape_tag_key(str(key))
                value = self._escape_tag_value(str(value))
                tag_pairs.append(f"{key}={value}")
            if tag_pairs:
                tag_string = "," + ",".join(tag_pairs)

        # Format fields
        field_pairs = []
        for key, value in fields.items():
            key = self._escape_field_key(str(key))
            value = self._format_field_value(value)
            field_pairs.append(f"{key}={value}")
        field_string = ",".join(field_pairs)

        # Format timestamp
        timestamp_string = ""
        if timestamp is not None:
            timestamp_string = f" {timestamp}"
        elif timestamp is None:
            # Use current time in nanoseconds
            timestamp_string = f" {int(time.time() * 1000000000)}"

        return f"{measurement}{tag_string} {field_string}{timestamp_string}"

    def _send_lines(self, lines: List[str]) -> bool:
        """
        Send line protocol data to the database.

        Args:
            lines: List of line protocol formatted strings

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = "\n".join(lines)
            url = self._get_write_url()

            headers = {"Content-Type": "text/plain; charset=utf-8"}

            response = self.session.post(
                url, data=data, headers=headers, timeout=self.timeout
            )

            if response.status_code in [200, 204]:
                database_type = (
                    "VictoriaMetrics"
                    if self.metrics_type == "victoriametrics"
                    else "InfluxDB"
                )
                self.logger.info(
                    f"Successfully inserted {len(lines)} records into {database_type}"
                )
                return True
            else:
                self.logger.error(
                    f"Failed to send metrics: HTTP {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error sending metrics: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending metrics: {str(e)}")
            return False

    def _get_write_url(self) -> str:
        """Get the appropriate write URL based on metrics type."""
        if self.metrics_type == "influxdb2":
            # InfluxDB 2.x format
            url = f"{self.endpoint}/api/v2/write"
            params = []
            if self.org:
                params.append(f"org={self.org}")
            if self.bucket:
                params.append(f"bucket={self.bucket}")
            elif self.database:
                params.append(f"bucket={self.database}")
            if params:
                url += "?" + "&".join(params)
            return url
        elif self.metrics_type == "victoriametrics":
            # VictoriaMetrics format
            return f"{self.endpoint}/api/v1/write"
        else:
            # InfluxDB 1.x format (default)
            url = f"{self.endpoint}/write"
            if self.database:
                url += f"?db={self.database}"
            return url

    def _escape_measurement(self, measurement: str) -> str:
        """Escape measurement name for line protocol."""
        return measurement.replace(" ", "\\ ").replace(",", "\\,")

    def _escape_tag_key(self, key: str) -> str:
        """Escape tag key for line protocol."""
        return key.replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

    def _escape_tag_value(self, value: str) -> str:
        """Escape tag value for line protocol."""
        return value.replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

    def _escape_field_key(self, key: str) -> str:
        """Escape field key for line protocol."""
        return key.replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

    def _format_field_value(self, value: Union[str, int, float, bool]) -> str:
        """Format field value for line protocol."""
        if isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, int):
            return f"{value}i"
        elif isinstance(value, float):
            return str(value)
        else:
            # String values need to be quoted and escaped
            escaped = str(value).replace('"', '\\"')
            return f'"{escaped}"'

    def test_connection(self) -> bool:
        """
        Test the connection to the metrics database.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Send a test metric
            test_metric = {
                "measurement": "test_connection",
                "tags": {"source": "escmd"},
                "fields": {"test": 1},
            }

            return self.send_metric(
                test_metric["measurement"], test_metric["tags"], test_metric["fields"]
            )

        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if hasattr(self, "session"):
            self.session.close()
