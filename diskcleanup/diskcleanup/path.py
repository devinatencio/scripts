#!/usr/bin/python3
"""
Disk Cleanup Utility - Path Resolution Module

Provides helpers for resolving file paths correctly whether running as:
  1. Normal Python interpreter  (python diskcleanup.py)
  2. PyInstaller --onefile      (./diskcleanup)
  3. Nuitka --standalone / --onefile  (./diskcleanup.bin)

Key differences between bundlers:

  PyInstaller --onefile:
    sys.frozen = True, sys._MEIPASS = temp extraction dir.
    sys.executable = the real binary the user invoked.
    __file__ points inside _MEIPASS (useless for locating user files).

  Nuitka --onefile:
    sys.frozen is NOT set.  __compiled__ is injected into compiled modules.
    sys.executable = the *extracted Python interpreter* inside a temp dir,
    NOT the binary the user ran.  __file__ also points into the temp dir.
    The real binary location is available via:
      - __main__.__nuitka_binary_dir  (set in --standalone/--onefile)
      - Falling back to os.path.abspath(sys.argv[0])

  Nuitka --standalone (no --onefile):
    Similar to above but no temp extraction — everything lives in the dist
    folder.  sys.executable is the real binary.

  Normal Python:
    __file__ works as expected.

We expose two path concepts:
  - bundle_dir:  read-only bundled resources (_MEIPASS / extraction dir / source)
  - app_dir:     writable location for config, logs, history (next to the real
                 binary when compiled, project root when running from source)
"""

import os
import sys
from pathlib import Path

APP_NAME = "diskcleanup"


# ── Detection helpers ────────────────────────────────────────────────

def is_pyinstaller() -> bool:
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def is_nuitka() -> bool:
    """True when the application was compiled by Nuitka."""
    import __main__
    return (
        hasattr(__main__, "__compiled__")
        or hasattr(sys, "__nuitka_binary_dir")
    )


def is_frozen() -> bool:
    """True when running as any compiled/frozen bundle (PyInstaller or Nuitka)."""
    return is_pyinstaller() or is_nuitka()


def _nuitka_binary_path() -> Path:
    """Resolve the real Nuitka binary path.

    In --onefile mode sys.executable is the extracted interpreter, not the
    binary the user ran.  We try two reliable sources:
      1. __nuitka_binary_dir  — set by Nuitka on the __main__ module
      2. sys.argv[0]          — the original invocation path (always preserved)
    """
    import __main__
    nuitka_dir = getattr(__main__, "__nuitka_binary_dir", None) or getattr(sys, "__nuitka_binary_dir", None)
    if nuitka_dir:
        return Path(nuitka_dir)
    # Fallback: resolve from how the user invoked the binary
    return Path(os.path.abspath(sys.argv[0])).parent


# ── Path resolution ─────────────────────────────────────────────────

def get_bundle_dir() -> Path:
    """Where read-only bundled resources live.

    PyInstaller  → sys._MEIPASS  (temp extraction directory)
    Nuitka       → temp extraction dir (--onefile) or dist dir (--standalone)
    Normal       → diskcleanup/ package directory (parent of this file)
    """
    if is_pyinstaller():
        return Path(sys._MEIPASS)
    if is_nuitka():
        # The extraction / dist dir where compiled modules live
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_app_dir() -> Path:
    """Where persistent, writable files should live (config, logs, history).

    PyInstaller  → directory containing the real executable (sys.executable)
    Nuitka       → directory containing the real binary (via __nuitka_binary_dir
                   or sys.argv[0], since sys.executable is unreliable in --onefile)
    Normal       → project root (one level above the package directory)
    """
    if is_pyinstaller():
        return Path(sys.executable).resolve().parent
    if is_nuitka():
        return _nuitka_binary_path()
    return Path(__file__).resolve().parent.parent
