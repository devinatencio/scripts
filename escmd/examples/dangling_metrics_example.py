#!/usr/bin/env python3
"""
Example script demonstrating dangling metrics functionality.

This script shows how to use the escmd dangling command with metrics integration
for InfluxDB/VictoriaMetrics monitoring.
"""

import os
import sys
import subprocess
import json
from datetime import datetime

# Configuration examples
EXAMPLE_CONFIGS = {
    "influxdb_v1": {
        "type": "influxdb",
        "endpoint": "http://localhost:8086",
        "database": "escmd",
        "username": "admin",
        "password": "password",
        "verify_ssl": False,
        "timeout": 10,
    },
    "influxdb_v2": {
        "type": "influxdb2",
        "endpoint": "http://localhost:8086",
        "org": "my-org",
        "bucket": "escmd",
        "token": "your-token-here",
        "verify_ssl": True,
        "timeout": 10,
    },
    "victoriametrics": {
        "type": "victoriametrics",
        "endpoint": "http://localhost:8428",
        "timeout": 10,
    },
}


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def run_escmd_command(command_args, dry_run=True):
    """
    Run an escmd command and return the result.

    Args:
        command_args: List of command arguments
        dry_run: Whether to include --dry-run flag

    Returns:
        dict: Command result with stdout, stderr, and return_code
    """
    # Add dry-run if requested
    if dry_run and "--dry-run" not in command_args:
        command_args.append("--dry-run")

    # Build full command
    full_command = ["python3", "escmd.py"] + command_args

    print(f"Running: {' '.join(full_command)}")
    print("-" * 40)

    try:
        result = subprocess.run(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=30,
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Command timed out",
            "return_code": 124,
            "success": False,
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "return_code": 1, "success": False}


def example_1_basic_metrics():
    """Example 1: Basic dangling metrics with dry-run."""
    print_header("Example 1: Basic Dangling Metrics (Dry Run)")

    print("This example shows how to test dangling metrics without sending data.")
    print("Perfect for validating your configuration and seeing the exact")
    print("line protocol that would be sent to InfluxDB/VictoriaMetrics.\n")

    # Run with dry-run
    result = run_escmd_command(["dangling", "--metrics"], dry_run=True)

    if result["success"]:
        print("✅ Command executed successfully")
        if result["stdout"]:
            print(f"Output:\n{result['stdout']}")
    else:
        print("❌ Command failed")
        if result["stderr"]:
            print(f"Error: {result['stderr']}")

    print("\nNext steps:")
    print("- Remove --dry-run to actually send metrics")
    print("- Configure your metrics endpoint in escmd.yml")
    print("- Set up monitoring dashboards")


def example_2_environment_metrics():
    """Example 2: Environment-wide metrics collection."""
    print_header("Example 2: Environment-Wide Metrics")

    print("This example demonstrates collecting metrics across all clusters")
    print("in a specific environment. Great for comprehensive monitoring.\n")

    # Example with environment
    result = run_escmd_command(
        ["dangling", "--env", "production", "--metrics"], dry_run=True
    )

    if result["success"]:
        print("✅ Environment scan completed")
        if result["stdout"]:
            print(f"Output:\n{result['stdout']}")
    else:
        print("❌ Environment scan failed")
        if result["stderr"]:
            print(f"Error: {result['stderr']}")


def example_3_cleanup_metrics():
    """Example 3: Cleanup operation with metrics."""
    print_header("Example 3: Cleanup with Metrics Tracking")

    print("This example shows how to track cleanup operations.")
    print("Metrics will include both found and deleted counts.\n")

    # Cleanup with metrics
    result = run_escmd_command(["dangling", "--cleanup-all", "--metrics"], dry_run=True)

    if result["success"]:
        print("✅ Cleanup simulation completed")
        if result["stdout"]:
            print(f"Output:\n{result['stdout']}")
    else:
        print("❌ Cleanup simulation failed")
        if result["stderr"]:
            print(f"Error: {result['stderr']}")


def example_4_cron_setup():
    """Example 4: Cron job setup examples."""
    print_header("Example 4: Cron Job Setup")

    print("Here are some example cron jobs for automated metrics collection:\n")

    cron_examples = [
        {
            "schedule": "0 */6 * * *",
            "description": "Every 6 hours - basic cluster check",
            "command": "./escmd.py dangling --metrics --locations prod-cluster",
        },
        {
            "schedule": "0 2 * * *",
            "description": "Daily at 2 AM - environment-wide scan",
            "command": "./escmd.py dangling --env production --metrics",
        },
        {
            "schedule": "0 3 * * 0",
            "description": "Weekly on Sunday at 3 AM - automated cleanup",
            "command": "./escmd.py dangling --cleanup-all --metrics --yes-i-really-mean-it",
        },
    ]

    for example in cron_examples:
        print(f"# {example['description']}")
        print(f"{example['schedule']} {example['command']}")
        print()

    print("🔶  Important notes for production:")
    print("- Test with --dry-run first")
    print("- Use --yes-i-really-mean-it only after thorough testing")
    print("- Set up proper logging for cron jobs")
    print("- Monitor the metrics database disk usage")


def example_5_grafana_queries():
    """Example 5: Grafana dashboard queries."""
    print_header("Example 5: Grafana Dashboard Queries")

    print("Example InfluxQL queries for creating Grafana dashboards:\n")

    queries = [
        {
            "title": "Dangling Indices Count by Cluster",
            "query": '''SELECT last("found")
FROM "elastic_dangling_deletion"
WHERE $timeFilter
GROUP BY "cluster"''',
            "description": "Shows current count of dangling indices per cluster",
        },
        {
            "title": "Cleanup Efficiency Over Time",
            "query": '''SELECT mean("deleted") / mean("found") * 100 as efficiency
FROM "elastic_dangling_deletion"
WHERE $timeFilter AND "deleted" > 0
GROUP BY time(1d), "cluster"''',
            "description": "Tracks cleanup success rate over time",
        },
        {
            "title": "Nodes Affected by Environment",
            "query": """SELECT sum("nodes_affected")
FROM "elastic_dangling_deletion"
WHERE $timeFilter
GROUP BY "environment", time(1h)""",
            "description": "Shows nodes affected by dangling indices per environment",
        },
        {
            "title": "Alert: High Dangling Index Count",
            "query": """SELECT last("found")
FROM "elastic_dangling_deletion"
WHERE time >= now() - 1h
GROUP BY "cluster"
HAVING last("found") > 10""",
            "description": "Alert when any cluster has more than 10 dangling indices",
        },
    ]

    for i, query in enumerate(queries, 1):
        print(f"{i}. {query['title']}")
        print(f"   Description: {query['description']}")
        print(f"   Query:")
        print(f"   {query['query']}")
        print()


def example_6_configuration_test():
    """Example 6: Test configuration setup."""
    print_header("Example 6: Configuration Testing")

    print("Here's how to test different metric configurations:\n")

    for db_type, config in EXAMPLE_CONFIGS.items():
        print(f"{db_type.upper()} Configuration:")
        print("=" * 30)

        # Show YAML format
        print("escmd.yml format:")
        print("metrics:")
        for key, value in config.items():
            if isinstance(value, str):
                print(f'  {key}: "{value}"')
            else:
                print(f"  {key}: {value}")

        print()

        # Show environment variables
        print("Environment variables:")
        for key, value in config.items():
            env_key = f"ESCMD_METRICS_{key.upper()}"
            print(f'export {env_key}="{value}"')

        print()
        print("-" * 50)
        print()


def example_7_monitoring_script():
    """Example 7: Custom monitoring script."""
    print_header("Example 7: Custom Monitoring Script")

    monitoring_script = """#!/bin/bash
# dangling_monitor.sh - Custom monitoring script for dangling indices

set -e

LOG_FILE="/var/log/escmd/dangling_monitor.log"
ESCMD_PATH="/opt/escmd"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

# Function to send metrics for a cluster
send_cluster_metrics() {
    local cluster=$1
    log "Checking cluster: $cluster"

    cd "$ESCMD_PATH"
    if ./escmd.py dangling --metrics --locations "$cluster" >> "$LOG_FILE" 2>&1; then
        log "✅ Successfully sent metrics for cluster: $cluster"
        return 0
    else
        log "❌ Failed to send metrics for cluster: $cluster"
        return 1
    fi
}

# Main monitoring loop
main() {
    log "Starting dangling indices monitoring"

    # List of clusters to monitor
    CLUSTERS=("prod-cluster-01" "prod-cluster-02" "staging-cluster")

    local failed_count=0
    local total_count=${#CLUSTERS[@]}

    for cluster in "${CLUSTERS[@]}"; do
        if ! send_cluster_metrics "$cluster"; then
            ((failed_count++))
        fi
        sleep 2  # Brief pause between clusters
    done

    # Summary
    local success_count=$((total_count - failed_count))
    log "Monitoring completed: $success_count/$total_count clusters successful"

    # Exit with error if any failures
    if [ $failed_count -gt 0 ]; then
        exit 1
    fi
}

main "$@"
"""

    print("Custom monitoring script template:")
    print("=" * 40)
    print(monitoring_script)

    print("\nUsage:")
    print("1. Save as dangling_monitor.sh")
    print("2. chmod +x dangling_monitor.sh")
    print("3. Add to cron: 0 */4 * * * /path/to/dangling_monitor.sh")
    print("4. Monitor logs in /var/log/escmd/dangling_monitor.log")


def main():
    """Run all examples."""
    print("🚀 ESCMD Dangling Metrics Examples")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("This script demonstrates various ways to use the dangling metrics feature")
    print("for monitoring Elasticsearch cluster health with InfluxDB/VictoriaMetrics.")

    # Check if we're in the right directory
    if not os.path.exists("escmd.py"):
        print("\n❌ Error: escmd.py not found in current directory")
        print("Please run this script from the escmd directory.")
        return 1

    examples = [
        example_1_basic_metrics,
        example_2_environment_metrics,
        example_3_cleanup_metrics,
        example_4_cron_setup,
        example_5_grafana_queries,
        example_6_configuration_test,
        example_7_monitoring_script,
    ]

    try:
        for example in examples:
            example()
            input("\nPress Enter to continue to next example...")

        print_header("Summary")
        print("✅ All examples completed successfully!")
        print("\nNext steps:")
        print("1. Configure your metrics endpoint in escmd.yml")
        print("2. Test with --dry-run flag first")
        print("3. Set up automated monitoring with cron")
        print("4. Create Grafana dashboards for visualization")
        print("5. Set up alerts for critical thresholds")

        return 0

    except KeyboardInterrupt:
        print("\n\n👋 Examples interrupted by user")
        return 0
    except Exception as e:
        print(f"\n❌ Error running examples: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
