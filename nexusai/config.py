"""Application configuration loaded from environment variables."""

import os
from pathlib import Path


def database_path() -> Path:
    """Return the SQLite file path configured for this application."""
    return Path(os.getenv("NEXUSAI_DB_PATH", "nexusai.db")).expanduser()
