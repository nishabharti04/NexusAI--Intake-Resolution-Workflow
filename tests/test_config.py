from pathlib import Path

import pytest

from nexusai.config import llm_settings


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
