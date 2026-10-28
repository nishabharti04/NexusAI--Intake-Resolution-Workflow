"""Application configuration loaded from environment variables."""

import json
import os
from pathlib import Path
import tomllib


def database_path() -> Path:
    """Return the SQLite file path configured for this application."""
    return Path(os.getenv("NEXUSAI_DB_PATH", "nexusai.db")).expanduser()


def streamlit_secrets_path() -> Path:
    """Return the path to private, local Streamlit settings."""
    return Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"


def llm_secrets_path() -> Path:
    """Return the path used for private LLM settings."""
    return streamlit_secrets_path()


def ensure_streamlit_secrets() -> None:
    """Create runtime Streamlit secrets from deployment environment variables."""
    secrets_path = streamlit_secrets_path()
    if secrets_path.exists():
        return

    auth_values = {
        key: os.getenv(environment_name)
        for key, environment_name in (
            ("redirect_uri", "NEXUSAI_AUTH_REDIRECT_URI"),
            ("cookie_secret", "NEXUSAI_AUTH_COOKIE_SECRET"),
            ("client_id", "NEXUSAI_AUTH_CLIENT_ID"),
            ("client_secret", "NEXUSAI_AUTH_CLIENT_SECRET"),
            ("server_metadata_url", "NEXUSAI_AUTH_SERVER_METADATA_URL"),
        )
    }
    configured_auth_values = [value for value in auth_values.values() if value]
    if not configured_auth_values:
        return
    missing = [key for key, value in auth_values.items() if not value]
    if missing:
        raise RuntimeError(
            "Incomplete hosted authentication configuration. Missing environment values: "
            + ", ".join(missing)
        )

    admin_emails = _email_list("NEXUSAI_ADMIN_EMAILS")
    reviewer_emails = _email_list("NEXUSAI_REVIEWER_EMAILS")
    lines = ["[auth]"]
    lines.extend(f"{key} = {json.dumps(value)}" for key, value in auth_values.items())
    lines.extend(
        [
            "",
            "[nexusai]",
            f"admin_emails = {json.dumps(admin_emails)}",
            f"reviewer_emails = {json.dumps(reviewer_emails)}",
        ]
    )
    llm_settings = {
        key: os.getenv(environment_name)
        for key, environment_name in (
            ("api_key", "NEXUSAI_LLM_API_KEY"),
            ("base_url", "NEXUSAI_LLM_BASE_URL"),
            ("model", "NEXUSAI_LLM_MODEL"),
        )
        if os.getenv(environment_name)
    }
    if llm_settings:
        lines.extend(["", "[llm]"])
        lines.extend(f"{key} = {json.dumps(value)}" for key, value in llm_settings.items())

    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    secrets_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _email_list(environment_name: str) -> list[str]:
    value = os.getenv(environment_name, "")
    return [email.strip() for email in value.split(",") if email.strip()]


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
