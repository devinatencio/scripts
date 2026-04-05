#!/usr/bin/env python3
"""
sanitize_docs.py — Replace sensitive/work-specific strings in documentation files.

Usage:
    python sanitize_docs.py [--config CONFIG] [--dry-run] [--verbose]

Options:
    --config CONFIG   Path to YAML config file (default: sanitize_config.yml)
    --dry-run         Show what would change without writing files
    --verbose         Print every replacement made
"""

import argparse
import re
import sys
from pathlib import Path
from collections import OrderedDict

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install it with: pip install pyyaml")
    sys.exit(1)


def build_ip_prefix_pattern(source_prefix: str) -> re.Pattern:
    """Build a regex that matches IPs starting with source_prefix."""
    escaped = re.escape(source_prefix)
    # Match the prefix followed by up to 3 more octet groups
    return re.compile(r"\b" + escaped + r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")


def apply_ip_prefix_rule(text: str, rule: dict) -> tuple[str, int]:
    """Replace IPs matching source_prefix with target_prefix, preserving the last octet."""
    source_prefix = rule["source_prefix"]
    target_prefix = rule["target_prefix"]
    pattern = build_ip_prefix_pattern(source_prefix)

    count = 0

    def replacer(m: re.Match) -> str:
        nonlocal count
        count += 1
        last_octet = m.group(3)
        return f"{target_prefix}{last_octet}"

    result = pattern.sub(replacer, text)
    return result, count


def apply_literal_rule(text: str, rule: dict) -> tuple[str, int]:
    find = rule["find"]
    replace = rule["replace"]
    count = text.count(find)
    return text.replace(find, replace), count


def apply_regex_rule(text: str, rule: dict) -> tuple[str, int]:
    pattern = re.compile(rule["pattern"])
    result, count = pattern.subn(rule["replace"], text)
    return result, count


# Shared hostname registry — persists across all files so the same hostname
# always maps to the same serverN label throughout the entire run.
_hostname_registry: OrderedDict[str, str] = OrderedDict()


def build_hostname_pattern(prefixes: list[str]) -> re.Pattern:
    """
    Build a regex that matches hostnames like:
      <site><nn>[-c<nn>[-ess<nn>[-<n>]]]
    e.g.  iad41  iad41-c01  aex10-c01-ess77-1
    Only matches site codes listed in `prefixes`.
    Longest match wins because alternation is ordered longest-first.
    """
    # Sort longest first so e.g. "aex10-c01-ess77-1" is matched before "aex10"
    sorted_pfx = sorted(prefixes, key=len, reverse=True)
    pfx_alt = "|".join(re.escape(p) for p in sorted_pfx)
    return re.compile(
        r"\b(?:" + pfx_alt + r")[0-9]{1,4}"
        r"(?:-c[0-9]{2}(?:-ess[0-9]+-[0-9]+|-ess[0-9]+)?)?"
        r"\b",
        re.IGNORECASE,
    )


def apply_hostname_rule(text: str, rule: dict) -> tuple[str, int]:
    """
    Replace internal hostnames with generic server1, server2, … labels.
    The mapping is stable across files (same hostname → same label always).
    """
    prefixes = rule.get("prefixes", [])
    label_prefix = rule.get("label_prefix", "server")
    if not prefixes:
        return text, 0

    pattern = build_hostname_pattern(prefixes)
    count = 0

    def replacer(m: re.Match) -> str:
        nonlocal count
        hostname = m.group(0).lower()
        if hostname not in _hostname_registry:
            idx = len(_hostname_registry) + 1
            _hostname_registry[hostname] = f"{label_prefix}{idx}"
        count += 1
        return _hostname_registry[hostname]

    result = pattern.sub(replacer, text)
    return result, count


def sanitize_text(text: str, rules: list[dict], verbose: bool = False, filepath: str = "") -> tuple[str, int]:
    total = 0
    for rule in rules:
        rtype = rule.get("type")
        if rtype == "literal":
            text, n = apply_literal_rule(text, rule)
        elif rtype == "regex":
            text, n = apply_regex_rule(text, rule)
        elif rtype == "ip_prefix":
            text, n = apply_ip_prefix_rule(text, rule)
        elif rtype == "hostname":
            text, n = apply_hostname_rule(text, rule)
        else:
            print(f"  WARNING: Unknown rule type '{rtype}', skipping.")
            n = 0

        if n and verbose:
            label = rule.get("find") or rule.get("pattern") or rule.get("source_prefix") or rule.get("type")
            print(f"  [{filepath}] rule '{rtype}:{label}' → {n} replacement(s)")
        total += n
    return text, total


def main():
    parser = argparse.ArgumentParser(description="Sanitize sensitive strings from documentation files.")
    parser.add_argument("--config", default="sanitize_config.yml", help="Path to YAML config file")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--verbose", action="store_true", help="Show each replacement")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    with config_path.open() as f:
        config = yaml.safe_load(f)

    rules = config.get("rules", [])
    files = config.get("files", [])

    if not rules:
        print("No rules defined in config. Nothing to do.")
        sys.exit(0)

    if not files:
        print("No files listed in config. Nothing to do.")
        sys.exit(0)

    print(f"Sanitization config: {config_path}")
    print(f"Rules loaded: {len(rules)}")
    print(f"Files to process: {len(files)}")
    if args.dry_run:
        print("DRY RUN — no files will be modified.\n")
    else:
        print()

    grand_total = 0
    missing = []

    for filepath in files:
        p = Path(filepath)
        if not p.exists():
            missing.append(filepath)
            print(f"  SKIP (not found): {filepath}")
            continue

        original = p.read_text(encoding="utf-8")
        sanitized, count = sanitize_text(original, rules, verbose=args.verbose, filepath=filepath)

        if count == 0:
            print(f"  OK (no changes):  {filepath}")
        elif args.dry_run:
            print(f"  WOULD CHANGE ({count} replacement(s)): {filepath}")
        else:
            p.write_text(sanitized, encoding="utf-8")
            print(f"  UPDATED ({count} replacement(s)): {filepath}")

        grand_total += count

    print()
    if args.dry_run:
        print(f"Dry run complete. {grand_total} replacement(s) would be made across {len(files) - len(missing)} file(s).")
    else:
        print(f"Done. {grand_total} replacement(s) made across {len(files) - len(missing)} file(s).")

    if missing:
        print(f"WARNING: {len(missing)} file(s) not found: {', '.join(missing)}")

    if _hostname_registry:
        print("\nHostname mapping applied:")
        for original, replacement in _hostname_registry.items():
            print(f"  {original:40s} → {replacement}")


if __name__ == "__main__":
    main()
