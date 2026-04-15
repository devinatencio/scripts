# UI Standards & Patterns for escmd

This document captures the established UI patterns used across all escmd commands.
Follow these patterns when creating new commands or updating existing ones.

---

## 1. Top Panel (Title Panel) — Standard Pattern

Every command that displays data should have a top panel following this structure:

```
╭──────────────────────── 📊 Command Title ─────────────────────────╮
│                                                                    │
│              ✅ Status Text - Centered Body Message                │
│                                                                    │
╰──────── Key: Value | Key: Value | Key: Value ─────────────────────╯
```

### Structure

- **Title bar** (`title=`): Command name with emoji, styled with themed primary.
  ```python
  ts = ss._get_style('semantic', 'primary', 'bold cyan') if ss else 'bold cyan'
  title=f"[{ts}]📊 Command Title[/{ts}]"
  ```

- **Body** (panel content): Status text centered, color reflects health/state.
  ```python
  Text("✅ Status Message", style="bold green", justify="center")
  ```
  - Green (`bold green`): healthy/success state
  - Yellow (`bold yellow`): warning state
  - Red (`bold red`): error/critical state

- **Subtitle bar** (`subtitle=`): Key stats as a `Text()` object with themed colors.
  ```python
  subtitle_rich = Text()
  subtitle_rich.append("Total: ", style="default")
  subtitle_rich.append("42", style=ss._get_style('semantic', 'info', 'cyan'))
  subtitle_rich.append(" | Green: ", style="default")
  subtitle_rich.append("40", style=ss._get_style('semantic', 'success', 'green'))
  ```

- **Border**: Health-aware. Yellow when warnings, red when critical, theme default when healthy.
  ```python
  border = ss._get_style('table_styles', 'border_style', 'cyan') if healthy else "yellow"
  ```

- **Padding**: `(1, 2)` for panels with body content.

### Examples from codebase

| Command | Title | Body | Subtitle |
|---------|-------|------|----------|
| `indices` | 📊 Elasticsearch Indices | ✅ Cluster Healthy - 245 of 247 Green | cluster v8.17 Total: 247 \| Green: 245 \| Yellow: 2 |
| `nodes` | 💻 Elasticsearch Nodes | 🟢 All Nodes Healthy - 3 Online | cluster v8.17 Total: 3 \| Master: 1 \| Data: 2 |
| `shards` | 📊 Elasticsearch Shards Overview | ✅ Good - All Shards Assigned | Total: 494 \| Started: 494 \| Primary: 247 |
| `allocation` | 🔀 Elasticsearch Allocation Settings | ✅ Enabled - All Shards Allocated | Total Nodes: 3 \| Data: 2 \| Active: 2 |
| `ping` | 🔍 Elasticsearch Connection Test | 🟢 Connected - cluster (Green) | Host: es:9200 \| SSL: Yes \| Nodes: 3 |
| `recovery` | 🔄 Cluster Recovery Status | ✅ No Active Recovery Operations | (none when idle) |
| `templates` | 📋 Elasticsearch Templates | ✅ 42 Templates Configured | Total: 42 \| Legacy: 5 \| Composable: 25 |
| `repositories` | 📦 Snapshot Repositories | ✅ 2 Repositories Configured | Total: 2 \| S3: 1 \| FS: 1 |
| `current-master` | 👑 Current Cluster Master | ✅ node-1 (Active Master) | Cluster: name \| Status: 🟢 Green \| Nodes: 3 |
| `indices-analyze` | 📊 Index Traffic Analysis | 🔶 3 Outliers Detected | Scanned: 150 \| Groups: 42 \| Flagged: 3 |

---

## 2. Help Tables — No-Args Pattern

When a command is run without required arguments, show a themed help table instead of raw argparse errors.

### Approach

1. Make positional args optional in argparse: `nargs="?", default=None`
2. Remove `required=True` from options that should trigger help
3. Remove `_RichErrorParser` — handle in the handler instead
4. In the handler, check for missing args and call `_show_<command>_help()`

### Structure

```
╭──────────────────────── 📝 Command Title ─────────────────────────╮
│                                                                    │
│  Run ./escmd.py command <args> [options]                           │
│                                                                    │
╰──────────────── Use --help for full options ──────────────────────╯

 Command / Option          Description                    Example
 command <arg>             What it does                   ./escmd.py command arg
 --option <val>            What the option does           ./escmd.py command --option val
 ── Section ──
 --advanced                Advanced option                ./escmd.py command --advanced
```

### Template code

```python
def _show_command_help(self):
    """Display help screen for command."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = self.console
    ss = self.es_client.style_system
    tm = self.es_client.theme_manager

    primary_style = ss.get_semantic_style("primary")
    success_style = ss.get_semantic_style("success")
    muted_style = ss._get_style('semantic', 'muted', 'dim')
    border_style = ss._get_style('table_styles', 'border_style', 'white')
    header_style = tm.get_theme_styles().get('header_style', 'bold white') if tm else 'bold white'
    title_style = tm.get_themed_style('panel_styles', 'title', 'bold white') if tm else 'bold white'
    box_style = ss.get_table_box()

    header_panel = Panel(
        Text("Run ./escmd.py command <args> [options]", style="bold white"),
        title=f"[{title_style}]📝 Command Title[/{title_style}]",
        subtitle=Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]for full options[/dim]"),
        border_style=border_style,
        padding=(1, 2),
        expand=True,
    )

    table = Table(
        show_header=True,
        header_style=header_style,
        border_style=border_style,
        box=box_style,
        show_lines=False,
        expand=True,
    )
    table.add_column("Command / Option", style=primary_style, ratio=2)
    table.add_column("Description", style="white", ratio=3)
    table.add_column("Example", style=success_style, ratio=3)

    # Main commands
    rows = [
        ("command <arg>", "Description", "command my-arg"),
    ]
    for i, (cmd, desc, ex) in enumerate(rows):
        table.add_row(cmd, desc, f"./escmd.py {ex}", style=ss.get_zebra_style(i) if ss else None)

    # Section separator
    table.add_row(
        Text("── Options ──", style=muted_style),
        Text("", style=muted_style),
        Text("", style=muted_style),
    )

    # Options/advanced rows (secondary style, muted examples)
    options = [
        ("--option <val>", "What it does", "command --option val"),
    ]
    for i, (opt, desc, ex) in enumerate(options):
        table.add_row(
            Text(opt, style=ss._get_style('semantic', 'secondary', 'magenta')),
            desc,
            Text(f"./escmd.py {ex}", style=muted_style),
            style=ss.get_zebra_style(i) if ss else None,
        )

    console.print()
    console.print(header_panel)
    console.print()
    console.print(table)
    console.print()
```

### Key rules

- Header panel body text: `style="bold white"` (not muted)
- Subtitle: color-coded `Text.from_markup("[dim]Use[/dim] [cyan]--help[/cyan] [dim]for full options[/dim]")`
- Main commands use `primary_style` + `success_style` for examples
- Section separators use `muted_style`
- Advanced/option rows use `secondary` style for the command, `muted_style` for examples
- Zebra striping via `ss.get_zebra_style(i)`

### Commands using this pattern

`snapshots`, `ilm`, `template`, `create-index`, `set-replicas`, `rollover`, `action`,
`exclude`, `exclude-reset`, `set`, `template-modify`, `template-backup`, `template-restore`,
`template-create`, `indice-add-metadata`

---

## 3. Theme Access Patterns

### Getting styles

```python
ss = self.es_client.style_system  # or self.style_system in renderers
tm = self.es_client.theme_manager  # or self.theme_manager in renderers
```

### Common style lookups

| What | Code | Fallback |
|------|------|----------|
| Title bar text | `ss._get_style('semantic', 'primary', 'bold cyan')` | `'bold cyan'` |
| Panel title style | `tm.get_themed_style('panel_styles', 'title', 'bold white')` | `'bold white'` |
| Table border | `ss._get_style('table_styles', 'border_style', 'bright_magenta')` | `'bright_magenta'` |
| Table header | `tm.get_theme_styles().get('header_style', 'bold white')` | `'bold white'` |
| Table box | `ss.get_table_box()` | `None` |
| Semantic success | `ss.get_semantic_style("success")` | `'green'` |
| Semantic error | `ss.get_semantic_style("error")` | `'red'` |
| Semantic warning | `ss.get_semantic_style("warning")` | `'yellow'` |
| Semantic info | `ss._get_style('semantic', 'info', 'cyan')` | `'cyan'` |
| Semantic primary | `ss._get_style('semantic', 'primary', 'bright_magenta')` | `'bright_magenta'` |
| Semantic muted | `ss._get_style('semantic', 'muted', 'dim')` | `'dim'` |
| Zebra row | `ss.get_zebra_style(row_index)` | `None` |

### Subtitle bar colors (for `_get_style`)

Use these consistently in subtitle bars:
- Counts/totals: `'semantic', 'info', 'cyan'`
- Primary identifiers: `'semantic', 'primary', 'bright_magenta'`
- Success/green values: `'semantic', 'success', 'green'`
- Warning/yellow values: `'semantic', 'warning', 'yellow'`
- Error/red values: `'semantic', 'error', 'red'`
- Muted/dim text: `'semantic', 'muted', 'dim'`
- Version numbers: `'semantic', 'muted', 'dim'`

---

## 4. Inner Panel Tables

When panels contain key-value data, use this pattern:

```python
table = Table(show_header=False, box=None, padding=(0, 1))
table.add_column("Label", style="bold", no_wrap=True)
table.add_column("Icon", justify="left", width=3)
table.add_column("Value", no_wrap=True)

table.add_row("Status:", "✅", "Enabled")
table.add_row("Nodes:", "💻", "3")
```

### Rules

- Label column: `style="bold"` (plain bold, not semantic primary)
- Icon column: `width=3`, single-codepoint emoji only (no `🖥️` or `⚠️` — they have variation selectors)
- No header shown (`show_header=False`)
- No box (`box=None`)
- Padding: `(0, 1)`

### Safe emoji (single codepoint)

✅ ❌ 🔶 💻 💾 📊 📋 🔑 📈 🔒 🚫 🔄 🔀 📝 🕐 🚧 💡 📦 🔩 📅 🆔 🔴 🟢 🟡

### Unsafe emoji (have variation selectors — avoid in width=3 columns)

🖥️ ⚠️ ☁️

---

## 5. Side-by-Side Panels

Use `Columns` with `expand=True`:

```python
from rich.columns import Columns
console.print(Columns([left_panel, right_panel], expand=True))
```

Do NOT use `Table.grid()` for side-by-side panels — it doesn't expand properly.

---

## 6. Success/Error Output Panels

For operation results (enable, disable, reset, etc.):

```python
panel = Panel(
    Text("✅ Successfully did the thing", style="bold green", justify="center"),
    title=f"[{ts}]🔄 Operation Name[/{ts}]",
    border_style=border,  # theme border for success, "red" for error
    padding=(1, 2)
)
```

---

## 7. Empty State Panels

When no data exists (no repos, no recovery, etc.):

```python
panel = Panel(
    Text("✅ No Active Recovery Operations", style="bold green", justify="center"),
    title=f"[{ts}]🔄 Recovery Status[/{ts}]",
    border_style=border,
    padding=(1, 2)
)
```

Keep it concise. For commands that need guidance (like repositories), add brief help text:

```python
Panel(
    Text.from_markup(
        "No data found.\n\n"
        "[bold]Quick Start:[/bold]\n"
        "  [cyan]./escmd.py command create my-thing[/cyan]",
        justify="left"
    ),
    title=f"[{ts}]📦 Title[/{ts}]",
    border_style="yellow",
    padding=(1, 2),
)
```

---

## 8. Table Titles

When a table follows a title panel, do NOT add a redundant title to the table.
The title panel already identifies the content.

```python
# Good — no table title, panel above already has it
table = style_system.create_standard_table(None, style_variant='dashboard')

# Bad — redundant title
table = style_system.create_standard_table("Elasticsearch Nodes", style_variant='dashboard')
```

---

## 9. Render Layout Order

Standard layout for most commands:

```
print()
console.print(title_panel)
print()
console.print(Columns([left_panel, right_panel], expand=True))  # if applicable
print()
console.print(detail_table_or_panel)  # if applicable
print()
```

Always have `print()` between panels for spacing. The title panel handles its own top spacing.
