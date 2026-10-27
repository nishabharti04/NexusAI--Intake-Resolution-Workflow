"""SQLite persistence for intake tickets."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from nexusai.models import (
    ActionProposal,
    ClassificationResult,
    IntakeRequest,
    TicketRecord,
    TicketStatus,
)


def initialize_database(path: Path) -> None:
    """Create the database directory and ticket table if they do not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_json TEXT NOT NULL,
                classification_json TEXT,
                proposal_json TEXT,
                status TEXT NOT NULL,
                reviewer_notes TEXT,
                created_by TEXT,
                reviewed_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(tickets)").fetchall()
        }
        if "created_by" not in columns:
            connection.execute("ALTER TABLE tickets ADD COLUMN created_by TEXT")
        if "reviewed_by" not in columns:
            connection.execute("ALTER TABLE tickets ADD COLUMN reviewed_by TEXT")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_tickets_created_by ON tickets(created_by)"
        )


def create_ticket(
    path: Path, request: IntakeRequest, *, created_by: str | None = None
) -> TicketRecord:
    """Persist a validated request as a new, unclassified ticket."""
    timestamp = datetime.now(UTC).isoformat()
    with sqlite3.connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO tickets (
                request_json, status, created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                request.model_dump_json(),
                TicketStatus.NEW.value,
                created_by,
                timestamp,
                timestamp,
            ),
        )
        ticket_id = cursor.lastrowid
    if ticket_id is None:
        raise RuntimeError("SQLite did not return an ID for the new ticket.")
    return get_ticket(path, ticket_id)


def get_ticket(path: Path, ticket_id: int) -> TicketRecord:
    """Load a ticket by ID, raising KeyError when it does not exist."""
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"Ticket {ticket_id} does not exist.")
    return _ticket_from_row(row)


def list_tickets(
    path: Path,
    status: TicketStatus | None = None,
    *,
    created_by: str | None = None,
) -> list[TicketRecord]:
    """Return tickets in newest-first order, optionally filtered by status."""
    conditions: list[str] = []
    parameters: list[str] = []
    if status is not None:
        conditions.append("status = ?")
        parameters.append(status.value)
    if created_by is not None:
        conditions.append("created_by = ?")
        parameters.append(created_by)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT * FROM tickets
            {where_clause}
            ORDER BY created_at DESC, id DESC
            """,
            parameters,
        ).fetchall()
    return [_ticket_from_row(row) for row in rows]


def update_ticket(
    path: Path,
    ticket_id: int,
    *,
    classification: ClassificationResult | None = None,
    proposal: ActionProposal | None = None,
    status: TicketStatus | None = None,
    reviewer_notes: str | None = None,
    reviewed_by: str | None = None,
) -> TicketRecord:
    """Update a ticket's assessment or review state."""
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        existing = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
    if existing is None:
        raise KeyError(f"Ticket {ticket_id} does not exist.")

    current = _ticket_from_row(existing)
    updated_classification = (
        classification.model_dump_json()
        if classification is not None
        else current.classification.model_dump_json()
        if current.classification
        else None
    )
    updated_proposal = (
        proposal.model_dump_json()
        if proposal is not None
        else current.proposal.model_dump_json()
        if current.proposal
        else None
    )
    new_status = status.value if status is not None else current.status.value
    new_reviewer_notes = (
        reviewer_notes if reviewer_notes is not None else current.reviewer_notes
    )
    timestamp = datetime.now(UTC).isoformat()

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE tickets
            SET classification_json = ?, proposal_json = ?, status = ?,
            reviewer_notes = ?, reviewed_by = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated_classification,
                updated_proposal,
                new_status,
                new_reviewer_notes,
                reviewed_by if reviewed_by is not None else current.reviewed_by,
                timestamp,
                ticket_id,
            ),
        )
    return get_ticket(path, ticket_id)


def _ticket_from_row(row: sqlite3.Row) -> TicketRecord:
    classification_json = row["classification_json"]
    proposal_json = row["proposal_json"]
    return TicketRecord(
        id=row["id"],
        request=IntakeRequest.model_validate_json(row["request_json"]),
        classification=(
            ClassificationResult.model_validate_json(classification_json)
            if classification_json
            else None
        ),
        proposal=(
            ActionProposal.model_validate_json(proposal_json)
            if proposal_json
            else None
        ),
        status=TicketStatus(row["status"]),
        reviewer_notes=row["reviewer_notes"],
        created_by=row["created_by"],
        reviewed_by=row["reviewed_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
