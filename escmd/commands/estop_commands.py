"""
es-top components: data models for the live Elasticsearch terminal dashboard.

This module contains all dataclass definitions used by the es-top feature,
including PollSnapshot (raw API responses), SessionTotals (per-index cumulative
counters), IndexDelta (per-cycle computed rates), NodeStat (per-node metrics),
and ProcessedData (the full output of DeltaCalculator consumed by EsTopRenderer).
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any

from rich.panel import Panel
from rich.table import Table
from rich.console import Group
from rich.text import Text
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

    # Index hot list data (pre-sorted, top N, only active indices)
    top_indices: List[IndexDelta]

    # Error states (None = no error)
    cluster_health_error: Optional[str]
    nodes_stats_error: Optional[str]
    cat_indices_error: Optional[str]


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

    def process(
        self,
        snapshot: PollSnapshot,
        interval: int = 30,
        top_nodes: int = 5,
        top_indices: int = 10,
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
            cluster_name=cluster_name,
            cluster_status=cluster_status,
            total_nodes=total_nodes,
            data_nodes=data_nodes,
            active_shards=active_shards,
            relocating_shards=relocating_shards,
            initializing_shards=initializing_shards,
            unassigned_shards=unassigned_shards,
            top_nodes=computed_top_nodes,
            top_indices=computed_top_indices,
            cluster_health_error=snapshot.cluster_health_error,
            nodes_stats_error=snapshot.nodes_stats_error,
            cat_indices_error=cat_indices_error,
        )

    def _elapsed_seconds(self, current: PollSnapshot, prior: PollSnapshot) -> float:
        """Returns elapsed time between two snapshots in seconds."""
        return (current.timestamp - prior.timestamp).total_seconds()

    def reset(self) -> None:
        """Clear prior snapshot, session totals, and poll counter (used on reconnect)."""
        self._prior = None
        self._session_totals = {}
        self._poll_count = 0


class EsTopRenderer:
    """Converts ProcessedData into a Rich Group containing three stacked panels."""

    def __init__(self, theme_manager=None) -> None:
        self.style_system = StyleSystem(theme_manager)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, data: "ProcessedData") -> Any:
        """Return a Rich Group (vertical stack) of the three dashboard sections."""
        header_panel = self._render_cluster_header(data)
        node_panel = self._render_node_panel(data)
        index_panel = self._render_index_hot_list(data)
        return Group(header_panel, node_panel, index_panel)

    # ------------------------------------------------------------------
    # Section renderers
    # ------------------------------------------------------------------

    def _render_cluster_header(self, data: "ProcessedData") -> Panel:
        """ClusterHeader panel: cluster name, status, node counts, shard counts."""
        border = self._border_style()

        if data.cluster_health_error:
            return Panel(
                Text(data.cluster_health_error, style="red"),
                title="[red]Cluster Health Error[/red]",
                border_style="red",
            )

        status_style = self._health_style(data.cluster_status)
        title = f"[{status_style}]Cluster: {data.cluster_name}[/{status_style}]"

        # Unassigned shards — red when > 0
        unassigned_str = (
            f"[red]{data.unassigned_shards}[/red]"
            if data.unassigned_shards > 0
            else str(data.unassigned_shards)
        )

        content = Text.assemble(
            ("Status: ", "white"),
            (data.cluster_status, status_style),
            ("  Nodes: ", "white"),
            (f"{data.total_nodes}/{data.data_nodes}", "white"),
            ("  Shards — active: ", "white"),
            (str(data.active_shards), "white"),
            ("  relocating: ", "white"),
            (str(data.relocating_shards), "white"),
            ("  initializing: ", "white"),
            (str(data.initializing_shards), "white"),
            ("  unassigned: ", "white"),
        )
        # Append unassigned with conditional red styling
        if data.unassigned_shards > 0:
            content.append(str(data.unassigned_shards), style="red")
        else:
            content.append(str(data.unassigned_shards))

        last_poll_ts = data.last_poll_time.strftime("%H:%M:%S") if data.last_poll_time else "—"
        footer = (
            f"Poll #{data.poll_count} | "
            f"Last poll: {last_poll_ts} ({data.elapsed_since_poll:.1f}s ago) | "
            f"Refresh: {data.interval}s"
        )

        from rich.console import Group as RichGroup
        body = RichGroup(content, Text(footer, style="dim white"))

        return Panel(body, title=title, border_style=border)

    def _render_node_panel(self, data: "ProcessedData") -> Any:
        """NodePanel: top N nodes by heap %, wrapped in a Panel."""
        border = self._border_style()

        if data.nodes_stats_error:
            return Panel(
                Text(data.nodes_stats_error, style="yellow"),
                title="[yellow]Node Stats Warning[/yellow]",
                border_style="yellow",
            )

        table = Table(box=box.SIMPLE, expand=True, show_header=True, header_style="bold white")
        table.add_column("Node", style="white")
        table.add_column("Heap%", style="white", justify="right")
        table.add_column("CPU%", style="white", justify="right")
        table.add_column("Load(1m)", style="white", justify="right")
        table.add_column("Disk%", style="white", justify="right")
        table.add_column("Disk Free", style="white", justify="right")

        for node in data.top_nodes:
            heap_style = self._heap_style(node.heap_pct)
            disk_style = self._disk_style(node.disk_used_pct)
            table.add_row(
                node.name,
                Text(f"{node.heap_pct:.1f}%", style=heap_style),
                f"{node.cpu_pct:.1f}%",
                f"{node.load_1m:.2f}",
                Text(f"{node.disk_used_pct:.1f}%", style=disk_style),
                self._format_bytes(node.disk_free_bytes),
            )

        return Panel(table, title="Top Nodes (by Heap %)", border_style=border)

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
                table.add_row(
                    idx.index_name,
                    str(idx.total_docs),
                    idx.store_size,
                    str(idx.session_docs),
                    str(idx.session_searches),
                )
            note = Text("Rates available after next poll", style="dim white")
            from rich.console import Group as RichGroup
            body = RichGroup(table, note)
            return Panel(
                body,
                title=f"Index Hot List (top {n} active)",
                border_style=border,
            )

        table = Table(box=box.SIMPLE, expand=True, show_header=True, header_style="bold white")
        table.add_column("Index", style="white")
        table.add_column("Docs/s", justify="right")
        table.add_column("Searches/s", justify="right")
        table.add_column("Session Docs", justify="right")
        table.add_column("Session Searches", justify="right")
        table.add_column("Total Docs", justify="right")
        table.add_column("Store Size", justify="right")

        for idx in data.top_indices:
            table.add_row(
                idx.index_name,
                f"{idx.docs_per_sec:.2f}",
                f"{idx.searches_per_sec:.2f}",
                str(idx.session_docs),
                str(idx.session_searches),
                str(idx.total_docs),
                idx.store_size,
            )

        return Panel(table, title=f"Index Hot List (top {n} active)", border_style=border)

    # ------------------------------------------------------------------
    # Threshold helpers
    # ------------------------------------------------------------------

    def _health_style(self, status: str) -> str:
        """Map cluster health status to a Rich style string."""
        mapping = {
            "green": "green",
            "yellow": "yellow",
            "red": "red bold",
        }
        return mapping.get(status.lower() if status else "", "white")

    def _heap_style(self, pct: float) -> str:
        """Return 'red bold' when heap >= 85%, else 'white'."""
        return "red bold" if pct >= 85 else "white"

    def _disk_style(self, pct: float) -> str:
        """Return 'red bold' >= 90%, 'yellow' >= 85%, else 'white'."""
        if pct >= 90:
            return "red bold"
        if pct >= 85:
            return "yellow"
        return "white"

    def _format_bytes(self, b: int) -> str:
        """Convert integer bytes to a human-readable string (KB/MB/GB/TB)."""
        if b is None:
            return "N/A"
        for unit in ("KB", "MB", "GB", "TB"):
            b /= 1024.0
            if abs(b) < 1024.0:
                return f"{b:.1f} {unit}"
        return f"{b:.1f} TB"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _border_style(self) -> str:
        """Return the panel border style from the style system, defaulting to 'cyan'."""
        if self.style_system and self.style_system.theme_manager:
            return self.style_system._get_style("table_styles", "border_style", "cyan")
        return "cyan"


class EsTopDashboard:
    """Owns the rich.live.Live context and the main polling loop."""

    def __init__(self, es_client, interval=30, top_nodes=5, top_indices=10, console=None):
        self.interval = max(10, interval)  # clamp to minimum 10s
        self.top_nodes = top_nodes
        self.top_indices = top_indices
        self._stopped = False
        self._poller = EsTopPoller(es_client)
        self._delta_calc = DeltaCalculator()
        theme_manager = getattr(es_client, 'theme_manager', None)
        self._renderer = EsTopRenderer(theme_manager)

    def run(self) -> None:
        """Enter rich.live.Live, run the poll loop until stop signal."""
        from rich.live import Live
        try:
            with Live(refresh_per_second=1, screen=True) as live:
                self._poll_loop(live)
        except KeyboardInterrupt:
            pass  # Clean exit — Live context manager restores terminal

    def _poll_loop(self, live) -> None:
        """Core loop: poll → calculate → render → sleep."""
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
                )
                last_layout = self._renderer.render(processed)
                last_error = None
                live.update(last_layout)
            except Exception as e:
                last_error = str(e)
                # Surface the error in the display rather than silently swallowing it
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
