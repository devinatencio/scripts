# Implementation Plan: indices-watch-collect-sessions

## Overview

Add a session layer to the index-watch collection system. Each collection run gets its own
subdirectory under the date folder (`<YYYY-MM-DD>/<session_id>/`). An interactive picker lets
the user join an existing session or start a new one. The same logic applies to `es-top --collect`.
All changes are additive: `default_run_dir()` is unchanged and legacy flat date directories
continue to work.

## Tasks

- [x] 1. Add session utility functions to `processors/indices_watch.py`
  - Add `sanitize_session_label(label: str) -> str` — replace `[^a-zA-Z0-9_-]` with `_`, truncate to 40 chars
  - Add `make_session_id(dt: datetime, label: Optional[str] = None) -> str` — format `HHMM` or `HHMM-<label>`
  - Add `resolve_session_dir(cluster_slug, day_iso, *, label, dt) -> Path` — non-conflicting path under `default_run_dir`; appends `-2`, `-3`, … on collision; does NOT create the directory
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 7.3_

  - [ ]* 1.1 Write property test for `sanitize_session_label`
    - **Property 3: Label sanitization**
    - **Validates: Requirements 1.4**

  - [ ]* 1.2 Write property test for `make_session_id`
    - **Property 2: Session ID derivation with optional label**
    - **Validates: Requirements 1.2, 1.3**

  - [ ]* 1.3 Write property test for `resolve_session_dir` path structure
    - **Property 1: Session path structure**
    - **Validates: Requirements 1.1**

  - [ ]* 1.4 Write property test for `resolve_session_dir` collision avoidance
    - **Property 4: Session ID collision avoidance**
    - **Validates: Requirements 1.5**

  - [ ]* 1.5 Write property test for `default_run_dir` unchanged behavior
    - **Property 10: `default_run_dir` unchanged**
    - **Validates: Requirements 7.3**

- [x] 2. Add `SessionInfo` dataclass and `list_sessions()` to `processors/indices_watch.py`
  - Define `SessionInfo` dataclass with fields: `session_id`, `session_dir`, `started_at`, `label`, `sample_count`, `schema_version`
  - Implement `list_sessions(date_dir: Path) -> List[SessionInfo]` — scan for subdirs with `schema_version == 2` `run.json`; sort ascending by `started_at`; skip invalid/missing `run.json`
  - Implement `is_legacy_date_dir(date_dir: Path) -> bool` — returns `True` when flat `.json` sample files exist directly in `date_dir` but no valid session subdirs
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1_

  - [ ]* 2.1 Write property test for `list_sessions` filtering and ordering
    - **Property 9: Session registry filtering and ordering**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

  - [ ]* 2.2 Write property test for `list_sessions` ascending order (most-recent last)
    - **Property 6: Most-recent session selection**
    - **Validates: Requirements 2.7, 5.3, 6.2**

  - [ ]* 2.3 Write property test for legacy flat directory load compatibility
    - **Property 12: Legacy flat directory load compatibility**
    - **Validates: Requirements 5.5, 7.1**

- [x] 3. Update `write_run_metadata` and add `format_session_list` to `processors/indices_watch.py`
  - Extend `write_run_metadata` signature with `session_id: Optional[str] = None` and `label: Optional[str] = None`; write `schema_version: 2` when `session_id` is provided, otherwise keep `schema_version: 1`
  - Add `format_session_list(sessions: List[SessionInfo]) -> str` — numbered list with session_id, start time, sample count, label (or `—` placeholder)
  - _Requirements: 2.2, 3.1, 3.3, 5.8, 6.2_

  - [ ]* 3.1 Write property test for `write_run_metadata` v2 field completeness
    - **Property 7: run.json v2 field completeness**
    - **Validates: Requirements 3.1, 3.3**

  - [ ]* 3.2 Write property test for `format_session_list` display completeness
    - **Property 5: Session listing display completeness**
    - **Validates: Requirements 2.2, 5.8, 6.2**

  - [ ]* 3.3 Write unit tests for `write_run_metadata` v1 vs v2 schema_version
    - Verify v1 written when `session_id` is omitted; v2 written when `session_id` is provided
    - _Requirements: 3.1, 3.3, 7.4_

- [x] 4. Checkpoint — run existing test suite
  - Ensure all existing tests in `tests/unit/processors/test_indices_watch.py` still pass after the changes above.
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement `pick_or_create_session_dir` in `processors/indices_watch.py`
  - Implement the central session-resolution helper with the full decision tree:
    1. `new_session=True` → `resolve_session_dir(...)`, return `(path, True)`
    2. Build `date_dir = default_run_dir(cluster_slug, day_iso)`
    3. `sessions = list_sessions(date_dir)`
    4. `join_latest=True` and sessions → return `(sessions[-1].session_dir, False)`
    5. `join_latest=True` and no sessions → `resolve_session_dir(...)`, return `(path, True)`
    6. No sessions and not legacy → `resolve_session_dir(...)`, return `(path, True)`
    7. Legacy flat dir → show picker with legacy option (or auto-new if not TTY, log notice to stderr)
    8. Sessions exist and not TTY → auto-select `sessions[-1]`, log notice to stderr, return `(sessions[-1].session_dir, False)`
    9. Sessions exist and TTY → show `Session_Picker` via `console`, return based on user choice
  - `--new-session` takes precedence over `--join-latest` when both are set
  - _Requirements: 2.1, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 7.1, 7.2_

  - [ ]* 5.1 Write property test for join-session preserves run.json
    - **Property 8: Join session preserves run.json**
    - **Validates: Requirements 3.2**

  - [ ]* 5.2 Write unit tests for `pick_or_create_session_dir` flag combinations
    - `--new-session` bypasses picker
    - `--join-latest` with and without existing sessions
    - Non-TTY auto-selection with stderr notice
    - No existing sessions → new session created silently
    - Legacy flat dir → picker shows legacy option
    - `--new-session` + `--join-latest` → `--new-session` wins
    - _Requirements: 2.5, 2.6, 2.7, 2.8, 2.9, 7.1, 7.2_

- [x] 6. Add new CLI arguments to `cli/argument_parser.py`
  - Add to `indices-watch-collect` parser: `--new-session`, `--join-latest`, `--label LABEL`
  - Add to `indices-watch-report` parser: `--session SESSION_ID`, `--list-sessions`
  - Add to `es-top` / `top` parser (inside `_add_estop_command`): `--new-session`, `--join-latest`, `--label LABEL`
  - _Requirements: 2.5, 2.6, 2.7, 4.3, 4.4, 4.5, 5.6, 5.8_

  - [ ]* 6.1 Write unit tests for new argument parsing
    - Verify each new flag is accepted and stored under the correct `dest` attribute
    - Verify `--new-session` / `--join-latest` / `--label` on `es-top` parse without error
    - _Requirements: 2.5, 2.6, 2.7, 4.3, 4.4, 4.5, 5.6, 5.8_

- [x] 7. Update `handlers/index_handler.py` — `handle_indices_watch_collect()`
  - Replace the `default_run_dir` + `write_run_metadata` block with a call to `pick_or_create_session_dir(cluster, day_iso, new_session=..., join_latest=..., label=..., console=self.console, is_tty=sys.stdin.isatty())`
  - Read `new_session`, `join_latest`, `label` from `self.args`
  - When `is_new` is `True`: call `write_run_metadata(..., session_id=session_id, label=label)` (v2)
  - When `is_new` is `False` (joining): skip `write_run_metadata` entirely to preserve existing `run.json`
  - _Requirements: 2.1, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2_

  - [ ]* 7.1 Write unit tests for `handle_indices_watch_collect` session integration
    - `--output-dir` bypasses session logic entirely (direct path, no picker)
    - `--new-session` creates a fresh session dir and writes v2 `run.json`
    - `--join-latest` with existing session skips `write_run_metadata`
    - _Requirements: 2.5, 3.1, 3.2_

- [x] 8. Update `commands/estop_commands.py` — `EsTopDashboard.__init__()`
  - Add `new_session`, `join_latest`, `label` constructor parameters (default `False`, `False`, `None`)
  - In the `if self.collect:` block, replace the `default_run_dir` + `write_run_metadata` call with `pick_or_create_session_dir(...)` when `collect_dir` is `None`
  - When `collect_dir` is given, keep the existing direct-path behavior unchanged
  - When `is_new` is `True`: call `write_run_metadata(..., session_id=..., label=...)` (v2)
  - When `is_new` is `False`: skip `write_run_metadata`
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 9. Update `handlers/estop_handler.py` to pass new session args to `EsTopDashboard`
  - Read `new_session`, `join_latest`, `label` from `self.args` (with `getattr` defaults)
  - Pass them through to `EsTopDashboard(...)` constructor
  - _Requirements: 4.1, 4.3, 4.4, 4.5_

  - [ ]* 9.1 Write unit tests for `EsTopDashboard` session integration
    - `collect=True`, `collect_dir=None` → calls `pick_or_create_session_dir`
    - `collect=True`, `collect_dir=<path>` → uses direct path, no session logic
    - _Requirements: 4.1, 4.2_

- [x] 10. Checkpoint — run full test suite
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Update `run_indices_watch_report` in `processors/indices_watch.py` for session-aware loading
  - Before the existing sample-loading block, handle `--list-sessions`: call `list_sessions(date_dir)`, print via `format_session_list`, and return early
  - Handle `--session SESSION_ID`: look up the matching `SessionInfo` in `list_sessions(date_dir)`; if not found, print error listing available sessions and raise `SystemExit(1)`
  - When `--dir` is not supplied and `--session` is not supplied: detect whether the date dir has sessions or is legacy
    - Multiple sessions + TTY → show picker, load selected session
    - Multiple sessions + non-TTY → auto-select latest, log notice to stderr
    - Exactly one session → load it without prompting
    - Legacy flat dir → load directly (existing behavior)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 7.4_

  - [ ]* 11.1 Write property test for legacy v1 run.json backward compatibility
    - **Property 11: Legacy v1 run.json backward compatibility**
    - **Validates: Requirements 7.4**

  - [ ]* 11.2 Write unit tests for `indices-watch-report` session selection
    - `--dir` supplied → load directly, no session logic
    - `--session <id>` happy path → loads correct session dir
    - `--session <id>` not found → prints error with available sessions, exits non-zero
    - `--list-sessions` → prints session list and exits without report
    - Single session in date dir → loads without prompting
    - Non-TTY with multiple sessions → auto-selects latest, logs notice
    - Legacy flat dir → loads flat files directly
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

- [x] 12. Extend `tests/unit/processors/test_indices_watch.py` with session unit tests
  - Add example-based tests for `sanitize_session_label` edge cases (empty string, all-invalid chars, exactly-40-char truncation)
  - Add example-based tests for `make_session_id` (no label, with label, label sanitization applied)
  - Add example-based tests for `resolve_session_dir` (no collision, single collision, multiple collisions)
  - Add example-based tests for `list_sessions` (empty dir, one valid session, mixed valid/invalid subdirs, legacy flat dir)
  - Add example-based tests for `is_legacy_date_dir` (flat files only, sessions only, mixed, empty)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.2, 6.3, 6.4, 7.1_

- [x] 13. Final checkpoint — ensure all tests pass
  - Run the full test suite including all new property-based and unit tests.
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests live in `tests/test_indices_watch_sessions.py` (new file); unit tests extend `tests/unit/processors/test_indices_watch.py`
- `default_run_dir()` is intentionally left unchanged; all session resolution goes through `resolve_session_dir` / `pick_or_create_session_dir`
- When joining an existing session, `write_run_metadata` must NOT be called — the original `run.json` must be preserved byte-for-byte
- `--new-session` takes precedence over `--join-latest` when both flags are set
