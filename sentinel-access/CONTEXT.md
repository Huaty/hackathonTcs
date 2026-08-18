# Sentinel Access — Project Context

## What this is

Sentinel Access is a security-operations concept product (design direction:
"Signal Room") that turns noisy cloud-access activity into explainable,
prioritized security decisions for lean security teams.

It currently ships as a **static, browser-only demo/prototype**:
- No real backend, authentication, or live cloud integration.
- All data is synthetic/generated client-side.
- No router library — the app is a single page (`Home.tsx`) that switches
  between internal "workspace" views using local React state plus
  `window.location.hash` (e.g. `#activity`, `#identities`).

## Tech stack

- React + TypeScript, Vite build (`client/`)
- shadcn/ui (Radix-based) component library (`client/src/components/ui/`)
- Recharts for charts
- `sonner` for toast notifications
- Server directory (`server/`, `dist/index.js`) exists but the current
  feature set does not depend on a real backend — most actions are
  simulated via local state + toast feedback.

## Views / Screens

| View key | Nav label | Description |
|---|---|---|
| `command` (default, `/`) | Command Center | KPI banner (activities checked, needs-attention count, most urgent case, avg review time), dataset importer, behavioral-variance chart (access volume vs. anomalies over the day), service-risk bar chart, sortable/filterable investigation queue table, and a "model rationale" panel. Clicking a queue row opens an evidence-dossier slide-over (explanation, evidence chips, Start investigation / Escalate). |
| `activity` (`#activity`) | Activity Explorer | Searchable/filterable list of access events ("Needs attention" / "Normal") with plain-language explanations and a "Record a check" action. Shows imported data instead of synthetic data if a dataset was uploaded. |
| `identities` (`#identities`) | Identity Profiles | Card grid of user/service identities with risk scores; detail panel shows "what looks unusual" vs. "what is normally expected," an activity timeline, and "Start a profile review." |
| `estate` (`#estate`) | Cloud Estate | List of connected cloud/identity sources (AWS IAM, AWS Secrets Manager, Azure AD, GitHub Enterprise, GCP Audit Logs) with connection status, event volume, and health. |
| `policies` | Policies | List of detection rules (e.g. new-country sign-in, sensitive permission changes, dormant account activity) with on/off toggles and "Add a simple rule." |
| `reports` (`#reports`) | Reports | Three report templates (daily summary, access activity export, identity review pack) with per-card "Prepare report" and a global "Export activity CSV." |
| `settings` (`#settings`) | Configuration | Notification / plain-language-explanation preference toggles, "Save preferences," and static info about the demo data environment. |

`client/src/pages/NotFound.tsx` exists but isn't wired into any route table
since there is no router.

## Cross-cutting features

- **Theming**: `ThemeContext.tsx` provides `dark` class toggling on `<html>`,
  with optional `localStorage` persistence when `switchable` is true. Currently
  hard-set to dark, non-switchable.
- **Error handling**: top-level `ErrorBoundary.tsx`.
- **Toast notifications**: confirm most simulated actions (dataset loaded,
  investigation started, rule added, report prepared, settings saved, etc.).
- **Client-side dataset import** (`DatasetImporter.tsx`): CSV/JSON upload,
  parsed entirely in-browser (no server upload), capped at 10,000 records,
  repopulates Activity Explorer for the session only (cleared on refresh).
- **Anomaly simulation**: "Simulate anomaly" button injects a synthetic
  high-severity alert into the queue live, to demo the detection workflow.
- **CSV export**: downloads currently filtered findings/activity.
- **Notification bell / user avatar menu**: demo-only, no real auth.
- **Charts**: Recharts `AreaChart`/`LineChart` combo (volume vs. anomalies)
  and horizontal `BarChart` (service risk concentration).
- **Segmented Trace**: custom segmented progress-bar visualization used for
  risk/confidence scores, per the "Signal Room" design language.

## Reusable UI library

Full shadcn/ui-style component set available under `client/src/components/ui/`:
accordion, alert, alert-dialog, aspect-ratio, avatar, badge, breadcrumb,
button/button-group, calendar, card, carousel, chart, checkbox, collapsible,
command, context-menu, dialog, drawer, dropdown-menu, empty, field, form,
hover-card, input/input-group/input-otp, item, kbd, label, menubar,
navigation-menu, pagination, popover, progress, radio-group, resizable,
scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner
(toast), spinner, switch, table, tabs, textarea, toggle/toggle-group, tooltip.

## Other notable components

- `WorkspaceViews.tsx` — houses the secondary workspace pages (Activity
  Explorer, Identity Profiles, Cloud Estate, Policies, Reports, Configuration).
- `DatasetImporter.tsx` — CSV/JSON upload feature described above.
- `ManusDialog.tsx` — a "Login with Manus" modal; **currently unused**
  anywhere in the app (leftover scaffold/template code).
- `Map.tsx` — a Google Maps integration wrapper (markers, places,
  geocoding); **currently unused** anywhere in the app (leftover scaffold
  code).

## Hooks (`client/src/hooks/`)

- `useMobile.tsx` — media-query/breakpoint hook for responsive/mobile
  detection (used for mobile nav behavior).
- `useComposition.ts` — IME composition-state handling for text inputs.
- `usePersistFn.ts` — stable persisted function reference across renders.

## Known cleanup candidates

- `ManusDialog.tsx` and `Map.tsx` are unused boilerplate and could be
  removed if not needed for future work.

## Build history (from `todo.md`)

Investigation-flow fix → plain-language pass over the dashboard →
"Expanded Workspace" addition (Activity Explorer, Identity Profiles, Cloud
Estate, Policies/Reports/Configuration) → interaction-completion audit →
client-side dataset import feature.
