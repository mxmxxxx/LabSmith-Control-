"""
Central log directory for OUTPUT.txt and session archives.

All runtime logs go under Python/logs/ next to this file.
"""
import os
from typing import Optional

_LOG_DIR: Optional[str] = None


def log_directory() -> str:
    """Return .../Python/logs, creating it if needed."""
    global _LOG_DIR
    if _LOG_DIR is None:
        base = os.path.dirname(os.path.abspath(__file__))
        _LOG_DIR = os.path.join(base, "logs")
        os.makedirs(_LOG_DIR, exist_ok=True)
    return _LOG_DIR


def output_txt_path() -> str:
    """Path to the active OUTPUT.txt file."""
    return os.path.join(log_directory(), "OUTPUT.txt")
