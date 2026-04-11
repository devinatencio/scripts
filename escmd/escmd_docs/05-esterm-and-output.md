# ESTERM, themes, and output

## ESTERM (interactive terminal)

**ESTERM** is an interactive front end around the same command set as `escmd.py`. Start it from the project root:

```bash
./esterm.py
```

or the `esterm` wrapper script if provided.

Typical benefits:

- One connection context per session; switch clusters with connect-style commands
- Readline history and less repetition than shell one-liners
- Watch-style refresh for monitoring (for example periodic health)

Behavior and key bindings are documented in the repository at `docs/guides/ESTERM_GUIDE.md`.

## Rich output vs ASCII

escmd uses the **rich** library for tables, panels, and colors. If symbols or colors break in your terminal or log capture:

- Enable **`ascii_mode`** in settings (see [03-configuration.md](03-configuration.md))
- Redirect output knowing that some views are designed forTTY width

## Themes

Theming is driven by YAML (for example `themes.yml`) referenced from **`themes_file`** in settings. Custom themes and migration notes live under `docs/themes/` (`THEME_GUIDE.md`, `CUSTOM_THEMES_GUIDE.md`, etc.).

## Paging

When output exceeds **`paging_threshold`** and **`enable_paging`** is true, escmd may invoke your pager. Adjust thresholds for automation so jobs do not block on a pager.

## ESTERM and actions

Action sequences can be run from ESTERM; output modes may default differently inside the interactive shell (for example native vs formatted). See `docs/features/esterm-actions.md`.
