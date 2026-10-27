"""Streamlit UI for the NexusAI intake and resolution workflow."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from nexusai.auth import (
    AuthenticatedUser,
    UserRole,
    allowed_pages,
    can_view_all_tickets,
    resolve_role,
)
from nexusai.classifier import LLMProviderError
from nexusai.config import database_path
from nexusai.models import (
    ActionProposal,
    IntakeRequest,
    RecommendedAction,
    TicketStatus,
)
from nexusai.storage import initialize_database, list_tickets
from nexusai.workflow import review_ticket, submit_request


DB_PATH = database_path()


def _mode_badge() -> str:
    api_key = os.getenv("NEXUSAI_LLM_API_KEY")
    if api_key:
        return "AI mode enabled"
    return "Demo mode active"


def _status_color(status: TicketStatus) -> str:
    palette = {
        TicketStatus.NEW: "#3a83f7",
        TicketStatus.PENDING_REVIEW: "#d99a00",
        TicketStatus.AWAITING_INFORMATION: "#ff8c42",
        TicketStatus.ROUTED: "#2bb673",
        TicketStatus.ESCALATED: "#c94d6a",
        TicketStatus.APPROVED: "#198754",
        TicketStatus.REJECTED: "#bb2d3b",
    }
    return palette.get(status, "#6c757d")


def _ticket_to_row(ticket) -> dict:
    classification = ticket.classification
    proposal = ticket.proposal
    return {
        "ID": ticket.id,
        "Requester": ticket.request.requester_name,
        "Category": classification.category.value if classification else "Unclassified",
        "Urgency": classification.urgency.value if classification else "Unassigned",
        "Status": ticket.status.value,
        "Assigned Team": classification.assigned_team if classification else "TBD",
        "Action": proposal.action.value if proposal else "None",
        "Created": ticket.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def _render_dashboard(user: AuthenticatedUser) -> None:
    tickets = _tickets_for_user(user)
    total = len(tickets)
    pending = sum(1 for ticket in tickets if ticket.status in {TicketStatus.NEW, TicketStatus.PENDING_REVIEW, TicketStatus.AWAITING_INFORMATION})
    escalated = sum(1 for ticket in tickets if ticket.status is TicketStatus.ESCALATED)
    approved = sum(1 for ticket in tickets if ticket.status is TicketStatus.APPROVED)

    cols = st.columns(4)
    cols[0].metric("Total tickets", total)
    cols[1].metric("Pending review", pending)
    cols[2].metric("Escalated", escalated)
    cols[3].metric("Approved", approved)

    if not tickets:
        st.info("No tickets have been submitted yet. Use New Request to add the first intake.")
        return

    df = pd.DataFrame([_ticket_to_row(ticket) for ticket in tickets[:10]])
    st.subheader("Recent tickets")
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_new_request(user: AuthenticatedUser) -> None:
    st.subheader("New Request")
    with st.form("new_request_form"):
        subject = st.text_input("Subject")
        description = st.text_area("Description")
        requester_name = st.text_input("Requester name", value=user.name, disabled=True)
        requester_email = st.text_input("Requester email", value=user.email, disabled=True)
        submitted = st.form_submit_button("Submit request")

    if not submitted:
        return

    try:
        request = IntakeRequest(
            subject=subject,
            description=description,
            requester_name=requester_name,
            requester_email=requester_email,
        )
    except Exception as exc:  # pragma: no cover - UI validation path
        st.error(f"Request data is invalid: {exc}")
        return

    try:
        ticket = submit_request(request, path=DB_PATH, created_by=user.subject)
    except LLMProviderError as exc:
        st.error(f"AI classification failed. The request was not saved. {exc}")
        return
    classification = ticket.classification
    proposal = ticket.proposal

    st.success("Ticket submitted successfully.")
    st.markdown("### Proposed classification")
    col1, col2, col3 = st.columns(3)
    if classification:
        col1.metric("Category", classification.category.value)
        col2.metric("Urgency", classification.urgency.value)
        col3.metric("Confidence", f"{classification.confidence:.0%}")
    st.write(classification.rationale if classification else "No classification available.")
    if proposal:
        st.markdown("### Proposed action")
        st.write(f"Action: **{proposal.action.value}**")
        st.write(f"Assigned team: **{proposal.assigned_team}**")
        st.write(f"Reason: {proposal.rationale}")
        if proposal.draft_response:
            st.code(proposal.draft_response)


def _render_ticket_queue(user: AuthenticatedUser) -> None:
    tickets = _tickets_for_user(user)
    if not tickets:
        st.info("The ticket queue is empty.")
        return

    status_filter = st.selectbox(
        "Status filter",
        ["All", *[status.value for status in TicketStatus]],
        index=0,
    )
    if status_filter != "All":
        tickets = [ticket for ticket in tickets if ticket.status.value == status_filter]

    df = pd.DataFrame([_ticket_to_row(ticket) for ticket in tickets])
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_approval_center(user: AuthenticatedUser) -> None:
    if user.role is UserRole.REQUESTER:
        st.error("Your account does not have permission to review tickets.")
        return
    tickets = [ticket for ticket in list_tickets(DB_PATH) if ticket.proposal and ticket.status in {TicketStatus.PENDING_REVIEW, TicketStatus.AWAITING_INFORMATION}]
    if not tickets:
        st.info("No tickets are pending approval.")
        return

    selected = st.selectbox("Review ticket", [f"#{ticket.id} - {ticket.request.subject}" for ticket in tickets])
    chosen = next(ticket for ticket in tickets if f"#{ticket.id} - {ticket.request.subject}" == selected)

    st.subheader(f"Ticket #{chosen.id}: {chosen.request.subject}")
    st.write(chosen.request.description)
    if chosen.classification:
        st.write(f"Category: {chosen.classification.category.value} | Urgency: {chosen.classification.urgency.value} | Confidence: {chosen.classification.confidence:.0%}")

    existing_proposal = chosen.proposal
    if existing_proposal is None:
        st.warning("This ticket has no proposal to review.")
        return

    with st.form(f"review_{chosen.id}"):
        action = st.selectbox(
            "Action",
            [item.value for item in RecommendedAction],
            index=[item.value for item in RecommendedAction].index(existing_proposal.action.value),
        )
        assigned_team = st.text_input("Assigned team", value=existing_proposal.assigned_team)
        rationale = st.text_area("Rationale", value=existing_proposal.rationale)
        draft_response = st.text_area("Draft response", value=existing_proposal.draft_response or "")
        reviewer_notes = st.text_area("Reviewer notes", value=chosen.reviewer_notes or "")
        decision = st.radio("Decision", ["approve", "reject", "request_more_info", "route"])
        submitted = st.form_submit_button("Submit review")

    if submitted:
        edited_proposal = ActionProposal(
            action=RecommendedAction(action),
            assigned_team=assigned_team,
            rationale=rationale,
            draft_response=draft_response or None,
        )
        updated = review_ticket(
            chosen.id,
            decision,
            reviewer_notes=reviewer_notes or None,
            edited_proposal=edited_proposal,
            reviewer_role=user.role,
            reviewed_by=user.subject,
            path=DB_PATH,
        )
        st.success(f"Ticket #{updated.id} updated to {updated.status.value}.")


def _render_analytics(user: AuthenticatedUser) -> None:
    if user.role is UserRole.REQUESTER:
        st.error("Your account does not have permission to view team analytics.")
        return
    tickets = list_tickets(DB_PATH)
    if not tickets:
        st.info("No analytics are available until a request is processed.")
        return

    df = pd.DataFrame([_ticket_to_row(ticket) for ticket in tickets])
    st.subheader("Category breakdown")
    st.bar_chart(df["Category"].value_counts())

    st.subheader("Urgency distribution")
    st.bar_chart(df["Urgency"].value_counts())

    st.subheader("Workflow status")
    st.bar_chart(df["Status"].value_counts())


def _tickets_for_user(user: AuthenticatedUser):
    if can_view_all_tickets(user.role):
        return list_tickets(DB_PATH)
    return list_tickets(DB_PATH, created_by=user.subject)


def _authenticate_user() -> AuthenticatedUser | None:
    try:
        auth_config = st.secrets.get("auth", {})
    except StreamlitSecretNotFoundError:
        auth_config = {}
    required_auth_settings = (
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    )
    if any(not auth_config.get(setting) for setting in required_auth_settings):
        st.error(
            "Sign-in is not configured. Follow the OIDC setup instructions in README.md "
            "and add credentials to .streamlit/secrets.toml."
        )
        return None

    if not st.user.is_logged_in:
        st.button("Sign in with your organization", on_click=st.login)
        return None

    email = st.user.get("email")
    subject = st.user.get("sub")
    if not isinstance(email, str) or not isinstance(subject, str) or not email or not subject:
        st.error("Your identity provider did not return the required email and subject claims.")
        st.logout()
        return None
    if st.user.get("email_verified") is False:
        st.error("Your identity provider reports that your email address is not verified.")
        st.logout()
        return None

    nexusai_config = st.secrets.get("nexusai", {})
    role = resolve_role(
        email,
        admin_emails=nexusai_config.get("admin_emails", []),
        reviewer_emails=nexusai_config.get("reviewer_emails", []),
    )
    name = st.user.get("name")
    return AuthenticatedUser(
        subject=subject,
        email=email,
        name=name if isinstance(name, str) and name else email,
        role=role,
    )


def main() -> None:
    initialize_database(DB_PATH)
    st.set_page_config(page_title="NexusAI", page_icon="🤖", layout="wide")
    st.markdown(
        """
        <style>
            .stApp { background: linear-gradient(135deg, #09182f 0%, #122a4d 100%); }
            .stSidebar { background: #0b1d36; }
            div[data-testid="stMetricValue"] { color: #cfe3ff; }
            div[data-testid="stFormSubmitButton"] button { background: #2f7df6; color: white; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("NexusAI — Intake Resolution Workflow")
    user = _authenticate_user()
    if user is None:
        st.stop()
    st.caption(f"System mode: { _mode_badge() }")

    with st.sidebar:
        st.markdown("### NexusAI")
        st.write(f"{user.name} · {user.role.value}")
        st.button("Sign out", on_click=st.logout)
        page = st.radio("Navigation", allowed_pages(user.role))

    if page == "Dashboard":
        _render_dashboard(user)
    elif page == "New Request":
        _render_new_request(user)
    elif page == "Ticket Queue":
        _render_ticket_queue(user)
    elif page == "Approval Center":
        _render_approval_center(user)
    else:
        _render_analytics(user)


if __name__ == "__main__":
    main()
