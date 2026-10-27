"""Role resolution for users authenticated by the configured OIDC provider."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class UserRole(StrEnum):
    REQUESTER = "Requester"
    REVIEWER = "Reviewer"
    ADMIN = "Admin"


@dataclass(frozen=True)
class AuthenticatedUser:
    subject: str
    email: str
    name: str
    role: UserRole


def resolve_role(
    email: str,
    *,
    admin_emails: Iterable[str] = (),
    reviewer_emails: Iterable[str] = (),
) -> UserRole:
    """Resolve the highest explicitly configured role; default to requester."""
    normalized_email = email.strip().casefold()
    if not normalized_email:
        raise ValueError("An authenticated email is required to resolve access.")

    if normalized_email in {value.strip().casefold() for value in admin_emails}:
        return UserRole.ADMIN
    if normalized_email in {value.strip().casefold() for value in reviewer_emails}:
        return UserRole.REVIEWER
    return UserRole.REQUESTER


def can_review(role: UserRole) -> bool:
    return role in {UserRole.REVIEWER, UserRole.ADMIN}


def can_view_all_tickets(role: UserRole) -> bool:
    return role in {UserRole.REVIEWER, UserRole.ADMIN}


def allowed_pages(role: UserRole) -> tuple[str, ...]:
    requester_pages = ("Dashboard", "New Request", "Ticket Queue")
    if role is UserRole.REQUESTER:
        return requester_pages
    return (*requester_pages, "Approval Center", "Analytics")
