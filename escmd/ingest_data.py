#!/usr/bin/env python3
"""
ingest_data.py - Write random data into an Elasticsearch index.

Usage:
    python3 ingest_data.py                          # uses default cluster, prompts for index
    python3 ingest_data.py -i my-index              # specify index name
    python3 ingest_data.py -l prod -i my-index      # specify cluster + index
    python3 ingest_data.py -i my-index -n 500       # write 500 docs
    python3 ingest_data.py -i my-index --continuous # keep writing until Ctrl+C
"""

import argparse
import json
import random
import string
import sys
import time
import urllib3
import warnings
from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

from configuration_manager import ConfigurationManager
from esclient import ElasticsearchClient

# ---------------------------------------------------------------------------
# Random data generators
# ---------------------------------------------------------------------------

WORDS = [
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
    "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa",
    "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey",
    "xray", "yankee", "zulu",
]

STATUSES = ["active", "inactive", "pending", "error", "ok", "warning", "critical"]
REGIONS  = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"]
ENVS     = ["production", "staging", "development", "qa", "sandbox"]


def random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_sentence(word_count=6):
    return " ".join(random.choices(WORDS, k=word_count))


def make_document():
    """Generate a realistic-looking random document."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "@timestamp":   now,
        "message":      random_sentence(random.randint(4, 10)),
        "host":         f"host-{random_string(4)}.example.com",
        "service":      random.choice(WORDS),
        "status":       random.choice(STATUSES),
        "region":       random.choice(REGIONS),
        "environment":  random.choice(ENVS),
        "level":        random.choice(["INFO", "WARN", "ERROR", "DEBUG"]),
        "duration_ms":  round(random.uniform(1, 5000), 2),
        "bytes":        random.randint(100, 1_000_000),
        "count":        random.randint(1, 10_000),
        "score":        round(random.uniform(0, 1), 4),
        "tags":         random.sample(WORDS, k=random.randint(1, 4)),
        "user_id":      random.randint(1000, 9999),
        "session_id":   random_string(16),
        "request_id":   random_string(12),
        "metadata": {
            "version":  f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}",
            "build":    random_string(7),
            "flag":     random.choice([True, False]),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Ingest random documents into an Elasticsearch index.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("-l", "--location",  default=None,
                   help="Cluster name from elastic_servers.yml (default: current default)")
    p.add_argument("-i", "--index",     default=None,
                   help="Target index name (prompted if omitted)")
    p.add_argument("-n", "--count",     type=int, default=100,
                   help="Number of documents to write (default: 100)")
    p.add_argument("--batch-size",      type=int, default=50,
                   help="Docs per bulk request (default: 50)")
    p.add_argument("--continuous",      action="store_true",
                   help="Keep writing indefinitely until Ctrl+C")
    p.add_argument("--interval",        type=float, default=1.0,
                   help="Seconds between batches in continuous mode (default: 1.0)")
    p.add_argument("--dry-run",         action="store_true",
                   help="Print sample doc without writing anything")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Bulk helpers
# ---------------------------------------------------------------------------

def bulk_index(es_client, index_name, docs):
    """Send a bulk index request; returns (indexed, errors)."""
    body = []
    for doc in docs:
        body.append(json.dumps({"index": {"_index": index_name}}))
        body.append(json.dumps(doc))
    payload = "\n".join(body) + "\n"

    try:
        resp = es_client.es.bulk(body=payload, refresh=False)
        errors = [
            item["index"]["error"]
            for item in resp.get("items", [])
            if "error" in item.get("index", {})
        ]
        indexed = len(resp.get("items", [])) - len(errors)
        return indexed, errors
    except Exception as exc:
        return 0, [str(exc)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # ---- Config & connection ------------------------------------------------
    config = ConfigurationManager()

    # Resolve location: explicit arg > saved default > first server in config
    if args.location:
        location = args.location
    else:
        saved = config.get_default_cluster()
        # "default" is the fallback string when no state file exists — not a real cluster
        if saved and saved != "default" and config.get_server_config(saved):
            location = saved
        else:
            # Fall back to the first configured server
            if config.servers_dict:
                location = next(iter(config.servers_dict))
            else:
                print("[ERROR] No clusters configured. Check elastic_servers.yml.")
                sys.exit(1)

    # get_server_config_by_location resolves hostnames, credentials, SSL, etc.
    location_config = config.get_server_config_by_location(location)
    if not location_config:
        available = ", ".join(config.servers_dict.keys()) or "(none)"
        print(f"[ERROR] Unknown cluster: '{location}'.")
        print(f"        Available clusters: {available}")
        sys.exit(1)

    # ElasticsearchClient reads config.server_config for connection details
    config.server_config = location_config
    config.preprocess_indices = False  # skip full index scan on startup

    try:
        es_client = ElasticsearchClient(configuration_manager=config)
    except Exception as exc:
        print(f"[ERROR] Could not connect to '{location}': {exc}")
        sys.exit(1)

    # ---- Index name ---------------------------------------------------------
    index_name = args.index
    if not index_name:
        index_name = input("Index name to write into: ").strip()
    if not index_name:
        print("[ERROR] Index name is required.")
        sys.exit(1)

    # ---- Dry run ------------------------------------------------------------
    if args.dry_run:
        sample = make_document()
        print("\n[DRY RUN] Sample document that would be indexed:")
        print(json.dumps(sample, indent=2))
        print(f"\n  cluster : {location}")
        print(f"  index   : {index_name}")
        print(f"  count   : {args.count}")
        return

    # ---- Write loop ---------------------------------------------------------
    total_indexed = 0
    total_errors  = 0
    run = 0

    print(f"\nWriting to  : {index_name}  on  {location}")
    if args.continuous:
        print(f"Mode        : continuous  (Ctrl+C to stop, {args.interval}s between batches)")
    else:
        print(f"Mode        : {args.count} documents  (batch size {args.batch_size})")
    print()

    try:
        while True:
            run += 1
            batch_docs = [make_document() for _ in range(args.batch_size)]

            if not args.continuous:
                remaining = args.count - total_indexed
                if remaining <= 0:
                    break
                batch_docs = batch_docs[:remaining]

            indexed, errors = bulk_index(es_client, index_name, batch_docs)
            total_indexed += indexed
            total_errors  += len(errors)

            ts = datetime.now().strftime("%H:%M:%S")
            if errors:
                print(f"[{ts}]  batch {run:>4}  +{indexed} docs  ({len(errors)} errors)  total={total_indexed}")
                for e in errors[:3]:
                    print(f"         error: {e}")
            else:
                print(f"[{ts}]  batch {run:>4}  +{indexed} docs  total={total_indexed}")

            if not args.continuous and total_indexed >= args.count:
                break

            if args.continuous:
                time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\nStopped by user.")

    print(f"\nDone.  Indexed: {total_indexed}  Errors: {total_errors}  Index: {index_name}")


if __name__ == "__main__":
    main()
