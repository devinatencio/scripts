"""
Metrics integration module for InfluxDB and VictoriaMetrics.

This module provides functionality to send metrics data to time-series databases
like InfluxDB and VictoriaMetrics for monitoring and alerting purposes.
"""

from .metrics_client import MetricsClient
from .dangling_metrics import DanglingMetrics

__all__ = ["MetricsClient", "DanglingMetrics"]
