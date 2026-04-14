## [3.11.0] - 2026-04-13

### `indices-watch-collect` / `indices-watch-report` — multi-session support per day

Adds a **session layer** beneath the existing date directory so multiple distinct collection runs on the same day for the same cluster are stored separately and never mixed together.

#### New directory layout

```
~/.escmd/index-watch/<cluster>/<YYYY-MM-DD>/<session_id>/
    run.json                        ← schema_version: 2 (new)
    20260413T143000_0001.json
    20260413T143100_0002.json
    ...
```

Session IDs are derived from the UTC start time (`HHMM`) with an optional user-supplied label (`1430-load-test`). Collisions are resolved automatically by appending `-2`, `-3`, etc.

#### `indices-watch-collect` changes

- **NEW**: **Interactive session picker** — on startup, when sessions already exist for the current cluster and date, a numbered list is shown and the user can join an existing session or create a new one. Non-interactive environments (non-TTY) automatically start a new session and log a notice to stderr.
- **NEW**: **`--new-session`** — skip the picker and always create a fresh session directory.
- **NEW**: **`--join-latest`** — skip the picker and automatically join the most recently started session (creates a new one if none exist).
- **NEW**: **`--label LABEL`** — append a human-readable label to the session ID (e.g. `--label load-test` → `1430-load-test`).
- **Behavior**: When joining an existing session, the original `run.json` is preserved and the sequence counter picks up from the last sample already in the directory (no more `_0001.json` restarts).
- **Behavior**: `--output-dir` bypasses all session logic and writes directly to the specified path (unchanged behavior).

#### `top` / `es-top --collect` changes

- **NEW**: Same `--new-session`, `--join-latest`, and `--label` flags accepted by `es-top` / `top` when `--collect` is active. No effect when `--collect` is not set.
- **Behavior**: When `--collect-dir` is given, the existing direct-path behavior is preserved with no session logic.

#### `indices-watch-report` changes

- **NEW**: **Interactive session picker** — when multiple sessions exist for the resolved cluster and date and no `--dir` or `--session` flag is given, a numbered list is shown and the user selects which session to report on. Non-interactive environments auto-select the most recent session and log a notice to stderr.
- **NEW**: **`--session SESSION_ID`** — load from the named session directly without prompting.
- **NEW**: **`--list-sessions`** — print available sessions (ID, start time, sample count, label) and exit without generating a report.
- **Behavior**: Exactly one session → loaded silently, no prompt. Legacy flat date directories (no session subdirs) → loaded directly, full backward compatibility.
- **Behavior**: `--session <id>` not found → prints an error listing available sessions and exits non-zero.

#### Backward compatibility

- Legacy flat `<YYYY-MM-DD>/` directories (schema_version 1) continue to work without any migration. The session picker offers a "continue appending to legacy directory" option when flat files are detected.
- `default_run_dir()` is unchanged. All session resolution flows through the new `resolve_session_dir()` / `pick_or_create_session_dir()` helpers.
- `run.json` schema_version 1 files are still parsed and reported correctly.

- **Code**: `processors/indices_watch.py` (`sanitize_session_label`, `make_session_id`, `resolve_session_dir`, `SessionInfo`, `list_sessions`, `is_legacy_date_dir`, `format_session_list`, `pick_or_create_session_dir`, updated `write_run_metadata`, updated `run_indices_watch_report`), `handlers/index_handler.py` (`handle_indices_watch_collect`), `commands/estop_commands.py` (`EsTopDashboard.__init__`), `handlers/estop_handler.py`, `cli/argument_parser.py`.
- **Tests**: `tests/unit/processors/test_indices_watch.py` (24 new session unit tests, 35 total passing).

---

## [3.10.1] - 2026-04-13

### `top` / `es-top` — `--collect` flag for post-session analysis


- **NEW**: **`--collect`** flag on `top` / `es-top` — writes a JSON index-stats snapshot to disk on every poll cycle, using the same file format and directory layout as `indices-watch-collect` (`~/.escmd/index-watch/<cluster>/<UTC-date>/`). When you exit `top`, run `indices-watch-report` against the saved directory to analyze ingest rates, HOT indices, and peer comparisons without an Elasticsearch connection.
- **NEW**: **`--collect-dir PATH`** — override the output directory when `--collect` is active (default: `~/.escmd/index-watch/<cluster>/<UTC-date>/`).
- **Behavior**: A `run.json` metadata file is written at startup (same schema as `indices-watch-collect`). Each poll cycle that returns valid `cat_indices` data saves a timestamped sample file (`YYYYMMDDTHHMMSS_NNNN.json`). Failed poll cycles are skipped silently (no partial files written).
- **Code**: `commands/estop_commands.py` (`EsTopDashboard.__init__`, `_poll_loop`), `handlers/estop_handler.py`, `cli/argument_parser.py`, `handlers/help/estop_help.py`.

---

## [3.10.0] - 2026-04-11

### `es-top` — live Elasticsearch cluster dashboard

- **NEW**: **`./escmd.py es-top`** — full-screen, auto-refreshing terminal dashboard modelled after the Unix `top` command. Uses `rich.live.Live` in alternate-screen mode (clears terminal on start, restores on exit). Exit with **Ctrl+C**.
- **NEW**: **Cluster Health Header** — cluster name, status (color-coded green/yellow/red), total/data node counts, active/relocating/initializing/unassigned shard counts. Unassigned shards render in red. Last-poll timestamp and refresh interval shown in the footer.
- **NEW**: **Top Nodes panel** — top N nodes ranked by JVM heap %. Columns: node name, heap %, CPU %, 1-min load average, disk used %, disk free. Heap ≥ 85% → red bold; disk ≥ 85% → yellow, ≥ 90% → red bold.
- **NEW**: **Index Hot List panel** — top N active indices ranked by docs/sec. Columns: index name, docs/sec, searches/sec, session total docs written, session total searches, total doc count, store size. Only indices with activity since `es-top` started are shown. First-poll cycle shows totals only with a note that rates are available after the next poll.
- **NEW**: **Session totals** — cumulative docs written and searches executed per index are accumulated across all poll cycles for the lifetime of the `es-top` session, giving a "most written to during this watch" view alongside per-interval rates.
- **NEW**: **Delta calculation** — docs/sec and searches/sec are computed from wall-clock timestamps between successive poll snapshots, never from the configured interval, so rates are accurate even when polls are slow.
- **NEW**: **CLI flags**: `--interval SEC` (default 30, min 10), `--top-nodes N` (default 5), `--top-indices N` (default 10).
- **NEW**: **`escmd.yml` configuration** — `settings.es_top.interval`, `settings.es_top.top_nodes`, `settings.es_top.top_indices`. CLI flags override config values; config values override built-in defaults.
- **NEW**: **`./escmd.py help es-top`** — dedicated help screen covering all flags, dashboard panels, threshold values, `escmd.yml` config block, and usage examples.
- **NEW**: `es-top` added to the **Operations** section of `./escmd.py help` and to the quick-start examples list.
- **Code**: `commands/estop_commands.py` (new — `PollSnapshot`, `SessionTotals`, `IndexDelta`, `NodeStat`, `ProcessedData`, `EsTopPoller`, `DeltaCalculator`, `EsTopRenderer`, `EsTopDashboard`), `handlers/estop_handler.py` (new — `EsTopHandler`), `handlers/help/estop_help.py` (new), `handlers/help/help_registry.py`, `cli/argument_parser.py`, `cli/help_system.py`, `command_handler.py`, `configuration_manager.py` (`get_estop_top_indices`, `get_estop_top_nodes`, `get_estop_interval`).

---

## [3.9.4] - 2026-04-11

### Specialized help screens for `template-backup`, `template-modify`, `template-restore`, `store-password` + help topic sort

- **NEW**: **`./escmd.py help template-backup`** — dedicated help screen covering all flags (`--type`, `--backup-dir`, `--cluster`), usage examples, default backup location, filename pattern, and a before-modify backup workflow.
- **NEW**: **`./escmd.py help template-modify`** — dedicated help screen covering all four operations (`set` / `append` / `remove` / `delete`), every flag (`--dry-run`, `--no-backup`, `--backup-dir`, `--type`), dot-notation field path reference for composable and legacy templates, and safety feature notes.
- **NEW**: **`./escmd.py help template-restore`** — dedicated help screen covering the full restore workflow (list-backups → copy path → restore → verify), backup file format, and cross-cluster portability notes.
- **NEW**: **`./escmd.py help store-password`** — dedicated help screen covering single-cluster and multi-environment setup, the full password resolution priority order, encryption details (AES-128 Fernet), session caching, and troubleshooting steps. Links to `./escmd.py help security` for the full deep-dive.
- **NEW**: All four topics added to the `help` subcommand `choices` list in **`cli/argument_parser.py`** so they are valid CLI arguments.
- **UX**: **`./escmd.py help`** (general help listing) now displays all registered topics in **alphabetical order** instead of a manually maintained ordered list. New topics automatically sort into the correct position.
- **Fix**: Replaced `⚙️` (U+2699 + VS16, narrow base codepoint) with `🔩` (U+1F529, wide base) in **`handlers/help/template_modify_help.py`** panel title, consistent with the VS16 emoji alignment fix introduced in 3.8.4.
- **Code**: **`handlers/help/template_backup_help.py`** (new), **`handlers/help/template_modify_help.py`** (new), **`handlers/help/template_restore_help.py`** (new), **`handlers/help/store_password_help.py`** (new), **`handlers/help/help_registry.py`** (register four new modules), **`handlers/help_handler.py`** (alphabetical sort), **`cli/argument_parser.py`** (extended choices).

---

## [3.9.3] - 2026-04-09

### `indices --delete`: progress and result presentation

- **NEW**: **Live progress** while deleting multiple indices — on an interactive TTY (and when not using **`--quiet`**), a **Rich status** spinner shows **current index / total** and a truncated index name for each deletion. Non-TTY (e.g. piped output) behavior is unchanged.
- **NEW**: **Structured result output** after deletion — **summary panel** (requested / removed / failed counts with semantic border: success, warning, or error), a **rounded table** listing removed indices (numbered; **40-row cap** with “… and N more not shown”), and a **failures table** when any delete errors occur.
- **Code**: **`handlers/index_handler.py`** (**`_delete_indices_with_progress`**, **`_render_indices_deletion_results`**), **`commands/indices_commands.py`** (optional **`on_progress`** callback on **`delete_indices`**), **`esclient.py`** (pass-through **`on_progress`**).
- **Tests**: Existing **`tests/unit/test_json_deletion.py`** still passes.

---

## [3.9.2] - 2026-04-08

### `indices-watch-report`: interval rate stats and table layout

- **NEW**: **Per-interval docs/s** between adjacent samples — **median**, **p90**, and **max** — exposed in JSON (`docs_per_sec_interval_median`, `docs_per_sec_interval_p90`, `docs_per_sec_interval_max`, `interval_rate_count`) and in the table when **`--rate-stats auto`** (default) and there are **≥3** samples (**med/s**, **p90/s**, **max/s**, plus **span/s** for the full first→last window). With only two samples, the table stays a single **docs/s** column (one interval equals the span).
- **NEW**: **`--rate-stats`**: **`auto`** (interval columns when ≥3 samples), **`span`** (always one full-window **docs/s** column), **`intervals`** (always interval stats + **span/s** when ≥2 samples). **`--top`** sorts by median interval docs/s when interval mode is active, otherwise by span docs/s.
- **Behavior**: **HOT** and peer **rate/med** logic still use **span** docs/s (first→last), not interval medians. JSON **`docs_per_sec`** remains the span rate for compatibility.
- **UX**: The **rate/med** column is **hidden** when no row has a defined ratio (e.g. index names not in a parsed rollover series, no sibling in both snapshots, or all peer span rates are zero). **`rate_vs_peer_median`** is still present in JSON whenever computed.
- **Summary JSON**: Adds **`interval_count`**, **`rate_stats`**, **`rate_stats_primary`** (`span` or `intervals`).
- **DOCS**: **`docs/commands/index-operations.md`**, **`escmd_docs/04-command-usage.md`**; topic help **`handlers/help/indices_watch_report_help.py`**.
- **Code**: **`processors/indices_watch.py`**, **`cli/argument_parser.py`**.
- **Tests**: **`tests/unit/processors/test_indices_watch.py`**.

---

## [3.9.1] - 2026-04-07

### Master key rotation and password state file alignment

- **NEW**: **`rotate-master-key`** — Backs up the state file to **`<state-file>.old`** (e.g. **`escmd.json.old`**), generates a new Fernet **`security.master_key`**, decrypts all entries under **`security.encrypted_passwords`** with the current key, re-encrypts them with the new key, and writes the state file atomically (temp file + replace). Supports **`--yes`** to skip the confirmation prompt. If **`ESCMD_MASTER_KEY`** is set, it is used for decryption during rotation; after rotation, update that variable to the new key or unset it so the file key is used (documented in command output).
- **Behavior**: Password-related special commands (**`store-password`**, **`list-stored-passwords`**, etc.) now use **`ConfigurationManager.state_file_path`** ( **`ESCMD_STATE`** / **`ESCMD_CONFIG`** when set, otherwise **`escmd.json`** beside **`escmd.py`** ) when constructing **`PasswordManager`**, so they target the same state file as the rest of the CLI.
- **Code**: **`security/password_manager.py`** (**`rotate_master_key`**, helpers), **`handlers/password_handler.py`**, **`escmd.py`**, **`command_handler.py`**, **`cli/argument_parser.py`**, **`cli/special_commands.py`**, **`handlers/help/security_help.py`**, **`interactive_help.py`**.
- **Tests**: **`tests/unit/test_password_manager_rotation.py`**.

### Index watch: canonical cluster directory (collect vs report)

- **Fix**: **`indices-watch-collect`** wrote samples under the raw **`-l`** label (e.g. **`aex20`**), while **`set-default`** stores the resolved **`servers_dict`** key (e.g. **`aex20-glip`**). **`indices-watch-report`** without **`-l`** then looked under the default key and missed samples. Collect now uses the same **canonical cluster name** as **`set-default`** (via **`get_server_config`** resolution) for the **`~/.escmd/index-watch/<cluster>/<date>/`** path and for **`cluster`** in JSON snapshots and **`run.json`**.
- **Behavior**: **`indices-watch-report`** (when **`--dir`** is not set) tries, in order: that canonical slug, the sanitized CLI/default string, the hyphen prefix of the canonical name (so legacy **`aex20`** dirs still match when the default is **`aex20-glip`**), and other **`servers_dict`** keys that share the same server entry—first directory with samples wins.
- **Code**: **`configuration_manager.py`** (**`canonical_cluster_name_for_location`**), **`processors/indices_watch.py`** (**`index_watch_storage_slug`**, **`resolve_default_watch_sample_dir`**, **`_index_watch_sample_dir_candidates`**), **`handlers/index_handler.py`** (**`handle_indices_watch_collect`**).
- **Tests**: **`tests/unit/test_configuration.py`**, **`tests/unit/processors/test_indices_watch.py`**.

---

## [3.9.0] - 2026-04-07
 - Jumping version to 3.9.0 to include new features of: indices-watch-collect, indices-watch-report, indices-analyze, indices-s3-estimate, and Auth Profiles
 - As we added quite a bit, i felt a version increment was needed. 

## [3.8.5] - 2026-04-07

### Auth profiles (portable per-cluster authentication presets)

- **NEW**: Top-level **`auth_profiles`** in **`escmd.yml`** (dual-file mode) or in the same YAML file as **`servers:`** (single-file mode). Each profile is a mapping (currently supports **`elastic_username`**; reserved for future fields).
- **NEW**: Per-server **`auth_profile`** — references a named profile when the server entry does not set **`elastic_username`**. Lets teams share a single **`elastic_servers.yml`** while each operator maps profile names to real account names in their own main config (or via **`ESCMD_MAIN_CONFIG`**).
- **Behavior**: Effective username resolution order: per-server **`elastic_username`** → **`auth_profiles[auth_profile].elastic_username`** → special case: **`passwords[env]`** with exactly one username key → **`elastic_username`** in **`escmd.json`** → **`settings.elastic_username`**. An unknown **`auth_profile`** prints a warning and resolution continues with the remaining steps.
- **Dual-file rule**: **`auth_profiles`** are loaded only from the **main** configuration file (**`escmd.yml`** or **`ESCMD_MAIN_CONFIG`**), not from **`elastic_servers.yml`**.
- **UI**: **`locations`**, **`show-settings`**, and related views label usernames sourced from a profile (e.g. **`Auth profile (name)`**).
- **DOCS**: **`docs/configuration/dual-file-config-guide.md`**, **`docs/configuration/cluster-setup.md`**, **`docs/configuration/password-management.md`**, **`docs/configuration/installation.md`**, **`docs/reference/troubleshooting.md`**, **`docs/commands/snapshot-management.md`**, **`docs/README.md`**; user-facing summary in **`escmd_docs/03-configuration.md`**.
- **Code**: **`configuration_manager.py`**, **`display/locations_data.py`**, **`display/settings_data.py`**; tests in **`tests/unit/test_configuration.py`**.

---

## [3.8.4] - 2026-04-04

### Terminal emoji alignment fix — replace narrow-width VS16 emoji throughout

#### Root cause

Six emoji used throughout the codebase as table-column labels and panel titles
were causing **column-value misalignment** visible in commands such as
`./escmd.py version` (e.g. the `D` in `Darwin arm64` starting one column to the
left of `3.14.3` on the `Python:` row above it).

The underlying issue is a three-layer disagreement:

| Layer | How it measured the emoji |
|---|---|
| **Python `unicodedata.east_asian_width()`** | `'N'` (Narrow = 1 cell) for the base codepoint |
| **Rich ≤ 14.1.0** | `1` cell (used the same narrow lookup table) |
| **Rich ≥ 14.3.0** (PR #3930) | `2` cells ✓ (new grapheme-aware VS16 handling) |
| **Terminal (system wcwidth / font metrics)** | `1` cell — follows the system Unicode data, which marks these base codepoints as narrow |

After upgrading to Rich 14.3.3 (see below) Rich correctly pads each column for
2-wide emoji, but the **terminal still renders them as 1-wide**, so every row
containing one of these emoji has its value shifted one column to the right
relative to all other rows.

The six problematic emoji all share the same pattern: their **base codepoint has
`east_asian_width = 'N'`** (Narrow), and they rely on **Variation Selector-16
(U+FE0F)** to force full-width emoji presentation in colour-capable terminals.
The problem is that the VS16 trick is honoured by *rendering* but not by the
system *width* calculation, so the terminal cursor advances by only 1 cell after
drawing a 2-cell glyph.

#### Fix — part 1: upgrade Rich to ≥ 14.3.3

`requirements.txt` minimum bumped from `rich>=13.9.4` to `rich>=14.3.3`.

Rich 14.3.3 ships PR #3930 *"Handle graphemes"*, which replaces the old single-
codepoint lookup table with grapheme-cluster-aware width tables derived from the
`wcwidth` project. This correctly accounts for VS16 sequences. Without this
upgrade the column widths Rich calculates are wrong for these emoji regardless
of any other change.

#### Fix — part 2: replace all six problematic emoji

Even with Rich 14.3.3 measuring widths correctly, the terminal's own width
calculation (used to advance the cursor) is independent of Rich. Terminals that
use the system `wcwidth()` or the font's glyph-advance metric for these
codepoints will render them 1 cell wide, creating a permanent 1-column shift.

The solution is to replace every occurrence of the six problematic emoji with
visually equivalent alternatives whose **base codepoints have
`east_asian_width = 'W'`** — so both Rich *and* every terminal agree they are
2 cells wide:

| Removed | `ea_width` | Replaced with | `ea_width` | Semantic meaning |
|---|---|---|---|---|
| `🖥️` U+1F5A5 + VS16 | `N` | `💻` U+1F4BB | `W` | Computer / platform / node |
| `⚠️` U+26A0 + VS16 | `N` | `🔶` U+1F536 | `W` | Warning / caution |
| `⚙️` U+2699 + VS16 | `N` | `🔩` U+1F529 | `W` | Settings / configuration |
| `⏱️` U+23F1 + VS16 | `N` | `⏰` U+23F0 | `W` | Time / elapsed |
| `🛡️` U+1F6E1 + VS16 | `N` | `🔐` U+1F510 | `W` | Security / protection |
| `🏷️` U+1F3F7 + VS16 | `N` | `🔖` U+1F516 | `W` | Label / tag |

Replacements applied globally across all 56 affected `.py` files.

#### Fix — part 3: remove compensatory double-spaces

Prior to the Rich upgrade, several label strings had a second space manually
inserted after the emoji (e.g. `"🖥️  Platform:"`) as an attempted visual
workaround. These over-padded strings were removed from all renderer and data
files now that both Rich and the terminal agree on the correct width:

- `display/version_renderer.py` — `🖥️  Platform:`, `🖥️  CPU Usage:`,
  `⏱️  System Time:`, `⏱️  Current Time:` (×2), `⚙️  Settings & Config`,
  `🛡️  Error Handling:`
- `display/version_data.py` — `⚙️  Settings & Config`, `🛡️  Error Handling:`
- `display/health_renderer.py` — `🖥️  Total Nodes:` (×2), `⚙️  Master Nodes:`,
  `🖥️  Node Information`, `⚠️  Version:`
- `display/ilm_renderer.py` — `⚠️  Check errors:`
- `display/index_renderer.py` — `🖥️  {count}`, `⚠️  {count}`
- `display/replica_renderer.py` — `⚠️  No replicas`
- `display/shard_renderer.py` — `⚠️  Warning …`, `🖥️  Node`
- `display/template_renderer.py` — 10 occurrences across panel titles and
  table titles

#### Verification

A diagnostic script `measure_labels.py` is included at the project root. It
runs `./escmd.py version`, captures the rendered output, and reports the
terminal column at which each value starts. After this fix every content line
in the version output is exactly 80 terminal columns wide and all value columns
are aligned:

```
Main version panel rows:
  label                           val_col
  ------------------------------------------
  🚀 Tool:                              19
  📦 Version:                           19
  📅 Released:                          19
  🎯 Purpose:                           19
  👥 Team:                              19
  🐍 Python:                            19
  💻 Platform:                          19
```

- **Code**: all `display/` renderers, `handlers/`, `commands/`, `cli/`,
  `escmd.py`, `esclient.py`, `configuration_manager.py`,
  `interactive_help.py`, `security/`, `esterm_modules/`, `reports/`,
  `processors/`, `generate_elastic_servers.py` (56 files total).
- **Dependency**: `requirements.txt` (`rich>=14.3.3`).
- **Tooling**: `measure_labels.py`, `analyze_version.py` (diagnostic scripts).

---

## [3.8.3] - 2026-04-03

### Elasticsearch read timeout propagation and `flush` request timeout

- **FIX**: **`read_timeout`** from **`escmd.yml`** / per-server YAML is now included in **`get_server_config_by_location()`**, and **`create_elasticsearch_client()`** always sets **`location_config["read_timeout"]`** so the Elasticsearch Python client uses the intended value instead of falling through to a short implicit default.
- **FIX**: **`ElasticsearchClient`** resolves HTTP timeout as **`read_timeout`** → **`elastic_read_timeout`** → **`ConfigurationManager.get_read_timeout()`** (default **60** seconds).
- **CHANGE**: Environment-scoped minimal client config uses **`config_manager.get_read_timeout()`** instead of a hard-coded **30** seconds.
- **NEW**: Cluster **`flush`** uses a dedicated HTTP **`request_timeout`**: optional **`flush_timeout`** in **`settings`** (`escmd.yml`), else **`max(5 × read_timeout, 300)`** seconds, so large clusters can complete flush without hitting the normal client read timeout.
- **DOCS**: **`flush_timeout`** described in **`display/settings_data.py`**, **`display/settings_renderer.py`**; example in **`display/settings_example.py`**.
- **Code**: `configuration_manager.py`, `escmd.py`, `esclient.py`, `commands/utility_commands.py`.

---

## [3.8.2] - 2026-04-02

### S3 storage estimate — months 2–3 projection

- **`indices-s3-estimate`** JSON and table now include **cumulative buffered bytes/GiB** and **estimated USD** for **month 2** and **month 3**, using **M ×** the one-month buffered slice **×** `price_per_gib_month` (steady accrual model). See `assumptions.multi_month_model` in JSON.
- **Code**: `processors/s3_storage_estimate.py`, `display/index_renderer.py`, tests, help text.

---

## [3.8.1] - 2026-04-02

### S3 storage estimate (`indices-s3-estimate`)

- **NEW**: **`indices-s3-estimate`** sums **`pri.store.size`** from **`_cat/indices`** for indices whose **rollover date in the name** is on or after **UTC today minus `--within-days`** (default **30**), same naming rules as **`indices-analyze`**. Replicas are excluded (single-copy basis for S3 planning).
- **Flags**: **`--price-per-gib-month USD`** (required; USD per gibibyte-month), **`--buffer-percent P`**, optional **`regex`**, **`--status`**, **`--include-undated`**, **`--format json`**. **`./escmd.py help indices-s3-estimate`** for full detail.
- **Code**: `processors/s3_storage_estimate.py`, `handlers/index_handler.py`, `display/index_renderer.py`, `cli/argument_parser.py`, `command_handler.py`, `cli/special_commands.py`, `handlers/help/indices_s3_estimate_help.py`, `handlers/help/help_registry.py`, `handlers/help/indices_help.py`, `handlers/help_handler.py`, `cli/help_system.py`, unit tests `tests/unit/processors/test_s3_storage_estimate.py`.

---

## [3.8.0] - 2026-03-30

### Index ingest watch (`indices-watch-collect` / `indices-watch-report`)

- **NEW**: **`indices-watch-collect`** calls `_cat/indices` on a configurable interval and writes JSON snapshots. Default path **`~/.escmd/index-watch/<location>/<UTC-YYYY-MM-DD>/`** (override with **`ESCMD_INDEX_WATCH_DIR`** or **`--output-dir`**). Supports **`--interval`**, **`--duration`** (omit to run until Ctrl+C), optional index **`regex`** and **`--status`**, and **`--retries` / `--retry-delay`** per host.
- **NEW**: Per-sample **failover** across **`elastic_host`**, **`elastic_host2`**, and optional **`elastic_host3`** (`hostname3` in server YAML / `elastic_host3` in resolved config). **`ElasticsearchClient`** exposes **`host3`**.
- **NEW**: **`indices-watch-report`** reads samples **without an Elasticsearch connection** (listed under no-connection commands). Defaults to **today’s UTC date** and cluster slug from **`-l`**, else **`--cluster`**, else default cluster from state. Flags: **`--dir`**, **`--date`**, **`--min-docs-delta`**, **`--hot-ratio`**, **`--min-peers`**, **`--top`**, **`--format json`**.
- **Method**: Report compares **first vs last** sample timestamps, computes **Δ docs**, **docs/s**, **Δ store**, and **HOT** when **docs/s** ≥ **`hot_ratio`** × leave-one-out **median peer docs/s** within the same rollover series (same name pattern as **`indices-analyze`**). Table output uses the same **theme / `StyleSystem` table** styling as **`indices-analyze`**; rows with **Δ docs = 0** are omitted from the report. **rate/med** (formerly a single “vs peer” column) uses sibling indices that appear in **both** samples even when their doc Δ is zero (so the column is populated whenever the peer median is positive). **Δ store** uses signed human-readable sizes (e.g. **-13.40MB**) when merge/compaction shrinks disk between samples.
- **Report**: **docs** = last-sample doc count; **med peer** = leave-one-out median doc count among sibling backing indices; **docs/med** = ratio (same idea as **`indices-analyze`** doc outliers). **⚠** when **docs/med** ≥ **`--docs-peer-ratio`** (default **5**; use **0** to disable the flag only). Columns **rate/med** and **docs/med** are both shown.
- **DOCS**: **`./escmd.py --help`** lists ingest-watch commands and topic examples; **`./escmd.py help`** includes **`indices-analyze`**, **`indices-watch-collect`**, and **`indices-watch-report`**; **`./escmd.py help indices-analyze`** / **`... indices-watch-collect`** / **`... indices-watch-report`** give detailed usage. **`handlers/help/indices_analyze_help.py`**, **`indices_watch_collect_help.py`**, **`indices_watch_report_help.py`**, **`cli/help_system.py`**, **`cli/argument_parser.py`** (`help` subcommand choices), **`handlers/help_handler.py`**. **`docs/commands/index-operations.md`** covers **`indices-analyze`** and ingest watch commands.
- **Code**: `processors/indices_watch.py`, `handlers/index_handler.py`, `cli/argument_parser.py`, `command_handler.py`, `escmd.py`, `configuration_manager.py`, `esclient.py`, `cli/special_commands.py`, `handlers/help/indices_help.py`, `tests/unit/processors/test_indices_watch.py`.

---

## [3.7.4] - 2026-03-27

### Index traffic analysis (`indices-analyze`)

- **NEW**: Command **`indices-analyze`** finds Elasticsearch backing indices whose size or document count is an outlier compared to **siblings in the same rollover series** (index names matching `...-YYYY.MM.DD-NNNNNN`, including `.ds-` data stream backing indices). Useful during incidents when one generation suddenly grows much larger than prior weeks.
- **Method**: For each base pattern, compares every index to a **leave-one-out median** of peer `docs.count` (and reports store size ratio vs peer median). Results are sorted by **highest doc ratio first**.
- **`--min-ratio`** (default **5**): Only show indices whose doc count is at least this multiple of the peer median.
- **`--min-docs`** (default **1_000_000**): Only show outliers with at least this many documents on that index (reduces noise from tiny indices with high ratios). Use **`0`** to disable the floor.
- **`--within-days N`**: Only show outliers whose **rollover date parsed from the index name** is on or after **UTC today minus N calendar days**. Baselines still use all siblings in the series. JSON `summary` includes `within_days`, `as_of_date_utc`, and `rollover_date_cutoff_utc` when this filter is active.
- **Additional flags**: `--min-peers`, `--top`, `--status` (green/yellow/red), `--format json`, `--pager`, and an optional **pattern** argument with the same semantics as **`indices`**.
- **Output**: Rich table (subtitle shows active filters; hot-index marker where applicable) or JSON with `summary` and `rows` for automation. Summary always includes `min_docs` (the configured floor, including `0`).
- **Code**: `processors/index_traffic_analyzer.py`, `handlers/index_handler.py`, `display/index_renderer.py`, `cli/argument_parser.py`, `command_handler.py`, `cli/special_commands.py`, `handlers/help/indices_help.py`, unit tests in `tests/unit/processors/test_index_traffic_analyzer.py`.

---

## [3.7.3] - 2026-03-25

### ILM: migrate by source policy
- **NEW**: `ilm set-policy <target-policy> --from-policy <source-policy>` selects every index that currently uses the source ILM policy and assigns the target policy. Works with existing `--dry-run`, `--yes`, `--format json`, and `--max-concurrent`.
- **NEW**: `ElasticsearchClient.get_indices_for_ilm_policy()` returns index rows shaped for bulk policy assignment (reuses `get_ilm_policy_detail()` / `explain_lifecycle`).

### ILM fixes
- **FIX**: `ilm policy <name> --show-all` now passes `show_all` into the policy detail renderer so the indices table lists all managed indices instead of truncating while ignoring the flag.
- **FIX**: `ilm set-policy` result export metadata uses the resolved `source_description` (e.g. pattern, file, or `from-policy: …`) instead of referencing an undefined name.
- **DOCS**: `--show-all` help for `ilm policy` now states the default preview count is **15** indices (matching the renderer).

### Other
- **DOCS**: ILM help text and examples updated for `--from-policy` (`handlers/lifecycle_handler.py`, `handlers/help/ilm_help.py`).

---

## [3.7.2] - 2026-02-26

### 🔧 Hotfix: Missing Method Implementation
- **Critical Fix**: Added missing `remove_ilm_policy_from_indices()` method to `ElasticsearchClient` class
- **Issue 1**: `ilm remove-policy --file` command was failing with `AttributeError: 'ElasticsearchClient' object has no attribute 'remove_ilm_policy_from_indices'`
- **Issue 2**: Indices without ILM policies were causing `index_not_found_exception` errors even though indices existed
- **Resolution**: Implemented the missing method with concurrent processing, progress tracking, error handling, and intelligent policy detection
- **Enhancement**: Method now pre-checks if index has ILM policy before attempting removal, skipping unmanaged indices with clear messages
- **Impact**: All ILM file-based removal operations now work correctly with smart skip logic for indices without policies

### 🎯 Major Feature: ILM Policy Backup and Restore

#### 💾 **New ILM Backup/Restore Commands**
- **ILM Policy Backup**: New `ilm backup-policies` command to backup ILM policies for a list of indices to JSON format
- **ILM Policy Restore**: New `ilm restore-policies` command to restore ILM policies from backup JSON with dry-run support
- **Maintenance Workflow Support**: Complete workflow for temporarily removing and restoring ILM policies during maintenance windows
- **Audit Trail**: Backup files include timestamps and full ILM state information for compliance and documentation

#### 📄 **Enhanced File Input Support**
- **Text File Support**: All ILM file-based commands now support simple text files (one index per line) in addition to JSON
- **Multiple Format Support**: Commands accept text files, JSON arrays, or JSON objects with "indices" key
- **Backward Compatible**: Existing JSON file workflows continue to work unchanged
- **Simplified Operations**: Text file format makes it easier to create and maintain index lists

#### 🔧 **Enhanced ILM Commands**
- **remove-policy Enhancement**: Now supports both text and JSON file inputs for maximum flexibility
- **set-policy Enhancement**: Now supports both text and JSON file inputs for easier bulk operations
- **Intelligent Format Detection**: Automatically detects and parses text or JSON format from input files
- **Error Resilience**: Continues processing all indices even if some fail, with comprehensive error reporting

#### 📊 **Rich Output and Reporting**
- **Summary Statistics**: Clear reporting of success/skip/error counts for all operations
- **Detailed Backup JSON**: Backup files include index name, policy, managed status, phase, action, and step information
- **Dry-Run Support**: Preview all changes before execution with detailed impact analysis
- **Multiple Output Formats**: Both table and JSON output formats for human and machine consumption

#### 🚀 **Command Usage Examples**
```bash
# Backup ILM policies for specific indices
./escmd.py ilm backup-policies \
  --input-file indices.txt \
  --output-file ilm-backup.json

# Preview restore operation
./escmd.py ilm restore-policies \
  --input-file ilm-backup.json \
  --dry-run

# Restore ILM policies
./escmd.py ilm restore-policies \
  --input-file ilm-backup.json

# Remove policies from text file
./escmd.py ilm remove-policy --file indices.txt --yes

# Set policy from text file
./escmd.py ilm set-policy my-policy --file indices.txt --yes
```

#### 📚 **Comprehensive Documentation**
- **Detailed Examples**: Complete workflow examples in `examples/ilm/README.md` with real-world use cases
- **Quick Start Guide**: New `QUICKSTART_ILM_BACKUP.md` for rapid onboarding
- **Visual Workflows**: Comprehensive workflow diagrams in `examples/ilm/WORKFLOW.md`
- **Updated ILM Docs**: Enhanced `docs/commands/ilm-management.md` with backup/restore sections
- **Feature Summary**: Complete feature documentation in `ILM_BACKUP_RESTORE_FEATURE.md`

#### 🛡️ **Production-Ready Features**
- **Graceful Error Handling**: Robust error handling with clear error messages and troubleshooting guidance
- **Concurrent Operations**: Efficient processing with configurable concurrency for large index lists
- **Skip Logic**: Automatically skips indices without policies during restore operations
- **Validation**: Comprehensive input validation for files, formats, and policy existence
- **State Tracking**: Full state information captured in backups for accurate restoration

#### 🎯 **Use Cases**
- **Maintenance Windows**: Temporarily remove ILM policies during maintenance, restore afterward
- **Policy Migration**: Backup current policies before migrating to new policy structures
- **Disaster Recovery**: Keep backups of ILM configurations for recovery scenarios
- **Testing**: Backup production policies, test changes, rollback if needed
- **Compliance**: Document which indices had which policies at specific times
- **Bulk Operations**: Easily manage ILM policies for many indices simultaneously

#### 📈 **Operational Benefits**
- **Reduced Risk**: Safe policy changes with backup and restore capability
- **Time Savings**: Bulk operations on multiple indices with single commands
- **Simplified Workflows**: Clear, documented process for policy management during maintenance
- **Better Tracking**: Timestamped backups provide audit trail of policy changes
- **Improved Safety**: Dry-run support prevents accidental changes

#### 🔄 **Complete Maintenance Workflow**
```bash
# 1. Create indices list (text file - simple!)
cat > maintenance-indices.txt << EOF
logs-prod-2024.01.01
logs-prod-2024.01.02
metrics-prod-2024.01.01
EOF

# 2. Backup ILM policies
./escmd.py ilm backup-policies \
  --input-file maintenance-indices.txt \
  --output-file ilm-backup-20260226.json

# 3. Remove ILM policies for maintenance
./escmd.py ilm remove-policy --file maintenance-indices.txt --yes

# 4. Perform maintenance operations...

# 5. Restore ILM policies
./escmd.py ilm restore-policies \
  --input-file ilm-backup-20260226.json

# 6. Verify restoration
./escmd.py ilm errors
```

#### 📦 **Files Modified/Created**
- **Modified**: `handlers/lifecycle_handler.py` - Added backup/restore methods and enhanced file loading
- **Modified**: `cli/argument_parser.py` - Added new command parsers and updated help text
- **Modified**: `docs/commands/ilm-management.md` - Added comprehensive backup/restore documentation
- **Created**: `examples/ilm/README.md` - Detailed examples and best practices guide
- **Created**: `examples/ilm/WORKFLOW.md` - Visual workflow diagrams and state transitions
- **Created**: `examples/ilm/sample-indices.txt` - Example input file
- **Created**: `QUICKSTART_ILM_BACKUP.md` - Quick start guide for new feature
- **Created**: `ILM_BACKUP_RESTORE_FEATURE.md` - Complete feature summary and reference

---

## [3.7.1] - 2025-11-03

### 🎯 Minor Enhancement: Repository Verification Error Handling

#### 🚫 **Enhanced Repository Verification Error Display**
- **Intelligent Error Parsing**: Automatically detects and parses `TransportError` messages with `repository_verification_exception` to extract individual node failure information
- **Beautiful Table Display**: Transforms ugly, unreadable error messages into clean, organized tables showing each failed node with details
- **Comprehensive Node Information**: Shows node name, IP address, availability zone, error type, and issue summary for each failed node
- **Zone Breakdown Analysis**: Displays affected availability zones with failure counts for quick infrastructure assessment

#### 📊 **Professional Error Reporting**
- **Summary Overview Panel**: Shows total failed nodes, primary error type, and zone distribution at a glance
- **Structured JSON Output**: Provides machine-readable error data for automation and monitoring systems with detailed metrics
- **Smart Error Classification**: Automatically categorizes error types (S3 Access Denied, IO Exception, Repository Access) with appropriate summaries
- **Contextual Troubleshooting**: Displays intelligent suggestions based on error type with specific remediation steps

#### 🛠️ **Technical Implementation**
- **Robust Error Parsing**: Advanced regex-based parsing handles complex nested error structures with escaped quotes and brackets
- **Multi-Node Support**: Efficiently processes and displays failures from multiple nodes (tested with 12+ node failures)
- **Graceful Fallback**: If enhanced parsing fails, automatically falls back to original error display for reliability
- **Format Consistency**: Works with both table and JSON output formats maintaining consistent user experience

#### 🎯 **User Experience Benefits**
- **Instant Problem Identification**: Immediately see which nodes are failing and why instead of parsing massive error text
- **Operational Efficiency**: Quick identification of permission issues, network problems, or configuration errors
- **Cross-Zone Analysis**: Easily identify if problems are zone-specific or cluster-wide
- **Actionable Information**: Clear next steps for resolving common issues like S3 permissions

#### 🚀 **Command Usage Examples**
```bash
# Enhanced table display (default)
./escmd.py -l cluster repositories verify repo-name

# Structured JSON for automation
./escmd.py -l cluster repositories verify repo-name --format json
```

#### 📈 **Operational Impact**
- **Faster Issue Resolution**: Reduced troubleshooting time from reading complex error logs to immediate problem identification
- **Better Monitoring Integration**: JSON output enables automated error tracking and alerting systems
- **Improved Documentation**: Clear error categorization helps with creating runbooks and troubleshooting guides
- **Enhanced Team Productivity**: Less time spent deciphering error messages, more time solving actual problems

---

## [3.7.0] - 2025-10-29

### 🌍 Major Feature: Environment-Specific Metrics Configuration

#### 🎯 **Automatic Environment Detection for Metrics**
- **Environment-Based Auto-Configuration**: New `--env` parameter integration with `--metrics` flag for automatic InfluxDB endpoint and database selection
- **Multi-Environment Support**: Pre-configured support for BIZ, LAB, OPS, US, EU, and IN environments with correct endpoints
- **Zero-Configuration Operation**: Eliminates manual configuration switches when working across different environments
- **Seamless Integration**: Works with all existing dangling command operations (cleanup, reporting, batch operations)

#### 🏗️ **Enhanced Configuration Architecture**
- **Extended YAML Structure**: New `metrics.environments` section in `escmd.yml` for environment-specific overrides
- **Intelligent Configuration Merging**: Environment-specific settings override base configuration while maintaining all other settings
- **Backward Compatibility**: Existing metrics configuration continues to work unchanged as fallback defaults
- **Flexible Environment Mapping**: Easy addition of new environments through simple YAML configuration

#### 📊 **Environment-to-Endpoint Mappings**
```yaml
biz: http://192.168.0.142:8086 → elk-stats
lab/ops: http://influxdb.ops.example.com:8086 → elk-stats
us/eu/in: http://na-metrics.int.example.com:8086 → elk-stats
```

#### 🚀 **Command Usage Examples**
```bash
# BIZ environment metrics - auto-detects correct endpoint
./escmd.py dangling --env biz --metrics

# LAB environment with cleanup and metrics
./escmd.py dangling --env lab --cleanup-all --metrics --dry-run

# Multi-environment support across all dangling operations
./escmd.py dangling --env us --batch 10 --metrics
```

#### 🔧 **Technical Implementation**
- **Configuration Manager Enhancement**: Extended `get_metrics_config()` method with environment parameter support
- **Metrics Client Integration**: Updated `DanglingMetrics` class constructor to accept environment context
- **Handler Integration**: All dangling handler metrics instantiations updated to pass environment from command arguments
- **Priority-Based Resolution**: Environment variables → Environment config → Base config → Defaults

#### 🛡️ **Production-Ready Features**
- **Fallback Behavior**: Unknown environments gracefully fall back to default configuration
- **Error Handling**: Clear error messages for configuration issues with helpful troubleshooting guidance
- **Validation**: Comprehensive configuration validation ensures required fields are present
- **Documentation**: Complete documentation with usage examples and troubleshooting guide

#### 📈 **Operational Benefits**
- **Reduced Operator Error**: No more manual endpoint switching between environments
- **Simplified Workflows**: Single command works across all environments with correct routing
- **Consistent Metrics**: Ensures metrics always go to the correct database for each environment
- **Audit Trail**: Clear logging shows which endpoint and database are being used for each operation

---

## [3.6.0] - 2025-10-23

### 🔍 Major Feature: Repository Verification Command

#### 📦 **New Repository Verification System**
- **Dedicated Command Structure**: New `./escmd.py repositories verify <repo_name>` command for testing repository connectivity
- **Multi-Node Testing**: Verifies that snapshot repositories are accessible from all cluster nodes
- **Alphabetical Sorting**: Node results displayed alphabetically by node name for improved readability
- **Comprehensive Coverage**: Tests repository connectivity across entire cluster before backup operations

#### 🛠️ **Enhanced Command Interface**
- **Intuitive Syntax**: Clean command structure `repositories verify` instead of nested under snapshots
- **Dual Output Formats**: Both table and JSON output formats supported with `--format` option
- **Rich Visual Display**: Color-coded verification results with status indicators (✓ Verified)
- **Detailed Node Information**: Shows node names, IDs, and verification status in organized table format

#### 🎯 **Operational Benefits**
- **Proactive Testing**: Identify repository connectivity issues before they cause backup failures
- **Cluster-Wide Validation**: Ensures all nodes can access repository, preventing partial backup scenarios
- **Easy Troubleshooting**: Clear visual feedback on which nodes have repository access issues
- **Automation Ready**: JSON output format perfect for monitoring systems and automated workflows

#### 📊 **Professional Output Display**
- **Sorted Node Lists**: Nodes displayed alphabetically (masters first, then data nodes in order)
- **Status Summary**: Clear success/failure summary with total node count and verification status
- **Error Handling**: Detailed error messages for missing repositories and connectivity issues
- **Consistent Formatting**: Matches escmd's rich terminal output standards with panels and tables

#### 🔧 **Technical Implementation**
- **REST API Integration**: Uses Elasticsearch's `POST _snapshot/<repo>/_verify` endpoint
- **Enhanced Argument Parser**: New verify subcommand under repositories with proper help text
- **Updated Documentation**: Comprehensive documentation with usage examples and troubleshooting guides
- **Backwards Compatible**: Existing repository commands unchanged, new verify functionality added seamlessly

#### 🚀 **Usage Examples**
```bash
# Verify S3 repository connectivity
./escmd.py repositories verify s3_repo

# Get JSON output for automation
./escmd.py repositories verify s3_repo --format json

# Use with specific clusters
./escmd.py -l production repositories verify backup-repo
```

#### 📈 **Integration & Workflows**
- **Pre-Backup Validation**: Natural integration into backup workflows for proactive testing
- **Monitoring Integration**: JSON output ready for Nagios, Prometheus, or other monitoring systems
- **Troubleshooting Workflows**: Clear diagnostics for repository connectivity issues
- **Documentation Updates**: Complete integration into snapshot management documentation and examples

---

## [3.5.0] - 2025-10-22

### ⚡ Performance Enhancement: Fast Mode Default for Snapshots

#### 🚀 **Improved Default Performance**
- **Fast Mode by Default**: `snapshots list` command now defaults to fast mode for dramatically improved performance
- **Up to 25x Faster**: Snapshot listing now completes in 1-2 seconds instead of 15-30+ seconds for large repositories
- **Backward Compatible**: All existing commands continue to work unchanged with improved performance

#### 🛠️ **Enhanced Command Options**
- **New `--slow` Flag**: Added `--slow` option to access full metadata when needed
- **Advanced Mode Selection**: New `--mode {fast,slow}` parameter for explicit mode control
- **Smart Defaults**: Intelligent mode selection prioritizes performance for common use cases
- **Preserved Compatibility**: Existing `--fast` flag continues to work for backward compatibility

#### 📊 **Significant Performance Improvements**
- **100 snapshots**: 0.3s (was 2.1s) - 7x faster
- **500 snapshots**: 0.6s (was 8.4s) - 14x faster
- **1000 snapshots**: 0.9s (was 15.2s) - 17x faster
- **2000+ snapshots**: 1.2s (was 30+ seconds) - 25x+ faster

#### 🎯 **User Experience Enhancements**
- **Clear Mode Indicators**: Status messages now clearly show current mode (fast mode/full metadata)
- **Updated Help Documentation**: All help text reflects new default behavior with examples
- **Smart Workflows**: Common operations now perform optimally without configuration changes

#### 🔧 **Technical Implementation**
- **Enhanced Argument Parser**: New mode-based argument structure with fallback compatibility
- **Updated Handler Logic**: Improved mode detection and processing in snapshot handler
- **Comprehensive Testing**: Thorough validation across all argument combinations and use cases

---

## [3.4.1] - 2025-10-06

### 🔧 Major Enhancement: Unified Dangling Command Logging System

#### 📝 **Simplified Log File Management**
- **Single Log File**: Changed from date-specific logs (`dangling_YYYYMMDD.log`) to unified `dangling.log`
- **Environment Consolidation**: All environments (us, eu, in, etc.) now log to single file for easier tracking
- **Automatic File Rotation**: Implements 200MB file size limit with automatic rotation to `dangling.log.1`
- **Smart Backup Management**: Keeps only 1 backup file, automatically removing older backups

#### 🔍 **Enhanced Cluster-Level Logging**
- **Individual Cluster Tracking**: Each cluster logs its dangling index count with detailed status
- **Clean Cluster Logging**: `Cluster 'cluster-name': 0 dangling indices (clean)`
- **Dangling Detection Logging**: `Cluster 'cluster-name': X dangling indices found`
- **Error State Logging**: `Cluster 'cluster-name': query failed - error details`

#### 📊 **Environment Summary Reporting**
- **Comprehensive Summaries**: Added environment-level summary logging after each scan
- **Clean Environment**: `Environment 'env-name' summary: All X clusters clean (0 dangling indices)`
- **Problem Detection**: `Environment 'env-name' summary: X dangling indices found across Y/Z clusters`
- **Centralized Monitoring**: Easy identification of environment health at a glance

#### 🛠️ **Technical Implementation**
- **Rotating File Handler**: Uses `RotatingFileHandler` with 200MB max size and 1 backup count
- **Unified Logger Configuration**: Updated both main application and report loggers to use same file
- **Error Handling Fixes**: Resolved `TypeError` issues with `PasswordCommands` and `ActionHandler` classes
- **Production Ready**: Suitable for cron jobs and automated monitoring systems

#### 🎯 **Operational Benefits**
- **Simplified Monitoring**: Single file to monitor all dangling operations across all environments
- **Historical Tracking**: Automatic file rotation preserves recent history while managing disk space
- **Audit Trail**: Complete logging of all cluster checks with timestamps and detailed results
- **Troubleshooting**: Enhanced error logging for failed cluster queries and connection issues

---

## [3.4.0] - 2025-09-29

### 🚀 Major Feature: Dangling Indices Metrics Integration

#### 📊 **InfluxDB/VictoriaMetrics Integration**
- **Metrics Collection**: New `--metrics` flag for dangling command to send statistics to time-series databases
- **Multiple Database Support**: Compatible with InfluxDB v1.x, InfluxDB v2.x, and VictoriaMetrics
- **Flexible Configuration**: Support for both configuration file and environment variable setup
- **Authentication Support**: Username/password, token-based, and SSL verification options

#### 🔍 **Comprehensive Metrics Coverage**
- **Single Cluster**: `./escmd.py dangling --metrics` - Send metrics for current cluster
- **Environment-Wide**: `./escmd.py dangling --env production --metrics` - Collect across all clusters in environment
- **Cluster Groups**: `./escmd.py dangling --group prod --metrics` - Monitor specific cluster groups
- **Cleanup Operations**: `./escmd.py dangling --cleanup-all --metrics` - Track cleanup success rates

#### 🧪 **Dry-Run Testing & Validation**
- **Line Protocol Preview**: `--dry-run` flag shows exact InfluxDB line protocol that would be sent
- **Configuration Testing**: Validate metrics setup without sending data
- **Clean Output**: Simplified dry-run output shows only line protocol for easy automation
- **Zero-Impact Testing**: Perfect for validating cron jobs and automated workflows

#### 📈 **Metrics Format & Structure**
- **Measurement**: `elastic_dangling_deletion` with cluster, environment, and operation tags
- **Key Fields**: `found` (discovered indices), `deleted` (cleanup count), `nodes_affected` (impacted nodes)
- **Rich Tagging**: Environment names, cluster groups, and operation types for detailed filtering
- **Timestamp Precision**: Nanosecond precision for accurate time-series analysis

#### ⚙️ **Configuration & Setup**
- **YAML Configuration**: New `metrics` section in `escmd.yml` for centralized setup
- **Environment Variables**: `ESCMD_METRICS_*` variables for secure credential management
- **Connection Validation**: Built-in connection testing and error reporting
- **Graceful Degradation**: Metrics failures don't impact primary dangling operations

#### 🔄 **Automation & Monitoring**
- **Cron Integration**: Perfect for automated monitoring with clean, parseable output
- **Grafana Dashboards**: Ready-to-use queries for visualization and alerting
- **Alert-Ready**: Structured data format ideal for threshold-based monitoring
- **Batch Processing**: Efficient bulk metrics sending for environment-wide scans

#### 🛡️ **Production-Ready Features**
- **Error Handling**: Comprehensive error reporting with detailed logging
- **SSL Support**: Full SSL/TLS support with certificate validation options
- **Timeout Management**: Configurable timeouts for reliable operations
- **Non-Intrusive**: Zero impact on existing dangling command functionality

#### 📚 **Documentation & Examples**
- **Complete Guide**: Comprehensive documentation at `docs/dangling-metrics.md`
- **Configuration Examples**: Templates for all supported database types
- **Cron Job Examples**: Production-ready automation scripts
- **Grafana Queries**: Dashboard and alerting query examples

#### 🔧 **Technical Implementation**
- **Modular Design**: Clean separation between core functionality and metrics
- **Efficient Processing**: Optimized data collection with minimal performance overhead
- **Memory Management**: Smart handling of large environment scans
- **Connection Pooling**: Efficient database connections for batch operations

---

## [3.3.0] - 2025-09-25

### 🚀 Major Release: Enhanced Actions System with Command Chaining & Data Passing

#### 🔗 **Revolutionary Command Chaining Architecture**
- **Output Capture & Variable Storage**: Steps can now capture command outputs and store them in variables for use in subsequent steps
- **JSON Path Extraction**: Extract specific values from JSON responses using JSONPath syntax (`$.field.subfield`)
- **Variable Interpolation**: Use captured variables in subsequent commands with Jinja2 template syntax (`{{ variable }}`)
- **Conditional Step Execution**: Execute steps conditionally based on previous step results with advanced condition evaluation
- **Cross-Step Data Flow**: Full data passing pipeline enables complex multi-step workflows

#### 🎯 **Rollover & Index Management Automation**
- **Automated Rollover + Cleanup**: New `roll-igl` action automatically rolls over datastreams and deletes old indices
- **Safety-First Rollover**: `roll-igl-safe` includes comprehensive health checks and verification steps
- **Parameterized Actions**: `roll-with-params` allows rollover operations on any datastream with configurable options
- **Smart Condition Logic**: Only deletes old indices when rollover actually succeeds
- **Built-in Confirmations**: Safety prompts for destructive operations with override options

#### 🛠 **Advanced Action Features**
- **Enhanced YAML Syntax**: Rich configuration options with capture directives, conditions, and transformations
- **Multiple Extraction Methods**: Support for JSONPath, regex patterns, and literal value assignments
- **Data Transformations**: Apply transforms like strip, lower, upper, replace to extracted values
- **Error Recovery**: Graceful handling of failed extractions with warning messages and fallback behavior
- **Debugging Support**: Verbose mode shows captured variables and extraction results

#### 📋 **Production-Ready Workflow System**
- **Dry Run Support**: Test complex actions without executing commands (`--dry-run` flag)
- **Rich Output Formatting**: Beautiful step-by-step progress with panels and status indicators
- **Comprehensive Logging**: Detailed execution logs with success/failure tracking
- **Backward Compatibility**: All existing simple actions continue to work unchanged
- **Enterprise Safety**: Confirmation prompts, health checks, and rollback capabilities

#### 🎨 **Enhanced User Experience**
- **Interactive Progress**: Real-time step execution with visual feedback and status updates
- **Flexible Output Modes**: Support for quiet (`--quiet`), compact (`--compact`), and native output modes
- **Command Integration**: Seamless integration with all existing ESCMD commands
- **Help & Documentation**: Comprehensive built-in help system with examples and syntax guides

#### 📚 **Comprehensive Documentation & Examples**
- **Complete User Guide**: In-depth documentation with examples, best practices, and troubleshooting
- **Working Examples**: Pre-configured actions for common operations like rollover, cleanup, and health checks
- **Interactive Demo**: Demonstration script showing all capabilities and syntax options
- **Migration Guide**: Clear instructions for upgrading from simple to enhanced actions

#### 🔧 **Technical Implementation**
- **Modular Architecture**: Clean separation of concerns with dedicated capture, extraction, and execution modules
- **JSON Processing**: Robust JSON parsing with multiple fallback strategies and error handling
- **Template Engine**: Full Jinja2 integration for powerful variable interpolation and condition evaluation
- **Performance Optimized**: Efficient execution with minimal overhead for simple actions
- **Memory Management**: Smart variable scoping and cleanup to prevent memory leaks during long workflows

#### 📊 **Key Capabilities Delivered**
- ✅ **Command Output Capture**: Store any command output in variables
- ✅ **JSON Data Extraction**: Extract specific fields from structured responses
- ✅ **Multi-Step Workflows**: Chain unlimited commands with data dependencies
- ✅ **Conditional Logic**: Smart execution based on previous step results
- ✅ **Safety Features**: Confirmations, health checks, and error recovery
- ✅ **Parameter Support**: Reusable parameterized actions for flexibility
- ✅ **Rich Feedback**: Beautiful progress indicators and result formatting
- ✅ **Production Ready**: Enterprise-grade reliability and error handling

### 🎯 **Impact & Business Value**
- **Workflow Automation**: Eliminates manual multi-step operations with reliable automation
- **Operational Safety**: Reduces human error through built-in safety checks and confirmations
- **Time Savings**: Complex operations like rollover + cleanup now execute as single commands
- **Consistency**: Standardizes administrative procedures across teams and environments
- **Scalability**: Easily extend with custom actions for organization-specific workflows

### 📖 **Documentation Organization**
- Moved enhanced actions documentation to `docs/features/enhanced_actions_guide.md`
- Created implementation summary at `docs/features/enhanced_actions_implementation.md`
- Added interactive demo at `demo/enhanced_actions_demo.py`

---

## [3.2.6] - 2025-09-25

### 🐛 Fixed
#### Rollover Command JSON Format Support
- **Fixed Action Handler Issue**: Resolved error where `rollover` command failed with `--format json` argument
  - **Root Cause**: The `rollover` command was listed as supporting JSON format in the action handler but lacked the `--format` argument in its CLI parser
  - **Solution**: Added `--format` argument to rollover command parser with choices `["json", "table"]` and default `"table"`
  - **Enhanced JSON Output**: Updated `handle_rollover` method to provide clean JSON output when `--format json` is specified
  - **Preserved Rich UI**: Maintained existing Rich-formatted console output for default table format
  - **Action Compatibility**: Fixed `roll-igl` and other rollover actions that automatically add `--format json` for programmatic consumption

### 🔧 Technical Details
- **CLI Parser**: Added missing `--format` argument to `rollover_parser` in `argument_parser.py`
- **Handler Enhancement**: Updated `LifecycleHandler.handle_rollover()` to check format and output appropriate response type
- **Error Handling**: Enhanced error responses to support both JSON and Rich formats based on output preference
- **Backward Compatibility**: All existing rollover functionality preserved with improved format support

## [3.2.5] - 2025-09-24

### 🐛 Fixed
#### Dangling Cleanup - Added support for Environment Reporting
- **Added Environment Support**: Added ability to run: dangling --env {environemnt}
- This makes it easier to not have to predefine groups and just search all clusters in environment.


## [3.2.3] - 2025-09-22

### 🚀 Complete Action Command System - Workflow Automation Platform
escmd now provides a **comprehensive action command system** for automating complex Elasticsearch workflows and standardizing administrative procedures.

#### 📋 **Action Management Commands**
- **Action Listing**: `./escmd.py action list` - Comprehensive action catalog with descriptions
  - **Rich Table Format**: Beautiful table showing action names, descriptions, and required parameters
  - **Parameter Indicators**: `*` symbol clearly marks required parameters for easy identification
  - **Multi-line Descriptions**: Full action descriptions displayed with proper text wrapping
  - **Professional Layout**: Clean, aligned table format using Rich library styling
  - **Parameter Summary**: Shows all parameters with required/optional status at a glance

- **Action Details**: `./escmd.py action show <name>` - Detailed action information
  - **Step-by-Step Breakdown**: Shows all action steps with commands and descriptions
  - **Parameter Documentation**: Complete parameter details with types and requirements
  - **Command Preview**: View exact commands that will be executed
  - **Rich Formatting**: Professional panels with structured information display

- **Action Execution**: `./escmd.py action run <name>` - Execute action sequences
  - **Parameter Support**: `--param-<name> <value>` for dynamic parameterization
  - **Dry-Run Mode**: `--dry-run` for safe preview without execution
  - **Output Control**: Multiple output formats (compact, native, JSON)
  - **Progress Tracking**: Real-time step execution with success/failure reporting
  - **Safety Features**: Built-in confirmations for destructive operations

#### 🎯 **Pre-Configured Action Library**
- **`add-host`**: Add host to allocation exclusions and update templates
  - Parameters: `*host` (hostname without -* suffix)
  - Steps: Update index templates, apply cluster exclusions

- **`remove-host`**: Remove host from allocation exclusions
  - Parameters: `*host` (hostname without -* suffix)
  - Steps: Remove from templates, clear cluster exclusions

- **`maintenance-mode`**: Control cluster maintenance mode
  - Parameters: `*action` (enable/disable)
  - Steps: Conditional exclusion management based on mode

- **`rollover-and-backup`**: Rollover indices and create snapshots
  - Parameters: `*index_pattern`, `*snapshot_name`
  - Steps: Perform rollover, create backup snapshot

- **`index-cleanup`**: Clean up old indices by age and pattern
  - Parameters: `*pattern`, `*days` (with confirmation prompts)
  - Steps: List and delete indices with safety confirmations

- **`health-check`**: Quick health assessment with JSON output
  - Parameters: none
  - Steps: Cluster health check, node listing

#### 🎨 **Advanced Features & Safety**
- **Parameter System**: Support for string, integer, and choice parameter types with validation
- **Conditional Execution**: Steps can be executed based on parameter values using Jinja2 syntax
- **Template Variables**: Full Jinja2 templating support for dynamic command generation
- **Safety Confirmations**: Built-in prompts for destructive operations
- **Rich Output Formatting**: Commands automatically get JSON formatting where supported
- **Progress Tracking**: Real-time execution status with success/failure indicators
- **Error Handling**: Comprehensive error recovery and user feedback

#### 📚 **Dedicated Action Help System**
- **Comprehensive Help**: `./escmd.py help action` - Complete action documentation
  - **Alias Support**: Both `./escmd.py help action` and `./escmd.py help actions` work seamlessly
  - **Rich Documentation**: Professional help panels with overview, commands, examples, and best practices
  - **Interactive Examples**: Step-by-step command examples with real-world use cases
  - **Advanced Features**: Parameter types, conditional steps, template variables, and safety features
  - **Tips & Best Practices**: Guidelines for effective action sequence management
  - **Reference Documentation**: Links to additional guides and command references

#### 🛡️ **Enterprise-Ready Automation**
- **Configuration-Driven**: Actions defined in `actions.yml` for easy customization
- **Standardization**: Consistent procedures for common administrative tasks
- **Error Prevention**: Pre-tested, validated command sequences reduce operational errors
- **Time Savings**: Complex multi-step workflows executed with single commands
- **Audit Trail**: Complete execution logging and progress tracking
- **Flexibility**: Parameter-driven actions adapt to different environments

### 🔧 Technical Implementation
- **Modular Architecture**: Complete action management system with ActionManager and ActionHandler
- **YAML Configuration**: Actions defined in structured YAML format for easy maintenance
- **Jinja2 Integration**: Full templating engine for dynamic parameter substitution
- **Rich Integration**: Leverages existing theme system for consistent styling across all interfaces
- **Argument Parser Enhancement**: Added "action" as alias for "actions" in help topic choices
- **Help System Integration**: Topic aliasing routes "action" requests to comprehensive help content
- **Safety Architecture**: Multi-layer validation with dry-run support and confirmation prompts
- **Welcome Screen Enhancement**: Added proper action command description to static command descriptions for main welcome display

### 🎯 User Experience Improvements
- **Intuitive Command Structure**: Natural action verb usage (`list`, `show`, `run`)
- **Visual Clarity**: Enhanced table formatting makes action information easy to scan and understand
- **Parameter Guidance**: Clear indication of required vs optional parameters reduces command errors
- **Welcome Screen Integration**: Action command now displays proper description in main welcome screen instead of generic "Command: action"
- **Progressive Disclosure**: From simple listing to detailed execution with multiple detail levels
- **Comprehensive Documentation**: Complete action system documentation in easily accessible help format
- **Workflow Standardization**: Pre-built actions for common Elasticsearch administrative tasks

### 📊 **Impact & Benefits**
- **Operational Efficiency**: Reduce complex multi-step procedures to single command execution
- **Error Reduction**: Pre-tested, validated workflows eliminate common administrative mistakes
- **Knowledge Sharing**: Standardized procedures make team onboarding and knowledge transfer easier
- **Compliance**: Consistent execution of maintenance procedures supports audit and compliance requirements
- **Scalability**: Template-driven approach scales across different environments and cluster configurations

## [3.2.0] - 2025-09-18

### 🐛 Fixed
- **ILM Policy Assignment Bug**: Fixed critical error when setting ILM policies to indices
  - **Error**: `'ElasticsearchClient' object has no attribute 'validate_ilm_policy_exists'`
  - **Root Cause**: Missing methods in ElasticsearchClient class after refactoring
  - **Resolution**: Added missing methods from backup implementation:
    - `validate_ilm_policy_exists()` - Validates ILM policy exists before assignment
    - `get_matching_indices()` - Gets indices matching regex pattern with ILM status
    - `set_ilm_policy_for_indices()` - Bulk policy assignment with progress tracking
    - `display_ilm_bulk_operation_results()` - Rich formatted results display
  - **Impact**: `ilm set-policy` command now works properly with validation and progress tracking
  - **Testing**: Verified with command `./escmd.py -l india-xcs ilm set-policy 30-days-default .pro-readonlyrest-audit-xcs-in-2025-08-15`

### 🚀 Enhanced
- **ILM Policy Management**: Complete lifecycle management with enhanced bulk operations
  - **Full Policy Lifecycle**: Create, delete, assign, and remove policies
  - Concurrent processing with configurable max workers
  - Rich progress tracking during operations
  - Comprehensive validation before policy application
  - Professional results display with success/failure/skipped statistics
  - Detailed operation summary with timing information

- **NEW: ILM Policy Creation**: Complete policy creation from JSON definitions
  - **Command**: `./escmd.py ilm create-policy <policy_name> [json_definition]` - Create new ILM policies
  - **Multi-Input Support**: Create from JSON files, inline JSON, or `--file` flag
  - **Intelligent Parsing**: Automatic detection of file paths vs inline JSON
  - **Rich Validation**: Comprehensive JSON structure validation and error handling
  - **Source Tracking**: Displays input method (file path or inline) in results
  - **Phase Display**: Shows configured lifecycle phases in success output
  - **JSON Support**: `--format json` for automation and integration
  - **Help Integration**: Full documentation in help system (`./escmd.py help ilm`)
  - **Examples**:
    - From file: `./escmd.py ilm create-policy my-policy policy.json`
    - With flag: `./escmd.py ilm create-policy my-policy --file policy.json`
    - Inline JSON: `./escmd.py ilm create-policy quick-policy '{"policy":{"phases":{...}}}'`
    - JSON output: `./escmd.py ilm create-policy my-policy policy.json --format json`

- **NEW: ILM Policy Deletion**: Complete policy lifecycle management with safe deletion capabilities
  - **Command**: `./escmd.py ilm delete-policy <policy_name>` - Delete ILM policies permanently
  - **Interactive Confirmation**: Shows policy details (name, phases) before deletion
  - **Automation Support**: `--yes` flag to skip confirmation prompts for scripted operations
  - **Safety Features**: Policy existence validation and detailed error handling
  - **Rich Output**: Beautiful success/error panels with phase information display
  - **JSON Support**: `--format json` for automation and integration
  - **Help Integration**: Full documentation in help system (`./escmd.py help ilm`)
  - **Examples**:
    - Interactive: `./escmd.py ilm delete-policy old-retention-policy`
    - Automated: `./escmd.py ilm delete-policy temp-policy --yes`
    - JSON output: `./escmd.py ilm delete-policy unused-policy --yes --format json`

- **Configuration Enhancement**: Username storage in configuration
  - **Command**: `./escmd.py set-username <username>` - Store default Elasticsearch username in escmd.json
  - **Persistent Storage**: Username is saved in the configuration file and used as default for authentication
  - **Clear Function**: Use `./escmd.py set-username clear` to remove stored username
  - **Show Current**: Use `--show-current` flag to display currently configured username
  - **Integration**: Stored username is automatically used when connecting to clusters requiring authentication

### 🔧 Technical
- **Code Quality**: Restored missing ElasticsearchClient methods from architecture refactoring
- **Error Handling**: Improved ILM operation error handling and user feedback
- **Performance**: Concurrent processing for bulk ILM policy operations

- **ILM Architecture Enhancement**: Complete policy management infrastructure
  - **ES Client Integration**: Added `create_ilm_policy()` and `delete_ilm_policy()` method delegation to SettingsCommands
    - Leveraged existing `SettingsCommands.create_ilm_policy()` and `SettingsCommands.delete_ilm_policy()` methods
    - Consistent delegation pattern following established architecture
  - **Handler Implementation**: New comprehensive policy management methods in LifecycleHandler
    - `_handle_ilm_create_policy()` - Multi-input parsing (file/inline/flag-based), validation, rich output
    - `_handle_ilm_delete_policy()` - Policy existence validation, confirmation prompts, safe deletion
    - Enhanced `handle_ilm()` router with create-policy and delete-policy action handling
  - **CLI Integration**: Enhanced argument parser with create-policy and delete-policy subcommands
    - `create-policy`: Supports positional JSON, `--file` flag, flexible input detection
    - `delete-policy`: Policy name argument, `--yes` confirmation skip, format options
    - Both commands support `--format` for JSON/table output modes
  - **Help System Updates**: Updated ILM help content and subcommand counts (8→9 commands)
    - Updated `cli/help_system.py` subcommand counts in `_get_subcommand_counts()`
    - Enhanced `handlers/help/ilm_help.py` with new commands and examples
    - Updated lifecycle handler's `_show_ilm_help()` with command and example entries
  - **Documentation**: Comprehensive updates to ILM management guides and README
    - Updated `docs/ILM_POLICY_CREATION_FEATURE_SUMMARY.md` to reflect complete policy management
    - Enhanced `docs/commands/ilm-management.md` with create-policy and delete-policy sections
    - Updated main `README.md` with policy creation and deletion examples
    - Added both commands to ILM quick reference and usage workflows
    - Updated subcommand counts and help system integration across multiple files
  - **Safety Implementation**: Comprehensive validation and error recovery systems
    - Policy JSON structure validation with detailed error messages
    - Policy existence validation before deletion attempts
    - Interactive confirmation prompts with policy phase information display
    - File existence validation for policy creation from files
    - Intelligent file vs inline JSON detection with fallback error handling
  - **Theme Consistency**: Rich formatting with existing theme system integration for both operations
    - Beautiful success/error panels following established styling patterns
    - Policy phase visualization with consistent iconography
    - Progress indicators and confirmation prompts using theme colors

### 🎯 **Feature Complete: ILM Policy Management**
escmd now provides **complete ILM policy lifecycle management** with all essential operations:
- ✅ **Policy Creation**: `ilm create-policy` - Create policies from JSON files, inline definitions, or `--file` flag
- ✅ **Policy Deletion**: `ilm delete-policy` - Safely delete policies with interactive confirmation prompts
- ✅ **Policy Assignment**: `ilm set-policy` - Apply policies to indices with bulk operations and progress tracking
- ✅ **Policy Removal**: `ilm remove-policy` - Remove policies from indices by regex pattern or file list
- ✅ **Policy Monitoring**: `ilm status`, `ilm policies`, `ilm policy`, `ilm explain`, `ilm errors`
- 🎨 **Rich User Experience**: Interactive confirmations, input validation, progress tracking, beautiful output formatting
- 🤖 **Automation Ready**: JSON output formats, `--yes` flags, comprehensive error handling, file-based operations

This completes the ILM management feature set, providing operations teams with everything needed for comprehensive Index Lifecycle Management in Elasticsearch environments - from policy creation to deletion, with full automation support and rich interactive experiences.

## [3.1.0] - 2025-09-17

### 🔄 Breaking Changes
- **Health Command Restructure**: Simplified health command interface for better usability
  - **NEW**: `health` command now provides quick status check (previously `health -q`)
  - **NEW**: `health-detail` command provides comprehensive dashboard (previously default `health`)
  - **REMOVED**: `-q/--quick` flag no longer needed - quick mode is now the default
  - **Migration Guide**:
    - Replace `./escmd.py health -q` with `./escmd.py health`
    - Replace `./escmd.py health` with `./escmd.py health-detail`
    - All advanced features (--compare, --group, --style) moved to `health-detail`

### 🚀 Enhanced
- **Quick Health Check**: Fast response time (~1-2 seconds) with essential cluster metrics
  - Clean, focused display of cluster status, nodes, and shard counts
  - Perfect for monitoring scripts and automation
  - JSON output support for programmatic access
- **Detailed Health Dashboard**: Comprehensive 6-panel dashboard with full diagnostics
  - Progress tracking during data collection
  - Recovery status, allocation issues, and performance metrics
  - Snapshot status and master node identification
  - All original styling options preserved (dashboard, classic, comparison, group)

### 🐛 Fixed
- **Status Display**: Fixed health command showing "UNKNOWN" status instead of actual cluster status
  - Now correctly displays GREEN, YELLOW, or RED status with appropriate icons

### 📚 Documentation
- **Updated Examples**: All documentation updated to reflect new command structure
  - Health monitoring guide with new quick vs detailed examples
  - Troubleshooting guide using simplified health command
  - Installation and configuration examples updated
  - Monitoring workflows adapted for new command structure

## [3.0.1] - 2025-09-04

### 🔧 Fixed
- **Dangling Command Bug**: Fixed critical error `'NodeProcessor' object has no attribute 'get_node_id_to_hostname_map'`
  - Corrected method delegation from `NodeProcessor` to `NodesCommands` in `ElasticsearchClient`
  - All dangling indices commands now work properly with hostname resolution
- **Password Management Commands**: Fixed commands to work without Elasticsearch connection
  - Added `store-password`, `list-stored-passwords`, `remove-stored-password`, `clear-session`, `session-info`, `set-session-timeout`, `generate-master-key`, `migrate-to-env-key` to `NO_CONNECTION_COMMANDS`
  - These commands now execute in `handle_special_commands()` without requiring cluster connectivity

### 🚀 Enhanced
- **Encryption Key Management**: Improved user experience for encryption key issues
  - **Fixed misleading message**: Now correctly shows "saved to escmd.json" instead of "escmd.yml"
  - **Enhanced warnings**: Shows count of existing encrypted passwords that will become invalid
  - **Better error messages**: When decryption fails, provides helpful troubleshooting steps:
    - Suggests re-storing passwords with `./escmd.py store-password`
    - Mentions setting `ESCMD_MASTER_KEY` environment variable
    - Offers session clearing as an option
  - **Updated documentation**: Added troubleshooting section for encryption key scenarios

- **Dangling Indices Dry-Run**: Major improvement to `--cleanup-all --dry-run` functionality
  - **New "What Would Be Deleted" table**: Shows detailed preview of indices scheduled for deletion
    - Displays full index names for proper identification
    - Shows more UUID characters (28 chars vs 8 previously) for unique identification
    - Includes node hostnames to understand impact scope
    - Removed "Created" column (always N/A for dangling indices)
  - **Enhanced summary**: Clear statistics on affected indices and nodes
  - **Better guidance**: Shows exact command to run for actual deletion
  - **Consistent theming**: Uses configured table box style and theme colors

### 📚 Documentation
- **Password Management**: Updated troubleshooting documentation
  - Added new error scenarios and solutions
  - Documented master key generation behavior
  - Enhanced troubleshooting for encryption key changes

### 🛡️ Security
- **Password Commands Isolation**: Password management commands no longer require Elasticsearch connection
  - Improves security by allowing password operations in isolated environments
  - Enables password setup before cluster connectivity
  - Reduces attack surface for credential management

### 🔄 Code Quality
- **Method Organization**: Improved delegation patterns in `ElasticsearchClient`
  - Proper separation between `NodeProcessor` and `NodesCommands` responsibilities
  - Better error handling and method resolution
- **Command Routing**: Enhanced special command handling
  - Cleaner separation of connection-required vs connection-free commands
  - Improved error handling for command execution

### 🎨 UI/UX Improvements
- **Dry-Run Visualization**: Significantly improved dry-run output readability
  - Clear table showing exactly what would be affected
  - Better use of terminal space with meaningful columns
  - Consistent color coding and theming
- **Error Messages**: More actionable and helpful error messages
  - Specific suggestions for resolution
  - Context-aware troubleshooting guidance

### 🧪 Testing
- **Validation**: Extensive testing of new functionality
  - Verified dangling command works across different cluster sizes
  - Tested password commands in isolated environments
  - Confirmed dry-run accuracy and clarity

### ⚙️ Technical Details
- **Elasticsearch Compatibility**: Maintained compatibility with ES 7.x and 8.x
- **Rich Console Integration**: Enhanced use of Rich library for better terminal output
- **Progress Tracking**: Maintained existing progress bar functionality
- **Logging**: Preserved comprehensive logging for troubleshooting


## [3.0.0] - 2025-09-02
### 🚀 MAJOR RELEASE - Complete Architecture Refactoring & Modular Design

#### 🏗️ **Complete Modular Architecture Transformation**
- **BREAKING**: Refactored monolithic `esclient.py` into a clean, modular handler-based architecture
- **NEW**: Dedicated handler modules in `handlers/` directory for specialized functionality:
  - `allocation_handler.py` - Shard allocation management and troubleshooting
  - `cluster_handler.py` - Cluster operations and health monitoring
  - `health_handler.py` - Health dashboards and monitoring systems
  - `index_handler.py` - Index management and operations
  - `node_handler.py` - Node information and management
  - `snapshot_handler.py` - Backup and snapshot operations
  - `utility_handler.py` - Utility functions and maintenance tasks
- **ENHANCED**: Clean separation of concerns with single-responsibility classes
- **IMPROVED**: 70%+ code reduction in main files through proper modularization

#### 🎛️ **Advanced Data Processing System**
- **NEW**: Specialized processor modules in `processors/` directory:
  - `index_processor.py` - Index data processing, pattern extraction, filtering
  - `node_processor.py` - Node statistics parsing and role-based filtering
  - `shard_processor.py` - Shard distribution analysis and optimization
  - `allocation_processor.py` - Allocation decision analysis and recommendations
  - `statistics_processor.py` - Data formatting, calculations, and validation
- **ENHANCED**: ~1,000+ lines of processing logic extracted from core client
- **IMPROVED**: Independent, testable data processing components
- **OPTIMIZED**: Efficient data transformation with caching and reuse patterns

#### 🎨 **Professional Display Rendering System**
- **NEW**: Dedicated renderer classes in `display/` directory:
  - `allocation_renderer.py` - Allocation issue visualization and panels
  - `recovery_renderer.py` - Recovery progress tracking and statistics
  - `health_renderer.py` - Health dashboard panels and status displays
  - `snapshot_renderer.py` - Snapshot status and management displays
- **ENHANCED**: Centralized display logic with consistent theming
- **IMPROVED**: ~500+ lines of display code properly organized
- **UNIFIED**: Consistent visual presentation across all commands

#### 🔧 **Enhanced CLI & Command System**
- **REFACTORED**: Complete CLI restructuring with dedicated `cli/` package:
  - `argument_parser.py` - Complete argument parsing logic (300+ lines extracted)
  - `help_system.py` - Beautiful Rich-formatted help display (120+ lines)
  - `special_commands.py` - Non-ES commands with consistent formatting (180+ lines)
- **REDUCED**: Main `escmd.py` reduced from 777 lines to 228 lines (70% reduction)
- **ENHANCED**: Modular, testable CLI components with clean interfaces
- **IMPROVED**: Professional command-line experience with better help system

#### ⚙️ **Dual-File Configuration Architecture**
- **NEW**: Advanced dual-file configuration system separating concerns:
  - `escmd.yml` - Core settings, cluster groups, and password management
  - `elastic_servers.yml` - Server connection definitions only
- **ENHANCED**: Environment-based password resolution with centralized management
- **IMPROVED**: Role-based access control and better security isolation
- **ADDED**: Automated migration tools and comprehensive testing suite
- **FLEXIBLE**: Backward compatibility with single-file configurations

#### 🎨 **Universal Theme System Enhancement**
- **ENHANCED**: Complete theme system applying to all commands and interfaces
- **NEW**: Separate `themes.yml` configuration with unlimited custom themes
- **EXPANDED**: Premium theme collection (Ocean, Midnight, Fire, Cyberpunk variants)
- **INTEGRATED**: Semantic styling system with `StyleSystem` class
- **IMPROVED**: Hot-reload capability and runtime theme switching
- **PROFESSIONAL**: Consistent theming across all handlers and displays

#### 📚 **Comprehensive Documentation Organization**
- **ORGANIZED**: Complete documentation restructure in `docs/` directory:
  - `commands/` - Detailed command references and examples
  - `configuration/` - Setup guides and configuration management
  - `themes/` - Theme development and customization guides
  - `reference/` - Testing, troubleshooting, and changelogs
  - `workflows/` - Real-world usage patterns and automation
- **ENHANCED**: User-facing documentation properly categorized and accessible
- **IMPROVED**: Professional documentation structure with better navigation

#### 🧪 **Enhanced Testing & Development Infrastructure**
- **NEW**: Comprehensive testing framework with unit and integration tests
- **ADDED**: Mock-based testing for reliable CI/CD without ES dependencies
- **ENHANCED**: Test coverage across all new modular components
- **IMPROVED**: Development workflow with proper testing infrastructure
- **DOCUMENTED**: Testing guide and contribution guidelines

#### 🛡️ **Enhanced Error Handling & Reliability**
- **IMPROVED**: Comprehensive error handling across all modules
- **ENHANCED**: Graceful degradation and fallback mechanisms
- **ADDED**: Better error messages with actionable guidance
- **ROBUST**: Connection handling and authentication improvements
- **RELIABLE**: Extensive validation and safety checks

#### 📈 **Performance & Maintainability Improvements**
- **OPTIMIZED**: Significant performance improvements through modular architecture
- **ENHANCED**: Memory efficiency through proper separation of concerns
- **IMPROVED**: Code reusability and maintainability across entire codebase
- **STREAMLINED**: Reduced complexity and cognitive load for developers
- **SCALABLE**: Architecture designed for easy feature extension

#### 🔄 **Migration & Compatibility**
- **MAINTAINED**: 100% backward compatibility for all existing commands
- **PRESERVED**: All command-line interfaces and output formats unchanged
- **ENHANCED**: Improved functionality while maintaining familiar experience
- **SUPPORTED**: Automatic migration tools for configuration updates
- **DOCUMENTED**: Comprehensive migration guides and best practices

#### 🎯 **Key Benefits of v3.0.0**
- **For Users**: Same powerful functionality with improved reliability and performance
- **For Developers**: Clean, modular architecture with 70% less complexity per module
- **For Operations**: Better configuration management and security isolation
- **For Administrators**: Enhanced documentation and easier customization
- **For Future**: Scalable architecture ready for new features and integrations

#### 📊 **Refactoring Statistics**
- **Code Reduction**: Main files 70% smaller through proper modularization
- **Module Creation**: 25+ new specialized modules for focused functionality
- **Documentation**: Complete reorganization with 15+ guides and references
- **Testing**: New comprehensive test suite with mock-based reliability
- **Performance**: Significant improvements through architectural optimization

This major release represents a complete transformation of the ESCMD codebase while maintaining full compatibility and significantly improving maintainability, reliability, and extensibility for future development.

## [2.9.0] - 2025-09-02
### 🎨 Major Enhancement: Integrated Theme Management & Advanced Styling System

#### 🎨 Integrated Theme Switching
 - **NEW**: `set-theme` command for seamless theme switching via CLI
 - **NEW**: `./escmd.py set-theme <theme-name>` integrated command interface
 - **NEW**: `--preview` flag to show theme colors before switching
 - **NEW**: `--no-confirm` flag for automated theme switching
 - **NEW**: Interactive confirmation prompts with current vs new theme display
 - **ENHANCED**: Runtime theme persistence in `escmd.json` state file
 - **NEW**: Priority-based theme loading: State file → Config file → Default fallback
 - **IMPROVED**: Error handling with available theme suggestions for invalid theme names

#### 🎯 Advanced Theme Preview System
 - **NEW**: Rich color preview showing theme-specific styling
 - **NEW**: Border color preview with actual theme border styles
 - **NEW**: Success/Warning/Error color preview with sample text
 - **NEW**: Table header styling preview with theme-appropriate formatting
 - **ENHANCED**: Real-time theme rendering in preview panels
 - **INTEGRATED**: Theme-specific panel borders matching selected theme aesthetic

#### 🔧 Configuration System Enhancements
 - **NEW**: `set_display_theme()` method in ConfigurationManager for persistent theme storage
 - **ENHANCED**: `get_display_theme()` with hierarchical fallback system
 - **NEW**: JSON state file management for runtime theme preferences
 - **IMPROVED**: Theme validation against available themes in `themes.yml`
 - **SEPARATED**: Theme configuration moved from YML to runtime state management
 - **STREAMLINED**: Clean separation between server config (YML) and user preferences (JSON)

#### 🎨 Theme System Architecture
 - **ENHANCED**: Cyberpunk theme with `bright_magenta` borders and heavy table styling
 - **NEW**: Cyberpunk Yellow theme with `bright_yellow` borders and double table styling
 - **NEW**: Configurable table border system with theme-specific box styles
 - **ENHANCED**: Semantic color mapping (success=green, error=red, warning=yellow, info=cyan)
 - **IMPROVED**: Full-width table layouts with `expand=True` for terminal optimization
 - **UNIFIED**: Consistent theming across all handlers and command outputs

#### 🛠️ Command Integration & Routing
 - **NEW**: Theme commands integrated into special command handling (no ES connection required)
 - **NEW**: `handle_set_theme_command()` and `handle_themes_command()` routing functions
 - **ENHANCED**: Updated `NO_CONNECTION_COMMANDS` to include theme operations
 - **FIXED**: `themes` command null pointer exception when ES client unavailable
 - **IMPROVED**: Graceful fallback to default table styling when style system unavailable

#### 💎 User Experience Improvements
 - **NEW**: Beautiful theme gallery display with color-coded theme previews
 - **ENHANCED**: Current active theme indicator in theme listings
 - **NEW**: Theme switching confirmation with "already active" detection
 - **IMPROVED**: Comprehensive error messages with actionable guidance
 - **STREAMLINED**: No more manual YML editing required for theme switching
 - **INTUITIVE**: Simple CLI commands for all theme operations

#### 🎯 Command Line Interface
 - **NEW**: `./escmd.py set-theme cyberpunk` - Direct theme switching
 - **NEW**: `./escmd.py set-theme cyberpunk_yellow --preview` - Preview before switching
 - **NEW**: `./escmd.py set-theme rich --no-confirm` - Automated switching
 - **ENHANCED**: `./escmd.py themes` - Fixed and improved theme gallery display
 - **NEW**: Comprehensive help system for theme commands with usage examples
 - **CONSISTENT**: Unified command structure with other ESCMD utilities

#### 🔒 System Reliability & Architecture
 - **ENHANCED**: Robust theme validation preventing invalid theme application
 - **NEW**: State file creation and management with error handling
 - **IMPROVED**: Null-safe theme loading with multiple fallback layers
 - **FIXED**: Theme command execution without Elasticsearch connection dependency
 - **OPTIMIZED**: Efficient theme loading with caching and reuse patterns
 - **MAINTAINABLE**: Clean separation of concerns between theme logic and ES operations

#### 📋 Technical Implementation
 - **NEW**: Enhanced argument parser with theme command definitions and validation
 - **NEW**: Theme handler methods for set operations and preview generation
 - **ENHANCED**: Configuration manager with JSON state file persistence
 - **IMPROVED**: Error handling with Rich markup compatibility fixes
 - **INTEGRATED**: Theme system integration across all display components
 - **DOCUMENTED**: Comprehensive theme switching workflows and troubleshooting guides

## [2.8.0] - 2025-09-01
### 🎨 Complete Semantic Styling System & Cyberpunk Theme Enhancement

#### 🎨 Semantic Styling Architecture
 - **NEW**: Complete semantic styling system with `StyleSystem` class in `display/style_system.py`
 - **NEW**: `get_semantic_style()` method for dynamic color mapping (success, error, warning, info, primary)
 - **NEW**: `create_semantic_text()` method for themed text object creation
 - **NEW**: `get_table_box()` method for configurable table border styles
 - **ENHANCED**: `create_standard_table()` method with full theme integration and semantic styling
 - **NEW**: Universal theming system applying consistent colors across all commands and handlers

#### ⚡ Enhanced Cyberpunk Themes
 - **ENHANCED**: Cyberpunk theme with `bright_magenta` borders and heavy table box styling
 - **NEW**: Cyberpunk Yellow theme with electric `bright_yellow` borders and double table box styling
 - **NEW**: Configurable `table_box` setting in themes.yml (heavy, double, simple, rounded, none)
 - **IMPROVED**: Enhanced color palette with neon aesthetics and high contrast visibility
 - **UNIFIED**: Consistent semantic color mapping across all cyberpunk theme variants

#### 🏗️ Complete Handler Migration to Semantic Styling
 - **MIGRATED**: Health handler - Complete conversion from hardcoded colors to semantic styling
 - **MIGRATED**: Snapshot handler - Core functionality with themed borders and semantic colors
 - **MIGRATED**: Index handler - Complete with flush/freeze operations using themed styling
 - **MIGRATED**: Datastream handler - Rollover operations and listing with full-width themed tables
 - **MIGRATED**: Dangling handler - Major panels and table displays with semantic styling
 - **MIGRATED**: Node commands - All node-related operations with consistent theming
 - **REMOVED**: All hardcoded color references replaced with semantic style calls

#### 📊 Enhanced Table & Display Systems
 - **NEW**: Configurable table borders with theme-specific box styles across all commands
 - **ENHANCED**: Full-width table layouts with `expand=True` for terminal optimization
 - **IMPROVED**: Consistent table styling using `create_standard_table()` with theme integration
 - **FIXED**: Table border inconsistencies by implementing unified theming approach
 - **ENHANCED**: Datastream listing display with proper themed title panels and borders
 - **OPTIMIZED**: Panel creation with semantic border styles and consistent spacing

#### 🚀 Architecture & Performance Improvements
 - **NEW**: Centralized style system with theme-aware component creation
 - **ENHANCED**: Theme switching capabilities with runtime color updates
 - **IMPROVED**: Memory efficiency through style system reuse patterns
 - **FIXED**: Critical bug with missing `flush_synced_elasticsearch` method implementation
 - **CLEANED**: Removed duplicate datastream code from utility handler
 - **STREAMLINED**: Command routing improvements for datastream operations

#### 🔧 Configuration & Theme Management
 - **ENHANCED**: themes.yml with `table_box` configuration for all existing themes
 - **NEW**: Theme inheritance system allowing easy customization and extension
 - **IMPROVED**: Dynamic theme loading with validation and error handling
 - **INTEGRATED**: Full ElasticsearchClient integration with style system
 - **DOCUMENTED**: Comprehensive theme development guidelines and examples

## [2.7.0] - 2025-08-31
### 📸 Major Enhancement: Comprehensive Snapshot Management System

#### 📸 Snapshot Management Features
 - **NEW**: `snapshots delete` command for safe snapshot deletion with confirmation prompts
 - **NEW**: `snapshots info` command for comprehensive snapshot information display
 - **ENHANCED**: Snapshot deletion requires exact snapshot name for safety
 - **ENHANCED**: Delete confirmation with detailed snapshot information display
 - **NEW**: `--force` flag for automated deletion workflows
 - **ENHANCED**: Complete snapshot metadata display including UUID, version, timestamps
 - **NEW**: Repository information integration showing type, settings, and configuration

#### 🎨 UI/UX Improvements
 - **FIXED**: Corrupted Unicode characters (�) in Legend & Quick Actions panel titles
 - **ENHANCED**: Legend & Quick Actions panel with better visual design and spacing
 - **IMPROVED**: 50/50 width distribution for Legend and Quick Actions columns
 - **ENHANCED**: Full terminal width utilization for better visual balance
 - **REDESIGNED**: Snapshot info display from scattered 2x2 grid to unified single panel
 - **INTEGRATED**: All snapshot information contained within one cohesive panel
 - **IMPROVED**: Better visual hierarchy with consistent indentation and spacing

#### 🔧 Technical Enhancements
 - **NEW**: `delete_snapshot()` method in ES client with version compatibility
 - **NEW**: `get_snapshot_info()` method for comprehensive snapshot data retrieval
 - **ENHANCED**: Repository information integration with snapshot details
 - **IMPROVED**: Error handling for non-existent snapshots and repositories
 - **NEW**: JSON output support for snapshot info command
 - **ENHANCED**: Timestamp formatting with proper timezone display
 - **INTEGRATED**: Duration calculations with human-readable formats

#### 🎯 Command Line Interface
 - **NEW**: `./escmd.py snapshots delete <snapshot_name> [--repository REPO] [--force]`
 - **NEW**: `./escmd.py snapshots info <snapshot_name> [--format {json,table}] [--repository REPO]`
 - **ENHANCED**: Comprehensive help system for all snapshot commands
 - **IMPROVED**: Better error messages with actionable guidance
 - **CONSISTENT**: Unified command structure across all snapshot operations

#### 🛡️ Safety & Validation
 - **ENHANCED**: Pre-deletion validation ensures snapshot exists before attempting deletion
 - **NEW**: Detailed confirmation panel showing snapshot details before deletion
 - **IMPROVED**: Clear success/failure feedback with appropriate styling
 - **ENHANCED**: Repository configuration validation for all snapshot operations
 - **SAFE**: Exact name matching prevents accidental deletions

## [2.6.0] - 2025-08-30
### 🎨 Major Enhancement: Universal Theme System & Documentation Organization

#### 🎨 Universal Theme System
 - **NEW**: Complete theme system applying to all commands and help menus
 - **NEW**: Separate `themes.yml` configuration file for unlimited custom themes
 - **NEW**: Built-in themes: Rich (white borders), Plain (black borders), Cyberpunk (bright magenta)
 - **NEW**: Premium themes: Ocean (deep sky blue), Midnight (slate blue), Fire (orange red)
 - **NEW**: Theme categories: panel_styles, help_styles, health_styles, status_styles, etc.
 - **NEW**: Theme switcher utility (`python3 theme_switcher.py <theme>`)
 - **ENHANCED**: Help system (`--help`) now respects theme configuration
 - **ENHANCED**: All panels throughout application use consistent theme styling
 - **ENHANCED**: Hot-reload capability - switch themes without restart
 - **COMPATIBLE**: Backward compatibility with legacy theme_styles in main config

#### 📚 Documentation Organization
 - **MOVED**: Theme guides relocated to `docs/themes/` directory
 - **NEW**: Comprehensive theme documentation with examples and color references
 - **NEW**: Universal Theme System Guide with implementation details
 - **ORGANIZED**: Better documentation structure for maintainability

#### 🔧 Configuration Improvements
 - **SEPARATED**: Theme configuration moved from `elastic_servers.yml` to dedicated `themes.yml`
 - **NEW**: `themes_file` setting for custom theme file location
 - **ENHANCED**: Theme loading with fallback support for both new and legacy configurations
 - **FLEXIBLE**: Support for relative and absolute theme file paths

## [2.5.0] - 2025-08-29
### 🏥 Major Enhancement: Advanced Group Health Monitoring & Performance Optimization

#### 🚀 Group Health Dashboard Enhancements
 - **NEW**: Enhanced group health display (`./escmd.py health --group <name>`) with comprehensive cluster metrics
 - **NEW**: Added ES Version, Primary Shards, Total Shards, Unassigned Shards, and Health Percentage columns
 - **NEW**: JSON format support for group health (`./escmd.py health --group <name> --format json`)
 - **FIXED**: Group health connection issues - corrected ElasticsearchClient parameter passing bug
 - **ENHANCED**: Group health now shows same detailed information as individual `health` command
 - **PROFESSIONAL**: Color-coded status indicators (🟢 GREEN, 🟡 YELLOW, 🔴 RED) for quick visual assessment

#### 📊 JSON API Support
 - **NEW**: Machine-readable JSON output for automation and monitoring integration
 - **NEW**: Structured cluster health data with comprehensive error handling
 - **NEW**: Error field tracking for troubleshooting cluster connectivity issues
 - **COMPATIBLE**: Maintains backward compatibility with existing table format

#### 📈 Enhanced Version Command with Dynamic Statistics
 - **NEW**: Dynamic command statistics table showing categorized command counts
 - **NEW**: Real-time subcommand counting for complex commands (ILM, allocation, etc.)
 - **NEW**: Features & Capabilities panel with system information
 - **ENHANCED**: Version display now shows Python version, platform, and script location
 - **SMART**: Automatically discovers available commands from argument parser
 - **COMPREHENSIVE**: Shows 57 total commands across 8 categories with proper subcounting

#### 🎨 Beautiful Welcome Screen (No Arguments) - DYNAMIC
 - **NEW**: Stunning welcome screen when running `./escmd.py` without arguments
 - **DYNAMIC**: Real-time command discovery - automatically detects all available commands
 - **SELF-UPDATING**: Command counts and categories update automatically when new commands are added
 - **ORGANIZED**: Quick start commands table with most common operations
 - **CATEGORIZED**: Dynamic command categories overview with live counts and examples
 - **RESPONSIVE**: Adaptive layout for different terminal widths (side-by-side vs stacked)
 - **HELPFUL**: Pro tips section with usage hints and best practices
 - **PROFESSIONAL**: Rich terminal UI with emojis, colors, and proper alignment
 - **GUIDANCE**: Clear navigation to help system and version statistics
 - **INTELLIGENT**: Falls back to static data if dynamic discovery fails

#### ⚡ Performance Optimizations
 - **OPTIMIZED**: Health dashboard loading time reduced from minutes to ~8 seconds
 - **NEW**: Fast snapshot statistics gathering with `get_snapshot_stats_fast()` method
 - **NEW**: Optimized node information retrieval with `get_nodes_fast()` method
 - **ENHANCED**: 5-step progress tracking for dashboard loading with time estimates

#### 🔧 Snapshot Repository Detection
 - **FIXED**: Snapshot information display for server8 and other clusters
 - **ENHANCED**: Support for both `repository` and `elastic_s3snapshot_repo` configuration keys
 - **IMPROVED**: Automatic repository detection and fallback logic

#### 🛠️ Configuration & Authentication
 - **ENHANCED**: Password resolution system with environment-based authentication
 - **IMPROVED**: Multi-cluster configuration support with proper state file handling
 - **DEBUGGED**: Configuration manager initialization for group operations

### 📈 Impact Summary
 - **Dashboard Performance**: 90%+ improvement in loading times
 - **Group Monitoring**: Complete multi-cluster health visibility
 - **API Integration**: JSON support enables programmatic access
 - **Data Completeness**: All health metrics now available in group view
 - **Error Handling**: Comprehensive error tracking and reporting

## [2.4.0] - 2025-08-27
### 🏥 Major Feature: Comprehensive Cluster Health Monitoring
#### 🔍 Advanced Cluster Health Checks
 - **NEW**: Added `cluster-check` command for comprehensive cluster health monitoring
 - **NEW**: ILM (Index Lifecycle Management) error detection and reporting
 - **NEW**: Detection of indices without ILM policies attached (unmanaged indices)
 - **NEW**: Large shard size monitoring with configurable thresholds (default: >50GB)
 - **ENHANCED**: Multi-category health assessment with detailed reporting
 - **COMPREHENSIVE**: Coverage analysis showing managed vs unmanaged indices
 - **INTELLIGENT**: Automatic ILM API compatibility detection with graceful fallbacks

#### 📊 Rich Formatted Health Reports
 - **NEW**: Professional multi-panel dashboard with color-coded status indicators
 - **NEW**: ILM Coverage Overview showing total indices, managed count, error count, and unmanaged count
 - **NEW**: Detailed tables for ILM errors with policy names, phases, actions, and error reasons
 - **NEW**: Dedicated table for indices without ILM policies for governance visibility
 - **NEW**: Large shard size reporting with shard-level details (index, shard number, type, size)
 - **ENHANCED**: Smart recommendations based on detected issues
 - **PROFESSIONAL**: Consistent Rich library styling with bordered panels and full-width tables

#### ⚙️ Flexible Configuration & Output
 - **NEW**: Added `--format` parameter supporting both table (default) and JSON output modes
 - **NEW**: Added `--max-shard-size` parameter for configurable shard size thresholds
 - **NEW**: Added `--show-details` flag for extended information display
 - **NEW**: Added `--skip-ilm` flag for clusters without ILM support or older Elasticsearch versions
 - **ROBUST**: JSON output with proper control character sanitization for automation compatibility
 - **RELIABLE**: Comprehensive error handling for API compatibility issues

#### 🔧 Technical Implementation
 - **ADDED**: `check_ilm_errors()` method for detecting ILM step errors via `/_all/_ilm/explain` API
 - **ADDED**: `check_no_replica_indices()` method for replica configuration validation
 - **ADDED**: `check_large_shards()` method for shard size monitoring via `/_cat/shards` API
 - **ADDED**: `display_cluster_health_report()` method for comprehensive formatted output
 - **ADDED**: JSON sanitization for problematic Elasticsearch stack traces and control characters
 - **ENHANCED**: Progress tracking with real-time status updates during health checks
 - **MAINTAINED**: Full backward compatibility with existing escmd command structure

#### 🎯 Use Cases & Benefits
 - **OPERATIONS**: Daily cluster health monitoring and issue identification
 - **GOVERNANCE**: ILM policy coverage analysis and compliance reporting
 - **CAPACITY**: Proactive shard size monitoring for performance optimization
 - **AUTOMATION**: JSON output support for integration with monitoring systems
 - **TROUBLESHOOTING**: Detailed error reporting with retry counts and failure reasons

### 🔧 Major Feature: Dual-Mode Replica Management System
#### 🚀 Integrated Health Check + Replica Fixing
 - **NEW**: Added `--fix-replicas` parameter to `cluster-check` command for seamless health-to-fix workflow
 - **NEW**: Automatic targeting of indices with 0 replicas discovered during health assessment
 - **NEW**: Professional workflow integration with clear visual progression from assessment to fixing
 - **NEW**: Added `--dry-run` and `--force` parameters for replica fixing operations
 - **COMPREHENSIVE**: Maintains complete cluster health context while adding replica fixing capability
 - **INTELLIGENT**: Uses existing `check_no_replica_indices()` results for targeted operations
 - **SEAMLESS**: Health assessment → Issue identification → Automated fixing in single command

#### ⚙️ Standalone Replica Management
 - **NEW**: Added dedicated `set-replicas` command for advanced replica operations
 - **NEW**: Multiple targeting modes: `--indices`, `--pattern`, `--no-replicas-only` filters
 - **NEW**: Flexible replica count setting with `--count` parameter (supports any replica count)
 - **NEW**: Pattern-based operations for bulk replica management (e.g., `--pattern "logs-*"`)
 - **NEW**: Advanced filtering capabilities for precise index selection
 - **GRANULAR**: Complete control over replica count changes for specific use cases
 - **AUTOMATION**: Dedicated interface optimized for scripts and maintenance workflows

#### 🛡️ Safety & Validation Features
 - **COMPREHENSIVE**: Pre-flight validation checks index existence and current settings
 - **SAFE**: Complete dry-run mode for both integrated and standalone operations
 - **INTERACTIVE**: Confirmation prompts with detailed impact information (bypassable with `--force`)
 - **ROBUST**: Graceful error handling for API failures, network issues, and invalid operations
 - **PLANNED**: Comprehensive planning engine shows current → target replica counts before execution
 - **VALIDATED**: Index existence verification and settings validation before any changes

#### 📊 Rich User Experience & Progress Tracking
 - **PROFESSIONAL**: ReplicaManager class with planning, execution, and display methods
 - **VISUAL**: Real-time progress bars with visual progress tracking during execution
 - **FORMATTED**: Full-width tables with color-coded status indicators and professional styling
 - **INFORMATIVE**: Executive summary panels and detailed recommendations
 - **STATUS**: Live status updates for each index during replica update operations
 - **RESULTS**: Comprehensive success/failure reporting with execution metrics

#### 🔄 Output Formats & Automation Support
 - **JSON**: Complete JSON export for both planning and execution results
 - **STRUCTURED**: Machine-readable output format for monitoring system integration
 - **AUTOMATION**: Force mode for non-interactive script execution
 - **MONITORING**: Structured error reporting for automated failure handling
 - **CONSISTENT**: Maintains escmd's established Rich library formatting standards
 - **FLEXIBLE**: Both table (default) and JSON output modes for different use cases

#### 🔧 Technical Implementation
 - **ADDED**: `ReplicaManager` class in `esclient.py` with comprehensive replica management capabilities
 - **ADDED**: `plan_replica_updates()` method for safe planning and validation
 - **ADDED**: `execute_replica_updates()` method with progress tracking and error handling
 - **ADDED**: `display_update_plan()` and `display_update_results()` methods for rich formatting
 - **ADDED**: `handle_set_replicas()` command handler for standalone operations
 - **ENHANCED**: `handle_cluster_check()` with integrated replica fixing workflow
 - **INTEGRATED**: Seamless integration with existing authentication and configuration systems
 - **MAINTAINED**: Full backward compatibility with all existing escmd functionality

#### 🎯 Use Cases & Workflows
 - **MAINTENANCE**: Routine replica fixes discovered during daily health checks
 - **OPERATIONS**: Bulk replica management for index lifecycle operations
 - **AUTOMATION**: Script-friendly replica management with JSON output and force mode
 - **GOVERNANCE**: Systematic replica count standardization across index patterns
 - **PRODUCTION**: Safe replica fixing with multiple validation layers and confirmation prompts
 - **MONITORING**: Integration with monitoring systems via structured JSON output

#### 💡 Command Examples
```bash
# Integrated health check + replica fixing
./escmd.py cluster-check --fix-replicas 1 --dry-run
./escmd.py cluster-check --fix-replicas 1 --force

# Standalone replica management
./escmd.py set-replicas --no-replicas-only --dry-run
./escmd.py set-replicas --pattern "logs-*" --count 2
./escmd.py set-replicas --indices "index1,index2" --count 1
```

## [2.3.0] - 2025-01-21
### ✨ Enhanced Snapshot Management
#### 📸 Comprehensive Snapshot Status Checking
 - **NEW**: Added `snapshots status` command for detailed snapshot status information
 - **NEW**: Support for checking specific snapshot job status with command: `./escmd.py -l <cluster> snapshots status <snapshot_name>`
 - **ENHANCED**: Rich formatted display with color-coded status indicators (✅ SUCCESS, ⏳ IN_PROGRESS, ❌ FAILED, ⚠️ PARTIAL)
 - **DETAILED**: Multi-panel layout showing snapshot information, statistics, progress, included indices, and failure details
 - **FLEXIBLE**: Support for both table and JSON output formats via `--format` parameter
 - **INTELLIGENT**: Repository auto-detection from cluster configuration with `--repository` override option
 - **COMPREHENSIVE**: Real-time progress tracking for in-progress snapshots with shard-level statistics
 - **INFORMATIVE**: Detailed failure analysis with index and shard-specific error information
 - **PROFESSIONAL**: Consistent styling with existing escmd interface using Rich library panels and tables
 - **ROBUST**: Comprehensive error handling for missing snapshots, repositories, and API errors

#### 🔧 Technical Enhancements
 - **ADDED**: `get_snapshot_status()` method in ElasticsearchClient for snapshot information retrieval
 - **ADDED**: `display_snapshot_status()` method for formatted output with professional presentation
 - **ADDED**: `_handle_snapshot_status()` command handler with full argument processing
 - **ENHANCED**: Extended snapshot command framework to support multiple actions (list, status)
 - **IMPROVED**: Repository validation and configuration lookup with helpful error messages
 - **MAINTAINED**: Full backward compatibility with existing `snapshots list` functionality

## [2.2.0] - 2025-08-20
### 🔥 Major Feature: Enhanced Dangling Index Management
#### 🚀 Advanced Bulk Cleanup Operations
 - **NEW**: Added `--cleanup-all` flag for automatic deletion of all dangling indices in a single operation
 - **NEW**: Added `--dry-run` mode to preview operations safely without making any changes
 - **NEW**: Added comprehensive progress tracking with real-time progress bars and ETA calculations
 - **NEW**: Added interactive confirmation prompts with detailed impact warnings for destructive operations
 - **ENHANCED**: Bulk processing with efficient handling of multiple dangling indices simultaneously
 - **SAFETY**: Pre-flight checks validate cluster state before operations begin

#### ⚡ Advanced Retry Logic & Error Recovery
 - **NEW**: Added `--max-retries` parameter for configurable retry attempts (default: 3)
 - **NEW**: Added `--retry-delay` parameter for configurable delay between retries (default: 5 seconds)
 - **NEW**: Added `--timeout` parameter for configurable operation timeouts (default: 60 seconds)
 - **INTELLIGENT**: Automatic retry for transient failures (timeouts, network issues, resource conflicts)
 - **ROBUST**: Graceful handling of partial failures with detailed error tracking
 - **RESILIENT**: Enhanced error recovery with specific handling for different failure types

#### 📊 Professional Logging & Reporting
 - **NEW**: Added `--log-file` parameter for optional file logging with structured output
 - **ENHANCED**: Multi-destination logging with console and file output support
 - **DETAILED**: Comprehensive operation summaries with success/failure statistics and timing
 - **AUDIT**: Complete audit trail of all operations for compliance and troubleshooting
 - **STRUCTURED**: Rich formatted output with color-coded status indicators and progress tracking

#### ⚙️ Configuration Management
 - **NEW**: Added `dangling_cleanup` configuration section in `elastic_servers.yml`
 - **CONFIGURABLE**: Default settings for max_retries, retry_delay, timeout, logging level
 - **FLEXIBLE**: Per-cluster configuration support with global defaults
 - **PRODUCTION**: Production-ready settings with confirmation requirements and progress bars

#### 🔧 Enhanced Command Options
 - **NEW**: `--yes-i-really-mean-it` flag extended to bulk operations for automated workflows
 - **IMPROVED**: Enhanced help system with comprehensive usage examples and safety guidelines
 - **ENHANCED**: Rich formatted progress indicators with completion estimates and status updates
 - **PROFESSIONAL**: Enterprise-grade error messages with specific recovery guidance

#### 🛡️ Production Safety Features
 - **ROBUST**: Comprehensive error handling with partial success tracking and graceful degradation
 - **SAFE**: Interactive confirmation system requiring explicit user acknowledgment
 - **MONITORED**: Real-time operation monitoring with detailed progress feedback
 - **VALIDATED**: Pre-operation validation checks and post-operation result verification
 - **RECOVERABLE**: Detailed logging and audit trails for operational transparency

#### 📈 Performance & User Experience
 - **FAST**: Optimized bulk operations with parallel processing capabilities
 - **VISUAL**: Rich console formatting with progress bars, panels, and status indicators
 - **INTUITIVE**: Clear command structure with comprehensive help and usage examples
 - **RELIABLE**: Extensive testing and validation across different cluster configurations
 - **SCALABLE**: Handles large numbers of dangling indices efficiently with progress tracking

## [2.1.0] - 2025-08-12
### 🐛 Bug Fixes
#### Fixed Snapshot Repository Access & Python Version Compatibility
 - **FIXED**: Corrected Elasticsearch snapshot repository method call in `list_snapshots()`
 - **NEW**: Added version compatibility helper `_call_with_version_compatibility()` for handling API differences
 - **IMPROVED**: Automatic fallback between newer (`repository=`) and older (`name=`) parameter formats
 - Resolves error: "SnapshotClient.get_repository() got an unexpected keyword argument 'name'"
 - **COMPATIBILITY**: Works with both Python 3.12.8 and 3.13.3 with different elasticsearch-py library versions
 - **IMPACT**: Fixes repository access for all clusters with snapshot repositories (e.g., server8-repo)
 - **FUTURE-PROOF**: Version compatibility helper can be extended to other Elasticsearch API methods if needed

## [2.0.8] - 2025-01-11
### 🔍 Dangling Indices Detection & Management
#### ⚠️ New Dangling Indices Command with Deletion Support
 - **NEW**: Added `dangling` command to detect, analyze, and delete dangling indices in the cluster
 - **NEW**: Added UUID-based deletion capability with `--delete` flag for targeted dangling index removal
 - **NEW**: Added hostname resolution for node IDs, showing actual hostnames instead of cryptic node IDs
 - **PERFORMANCE**: Optimized hostname resolution to avoid multiple API calls - now gets node mapping once for all indices
 - Implemented comprehensive dangling indices detection using Elasticsearch's `/_dangling` API
 - Created enhanced multi-panel display system:
   - **📊 Statistics Panel**: Shows total dangling indices, affected nodes, cluster nodes, and oldest creation date
   - **ℹ️ Information Panel**: Explains what dangling indices are, common causes, and implications
   - **⚠️ Detailed Table**: Lists index UUIDs, creation dates, hostnames, and node counts with color coding
   - **🚨 Warning Panel**: Provides critical alerts about data accessibility and recovery requirements
   - **🔧 Recovery Options**: Shows available actions (delete command, import, backup, log analysis)
 - Added intelligent color coding: Yellow (multiple nodes), Red (single node), Dim (no nodes)
 - Implemented success case handling with positive messaging when no dangling indices found
 - Added pure JSON output support for automation and integration (--format json)
 - Enhanced user experience with hostname display for better operational visibility

#### 🗑️ Dangling Index Deletion Capabilities
 - **NEW**: UUID parameter support for targeting specific dangling indices for deletion
 - **NEW**: `--delete` flag enables destructive operations with safety confirmations
 - **Safety Features**:
   - Interactive confirmation prompt requiring partial UUID match (DELETE <short-uuid>)
   - Detailed pre-deletion information display with affected nodes count
   - Comprehensive warning panels about data loss and irreversible operations
   - Error validation and UUID verification before deletion attempts
   - **NEW**: `--yes-i-really-mean-it` flag for automated deletion without confirmation prompts (use with extreme caution)
 - **Enhanced User Experience**:
   - Rich formatted deletion progress with status indicators
   - Success/failure panels with clear operation results
   - Post-deletion next steps guidance and related commands
   - Keyboard interrupt handling for user cancellation
   - Automated deletion support for scripting and automation scenarios
 - **Error Handling**: Professional error panels with troubleshooting guidance and connectivity checks
 - **Performance Enhancement**: Fixed hostname resolution performance issue that caused hanging on large clusters
 - Usage: `./escmd.py dangling [<uuid> --delete [--yes-i-really-mean-it]] [--format json]`

#### 📝 Command Integration & Help System
 - Added dangling command to main help system in "Index Operations" section
 - Integrated dangling command into argument parser with UUID parameter and delete flag
 - Updated help text to reflect both listing and deletion capabilities
 - Added command to no-preprocessing list for optimal performance
 - Updated command handler execute() method to route dangling commands properly
 - Enhanced esclient.py with `list_dangling_indices()` method using low-level transport

#### 🎯 Enhanced JSON Output Handling
 - **IMPROVED**: Fixed JSON format output to return pure JSON without Rich formatting
 - Optimized JSON output flow to skip all UI elements, titles, and status messages
 - Ensures clean pipeable output compatible with tools like `jq`, `grep`, and shell scripts
 - JSON output now executes immediately after data retrieval for maximum efficiency

## [2.0.7] - 2025-08-06
### 🛠️ Minor Bug Fixes & Optimizations
 - Updated version number and release date
 - Various small improvements and optimizations

## [2.0.6] - 2025-07-28
### 🗂️ Datastreams Management
 - Added new `datastreams` command to list all datastreams in the cluster
 - Added ability to show detailed information for a specific datastream by passing its name
 - Added `--delete` option to safely delete datastreams with confirmation prompts
 - Delete operation includes safety checks: datastream verification, backing indices warning, and required confirmation text
 - Interactive deletion requires typing 'DELETE <datastream_name>' to confirm the irreversible operation
 - Supports both JSON and table output formats
 - Table format displays datastream name, status, template, ILM policy, generation, and indices count
 - Detail view shows comprehensive datastream metadata and lists all backing indices
 - Updated help system to include datastreams command in maintenance operations section
 - Added examples to README for datastream operations including deletion

## [2.0.5] - 2025-07-27
### 🔄 Flush Command Auto-Retry Enhancement
#### ⚠️ Comprehensive Shard Colocation Detection
 - The `flush` command now automatically retries failed shards with a 10-second delay, up to 10 times (11 total attempts).
 - Retries continue until all shards are successfully flushed or the maximum number of attempts is reached.
 - Real-time visual feedback is provided for each retry attempt, including countdowns and progress panels.
 - Success after retries is celebrated with a dedicated panel; persistent failures after all retries are clearly reported with troubleshooting guidance.
 - Operation summary and details panels now include retry statistics and final status.
 - This enhancement greatly improves the reliability and robustness of flush operations, especially in clusters with transient issues.
 - Added new `shard-colocation` command to identify availability risks in index shard distribution
 - Implemented detection of indices with primary and replica shards on the same physical host
 - Created comprehensive analysis engine with risk assessment (LOW/MEDIUM/HIGH/CRITICAL levels)
 - Added detailed colocation results display with affected indices, problematic shard groups, and risk percentages
 - Integrated visual status indicators with color-coded risk levels and severity icons
 - Enhanced display with consolidated title panel showing comprehensive statistics (analyzed indices, affected indices, shard groups, issues)
 - Added regex pattern filtering support for targeted analysis (./escmd.py shard-colocation <pattern>)
 - Implemented recommendation engine with actionable guidance for resolving allocation issues
 - Added complete JSON format support for automation and integration (--format json)
 - Created streamlined success display when no colocation issues are found

#### ⚖️ Enhanced Allocation Explain System
 - **NEW**: Added dedicated `allocation explain` subcommand for comprehensive shard allocation analysis
 - Implemented enhanced allocation explanation with node decision analysis and barrier identification
 - Created rich multi-panel display system:
   - **✅ Current Allocation Panel**: Shows allocated node, node ID, weight ranking, and allocation status
   - **📊 Summary Panel**: Displays nodes evaluated, allocation possibilities, recommendations, and primary barriers
   - **🖥️ Node Decisions Table**: Comprehensive table showing all nodes with decisions (✅ Yes/❌ No/⏸️ Throttle), weight rankings, primary reasons, and addresses
   - **🚫 Barriers Analysis**: When issues exist, shows allocation barriers with impact analysis and severity levels
   - **🚀 Quick Actions Panel**: Related commands and investigation options
 - Enhanced allocation explanation engine with comprehensive context gathering (cluster nodes, index settings, shard information)
 - Added smart auto-detection of primary vs replica shards with manual override option (--primary flag)
 - Implemented shard number specification support (--shard/-s flag, default: 0)
 - Added detailed error handling with professional error panels for missing indices/shards
 - Complete JSON export support for automation and detailed analysis
 - Usage: `./escmd.py allocation explain <index> [--shard N] [--primary] [--format json]`

#### 🏥 Health Dashboard Integration for Allocation Issues
 - **NEW**: Added automatic allocation issue detection in health dashboard
 - Created allocation issues panel that appears when unassigned shards are detected
 - Implemented severity assessment system (Minor/Moderate/Critical) based on number of unassigned shards
 - Added real-time statistics: unassigned shard count, impact percentage, active shards percentage
 - Integrated example problematic index display with quick action recommendations
 - Enhanced health dashboard layout to conditionally show allocation issues panel next to snapshots
 - Smart display logic: panel only appears when issues exist, maintaining clean interface when healthy
 - Color-coded severity indicators: ⚠️ Yellow (Minor), 🟠 Orange (Moderate), 🔴 Red (Critical)

#### 🎨 Enhanced User Interface & Configuration
 - **NEW**: Added configurable Legend/Quick Actions panels for indices command
 - Implemented `show_legend_panels` setting in elastic_servers.yml (default: false for cleaner display)
 - Enhanced ConfigurationManager with `get_show_legend_panels()` method for legend panel control
 - Created conditional legend and quick actions display based on configuration settings
 - Updated indices command to respect legend panel configuration with fallback error handling

#### 🐛 Bug Fixes & UI Improvements
 - **FIXED**: Resolved duplicate output issue in `indices` command that was displaying content twice
 - **FIXED**: Enhanced "NEEDS ATTENTION" text wrapping in Performance panel by increasing column and panel widths
 - **FIXED**: Improved snapshots panel layout by removing empty row when repository is not configured
 - **ENHANCED**: Removed "-master" suffix from master node display name in health screen for cleaner appearance
 - **IMPROVED**: Streamlined shard colocation display by moving analysis summary into main title panel
 - **ENHANCED**: Better error handling and user feedback across all new allocation features

#### 📖 Command Reference
```bash
# Shard Colocation Analysis
./escmd.py shard-colocation                    # Analyze all indices
./escmd.py shard-colocation "logs-*"           # Filter by pattern
./escmd.py shard-colocation --format json      # JSON output

# Enhanced Allocation Explain
./escmd.py allocation explain my-index          # Explain shard 0 allocation
./escmd.py allocation explain my-index --shard 2 # Explain specific shard
./escmd.py allocation explain my-index --primary # Force primary analysis
./escmd.py allocation explain my-index --format json # JSON output

# Configuration
# Add to elastic_servers.yml settings section:
show_legend_panels: true   # Enable legend panels (default: false)
```

## [2.0.3] - 2025-07-23
### ✨ Enhanced Snapshots, Allocation, Settings, ILM Support & Command Improvements
#### 📦 Comprehensive Snapshots Visual Upgrade
 - Enhanced `snapshots list` command with complete Rich formatting and multi-panel layout
 - Added statistics overview panel with total snapshots, success/failure counts, and indices summary
 - Implemented enhanced table with emoji column headers (📸 🎯 📅 ⏱️ 📊 ❌) and state icons
 - Added color-coded state indicators (✅ Success, ⏳ Progress, ❌ Failed, ⚠️ Partial) with row styling
 - Created legend panel explaining snapshot states and quick actions panel with usage examples
 - Integrated side-by-side bottom panels following the 2.0+ visual design pattern
 - Enhanced statistics calculation with comprehensive snapshot analysis and filtering info
 - Improved professional appearance with proper spacing, padding, and panel alignment

#### ⚖️ Comprehensive Allocation Management Upgrade
 - Enhanced `allocation` command with complete Rich formatting and four-panel layout system
 - Added comprehensive statistics overview with status, node counts, and exclusion tracking
 - Implemented allocation status panel (📊) with enable/disable state and shard movement info
 - Created configuration details panel (⚙️) showing current settings and custom configurations
 - Added excluded nodes panel (❌) with numbered list or success message if none excluded
 - Integrated quick actions panel (🚀) with all available allocation commands and examples
 - Enhanced success/error messages with color-coded Rich message boxes and detailed feedback
 - Added comprehensive JSON format support (`--format json`) for all allocation subcommands
 - Improved visual indicators: ✅ Enabled, ⚠️ Disabled, 🔄 Movement, 🔒 Restricted, ❌ Excluded
 - Professional two-column layout with proper spacing and consistent panel styling

#### ⚙️ Comprehensive Cluster Settings Upgrade
 - Enhanced `settings` command with complete Rich formatting and five-panel layout system
 - Added comprehensive cluster overview panel (📊) with status, nodes, and custom settings count
 - Implemented allocation settings panel (⚖️) showing allocation status and excluded nodes summary
 - Created security & configuration panel (🔐) with SSL, authentication, and certificate verification status
 - Added settings breakdown panel (📈) with transient/persistent counts and category analysis
 - Integrated quick actions panel (🚀) with related commands and navigation options
 - Enhanced detailed settings table (📋) with formatted values, setting types, and organized display
 - Maintains original detailed cluster settings table with improved Rich formatting and value formatting
 - Added smart value display for booleans (✅/❌), large numbers (comma formatting), and long strings
 - Professional multi-column layout combining both overview panels and detailed settings table
 - Enhanced settings analysis with recursive counting of nested configuration values
 - Improved visual organization of complex cluster settings into logical, digestible categories
 - Maintains full JSON format support (`--format json`) for programmatic access

#### 📋 Comprehensive Index Lifecycle Management (ILM) Support
 - Added ILM overview panel to `settings` command showing status, policies, and phase distribution
 - Created dedicated `ilm` command with four subcommands for comprehensive ILM management
 - Implemented `ilm status` with multi-panel display (📊 Status, 🔄 Phase Distribution, 🚀 Actions)
 - Added `ilm policies` command showing policy matrix with phase coverage (🔥🟡🧊❄️🗑️)
 - Created `ilm policy <name>` command for detailed single policy configuration and usage analysis
 - Created `ilm explain <index>` for detailed index lifecycle analysis and error detection
 - Implemented `ilm errors` showing indices with ILM errors in organized table format
 - Enhanced ILM data collection with phase counting, error detection, and policy analysis
 - Added comprehensive error handling for clusters without ILM enabled or access issues
 - Integrated visual phase icons (🔥 Hot, 🟡 Warm, 🧊 Cold, ❄️ Frozen, 🗑️ Delete, ⚪ Unmanaged)
 - Professional multi-panel layouts with consistent styling across all ILM commands
 - Complete JSON format support for all ILM subcommands for automation and integration

#### 🛠️ Enhanced Core Commands with Rich Formatting
 - Enhanced `ping` command with comprehensive connection testing and cluster overview panels
 - Added connection details panel (🔗) showing host, port, SSL, authentication, and certificate info
 - Integrated cluster overview panel (📊) with health status, node counts, and quick actions
 - Implemented JSON format support for `ping` command with structured connection data
 - Added detailed error handling with Rich panels for connection failures and exceptions

 - Enhanced `flush` command with multi-panel synced flush operation monitoring
 - Added operation summary panel (📊) with shard statistics, success rates, and failure tracking
 - Implemented detailed failure reporting with index/shard-specific error messages
 - Added progress status indicator during flush operation with visual feedback
 - Integrated quick actions panel (🚀) with related monitoring commands

 - Enhanced `freeze` command with comprehensive index validation and operation tracking
 - Added index validation panel (✅) showing health, status, documents, and size information
 - Implemented freeze operation details panel (⚙️) explaining read-only mode and effects
 - Added available indices display when target index not found with helpful error messages
 - Integrated success confirmation with detailed operation results and next steps

 - Updated help system with enhanced descriptions for all improved commands
 - Added JSON format support documentation and command categorization improvements
 - Professional multi-panel layouts following the 2.0+ visual design pattern consistently

#### 🐛 Bug Fixes and Improvements
 - Fixed `current-master` command JSON format support by changing positional argument to `--format` flag
 - Enhanced `current-master` JSON output with comprehensive master node details and cluster overview
 - Added structured JSON response including node details (hostname, transport_address, IP, version, JVM, OS info)
 - Improved JSON field accuracy by removing misleading per-node statistics for dedicated master nodes
 - Added clarity fields (`is_dedicated_master`, `is_data_node`) and conditional per-node stats only for data nodes
 - Fixed `ping` command cluster status display (was showing "Unknown", now shows correct Green/Yellow/Red)
 - Improved argument consistency across all commands using `--format` instead of positional arguments

## [2.0.2] - 2025-07-23
### ✨ Enhanced Paging System
#### 🔄 Configurable Paging for Large Datasets
 - Added comprehensive paging support for `indices`, `shards`, and `snapshots` commands
 - Implemented configuration-based auto-paging with `enable_paging` and `paging_threshold` settings
 - Added `--pager` flag to all supported commands for manual paging override
 - Enhanced user experience for viewing large datasets with less-like navigation
 - Configurable thresholds allow customization of when paging automatically activates
 - Maintains full Rich formatting (colors, borders, emojis) within the pager experience

#### ⚙️ Configuration Management
 - Added `enable_paging: true/false` setting to elastic_servers.yml for global paging control
 - Added `paging_threshold: 50` setting to control when auto-paging activates
 - Enhanced ConfigurationManager with `get_paging_enabled()` and `get_paging_threshold()` methods
 - Backward compatible - paging enabled by default with sensible threshold values

## [2.0.1] - 2025-07-23
### ✨ Enhanced Command Display & Alignment
#### 📊 Improved Index & Shard Commands
 - Enhanced `indice` command with comprehensive Rich formatting and detailed information panels
 - Added three-panel layout: Overview, Settings, and Shards Distribution with perfect column alignment
 - Integrated ILM (Index Lifecycle Management) policy and phase information display
 - Implemented detailed shard-level information with color-coded state indicators
 - Added hot/frozen index detection with theme-based coloring (red for hot, blue for frozen)
 - Enhanced `shards` command with full-width styling and improved statistics panel
 - Implemented proper icon and text alignment across all tabular displays
 - Added comprehensive index metadata including UUID, creation date, version, and configuration

#### 👑 Enhanced Current Master & Recovery Commands
 - Enhanced `current-master` command with comprehensive Rich formatting and dual-panel layout
 - Added detailed master node information including hostname, node ID, and role breakdown
 - Integrated cluster status panel with real-time health indicators and node counts
 - Enhanced `recovery` command with advanced recovery monitoring and progress tracking
 - Added recovery summary dashboard with completion rates and stage breakdowns
 - Implemented color-coded recovery progress with visual stage indicators
 - Added recovery type analysis and comprehensive operation tracking

#### 🎨 Visual Consistency & Alignment
 - Fixed emoji and text alignment issues across all Rich table displays
 - Implemented three-column layout (Label | Icon | Value) for perfect alignment
 - Enhanced spacing and formatting for professional appearance
 - Added consistent icon usage and spacing throughout the application
 - Improved full-width panel layouts for better terminal utilization

## [2.0.0] - 2025-07-22
### 🎉 MAJOR RELEASE - Complete UI & UX Overhaul
#### ✨ Enhanced Health Dashboard System
 - Added comprehensive 6-panel health dashboard with visual status indicators
 - Implemented dashboard/classic style configuration (health_style: dashboard|classic)
 - Added configurable classic format options (classic_style: table|panel)
 - Enhanced cluster overview panel with current master node display
 - Added complete node topology breakdown (total, data, master, client nodes)
 - Implemented shard balance metrics with shards-per-data-node calculations
 - Added real-time performance monitoring (pending tasks, in-flight operations, recovery jobs)
 - Integrated snapshot management panel with repository health and backup status
 - Added visual progress bars and status indicators throughout (✅ 📊 ⚠️ ❌)
 - Improved panel alignment and spacing for professional appearance

#### 🔄 Multi-Cluster Comparison & Grouping
 - Added side-by-side cluster health comparison (--compare feature)
 - Implemented cluster groups for bulk monitoring (--group feature)
 - Added cluster_groups configuration section in elastic_servers.yml
 - Support for 2-3+ cluster simultaneous monitoring in grid layout
 - Enhanced error handling for failed cluster connections in group operations

#### 🎨 Enhanced Visual System
 - Implemented fancy categorized help system with Rich panels
 - Added color-coded command categories (Cluster, Node, Index, Maintenance)
 - Created visual command organization with icons and descriptions
 - Added practical usage examples in help display
 - Enhanced version command with professional panel layout and dynamic Python version
 - Improved all output formatting for consistency and visual appeal

#### ⚙️ Configuration Enhancements
 - Added global and per-cluster health_style configuration
 - Implemented classic_style configuration (table vs panel format)
 - Added verify_certs support for SSL certificate validation
 - Enhanced configuration validation and error handling
 - Added command-line overrides for all display style options

#### 🔧 Health Command Improvements
 - Commands:
   ./escmd.py health                           # Use configured style
   ./escmd.py health --style dashboard         # Force dashboard style
   ./escmd.py health --style classic           # Force classic style
   ./escmd.py health --classic-style table     # Force original table format
   ./escmd.py health --classic-style panel     # Force enhanced panel format
   ./escmd.py health --compare server5           # Side-by-side comparison
   ./escmd.py health --group att               # Group health monitoring
   ./escmd.py health --group production --format json  # Group with JSON output

#### 📖 Documentation & Help
 - Complete README.md overhaul with comprehensive feature documentation
 - Added enhanced help system with visual command categorization
 - Added configuration examples and best practices
 - Added troubleshooting section and usage workflows
 - Documented all new features with examples

#### 🛠️ Technical Improvements
 - Refactored code for better modularity and maintainability
 - Enhanced error handling and connection reliability
 - Improved Rich library integration for consistent styling
 - Added comprehensive configuration validation
 - Enhanced JSON export capabilities for all new features

### 📊 Key Features Summary
 - **6-Panel Health Dashboard**: Complete cluster overview in organized visual layout
 - **Multi-Cluster Operations**: Compare and monitor multiple clusters simultaneously
 - **Flexible Display Options**: Configurable styles with command-line overrides
 - **Enhanced Help System**: Visual command discovery with categorization
 - **Professional UI**: Consistent styling throughout all commands
 - **Cluster Groups**: Logical organization for bulk operations

## [1.8.0] - 2025-07-22
 - Added support to list Elasticsearch snapshots via:
   # Commands are as follow:
   ./escmd.py -l server8 snapshots list
   ./escmd.py -l server8 snapshots list logs-gas
   ./escmd.py -l server8 snapshots list --format json
   ./escmd.py -l server8 snapshots list logs-gas --format json
 - Added Allocation settings changes:
  # Commands are as follows:
  ./escmd.py allocation display     # Show current allocation settings
  ./escmd.py allocation enable      # Enable shard allocation
  ./escmd.py allocation disable     # Disable shard allocation
  ./escmd.py allocation exclude add {hostname}     # Add host to exclusion list
  ./escmd.py allocation exclude remove {hostname}  # Remove host from exclusion list
  ./escmd.py allocation exclude reset              # Clear all exclusions
## [1.6.0] - 2025-05-30
 - Added allocation exclude feature to exclude server from allocations (./escmd.py allocation exclude {hostname})
 - Fixed issue with cursor issue when deleting indice from cluster.
## [1.5.0] - 2025-04-14
 - Refactored main script for readability (command_handler.py, configuration_manager.py, utils.py) updated accordingly
 - Added snowflake next to indices, to automatically show frozen indices.
 - Added exclude option, allows excluding indice from node. (./escmd.py exclude .ds-server17-logs-qdf-k8s-default-2025.04.01-000238 -s ess01)
 - Added exclude-reset option, removes any exclusions from index. (./escmd.py exclude-reset .ds-server17-logs-qdf-k8s-default-2025.04.01-000238)
## [1.4.2] - 2025-03-17
 - Changed default rollover behavior to Datastream (./escmd.py rollover server18-logs-gan-k8s-access )
 - Changed old rollover to auto-rollover (./escmd.py auto-rollover -l server1)
 - Now shows hot shards for datastreams
## [1.4.0] - 2025-01-13
 - Migrated to use PyClasses
 - Added shards sorting by size (--size, -s)
 - Added shards limit output based upon node (--location, -l)
 - Added ability to limit number of rows returned in data (-n)
 - Added ability to rollover indices (./escmd rollover -l server1)
## [1.2.4] - 2024-09-23
 - Added default timeout of 60 seconds.
## [1.2.2] - 2024-08-28
 - Added password prompt if password == None
 - Added progress bar on recovery screen
## [1.2.1] - 2024-08-27
 - Fixed Flushed to ignore SSL cert validation
## [1.2.0] - 2024-08-22
 - Fixed Indice Search issue that was broken
 - Added Guage next to ES health.
## [1.1.9] - 2024-08-15
 - Added ability to filter indices by status (example: ./escmd.py -l server19 indices --status yellow)
 - Added ability to delete matching indices (example: ./escmd.py -l server19 indices 2024.15 --delete)
 - Added ability to check indice (replication status) --- TODO
## [1.0.12] - 2024-07-16
 - Fixed version to not require ES connection.
## [1.0.11] - 2024-07-15
 - Added hostname2, to provide 2nd failover node for queries.
 - Added locations, to show configured servers.
 - Added Index Column auto width based upon index length.
## [1.0.10] - 2024-05-16
 - Fixed Recovery Status
## [1.0.9] - 2024-05-14
 - Fixed Recovery Status to show percent and source/dest node.
## [1.0.8] - 2024-04-22
 - Added Flush feature, to POST _flush/synced
## [1.0.7] - 2024-04-21
 - Added shards feature
## [1.0.4] - 2024-04-17
 - Fixed Missing Authentication, Now supports ES Authentication
## [1.0.3] - 2024-04-16
 - Changed output of nodes, indices to sort alphabetically by default
