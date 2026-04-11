# Release Notes: ESCMD Version 3.8.5

**Release Date**: April 7, 2026
**Version**: 3.8.5
**Type**: Feature Release

---

## Overview

Version 3.8.5 adds **auth profiles**: named authentication presets in **`escmd.yml`** (or single-file YAML) that servers can reference with **`auth_profile`**, so shared **`elastic_servers.yml`** files stay portable without embedding per-user usernames.

---

## New configuration

| Item | Location | Purpose |
|------|----------|---------|
| **`auth_profiles`** | Top-level in **`escmd.yml`** (dual-file) or same file as **`servers:`** (single-file) | Maps profile names to **`elastic_username`** (extensible later) |
| **`auth_profile`** | Per-server in **`elastic_servers.yml`** | Selects a profile when **`elastic_username`** is not set on that server |

**Dual-file:** **`auth_profiles`** are read only from the **main** config, not from **`elastic_servers.yml`**.

**Username resolution order:** server **`elastic_username`** → profile **`elastic_username`** → single-key **`passwords[env]`** shortcut → **`escmd.json`** → **`settings.elastic_username`**.

Unknown profile names log a warning and resolution continues.

---

## Documentation

- **`docs/reference/changelog.md`** — full entry
- **`docs/configuration/dual-file-config-guide.md`** — Auth profiles section
- **`docs/configuration/cluster-setup.md`**, **`password-management.md`**, **`installation.md`**
- **`docs/reference/troubleshooting.md`**, **`docs/commands/snapshot-management.md`**
- **`docs/README.md`**, **`escmd_docs/03-configuration.md`**

---

## Code and tests

- **`configuration_manager.py`**, **`display/locations_data.py`**, **`display/settings_data.py`**
- **`tests/unit/test_configuration.py`**
