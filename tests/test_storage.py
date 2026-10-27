from pathlib import Path

import pytest

from nexusai.models import IntakeRequest, TicketStatus
from nexusai.storage import create_ticket, get_ticket, initialize_database, list_tickets


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "nested" / "tickets.sqlite3"
    initialize_database(path)
    return path


def sample_request(subject: str = "Laptop setup") -> IntakeRequest:
    return IntakeRequest(
        subject=subject,
        description="Please prepare a laptop for a new employee.",
        requester_name="Alex Doe",
        requester_email="alex@example.com",
    )


def test_create_ticket_persists_request(database_path: Path) -> None:
    created = create_ticket(database_path, sample_request())
    loaded = get_ticket(database_path, created.id)

    assert loaded.id == created.id
    assert loaded.request == sample_request()
    assert loaded.status is TicketStatus.NEW
    assert loaded.created_at == loaded.updated_at


def test_list_tickets_orders_newest_first_and_filters_status(
    database_path: Path,
) -> None:
    first = create_ticket(database_path, sample_request("First request"))
    second = create_ticket(database_path, sample_request("Second request"))

    tickets = list_tickets(database_path)
    new_tickets = list_tickets(database_path, TicketStatus.NEW)

    assert [ticket.id for ticket in tickets] == [second.id, first.id]
    assert [ticket.id for ticket in new_tickets] == [second.id, first.id]
    assert list_tickets(database_path, TicketStatus.APPROVED) == []


def test_list_tickets_can_be_scoped_to_creator(database_path: Path) -> None:
    first = create_ticket(database_path, sample_request("First request"), created_by="user-1")
    create_ticket(database_path, sample_request("Second request"), created_by="user-2")

    assert [ticket.id for ticket in list_tickets(database_path, created_by="user-1")] == [
        first.id
    ]


def test_initialize_database_migrates_existing_ticket_table(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE tickets (
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

    initialize_database(path)

    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tickets)")}
    assert "created_by" in columns
    assert "reviewed_by" in columns


def test_get_ticket_reports_missing_id(database_path: Path) -> None:
    with pytest.raises(KeyError, match="does not exist"):
        get_ticket(database_path, 999)
