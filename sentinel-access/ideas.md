# Sentinel Access — Design Directions

## Approach 1
**Theme Name:** Signal Room

**Very Brief Intro:** A high-focus security operations environment with deep ink surfaces, electric signals, and intelligence-dossier typography. It makes complex activity feel calm, legible, and actionable.

**Probability:** 0.07

## Approach 2
**Theme Name:** Compliance Ledger

**Very Brief Intro:** An editorial, paper-forward governance console that feels like an internal audit briefing. Warm neutrals and precise tabular rhythm foreground evidence over spectacle.

**Probability:** 0.04

## Approach 3
**Theme Name:** Incident Atlas

**Very Brief Intro:** A luminous cartographic interface where every access event is a navigable point in a broader behavioral landscape. It privileges spatial thinking and interconnected narratives.

**Probability:** 0.09

# Chosen Direction: Signal Room

## Design Movement
**Contemporary intelligence-console design** with editorial restraint: inspired by high-stakes command rooms, technical field guides, and precision instrumentation rather than consumer analytics dashboards.

## Core Principles
1. **Signal before decoration:** Severity, behavioral deviation, and recommended action must be visually obvious before secondary metadata.
2. **Evidence in layers:** Start with a concise operational overview, then reveal causal detail and raw events through interaction.
3. **Measured tension:** Dark graphite surfaces and sparse warning colors create focus without resorting to a neon cyberpunk aesthetic.
4. **Human-readable intelligence:** Numbers are paired with plain-language reasoning so an analyst can explain a finding in seconds.

## Color Philosophy
The interface uses deep graphite and blue-black as a quiet operational field, with a proprietary oxidized cyan, **Signal Teal**, as the steady-state identity color. Amber is reserved for elevated attention, while a saturated vermilion marks high-confidence risk only. Pale mineral text is used generously to keep dense data readable.

## Layout Paradigm
An **analyst workbench** replaces a centered card grid. A fixed evidence rail anchors navigation and contextual status; the main area reads as a horizontally layered investigation canvas with a command strip, metric line, activity instrument panel, and alert queue. The selected alert opens as a slide-over evidence dossier rather than a separate dead-end page.

## Signature Elements
1. A thin vertical **signal rail** with a pulsing live marker and compact environment status.
2. A **risk trace** motif: compact segmented score bars and tiny variance ticks used across users, events, and explanations.
3. **Annotation chips** that state an anomaly cause in natural language, such as “New ASN” or “Privilege pivot.”

## Interaction Philosophy
The product should make triage feel deliberate. Clicking an alert opens its evidence dossier; filters recalculate visible records; a simulation control injects a clearly labeled synthetic abnormal event to demonstrate detection. Every interaction confirms its outcome with restrained motion and readable state changes.

## Animation
Cards and queue rows enter with a 30–60 ms stagger using opacity and a 6 px upward transform. Dossiers slide in from the right in 220 ms with `cubic-bezier(0.23, 1, 0.32, 1)`. The live marker has a soft 1.8-second opacity pulse only when motion is permitted. Buttons compress to 0.97 scale on press; routine filter changes avoid decorative animation and remain immediate.

## Typography System
**Space Grotesk** supplies the display and numerical hierarchy; its geometric structure makes metric headlines crisp. **IBM Plex Mono** carries timestamps, cloud resources, geographies, and evidence labels, creating an instrument-panel contrast. Headings are compact and weighty; body copy is calm and slightly expanded; numbers use tabular figures.

## Brand Essence
**Sentinel Access turns noisy cloud-access activity into explainable, prioritized security decisions for lean security teams.**

Personality adjectives: **vigilant, composed, exacting.**

## Brand Voice
Headlines are direct and evidence-led. CTAs use operational verbs, while microcopy explains what changed and why.

Examples:

> “Three access patterns need analyst judgment.”

> “Open the evidence trail.”

## Wordmark & Logo
The mark is a **split aperture within a shield silhouette**: two offset arcs create an “S” through negative space while evoking a monitored access gate. The wordmark uses a custom-spaced Space Grotesk treatment with a small teal signal point, never a default system wordmark.

## Signature Brand Color
**Signal Teal — #39E0C5**

## Style Decisions
- Maintain dark-on-dark hierarchy with broad negative space; do not introduce rainbow gradients or glossy neon treatments.
- Keep dense operational data on low-contrast panels and reserve bright color for meaning, not decoration.
- Treat all records as clearly labeled **synthetic demo telemetry** until a live integration is implemented.
- Make the **signal rail** a structural operational spine with the environment state, live marker, brand, and evidence navigation visible at all times on desktop.
- Use the split-aperture shield with a custom-spaced Sentinel Access wordmark as a primary brand anchor, not a small afterthought.
- Render risk as proprietary **segmented traces with variance ticks** rather than generic continuous progress bars; keep secondary state colors mineral and restrained.
