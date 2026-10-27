# NexusAI — Implementation Plan

## Delivery approach

Implement a small, testable functional application in sequential sprints. At the end of each sprint, run its relevant tests, create a sprint commit, and push that commit to the configured GitHub repository before beginning the next sprint. If a push fails, stop and resolve the repository/authentication issue rather than continuing to a later sprint.

The planning documents are created before implementation. The planning-only commit is pushed first so the specification and plan are versioned before the build begins.

## Sprint 0 — Project specification and plan

**Scope**

- Add `spec.md` with requirements, acceptance criteria, technical constraints, and out-of-scope items.
- Add `plan.md` with sprint boundaries, verification, and push gates.

**Done when**

- Both planning documents are present and aligned with the requested MVP.
- Planning-only changes are committed and pushed before implementation.

## Sprint 1 — Foundation, data model, and persistence

**Scope**

- Set up the Python package layout, dependencies, configuration, and local launch entry point.
- Define Pydantic request, classification, and workflow models.
- Implement SQLite initialization and parameterized ticket persistence/query operations.
- Add focused tests for validation and persistence.

**Done when**

- The application initializes its local database without manual schema steps.
- Valid tickets persist and reload; invalid input is rejected with clear errors.
- Sprint tests pass; commit and push before Sprint 2.

## Sprint 2 — Classification, policy, and workflow

**Scope**

- Add a configurable LLM API adapter and structured response validation.
- Add deterministic critical-incident rules independent of the model.
- Add a clearly labelled demo-mode classifier for missing API configuration.
- Implement action proposals, reviewer approval/edit/rejection, and status transitions.
- Test demo behavior, policy precedence, configured adapter errors, and workflow transitions.

**Done when**

- Requests receive category, urgency, confidence, team, rationale, and a proposed action.
- Critical signals always escalate to a human.
- Adapter failures are surfaced rather than presented as successful AI classifications.
- Sprint tests pass; commit and push before Sprint 3.

## Sprint 3 — Streamlit application and analytics

**Scope**

- Build the navy-themed sidebar and Dashboard, New Request, Ticket Queue, Approval Center, and Analytics pages.
- Connect all pages to the persistence and workflow layers.
- Add filters, review controls, summary metrics, breakdowns, and empty states.
- Ensure AI/demo mode is visible in the interface.

**Done when**

- A user can submit, inspect, review, approve/edit, and reject requests through the app.
- Workflow changes and analytics reflect persisted state.
- Sprint tests pass; commit and push before Sprint 4.

## Sprint 4 — End-to-end verification and handoff

**Scope**

- Add or complete automated coverage for critical policy, workflow, and analytics acceptance criteria.
- Run the complete test suite; fix regressions and usability defects within scope.
- Document installation, environment configuration, demo mode, testing, and exact launch commands.
- Perform a final clean-worktree/status check and push the verified sprint commit.

**Done when**

- The full test suite passes.
- The app can be launched with the documented commands without an API key.
- Each sprint is represented by a commit pushed in order to the requested GitHub repository.

## Sprint execution record

| Sprint | Commit | Push status | Verification |
|---|---|---|---|
| 0 — Specification and plan | `69e755b` | Pushed | Planning documents committed first |
| 1 — Foundation and persistence | `0760e01` | Pushed | Initial model and persistence suite passed |
| 2 — Classification and workflow | `e6b6747` | Pushed | Workflow, demo policy, and review tests passed |
| 3 — Streamlit and analytics | `e6b6747` | Pushed | Streamlit UI smoke test passed |
| 4 — Verification and handoff | `081b47d` | Pushed | 20 tests passed; provider integration documented |

## Post-MVP extension — OIDC authentication and RBAC

- Added Streamlit OIDC sign-in, email-based role assignment, requester ticket ownership, reviewer authorization, and legacy SQLite schema migration.
- Verification before push: full test suite and unauthenticated UI smoke test.
- Commit and push status: pending.
