# NexusAI — Intake Resolution Workflow

NexusAI is a beginner-friendly Streamlit application that captures intake requests, classifies them, applies deterministic critical-incident rules, stores tickets in SQLite, and gives reviewers a queue for approval and edits.

## Features

- Intake form for requests and personnel metadata
- Demo AI mode when no API key is configured
- Structured classification into IT Support, Security, HR, Customer Support, and Vendor Onboarding
- Urgency, confidence, assigned team, and action recommendation
- Deterministic critical incident policy outside the LLM
- Human review for critical incidents, High/Critical urgency, or human-escalation recommendations; routine tickets are auto-processed
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

## Run a local AI model with Ollama

Ollama runs the model on your computer, so requests are not sent to a cloud AI
provider and there is no per-request API charge. Install Ollama, then open a
terminal and download a small model:

```powershell
ollama pull qwen2.5:3b
```

In the same terminal where you will run NexusAI, configure Ollama's
OpenAI-compatible endpoint and start the app:

```powershell
$env:NEXUSAI_LLM_API_KEY = "ollama"
$env:NEXUSAI_LLM_BASE_URL = "http://localhost:11434/v1/chat/completions"
$env:NEXUSAI_LLM_MODEL = "qwen2.5:3b"
python -m streamlit run app.py
```

The `ollama` value is a local compatibility placeholder, not a personal API
key. Keep Ollama running while you use the app. The first model download needs
an internet connection and several gigabytes of disk space.

To keep Ollama settings across terminal sessions, add this section to your
Git-ignored `.streamlit/secrets.toml` instead of setting environment variables:

```toml
[llm]
api_key = "ollama"
base_url = "http://localhost:11434/v1/chat/completions"
model = "qwen2.5:3b"
```

Environment variables take precedence over values in the local secrets file.

## Configure a cloud LLM provider

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

For an OpenAI-compatible cloud provider, set `NEXUSAI_LLM_BASE_URL` to that
provider's Chat Completions endpoint and set `NEXUSAI_LLM_MODEL` to a model it
supports. When no API key is configured, the app clearly indicates demo mode.
If a configured provider request fails, the app reports the error and does not
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

Routine tickets are marked `auto_processed` and do not enter the Approval
Center. Critical incidents, High/Critical urgency tickets, and recommendations
to escalate to a human remain pending review. Auto-processing accepts the
workflow recommendation in this local app; it does not send messages or perform
actions in external systems.

## Deploy to Render's free tier

The repository includes `render.yaml` for a free Render Web Service. Hosted
SQLite storage is temporary on Render's free tier: Restarts and redeployments
can remove tickets. This deployment is for validation, not durable production
use.

Before deployment:

1. Connect the GitHub repository in Render and select `render.yaml` for Blueprint deployment.
2. Choose HTTPS as the deployed URL and enter it as
   `https://YOUR-SERVICE.onrender.com/oauth2callback` in Google OAuth.
3. Enter the Google OAuth Client ID and secret in Render's environment settings.
4. Set `NEXUSAI_ADMIN_EMAILS` to the administrator's Google email. Use comma-separated values for multiple reviewers.
5. Leave the LLM variables unset for demo-mode deployment. Do not copy local
   Ollama settings to Render; Ollama on your PC is not reachable from the host.

Render restarts free services, and they can sleep while inactive. Test with
non-sensitive sample requests and do not use temporary hosted data for real
records.

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
