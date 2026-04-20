"""
daemon.py - Master scheduler daemon for Elasticsearch utilities.

Replaces individual cron jobs with a single long-running process that
sleeps between runs and executes each utility on its configured schedule.
Supports fixed-interval and time-window schedules with random jitter.

Usage:
    python -m server.daemon                     # foreground
    python -m server.daemon --config my.yml     # custom schedule config
    python -m server.daemon --debug             # verbose logging
    python -m server.daemon --dry-run           # log schedule decisions only

Dry-run mode can also be enabled via ``dry_run: true`` in
``daemon_config.yml``.  When active, every child task is invoked with
its own dry-run / no-action flag so it goes through the motions
(connects, queries, evaluates) but never mutates Elasticsearch state
and never updates metrics counters.
"""

import argparse
import datetime
import os
import random
import signal
import sys
import threading
import time
import traceback

import yaml

from server.log_manager import setup_logger
from server.metrics_collector import record_heartbeat

# Version
from server import __version__

# ---------------------------------------------------------------------------
# Task registry - maps task names to their entry-point functions.
# Each function is imported lazily to keep startup fast and avoid circular
# imports.  The functions are the existing main() entry points, but we
# override sys.argv so they run with no CLI args (the daemon controls
# behaviour centrally).
# ---------------------------------------------------------------------------

_TASK_REGISTRY = {
    'cold_snapshots': 'server.cold_snapshots',
    'ilm_curator': 'server.ilm_curator',
    'retention_enforcer': 'server.retention_enforcer',
    'restored_index_manager': 'server.restored_index_manager',
    'snapshot_stats': 'server.snapshot_stats',
}


# ---------------------------------------------------------------------------
# Per-task dry-run flags.
# Each child module uses a slightly different CLI flag name.
# ---------------------------------------------------------------------------

_TASK_DRY_RUN_FLAGS = {
    'cold_snapshots': '--noaction',
    'ilm_curator': '--noaction',
    'retention_enforcer': '--noaction',
    'restored_index_manager': '--dry-run',
}


def _run_task_main(module_path, logger, dry_run=False, task_name=None):
    # type: (str, object, bool, str) -> bool
    """Import and run the main() of a utility module.

    Overrides sys.argv to prevent argparse in the child module from
    seeing the daemon's own arguments.  When *dry_run* is True the
    appropriate no-action flag for the task is injected into sys.argv
    so the child runs in dry-run mode.

    Returns True on success, False on error.
    """
    import importlib
    saved_argv = sys.argv
    try:
        argv = [module_path]
        if dry_run and task_name and task_name in _TASK_DRY_RUN_FLAGS:
            argv.append(_TASK_DRY_RUN_FLAGS[task_name])
        sys.argv = argv
        mod = importlib.import_module(module_path)
        mod.main()
        return True
    except SystemExit as exc:
        # main() may call sys.exit(0) on success
        if exc.code in (None, 0):
            return True
        logger.warning('Task %s exited with code %s.', module_path, exc.code)
        return False
    except Exception:
        logger.error('Task %s failed:\n%s', module_path, traceback.format_exc())
        return False
    finally:
        sys.argv = saved_argv


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------

def _parse_time(time_str):
    # type: (str) -> datetime.time
    """Parse an "HH:MM" string into a datetime.time."""
    parts = time_str.strip().split(':')
    return datetime.time(int(parts[0]), int(parts[1]))


def _in_time_window(window_start, window_end):
    # type: (str, str) -> bool
    """Return True if the current local time is within [start, end).

    Handles overnight windows (e.g. 23:00 - 03:00).
    """
    now = datetime.datetime.now().time()
    start = _parse_time(window_start)
    end = _parse_time(window_end)

    if start <= end:
        return start <= now < end
    else:
        # Overnight window (e.g. 23:00 -> 03:00)
        return now >= start or now < end


# ---------------------------------------------------------------------------
# Task state tracker
# ---------------------------------------------------------------------------

class TaskState(object):
    """Tracks last-run time and next-eligible time for a single task."""

    def __init__(self, name, config):
        # type: (str, dict) -> None
        self.name = name
        self.enabled = config.get('enabled', True)
        self.schedule_type = config.get('schedule_type', 'interval')
        self.interval_seconds = config.get('interval_minutes', 60) * 60
        self.jitter_seconds = config.get('jitter_minutes', 0) * 60
        self.window_start = config.get('window_start', '00:00')
        self.window_end = config.get('window_end', '23:59')
        self.description = config.get('description', '')
        self.last_run = 0.0  # epoch
        self.running = False

    def is_due(self):
        # type: () -> bool
        """Check whether this task should run now."""
        if not self.enabled or self.running:
            return False

        now = time.time()
        if now - self.last_run < self.interval_seconds:
            return False

        if self.schedule_type == 'window':
            if not _in_time_window(self.window_start, self.window_end):
                return False

        return True

    def jitter_delay(self):
        # type: () -> float
        """Return a random delay in seconds [0, jitter_seconds]."""
        if self.jitter_seconds <= 0:
            return 0.0
        return random.uniform(0, self.jitter_seconds)


# ---------------------------------------------------------------------------
# Daemon core
# ---------------------------------------------------------------------------

class Daemon(object):
    """Master scheduler that ticks every minute and dispatches tasks."""

    TICK_SECONDS = 30  # how often the main loop checks schedules

    def __init__(self, config_path, logger, dry_run=False):
        # type: (str, object, bool) -> None
        self.logger = logger
        self.dry_run = dry_run
        self._shutdown = threading.Event()
        self._tasks = {}  # type: dict[str, TaskState]
        self._metrics_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'metrics', 'snapshot_metrics.json',
        )
        self._load_config(config_path)

    # -- configuration -------------------------------------------------------

    def _load_config(self, config_path):
        # type: (str) -> None
        with open(config_path, 'r') as fh:
            raw = yaml.safe_load(fh)

        # Global dry_run from config file (CLI --dry-run takes precedence)
        if not self.dry_run:
            self.dry_run = bool(raw.get('dry_run', False))
        if self.dry_run:
            self.logger.info(
                'DRY-RUN mode enabled — tasks will report actions '
                'without mutating Elasticsearch or updating metrics.',
            )

        tasks_cfg = raw.get('tasks', {})
        for name, cfg in tasks_cfg.items():
            if name not in _TASK_REGISTRY:
                self.logger.warning(
                    'Unknown task "%s" in config - skipping.', name,
                )
                continue
            self._tasks[name] = TaskState(name, cfg)
            state = self._tasks[name]
            self.logger.info(
                'Loaded task: %-25s  type=%-8s  interval=%dm  jitter=%dm  enabled=%s',
                name, state.schedule_type,
                state.interval_seconds // 60,
                state.jitter_seconds // 60,
                state.enabled,
            )

    # -- signal handling -----------------------------------------------------

    def _handle_signal(self, signum, frame):
        # type: (int, object) -> None
        self.logger.info('Received signal %d, shutting down...', signum)
        self._shutdown.set()

    # -- task execution ------------------------------------------------------

    def _execute_task(self, task):
        # type: (TaskState) -> None
        """Run a single task (called from a worker thread)."""
        module_path = _TASK_REGISTRY[task.name]
        self.logger.info('>>> Starting task: %s%s', task.name,
                         ' [dry-run]' if self.dry_run else '')
        start = time.time()
        ok = _run_task_main(module_path, self.logger,
                            dry_run=self.dry_run, task_name=task.name)
        elapsed = time.time() - start
        status = 'OK' if ok else 'FAILED'
        self.logger.info(
            '<<< Finished task: %s  status=%s  elapsed=%.1fs',
            task.name, status, elapsed,
        )
        task.last_run = time.time()
        task.running = False

    def _dispatch_task(self, task):
        # type: (TaskState) -> None
        """Apply jitter then run the task in a background thread."""
        task.running = True
        delay = task.jitter_delay()

        def _worker():
            if delay > 0:
                self.logger.info(
                    'Task %s: sleeping %.0fs (jitter) before start.',
                    task.name, delay,
                )
                # Sleep in small increments so we can respond to shutdown
                remaining = delay
                while remaining > 0 and not self._shutdown.is_set():
                    time.sleep(min(remaining, 5.0))
                    remaining -= 5.0
                if self._shutdown.is_set():
                    task.running = False
                    return
            self._execute_task(task)

        t = threading.Thread(target=_worker, name='task-%s' % task.name)
        t.daemon = True
        t.start()

    # -- main loop -----------------------------------------------------------

    def _write_heartbeat(self):
        # type: () -> None
        """Write a heartbeat entry to the metrics database."""
        summary = {}
        for task in self._tasks.values():
            task_info = {
                'enabled': task.enabled,
                'schedule_type': task.schedule_type,
                'running': task.running,
                'last_run_epoch': task.last_run,
                'interval_seconds': task.interval_seconds,
                'jitter_seconds': task.jitter_seconds,
            }
            if task.schedule_type == 'window':
                task_info['window_start'] = task.window_start
                task_info['window_end'] = task.window_end
            summary[task.name] = task_info
        try:
            record_heartbeat(self._metrics_file, os.getpid(), summary)
        except Exception:
            self.logger.debug('Failed to write heartbeat.', exc_info=True)

    def run(self):
        # type: () -> None
        """Block forever, dispatching tasks on schedule."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        self.logger.info('Daemon started (pid %d). Tick every %ds.', os.getpid(), self.TICK_SECONDS)
        self.logger.info('Tasks loaded: %s', ', '.join(
            t.name for t in self._tasks.values() if t.enabled
        ))

        while not self._shutdown.is_set():
            self._write_heartbeat()

            for task in self._tasks.values():
                if task.is_due():
                    self._dispatch_task(task)

            self._shutdown.wait(self.TICK_SECONDS)

        self.logger.info('Daemon shut down cleanly.')


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    # type: () -> None
    parser = argparse.ArgumentParser(
        description='Master daemon scheduler for Elasticsearch utilities.',
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='Path to daemon_config.yml (default: searches server/ and cwd).',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Enable verbose debug logging.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Log scheduling decisions without actually running tasks.',
    )
    args = parser.parse_args()

    logger = setup_logger('daemon', debug=args.debug)
    logger.info('Elasticsearch Utilities Daemon v%s starting...', __version__)

    # Locate config
    if args.config:
        config_path = args.config
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for candidate in [
            os.path.join(script_dir, 'daemon_config.yml'),
            os.path.join(script_dir, '..', 'daemon_config.yml'),
            os.path.join('.', 'daemon_config.yml'),
        ]:
            if os.path.isfile(candidate):
                config_path = os.path.abspath(candidate)
                break
        else:
            logger.error('daemon_config.yml not found. Use --config to specify.')
            sys.exit(1)

    logger.info('Using config: %s', config_path)

    daemon = Daemon(config_path, logger, dry_run=args.dry_run)
    daemon.run()


if __name__ == '__main__':
    main()
