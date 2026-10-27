from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_local_llm_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "nexusai.config.llm_secrets_path",
        lambda: tmp_path / "secrets.toml",
    )
