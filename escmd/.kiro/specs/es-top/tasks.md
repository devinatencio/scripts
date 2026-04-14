# Implementation Plan: es-top

## Overview

Implement the `es-top` live terminal dashboard as a self-contained feature integrated into the existing `escmd.py` CLI. The implementation follows the existing handler pattern and is decomposed into four focused components (`EsTopPoller`, `DeltaCalculator`, `EsTopRenderer`, `EsTopDashboard`) connected by plain dataclasses, with a thin `EsTopHandler` entry point registered in `CommandHandler`.

## Tasks

- [x] 1. Define data models in `commands/estop_commands.py`
  - Create `commands/estop_commands.py` with all dataclass definitions: `PollSnapshot` (frozen), `SessionTotals`, `IndexDelta`, `NodeStat`, and `ProcessedData`
  - Ensure `PollSnapshot` uses `frozen=True` and carries per-field error strings alongside optional API response fields
  - Ensure `ProcessedData` carries all cluster header fields, `top_nodes: List[NodeStat]`, `top_indices: List[IndexDelta]`, `is_first_poll: bool`, `poll_count: int`, `last_poll_time: datetime`, and all three error fields
  - _Requirements: 3.1, 3.2, 4.2, 5.1, 5.2, 5.3, 8.1, 8.2_

- [x] 2. Implement `EsTopPoller`
  - [x] 2.1 Add `EsTopPoller` class to `commands/estop_commands.py`
    - Implement `poll() -> PollSnapshot` issuing the three API calls sequentially: `es_client.es.cluster.health()`, `es_client.es.nodes.stats(metric='indices,os,jvm,fs')`, and `es_client.es.cat.indices(h='index,docs.count,search.query_total,store.size,pri,rep', format='json')`
    - Wrap each call in an independent `try/except`; on failure set the field to `None` and populate the corresponding `_error` string
    - Set `timestamp=datetime.now()` on the snapshot
    - _Requirements: 1.2, 2.3, 3.5, 4.5, 5.7_

  - [x] 2.2 Write unit tests for `EsTopPoller` in `tests/test_estop.py`
    - Mock `es_client.es`; verify `poll()` returns a fully-populated `PollSnapshot` on success
    - Verify each API failure independently sets the corresponding field to `None` and populates the error string while the other two fields remain populated
    - _Requirements: 3.5, 4.5, 5.7_

- [x] 3. Implement `DeltaCalculator`
  - [x] 3.1 Add `DeltaCalculator` class to `commands/estop_commands.py`
    - Implement `process(snapshot: PollSnapshot) -> ProcessedData` computing cluster header fields from `cluster_health`, extracting `NodeStat` list from `nodes_stats`, and computing `IndexDelta` list from `cat_indices` vs prior snapshot
    - On first poll (`_prior is None`), return `ProcessedData` with `is_first_poll=True`, zero rates, and empty `top_indices`
    - Compute `elapsed_seconds` from `(current.timestamp - prior.timestamp).total_seconds()`; never use the configured interval for rate math
    - For each index in current snapshot: if absent from prior → `docs_per_sec=0`, `searches_per_sec=0`, initialize `SessionTotals` to zero; if present in prior → compute rates using the formula; accumulate `SessionTotals`
    - For each index in prior snapshot absent from current → retain its `SessionTotals` entry unchanged, omit from `top_indices`
    - Replace `_prior` with the new snapshot after computation
    - Implement `reset()` to clear `_prior`, `_session_totals`, and `_poll_count`
    - _Requirements: 5.1, 5.2, 5.3, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 1.7, 1.8_

  - [x] 3.2 Write property test: rate computation formula (Property 2)
    - **Property 2: Rate computation formula**
    - **Validates: Requirements 5.1, 5.2, 8.2, 8.6**
    - `@given` two snapshots with generated doc/search counts and a `timedelta(seconds≥1)` between timestamps; verify `docs_per_sec == (curr_docs - prior_docs) / elapsed` and `searches_per_sec == (curr_searches - prior_searches) / elapsed` for each index

  - [ ]* 3.3 Write property test: session total accumulation invariant (Property 3)
    - **Property 3: Session total accumulation invariant**
    - **Validates: Requirements 5.3, 8.3**
    - `@given` a list of monotonically increasing doc count sequences (min_size=2); simulate N poll cycles; verify `session_docs` equals the sum of all per-cycle deltas and is monotonically non-decreasing

  - [ ]* 3.4 Write property test: single prior snapshot invariant (Property 4)
    - **Property 4: Single prior snapshot invariant**
    - **Validates: Requirements 8.1**
    - `@given` a list of generated `PollSnapshot` values (min_size=1); process each in sequence; verify `_prior` is always the most recently processed snapshot

  - [ ]* 3.5 Write property test: disappeared index retains session total (Property 5)
    - **Property 5: Disappeared index retains session total**
    - **Validates: Requirements 8.4**
    - `@given` prior snapshot with index set A, current snapshot with index set B ⊂ A; verify missing indices are absent from `top_indices` but their `SessionTotals` remain in `_session_totals` unchanged

  - [ ]* 3.6 Write property test: new index initializes to zero rates (Property 6)
    - **Property 6: New index initializes to zero rates**
    - **Validates: Requirements 8.5**
    - `@given` prior snapshot with index set A, current snapshot with A ∪ {new_index}; verify new index has `docs_per_sec=0`, `searches_per_sec=0`, and `SessionTotals(0, 0)`

  - [x] 3.7 Write property test: poll counter monotonicity (Property 12)
    - **Property 12: Poll counter monotonicity**
    - **Validates: Requirements 1.8**
    - `@given(st.lists(st.builds(PollSnapshot, ...), min_size=1, max_size=20))`: process each snapshot in sequence; verify `poll_count` equals the 1-based index of each call; call `reset()` and verify the next `process()` returns `poll_count = 1`

  - [x] 3.8 Wrgite unit tests for `DeltaCalculator`
    - Verify first poll returns `is_first_poll=True` with empty `top_indices`
    - Verify `reset()` clears `_prior`, `_session_totals`, and `_poll_count`
    - Verify elapsed time is derived from snapshot timestamps, not the configured interval
    - Verify `poll_count` increments by 1 on each `process()` call
    - _Requirements: 5.1, 5.2, 5.3, 8.1, 8.2, 8.3, 8.4, 8.5, 1.7, 1.8_

- [ ] 4. Checkpoint — ensure data model and calculator tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement `EsTopRenderer`
  - [x] 5.1 Add `EsTopRenderer` class to `commands/estop_commands.py`
    - Implement `render(data: ProcessedData) -> RenderableType` returning a `rich.console.Group` (or `Layout`) containing the three sections
    - Implement `_render_cluster_header(data)` as a `Panel` showing cluster name, health status (color-coded via `_health_style`), total nodes, data nodes, active/relocating/initializing/unassigned shards, poll counter (`Poll #N`), and last-polled timestamp (`HH:MM:SS`); render unassigned count in red when `> 0`; show red error banner when `cluster_health_error` is set
    - Implement `_render_node_panel(data)` as a `Table` with columns: node name, heap %, CPU %, load 1m, disk used %, disk free; apply `_heap_style` and `_disk_style` per cell; show yellow warning banner when `nodes_stats_error` is set
    - Implement `_render_index_hot_list(data)` as a `Table`; when `is_first_poll=True` show total counts and session totals without rate columns and include a note that rates will be available after the next poll; when `is_first_poll=False` show all columns; show yellow warning banner when `cat_indices_error` is set
    - Implement `_health_style`, `_heap_style`, `_disk_style` threshold helpers
    - Use `StyleSystem(theme_manager)` when `theme_manager` is provided, else `StyleSystem()` with no args
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.4, 5.5, 5.6, 5.7_

  - [x] 5.2 Write property test: node panel threshold styling (Property 7)
    - **Property 7: Node panel threshold styling**
    - **Validates: Requirements 4.3, 4.4**
    - `@given(st.floats(min_value=0, max_value=100))`: call `_heap_style(pct)` and `_disk_style(pct)`; verify `'red bold'` when `heap_pct >= 85`; verify `'red bold'` when `disk_pct >= 90`, `'yellow'` when `85 <= disk_pct < 90`, default otherwise

  - [ ]* 5.3 Write property test: cluster header completeness (Property 8)
    - **Property 8: Cluster header completeness**
    - **Validates: Requirements 3.1, 3.2, 1.7, 1.8**
    - `@given` generated `ProcessedData` with non-None `cluster_health` fields; render `ClusterHeader`; verify cluster name, status, total nodes, data nodes, active shards, relocating shards, initializing shards, unassigned shards, poll counter, and last-polled timestamp all appear in the rendered output string

  - [ ]* 5.4 Write property test: unassigned shard red styling (Property 9)
    - **Property 9: Unassigned shard red styling**
    - **Validates: Requirements 3.3**
    - `@given(st.integers(min_value=0, max_value=10000))`: build `ProcessedData` with generated `unassigned_shards`; render `ClusterHeader`; verify red styling present iff `unassigned_shards > 0`

  - [ ]* 5.5 Write property test: index hot list completeness and cap (Property 10)
    - **Property 10: Index hot list completeness and cap**
    - **Validates: Requirements 5.4, 5.5**
    - `@given` generated list of `IndexDelta` objects (0–50) and `top_indices` N (1–20); build `ProcessedData` with `is_first_poll=False`; render `IndexHotList`; verify displayed row count ≤ N and each row contains all required fields

  - [ ]* 5.6 Write unit tests for `EsTopRenderer`
    - Verify first-poll rendering omits rate columns and shows the "rates available after next poll" message
    - Verify health status color mapping (green/yellow/red)
    - Verify error banners appear when error fields are set in `ProcessedData`
    - _Requirements: 3.4, 3.5, 4.5, 5.6, 5.7_

- [x] 6. Implement `EsTopDashboard` and `EsTopHandler`
  - [x] 6.1 Add `EsTopDashboard` class to `commands/estop_commands.py`
    - Implement `run()` entering `rich.live.Live` context and calling `_poll_loop(live)`; catch `KeyboardInterrupt` to exit cleanly; ensure `Live` context manager restores terminal on exit
    - Implement `_poll_loop(live)`: record `cycle_start = time.monotonic()`; call `poller.poll()`, `delta_calc.process(snapshot)`, `renderer.render(processed)`, `live.update(layout)`; compute `sleep_time = max(0, interval - elapsed)`; sleep
    - Implement `_stop()` to set the stop flag
    - Clamp `interval = max(10, interval)` in `__init__`
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6_

  - [x] 6.2 Create `handlers/estop_handler.py` with `EsTopHandler`
    - Extend `BaseHandler`; implement `handle_es_top()` reading `--interval`, `--top-nodes`, `--top-indices` from `self.args` with defaults (30, 5, 10); clamp interval to `max(10, interval)`; construct `EsTopDashboard` and call `run()`
    - _Requirements: 1.1, 2.2, 2.3_

  - [ ]* 6.3 Write property test: interval validation clamps to minimum (Property 1)
    - **Property 1: Interval validation clamps to minimum**
    - **Validates: Requirements 1.1**
    - `@given(st.integers())`: construct `EsTopDashboard` with generated interval; verify effective interval equals `max(10, input_value)`

  - [ ]* 6.4 Write property test: next-cycle scheduling after slow poll (Property 11)
    - **Property 11: Next-cycle scheduling after slow poll**
    - **Validates: Requirements 1.5**
    - `@given(st.floats(min_value=0, max_value=120), st.integers(min_value=10, max_value=120))`: compute `max(0, interval - poll_duration)`; verify result is always ≥ 0 and equals the expected formula

  - [ ]* 6.5 Write unit tests for `EsTopHandler`
    - Verify `handle_es_top` clamps interval to 10 for sub-minimum inputs
    - Verify correct args are passed to `EsTopDashboard`
    - _Requirements: 1.1, 2.2_

- [x] 7. Register `es-top` in `CommandHandler`
  - Add `from handlers.estop_handler import EsTopHandler` import to `command_handler.py`
  - Instantiate `self.estop_handler = EsTopHandler(es_client, args, console, config_file, location_config, current_location, logger)` in `CommandHandler.__init__`
  - Add `"es-top": self.estop_handler.handle_es_top` to the `command_handlers` dict in `execute()`
  - _Requirements: 2.2, 2.5_

  - [ ]* 7.1 Write unit test: command registration
    - Verify `'es-top'` key exists in the `command_handlers` dict inside `CommandHandler.execute()`
    - _Requirements: 2.2_

- [x] 8. Implement hot indicator display mode
  - [x] 8.1 Add `get_estop_hot_indicator()` to `ConfigurationManager`
    - Read `es_top.hot_indicator` from `escmd.yml`; validate against `{'emoji', 'color', 'both', 'none'}`; return `'emoji'` as default and for any invalid value
    - _Requirements: 9.2, 9.9_

  - [x] 8.2 Add `hot_indicator` field to `ProcessedData` and thread it through `EsTopDashboard` → `DeltaCalculator.process()` → `ProcessedData`
    - `EsTopDashboard.__init__` reads `hot_indicator` from config (via `ConfigurationManager.get_estop_hot_indicator()`) and passes it to `DeltaCalculator.process()` each cycle
    - `ProcessedData` gains a `hot_indicator: str = "emoji"` field
    - _Requirements: 9.1, 9.2_

  - [x] 8.3 Add `_hot_prefix(rank, mode)` helper to `EsTopRenderer`
    - Returns `'🔥 '` for rank 0 when mode is `emoji` or `both`
    - Returns `'🌡️ '` for rank 1 when mode is `emoji` or `both`
    - Returns `''` for rank ≥ 2, or when mode is `color` or `none`
    - _Requirements: 9.3, 9.7, 9.8_

  - [x] 8.4 Update `_render_index_hot_list` to apply hot indicator
    - Indices are already sorted by `docs_per_sec` descending; use rank position (0, 1, …) to call `_hot_prefix`
    - WHEN mode is `emoji` or `none`: skip `_index_activity_style` (use default row style)
    - WHEN mode is `color` or `both`: apply existing `_index_activity_style` relative color coding
    - Prepend the prefix from `_hot_prefix` to the index name `Text` object
    - _Requirements: 9.3, 9.4, 9.5, 9.6_

  - [x] 8.5 Update `_render_node_panel` to apply hot indicator to node names
    - Nodes are already sorted by `heap_pct` descending; apply `_hot_prefix(rank, mode)` to node name column
    - _Requirements: 9.7, 9.8_

  - [x] 8.6 Add `hot_indicator: emoji` to `escmd.yml` under `es_top` section with a comment listing valid values
    - _Requirements: 9.2_

  - [ ]* 8.7 Write property test: hot indicator prefix correctness (Property 13)
    - **Property 13: Hot indicator prefix correctness**
    - **Validates: Requirements 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
    - `@given(st.sampled_from(['emoji', 'color', 'both', 'none']), st.integers(min_value=0, max_value=5))`: call `_hot_prefix(rank, mode)`; verify 🔥 returned for rank 0 with emoji/both, 🌡️ for rank 1 with emoji/both, empty string otherwise

  - [ ]* 8.8 Write unit tests for hot indicator
    - Verify `get_estop_hot_indicator()` returns `'emoji'` for missing/invalid config values
    - Verify `_render_index_hot_list` prepends 🔥 to the top index name when mode is `emoji`
    - Verify no emoji appears when mode is `none`
    - Verify color coding is absent when mode is `emoji`, present when mode is `color`
    - _Requirements: 9.1–9.9_

- [ ] 9. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests use [Hypothesis](https://hypothesis.readthedocs.io/) with `@settings(max_examples=100)`
- Unit tests and property tests both live in `tests/test_estop.py`
- `EsTopDashboard` and all supporting classes live in `commands/estop_commands.py`; only `EsTopHandler` lives in `handlers/estop_handler.py`
