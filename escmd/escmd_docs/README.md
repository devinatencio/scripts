# escmd_docs

This folder is the **print-oriented user manual** for escmd. Chapters are plain Markdown, ordered for merging into a single PDF.

## Build the PDF

From the repository root (same directory as `escmd.py`):

```bash
pip install -r requirements-docs-pdf.txt
python3 scripts/generate_docs_pdf.py -c escmd_docs/pdf-config.yaml
```

The output file is written to `escmd_docs/build/escmd-user-manual.pdf` (see `pdf-config.yaml`).

Options:

- `-v` / `--verbose` — print each source file as it is included
- `-c PATH` — use a different YAML config

## Relationship to `docs/`

The repository `docs/` tree is the full documentation set (deep dives, development notes, release notes). **escmd_docs** is a shorter linear manual. For topics not covered here, browse `docs/README.md` in the repo.

## Chapter list

| File | Topic |
|------|--------|
| `01-introduction.md` | What escmd is and main capabilities |
| `02-installation.md` | Requirements and installation |
| `03-configuration.md` | `elastic_servers.yml`, dual-file mode, passwords |
| `04-command-usage.md` | Full command reference with examples and alphabetical index |
| `05-esterm-and-output.md` | Interactive terminal, themes, formats |
| `06-workflows-reference.md` | Common workflows, troubleshooting, changelog pointer |
