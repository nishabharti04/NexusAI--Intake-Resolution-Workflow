"""User workflow helpers for triage, review, and approval."""

from __future__ import annotations

from pathlib import Path

from nexusai.classifier import build_proposal
from nexusai.config import database_path
from nexusai.models import ActionProposal, ClassificationResult, IntakeRequest, TicketRecord, TicketStatus
from nexusai.storage import create_ticket, get_ticket, initialize_database, update_ticket


def submit_request(request: IntakeRequest, path: Path | None = None) -> TicketRecord:
    """Submit a request, classify it, and store the first decision."""
    target_path = path or database_path()
    initialize_database(target_path)
    ticket = create_ticket(target_path, request)
    classification, proposal, _ = build_proposal(request)
    updated = update_ticket(
        target_path,
        ticket.id,
        classification=classification,
        proposal=proposal,
        status=TicketStatus.PENDING_REVIEW,
    )
    return updated


def review_ticket(
    ticket_id: int,
    decision: str,
    *,
    reviewer_notes: str | None = None,
    edited_proposal: ActionProposal | None = None,
    path: Path | None = None,
) -> TicketRecord:
    """Approve, reject, or edit a proposed action for a ticket."""
    target_path = path or database_path()
    existing = get_ticket(target_path, ticket_id)
    status_map = {
        "approve": TicketStatus.APPROVED,
        "reject": TicketStatus.REJECTED,
        "request_more_info": TicketStatus.AWAITING_INFORMATION,
        "route": TicketStatus.ROUTED,
    }
    if decision not in status_map:
        raise ValueError(f"Unsupported review decision: {decision}")

    updated_proposal = edited_proposal or existing.proposal
    if updated_proposal is None:
        raise ValueError("Tickets without a proposal cannot be reviewed.")

    return update_ticket(
        target_path,
        ticket_id,
        proposal=updated_proposal,
        status=status_map[decision],
        reviewer_notes=reviewer_notes or existing.reviewer_notes,
    )
