import pytest
from pydantic import ValidationError

from nexusai.models import (
    ClassificationResult,
    IntakeRequest,
    RequestCategory,
    Urgency,
)


def test_intake_request_strips_whitespace_and_accepts_valid_email() -> None:
    request = IntakeRequest(
        subject="  Laptop setup  ",
        description="  Please prepare a laptop for a new employee.  ",
        requester_name="  Alex Doe ",
        requester_email=" alex@example.com ",
    )

    assert request.subject == "Laptop setup"
    assert request.requester_email == "alex@example.com"


@pytest.mark.parametrize(
    "email",
    ["not-an-email", "alex@", "@example.com", "alex@example"],
)
def test_intake_request_rejects_invalid_email(email: str) -> None:
    with pytest.raises(ValidationError, match="valid email"):
        IntakeRequest(
            subject="Laptop setup",
            description="Please prepare a laptop for a new employee.",
            requester_name="Alex Doe",
            requester_email=email,
        )


def test_intake_request_rejects_blank_subject() -> None:
    with pytest.raises(ValidationError, match="cannot be blank"):
        IntakeRequest(
            subject="   ",
            description="Please prepare a laptop for a new employee.",
            requester_name="Alex Doe",
            requester_email="alex@example.com",
        )


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_classification_rejects_confidence_out_of_range(confidence: float) -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            category=RequestCategory.IT_SUPPORT,
            urgency=Urgency.NORMAL,
            confidence=confidence,
            assigned_team="IT Helpdesk",
            rationale="The request asks for a device setup.",
        )
