# NexusAI — Intake Resolution Workflow

NexusAI is a beginner-friendly Streamlit application that captures intake requests, classifies them, applies deterministic critical-incident rules, stores tickets in SQLite, and gives reviewers a queue for approval and edits.

## Features

- Intake form for requests and personnel metadata
- Demo AI mode when no API key is configured
- Structured classification into IT Support, Security, HR, Customer Support, and Vendor Onboarding
- Urgency, confidence, assigned team, and action recommendation
- Deterministic critical incident policy outside the LLM
- SQLite-backed ticket persistence and workflow status tracking
- Review and approval center for routing decisions
- Dashboard and analytics views
- Google or Microsoft OIDC login with Requester, Reviewer, and Admin roles
- Requester-owned ticket visibility and reviewer attribution
- Automated tests with pytest

## Local setup

1. Open a terminal in the project root.
2. Create a virtual environment:
   `python -m venv .venv`
3. Activate it:
   - Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
   - Windows CMD: `.\.venv\Scripts\activate.bat`
4. Install dependencies:
   `python -m pip install -r requirements.txt`

## Demo mode

No API key is required for local use. The app automatically uses demo mode when either `NEXUSAI_LLM_API_KEY` or `NEXUSAI_LLM_BASE_URL` is missing.

## Configure a real LLM provider

The default provider is OpenAI's Chat Completions API. Set the API key as an
environment variable; do not put a real key in source files or commit it.
Classification sends only the request subject and description to the provider,
not the requester's name or email.

PowerShell:

```powershell
$env:NEXUSAI_LLM_API_KEY = Read-Host "Enter your LLM API key"
$env:NEXUSAI_LLM_BASE_URL = "https://api.openai.com/v1/chat/completions"
$env:NEXUSAI_LLM_MODEL = "gpt-4o-mini"
python -m streamlit run app.py
```

For an OpenAI-compatible provider, set `NEXUSAI_LLM_BASE_URL` to that provider's
Chat Completions endpoint and set `NEXUSAI_LLM_MODEL` to a model it supports.
When no API key is configured, the app clearly indicates demo mode. If a
configured provider request fails, the app reports the error and does not
silently switch to demo mode or save a partially classified request.

## Configure sign-in and roles

The app requires OIDC sign-in; there is no unauthenticated mode. Streamlit
handles the OpenID Connect login, and NexusAI maps authenticated email addresses
to roles. Users not listed as admins or reviewers receive the Requester role.

1. Register an OIDC web application with Google Identity, Microsoft Entra ID,
   or another compatible provider.
2. Register this local redirect URI with the provider:
   `http://localhost:8501/oauth2callback`
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
4. Replace the client ID, client secret, and cookie secret with your own values.
   Generate a cookie secret with:
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`
5. Add the email addresses for administrators to `admin_emails` and reviewers
   to `reviewer_emails`. Keep the lists private.
6. Start the app using the launch command below and sign in through your
   provider.

Role permissions:

- **Requester:** submit requests and view only tickets they created.
- **Reviewer:** view the team queue, review/approve/reject tickets, and see
  analytics.
- **Admin:** all Reviewer permissions; role assignments are managed through
  the private `admin_emails` and `reviewer_emails` configuration.

Ticket ownership is tied to the OIDC subject claim, not a form field. Tickets
created before login was enabled have no owner and are visible only to
Reviewers and Admins. Never commit `.streamlit/secrets.toml` or share its
contents.

## Launch the app

```powershell
python -m streamlit run app.py
```

## Run tests

```powershell
python -m pytest -q
```

## Project structure

- `app.py`: Streamlit UI
- `nexusai/models.py`: Pydantic validation models
- `nexusai/storage.py`: SQLite persistence layer
- `nexusai/classifier.py`: AI/demo classification and deterministic policy rules
- `nexusai/workflow.py`: Submission and review orchestration
- `tests/`: Automated tests
