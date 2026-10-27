from pathlib import Path

import pytest

from nexusai.classifier import build_proposal, policy_override
from nexusai.auth import UserRole
from nexusai.models import ActionProposal, IntakeRequest, RecommendedAction, RequestCategory, TicketStatus, Urgency
from nexusai.workflow import review_ticket, submit_request


def sample_request(subject: str = "Password reset") -> IntakeRequest:
    return IntakeRequest(
        subject=subject,
        description="I cannot access my account and need my password reset immediately.",
        requester_name="Alex Doe",
        requester_email="alex@example.com",
    )


def test_build_proposal_uses_demo_mode_when_no_api_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEXUSAI_LLM_API_KEY", raising=False)
    monkeypatch.delenv("NEXUSAI_LLM_BASE_URL", raising=False)

    classification, proposal, mode = build_proposal(sample_request())

    assert mode == "demo"
    assert classification.category in RequestCategory
    assert proposal.action in RecommendedAction


def test_policy_override_enforces_critical_security_escalation() -> None:
    request = sample_request("Security breach: we suspect ransomware is encrypting files")
    override = policy_override(request)

    assert override is not None
    classification, proposal = override
    assert classification.urgency is Urgency.CRITICAL
    assert proposal.action is RecommendedAction.ESCALATE_HUMAN


def test_submit_request_persists_classification_and_status(tmp_path: Path) -> None:
    ticket = submit_request(
        sample_request(),
        path=tmp_path / "tickets.sqlite3",
        created_by="oidc-user-1",
    )

    assert ticket.status is TicketStatus.PENDING_REVIEW
    assert ticket.classification is not None
    assert ticket.proposal is not None


def test_review_ticket_allows_edit_and_approve(tmp_path: Path) -> None:
    ticket = submit_request(
        sample_request(),
        path=tmp_path / "tickets.sqlite3",
        created_by="oidc-user-1",
    )
    edited = ActionProposal(
        action=RecommendedAction.DRAFT_RESPONSE,
        assigned_team="Customer Support Team",
        rationale="The customer issue only needs a service response.",
        draft_response="We have started the review on your ticket.",
    )

    updated = review_ticket(
        ticket.id,
        "approve",
        edited_proposal=edited,
        reviewer_role=UserRole.REVIEWER,
        reviewed_by="oidc-reviewer-1",
        path=tmp_path / "tickets.sqlite3",
    )

    assert updated.status is TicketStatus.APPROVED
    assert updated.proposal == edited
    assert updated.created_by == "oidc-user-1"
    assert updated.reviewed_by == "oidc-reviewer-1"


def test_requester_cannot_review_ticket(tmp_path: Path) -> None:
    ticket = submit_request(
        sample_request(),
        path=tmp_path / "tickets.sqlite3",
        created_by="oidc-user-1",
    )

    with pytest.raises(PermissionError, match="Only reviewers and admins"):
        review_ticket(
            ticket.id,
            "approve",
            reviewer_role=UserRole.REQUESTER,
            reviewed_by="oidc-user-2",
            path=tmp_path / "tickets.sqlite3",
        )
