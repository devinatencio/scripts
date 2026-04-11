# Workflows, reference, and full documentation

## Everyday workflows

**Morning checks**

```bash
./escmd.py -l production health
./escmd.py -l production cluster-check --dry-run
```

**Before maintenance**

```bash
./escmd.py -l production cluster-check > "pre-$(date +%Y%m%d).txt"
./escmd.py -l production allocation exclude add <node>
```

**After maintenance**

```bash
./escmd.py -l production allocation exclude remove <node>
./escmd.py -l production health
./escmd.py -l production snapshots list
```

**Dangling indices (always preview first)**

```bash
./escmd.py -l production dangling --cleanup-all --dry-run
```

More narrative workflows: `docs/workflows/monitoring-workflows.md`, `docs/workflows/dangling-cleanup.md`.

## Troubleshooting

Common problems (connectivity, TLS, auth, display) are collected in `docs/reference/troubleshooting.md`. Check:

- `ping` and `show-settings`
- TLS flags vs corporate MITM proxies
- Password resolution (environment, store-password, YAML)

## Changelog and releases

- **`docs/reference/changelog.md`** — consolidated change history
- **`docs/releases/`** — per-version release notes

## Index of all docs

**`docs/README.md`** in the repository is the master index (commands, configuration, guides, features, themes, reference).

## Generating this manual as PDF

See **`README.md`** in this folder for the exact `generate_docs_pdf.py` command and output path.
