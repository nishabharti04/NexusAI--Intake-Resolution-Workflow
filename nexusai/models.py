"""Validated data models shared by the application layers."""

import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RequestCategory(StrEnum):
    IT_SUPPORT = "IT Support"
    SECURITY = "Security"
    HR = "HR"
    CUSTOMER_SUPPORT = "Customer Support"
    VENDOR_ONBOARDING = "Vendor Onboarding"


class Urgency(StrEnum):
    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"
    CRITICAL = "Critical"


class RecommendedAction(StrEnum):
    ROUTE = "route"
    REQUEST_INFORMATION = "request_information"
    DRAFT_RESPONSE = "draft_response"
    ESCALATE_HUMAN = "escalate_human"


class TicketStatus(StrEnum):
    NEW = "new"
    PENDING_REVIEW = "pending_review"
    AWAITING_INFORMATION = "awaiting_information"
    ROUTED = "routed"
    ESCALATED = "escalated"
    APPROVED = "approved"
    REJECTED = "rejected"


class IntakeRequest(BaseModel):
    """A request submitted through the intake form."""

    model_config = ConfigDict(str_strip_whitespace=True)

    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10_000)
    requester_name: str = Field(min_length=1, max_length=120)
    requester_email: str = Field(min_length=6, max_length=254)

    @field_validator(
        "subject", "description", "requester_name", mode="before"
    )
    @classmethod
    def reject_blank_text(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("This field cannot be blank.")
        return value.strip() if isinstance(value, str) else value

    @field_validator("requester_email", mode="before")
    @classmethod
    def validate_requester_email(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class ClassificationResult(BaseModel):
    """Structured classification proposed by an AI or demo classifier."""

    category: RequestCategory
    urgency: Urgency
    confidence: float = Field(ge=0, le=1)
    assigned_team: str = Field(min_length=1, max_length=120)
    rationale: str = Field(min_length=1, max_length=2_000)


class ActionProposal(BaseModel):
    """A proposed next step requiring human review."""

    action: RecommendedAction
    assigned_team: str = Field(min_length=1, max_length=120)
    rationale: str = Field(min_length=1, max_length=2_000)
    draft_response: str | None = Field(default=None, max_length=5_000)


class TicketRecord(BaseModel):
    """Persisted ticket and its current workflow state."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    request: IntakeRequest
    classification: ClassificationResult | None = None
    proposal: ActionProposal | None = None
    status: TicketStatus = TicketStatus.NEW
    reviewer_notes: str | None = None
    created_by: str | None = None
    reviewed_by: str | None = None
    created_at: datetime
    updated_at: datetime
