# Command reference

Examples use `./escmd.py`. Substitute `python3 escmd.py` on your system. Add **`-l CLUSTER`** (or **`--locations`**) before the subcommand when you are not using the default cluster.

Many commands accept **`--format json`** or **`--format table`** (some allow **`data`** for machine-oriented tables). Omitted below unless the choices differ.

---

## help

Themed documentation for major topics.

```bash
./escmd.py help
./escmd.py help ilm
./escmd.py help indices
./escmd.py help actions
```

Topics include: `indices`, `indices-analyze`, `indices-s3-estimate`, `indices-watch-collect`, `indices-watch-report`, `ilm`, `health`, `nodes`, `allocation`, `snapshots`, `repositories`, `dangling`, `shards`, `exclude`, `security`, `freeze`, `unfreeze`, `indice-add-metadata`, `templates`, `template-modify`, `actions`, `action`.

---

## Cluster visibility and health

### ping

Test HTTP connectivity to the configured cluster.

```bash
./escmd.py ping
./escmd.py -l production ping --format json
```

### health

Compact health summary.

```bash
./escmd.py health
./escmd.py health --format json
./escmd.py health --group production
```

### health-detail

Full dashboard or classic layout; optional compare and group modes.

```bash
./escmd.py health-detail
./escmd.py health-detail --style classic --classic-style panel
./escmd.py health-detail --compare staging
./escmd.py health-detail --group production
```

### current-master

```bash
./escmd.py current-master
./escmd.py current-master --format json
```

### masters

```bash
./escmd.py masters
./escmd.py masters --format json
```

### nodes

```bash
./escmd.py nodes
./escmd.py nodes --format data
./escmd.py nodes --format json
```

### cluster-check

Deep checks; optional replica repair and ILM tuning.

```bash
./escmd.py cluster-check
./escmd.py cluster-check --show-details
./escmd.py cluster-check --skip-ilm
./escmd.py cluster-check --fix-replicas 1 --dry-run
./escmd.py cluster-check --fix-replicas 1 --force
./escmd.py cluster-check --max-shard-size 80 --ilm-limit 100
```

---

## Indices

### indices

List or delete indices. Optional regex filter.

```bash
./escmd.py indices
./escmd.py indices "logs-*"
./escmd.py indices --status red
./escmd.py indices --cold
./escmd.py indices --pager
./escmd.py indices "temp-*" --delete
./escmd.py indices "temp-*" --delete -y
```

### indices-analyze

Find backing indices that diverge from peer medians (size/docs).

```bash
./escmd.py indices-analyze
./escmd.py indices-analyze "metrics-*" --status green
./escmd.py indices-analyze --min-ratio 3 --min-docs 500000 --top 20
./escmd.py indices-analyze --within-days 7 --pager
```

### indices-s3-estimate

Estimate monthly object-storage cost from primary sizes (requires price).

```bash
./escmd.py indices-s3-estimate --price-per-gib-month 0.023
./escmd.py indices-s3-estimate "logs-*" --within-days 14 --price-per-gib-month 0.023 --buffer-percent 10
./escmd.py indices-s3-estimate --price-per-gib-month 0.023 --include-undated
```

### indices-watch-collect

Samples `_cat`/index stats on an interval; writes JSON under `~/.escmd/index-watch/` (or `ESCMD_INDEX_WATCH_DIR`).

```bash
./escmd.py indices-watch-collect
./escmd.py indices-watch-collect "hot-*" --interval 30 --duration 3600
./escmd.py indices-watch-collect --output-dir /var/tmp/escmd-watch --retries 5
```

### indices-watch-report

Summarizes JSON samples from **`indices-watch-collect`** without connecting to Elasticsearch when using the default **`~/.escmd/index-watch/...`** path. Compares **first ↔ last** snapshot for **Δ docs** and **span docs/s**; with **≥3** samples and default **`--rate-stats auto`**, the table also shows **med/s**, **p90/s**, **max/s** (per adjacent interval) and **span/s**. **`--rate-stats span`** keeps a single **docs/s** column; **`--rate-stats intervals`** always uses interval columns + **span/s** (≥2 samples). **HOT** / **rate/med** use span rates vs rollover-series peers (same idea as **`indices-analyze`**); the **rate/med** column is hidden when no row has a valid peer ratio. JSON always includes **`docs_per_sec`** (span) and, when ≥2 samples, **`docs_per_sec_interval_*`** and **`interval_rate_count`**, plus summary **`interval_count`**, **`rate_stats`**, **`rate_stats_primary`**.

```bash
./escmd.py indices-watch-report
./escmd.py indices-watch-report --date 2026-04-01 --format json
./escmd.py indices-watch-report --dir ~/.escmd/index-watch/mycluster/2026-04-06 --top 15
./escmd.py indices-watch-report --rate-stats span
./escmd.py indices-watch-report --rate-stats intervals --format json
```

| Flag | Role |
|------|------|
| `--dir` | Explicit sample directory |
| `--cluster` | Slug for default path without **`-l`** |
| `--date` | UTC date folder **`YYYY-MM-DD`** |
| `--format` | **`table`** or **`json`** |
| `--min-docs-delta` | Floor on doc increase; zero-Δ indices omitted |
| `--hot-ratio` / `--min-peers` / `--docs-peer-ratio` | Peer comparison thresholds (see **`help indices-watch-report`**) |
| `--top` | Cap rows after sort |
| `--rate-stats` | **`auto`** \| **`span`** \| **`intervals`** |

### indice

Details for a single index (name optional in parser).

```bash
./escmd.py indice
./escmd.py indice my-index-000001
```

### indice-add-metadata

```bash
./escmd.py indice-add-metadata my-index '{"team":"search"}'
```

### create-index

```bash
./escmd.py create-index new-index -s 3 -r 1
./escmd.py create-index new-index --settings '{"index":{"number_of_shards":1}}' --mappings '{"properties":{"@timestamp":{"type":"date"}}}'
```

### recovery

```bash
./escmd.py recovery
./escmd.py recovery --format json
```

### datastreams

List all data streams, or show one; optional delete.

```bash
./escmd.py datastreams
./escmd.py datastreams logs-esdb
./escmd.py datastreams logs-esdb --delete
```

### dangling

List or remove dangling indices. Prefer **`--dry-run`** first.

```bash
./escmd.py dangling
./escmd.py dangling --cleanup-all --dry-run
./escmd.py dangling --cleanup-all --batch 50
./escmd.py dangling <uuid> --delete
./escmd.py dangling --group production
./escmd.py dangling --env prod --metrics
```

### freeze / unfreeze

```bash
./escmd.py freeze my-index -e
./escmd.py freeze '^logs-.*' -r
./escmd.py unfreeze my-index -y
```

### flush

Cluster flush (no extra arguments in the CLI).

```bash
./escmd.py flush
```

### exclude (index routing)

Exclude an index from a node pattern (legacy index-level helper).

```bash
./escmd.py exclude my-index --server ess01
```

### exclude-reset

Clear index-level exclude settings for an index.

```bash
./escmd.py exclude-reset my-index
```

### rollover

```bash
./escmd.py rollover logs-datastream
./escmd.py rollover --format json
```

### auto-rollover

```bash
./escmd.py auto-rollover
./escmd.py auto-rollover 'ess.*'
```

---

## Shards, colocation, storage

### shards

```bash
./escmd.py shards
./escmd.py shards 'logs-*' -s ess46 -n 50
./escmd.py shards --size --pager
```

### shard-colocation

Indices where primary and replica sit on the same host.

```bash
./escmd.py shard-colocation
./escmd.py shard-colocation 'large-*' --format json
```

### storage

Disk usage view.

```bash
./escmd.py storage
./escmd.py storage --format json
```

---

## Cluster settings

### cluster-settings

```bash
./escmd.py cluster-settings
./escmd.py cluster-settings show --format json
```

### set

Dot-notation cluster settings (`transient` or `persistent`). Use **`null`** to clear.

```bash
./escmd.py set transient cluster.routing.allocation.enable all
./escmd.py set persistent cluster.routing.allocation.disk.threshold_enabled false --dry-run
./escmd.py set persistent some.setting.key null --yes
```

---

## Templates

### templates

```bash
./escmd.py templates
./escmd.py templates --type composable --pager
```

### template

```bash
./escmd.py template my-template
./escmd.py template my-template --type legacy
```

### template-usage

```bash
./escmd.py template-usage
./escmd.py template-usage --format json --pager
```

### template-modify

```bash
./escmd.py template-modify my-tmpl -f template.settings.index.routing.allocation.exclude._name -o append -v "rack-a-*"
./escmd.py template-modify my-tmpl -f index.lifecycle.name -o set -v my-policy --dry-run
./escmd.py template-modify my-tmpl -f some.field -o delete --no-backup
```

### template-backup / template-restore / list-backups

```bash
./escmd.py template-backup my-template --cluster production
./escmd.py list-backups --name my-template
./escmd.py template-restore --backup-file /path/to/backup.json
```

### template-create

From file or inline name + definition.

```bash
./escmd.py template-create -f templates.json
./escmd.py template-create -n my-component -t component -d '{"template":{"settings":{}}}' --dry-run
```

---

## Allocation (cluster routing)

Parent command requires a subcommand.

```bash
./escmd.py allocation enable
./escmd.py allocation disable --format json
./escmd.py allocation exclude add ess46-data-01
./escmd.py allocation exclude remove ess46-data-01
./escmd.py allocation exclude reset
./escmd.py allocation exclude reset --yes-i-really-mean-it
./escmd.py allocation explain my-index --shard 2 --primary
```

---

## Repositories

```bash
./escmd.py repositories list
./escmd.py repositories verify my-fs-repo
./escmd.py repositories create my-s3 --type s3 --bucket my-bucket --base-path snapshots --region us-east-1 --dry-run
./escmd.py repositories create my-fs --type fs --location /mnt/es-snapshots --force
```

---

## Snapshots

```bash
./escmd.py snapshots list
./escmd.py snapshots list '^nightly-.*' --mode slow --pager
./escmd.py snapshots status snap-20260406 --repository my-repo
./escmd.py snapshots info snap-20260406
./escmd.py snapshots create 'logs-*' --repository my-repo --wait
./escmd.py snapshots create my-datastream --type datastream --dry-run
./escmd.py snapshots delete old-snap --repository my-repo --force
./escmd.py snapshots list-restored
./escmd.py snapshots clear-staged --force
./escmd.py snapshots repositories
```

---

## ILM (`ilm`)

```bash
./escmd.py ilm status
./escmd.py ilm policies
./escmd.py ilm errors
./escmd.py ilm policy my-policy
./escmd.py ilm policy my-policy --show-all
./escmd.py ilm explain my-index-000042
./escmd.py ilm remove-policy 'temp-*' --dry-run
./escmd.py ilm remove-policy --file indices.txt --yes
./escmd.py ilm set-policy nightly-policy '^logs-.*'
./escmd.py ilm set-policy new-policy --from-policy old-policy --dry-run
./escmd.py ilm create-policy roll-monthly policy.json
./escmd.py ilm create-policy roll-monthly --file ./policy.json
./escmd.py ilm delete-policy old-policy --yes
./escmd.py ilm index-patterns my-policy --show-all
./escmd.py ilm backup-policies --input-file indices.txt --output-file policies-backup.json
./escmd.py ilm restore-policies --input-file policies-backup.json --dry-run
```

---

## Replicas

```bash
./escmd.py set-replicas --pattern "critical-*" --count 2
./escmd.py set-replicas --indices idx1,idx2 --count 1 --dry-run
./escmd.py set-replicas --no-replicas-only --force
```

---

## Utilities and configuration

```bash
./escmd.py locations
./escmd.py get-default
./escmd.py version
./escmd.py themes
./escmd.py cluster-groups
./escmd.py cluster-groups --format json
./escmd.py show-settings
./escmd.py show-settings --format json
./escmd.py set-default production
./escmd.py set-username kibana_system
./escmd.py set-username clear
./escmd.py set-theme ocean --preview
./escmd.py set-theme ocean --no-confirm
```

---

## Passwords and session cache

```bash
./escmd.py store-password
./escmd.py store-password prod --username kibana_system
./escmd.py list-stored-passwords
./escmd.py list-stored-passwords --decrypt
./escmd.py remove-stored-password lab
./escmd.py clear-session
./escmd.py session-info
./escmd.py set-session-timeout 120
./escmd.py generate-master-key --show-setup
./escmd.py migrate-to-env-key
./escmd.py migrate-to-env-key --force
```

---

## action (workflow sequences)

```bash
./escmd.py action list
./escmd.py action show health-check
./escmd.py action run health-check --dry-run
./escmd.py action run nightly-check --quiet --yes
./escmd.py action run my-action --param-index-pattern 'logs-*' --param-days 7
```

Dynamic **`--param-*`** flags depend on the action definition; use **`action show`** for the exact parameters your installation exposes.

---

## Quick command index (alphabetical)

| Command | Purpose (short) |
|---------|------------------|
| `action` | List, show, or run named workflows |
| `allocation` | Enable/disable allocation; exclude nodes; explain shard |
| `auto-rollover` | Rollover largest shard on matching nodes |
| `cluster-check` | Deep health and optional replica fixes |
| `cluster-groups` | Show configured groups |
| `cluster-settings` | Display cluster settings |
| `create-index` | Create an empty index |
| `clear-session` | Clear cached decrypted passwords |
| `current-master` | Show elected master |
| `datastreams` | List or detail data streams; delete |
| `dangling` | Dangling index report and cleanup |
| `exclude` / `exclude-reset` | Index-level exclude helpers |
| `flush` | Flush indices |
| `freeze` / `unfreeze` | Freeze or unfreeze indices |
| `generate-master-key` | Emit/setup `ESCMD_MASTER_KEY` material |
| `get-default` | Show default cluster name |
| `health` / `health-detail` | Cluster health summaries |
| `help` | Topic help |
| `ilm` | ILM status, policies, attach/detach, backup/restore policies |
| `indices` | List/delete indices |
| `indices-analyze` | Backing-index outlier analysis |
| `indices-s3-estimate` | S3 cost estimate from sizes |
| `indices-watch-collect` / `indices-watch-report` | Sample `_cat` stats to JSON; offline report (span + optional interval med/p90/max docs/s) |
| `indice` | Single index detail |
| `indice-add-metadata` | Attach metadata JSON to an index |
| `list-backups` | List template backups |
| `list-stored-passwords` | List password store entries |
| `locations` | List configured clusters |
| `masters` | Master-eligible nodes |
| `migrate-to-env-key` | Move master key to environment variable |
| `nodes` | Data node listing |
| `ping` | Connectivity check |
| `recovery` | Recovery tasks |
| `repositories` | List, create, verify snapshot repos |
| `remove-stored-password` | Remove one stored environment |
| `rollover` / `auto-rollover` | Data stream rollover helpers |
| `session-info` | Session cache status |
| `set` | Set transient/persistent cluster settings |
| `set-default` | Default cluster selection |
| `set-replicas` | Bulk replica count changes |
| `set-session-timeout` | Session cache TTL |
| `set-theme` | Active Rich theme |
| `set-username` | Default ES username in config |
| `shards` / `shard-colocation` | Shard listing and risk report |
| `show-settings` | Local escmd YAML settings |
| `snapshots` | Snapshot list/create/delete/status and helpers |
| `storage` | Disk usage |
| `store-password` | Encrypt and store a password |
| `template` / `templates` / `template-usage` | Template inspection |
| `template-backup` / `template-restore` / `template-modify` / `template-create` | Template lifecycle |
| `themes` | Preview installed themes |
| `version` | escmd version |

For behavior beyond these examples, run **`./escmd.py help <topic>`** or the subcommand’s **`--help`** where argparse exposes it.
