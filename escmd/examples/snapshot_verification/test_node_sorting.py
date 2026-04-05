#!/usr/bin/env python3
"""
Test demonstration for alphabetical node sorting in repository verification.

This script simulates the node sorting behavior that occurs when displaying
repository verification results. It demonstrates how nodes are sorted
alphabetically by name for better readability.
"""

import json
from typing import Dict, Any


def simulate_elasticsearch_response() -> Dict[str, Any]:
    """
    Simulate an Elasticsearch repository verification response with nodes
    in random order (as they would come from the API).

    Returns:
        dict: Simulated verification response with nodes
    """
    return {
        "nodes": {
            "EEXhxdEhSs-36C0y1H_G0Q": {"name": "aex20-c01-ess12-1"},
            "Jgzt08o0RWOX6HsW-v0tFQ": {"name": "aex20-c01-ess18-1"},
            "8mvd0sJXTYWtdtQ4nfSpaQ": {"name": "aex20-c01-ess25-1"},
            "8sTkJNIeRWyeBbwX8mMxmg": {"name": "aex20-c01-ess14-1"},
            "43_VzERtQ4KpBAXCxF5z9g": {"name": "aex20-c01-ess15-1"},
            "cy-LSZlNR_yYxCu-r0WoYg": {"name": "aex20-c01-ess19-1"},
            "N0SvfNeZTBiYbq3xhX7jWw": {"name": "aex20-c01-ess13-1"},
            "mo_qkfqyRuOj4qCWx1z2GQ": {"name": "aex20-c01-esm02-master"},
            "43TgFWRQQCmDnQtbAULwzA": {"name": "aex20-c01-ess22-1"},
            "btM5JJhCR9SAdcN661tVig": {"name": "aex20-c01-ess20-1"},
            "laaYWjE1SJWa0UBBEkCjzA": {"name": "aex20-c01-esm03-master"},
            "ZLnV06agQWC37-ru8AMypw": {"name": "aex20-c01-ess21-1"},
            "B2Eo0qPCQkCX8QZwv0T-tg": {"name": "aex20-c01-ess11-1"},
            "rFMpDktVTpiyKjTpDQiatg": {"name": "aex20-c01-esm01-master"},
            "euZb4u3_QCySW_u-MqBfnA": {"name": "aex20-c01-ess17-1"},
            "I76thFwSSo-rIR-YbsX1oA": {"name": "aex20-c01-ess24-1"},
            "mZk-pT9ARee0-OQ-odEF-A": {"name": "aex20-c01-ess23-1"},
            "ZpHcr0e2RrSyft_rY25JMg": {"name": "aex20-c01-ess10-1"},
        }
    }


def demonstrate_original_order(verification_result: Dict[str, Any]) -> None:
    """
    Demonstrate the original order of nodes as returned by Elasticsearch.

    Args:
        verification_result: The verification response from Elasticsearch
    """
    print("Original Order (as returned by Elasticsearch API):")
    print("=" * 55)

    nodes = verification_result.get("nodes", {})

    for i, (node_id, node_info) in enumerate(nodes.items(), 1):
        node_name = node_info.get("name", "Unknown")
        print(f"{i:2d}. {node_name:<25} ({node_id[:8]}...)")

    print()


def demonstrate_sorted_order(verification_result: Dict[str, Any]) -> None:
    """
    Demonstrate the alphabetically sorted order of nodes.

    Args:
        verification_result: The verification response from Elasticsearch
    """
    print("Alphabetically Sorted Order (escmd display):")
    print("=" * 45)

    nodes = verification_result.get("nodes", {})

    # Sort nodes by name alphabetically (same logic as in escmd)
    sorted_nodes = sorted(
        nodes.items(), key=lambda item: item[1].get("name", "Unknown")
    )

    for i, (node_id, node_info) in enumerate(sorted_nodes, 1):
        node_name = node_info.get("name", "Unknown")
        print(f"{i:2d}. {node_name:<25} ({node_id[:8]}...)")

    print()


def demonstrate_table_format(verification_result: Dict[str, Any]) -> None:
    """
    Demonstrate how the sorted nodes would appear in table format.

    Args:
        verification_result: The verification response from Elasticsearch
    """
    print("Table Format Display (as shown in escmd):")
    print("=" * 42)
    print()
    print("┌────────────────────────┬────────────────────────┬────────────┐")
    print("│ Node Name              │ Node ID                │   Status   │")
    print("├────────────────────────┼────────────────────────┼────────────┤")

    nodes = verification_result.get("nodes", {})
    sorted_nodes = sorted(
        nodes.items(), key=lambda item: item[1].get("name", "Unknown")
    )

    for node_id, node_info in sorted_nodes:
        node_name = node_info.get("name", "Unknown")
        short_id = node_id[:22] if len(node_id) > 22 else node_id
        print(f"│ {node_name:<22} │ {short_id:<22} │ ✓ Verified │")

    print("└────────────────────────┴────────────────────────┴────────────┘")
    print()


def demonstrate_sorting_benefits() -> None:
    """Demonstrate the benefits of alphabetical sorting."""
    print("Benefits of Alphabetical Sorting:")
    print("=" * 33)
    print("✅ Easier to find specific nodes")
    print("✅ Consistent output across runs")
    print("✅ Better readability for large clusters")
    print("✅ Easier to spot missing nodes")
    print("✅ Natural grouping (masters, data nodes, etc.)")
    print()


def demonstrate_node_patterns() -> None:
    """Demonstrate common node naming patterns and how they sort."""
    print("Node Naming Patterns and Sorting:")
    print("=" * 34)

    patterns = [
        ("Master Nodes", ["esm01-master", "esm02-master", "esm03-master"]),
        ("Data Nodes", ["ess10-1", "ess11-1", "ess12-1", "ess13-1"]),
        ("Mixed Types", ["coord01", "data01", "master01", "ingest01"]),
    ]

    for pattern_name, nodes in patterns:
        print(f"\n{pattern_name}:")
        # Simulate unsorted input
        import random

        shuffled = nodes.copy()
        random.shuffle(shuffled)

        print(f"  Unsorted: {', '.join(shuffled)}")
        print(f"  Sorted:   {', '.join(sorted(nodes))}")


def main():
    """Main demonstration function."""
    print("Repository Verification Node Sorting Demonstration")
    print("=" * 54)
    print("This script demonstrates how escmd sorts nodes alphabetically")
    print("for better readability in verification results.\n")

    # Get simulated response
    verification_result = simulate_elasticsearch_response()

    print(f"Cluster: aex20 (Total Nodes: {len(verification_result['nodes'])})")
    print()

    # Demonstrate original vs sorted order
    demonstrate_original_order(verification_result)
    demonstrate_sorted_order(verification_result)

    # Show table format
    demonstrate_table_format(verification_result)

    # Show benefits and patterns
    demonstrate_sorting_benefits()
    demonstrate_node_patterns()

    print("\nUsage in escmd:")
    print("./escmd.py -l aex20 repositories verify aex20-repo")
    print("\nThe output will show nodes sorted alphabetically by name,")
    print("making it easier to verify all expected nodes are present.")


if __name__ == "__main__":
    main()
