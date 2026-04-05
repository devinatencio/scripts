# Plan: Improve `generate_elastic_servers.py` credential handling

## Context

- `WORK_ENVIRONMENT.md` is not present in this repository; this plan stands alone.
- Runtime auth for escmd is documented in `configuration_manager.py` (`_resolve_password`, `_resolve_username`) and `security/password_manager.py` (keys like `prod.kibana_system` in `escmd.json`).
- The generator already derives **per-environment `kibana_system` passwords** from fixed seeds via **SHA512** (`hashlib.sha512(seed).hexdigest()`). This is not MD5 in the current code; the idea is the same: **deterministic “built-in” passwords** that work when nothing is stored locally.

## Why keep the hash (seed) method

`escmd.json` may be empty, on another machine, or missing keys for every environment. The seed/hash pipeline is **self-contained**: anyone with the repo (or script) and crosscluster YAML can probe clusters without prior `store-password`. So the updated design **keeps** hash-derived `kibana_system` credentials as a first-class path, not a legacy flag.

When `escmd.json` *does* have `kibana_system` (or another user) for an env, those values can be **more accurate** than the hash if operators rotate service passwords away from the seed-derived value. Ordering below reflects that.

## Current gaps (still valid)

1. **No `PasswordManager` integration** — stored `prod.kibana_system` etc. are never tried alongside the hash.
2. **No alternate user in the chain** — no `elastic_username` from JSON, no CLI user+prompted password, before or after hash attempts.
3. **Success metadata** — still only `config_password`; winning **username** is not recorded or written to YAML.
4. **`create_minimal_config`** — does not reflect which credential strategy applies.

## Goal

- **Three cases**, in a sensible merge with the hash method:
  1. **`kibana_system`** — try **stored** `{pwd_env}.kibana_system` when present; else **hash-derived** password for that env (current `_generate_password_hashes` behavior).
  2. **Alternate user** — `elastic_username` from `escmd.json` (or `--username`) + stored password for `{pwd_env}.<user>` / `global.<user>` via `get_password` semantics; plus **CLI password** when not in store.
  3. **`kibana` / `kibana`** — final fallback (unchanged idea).

## Proposed credential order (per `pwd_env` in chain)

For each `pwd_env` in `env_password_chains` (existing mapping):

1. **Stored `kibana_system`:** `PasswordManager.get_password(pwd_env, "kibana_system")` — if non-empty, attempt once.
2. **Hash `kibana_system`:** same as today — SHA512(seed) for that env — **only if** step 1 did not run or you want “try both”: prefer **skip hash if stored attempt exists and you want fewer round-trips**, or **try hash after failed stored** if clusters might still use seed password while JSON is stale. Recommended: **stored first, then hash** (covers “JSON wrong/missing” and “JSON right”).
3. **Stored human user:** resolve username = `escmd.json` `elastic_username` or default; `get_password(pwd_env, username)` (inherits global fallbacks inside `get_password`).
4. **CLI user + password:** if `--username` (and password from `--password` / env / `getpass`), attempt for this `pwd_env` (see open decision on breadth).
5. After all `pwd_env` entries, **global final:** `kibana` / `kibana` → `config_password` / label `default` as today.

**Dedup:** If stored and hash produce the same string for `kibana_system`, attempt once.

**Logging:** On success, print label such as `kibana_system (stored prod)`, `kibana_system (seed)`, `user devin.acosta (stored)`, `user X (cli)`, `kibana:kibana`.

## CLI (unchanged intent)

- `--username`, `--password` or env / `--prompt-password`, `--escmd-json`.
- Docstring: hash path works without `escmd.json`; stored path preferred when available.

## Emit YAML

- Thread `(config_password_env, winning_username)` from `connect_to_elasticsearch` into `process_cluster`.
- Set `elastic_username` when the winner is not the default you want escmd to infer, or always set for clarity.
- For `kibana:kibana`, keep aligning with existing hand-edited patterns (inline or `default` + store).

## Open decisions

1. **CLI user tries which envs:** all `pwd_env` in chain vs `--password-env` only.
2. **Stale JSON:** order “stored then hash” vs “hash only when no key” — recommend stored-then-hash for robustness.
3. **Inline `elastic_password` in generated YAML:** only when winner is basic auth not representable by store + `config_password` alone.

## Implementation order (suggested)

1. Refactor credential list builder: merge `PasswordManager` reads with existing `self.passwords` hash map; unified ordered attempts with labels.
2. Extend `connect_to_elasticsearch` return value with winning username + label.
3. Add CLI prompt / password flags.
4. Update `process_cluster` / `create_minimal_config` for `elastic_username` (and inline password if needed).
5. Docstring / `--help` only if requested.

## Files to touch

- `generate_elastic_servers.py` (main work)
- `security/password_manager.py` — only if a tiny helper is needed (optional)
