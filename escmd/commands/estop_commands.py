"""
es-top components: data models for the live Elasticsearch terminal dashboard.

This module contains all dataclass definitions used by the es-top feature,
including PollSnapshot (raw API responses), SessionTotals (per-index cumulative
counters), IndexDelta (per-cycle computed rates), NodeStat (per-node metrics),
and ProcessedData (the full output of DeltaCalculator consumed by EsTopRenderer).
"""

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Deque

from rich.panel import Panel
from rich.table import Table
from rich.console import Group
from rich.text import Text
from rich.columns import Columns
from rich import box

from display.style_system import StyleSystem


@dataclass(frozen=True)
class PollSnapshot:
    """Immutable record of one poll cycle's raw API responses."""

    timestamp: datetime                          # wall-clock time of this poll
    cluster_health: Optional[Dict[str, Any]]     # _cluster/health response; None on failure
    nodes_stats: Optional[Dict[str, Any]]        # _nodes/stats response; None on failure
    cat_indices: Optional[List[Dict[str, Any]]]  # _cat/indices response; None on failure
    cluster_health_error: Optional[str] = None   # error message if cluster_health is None
    nodes_stats_error: Optional[str] = None      # error message if nodes_stats is None
    cat_indices_error: Optional[str] = None      # error message if cat_indices is None


@dataclass
class SessionTotals:
    """Per-index cumulative counters accumulated across all poll cycles."""

    docs_written: int = 0       # sum of per-cycle docs.count deltas
    searches_executed: int = 0  # sum of per-cycle search.query_total deltas


@dataclass
class IndexDelta:
    """Per-index computed values for one poll cycle."""

    index_name: str
    docs_per_sec: float          # (current_docs - prior_docs) / elapsed_seconds
    searches_per_sec: float      # (current_searches - prior_searches) / elapsed_seconds
    session_docs: int            # cumulative docs written this session
    session_searches: int        # cumulative searches this session
    total_docs: int              # current total doc count
    store_size: str              # human-readable store size from _cat/indices


@dataclass
class NodeStat:
    """Per-node extracted metrics."""

    name: str
    heap_pct: float       # JVM heap used %
    cpu_pct: float        # OS CPU %
    load_1m: float        # 1-minute load average
    disk_used_pct: float  # disk used %
    disk_free_bytes: int  # disk available bytes


@dataclass
class ProcessedData:
    """Complete output of DeltaCalculator.process(), consumed by EsTopRenderer."""

    snapshot: PollSnapshot           # the current snapshot (for error banners)
    is_first_poll: bool              # True if no prior snapshot existed
    elapsed_since_poll: float        # seconds since this snapshot's timestamp (for header)
    interval: int                    # configured refresh interval (for header)

    # Poll tracking
    poll_count: int                  # number of successful polls since EsTop started (1-based)
    last_poll_time: datetime         # wall-clock time of the current snapshot (for header display)
    session_start: datetime          # wall-clock time when the session began (for uptime display)

    # Cluster header data
    cluster_name: str
    cluster_status: str              # 'green' | 'yellow' | 'red'
    total_nodes: int
    data_nodes: int
    active_shards: int
    relocating_shards: int
    initializing_shards: int
    unassigned_shards: int

    # Node panel data (pre-sorted, top N)
    top_nodes: List[NodeStat]

    # Per-node metric history for sparklines: name → deque of (heap_pct, cpu_pct)
    node_history: Dict[str, "Deque"]

    # Index hot list data (pre-sorted, top N, only active indices)
    top_indices: List[IndexDelta]

    # Error states (None = no error)
    cluster_health_error: Optional[str]
    nodes_stats_error: Optional[str]
    cat_indices_error: Optional[str]

    # Names of indices flagged as abnormal by indices-analyze (empty if not available)
    abnormal_indices: frozenset = field(default_factory=frozenset)

    # Hot indicator display mode: 'emoji' | 'color' | 'both' | 'none' (from config)
    hot_indicator: str = "emoji"


class EsTopPoller:
    """Issues the three required API calls and packages results into a PollSnapshot."""

    def __init__(self, es_client) -> None:
        self.es_client = es_client

    def poll(self) -> PollSnapshot:
        """
        Issue _cluster/health, _nodes/stats, _cat/indices and return a PollSnapshot.
        Each call is wrapped in try/except; failures set the corresponding field to None
        and record the error message.
        """
        cluster_health, cluster_health_error = self._fetch_cluster_health()
        nodes_stats, nodes_stats_error = self._fetch_nodes_stats()
        cat_indices, cat_indices_error = self._fetch_cat_indices()

        return PollSnapshot(
            timestamp=datetime.now(),
            cluster_health=cluster_health,
            nodes_stats=nodes_stats,
            cat_indices=cat_indices,
            cluster_health_error=cluster_health_error,
            nodes_stats_error=nodes_stats_error,
            cat_indices_error=cat_indices_error,
        )

    def _fetch_cluster_health(self):
        """Returns (data, error_str) tuple for cluster health API call."""
        try:
            response = self.es_client.es.cluster.health()
            data = response.body if hasattr(response, 'body') else response
            return data, None
        except Exception as e:
            return None, str(e)

    def _fetch_nodes_stats(self):
        """Returns (data, error_str) tuple for nodes stats API call."""
        try:
            response = self.es_client.es.nodes.stats(metric='indices,os,jvm,fs')
            data = response.body if hasattr(response, 'body') else response
            return data, None
        except Exception as e:
            return None, str(e)

    def _fetch_cat_indices(self):
        """Returns (data, error_str) tuple for cat indices API call."""
        try:
            response = self.es_client.es.cat.indices(
                h='index,docs.count,search.query_total,store.size,pri,rep,indexing.index_total',
                format='json',
            )
            data = response.body if hasattr(response, 'body') else response
            return data, None
        except Exception as e:
            return None, str(e)


class DeltaCalculator:
    """Pure computation component. Holds the prior PollSnapshot and session totals map."""

    def __init__(self) -> None:
        self._prior: Optional[PollSnapshot] = None
        self._session_totals: Dict[str, SessionTotals] = {}  # index_name → SessionTotals
        self._poll_count: int = 0                            # incremented on each successful process() call
        self._session_start: datetime = datetime.now()       # wall-clock time when DeltaCalculator was created
        self._node_history: Dict[str, deque] = {}            # node name → deque[(heap_pct, cpu_pct)]

    def process(
        self,
        snapshot: PollSnapshot,
        interval: int = 30,
        top_nodes: int = 5,
        top_indices: int = 10,
        abnormal_indices: frozenset = frozenset(),
        hot_indicator: str = "emoji",
    ) -> ProcessedData:
        """
        Compute rates and session totals from snapshot vs prior.
        Replaces prior with snapshot after computation.
        Returns ProcessedData with is_first_poll=True if no prior exists.
        """
        # 1. Extract cluster header fields
        ch = snapshot.cluster_health
        if ch is not None:
            cluster_name = ch.get('cluster_name', 'unknown')
            cluster_status = ch.get('status', 'unknown')
            total_nodes = ch.get('number_of_nodes', 0)
            data_nodes = ch.get('number_of_data_nodes', 0)
            active_shards = ch.get('active_shards', 0)
            relocating_shards = ch.get('relocating_shards', 0)
            initializing_shards = ch.get('initializing_shards', 0)
            unassigned_shards = ch.get('unassigned_shards', 0)
        else:
            cluster_name = 'unknown'
            cluster_status = 'unknown'
            total_nodes = 0
            data_nodes = 0
            active_shards = 0
            relocating_shards = 0
            initializing_shards = 0
            unassigned_shards = 0

        # 2. Extract NodeStat list
        nodes: List[NodeStat] = []
        if snapshot.nodes_stats is not None:
            for _node_id, node in snapshot.nodes_stats.get('nodes', {}).items():
                name = node.get('name', '')
                heap_pct = float(
                    (node.get('jvm') or {})
                    .get('mem', {})
                    .get('heap_used_percent', 0.0) or 0.0
                )
                cpu_pct = float(
                    (node.get('os') or {})
                    .get('cpu', {})
                    .get('percent', 0.0) or 0.0
                )
                load_1m = float(
                    (node.get('os') or {})
                    .get('cpu', {})
                    .get('load_average', {})
                    .get('1m', 0.0) or 0.0
                )
                fs_total = (node.get('fs') or {}).get('total', {})
                total_bytes = fs_total.get('total_in_bytes', 0) or 0
                available_bytes = fs_total.get('available_in_bytes', 0) or 0
                if total_bytes > 0:
                    disk_used_pct = (total_bytes - available_bytes) / total_bytes * 100.0
                else:
                    disk_used_pct = 0.0
                disk_free_bytes = available_bytes

                nodes.append(NodeStat(
                    name=name,
                    heap_pct=heap_pct,
                    cpu_pct=cpu_pct,
                    load_1m=load_1m,
                    disk_used_pct=disk_used_pct,
                    disk_free_bytes=disk_free_bytes,
                ))

        nodes.sort(key=lambda n: n.heap_pct, reverse=True)
        computed_top_nodes = nodes[:top_nodes]

        # Update per-node sparkline history (all nodes, not just top N)
        _HISTORY_LEN = 10
        seen_names = set()
        for node in nodes:
            seen_names.add(node.name)
            if node.name not in self._node_history:
                self._node_history[node.name] = deque(maxlen=_HISTORY_LEN)
            self._node_history[node.name].append((node.heap_pct, node.cpu_pct))
        # Prune history for nodes that have disappeared
        for gone in set(self._node_history) - seen_names:
            del self._node_history[gone]

        # 3. Compute IndexDelta list
        is_first_poll = self._prior is None
        cat_indices_error = snapshot.cat_indices_error

        if snapshot.cat_indices is None:
            # API failure — return empty top_indices with last known data if available
            computed_top_indices: List[IndexDelta] = []
        elif is_first_poll:
            # First poll — no prior to diff against; initialize session totals
            for row in snapshot.cat_indices:
                idx = row.get('index', '')
                if idx and idx not in self._session_totals:
                    self._session_totals[idx] = SessionTotals()
            computed_top_indices = []
        else:
            prior = self._prior
            elapsed = self._elapsed_seconds(snapshot, prior)

            # Build prior index map
            prior_map: Dict[str, Any] = {}
            if prior.cat_indices is not None:
                prior_map = {row['index']: row for row in prior.cat_indices if 'index' in row}

            index_deltas: List[IndexDelta] = []
            for row in snapshot.cat_indices:
                idx = row.get('index', '')
                if not idx:
                    continue

                # Parse current counts
                raw_docs = row.get('docs.count')
                raw_searches = row.get('search.query_total')
                raw_index_total = row.get('indexing.index_total')
                cur_docs = int(raw_docs) if raw_docs not in (None, '') else 0
                cur_searches = int(raw_searches) if raw_searches not in (None, '') else 0
                cur_index_total = int(raw_index_total) if raw_index_total not in (None, '') else 0

                if idx in prior_map:
                    p_row = prior_map[idx]
                    p_raw_docs = p_row.get('docs.count')
                    p_raw_searches = p_row.get('search.query_total')
                    p_raw_index_total = p_row.get('indexing.index_total')
                    p_docs = int(p_raw_docs) if p_raw_docs not in (None, '') else 0
                    p_searches = int(p_raw_searches) if p_raw_searches not in (None, '') else 0
                    p_index_total = int(p_raw_index_total) if p_raw_index_total not in (None, '') else 0

                    # Use indexing.index_total for rate (updates immediately, no refresh lag)
                    # Fall back to docs.count delta if index_total unavailable
                    if cur_index_total > 0 or p_index_total > 0:
                        doc_delta = max(0, cur_index_total - p_index_total)
                    else:
                        doc_delta = max(0, cur_docs - p_docs)
                    search_delta = max(0, cur_searches - p_searches)

                    if elapsed > 0:
                        docs_per_sec = doc_delta / elapsed
                        searches_per_sec = search_delta / elapsed
                    else:
                        docs_per_sec = 0.0
                        searches_per_sec = 0.0

                    # Accumulate session totals
                    if idx not in self._session_totals:
                        self._session_totals[idx] = SessionTotals()
                    self._session_totals[idx].docs_written += doc_delta
                    self._session_totals[idx].searches_executed += search_delta
                else:
                    # New index not in prior — zero rates this cycle per spec (Property 6 / Req 8.5).
                    # Seed session totals from index_total (or docs count) so the index passes
                    # the active filter and appears in the hot list; real deltas start next cycle.
                    docs_per_sec = 0.0
                    searches_per_sec = 0.0
                    if idx not in self._session_totals:
                        seed_docs = cur_index_total if cur_index_total > 0 else cur_docs
                        self._session_totals[idx] = SessionTotals(
                            docs_written=seed_docs,
                            searches_executed=cur_searches,
                        )

                totals = self._session_totals[idx]
                index_deltas.append(IndexDelta(
                    index_name=idx,
                    docs_per_sec=docs_per_sec,
                    searches_per_sec=searches_per_sec,
                    session_docs=totals.docs_written,
                    session_searches=totals.searches_executed,
                    total_docs=cur_docs,
                    store_size=row.get('store.size', ''),
                ))

            # Filter to only active indices
            active = [d for d in index_deltas if d.session_docs > 0 or d.session_searches > 0]
            active.sort(key=lambda d: d.docs_per_sec, reverse=True)
            computed_top_indices = active[:top_indices]

        # 4. Elapsed since poll
        elapsed_since_poll = (datetime.now() - snapshot.timestamp).total_seconds()

        # 5. Replace prior
        self._prior = snapshot

        # 6. Increment poll counter
        self._poll_count += 1

        # 7. Return ProcessedData
        return ProcessedData(
            snapshot=snapshot,
            is_first_poll=is_first_poll,
            elapsed_since_poll=elapsed_since_poll,
            interval=interval,
            poll_count=self._poll_count,
            last_poll_time=snapshot.timestamp,
            session_start=self._session_start,
            cluster_name=cluster_name,
            cluster_status=cluster_status,
            total_nodes=total_nodes,
            data_nodes=data_nodes,
            active_shards=active_shards,
            relocating_shards=relocating_shards,
            initializing_shards=initializing_shards,
            unassigned_shards=unassigned_shards,
            top_nodes=computed_top_nodes,
            node_history=dict(self._node_history),
            top_indices=computed_top_indices,
            abnormal_indices=abnormal_indices,
            hot_indicator=hot_indicator,
            cluster_health_error=snapshot.cluster_health_error,
            nodes_stats_error=snapshot.nodes_stats_error,
            cat_indices_error=cat_indices_error,
        )
    def _elapsed_seconds(self, current: PollSnapshot, prior: PollSnapshot) -> float:
        """Returns elapsed time between two snapshots in seconds."""
        return (current.timestamp - prior.timestamp).total_seconds()

    def reset(self) -> None:
        """Clear prior snapshot, session totals, poll counter, and node history (used on reconnect)."""
        self._prior = None
        self._session_totals = {}
        self._poll_count = 0
        self._node_history = {}


class EsTopRenderer:
    """Converts ProcessedData into a Rich Group containing three stacked panels."""

    # Unicode block chars for progress bars (8 levels + full)
    _BAR_CHARS = " ▏▎▍▌▋▊▉█"
    _BAR_WIDTH = 10  # characters wide

    def __init__(self, theme_manager=None) -> None:
        self.style_system = StyleSystem(theme_manager)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, data: "ProcessedData") -> Any:
        """Return a Rich Group (vertical stack) of the three dashboard sections."""
        header_panel = self._render_cluster_header(data)
        alerts_panel = self._render_alerts(data)
        node_panel = self._render_node_panel(data)
        index_panel = self._render_index_hot_list(data)
        if alerts_panel is not None:
            return Group(header_panel, alerts_panel, node_panel, index_panel)
        return Group(header_panel, node_panel, index_panel)

    # ------------------------------------------------------------------
    # Section renderers
    # ------------------------------------------------------------------

    def _render_cluster_header(self, data: "ProcessedData") -> Panel:
        """ClusterHeader panel: grid layout with status pill, node counts, shard breakdown."""
        border = self._border_style()

        if data.cluster_health_error:
            return Panel(
                Text(data.cluster_health_error, style="red"),
                title="[red]Cluster Health Error[/red]",
                border_style="red",
            )

        status_style = self._health_style(data.cluster_status)
        status_upper = (data.cluster_status or "unknown").upper()

        # ── Row 1: two side-by-side info blocks ──────────────────────────
        # Left block: status pill + cluster identity
        left = Table.grid(padding=(0, 2))
        left.add_column(no_wrap=True)
        left.add_column(no_wrap=True)
        left.add_row(
            Text(f"● {status_upper}", style=f"bold {status_style}"),
            Text(data.cluster_name, style="bold white"),
        )
        left.add_row(
            Text("Nodes", style="dim white"),
            Text(
                f"{data.total_nodes} total  {data.data_nodes} data",
                style="white",
            ),
        )

        # Right block: shard breakdown as labeled pairs
        right = Table.grid(padding=(0, 2))
        right.add_column(no_wrap=True, justify="right")
        right.add_column(no_wrap=True, justify="right")
        right.add_column(no_wrap=True, justify="right")
        right.add_column(no_wrap=True, justify="right")

        right.add_row(
            Text("Active", style="dim white"),
            Text("Relocating", style="dim white"),
            Text("Initializing", style="dim white"),
            Text("Unassigned", style="dim white"),
        )
        unassigned_style = "red bold" if data.unassigned_shards > 0 else "white"
        relocating_style = "yellow" if data.relocating_shards > 0 else "white"
        initializing_style = "yellow" if data.initializing_shards > 0 else "white"
        right.add_row(
            Text(str(data.active_shards), style="green"),
            Text(str(data.relocating_shards), style=relocating_style),
            Text(str(data.initializing_shards), style=initializing_style),
            Text(str(data.unassigned_shards), style=unassigned_style),
        )

        # ── Row 2: poll metadata footer ──────────────────────────────────
        last_poll_ts = data.last_poll_time.strftime("%H:%M:%S") if data.last_poll_time else "—"
        uptime_secs = int((datetime.now() - data.session_start).total_seconds())
        h, rem = divmod(uptime_secs, 3600)
        m, s = divmod(rem, 60)
        uptime_str = f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"
        footer = Text.assemble(
            ("Poll #", "dim white"),
            (str(data.poll_count), "white"),
            ("  ·  Last poll: ", "dim white"),
            (last_poll_ts, "white"),
            ("  ·  Runtime: ", "dim white"),
            (uptime_str, "white"),
            ("  ·  Refresh: ", "dim white"),
            (f"{data.interval}s", "white"),
        )

        body = Group(
            Columns([left, right], expand=True),
            Text(""),  # spacer
            footer,
        )

        return Panel(
            body,
            title=f"[bold {status_style}]es-top[/bold {status_style}]  [dim white]Cluster Health[/dim white]",
            border_style=border,
        )

    def _render_alerts(self, data: "ProcessedData") -> Any:
        """Alerts panel: surfaces actionable conditions. Returns None when all clear."""
        alerts = []

        # Shard alerts
        if data.unassigned_shards > 0:
            alerts.append(Text.assemble(
                ("⚠  ", "bold red"),
                (f"{data.unassigned_shards} unassigned shard{'s' if data.unassigned_shards != 1 else ''}",
                 "red"),
            ))
        if data.relocating_shards > 0:
            alerts.append(Text.assemble(
                ("↔  ", "bold yellow"),
                (f"{data.relocating_shards} shard{'s' if data.relocating_shards != 1 else ''} relocating",
                 "yellow"),
            ))
        if data.initializing_shards > 0:
            alerts.append(Text.assemble(
                ("⟳  ", "bold yellow"),
                (f"{data.initializing_shards} shard{'s' if data.initializing_shards != 1 else ''} initializing",
                 "yellow"),
            ))

        # Node pressure alerts
        for node in data.top_nodes:
            if node.heap_pct >= 85:
                alerts.append(Text.assemble(
                    ("⚠  ", "bold red"),
                    (f"{node.name}", "bold white"),
                    ("  heap ", "dim white"),
                    (f"{node.heap_pct:.1f}%", "red bold"),
                ))
            if node.disk_used_pct >= 90:
                alerts.append(Text.assemble(
                    ("⚠  ", "bold red"),
                    (f"{node.name}", "bold white"),
                    ("  disk ", "dim white"),
                    (f"{node.disk_used_pct:.1f}% used", "red bold"),
                ))
            elif node.disk_used_pct >= 85:
                alerts.append(Text.assemble(
                    ("▲  ", "bold yellow"),
                    (f"{node.name}", "bold white"),
                    ("  disk ", "dim white"),
                    (f"{node.disk_used_pct:.1f}% used", "yellow"),
                ))

        if not alerts:
            return None

        # Determine worst severity for border colour
        border = "yellow"
        for node in data.top_nodes:
            if node.heap_pct >= 85 or node.disk_used_pct >= 90:
                border = "red"
                break
        if data.unassigned_shards > 0:
            border = "red"

        grid = Table.grid(padding=(0, 3))
        grid.add_column(no_wrap=True)
        grid.add_column(no_wrap=True)
        # Two-column layout: pair alerts side by side
        for i in range(0, len(alerts), 2):
            left = alerts[i]
            right = alerts[i + 1] if i + 1 < len(alerts) else Text("")
            grid.add_row(left, right)

        return Panel(
            grid,
            title=f"[bold {border}]⚡ Alerts[/bold {border}]",
            border_style=border,
            padding=(0, 2),
        )

    def _render_node_panel(self, data: "ProcessedData") -> Any:
        """NodePanel: top N nodes with inline progress bars for heap, CPU, disk."""
        border = self._border_style()

        if data.nodes_stats_error:
            return Panel(
                Text(data.nodes_stats_error, style="yellow"),
                title="[yellow]Node Stats Warning[/yellow]",
                border_style="yellow",
            )

        table = Table(box=box.SIMPLE, expand=True, show_header=True, header_style="bold white")
        table.add_column("Node", style="white", no_wrap=True)
        table.add_column("Heap", no_wrap=True)
        table.add_column("Heap Trend", no_wrap=True)
        table.add_column("CPU", no_wrap=True)
        table.add_column("CPU Trend", no_wrap=True)
        table.add_column("Load 1m", justify="right", style="white")
        table.add_column("Disk", no_wrap=True)
        table.add_column("Disk Free", justify="right", style="white")

        for rank, node in enumerate(data.top_nodes):
            heap_style = self._heap_style(node.heap_pct)
            disk_style = self._disk_style(node.disk_used_pct)
            cpu_style = self._cpu_style(node.cpu_pct)
            history = data.node_history.get(node.name, [])
            heap_history = [h for h, _ in history]
            cpu_history = [c for _, c in history]
            table.add_row(
                node.name,
                self._bar(node.heap_pct, heap_style),
                self._sparkline(heap_history, heap_style),
                self._bar(node.cpu_pct, cpu_style),
                self._sparkline(cpu_history, cpu_style),
                f"{node.load_1m:.2f}",
                self._bar(node.disk_used_pct, disk_style),
                self._format_bytes(node.disk_free_bytes),
            )
        return Panel(table, title="Top Nodes  [dim white](by Heap %)[/dim white]", border_style=border)

    def _render_index_hot_list(self, data: "ProcessedData") -> Any:
        """IndexHotList: top N active indices, wrapped in a Panel."""
        border = self._border_style()
        n = len(data.top_indices)

        if data.cat_indices_error:
            return Panel(
                Text(data.cat_indices_error, style="yellow"),
                title="[yellow]Index Stats Warning[/yellow]",
                border_style="yellow",
            )

        if data.is_first_poll:
            table = Table(box=box.SIMPLE, expand=True, show_header=True, header_style="bold white")
            table.add_column("Index", style="white")
            table.add_column("Total Docs", justify="right")
            table.add_column("Store Size", justify="right")
            table.add_column("Session Docs", justify="right")
            table.add_column("Session Searches", justify="right")
            for idx in data.top_indices:
                is_abnormal = idx.index_name in data.abnormal_indices
                name_text = Text()
                if is_abnormal:
                    name_text.append("⚠ ", style="bold yellow")
                name_text.append(idx.index_name, style="bold yellow" if is_abnormal else "white")
                table.add_row(
                    name_text,
                    Text(str(idx.total_docs), style="bold yellow" if is_abnormal else "white"),
                    Text(idx.store_size, style="bold yellow" if is_abnormal else "white"),
                    Text(str(idx.session_docs), style="bold yellow" if is_abnormal else "white"),
                    Text(str(idx.session_searches), style="bold yellow" if is_abnormal else "white"),
                )
            note = Text("Rates available after next poll", style="dim white")
            body = Group(table, note)
            return Panel(
                body,
                title=f"Index Hot List  [dim white](top {n} active)[/dim white]",
                border_style=border,
            )

        # Find max docs/s for relative activity colouring
        max_docs_rate = max((idx.docs_per_sec for idx in data.top_indices), default=0.0)
        mode = getattr(data, "hot_indicator", "emoji")

        table = Table(box=box.SIMPLE, expand=True, show_header=True, header_style="bold white")
        table.add_column("Index", style="white")
        table.add_column("Docs/s", justify="right")
        table.add_column("Searches/s", justify="right")
        table.add_column("Session Docs", justify="right")
        table.add_column("Session Searches", justify="right")
        table.add_column("Total Docs", justify="right")
        table.add_column("Store Size", justify="right")

        for rank, idx in enumerate(data.top_indices):
            # Color coding: active when mode is 'color' or 'both'
            if mode in ("color", "both"):
                row_style = self._index_activity_style(idx.docs_per_sec, max_docs_rate)
            else:
                row_style = "white"

            is_abnormal = idx.index_name in data.abnormal_indices
            name_text = Text()
            if is_abnormal:
                name_text.append("⚠ ", style="bold yellow")
            name_text.append(idx.index_name, style="bold yellow" if is_abnormal else row_style)
            if not is_abnormal:
                suffix = self._hot_prefix(rank, mode)
                if suffix:
                    name_text.append(f" {suffix}")
            table.add_row(
                name_text,
                Text(f"{idx.docs_per_sec:.2f}", style="bold yellow" if is_abnormal else row_style),
                Text(f"{idx.searches_per_sec:.2f}", style="bold yellow" if is_abnormal else row_style),
                Text(str(idx.session_docs), style="bold yellow" if is_abnormal else row_style),
                Text(str(idx.session_searches), style="bold yellow" if is_abnormal else row_style),
                Text(str(idx.total_docs), style="bold yellow" if is_abnormal else row_style),
                Text(idx.store_size, style="bold yellow" if is_abnormal else row_style),
            )
        abnormal_count = sum(1 for idx in data.top_indices if idx.index_name in data.abnormal_indices)
        title_suffix = (
            f"  [bold yellow]⚠ {abnormal_count} abnormal[/bold yellow]"
            if abnormal_count > 0
            else ""
        )
        return Panel(
            table,
            title=f"Index Hot List  [dim white](top {n} active)[/dim white]{title_suffix}",
            border_style=border,
        )

    # ------------------------------------------------------------------
    # Progress bar + sparkline helpers
    # ------------------------------------------------------------------

    _SPARK_CHARS = "▁▂▃▄▅▆▇█"

    def _sparkline(self, values: list, style: str) -> Text:
        """Render a Unicode sparkline from a list of 0–100 floats."""
        if not values:
            return Text("", style=style)
        lo, hi = min(values), max(values)
        span = hi - lo if hi != lo else 1.0
        chars = self._SPARK_CHARS
        result = ""
        for v in values:
            idx = int((v - lo) / span * (len(chars) - 1))
            result += chars[idx]
        return Text(result, style=style)

    def _bar(self, pct: float, style: str, width: int = _BAR_WIDTH) -> Text:
        """Render a Unicode block progress bar with the percentage label alongside."""
        pct = max(0.0, min(100.0, pct))
        filled_units = pct / 100.0 * width
        full_blocks = int(filled_units)
        remainder = filled_units - full_blocks
        # Pick the partial block character (0–7 index into _BAR_CHARS[1:])
        partial_idx = int(remainder * 8)
        partial_char = self._BAR_CHARS[partial_idx] if partial_idx > 0 else ""
        empty = width - full_blocks - (1 if partial_char else 0)
        bar_str = "█" * full_blocks + partial_char + " " * empty
        label = f"{pct:5.1f}%"
        t = Text()
        t.append(f"[{bar_str}]", style=style)
        t.append(f" {label}", style=style)
        return t

    # ------------------------------------------------------------------
    # Threshold / style helpers
    # ------------------------------------------------------------------

    def _health_style(self, status: str) -> str:
        mapping = {"green": "green", "yellow": "yellow", "red": "red bold"}
        return mapping.get(status.lower() if status else "", "white")

    def _heap_style(self, pct: float) -> str:
        if pct >= 85:
            return "red bold"
        if pct >= 70:
            return "yellow"
        return "green"

    def _cpu_style(self, pct: float) -> str:
        if pct >= 90:
            return "red bold"
        if pct >= 70:
            return "yellow"
        return "cyan"

    def _disk_style(self, pct: float) -> str:
        if pct >= 90:
            return "red bold"
        if pct >= 85:
            return "yellow"
        return "blue"

    def _index_activity_style(self, docs_per_sec: float, max_rate: float) -> str:
        """Colour index rows by relative write activity."""
        if max_rate <= 0 or docs_per_sec <= 0:
            return "dim white"
        ratio = docs_per_sec / max_rate
        if ratio >= 0.75:
            return "bold white"
        if ratio >= 0.25:
            return "white"
        return "dim white"

    def _format_bytes(self, b: int) -> str:
        if b is None:
            return "N/A"
        for unit in ("KB", "MB", "GB", "TB"):
            b /= 1024.0
            if abs(b) < 1024.0:
                return f"{b:.1f} {unit}"
        return f"{b:.1f} TB"

    def _border_style(self) -> str:
        if self.style_system and self.style_system.theme_manager:
            return self.style_system._get_style("table_styles", "border_style", "cyan")
        return "cyan"

    def _hot_prefix(self, rank: int, mode: str) -> str:
        """Return the emoji suffix for a ranked item given the hot_indicator mode.

        rank=0 → '🔥', rank=1 → '🌡', rank>=2 → ''.
        Returns '' when mode is 'color' or 'none'.
        """
        if mode not in ("emoji", "both"):
            return ""
        if rank == 0:
            return "🔥"
        if rank == 1:
            return "🌡"
        return ""


class EsTopDashboard:
    """Owns the rich.live.Live context and the main polling loop."""

    def __init__(self, es_client, interval=30, top_nodes=5, top_indices=10, console=None,
                 hot_indicator="emoji", collect=False, collect_dir=None, current_location=None,
                 new_session: bool = False, join_latest: bool = False, label=None):
        self.interval = max(10, interval)
        self.top_nodes = top_nodes
        self.top_indices = top_indices
        self.hot_indicator = hot_indicator
        self.collect = collect
        self.collect_dir = collect_dir
        self.current_location = current_location
        self.new_session = new_session
        self.join_latest = join_latest
        self.label = label
        self._stopped = False
        self._poller = EsTopPoller(es_client)
        self._delta_calc = DeltaCalculator()
        theme_manager = getattr(es_client, 'theme_manager', None)
        self._renderer = EsTopRenderer(theme_manager)
        self._abnormal_indices = self._fetch_abnormal_indices(es_client)
        self._es_client = es_client

        # Set up collect output directory if --collect is active
        self._collect_out_dir = None
        self._collect_seq = 0
        self._collect_cluster = "unknown"
        if self.collect:
            from datetime import timezone
            from pathlib import Path
            from processors.indices_watch import (
                default_run_dir,
                index_watch_storage_slug,
                utc_today_iso,
                write_run_metadata,
            )
            cm = getattr(es_client, 'configuration_manager', None)
            raw_loc = current_location or "default"
            self._collect_cluster = (
                index_watch_storage_slug(raw_loc, cm) if cm is not None else raw_loc
            )
            day_iso = utc_today_iso()
            import sys
            if collect_dir and str(collect_dir).strip():
                # Explicit path: direct write, no session logic
                self._collect_out_dir = Path(str(collect_dir).strip()).expanduser()
                self._collect_out_dir.mkdir(parents=True, exist_ok=True)
                write_run_metadata(
                    self._collect_out_dir,
                    cluster=self._collect_cluster,
                    interval_seconds=self.interval,
                    duration_seconds=None,
                    pattern=None,
                    status=None,
                )
            else:
                # Session-aware path
                from processors.indices_watch import pick_or_create_session_dir
                self._collect_out_dir, is_new = pick_or_create_session_dir(
                    self._collect_cluster,
                    day_iso,
                    new_session=self.new_session,
                    join_latest=self.join_latest,
                    label=self.label,
                    console=console,
                    is_tty=sys.stdin.isatty(),
                )
                self._collect_out_dir.mkdir(parents=True, exist_ok=True)
                if is_new:
                    write_run_metadata(
                        self._collect_out_dir,
                        cluster=self._collect_cluster,
                        interval_seconds=self.interval,
                        duration_seconds=None,
                        pattern=None,
                        status=None,
                        session_id=self._collect_out_dir.name,
                        label=self.label,
                    )

    def _fetch_abnormal_indices(self, es_client) -> frozenset:
        """Run indices-analyze once at startup to get the set of abnormal index names."""
        try:
            from processors.index_traffic_analyzer import analyze_index_traffic
            indices = es_client.filter_indices()
            result = analyze_index_traffic(indices, min_ratio=5.0, min_docs=1_000_000)
            return frozenset(r.get("index", "") for r in result.get("rows", []))
        except Exception:
            return frozenset()

    def run(self) -> None:
        """Enter rich.live.Live, run the poll loop until stop signal."""
        from rich.live import Live
        try:
            with Live(refresh_per_second=1, screen=True) as live:
                self._poll_loop(live)
        except KeyboardInterrupt:
            pass  # Clean exit — Live context manager restores terminal

    def _poll_loop(self, live) -> None:
        """Core loop: poll → calculate → render → sleep → optionally save sample."""
        last_layout = None
        last_error: Optional[str] = None
        while not self._stopped:
            cycle_start = time.monotonic()
            try:
                snapshot = self._poller.poll()
                processed = self._delta_calc.process(
                    snapshot,
                    interval=self.interval,
                    top_nodes=self.top_nodes,
                    top_indices=self.top_indices,
                    abnormal_indices=self._abnormal_indices,
                    hot_indicator=self.hot_indicator,
                )
                last_layout = self._renderer.render(processed)
                last_error = None
                live.update(last_layout)

                # --collect: persist this poll's cat_indices as a watch sample
                if self.collect and self._collect_out_dir is not None:
                    if snapshot.cat_indices is not None:
                        from datetime import timezone as _tz
                        from processors.indices_watch import save_sample_file
                        self._collect_seq += 1
                        captured_at = snapshot.timestamp.replace(tzinfo=_tz.utc)
                        save_sample_file(
                            self._collect_out_dir,
                            cluster=self._collect_cluster,
                            indices=snapshot.cat_indices,
                            captured_at=captured_at,
                            host_used=getattr(self._es_client, 'host1', None),
                            sequence=self._collect_seq,
                        )

            except Exception as e:
                last_error = str(e)
                from rich.panel import Panel as _Panel
                from rich.text import Text as _Text
                error_display = _Panel(
                    _Text(f"Poll cycle error: {last_error}", style="red"),
                    title="[red]es-top Error[/red]",
                    border_style="red",
                )
                live.update(error_display)
            elapsed = time.monotonic() - cycle_start
            sleep_time = max(0.0, self.interval - elapsed)
            time.sleep(sleep_time)

    def _stop(self) -> None:
        """Signal the loop to stop."""
        self._stopped = True
