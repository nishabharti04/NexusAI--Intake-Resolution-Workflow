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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_json TEXT NOT NULL,
                classification_json TEXT,
                proposal_json TEXT,
                status TEXT NOT NULL,
                reviewer_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)"
        )


def create_ticket(path: Path, request: IntakeRequest) -> TicketRecord:
    """Persist a validated request as a new, unclassified ticket."""
    timestamp = datetime.now(UTC).isoformat()
    with sqlite3.connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO tickets (
                request_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                request.model_dump_json(),
                TicketStatus.NEW.value,
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
    path: Path, status: TicketStatus | None = None
) -> list[TicketRecord]:
    """Return tickets in newest-first order, optionally filtered by status."""
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        if status is None:
            rows = connection.execute(
                "SELECT * FROM tickets ORDER BY created_at DESC, id DESC"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM tickets
                WHERE status = ?
                ORDER BY created_at DESC, id DESC
                """,
                (status.value,),
            ).fetchall()
    return [_ticket_from_row(row) for row in rows]


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
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
