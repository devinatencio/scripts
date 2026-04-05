# Release Notes: ESCMD Version 3.8.4

**Release Date**: April 4, 2026
**Version**: 3.8.4
**Type**: Bugfix Release

---

## 🎯 Overview

Version 3.8.4 fixes a long-standing terminal table misalignment issue caused by a category
of emoji characters that terminals and the Rich library were measuring at different widths.
The fix required both upgrading Rich to a version that contains the upstream grapheme-aware
width fix, and replacing a set of structurally problematic emoji with visually equivalent
alternatives that are universally rendered at the correct width across all terminal
emulators.

---

## 🐛 Bug Fixed

### Terminal Table Column Misalignment with Certain Emoji

**Symptom**

In screens that contained emoji labels inside Rich table grid columns — most visibly the
`version` command — certain rows would have their value column shifted one terminal cell
to the right or left relative to adjacent rows. For example, the `Platform:` row would
show `Darwin arm64` starting one column earlier than `3.14.3` on the `Python:` row
directly above it, even though both rows belonged to the same column grid.

The same misalignment was present in any screen that used the affected emoji as label
prefixes, including the health dashboard, allocation settings, ILM status, shard tables,
settings panel, and others.

**Root Cause — Two Separate but Related Issues**

*Issue 1: Rich < 14.3.0 did not handle Variation Selector-16 (VS16) sequences*

Several emoji in the codebase were written as a base Unicode character followed by
`U+FE0F` (Variation Selector-16), which instructs terminals to render the character in
full-color emoji presentation rather than as a monochrome text symbol. Examples:

- `⚠️`  = `U+26A0` WARNING SIGN  + `U+FE0F`
- `⚙️`  = `U+2699` GEAR          + `U+FE0F`
- `🖥️`  = `U+1F5A5` DESKTOP COMPUTER + `U+FE0F`
- `⏱️`  = `U+23F1` STOPWATCH     + `U+FE0F`
- `🛡️`  = `U+1F6E1` SHIELD       + `U+FE0F`
- `🏷️`  = `U+1F3F7` LABEL        + `U+FE0F`

Rich versions prior to 14.3.0 used a simple per-codepoint lookup table and treated
`U+FE0F` as zero-width without accounting for the fact that it upgrades a preceding
narrow (1-cell) character into a wide (2-cell) emoji glyph. Rich therefore measured these
sequences as 1 cell wide while the terminal rendered them as 2 cells wide. The result
was that Rich allocated one too few padding cells for those rows, causing the right panel
border and every subsequent column to appear shifted.

Rich 14.3.0 (PR #3930, merged 2026-01-22) rewrote the width calculation to be
grapheme-aware, using the same Unicode data as the `wcwidth` library, and correctly
handles VS16 sequences. Rich 14.3.3 added a further fix for an infinite loop in the
`split_graphemes` function.

*Issue 2: Six emoji have `east_asian_width = 'N'` (Narrow) for their base codepoint*

Even with Rich 14.3.3 correctly measuring these emoji as 2 cells wide, a second problem
remained. The six emoji listed above all have base codepoints whose Unicode
`east_asian_width` property is `'N'` (Narrow) rather than `'W'` (Wide):

| Emoji | Codepoint | `east_asian_width` |
|-------|-----------|-------------------|
| `⚠️` base `⚠` | U+26A0  | N |
| `⚙️` base `⚙` | U+2699  | N |
| `🖥️` base `🖥` | U+1F5A5 | N |
| `⏱️` base `⏱` | U+23F1  | N |
| `🛡️` base `🛡` | U+1F6E1 | N |
| `🏷️` base `🏷` | U+1F3F7 | N |

Terminals determine the display width of a character using the system's Unicode width
data (via `wcwidth()` or equivalent font metrics). Systems with older Unicode databases,
or terminals that do not apply the VS16 emoji-upgrade rule when computing glyph advances,
consult only the `east_asian_width` of the base codepoint and conclude the character is
1 cell wide. Rich 14.3.3 outputs spacing calculated for a 2-cell-wide glyph; the
terminal renders the glyph into 1 cell; the cursor ends up 1 column earlier than Rich
expected; the value column for that row is visually shifted left by 1 cell relative to
all other rows.

**Fix**

Two complementary changes were applied:

1. **Upgraded Rich from 14.1.0 to ≥ 14.3.3** in `requirements.txt`. This resolves
   Issue 1 completely and is the correct long-term fix for the VS16 measurement problem.

2. **Replaced all six problematic emoji** with semantically equivalent alternatives
   whose base codepoints have `east_asian_width = 'W'`. This resolves Issue 2 and
   ensures correct alignment on every terminal, regardless of its Unicode database
   version:

| Removed | Replaced with | Replacement name |
|---------|--------------|-----------------|
| `🖥️`  U+1F5A5 + VS16 | `💻` U+1F4BB | Laptop Computer |
| `⚠️`  U+26A0  + VS16 | `🔶` U+1F536 | Large Orange Diamond |
| `⚙️`  U+2699  + VS16 | `🔩` U+1F529 | Nut and Bolt |
| `⏱️`  U+23F1  + VS16 | `⏰` U+23F0  | Alarm Clock |
| `🛡️`  U+1F6E1 + VS16 | `🔐` U+1F510 | Locked with Key |
| `🏷️`  U+1F3F7 + VS16 | `🔖` U+1F516 | Bookmark |

All six replacements have `east_asian_width = 'W'`, so both Rich and every terminal
width implementation agree they are exactly 2 terminal cells wide.

Additionally, approximately 25 compensatory double-space workarounds that had been
manually inserted throughout the renderer files to partially offset the misalignment
(e.g. `"🖥️  Platform:"` with two spaces instead of one) were removed, as they were no
longer needed and caused minor visual inconsistency when the underlying emoji width was
being correctly calculated.

---

## 📋 Files Changed

### Core Fix
| File | Change |
|------|--------|
| `requirements.txt` | Bumped `rich>=13.9.4` → `rich>=14.3.3` |

### Emoji Replacements (56 files)
The six problematic emoji were replaced globally across every Python file in the project.
The most visually significant files in the `display/` layer:

| File | Emoji replaced |
|------|---------------|
| `display/version_renderer.py` | `🖥️` → `💻`, `⚙️` → `🔩`, `⏱️` → `⏰`, `🛡️` → `🔐` |
| `display/health_renderer.py` | `🖥️` → `💻`, `⚠️` → `🔶`, `⚙️` → `🔩` |
| `display/allocation_renderer.py` | `🖥️` → `💻`, `⚠️` → `🔶`, `⚙️` → `🔩` |
| `display/ilm_renderer.py` | `⚠️` → `🔶`, `⚙️` → `🔩` |
| `display/shard_renderer.py` | `🖥️` → `💻`, `⚠️` → `🔶` |
| `display/template_renderer.py` | `⚠️` → `🔶`, `⚙️` → `🔩` |
| `display/settings_renderer.py` | `⚠️` → `🔶`, `⚙️` → `🔩`, `🛡️` → `🔐` |
| `display/snapshot_renderer.py` | `⚠️` → `🔶`, `⏱️` → `⏰`, `🏷️` → `🔖` |
| `display/storage_renderer.py` | `🖥️` → `💻`, `⚠️` → `🔶` |
| `display/index_renderer.py` | `🖥️` → `💻`, `⚠️` → `🔶`, `⚙️` → `🔩` |
| `display/replica_renderer.py` | `⚠️` → `🔶` |
| `display/repositories_renderer.py` | `⚙️` → `🔩` |
| `display/recovery_renderer.py` | `⚙️` → `🔩` |
| `display/version_data.py` | `⚙️` → `🔩`, `🛡️` → `🔐` |
| `display/settings_data.py` | `⚠️` → `🔶` |
| `display/style_system.py` | `⚠️` → `🔶` |
| `handlers/` (all handler files) | All six emoji replaced as applicable |
| `commands/` (all command files) | All six emoji replaced as applicable |
| `cli/`, `escmd.py`, `esclient.py`, others | All six emoji replaced as applicable |

### Double-Space Cleanup (~25 instances across display files)
Compensatory double-spaces that were previously hand-inserted to partially offset the
misalignment were removed from all renderer files.

### Diagnostic Tooling (new, stays in repo)
| File | Purpose |
|------|---------|
| `measure_labels.py` | Verifies Rich `cell_len` matches terminal display width for all emoji-containing table labels across every renderer. Run with `python measure_labels.py` to catch regressions. |

---

## 🔍 How to Verify the Fix

Run the version command and inspect that all value-column entries align vertically:

```bash
./escmd.py version
```

The `Platform:` row value (`Darwin arm64` or similar) must start at the same horizontal
column as `Python:`, `Version:`, `Released:`, and all other rows in that panel.

To programmatically confirm there are no remaining width mismatches:

```bash
python measure_labels.py
```

Expected output ends with:

```
ALL LABELS OK – Rich 14.3.3 measurements match terminal widths.
```

---

## ✅ Testing

- All 56 modified files pass Python syntax validation (`python -m py_compile`).
- `measure_labels.py` reports zero mismatches under Python 3.13 and 3.14.3 with
  Rich 14.3.3.
- No existing command behavior or output content was changed; only the emoji glyphs
  used in labels and titles were substituted with visually similar alternatives.
- Backward compatibility is fully maintained.

---

## 🔄 Upgrade Notes

### Dependency Change

If you manage your own virtual environment, upgrade Rich explicitly:

```bash
pip install "rich>=14.3.3"
```

Or recreate the environment from `requirements.txt`:

```bash
pip install -r requirements.txt --upgrade
```

### Visual Change

The six replaced emoji are visually distinct from their predecessors. Screens that
previously showed `⚠️`, `⚙️`, `🖥️`, `⏱️`, `🛡️`, or `🏷️` now show `🔶`, `🔩`, `💻`,
`⏰`, `🔐`, or `🔖` respectively. The semantic intent of each label is unchanged.

---

## 📝 Summary

This release eliminates a persistent one-column misalignment that affected every table
or panel screen in the tool that used VS16 emoji as row label prefixes. The fix is both
correct and durable: upgrading Rich ensures the library side measures grapheme sequences
properly, and replacing the ambiguous-width emoji ensures the terminal side renders them
at the expected width regardless of the system's Unicode database version.

---

*ESCMD v3.8.4 — April 4, 2026*