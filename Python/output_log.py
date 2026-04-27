"""
Central log directory for OUTPUT.txt and session archives.

Development: logs under ``Python/logs/`` next to this file.

PyInstaller one-file / one-folder: logs default to ``<folder of .exe>/logs/``
(writable next to the app). Override with env ``LABSMITH_DATA_DIR``.
"""
import os
import sys
from typing import Optional

_LOG_DIR: Optional[str] = None


def app_writable_root() -> str:
    """
    Directory used for user-writable data (logs, future config/flows).

    - ``LABSMITH_DATA_DIR`` if set (absolute path recommended).
    - Frozen (PyInstaller): directory containing the executable.
    - Otherwise: directory containing this package (``Python/``).
    """
    override = os.environ.get("LABSMITH_DATA_DIR", "").strip()
    if override:
        return os.path.abspath(override)
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def log_directory() -> str:
    """Return ``<app_writable_root>/logs``, creating it if needed."""
    global _LOG_DIR
    if _LOG_DIR is None:
        base = app_writable_root()
        _LOG_DIR = os.path.join(base, "logs")
        os.makedirs(_LOG_DIR, exist_ok=True)
    return _LOG_DIR


def output_txt_path() -> str:
    """Path to the active OUTPUT.txt file."""
    return os.path.join(log_directory(), "OUTPUT.txt")


def reset_log_directory_cache() -> None:
    """For tests only: force next call to recompute ``log_directory()``."""
    global _LOG_DIR
    _LOG_DIR = None
