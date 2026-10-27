"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
import tomllib


def database_path() -> Path:
    """Return the SQLite file path configured for this application."""
    return Path(os.getenv("NEXUSAI_DB_PATH", "nexusai.db")).expanduser()


def llm_secrets_path() -> Path:
    """Return the path to private, local Streamlit settings."""
    return Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"


def llm_settings() -> dict[str, str]:
    """Load LLM settings from environment variables and local Streamlit secrets."""
    local_settings: dict[str, object] = {}
    secrets_path = llm_secrets_path()
    if secrets_path.exists():
        with secrets_path.open("rb") as secrets_file:
            secrets = tomllib.load(secrets_file)
        configured_settings = secrets.get("llm", {})
        if not isinstance(configured_settings, dict):
            raise ValueError("The [llm] section in .streamlit/secrets.toml must be a table.")
        local_settings = configured_settings

    settings: dict[str, str] = {}
    for key, environment_name, default in (
        ("api_key", "NEXUSAI_LLM_API_KEY", None),
        ("base_url", "NEXUSAI_LLM_BASE_URL", "https://api.openai.com/v1/chat/completions"),
        ("model", "NEXUSAI_LLM_MODEL", "gpt-4o-mini"),
    ):
        value = os.getenv(environment_name) or local_settings.get(key) or default
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"The {key} value in .streamlit/secrets.toml must be a string.")
            settings[key] = value
    return settings
