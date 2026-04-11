# Introduction

## What is escmd?

**escmd** is a Python command-line tool for day-to-day **Elasticsearch** administration. It wraps cluster APIs with clearer output (tables, panels, dashboards), sensible defaults for operations work, and support for **multiple clusters** from one configuration file.

Typical uses:

- Health and capacity checks before and after changes
- Index and shard visibility (list, filter, dangling indices, replicas)
- **Index Lifecycle Management (ILM)** — policies, errors, attach/detach, backup/restore of policy definitions
- Snapshots and repositories
- Allocation and exclusion rules for maintenance windows
- Optional **automation** via named action sequences

## Interactive mode (ESTERM)

For repeated work in one session, **ESTERM** (`esterm.py` or the `esterm` wrapper) provides a persistent shell: connect once, run escmd commands without typing `./escmd.py` each time, with history and optional watch-style commands. See [05-esterm-and-output.md](05-esterm-and-output.md).

## What this manual covers

The following chapters walk through **installation**, **configuration**, **command usage**, and related topics in order. They are written so they can be merged into a single **PDF** (title page plus one section per chapter file).

## Version

The project version is carried in the main `README.md` at the repository root and in `escmd.py` at runtime (`version` / welcome output). Use `./escmd.py` with your environment’s help or version command to confirm what you have installed.

## Requirements in brief

- **Python** 3.6+ (newer Python is recommended)
- Network access to Elasticsearch HTTP APIs
- Dependencies listed in `requirements.txt` (for example `requests`, `rich`, `PyYAML`)

Details are in [02-installation.md](02-installation.md).
