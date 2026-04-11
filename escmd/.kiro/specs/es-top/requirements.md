# Requirements Document

## Introduction

`es-top` is a live, auto-refreshing terminal dashboard for Elasticsearch clusters, modeled after the Unix `top` command. It integrates into the existing `escmd.py` CLI utility and uses the Rich library (`rich.live`, `rich.table`) to render a hierarchical, color-coded view of cluster health, node pressure, and index hot-spots. The dashboard polls the cluster at a configurable interval (default 30 seconds) and computes per-poll deltas to derive throughput rates, as well as cumulative session totals since the dashboard started.

The initial scope focuses on the core essentials: cluster health header, node pressure panel, and index hot list with delta rates and session totals. More advanced panels (active operations/recovery, lightweight mode) are deferred to a later phase.

---

## Glossary

- **Dashboard**: The full-screen terminal UI rendered by `es-top`.
- **EsTop**: The top-level component that owns the polling loop, state, and rendering lifecycle.
- **Poller**: The sub-component responsible for issuing Elasticsearch API calls and returning raw data each cycle.
- **DeltaCalculator**: The sub-component that computes per-second rates by diffing successive poll snapshots and accumulates session totals.
- **Renderer**: The sub-component that converts processed data into Rich renderables (tables, panels).
- **ClusterHeader**: The top section of the Dashboard showing cluster-level health metrics.
- **NodePanel**: The Dashboard section showing per-node resource pressure metrics.
- **IndexHotList**: The Dashboard section showing the top write/search-load indices with computed rates and session totals.
- **PollSnapshot**: A timestamped record of raw API responses captured during one poll cycle.
- **RefreshInterval**: The configurable number of seconds between successive poll cycles.
- **HotNode**: A node whose JVM heap usage, CPU, or disk usage exceeds a configured warning threshold.
- **HotIndex**: An index ranked in the top N by docs/sec or searches/sec during the current interval.
- **SessionTotal**: The cumulative count of docs written or searches executed for an index since `es-top` started, accumulated across all poll cycles in the current session.
- **WatermarkBreach**: A condition where a node's disk usage exceeds the Elasticsearch low-watermark threshold.

---

## Requirements

### Requirement 1: Dashboard Lifecycle and Refresh Loop

**User Story:** As an operator, I want `es-top` to continuously refresh the terminal display at a configurable interval, so that I can monitor cluster state in real time without re-running the command.

#### Acceptance Criteria

1. THE EsTop SHALL accept a `--interval` CLI argument specifying the RefreshInterval in seconds, with a default value of 30 seconds and a minimum allowed value of 10 seconds.
2. WHEN the RefreshInterval elapses, THE Poller SHALL issue all required API calls and produce a new PollSnapshot.
3. WHILE the Dashboard is running, THE Renderer SHALL update the terminal display in-place using `rich.live.Live` without clearing the scroll buffer.
4. WHEN the user presses `q` or `Ctrl+C`, THE EsTop SHALL stop the refresh loop and restore the terminal to its prior state.
5. IF a poll cycle takes longer than the RefreshInterval, THEN THE EsTop SHALL begin the next cycle immediately after the previous one completes rather than skipping it.
6. THE EsTop SHALL display the elapsed time since the last successful poll and the configured RefreshInterval in the Dashboard header.
7. THE EsTop SHALL display the wall-clock timestamp of the last successful poll in the Dashboard header, formatted as `HH:MM:SS`.
8. THE EsTop SHALL display a monotonically incrementing poll cycle counter in the Dashboard header, starting at 1 on the first successful poll and incrementing by 1 on each subsequent successful poll.

---

### Requirement 2: Integration with Existing Connection and Configuration System

**User Story:** As an operator, I want `es-top` to use the same cluster connection and authentication configuration as all other `escmd.py` commands, so that I do not need to reconfigure credentials separately.

#### Acceptance Criteria

1. THE EsTop SHALL accept the same `-l` / `--location` argument used by other `escmd.py` commands to select the target cluster from `elastic_servers.yml`.
2. THE EsTop SHALL be registered as a command in `CommandHandler` under the name `es-top`, following the same handler pattern as existing commands.
3. THE EsTop SHALL obtain its Elasticsearch client instance from the existing `es_client` object passed to the command handler, reusing all authentication, SSL, and timeout settings.
4. WHERE the existing `ThemeManager` is available, THE Renderer SHALL apply the active display theme to all Dashboard panels and tables.
5. THE EsTop SHALL be invocable as `./escmd.py es-top` and as `es-top` within the ESTERM interactive terminal.

---

### Requirement 3: Cluster Health Header

**User Story:** As an operator, I want the top section of the dashboard to show cluster-level health at a glance, so that I can immediately identify whether the cluster is in a degraded state.

#### Acceptance Criteria

1. WHEN a PollSnapshot is available, THE ClusterHeader SHALL display the cluster name, overall health status (green / yellow / red), total node count, and data node count sourced from `_cluster/health`.
2. THE ClusterHeader SHALL display active shard count, relocating shard count, initializing shard count, and unassigned shard count.
3. WHEN the unassigned shard count is greater than zero, THE ClusterHeader SHALL render the unassigned shard count in red with a flashing indicator.
4. THE ClusterHeader SHALL map health status values to color-coded indicators: green → `[green]`, yellow → `[yellow]`, red → `[red bold]`.
5. IF the `_cluster/health` API call fails, THEN THE ClusterHeader SHALL display a red error banner with the failure reason and retain the last successful values.

---

### Requirement 4: Node Pressure Panel

**User Story:** As an operator, I want to see the top nodes under the most resource pressure, so that I can quickly identify hot nodes before they cause cluster instability.

#### Acceptance Criteria

1. WHEN a PollSnapshot is available, THE NodePanel SHALL display the top N nodes ranked by JVM heap usage percentage, where N is configurable via `--top-nodes` with a default of 5.
2. THE NodePanel SHALL display for each node: node name, JVM heap used percentage, CPU usage percentage, 1-minute load average, disk used percentage, and disk free bytes, sourced from `_nodes/stats`.
3. WHEN a node's JVM heap usage percentage is 85% or greater, THE NodePanel SHALL render that node's heap cell in red bold.
4. WHEN a node's disk used percentage reaches or exceeds the Elasticsearch low-watermark threshold (default 85%), THE NodePanel SHALL render that node's disk cell in yellow; WHEN it reaches the high-watermark threshold (default 90%), THE NodePanel SHALL render it in red bold.
5. IF the `_nodes/stats` API call fails, THEN THE NodePanel SHALL display a warning banner and retain the last successfully retrieved node data.

---

### Requirement 5: Index Hot List with Delta Rates and Session Totals

**User Story:** As an operator, I want to see which indices have the highest write and search load during the current interval and across the entire watching session, so that I can identify indexing bottlenecks or query hot-spots and understand cumulative activity since I started monitoring.

#### Acceptance Criteria

1. THE DeltaCalculator SHALL compute docs/sec for each index by dividing the difference in `docs.count` between the current and previous PollSnapshot by the elapsed seconds between those snapshots.
2. THE DeltaCalculator SHALL compute searches/sec for each index by dividing the difference in `search.query_total` between the current and previous PollSnapshot by the elapsed seconds between those snapshots.
3. THE DeltaCalculator SHALL accumulate a SessionTotal for each index by summing the per-cycle docs written delta and searches executed delta across all poll cycles since EsTop started.
4. WHEN a PollSnapshot is available and a prior snapshot exists, THE IndexHotList SHALL display only indices that have had at least one doc written or search executed during the current session, capped at the top N indices ranked by docs/sec, where N is configurable via `--top-indices` with a default of 10. *(Note: the cap limit may be increased in a future phase.)*
5. THE IndexHotList SHALL display for each index: index name, docs/sec, searches/sec, session total docs written, session total searches executed, total doc count, and store size, sourced from `_cat/indices` using explicit field selection via the `h` parameter.
6. WHEN only one PollSnapshot exists (first poll), THE IndexHotList SHALL display total counts and session totals without rate columns and indicate that rates will be available after the next poll.
7. IF the `_cat/indices` API call fails, THEN THE IndexHotList SHALL display a warning banner and retain the last successfully computed rates and session totals.

---

### Requirement 6: Active Operations and Recovery Panel *(Deferred — Phase 2)*

**User Story:** As an operator, I want to see active shard recoveries and long-running cluster tasks, so that I can monitor ongoing operations and detect stuck or runaway processes.

> **Status: Deferred.** This panel adds meaningful complexity (additional API calls to `_cat/recovery` and `_tasks`, task duration thresholds, and a separate panel section). It will be implemented in a follow-on phase once the core dashboard is stable.

---

### Requirement 7: Cluster Load Awareness and Polling Strategy *(Deferred — Phase 2)*

**User Story:** As an operator managing large clusters, I want `es-top` to minimize its own impact on cluster performance, so that the monitoring tool does not become a source of load.

> **Status: Deferred.** The `--lightweight` flag, per-request timeout configurability, and poll-cycle duration warnings are useful but non-essential for the initial implementation. The Poller will issue API calls sequentially by default. These controls will be added in a follow-on phase.

---

### Requirement 8: Delta State and Session Total Persistence Across Poll Cycles

**User Story:** As an operator, I want rate calculations and session totals to be accurate across poll cycles, so that docs/sec and searches/sec reflect real throughput and cumulative session counts reflect all activity since monitoring started.

#### Acceptance Criteria

1. THE DeltaCalculator SHALL retain exactly one prior PollSnapshot in memory at all times; WHEN a new PollSnapshot is produced, THE DeltaCalculator SHALL replace the prior snapshot with the new one.
2. THE DeltaCalculator SHALL use the wall-clock timestamp embedded in each PollSnapshot to compute the elapsed interval, rather than assuming the elapsed time equals the configured RefreshInterval.
3. THE DeltaCalculator SHALL maintain a per-index SessionTotal map in memory for the lifetime of the EsTop process, accumulating the docs written delta and searches executed delta from each poll cycle.
4. WHEN an index present in the prior PollSnapshot is absent from the current PollSnapshot, THE DeltaCalculator SHALL omit that index from rate calculations for the current cycle but SHALL retain its SessionTotal in the session map.
5. WHEN an index is new in the current PollSnapshot (not present in the prior snapshot), THE DeltaCalculator SHALL report its rates as zero for the current cycle, initialize its SessionTotal to zero, and include it in the next cycle's delta calculation.
6. FOR ALL valid pairs of successive PollSnapshots, the docs/sec computed by THE DeltaCalculator SHALL equal `(current_docs_count - prior_docs_count) / elapsed_seconds` where elapsed_seconds is derived from the PollSnapshot timestamps (round-trip property for delta calculation correctness).
