# NexusAI — Intake Resolution Workflow

## Purpose

NexusAI is a functional, local-first intake workflow application. It accepts incoming requests, uses a configurable language-model adapter to propose a classification and next action, applies deterministic safeguards to critical incidents, and gives a human reviewer control over proposed actions.

## Users and operating assumptions

- Intake agents submit requests and review the resulting ticket queue.
- Reviewers approve, edit, or reject proposed actions in the Approval Center.
- The initial release is a single-user local application; authentication and multi-user permissions are out of scope.
- SQLite is the system of record. No external service is required to run the application in clearly labelled demo mode.

## Functional requirements

### Request intake

- Provide a form to submit a request with a subject, description, requester name, and requester email.
- Validate submitted data with Pydantic and return understandable validation feedback.
- Persist accepted tickets and their workflow state in SQLite.

### Classification and recommendations

- Classify each request into exactly one category: IT Support, Security, HR, Customer Support, or Vendor Onboarding.
- Produce urgency, confidence, assigned team, recommended action, and a concise rationale.
- Support an LLM API adapter configured through environment variables; never commit or hardcode credentials.
- Validate model output as structured data. On missing configuration, use a clearly labelled demo mode so intake and the workflow remain usable.
- Keep critical-incident policy rules deterministic and outside the LLM. A matched critical signal must trigger human escalation regardless of model output or confidence.
- Choose a proposed workflow action from route, request missing information, draft a response, or escalate to a human.

### Review and workflow

- Show submitted tickets in a searchable/filterable Ticket Queue with current status and classification.
- Provide an Approval Center for proposed actions. A reviewer can approve, edit and approve, or reject an action.
- Persist reviewer decisions, edited recommendations, and status changes.
- Keep critical incidents escalated for human handling; do not allow an AI recommendation to bypass deterministic policy.

### Dashboard and analytics

- Provide a dashboard summary of ticket volume, pending review, urgency, and category.
- Provide an Analytics page with ticket counts and breakdowns by category, urgency, and workflow status.
- Present understandable empty states when the database has no tickets.

### Interface and operation

- Use Streamlit with a professional navy-blue visual theme and sidebar navigation.
- Include Dashboard, New Request, Ticket Queue, Approval Center, and Analytics pages.
- Display whether the app is using configured AI or demo mode.
- Provide beginner-friendly setup and launch instructions.

## Technical requirements

- Python application with Streamlit UI, SQLite persistence, Pydantic validation, a modular LLM API adapter, and Pytest tests.
- Keep database access, models/validation, policy rules, classification, and UI code separated.
- Store local data in a configurable or documented SQLite file; initialize its schema automatically.
- Read API configuration from environment variables, with safe missing-configuration behavior.
- Include automated tests for validation, persistence, critical policy behavior, workflow decisions, and analytics.

## Security and reliability

- No API keys or secrets in source control or sample configuration values.
- Do not let model output determine or override deterministic critical-incident handling.
- Treat model output as untrusted input and validate it before persistence or display.
- Use parameterized SQLite queries.
- If an AI request fails, report the failure clearly and use the explicitly labelled demo path only when the adapter is not configured; do not disguise configured-service failures as successful AI results.

## Acceptance criteria

1. A user can launch the app locally without an API key and see that demo mode is active.
2. A user can submit a request in any of the five categories' likely subject areas and receive a complete proposed classification and action.
3. A deterministic critical signal always results in human escalation, even if a model would recommend another action.
4. Tickets and reviewer decisions survive application restarts.
5. A reviewer can review, edit/approve, and reject proposed actions.
6. Dashboard and analytics reflect stored tickets and workflow statuses.
7. Automated tests pass, and the README contains exact setup and launch commands.

## Out of scope for the MVP

- Authentication, role-based access, and multi-tenant deployment.
- Email ingestion, external ticketing integrations, and background job processing.
- Automatic execution of model-generated actions without human review.
- Production hosting, SLA guarantees, and advanced audit/compliance features.
