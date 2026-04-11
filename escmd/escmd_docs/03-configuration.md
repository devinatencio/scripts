# Configuration

escmd reads **YAML** from the working directory (the folder you run `escmd.py` from, or the project root in normal use).

## Primary files

| File | Role |
|------|------|
| `elastic_servers.yml` | Cluster definitions: hostnames, ports, TLS, auth, optional per-server overrides |
| `escmd.yml` | Optional second file: global settings, **cluster_groups**, **passwords** map (dual-file mode) |

## Single-file mode (legacy)

If **only** `elastic_servers.yml` exists, put both `settings:` and `servers:` in that file. This matches older deployments.

## Dual-file mode (recommended)

If **`escmd.yml` exists**, escmd uses **dual-file mode**:

- **`escmd.yml`**: application settings, `cluster_groups`, centralized `passwords` by environment (and optional usernames)
- **`elastic_servers.yml`**: `servers:` entries only; servers can reference an `env` key that ties into `passwords`

Benefits: separate connection facts from secrets and grouping; easier rotation and reviews.

## Minimal `elastic_servers.yml`

```yaml
servers:
  - name: local
    hostname: localhost
    port: 9200
    use_ssl: false
    verify_certs: false
    elastic_authentication: false
```

## Typical production fields

Per server (non-exhaustive):

- `name` — logical label; used with `-l` / `--locations`
- `hostname`, optional `hostname2` — primary and fallback API host
- `port` — usually `9200`
- `use_ssl`, `verify_certs` — HTTPS and certificate validation
- `elastic_authentication`, `elastic_username`, `elastic_password` — basic auth
- `auth_profile` — optional name of an entry under `auth_profiles:` in `escmd.yml` (or single-file config) so shared server lists need not embed usernames; see **Auth profiles** below
- `env` — environment key for dual-file password lookup
- `elastic_s3snapshot_repo` — default snapshot repository name when relevant

Global **`settings:`** (in either `elastic_servers.yml` or `escmd.yml`) control display and behavior, for example:

- `health_style` — `dashboard` or `classic`
- `box_style`, `classic_style` — panel and table styling
- `enable_paging`, `paging_threshold` — when to pipe long output through a pager
- `ascii_mode` — ASCII-only output for constrained terminals
- `connection_timeout`, `read_timeout` — HTTP timeouts
- `dangling_cleanup` — defaults for dangling-index workflows (retries, confirmations, logging)

A fuller option list and examples live in the repository under `docs/configuration/cluster-setup.md`.

## Choosing a cluster on the CLI

- **`-l NAME`** or **`--locations NAME`** — target the server entry whose `name` matches (case per your config).
- Default location behavior is described in the built-in help if no `-l` is given.

## Auth profiles

Use **auth profiles** when most clusters share a default username but some need a different *kind* of account (e.g. service user vs human user), and you want a **portable** `elastic_servers.yml` that everyone can share without editing per-user usernames.

1. In **`escmd.yml`** (recommended) or in single-file YAML, define named profiles:

```yaml
settings:
  elastic_username: kibana_system

auth_profiles:
  kibana_service:
    elastic_username: kibana_system
  human_operator:
    elastic_username: alice.example
```

2. On each server in **`elastic_servers.yml`**, either omit username (inherit `settings.elastic_username`) or set only a profile:

```yaml
servers:
  - name: prod-metrics
    hostname: es-prod.example.com
    env: prod
    elastic_authentication: true
    auth_profile: kibana_service

  - name: lab-adhoc
    hostname: es-lab.example.com
    env: lab
    elastic_authentication: true
    auth_profile: human_operator
```

**Resolution order** for the effective username: per-server `elastic_username` (if set) → `auth_profiles[auth_profile].elastic_username` → (special case) single-user `passwords[env]` → `escmd.json` → `settings.elastic_username`.

Each user or team maps profile names to real usernames in their own `escmd.yml`; shared inventory only references stable profile names.

Longer reference (examples, troubleshooting, password interaction): **`docs/configuration/dual-file-config-guide.md`** (Auth profiles), **`docs/configuration/cluster-setup.md`**, **`docs/configuration/password-management.md`**, **`docs/reference/troubleshooting.md`**, and **`docs/reference/changelog.md`** (v3.8.5).

## Password management

escmd supports:

- Inline passwords in YAML (simple, least ideal for shared repos)
- Environment-based resolution (`use_env_password`, `env`)
- **Encrypted storage** via `store-password`, `list-stored-passwords`, `remove-stored-password`, plus session cache commands (`session-info`, `clear-session`, `set-session-timeout`, `generate-master-key`, `migrate-key`)

Resolution order favors explicit references, then stored secrets, then traditional fields. Full behavior and examples are in `docs/configuration/password-management.md`.

## Themes

Global settings may reference **`themes_file`** (for example `themes.yml`) for color and style packs used by rich output and ESTERM. See [05-esterm-and-output.md](05-esterm-and-output.md) and `docs/themes/` in the repo.

## Validate configuration

```bash
./escmd.py show-settings
./escmd.py locations
./escmd.py ping
```

## Security practices

- Restrict file permissions on YAML that contains passwords.
- Prefer encrypted `store-password` + `ESCMD_MASTER_KEY` (or your org’s secret store) over committing secrets.
- Use read-only Elasticsearch users where possible for monitoring commands.
