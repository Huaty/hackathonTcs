import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT = "C:/Users/GENAISINCBPUSR8/hackathonTcs/Sentinel_Access_Project_Deck.pptx";
const BUILD = "C:/Users/GENAISINCBPUSR8/hackathonTcs/pptx_build_sentinel_20260818";
const RENDERS = path.join(BUILD, "renders");

const C = {
  canvas: "#FFFFFF",
  ink: "#0B1220",
  muted: "#596574",
  panel: "#EDF1F3",
  rule: "#B8BCC4",
  teal: "#39E0C5",
  tealDark: "#0B7D70",
  tealPale: "#D9F8F2",
  amber: "#E7A93D",
};
const FONT = "Arial";
const W = 1280;
const H = 720;
const M = 56;

function addText(slide, name, text, x, y, w, h, opts = {}) {
  const s = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left: x, top: y, width: w, height: h },
    fill: opts.fill ?? "none",
    line: opts.line ?? { style: "solid", fill: "none", width: 0 },
  });
  s.text = text;
  s.text.style = {
    fontSize: opts.fontSize ?? 22,
    typeface: FONT,
    color: opts.color ?? C.ink,
    bold: opts.bold ?? false,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "top",
    autoFit: "none",
  };
  return s;
}

function addBox(slide, name, x, y, w, h, opts = {}) {
  return slide.shapes.add({
    geometry: opts.geometry ?? "rect",
    name,
    position: { left: x, top: y, width: w, height: h },
    fill: opts.fill ?? C.panel,
    line: opts.line ?? { style: "solid", fill: C.rule, width: 1 },
  });
}

function addRule(slide, name, x, y, w, color = C.rule, width = 1, dashed = false) {
  return slide.shapes.add({
    geometry: "straightConnector1",
    name,
    position: { left: x, top: y, width: w, height: 0 },
    fill: "none",
    line: { style: dashed ? "dashed" : "solid", fill: color, width },
  });
}

function addVRule(slide, name, x, y, h, color = C.rule, width = 1, dashed = false) {
  return slide.shapes.add({
    geometry: "straightConnector1",
    name,
    position: { left: x, top: y, width: 0, height: h },
    fill: "none",
    line: { style: dashed ? "dashed" : "solid", fill: color, width },
  });
}

function header(slide, title, n, eyebrow = "SENTINEL ACCESS") {
  addText(slide, `eyebrow-${n}`, eyebrow, M, 34, 300, 26, { fontSize: 16, bold: true, color: C.tealDark });
  addText(slide, `title-${n}`, title, M, 76, 1168, 66, { fontSize: 48, bold: true });
  addRule(slide, `header-rule-${n}`, M, 156, 1168, C.ink, 1);
  addText(slide, `page-${n}`, String(n).padStart(2, "0"), 1184, 670, 40, 20, { fontSize: 14, color: C.muted, align: "right" });
}

function note(slide, sources, extra = "") {
  const lines = [extra, "[Sources]", ...sources.map((s) => `- ${s}`)].filter(Boolean);
  slide.speakerNotes.textFrame.setText(lines.join("\n"));
  slide.speakerNotes.setVisible(false);
}

function statusLabel(slide, name, text, x, y, w, current = true) {
  addText(slide, name, text, x, y, w, 28, {
    fontSize: 15,
    bold: true,
    color: current ? C.tealDark : C.muted,
    align: "left",
  });
}

function node(slide, name, x, y, w, h, title, body, planned = false) {
  addBox(slide, `${name}-box`, x, y, w, h, {
    fill: planned ? C.canvas : C.panel,
    line: { style: planned ? "dashed" : "solid", fill: planned ? C.tealDark : C.rule, width: planned ? 2 : 1 },
  });
  addText(slide, `${name}-title`, title, x + 22, y + 20, w - 44, 40, { fontSize: 28, bold: true });
  addText(slide, `${name}-body`, body, x + 22, y + 72, w - 44, h - 88, { fontSize: 21.5, color: C.muted });
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

const deck = Presentation.create({ slideSize: { width: W, height: H } });

// 1 — Cover: sparse Codex Grid-inspired composition.
{
  const s = deck.slides.add();
  s.background.fill = C.canvas;
  addText(s, "cover-eyebrow", "HACKATHON PROJECT · CLOUD ACCESS SECURITY", 56, 42, 560, 28, { fontSize: 16, bold: true, color: C.tealDark });
  addBox(s, "cover-signal", 56, 136, 18, 336, { fill: C.teal, line: { style: "solid", fill: C.teal, width: 0 } });
  addText(s, "cover-title", "Sentinel\nAccess", 102, 126, 650, 254, { fontSize: 82, bold: true, valign: "bottom" });
  addText(s, "cover-subtitle", "Explainable cloud-access decisions\nfor lean security teams", 102, 414, 670, 106, { fontSize: 32, color: C.muted });
  addRule(s, "cover-rule", 820, 126, 356, C.ink, 1);
  addText(s, "cover-principle-1", "SIGNAL", 820, 158, 356, 32, { fontSize: 16, bold: true, color: C.tealDark });
  addText(s, "cover-principle-2", "EVIDENCE", 820, 270, 356, 32, { fontSize: 16, bold: true, color: C.tealDark });
  addText(s, "cover-principle-3", "ACTION", 820, 382, 356, 32, { fontSize: 16, bold: true, color: C.tealDark });
  addText(s, "cover-description", "Noisy activity is reduced into prioritized findings, plain-language rationale, and an auditable path to action.", 820, 450, 356, 116, { fontSize: 22, color: C.muted });
  note(s, [
    "sentinel-access/CONTEXT.md",
    "sentinel-access/ideas.md",
  ]);
}

// 2 — Problem statement.
{
  const s = deck.slides.add();
  s.background.fill = C.canvas;
  header(s, "Cloud access produces alerts—not decisions", 2, "PROBLEM STATEMENT");
  addText(s, "problem-thesis", "Security teams have signals.\nWhat they need is\ndecision-ready context.", 56, 206, 560, 190, { fontSize: 43, bold: true });
  addText(s, "problem-support", "A lean team must connect identity, baseline behavior, cloud action, and business impact before it can explain what matters and act confidently.", 56, 420, 520, 136, { fontSize: 24, color: C.muted });
  const ys = [206, 342, 478];
  const nums = ["01", "02", "03"];
  const titles = ["Fragmented telemetry", "Opaque prioritization", "Slow investigation"];
  const bodies = [
    "Cloud and identity events arrive in different shapes and lose their lineage.",
    "A score without matched evidence is difficult to trust, defend, or tune.",
    "Analysts jump between filters, raw logs, and reports before choosing an action.",
  ];
  for (let i = 0; i < 3; i++) {
    addRule(s, `problem-rule-${i}`, 674, ys[i] - 18, 550, i === 0 ? C.teal : C.rule, i === 0 ? 4 : 1);
    addText(s, `problem-num-${i}`, nums[i], 674, ys[i], 58, 34, { fontSize: 20, bold: true, color: C.tealDark });
    addText(s, `problem-title-${i}`, titles[i], 752, ys[i], 420, 38, { fontSize: 28, bold: true });
    addText(s, `problem-body-${i}`, bodies[i], 752, ys[i] + 46, 440, 62, { fontSize: 21.5, color: C.muted });
  }
  note(s, ["sentinel-access/CONTEXT.md", "specs/004-contextual-risk-scoring/spec.md"]);
}

// 3 — Solution flow. Lines first so nodes sit above them.
{
  const s = deck.slides.add();
  s.background.fill = C.canvas;
  header(s, "Our approach makes every decision traceable", 3, "APPROACH & SOLUTION ARCHITECTURE");
  const xs = [56, 354, 652, 950];
  for (let i = 0; i < 3; i++) {
    addRule(s, `solution-link-${i}`, xs[i] + 246, 352, 52, C.tealDark, 3);
    addBox(s, `solution-chevron-${i}`, xs[i] + 264, 342, 20, 20, { geometry: "chevron", fill: C.teal, line: { style: "solid", fill: C.teal, width: 0 } });
  }
  node(s, "solution-1", xs[0], 236, 246, 232, "1 · Ingest", "CSV/JSON import today; provider-native cloud logs next.");
  node(s, "solution-2", xs[1], 236, 246, 232, "2 · Context", "SQLite-backed activity, identities, evidence, and baselines.");
  node(s, "solution-3", xs[2], 236, 246, 232, "3 · Decide", "Transparent rules plus a bounded AI contextual adjustment.", true);
  node(s, "solution-4", xs[3], 236, 246, 232, "4 · Act", "Command Center, evidence dossier, copilot, and reports.");
  statusLabel(s, "solution-mvp", "SOLID = MVP CAPABILITY", 56, 500, 260, true);
  statusLabel(s, "solution-roadmap", "DASHED = DESIGNED EXPANSION", 430, 500, 310, false);
  addBox(s, "solution-outcome-box", 56, 558, 1140, 66, { fill: C.tealPale, line: { style: "solid", fill: C.teal, width: 1 } });
  addText(s, "solution-outcome", "Outcome: analysts see what happened, why it matters, the evidence, and the next action.", 82, 578, 1088, 30, { fontSize: 23, bold: true, color: C.tealDark, align: "center" });
  note(s, [
    "sentinel-access/backend/app/routers/datasets.py",
    "sentinel-access/backend/app/routers/command_center.py",
    "specs/004-contextual-risk-scoring/spec.md",
    "specs/005-cloud-log-ingestion/plan.md",
  ]);
}

// 4 — High-level technical architecture.
{
  const s = deck.slides.add();
  s.background.fill = C.canvas;
  header(s, "The MVP is modular from interface to intelligence", 4, "HIGH-LEVEL TECHNICAL ARCHITECTURE");
  const colX = [56, 334, 642, 936];
  const colW = [238, 268, 254, 288];
  for (let i = 0; i < 3; i++) {
    addRule(s, `tech-link-${i}`, colX[i] + colW[i], 344, colX[i + 1] - (colX[i] + colW[i]), C.tealDark, 2);
    addBox(s, `tech-chevron-${i}`, colX[i + 1] - 24, 334, 18, 18, { geometry: "chevron", fill: C.teal, line: { style: "solid", fill: C.teal, width: 0 } });
  }
  addVRule(s, "tech-planned-link", 174, 438, 46, C.tealDark, 2, true);

  addText(s, "tech-col-1-title", "TELEMETRY", colX[0], 204, colW[0], 30, { fontSize: 16, bold: true, color: C.tealDark });
  addBox(s, "tech-upload", colX[0], 250, colW[0], 188, { fill: C.panel });
  addText(s, "tech-upload-title", "Synthetic CSV / JSON", colX[0] + 20, 272, colW[0] - 40, 66, { fontSize: 27, bold: true });
  addText(s, "tech-upload-body", "Upload boundary\n≤10,000 records", colX[0] + 20, 350, colW[0] - 40, 62, { fontSize: 21.5, color: C.muted });
  addBox(s, "tech-cloud", colX[0], 484, colW[0], 132, { fill: C.canvas, line: { style: "dashed", fill: C.tealDark, width: 2 } });
  addText(s, "tech-cloud-text", "AWS · Azure · GCP\nnormalizers\nplanned", colX[0] + 18, 504, colW[0] - 36, 94, { fontSize: 21.5, bold: true });

  addText(s, "tech-col-2-title", "API & STORAGE", colX[1], 204, colW[1], 30, { fontSize: 16, bold: true, color: C.tealDark });
  addBox(s, "tech-fastapi", colX[1], 250, colW[1], 188, { fill: C.panel });
  addText(s, "tech-fastapi-title", "FastAPI", colX[1] + 20, 272, colW[1] - 40, 42, { fontSize: 28, bold: true });
  addText(s, "tech-fastapi-body", "REST routers for data, investigations, identities, policy, reports, and copilot", colX[1] + 20, 326, colW[1] - 40, 94, { fontSize: 21.5, color: C.muted });
  addBox(s, "tech-sqlite", colX[1], 466, colW[1], 150, { fill: C.canvas, line: { style: "solid", fill: C.rule, width: 1 } });
  addText(s, "tech-sqlite-title", "Store + SQLite", colX[1] + 20, 480, colW[1] - 40, 42, { fontSize: 27, bold: true });
  addText(s, "tech-sqlite-body", "Findings · activity\nIdentities · policies\nReports · AI cache", colX[1] + 20, 528, colW[1] - 40, 80, { fontSize: 21.5, color: C.muted });

  addText(s, "tech-col-3-title", "AI LAYER", colX[2], 204, colW[2], 30, { fontSize: 16, bold: true, color: C.tealDark });
  addBox(s, "tech-litellm", colX[2], 250, colW[2], 188, { fill: C.tealPale, line: { style: "solid", fill: C.teal, width: 1 } });
  addText(s, "tech-litellm-title", "liteLLM", colX[2] + 20, 272, colW[2] - 40, 42, { fontSize: 27, bold: true });
  addText(s, "tech-litellm-body", "OpenAI-compatible chat path\n15-second timeout", colX[2] + 20, 336, colW[2] - 40, 62, { fontSize: 21.5, color: C.muted });
  addBox(s, "tech-ai-features", colX[2], 466, colW[2], 150, { fill: C.canvas, line: { style: "solid", fill: C.rule, width: 1 } });
  addText(s, "tech-ai-features-title", "AI capabilities", colX[2] + 20, 480, colW[2] - 40, 42, { fontSize: 27, bold: true });
  addText(s, "tech-ai-features-body", "Explanations\nCopilot tool calls\nReport narratives", colX[2] + 20, 528, colW[2] - 40, 80, { fontSize: 21.5, color: C.muted });

  addText(s, "tech-col-4-title", "ANALYST EXPERIENCE", colX[3], 204, colW[3], 30, { fontSize: 16, bold: true, color: C.tealDark });
  addBox(s, "tech-react", colX[3], 250, colW[3], 366, { fill: C.ink, line: { style: "solid", fill: C.ink, width: 1 } });
  addText(s, "tech-react-title", "React + Vite", colX[3] + 24, 274, colW[3] - 48, 44, { fontSize: 30, bold: true, color: C.canvas });
  addText(s, "tech-react-body", "Command Center\nActivity Explorer\nIdentity Profiles\nCloud Estate\nPolicies & Reports", colX[3] + 24, 344, colW[3] - 48, 210, { fontSize: 23, color: C.canvas });
  addText(s, "tech-react-footer", "Evidence dossier + Ask Sentinel", colX[3] + 24, 566, colW[3] - 48, 38, { fontSize: 20, bold: true, color: C.teal });
  note(s, [
    "sentinel-access/package.json",
    "sentinel-access/backend/app/main.py",
    "sentinel-access/backend/app/db.py",
    "sentinel-access/backend/app/ai_client.py",
    "sentinel-access/client/src/lib/api.ts",
  ]);
}

// 5 — AI components.
{
  const s = deck.slides.add();
  s.background.fill = C.canvas;
  header(s, "AI adds context without owning the controls", 5, "AI / ML COMPONENTS");
  const xs = [56, 440, 824];
  const titles = ["Finding explanations", "Ask Sentinel copilot", "Report narratives"];
  const bodies = [
    "Generates 2–3 plain-language sentences from a finding’s evidence and baseline; caches the result; falls back safely.",
    "Uses bounded tool calling to filter current findings, activity, and identities; returns the underlying records with the answer.",
    "Drafts a 3–5 sentence security narrative from current findings and event counts without inventing new data.",
  ];
  const tags = ["IMPLEMENTED", "IMPLEMENTED", "IMPLEMENTED"];
  for (let i = 0; i < 3; i++) {
    addRule(s, `ai-top-rule-${i}`, xs[i], 220, 344, i === 1 ? C.teal : C.ink, i === 1 ? 5 : 1);
    addText(s, `ai-tag-${i}`, tags[i], xs[i], 242, 180, 24, { fontSize: 15, bold: true, color: C.tealDark });
    addText(s, `ai-title-${i}`, titles[i], xs[i], 288, 330, 72, { fontSize: 31, bold: true });
    addText(s, `ai-body-${i}`, bodies[i], xs[i], 372, 330, 150, { fontSize: 22, color: C.muted });
  }
  addBox(s, "ai-guardrail", 56, 556, 1112, 82, { fill: C.ink, line: { style: "solid", fill: C.ink, width: 0 } });
  addText(s, "ai-guardrail-title", "DESIGNED NEXT · POLICY-FIRST RISK", 82, 574, 330, 24, { fontSize: 15, bold: true, color: C.teal });
  addText(s, "ai-guardrail-formula", "Final score = deterministic policy score + validated AI adjustment, with severity floors applied last.", 412, 571, 722, 48, { fontSize: 23, bold: true, color: C.canvas, align: "right" });
  note(s, [
    "sentinel-access/backend/app/routers/command_center.py",
    "sentinel-access/backend/app/routers/copilot.py",
    "sentinel-access/backend/app/routers/reports.py",
    "specs/004-contextual-risk-scoring/spec.md",
  ]);
}

// 6 — Innovation.
{
  const s = deck.slides.add();
  s.background.fill = C.canvas;
  header(s, "Innovation connects evidence directly to action", 6, "INNOVATION & CREATIVITY");
  const cells = [
    { x: 56, y: 218, n: "01", t: "Evidence before alarm", b: "The dossier starts with the causal story, evidence chips, expected baseline, and a recommended action." },
    { x: 650, y: 218, n: "02", t: "Constrained intelligence", b: "AI explains and searches; deterministic controls, validation, fallbacks, and evidence IDs protect the decision." },
    { x: 56, y: 432, n: "03", t: "Signal Room language", b: "A calm intelligence-console design uses Signal Teal, segmented risk traces, and operational verbs—not cyberpunk noise." },
    { x: 650, y: 432, n: "04", t: "Demo-safe realism", b: "Synthetic telemetry, anomaly simulation, provider-shaped fixtures, and separate test oracles enable a credible demonstration." },
  ];
  for (const c of cells) {
    addRule(s, `innov-rule-${c.n}`, c.x, c.y, 520, c.n === "01" ? C.teal : C.rule, c.n === "01" ? 4 : 1);
    addText(s, `innov-num-${c.n}`, c.n, c.x, c.y + 22, 60, 36, { fontSize: 20, bold: true, color: C.tealDark });
    addText(s, `innov-title-${c.n}`, c.t, c.x + 78, c.y + 20, 430, 42, { fontSize: 30, bold: true });
    addText(s, `innov-body-${c.n}`, c.b, c.x + 78, c.y + 76, 430, 100, { fontSize: 21.5, color: C.muted });
  }
  note(s, [
    "sentinel-access/ideas.md",
    "sentinel-access/CONTEXT.md",
    "specs/004-contextual-risk-scoring/spec.md",
    "specs/005-cloud-log-ingestion/spec.md",
  ]);
}

// 7 — Scalability timeline. Rules and dots precede milestone copy.
{
  const s = deck.slides.add();
  s.background.fill = C.canvas;
  header(s, "Scale by replacing adapters—not the workflow", 7, "SCALABILITY FOR FUTURE EXPANSION");
  addRule(s, "scale-line", 104, 340, 1030, C.ink, 2);
  const xs = [116, 486, 856];
  for (let i = 0; i < 3; i++) {
    addBox(s, `scale-dot-${i}`, xs[i], 330, 20, 20, { geometry: "ellipse", fill: i === 0 ? C.teal : C.ink, line: { style: "solid", fill: i === 0 ? C.teal : C.ink, width: 0 } });
  }
  statusLabel(s, "scale-now-label", "NOW · HACKATHON MVP", 104, 250, 300, true);
  statusLabel(s, "scale-next-label", "NEXT · TRUSTED DATA", 474, 250, 300, false);
  statusLabel(s, "scale-prod-label", "SCALE · PRODUCTION", 844, 250, 300, false);
  addText(s, "scale-now-title", "Single-process foundation", 104, 384, 300, 70, { fontSize: 30, bold: true });
  addText(s, "scale-now-body", "React/Vite + FastAPI\nSQLite-backed store\nliteLLM AI features", 104, 468, 300, 126, { fontSize: 22, color: C.muted });
  addText(s, "scale-next-title", "Raw-first multi-cloud", 474, 384, 300, 70, { fontSize: 30, bold: true });
  addText(s, "scale-next-body", "AWS, Azure, GCP adapters\nImmutable raw archive\nVersioned normalization + replay", 474, 468, 310, 126, { fontSize: 22, color: C.muted });
  addText(s, "scale-prod-title", "Durable operating model", 844, 384, 330, 70, { fontSize: 30, bold: true });
  addText(s, "scale-prod-body", "Object storage + workers\nDurable database\nAuth, tenancy, retention, observability", 844, 468, 330, 126, { fontSize: 22, color: C.muted });
  addText(s, "scale-principle", "Stable contracts preserve the same evidence dossier, policy trace, and analyst experience as infrastructure evolves.", 104, 618, 1050, 36, { fontSize: 21.5, bold: true, color: C.tealDark, align: "center" });
  note(s, [
    "specs/005-cloud-log-ingestion/plan.md",
    "specs/004-contextual-risk-scoring/plan.md",
    "specs/003-sqlite-storage/plan.md",
  ]);
}

// 8 — Decision-oriented close.
{
  const s = deck.slides.add();
  s.background.fill = C.canvas;
  addText(s, "close-eyebrow", "WHY SENTINEL ACCESS", 56, 42, 420, 28, { fontSize: 16, bold: true, color: C.tealDark });
  addText(s, "close-title", "From noisy access logs\nto explainable action.", 56, 126, 800, 202, { fontSize: 67, bold: true, valign: "bottom" });
  addRule(s, "close-main-rule", 56, 368, 1168, C.ink, 1);
  const items = [
    ["BUILT", "A working analyst experience with FastAPI, SQLite, AI explanations, copilot search, and narrative reports."],
    ["TRUSTED", "A policy-first risk design that keeps AI bounded, validated, evidence-grounded, and fail-safe."],
    ["EXTENSIBLE", "A raw-first three-cloud ingestion path that can grow behind stable contracts and adapter boundaries."],
  ];
  const ys = [410, 492, 574];
  for (let i = 0; i < items.length; i++) {
    addText(s, `close-tag-${i}`, items[i][0], 56, ys[i], 170, 30, { fontSize: 16, bold: true, color: C.tealDark });
    addText(s, `close-copy-${i}`, items[i][1], 242, ys[i] - 2, 930, 54, { fontSize: 22.5, color: C.muted });
  }
  addBox(s, "close-accent", 1058, 88, 166, 166, { fill: C.teal, line: { style: "solid", fill: C.teal, width: 0 } });
  addText(s, "close-accent-text", "SIGNAL\n→\nDECISION", 1078, 112, 126, 122, { fontSize: 22, bold: true, color: C.ink, align: "center", valign: "middle" });
  note(s, [
    "sentinel-access/backend/app/main.py",
    "sentinel-access/backend/app/routers/copilot.py",
    "specs/004-contextual-risk-scoring/spec.md",
    "specs/005-cloud-log-ingestion/plan.md",
  ]);
}

await fs.mkdir(RENDERS, { recursive: true });
for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(path.join(RENDERS, `${stem}.png`), await deck.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(RENDERS, `${stem}.layout.json`), await layout.text());
}
await writeBlob(path.join(BUILD, "montage.webp"), await deck.export({ format: "webp", montage: true, scale: 1 }));
const inspection = await deck.inspect({ kind: "slide,textbox,shape,notes", maxChars: 30000 });
await fs.writeFile(path.join(BUILD, "inspection.ndjson"), inspection.ndjson);
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(OUT);
console.log(`Wrote ${OUT}`);
