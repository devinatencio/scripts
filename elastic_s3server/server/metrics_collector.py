"""
metrics_collector.py - SQLite-backed metrics with safe concurrent access.

Replaces the previous JSON read-modify-write approach with SQLite, which
handles all locking internally — across threads (daemon workers) and
across processes (manual script runs) — eliminating the class of bugs
where concurrent writers clobber each other's data.

The public API is unchanged: callers still pass a ``metrics_file`` path
ending in ``.json``.  The actual storage is a ``.db`` sibling file in
the same directory.  ``read_metrics`` returns the same dict structure
the dashboard and other consumers expect.
"""

import datetime
import json
import os
import sqlite3

from typing import Optional  # noqa: F401

# Timeout (seconds) for SQLite to wait when the database is locked by
# another process or thread.  5 s is generous for the tiny writes here.
_BUSY_TIMEOUT_MS = 5000


def _db_path_from(metrics_file):
    # type: (str) -> str
    """Derive the SQLite database path from the legacy JSON path.

    Keeps the database next to where the JSON file would have been so
    that existing ``--metrics-file`` flags and ``_METRICS_FILE`` module
    constants continue to work without changes.
    """
    base, _ = os.path.splitext(os.path.abspath(metrics_file))
    return base + '.db'


def _ensure_dir(path):
    # type: (str) -> None
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)


def _get_connection(db_path):
    # type: (str) -> sqlite3.Connection
    """Open (or create) the metrics database and ensure the schema exists."""
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path, timeout=_BUSY_TIMEOUT_MS / 1000.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=%d' % _BUSY_TIMEOUT_MS)
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn):
    # type: (sqlite3.Connection) -> None
    """Create tables if they don't exist yet."""
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS daily_counters (
            date           TEXT PRIMARY KEY,
            snapshots_created   INTEGER NOT NULL DEFAULT 0,
            snapshots_deleted   INTEGER NOT NULL DEFAULT 0,
            indices_deleted_ilm INTEGER NOT NULL DEFAULT 0,
            total_snapshots     INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS utility_health (
            utility_name TEXT PRIMARY KEY,
            last_run     TEXT NOT NULL,
            success      INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS snapshot_statuses (
            status TEXT PRIMARY KEY,
            count  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS daemon_heartbeat (
            id        INTEGER PRIMARY KEY CHECK (id = 1),
            pid       INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            tasks     TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS daily_history (
            date                TEXT PRIMARY KEY,
            snapshots_created   INTEGER NOT NULL DEFAULT 0,
            snapshots_deleted   INTEGER NOT NULL DEFAULT 0,
            indices_deleted_ilm INTEGER NOT NULL DEFAULT 0,
            total_snapshots     INTEGER NOT NULL DEFAULT 0
        );
    ''')

    # Schema migration: add total_snapshots column to existing databases
    for table in ('daily_counters', 'daily_history'):
        try:
            conn.execute(
                'ALTER TABLE %s ADD COLUMN total_snapshots '
                'INTEGER NOT NULL DEFAULT 0' % table
            )
        except sqlite3.OperationalError:
            pass  # column already exists


def _today():
    # type: () -> str
    return datetime.date.today().strftime('%Y-%m-%d')


def _ensure_today_row(conn):
    # type: (sqlite3.Connection) -> str
    """Ensure a row exists for today in daily_counters.

    If the most recent row is for a previous date, archive it into
    daily_history first, then insert today's row.

    Returns today's date string.
    """
    today = _today()
    row = conn.execute(
        'SELECT date FROM daily_counters ORDER BY date DESC LIMIT 1'
    ).fetchone()

    if row and row[0] == today:
        return today

    # Archive the old day (if any) before creating today's row
    if row and row[0] != today:
        old_date = row[0]
        old = conn.execute(
            'SELECT snapshots_created, snapshots_deleted, indices_deleted_ilm, '
            'total_snapshots FROM daily_counters WHERE date = ?', (old_date,)
        ).fetchone()
        if old:
            conn.execute(
                'INSERT OR IGNORE INTO daily_history '
                '(date, snapshots_created, snapshots_deleted, '
                'indices_deleted_ilm, total_snapshots) '
                'VALUES (?, ?, ?, ?, ?)',
                (old_date, old[0], old[1], old[2], old[3]),
            )
        # Remove old counter rows (keep only today)
        conn.execute('DELETE FROM daily_counters WHERE date != ?', (today,))

    conn.execute(
        'INSERT OR IGNORE INTO daily_counters (date) VALUES (?)', (today,)
    )
    # Prune history to 90 days
    conn.execute(
        'DELETE FROM daily_history WHERE date NOT IN '
        '(SELECT date FROM daily_history ORDER BY date DESC LIMIT 90)'
    )
    return today


# ---------------------------------------------------------------------------
# Public API — signatures unchanged from the JSON version
# ---------------------------------------------------------------------------

def get_default_metrics():
    # type: () -> dict
    """Return default metrics structure with zero values.

    Provided for backward compatibility with tests and any code that
    needs a blank metrics dict.
    """
    today = _today()
    return {
        'daily_counters': {
            'date': today,
            'snapshots_created': 0,
            'snapshots_deleted': 0,
            'indices_deleted_ilm': 0,
            'total_snapshots': 0,
        },
        'utility_health': {},
        'snapshot_statuses': {
            'SUCCESS': 0,
            'FAILED': 0,
            'PARTIAL': 0,
            'IN_PROGRESS': 0,
            'INCOMPATIBLE': 0,
        },
    }


def read_metrics(metrics_file):
    # type: (str) -> dict
    """Read all metrics into the dict structure consumers expect.

    Returns the same shape as ``get_default_metrics()`` plus optional
    ``daemon_heartbeat`` and ``daily_history`` keys.  Safe to call from
    any thread or process — SQLite handles the locking.
    """
    db_path = _db_path_from(metrics_file)
    if not os.path.isfile(db_path):
        return get_default_metrics()

    try:
        conn = _get_connection(db_path)
    except sqlite3.Error:
        return get_default_metrics()

    try:
        result = get_default_metrics()

        # --- daily_counters (today only) ---
        today = _today()
        row = conn.execute(
            'SELECT date, snapshots_created, snapshots_deleted, '
            'indices_deleted_ilm, total_snapshots FROM daily_counters '
            'ORDER BY date DESC LIMIT 1'
        ).fetchone()
        if row:
            result['daily_counters'] = {
                'date': row[0],
                'snapshots_created': row[1],
                'snapshots_deleted': row[2],
                'indices_deleted_ilm': row[3],
                'total_snapshots': row[4],
            }

        # --- utility_health ---
        health = {}
        for urow in conn.execute(
            'SELECT utility_name, last_run, success FROM utility_health'
        ):
            health[urow[0]] = {
                'last_run': urow[1],
                'success': bool(urow[2]),
            }
        result['utility_health'] = health

        # --- snapshot_statuses ---
        statuses = {}
        for srow in conn.execute(
            'SELECT status, count FROM snapshot_statuses'
        ):
            statuses[srow[0]] = srow[1]
        if statuses:
            result['snapshot_statuses'] = statuses

        # --- daemon_heartbeat ---
        hb = conn.execute(
            'SELECT pid, timestamp, tasks FROM daemon_heartbeat WHERE id = 1'
        ).fetchone()
        if hb:
            try:
                tasks = json.loads(hb[2])
            except (ValueError, TypeError):
                tasks = {}
            result['daemon_heartbeat'] = {
                'pid': hb[0],
                'timestamp': hb[1],
                'tasks': tasks,
            }

        # --- daily_history ---
        history = []
        for hrow in conn.execute(
            'SELECT date, snapshots_created, snapshots_deleted, '
            'indices_deleted_ilm, total_snapshots '
            'FROM daily_history ORDER BY date'
        ):
            history.append({
                'date': hrow[0],
                'snapshots_created': hrow[1],
                'snapshots_deleted': hrow[2],
                'indices_deleted_ilm': hrow[3],
                'total_snapshots': hrow[4],
            })
        if history:
            result['daily_history'] = history

        return result
    except sqlite3.Error:
        return get_default_metrics()
    finally:
        conn.close()


def write_metrics(metrics_file, metrics_data):
    # type: (str, dict) -> None
    """Write a full metrics dict to the database.

    Primarily used by tests that seed specific state.  In production
    the individual ``record_*`` / ``increment_*`` functions are
    preferred because they touch only their own rows.
    """
    db_path = _db_path_from(metrics_file)
    conn = _get_connection(db_path)
    try:
        with conn:
            # daily_counters
            counters = metrics_data.get('daily_counters', {})
            date = counters.get('date', _today())
            conn.execute('DELETE FROM daily_counters')
            conn.execute(
                'INSERT INTO daily_counters '
                '(date, snapshots_created, snapshots_deleted, '
                'indices_deleted_ilm, total_snapshots) '
                'VALUES (?, ?, ?, ?, ?)',
                (date,
                 counters.get('snapshots_created', 0),
                 counters.get('snapshots_deleted', 0),
                 counters.get('indices_deleted_ilm', 0),
                 counters.get('total_snapshots', 0)),
            )

            # utility_health
            health = metrics_data.get('utility_health', {})
            conn.execute('DELETE FROM utility_health')
            for name, info in health.items():
                conn.execute(
                    'INSERT INTO utility_health (utility_name, last_run, success) '
                    'VALUES (?, ?, ?)',
                    (name, info.get('last_run', ''), int(info.get('success', False))),
                )

            # snapshot_statuses
            statuses = metrics_data.get('snapshot_statuses', {})
            conn.execute('DELETE FROM snapshot_statuses')
            for status, count in statuses.items():
                conn.execute(
                    'INSERT INTO snapshot_statuses (status, count) VALUES (?, ?)',
                    (status, count),
                )

            # daemon_heartbeat
            hb = metrics_data.get('daemon_heartbeat')
            if hb:
                conn.execute('DELETE FROM daemon_heartbeat')
                conn.execute(
                    'INSERT INTO daemon_heartbeat (id, pid, timestamp, tasks) '
                    'VALUES (1, ?, ?, ?)',
                    (hb.get('pid', 0),
                     hb.get('timestamp', ''),
                     json.dumps(hb.get('tasks', {}))),
                )

            # daily_history
            history = metrics_data.get('daily_history')
            if history is not None:
                conn.execute('DELETE FROM daily_history')
                for entry in history:
                    conn.execute(
                        'INSERT OR IGNORE INTO daily_history '
                        '(date, snapshots_created, snapshots_deleted, '
                        'indices_deleted_ilm, total_snapshots) '
                        'VALUES (?, ?, ?, ?, ?)',
                        (entry.get('date', ''),
                         entry.get('snapshots_created', 0),
                         entry.get('snapshots_deleted', 0),
                         entry.get('indices_deleted_ilm', 0),
                         entry.get('total_snapshots', 0)),
                    )
    finally:
        conn.close()


def increment_counter(metrics_file, counter_name, amount=1):
    # type: (str, str, int) -> None
    """Atomically increment a daily counter.

    SQLite handles all locking.  The increment is a single UPDATE
    statement — no read-modify-write cycle, no lost updates.
    """
    if counter_name not in ('snapshots_created', 'snapshots_deleted',
                            'indices_deleted_ilm'):
        return

    db_path = _db_path_from(metrics_file)
    conn = _get_connection(db_path)
    try:
        with conn:
            _ensure_today_row(conn)
            today = _today()
            conn.execute(
                'UPDATE daily_counters SET %s = %s + ? WHERE date = ?'
                % (counter_name, counter_name),
                (amount, today),
            )
    finally:
        conn.close()


def record_health(metrics_file, utility_name, success, timestamp=None):
    # type: (str, str, bool, Optional[str]) -> None
    """Record a utility's health status.

    Also triggers date-rollover archival if the day has changed.
    """
    if timestamp is None:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    db_path = _db_path_from(metrics_file)
    conn = _get_connection(db_path)
    try:
        with conn:
            _ensure_today_row(conn)
            conn.execute(
                'INSERT OR REPLACE INTO utility_health '
                '(utility_name, last_run, success) VALUES (?, ?, ?)',
                (utility_name, timestamp, int(success)),
            )
    finally:
        conn.close()


def record_heartbeat(metrics_file, pid, tasks_summary=None):
    # type: (str, int, Optional[dict]) -> None
    """Record a daemon heartbeat."""
    db_path = _db_path_from(metrics_file)
    conn = _get_connection(db_path)
    try:
        with conn:
            conn.execute(
                'INSERT OR REPLACE INTO daemon_heartbeat '
                '(id, pid, timestamp, tasks) VALUES (1, ?, ?, ?)',
                (pid,
                 datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                 json.dumps(tasks_summary or {})),
            )
    finally:
        conn.close()


def record_snapshot_statuses(metrics_file, status_counts):
    # type: (str, dict) -> None
    """Record snapshot status distribution counts."""
    db_path = _db_path_from(metrics_file)
    conn = _get_connection(db_path)
    try:
        with conn:
            conn.execute('DELETE FROM snapshot_statuses')
            for status, count in status_counts.items():
                conn.execute(
                    'INSERT INTO snapshot_statuses (status, count) '
                    'VALUES (?, ?)',
                    (status, count),
                )
    finally:
        conn.close()


def record_total_snapshots(metrics_file, total):
    # type: (str, int) -> None
    """Record the total number of snapshots in the S3 repository.

    Sets today's ``total_snapshots`` gauge to the given value.  Unlike
    ``increment_counter`` this is an absolute set, not an increment —
    it always reflects the latest count.
    """
    db_path = _db_path_from(metrics_file)
    conn = _get_connection(db_path)
    try:
        with conn:
            today = _ensure_today_row(conn)
            conn.execute(
                'UPDATE daily_counters SET total_snapshots = ? '
                'WHERE date = ?',
                (total, today),
            )
    finally:
        conn.close()
