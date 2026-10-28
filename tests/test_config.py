from pathlib import Path

import pytest

from nexusai.config import ensure_streamlit_secrets, llm_settings


def test_llm_settings_load_from_local_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secrets_path = tmp_path / "secrets.toml"
    secrets_path.write_text(
        '[llm]\napi_key = "ollama"\n'
        'base_url = "http://localhost:11434/v1/chat/completions"\n'
        'model = "qwen2.5:3b"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("nexusai.config.llm_secrets_path", lambda: secrets_path)

    assert llm_settings() == {
        "api_key": "ollama",
        "base_url": "http://localhost:11434/v1/chat/completions",
        "model": "qwen2.5:3b",
    }


def test_environment_variables_override_local_llm_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secrets_path = tmp_path / "secrets.toml"
    secrets_path.write_text(
        '[llm]\napi_key = "local-key"\n'
        'base_url = "http://localhost:11434/v1/chat/completions"\n'
        'model = "qwen2.5:3b"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("nexusai.config.llm_secrets_path", lambda: secrets_path)
    monkeypatch.setenv("NEXUSAI_LLM_API_KEY", "environment-key")

    assert llm_settings()["api_key"] == "environment-key"


def test_hosted_secrets_are_created_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secrets_path = tmp_path / ".streamlit" / "secrets.toml"
    monkeypatch.setattr("nexusai.config.streamlit_secrets_path", lambda: secrets_path)
    monkeypatch.setenv("NEXUSAI_AUTH_REDIRECT_URI", "https://nexusai.example/oauth2callback")
    monkeypatch.setenv("NEXUSAI_AUTH_COOKIE_SECRET", "cookie-secret")
    monkeypatch.setenv("NEXUSAI_AUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("NEXUSAI_AUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv(
        "NEXUSAI_AUTH_SERVER_METADATA_URL",
        "https://accounts.google.com/.well-known/openid-configuration",
    )
    monkeypatch.setenv("NEXUSAI_ADMIN_EMAILS", "admin@example.com")
    monkeypatch.setenv("NEXUSAI_REVIEWER_EMAILS", "reviewer@example.com")

    ensure_streamlit_secrets()

    content = secrets_path.read_text(encoding="utf-8")
    assert "[auth]" in content
    assert 'client_id = "client-id"' in content
    assert "admin_emails" in content


def test_hosted_secrets_refresh_existing_runtime_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secrets_path = tmp_path / ".streamlit" / "secrets.toml"
    secrets_path.parent.mkdir()
    secrets_path.write_text(
        '[auth]\nredirect_uri = "https://nexusai.onrender.com/oauth2callback"\n'
        'cookie_secret = "old-cookie"\nclient_id = "old-client"\n'
        'client_secret = "old-secret"\n'
        'server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("nexusai.config.streamlit_secrets_path", lambda: secrets_path)
    monkeypatch.setenv(
        "NEXUSAI_AUTH_REDIRECT_URI",
        "https://nexusai-v21a.onrender.com/oauth2callback",
    )
    monkeypatch.setenv("NEXUSAI_AUTH_COOKIE_SECRET", "new-cookie")
    monkeypatch.setenv("NEXUSAI_AUTH_CLIENT_ID", "new-client")
    monkeypatch.setenv("NEXUSAI_AUTH_CLIENT_SECRET", "new-secret")
    monkeypatch.setenv(
        "NEXUSAI_AUTH_SERVER_METADATA_URL",
        "https://accounts.google.com/.well-known/openid-configuration",
    )

    ensure_streamlit_secrets()

    content = secrets_path.read_text(encoding="utf-8")
    assert "nexusai-v21a.onrender.com" in content
    assert "old-client" not in content


def test_hosted_secrets_reject_incomplete_auth_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secrets_path = tmp_path / ".streamlit" / "secrets.toml"
    monkeypatch.setattr("nexusai.config.streamlit_secrets_path", lambda: secrets_path)
    monkeypatch.setenv("NEXUSAI_AUTH_CLIENT_ID", "client-id")

    with pytest.raises(RuntimeError, match="Incomplete hosted authentication"):
        ensure_streamlit_secrets()
