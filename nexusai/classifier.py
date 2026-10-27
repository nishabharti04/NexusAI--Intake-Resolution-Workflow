"""AI and demo classification logic for NexusAI."""

from __future__ import annotations

import json
import os
from typing import Any

import requests
from pydantic import TypeAdapter, ValidationError

from nexusai.models import (
    ActionProposal,
    ClassificationResult,
    IntakeRequest,
    RecommendedAction,
    RequestCategory,
    Urgency,
)


class LLMProviderError(RuntimeError):
    """A provider request or response could not be completed safely."""


def _category_for_text(text: str) -> RequestCategory:
    lower = text.lower()
    if any(token in lower for token in ["security", "breach", "phishing", "malware", "data leak", "incident", "ransomware", "hack"]):
        return RequestCategory.SECURITY
    if any(token in lower for token in ["hr", "benefits", "leave", "payroll", "policy", "employee", "termination", "vacation"]):
        return RequestCategory.HR
    if any(token in lower for token in ["customer", "billing", "invoice", "refund", "complaint", "support", "ticket", "service outage"]):
        return RequestCategory.CUSTOMER_SUPPORT
    if any(token in lower for token in ["vendor", "supplier", "onboarding", "contract", "access request", "new vendor"]):
        return RequestCategory.VENDOR_ONBOARDING
    return RequestCategory.IT_SUPPORT


def _urgency_for_text(processed_text: str) -> Urgency:
    lower = processed_text.lower()
    if any(token in lower for token in ["critical", "breach", "ransomware", "security incident", "outage", "data exfiltration", "system down", "production issue"]):
        return Urgency.CRITICAL
    if any(token in lower for token in ["urgent", "deadline", "customer impact", "cannot access", "blocked", "incident"]):
        return Urgency.HIGH
    if any(token in lower for token in ["soon", "asap", "time-sensitive"]):
        return Urgency.NORMAL
    return Urgency.LOW


def _default_team_for_category(category: RequestCategory) -> str:
    mapping = {
        RequestCategory.IT_SUPPORT: "IT Helpdesk",
        RequestCategory.SECURITY: "Security Operations",
        RequestCategory.HR: "People Operations",
        RequestCategory.CUSTOMER_SUPPORT: "Customer Support Team",
        RequestCategory.VENDOR_ONBOARDING: "Procurement & Vendor Management",
    }
    return mapping[category]


def _default_action_for_category(category: RequestCategory, urgency: Urgency) -> RecommendedAction:
    if urgency is Urgency.CRITICAL:
        return RecommendedAction.ESCALATE_HUMAN
    if category is RequestCategory.SECURITY:
        return RecommendedAction.ESCALATE_HUMAN
    if category is RequestCategory.HR:
        return RecommendedAction.REQUEST_INFORMATION
    if category is RequestCategory.CUSTOMER_SUPPORT:
        return RecommendedAction.DRAFT_RESPONSE
    return RecommendedAction.ROUTE


def _demo_classification(request: IntakeRequest) -> ClassificationResult:
    category = _category_for_text(f"{request.subject} {request.description}")
    urgency = _urgency_for_text(f"{request.subject} {request.description}")
    assigned_team = _default_team_for_category(category)
    action = _default_action_for_category(category, urgency)
    rationale = (
        f"Demo-mode rules matched the request to {category.value} with "
        f"{urgency.value.lower()} urgency. Recommended action: {action.value}."
    )
    return ClassificationResult(
        category=category,
        urgency=urgency,
        confidence=0.9 if urgency is not Urgency.LOW else 0.8,
        assigned_team=assigned_team,
        rationale=rationale,
    )


def _validate_model_payload(payload: Any) -> ClassificationResult:
    adapter = TypeAdapter(ClassificationResult)
    return adapter.validate_python(payload)


def _build_llm_request_body(request: IntakeRequest) -> dict[str, Any]:
    return {
        "model": os.getenv("NEXUSAI_LLM_MODEL", "gpt-4o-mini"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You classify enterprise support requests. Return strict JSON with the keys: "
                    "category, urgency, confidence, assigned_team, rationale. "
                    "Use one of these category strings exactly: 'IT Support', 'Security', 'HR', 'Customer Support', 'Vendor Onboarding'. "
                    "Use urgency values only from: 'Low', 'Normal', 'High', 'Critical'. "
                    "Confidence must be between 0 and 1."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Subject: {request.subject}\nDescription: {request.description}\n"
                ),
            },
        ],
        "temperature": 0,
    }


def classify_request(request: IntakeRequest) -> tuple[ClassificationResult, str]:
    """Return a structured classification and the mode used to generate it."""
    api_key = os.getenv("NEXUSAI_LLM_API_KEY")
    if not api_key:
        return _demo_classification(request), "demo"
    base_url = os.getenv(
        "NEXUSAI_LLM_BASE_URL",
        "https://api.openai.com/v1/chat/completions",
    )

    try:
        response = requests.post(
            base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=_build_llm_request_body(request),
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status is not None:
            raise LLMProviderError(
                f"LLM provider returned HTTP {status}. Check the API key, endpoint, and provider status."
            ) from None
        raise LLMProviderError(
            "Could not reach the LLM provider. Check the endpoint and network connection."
        ) from None

    try:
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content) if isinstance(content, str) else content
        classification = _validate_model_payload(parsed)
    except (KeyError, IndexError, TypeError, ValueError, ValidationError):
        raise LLMProviderError(
            "The LLM provider response did not contain valid classification JSON."
        ) from None

    return classification, "ai"


def policy_override(request: IntakeRequest) -> tuple[ClassificationResult, ActionProposal] | None:
    """Apply deterministic critical policies before any model result is accepted."""
    text = f"{request.subject} {request.description}".lower()
    severe_signals = [
        "security breach",
        "ransomware",
        "phishing",
        "credential theft",
        "data leak",
        "outage",
        "service down",
        "system unavailable",
        "production issue",
    ]
    if any(signal in text for signal in severe_signals):
        classification = ClassificationResult(
            category=RequestCategory.SECURITY,
            urgency=Urgency.CRITICAL,
            confidence=0.99,
            assigned_team="Security Operations",
            rationale=(
                "Deterministic policy rules detected a critical security or operational outage "
                "signal and forced human escalation."
            ),
        )
        proposal = ActionProposal(
            action=RecommendedAction.ESCALATE_HUMAN,
            assigned_team="Security Operations",
            rationale=(
                "The request matches a critical safety policy. A human responder must triage it "
                "immediately and perform incident handling."
            ),
            draft_response="This request requires immediate human triage due to a critical security or outage signal. Please escalate to the on-call security or IT lead.",
        )
        return classification, proposal
    return None


def build_proposal(request: IntakeRequest) -> tuple[ClassificationResult, ActionProposal, str]:
    """Return a classification and draft action, respecting deterministic policy."""
    override = policy_override(request)
    if override is not None:
        classification, proposal = override
        return classification, proposal, "policy"

    classification, mode = classify_request(request)
    action = _default_action_for_category(classification.category, classification.urgency)
    proposal = ActionProposal(
        action=action,
        assigned_team=classification.assigned_team,
        rationale=classification.rationale,
        draft_response=(
            "Please review the request and proceed with the assigned team workflow. "
            "A summary is included in the ticket for full review."
            if action is not RecommendedAction.ESCALATE_HUMAN
            else "This is a critical request. Human escalation is required immediately."
        ),
    )
    if classification.urgency is Urgency.CRITICAL:
        proposal.action = RecommendedAction.ESCALATE_HUMAN
        proposal.rationale = "Critical urgency indicates a need for human-led escalation and incident handling."
        proposal.draft_response = "This request was flagged as critical and requires immediate human triage."
    return classification, proposal, mode
