<!--
Sync Impact Report
- Version change: 1.0.0 → 2.0.0
- Modified principle: III. Simplicity and YAGNI → III. Scoped Demo
  Infrastructure and YAGNI
- Modified sections: Technology & Architecture Constraints, Development
  Workflow
- Added sections: none
- Removed sections: none
- Rationale for MAJOR change: the prior NON-NEGOTIABLE prohibition on any
  database or external service is replaced with explicit approval for the
  process-local SQLite store and bounded liteLLM proxy already adopted by
  approved features. Durable infrastructure remains gated by a feature spec.
- Follow-up TODOs: none
-->

# Sentinel Access Constitution

## Core Principles

### I. API-First Backend Migration
The FastAPI backend MUST expose REST endpoints that map one-to-one to each
existing frontend view's data needs (Command Center KPIs/alerts, Activity
Explorer, Identity Profiles, Cloud Estate, Policies, Reports/Configuration,
dataset import). The frontend MUST be migrated to consume these endpoints
in place of local hardcoded fixtures — no view may retain hardcoded demo
data once its corresponding endpoint exists. Rationale: the project's
explicit goal is replacing a fully static, browser-only demo with a real
backend without changing what each screen shows or how it behaves.

### II. Preserve Existing UX and Data Shapes
The "Signal Room" visual design, interaction behavior, and response data
shapes MUST NOT change as a side effect of the backend migration. New
endpoints MUST return data compatible with the field names, types, and
structure already established in `server/data/synthetic-data.json` and the
existing component props, unless a change is explicitly requested.
Rationale: this is a backend-swap, not a redesign; unrelated UI churn adds
risk and review burden without serving the stated goal.

### III. Scoped Demo Infrastructure and YAGNI (NON-NEGOTIABLE)
The project MUST use the simplest infrastructure that satisfies an approved
feature specification. Process-local SQLite using Python's standard library
is approved for relational demo state and MUST remain seeded from bundled
synthetic fixtures. A separately operated liteLLM-compatible proxy is
approved only for explicitly specified AI features; every such dependency
MUST have bounded calls, validated outputs, and a usable non-AI fallback.
The project MUST NOT introduce a durable database server, ORM, migration
framework, authentication/authorization system, message broker, or other
managed infrastructure without a new specification that demonstrates why
the existing process-local approach is insufficient. Rationale: SQLite and
the bounded AI proxy now serve demonstrated product needs, while the gate on
additional infrastructure preserves the hackathon project's low setup cost
and small failure surface.

### IV. Contract Clarity Before Implementation
Every new endpoint MUST have its request/response shape (path, method,
params, JSON schema) specified in the feature spec/plan before
implementation begins. Frontend and backend work on a given view MUST
agree on the contract first so both sides can be built/verified
independently. Rationale: avoids drift between what the UI expects and
what the API returns, especially since persistence is in-memory and easy
to reshape carelessly.

### V. Demo-Safe Data Only
All seeded, generated, or sample data handled by the backend MUST remain
fictitious/synthetic, consistent with the existing "synthetic demo
telemetry" labeling in the product. No real credentials, personal data, or
production cloud data may be introduced through backend fixtures, dataset
import, or documentation examples. Rationale: preserves the product's
existing demo-safety guarantee described in `CONTEXT.md`.

## Technology & Architecture Constraints

- Backend: Python + FastAPI, run as a standalone service separate from the
  existing Express static-file server (or replacing it — decided at plan
  time), serving JSON over REST.
- Persistence: one process-local in-memory SQLite database accessed through
  the existing `app/db.py` serialization helpers and seeded from bundled
  synthetic fixtures. No durable database server, ORM, or migration
  framework without a separately approved feature specification.
- AI integration: the existing liteLLM-compatible proxy MAY be used by
  explicitly specified AI capabilities. Prompts MUST contain demo-safe data,
  outputs MUST be schema-validated before affecting application state, and a
  timeout/fallback path MUST keep core non-AI workflows usable.
- Auth: none. Endpoints are open, matching the current no-auth demo
  posture. Do not add API keys, sessions, or login flows unless a future
  amendment changes this principle.
- Frontend integration: React frontend calls the FastAPI backend via
  `axios` (already a dependency) or `fetch`; routing may use `wouter`
  (already a dependency) if navigation changes are needed.
- Seed data: `server/data/synthetic-data.json` and feature-specific files
  under `datasets/` are the sources of truth for initial/demo data. Expected
  test labels MUST be kept separate from runtime model inputs.

## Development Workflow

- Follow the Spec-Driven Development flow for this migration:
  `/speckit-specify` → (`/speckit-clarify` if needed) → `/speckit-plan` →
  `/speckit-tasks` → (`/speckit-analyze`/`/speckit-checklist` as needed) →
  `/speckit-implement`.
- Each view's backend migration (Command Center, Activity Explorer,
  Identity Profiles, Cloud Estate, Policies, Reports/Configuration, dataset
  import) MUST be traceable to explicit tasks before implementation.
- Features that add or change stored relationships, scoring rules, or AI
  authority boundaries MUST define their data model, calculation semantics,
  failure behavior, and REST contracts before task generation.
- Changes MUST be verified by running both the FastAPI backend and the
  Vite frontend together and confirming the affected view renders
  real API data with the same behavior as before the migration.

## Governance

This constitution supersedes ad-hoc practices for this project. Amendments
require: (1) a documented rationale for the change, (2) an updated version
number following semantic versioning (MAJOR for incompatible
principle/governance removals or redefinitions, MINOR for new
principles/sections or materially expanded guidance, PATCH for wording/
clarification only), and (3) an updated `Last Amended` date. All specs,
plans, and task lists produced via Spec Kit commands MUST comply with
these principles; any deviation must be explicitly justified in the
relevant plan's Complexity Tracking section.

**Version**: 2.0.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-18
