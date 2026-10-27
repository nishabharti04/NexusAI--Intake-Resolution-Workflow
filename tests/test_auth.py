import pytest

from nexusai.auth import (
    UserRole,
    allowed_pages,
    can_review,
    can_view_all_tickets,
    resolve_role,
)


def test_resolve_role_defaults_to_requester() -> None:
    assert resolve_role("new.user@example.com") is UserRole.REQUESTER


def test_resolve_role_matches_emails_case_insensitively() -> None:
    role = resolve_role(
        "REVIEWER@example.com ",
        reviewer_emails=["reviewer@example.com"],
    )

    assert role is UserRole.REVIEWER


def test_admin_role_has_precedence_over_reviewer_role() -> None:
    role = resolve_role(
        "admin@example.com",
        admin_emails=["admin@example.com"],
        reviewer_emails=["admin@example.com"],
    )

    assert role is UserRole.ADMIN


@pytest.mark.parametrize("role", [UserRole.REVIEWER, UserRole.ADMIN])
def test_reviewers_and_admins_can_review_and_view_all_tickets(role: UserRole) -> None:
    assert can_review(role)
    assert can_view_all_tickets(role)
    assert "Approval Center" in allowed_pages(role)


def test_requesters_cannot_review_or_view_other_users_tickets() -> None:
    assert not can_review(UserRole.REQUESTER)
    assert not can_view_all_tickets(UserRole.REQUESTER)
    assert "Approval Center" not in allowed_pages(UserRole.REQUESTER)
