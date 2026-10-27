import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from nexusai.classifier import LLMProviderError, classify_request
from nexusai.models import IntakeRequest, RequestCategory, Urgency
from nexusai.storage import list_tickets
from nexusai.workflow import submit_request


def sample_request() -> IntakeRequest:
    return IntakeRequest(
        subject="Cannot access account",
        description="I cannot access my account after resetting my password.",
        requester_name="Private Requester",
        requester_email="private@example.com",
    )


def test_classify_request_uses_openai_default_and_minimizes_personal_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXUSAI_LLM_API_KEY", "test-token")
    monkeypatch.delenv("NEXUSAI_LLM_BASE_URL", raising=False)
    monkeypatch.setenv("NEXUSAI_LLM_MODEL", "test-model")
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "category": "IT Support",
                                    "urgency": "High",
                                    "confidence": 0.94,
                                    "assigned_team": "IT Helpdesk",
                                    "rationale": "The requester cannot sign in.",
                                }
                            )
                        }
                    }
                ]
            }

    def fake_post(url: str, **kwargs: dict) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("nexusai.classifier.requests.post", fake_post)

    classification, mode = classify_request(sample_request())

    assert mode == "ai"
    assert classification.category is RequestCategory.IT_SUPPORT
    assert classification.urgency is Urgency.HIGH
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["json"]["model"] == "test-model"
    user_message = captured["json"]["messages"][1]["content"]
    assert "Private Requester" not in user_message
    assert "private@example.com" not in user_message
    assert captured["timeout"] == 30


def test_classify_request_uses_demo_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NEXUSAI_LLM_API_KEY", raising=False)
    monkeypatch.setenv("NEXUSAI_LLM_BASE_URL", "https://provider.example/v1/chat/completions")

    classification, mode = classify_request(sample_request())

    assert mode == "demo"
    assert classification.category in RequestCategory


def test_classify_request_surfaces_provider_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXUSAI_LLM_API_KEY", "test-token")
    monkeypatch.setattr(
        "nexusai.classifier.requests.post",
        lambda *args, **kwargs: _UnauthorizedResponse(),
    )

    with pytest.raises(LLMProviderError, match="HTTP 401"):
        classify_request(sample_request())


def test_classify_request_rejects_malformed_provider_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXUSAI_LLM_API_KEY", "test-token")

    class MalformedResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": '{"category":"unknown"}'}}]}

    monkeypatch.setattr(
        "nexusai.classifier.requests.post",
        lambda *args, **kwargs: MalformedResponse(),
    )

    with pytest.raises(LLMProviderError, match="valid classification JSON"):
        classify_request(sample_request())


def test_provider_failure_does_not_save_unclassified_ticket(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("NEXUSAI_LLM_API_KEY", "test-token")

    def fail_to_connect(*args: object, **kwargs: object) -> None:
        raise requests.ConnectionError()

    monkeypatch.setattr(
        "nexusai.classifier.requests.post",
        fail_to_connect,
    )
    path = tmp_path / "tickets.sqlite3"

    with pytest.raises(LLMProviderError):
        submit_request(
            sample_request(),
            path=path,
            created_by="oidc-user-1",
        )

    assert list_tickets(path) == []


class _UnauthorizedResponse:
    def raise_for_status(self) -> None:
        response = SimpleNamespace(status_code=401)
        raise requests.HTTPError(response=response)
