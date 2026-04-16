# Requirements Document — Nord v2 Theme Overhaul

## Introduction

This feature replaces the current approximate-color Nord theme in escmd with a true-hex Nord v2 palette (nord0 `#2e3440` through nord15 `#b48ead`), audits every renderer and command for hardcoded Rich color strings, and routes all styling through the existing ThemeManager/StyleSystem pipeline. The overhaul ensures that every theme — not just Nord — benefits from consistent theme routing, while maintaining full backward compatibility with all existing themes (rich, plain, cyberpunk, cyberpunk_yellow, ocean, midnight, fire, corporate, matrix, solarized).

## Glossary

- **ThemeManager**: The class in `display/theme_manager.py` responsible for loading, caching, and retrieving theme data from `themes.yml`.
- **StyleSystem**: The class in `display/style_system.py` that provides semantic style resolution (success, warning, error, info, primary, secondary, neutral, muted) and utility methods for tables, panels, and progress bars.
- **Semantic_Style**: A named style token (e.g. "success", "error") that maps to a concrete Rich style string via the `semantic_styles` section in `themes.yml`.
- **Hardcoded_Color**: A literal Rich color string (e.g. `"bold green"`, `"bright_red"`, `"on dark_red"`) embedded directly in renderer or command code instead of being resolved through ThemeManager or StyleSystem.
- **Nord_Palette**: The official 16-color Nord palette from nordtheme.com, consisting of Polar Night (nord0–nord3), Snow Storm (nord4–nord6), Frost (nord7–nord10), and Aurora (nord11–nord15).
- **Renderer**: Any Python module in the `display/` directory responsible for formatting and printing Rich output for a specific command domain.
- **themes.yml**: The YAML configuration file at the project root that defines all theme color mappings.
- **Box_Style**: The Rich `box` type used for table borders (e.g. HEAVY, ROUNDED, SIMPLE).

## Requirements

### Requirement 1: Replace Nord Theme Definition with True Hex Values

**User Story:** As a user of the Nord theme, I want the theme to use the official Nord hex color values, so that the terminal output matches the canonical Nord palette exactly.

#### Acceptance Criteria

1. WHEN the Nord theme is loaded from `themes.yml`, THE ThemeManager SHALL return hex color values from the official Nord palette (nord0 `#2e3440` through nord15 `#b48ead`) for all style categories.
2. THE Nord theme definition in `themes.yml` SHALL map `health_styles.green` to nord7 (`#8fbcbb`), `health_styles.yellow` to nord13 (`#ebcb8b`), and `health_styles.red` to nord11 (`#bf616a`).
3. THE Nord theme definition in `themes.yml` SHALL map `status_styles.open` to nord14 (`#a3be8c`) and `status_styles.close` to nord11 (`#bf616a`).
4. THE Nord theme definition in `themes.yml` SHALL map `state_styles.STARTED` to nord14 (`#a3be8c`), `state_styles.INITIALIZING` to nord13 (`#ebcb8b`), `state_styles.RELOCATING` to nord10 (`#5e81ac`), and `state_styles.UNASSIGNED` to nord11 (`#bf616a`).
5. THE Nord theme definition in `themes.yml` SHALL map `type_styles.primary` to nord8 (`#88c0d0`) and `type_styles.replica` to nord9 (`#81a1c1`).
6. THE Nord theme definition in `themes.yml` SHALL map `row_styles.normal` to nord4 (`#d8dee9`), `row_styles.zebra` to nord2 (`#434c5e`), `row_styles.hot` to nord12 (`#d08770`), `row_styles.frozen` to nord15 (`#b48ead`), `row_styles.critical_health` to nord11 (`#bf616a`), `row_styles.warning_health` to nord13 (`#ebcb8b`), and `row_styles.healthy` to nord4 (`#d8dee9`).
7. THE Nord theme definition in `themes.yml` SHALL map `border_style` to nord9 (`#81a1c1`) and `header_style` to `bold #eceff4 on #3b4252`.
8. THE Nord theme definition in `themes.yml` SHALL set `table_box` to `rounded`.
9. THE Nord theme definition in `themes.yml` SHALL map `panel_styles.title` to `bold #88c0d0`, `panel_styles.subtitle` to `dim #d8dee9`, `panel_styles.success` to `#a3be8c`, `panel_styles.warning` to `#ebcb8b`, `panel_styles.error` to `#bf616a`, `panel_styles.info` to `#5e81ac`, and `panel_styles.secondary` to `#b48ead`.
10. THE Nord theme definition in `themes.yml` SHALL map `help_styles.title` to `bold #88c0d0`, `help_styles.section_header` to `bold #81a1c1`, `help_styles.command` to `#ebcb8b bold`, `help_styles.description` to `#d8dee9`, `help_styles.example` to `#8fbcbb`, and `help_styles.footer` to `dim #4c566a`.
11. THE Nord theme definition in `themes.yml` SHALL map `semantic_styles.primary` to `#88c0d0`, `semantic_styles.secondary` to `#b48ead`, `semantic_styles.success` to `#a3be8c`, `semantic_styles.warning` to `#ebcb8b`, `semantic_styles.error` to `#bf616a`, and `semantic_styles.info` to `#5e81ac`.

### Requirement 2: ThemeManager and StyleSystem Hex Color Support

**User Story:** As a theme author, I want the theme system to correctly handle hex color values (`#rrggbb`) in all style categories, so that I can define themes with precise colors.

#### Acceptance Criteria

1. WHEN a theme in `themes.yml` specifies a hex color value (e.g. `#88c0d0`) in any style category, THE ThemeManager SHALL return that hex value unchanged to callers.
2. WHEN StyleSystem resolves a semantic style that contains a hex color value, THE StyleSystem SHALL pass the hex value to Rich without modification.
3. WHEN StyleSystem constructs a zebra stripe style from a hex-valued `row_styles.zebra`, THE StyleSystem SHALL produce a valid Rich background style string (e.g. `on #434c5e`).
4. WHEN ThemeManager builds the `semantic_styles` fallback from `panel_styles` for built-in themes, THE ThemeManager SHALL preserve hex color values in the mapping.

### Requirement 3: Eliminate Hardcoded Colors in Index Renderer

**User Story:** As a theme user, I want the index detail and traffic analysis views to respect my chosen theme, so that all index displays are visually consistent.

#### Acceptance Criteria

1. WHEN `IndexRenderer.print_detailed_indice_info` renders shard state indicators, THE IndexRenderer SHALL obtain state colors from `state_styles` via ThemeManager instead of using hardcoded color strings.
2. WHEN `IndexRenderer.print_detailed_indice_info` renders shard type indicators, THE IndexRenderer SHALL obtain type colors from `type_styles` via ThemeManager instead of using hardcoded color strings.
3. WHEN `IndexRenderer.print_detailed_indice_info` renders metadata table cells, THE IndexRenderer SHALL obtain cell styles from ThemeManager or StyleSystem instead of using hardcoded strings like `bright_cyan`, `bright_white`, or `dim bright_white`.
4. WHEN `IndexRenderer.print_detailed_indice_info` renders row styles for shard rows, THE IndexRenderer SHALL obtain the row style from ThemeManager or StyleSystem instead of using hardcoded strings like `bright_green`, `bright_yellow`, `bright_blue`, or `bright_red`.
5. WHEN `IndexRenderer.print_indices_traffic_analysis` renders severity-styled rows, THE IndexRenderer SHALL obtain severity colors from StyleSystem semantic styles instead of using hardcoded strings like `bright_red` or `yellow`.

### Requirement 4: Eliminate Hardcoded Colors in Indices Commands

**User Story:** As a theme user, I want the indices list view to respect my chosen theme for all visual elements, so that the main indices table is fully themed.

#### Acceptance Criteria

1. WHEN `IndicesCommands.print_table_indices` determines the foreground color for index names based on health, THE IndicesCommands SHALL obtain the color from `health_styles` or `row_styles` via ThemeManager instead of using hardcoded strings like `red`, `yellow`, or `white`.
2. WHEN `IndicesCommands.print_table_indices` styles hot index names, THE IndicesCommands SHALL obtain the hot style from `row_styles.hot` via ThemeManager instead of using the hardcoded string `bright_red`.
3. WHEN `IndicesCommands.print_table_indices` styles frozen index names, THE IndicesCommands SHALL obtain the frozen style from `row_styles.frozen` via ThemeManager instead of using the hardcoded string `bright_blue`.

### Requirement 5: Eliminate Hardcoded Colors in Health Renderer

**User Story:** As a theme user, I want the health dashboard panels to respect my chosen theme, so that the cluster health display is visually consistent.

#### Acceptance Criteria

1. WHEN `HealthRenderer._create_cluster_overview_panel` renders the cluster overview, THE HealthRenderer SHALL obtain label column styles from ThemeManager or StyleSystem instead of using the hardcoded string `bold white`.
2. WHEN `HealthRenderer._create_nodes_panel` renders node information, THE HealthRenderer SHALL obtain label column styles from ThemeManager or StyleSystem instead of using the hardcoded string `bold white`.
3. WHEN `HealthRenderer._create_shards_panel` renders shard status, THE HealthRenderer SHALL obtain label column styles from ThemeManager or StyleSystem instead of using the hardcoded string `bold white`.
4. WHEN `HealthRenderer._create_performance_panel` renders performance metrics, THE HealthRenderer SHALL obtain label column styles from ThemeManager or StyleSystem instead of using the hardcoded string `bold white`.
5. WHEN `HealthRenderer` determines panel border colors based on cluster health status, THE HealthRenderer SHALL obtain the colors from `health_styles` via ThemeManager instead of using hardcoded strings like `green`, `yellow`, or `red`.

### Requirement 6: Eliminate Hardcoded Colors in Snapshot Renderer

**User Story:** As a theme user, I want snapshot status displays to respect my chosen theme, so that snapshot information is visually consistent.

#### Acceptance Criteria

1. WHEN `SnapshotRenderer.display_snapshot_status` renders snapshot state indicators, THE SnapshotRenderer SHALL obtain state colors from StyleSystem semantic styles instead of using hardcoded strings like `bold green`, `bold yellow`, `bold red`, or `bold white`.
2. WHEN `SnapshotRenderer.display_snapshot_status` renders the status table columns, THE SnapshotRenderer SHALL obtain column styles from ThemeManager or StyleSystem instead of using hardcoded strings like `bold white` and `bold cyan`.
3. WHEN `SnapshotRenderer.display_snapshot_status` renders failure details, THE SnapshotRenderer SHALL obtain failure text styles from StyleSystem semantic styles instead of using hardcoded strings like `bold white`, `white`, and `red`.
4. WHEN `SnapshotRenderer._create_snapshots_panel_legacy` renders the legacy panel, THE SnapshotRenderer SHALL obtain all label and value styles from ThemeManager instead of using hardcoded strings like `bold white`.

### Requirement 7: Eliminate Hardcoded Colors in Recovery Renderer

**User Story:** As a theme user, I want recovery status displays to respect my chosen theme, so that recovery operations are visually consistent.

#### Acceptance Criteria

1. WHEN `RecoveryRenderer._create_recovery_table` assigns row styles based on recovery progress percentage, THE RecoveryRenderer SHALL obtain the row colors from StyleSystem semantic styles instead of using hardcoded strings like `green`, `yellow`, `cyan`, and `red`.
2. WHEN `RecoveryRenderer.create_progress_bar` renders the 25–50% range, THE RecoveryRenderer SHALL obtain the bar color from StyleSystem instead of using the hardcoded string `orange1`.
3. WHEN `RecoveryRenderer.render_enhanced_recovery_status` renders the title panel border, THE RecoveryRenderer SHALL obtain the border color from ThemeManager instead of using the hardcoded string `yellow`.

### Requirement 8: Eliminate Hardcoded Colors in Shard Renderer

**User Story:** As a theme user, I want shard displays to respect my chosen theme, so that shard tables are visually consistent.

#### Acceptance Criteria

1. WHEN `ShardRenderer._create_detailed_shards_table` assigns a background style to UNASSIGNED shard rows, THE ShardRenderer SHALL obtain the background color from ThemeManager (e.g. `row_styles.critical_health`) instead of using the hardcoded string `on dark_red`.

### Requirement 9: Eliminate Hardcoded Colors in Allocation Renderer

**User Story:** As a theme user, I want allocation displays to respect my chosen theme, so that allocation information is visually consistent.

#### Acceptance Criteria

1. WHEN `AllocationRenderer.create_allocation_issues_panel` renders issue counts without StyleSystem, THE AllocationRenderer SHALL obtain fallback colors from ThemeManager instead of using hardcoded strings like `bold red`, `bold yellow`, and `dim`.
2. WHEN `AllocationRenderer.render_allocation_explain_results` renders the title panel body text without StyleSystem, THE AllocationRenderer SHALL obtain the text style from ThemeManager instead of using the hardcoded string `bold white`.

### Requirement 10: Eliminate Hardcoded Colors in Storage Renderer

**User Story:** As a theme user, I want storage displays to respect my chosen theme, so that storage tables are visually consistent.

#### Acceptance Criteria

1. WHEN `StorageRenderer.print_enhanced_storage_table` renders the storage alerts panel, THE StorageRenderer SHALL obtain alert text styles from StyleSystem semantic styles instead of using hardcoded Rich markup strings like `[bold bright_red]`, `[bold red]`, and `[bold yellow]`.
2. WHEN `StorageRenderer.create_usage_progress_bar` renders the empty portion of the bar, THE StorageRenderer SHALL obtain the empty style from ThemeManager instead of using the hardcoded fallback `dim white`.

### Requirement 11: Eliminate Hardcoded Colors in Help System

**User Story:** As a theme user, I want the help command reference to respect my chosen theme, so that the help display is visually consistent.

#### Acceptance Criteria

1. WHEN `show_custom_help` renders the command reference table, THE Help_System SHALL obtain header style, border style, category colors, command colors, description colors, and example colors from ThemeManager `help_styles` instead of using hardcoded strings like `bold white on grey23`, `grey23`, `bold green`, `bold blue`, `bold cyan`, `bold yellow`, `bold white`, `bright_black`, `bold red`, `dim cyan`, and `on grey7`.
2. WHEN `show_custom_help` renders the header and footer panels, THE Help_System SHALL obtain title and footer styles from ThemeManager `help_styles` instead of using hardcoded strings like `bold white`, `bold cyan`, `bold yellow`, and `dim`.

### Requirement 12: Eliminate Hardcoded Colors in Version Renderer

**User Story:** As a theme user, I want the version display to respect my chosen theme, so that version information is visually consistent.

#### Acceptance Criteria

1. WHEN `VersionRenderer._render_banner` renders the ASCII art banner, THE VersionRenderer SHALL obtain gradient colors from ThemeManager or StyleSystem instead of using hardcoded strings like `bold cyan`, `bold blue`, and `bold magenta`.
2. WHEN `VersionRenderer._render_main_version_panel` renders version information rows, THE VersionRenderer SHALL obtain label and value styles from ThemeManager or StyleSystem instead of using hardcoded strings like `bold cyan`, `white`, `bold green`, `dim`, and `bold white on dark_blue`.
3. WHEN `VersionRenderer._render_footer` renders the footer, THE VersionRenderer SHALL obtain text styles from ThemeManager or StyleSystem instead of using hardcoded strings like `bold yellow`, `bold white`, `bold cyan`, and `dim`.

### Requirement 13: Eliminate Hardcoded Colors in Template Renderer

**User Story:** As a theme user, I want template displays to respect my chosen theme, so that template information is visually consistent.

#### Acceptance Criteria

1. WHEN `TemplateRenderer` renders error messages, THE TemplateRenderer SHALL obtain the error text style from StyleSystem semantic styles instead of using the hardcoded string `bold red`.
2. WHEN `TemplateRenderer._print_template_summary` renders the status text, THE TemplateRenderer SHALL obtain the status style from StyleSystem instead of using the hardcoded string `bold green`.

### Requirement 14: Eliminate Hardcoded Colors in ILM Renderer

**User Story:** As a theme user, I want ILM displays to respect my chosen theme, so that lifecycle management information is visually consistent.

#### Acceptance Criteria

1. WHEN `ILMRenderer.print_enhanced_ilm_policy_detail` renders phase panels, THE ILMRenderer SHALL obtain phase border colors from ThemeManager or StyleSystem instead of using hardcoded strings like `red`, `yellow`, `blue`, `cyan`, and `magenta`.
2. WHEN `ILMRenderer.print_enhanced_ilm_policy_detail` renders the indices table header, THE ILMRenderer SHALL obtain the header style from ThemeManager instead of using the hardcoded string `bold white`.

### Requirement 15: Eliminate Hardcoded Colors in Locations Renderer

**User Story:** As a theme user, I want the locations display to respect my chosen theme, so that cluster location information is visually consistent.

#### Acceptance Criteria

1. WHEN `LocationsRenderer._create_locations_table` constructs the zebra stripe style, THE LocationsRenderer SHALL obtain the zebra color from ThemeManager `row_styles.zebra` instead of using the hardcoded fallback `on grey11`.
2. WHEN `LocationsRenderer` renders location details without a styles parameter, THE LocationsRenderer SHALL obtain default styles from ThemeManager instead of using the hardcoded default styles dictionary.

### Requirement 16: Eliminate Hardcoded Colors in Repositories Renderer

**User Story:** As a theme user, I want the repositories display to respect my chosen theme, so that repository information is visually consistent.

#### Acceptance Criteria

1. WHEN `RepositoriesRenderer.print_enhanced_repositories_table` renders the empty-state panel, THE RepositoriesRenderer SHALL obtain markup colors from ThemeManager or StyleSystem instead of using hardcoded Rich markup strings like `[cyan]` and `[bold]`.

### Requirement 17: Eliminate Hardcoded Colors in Replica Renderer

**User Story:** As a theme user, I want replica management displays to respect my chosen theme, so that replica information is visually consistent.

#### Acceptance Criteria

1. WHEN `ReplicaRenderer.render_replica_summary` renders the status column, THE ReplicaRenderer SHALL obtain status colors from StyleSystem semantic styles instead of using hardcoded inline markup strings like `[red]`, `[yellow]`, and `[green]`.

### Requirement 18: Eliminate Hardcoded Colors in Settings Renderer

**User Story:** As a theme user, I want the settings display to respect my chosen theme, so that configuration information is visually consistent.

#### Acceptance Criteria

1. THE SettingsRenderer SHALL route all styling through its `_sem()`, `_border()`, and `_title_style()` helper methods, which resolve styles from ThemeManager and StyleSystem, for all panels and tables it renders.

### Requirement 19: Eliminate Hardcoded Colors in Panel Renderer

**User Story:** As a theme user, I want all panels created by the panel renderer to respect my chosen theme, so that panel styling is visually consistent.

#### Acceptance Criteria

1. WHEN `PanelRenderer.create_status_panel` maps status types to border colors, THE PanelRenderer SHALL obtain the border colors from ThemeManager `panel_styles` instead of using the hardcoded color map (`success: green`, `error: red`, `warning: yellow`, `info: blue`, `secondary: magenta`).

### Requirement 20: Eliminate Hardcoded Colors in Table Renderer

**User Story:** As a theme user, I want all tables created by the table renderer to respect my chosen theme, so that table styling is visually consistent.

#### Acceptance Criteria

1. WHEN `TableRenderer.get_state_color` maps states to colors, THE TableRenderer SHALL obtain the colors from ThemeManager `state_styles` and `health_styles` instead of using the hardcoded color dictionary.
2. WHEN `TableRenderer.print_table_from_dict` renders key-value tables, THE TableRenderer SHALL obtain column styles from ThemeManager instead of using hardcoded strings like `cyan` and `white`.

### Requirement 21: Backward Compatibility for All Existing Themes

**User Story:** As a user of any existing theme, I want the theme overhaul to preserve the visual appearance of all non-Nord themes, so that my preferred theme continues to work correctly.

#### Acceptance Criteria

1. WHEN any existing theme (rich, plain, cyberpunk, cyberpunk_yellow, ocean, midnight, fire, corporate, matrix, solarized) is active, THE ThemeManager SHALL return the same style values as before the overhaul for all style categories.
2. WHEN a theme does not define a `semantic_styles` section, THE StyleSystem SHALL fall back to deriving semantic styles from `panel_styles` and `row_styles` as it does today.
3. WHEN a theme does not define a `help_styles` section, THE Help_System SHALL fall back to reasonable defaults that match the current behavior.
4. IF a theme defines style values using Rich color names (not hex), THEN THE ThemeManager SHALL return those color names unchanged.

### Requirement 22: Eliminate Hardcoded Colors in Datastream Handler

**User Story:** As a theme user, I want datastream displays to respect my chosen theme, so that datastream information is visually consistent.

#### Acceptance Criteria

1. WHEN `DatastreamHandler` renders datastream detail panels, THE DatastreamHandler SHALL obtain label and value column styles from ThemeManager or StyleSystem instead of using hardcoded strings like `bold white`, `cyan`, and `bold cyan`.

### Requirement 23: Eliminate Hardcoded Colors in Snapshot Handler

**User Story:** As a theme user, I want snapshot management operations to respect my chosen theme, so that snapshot command output is visually consistent.

#### Acceptance Criteria

1. WHEN snapshot handler renders snapshot information panels, THE Snapshot_Handler SHALL obtain border styles and label styles from ThemeManager or StyleSystem instead of using hardcoded strings like `bright_blue`, `bold white`, and `bold cyan`.

### Requirement 24: Eliminate Hardcoded Colors in Dangling Handler

**User Story:** As a theme user, I want dangling index displays to respect my chosen theme, so that dangling index information is visually consistent.

#### Acceptance Criteria

1. WHEN `DanglingHandler` renders dangling index panels, THE DanglingHandler SHALL obtain border and text styles from ThemeManager or StyleSystem instead of using hardcoded strings like `orange1`, `bold blue`, `bold yellow`, and `bold red`.

### Requirement 25: Eliminate Hardcoded Colors in Interactive Help

**User Story:** As a theme user, I want the interactive help system to respect my chosen theme, so that help navigation is visually consistent.

#### Acceptance Criteria

1. WHEN `interactive_help` renders help content panels and text, THE Interactive_Help SHALL obtain text styles from ThemeManager `help_styles` instead of using hardcoded strings like `bold blue`, `bold yellow`, `bold green`, `bold magenta`, `bold cyan`, `cyan`, and `dim cyan`.
