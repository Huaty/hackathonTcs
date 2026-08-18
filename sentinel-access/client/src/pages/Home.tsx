/** Signal Room reminder: this analyst workbench uses asymmetric evidence layers, not a generic centered card grid. */
import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { toast } from "sonner";
import { api, getFindingExplanation } from "@/lib/api";
import {
  Activity,
  ArrowDownToLine,
  ArrowUpRight,
  Bell,
  Check,
  ChevronDown,
  CircleAlert,
  Cloud,
  FileWarning,
  Globe2,
  KeyRound,
  LayoutDashboard,
  Menu,
  MoreHorizontal,
  Radio,
  Search,
  Server,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  Users,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import WorkspaceViews, { type WorkspaceKey } from "@/components/WorkspaceViews";
import DatasetImporter, { type ImportedDataset } from "@/components/DatasetImporter";
import CopilotPanel from "@/components/CopilotPanel";

type Severity = "Critical" | "High" | "Medium" | "Low";
type FindingStatus = "open" | "in_progress" | "escalated" | null;
type AlertRecord = {
  id: string;
  severity: Severity;
  title: string;
  entity: string;
  role: string;
  source: string;
  region: string;
  service: string;
  score: number;
  time: string;
  description: string;
  signals: string[];
  baseline: string;
  recommended: string;
  status: FindingStatus;
};

type SummaryMetrics = {
  activitiesChecked: number;
  needsAttention: number;
  mostUrgentCase: { rank: string; label: string };
  averageReviewTime: string;
  signalConfidencePct: number;
  identityCoveragePct: number;
};

type ModelRationale = {
  topFindingId: string;
  explanation: string;
  signals: { label: string; score: number; tone: string }[];
};

type AccessTrendPoint = { label: string; events: number; anomalies: number };
type ServiceRisk = { name: string; risk: number; events: number };
type ServiceRiskSummary = { highestRiskService: string; sensitiveAssets: number; coverage: string };

type CommandCenterData = {
  summaryMetrics: SummaryMetrics;
  findings: AlertRecord[];
  modelRationale: ModelRationale;
  accessTrend: AccessTrendPoint[];
  accessTrendPeakLabel: string;
  serviceRisk: ServiceRisk[];
  serviceRiskSummary: ServiceRiskSummary;
};

const navItems: { label: string; icon: typeof LayoutDashboard; key: WorkspaceKey }[] = [
  { label: "Command center", icon: LayoutDashboard, key: "command" },
  { label: "Activity explorer", icon: Activity, key: "activity" },
  { label: "Identity profiles", icon: Users, key: "identities" },
  { label: "Cloud estate", icon: Cloud, key: "estate" },
  { label: "Policies", icon: ShieldCheck, key: "policies" },
];

const workspaceLabels: Record<WorkspaceKey, { eyebrow: string; title: string }> = {
  command: { eyebrow: "Command center", title: "Cloud access intelligence" },
  activity: { eyebrow: "Activity explorer", title: "Cloud activity review" },
  identities: { eyebrow: "Identity profiles", title: "People and accounts" },
  estate: { eyebrow: "Cloud estate", title: "Connected cloud systems" },
  policies: { eyebrow: "Policies", title: "What Sentinel watches" },
  reports: { eyebrow: "Reports", title: "Shareable security updates" },
  settings: { eyebrow: "Configuration", title: "Workspace preferences" },
};

const severityTone: Record<Severity, { pill: string; dot: string; border: string; label: string }> = {
  Critical: { pill: "bg-[#ff4d55]/10 text-[#ff8288]", dot: "bg-[#ff5962]", border: "border-l-[#ff5962]", label: "Critical" },
  High: { pill: "bg-[#f5ae45]/10 text-[#ffc570]", dot: "bg-[#f5ae45]", border: "border-l-[#f5ae45]", label: "High" },
  Medium: { pill: "bg-[#97a9ba]/10 text-[#c5d0da]", dot: "bg-[#94a4b5]", border: "border-l-[#94a4b5]", label: "Medium" },
  Low: { pill: "bg-[#39e0c5]/10 text-[#6ae9d4]", dot: "bg-[#39e0c5]", border: "border-l-[#39e0c5]", label: "Low" },
};

function SeverityPill({ severity }: { severity: Severity }) {
  const tone = severityTone[severity];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.11em] ${tone.pill}`}>
      <span className={`size-1.5 rounded-full ${tone.dot}`} />
      {tone.label}
    </span>
  );
}

function SegmentedTrace({ value, color, segments = 10 }: { value: number; color: string; segments?: number }) {
  const filled = Math.max(1, Math.round((value / 100) * segments));
  const style = { gridTemplateColumns: `repeat(${segments}, minmax(0, 1fr))`, "--trace-color": color } as CSSProperties;
  return <div className="segment-trace flex-1" style={style}>{Array.from({ length: segments }, (_, index) => <span key={index} className={index < filled ? "is-lit" : ""} />)}</div>;
}

function RiskTrace({ value, severity }: { value: number; severity: Severity }) {
  const color = severity === "Critical" ? "#ff5962" : severity === "High" ? "#f5ae45" : severity === "Medium" ? "#94a4b5" : "#39e0c5";
  return (
    <div className="flex min-w-[82px] items-center gap-2">
      <SegmentedTrace value={value} color={color} />
      <span className="mono text-[10px] text-slate-300">{value}</span>
    </div>
  );
}

function Metric({ label, value, subtext, accent = "teal" }: { label: string; value: string; subtext: string; accent?: "teal" | "amber" | "red" }) {
  const dot = accent === "red" ? "bg-[#ff5962]" : accent === "amber" ? "bg-[#f5ae45]" : "bg-[#39e0c5]";
  return (
    <div className="relative min-w-0 border-l border-white/10 px-4 first:border-l-0 first:pl-0 sm:px-5">
      <p className="mono mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] text-slate-500"><span className={`size-1.5 rounded-full ${dot}`} />{label}</p>
      <p className="metric-value text-2xl font-semibold tracking-tight text-slate-100 sm:text-[28px]">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{subtext}</p>
    </div>
  );
}

export default function Home() {
  const [commandCenter, setCommandCenter] = useState<CommandCenterData | null>(null);
  const [commandCenterError, setCommandCenterError] = useState(false);
  const alerts = commandCenter?.findings ?? [];
  const [selected, setSelected] = useState<AlertRecord | null>(null);
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [aiExplanationLoading, setAiExplanationLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<"All" | Severity>("All");
  const [serviceFilter, setServiceFilter] = useState("All services");
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceKey>(() => {
    const requestedView = window.location.hash.replace("#", "") as WorkspaceKey;
    return workspaceLabels[requestedView] ? requestedView : "command";
  });
  const [importedDataset, setImportedDataset] = useState<ImportedDataset | null>(null);
  const [notificationUnread, setNotificationUnread] = useState(true);
  const [copilotOpen, setCopilotOpen] = useState(false);

  const loadCommandCenter = useCallback(() => {
    api
      .get<CommandCenterData>("/command-center")
      .then((response) => {
        setCommandCenter(response.data);
        setCommandCenterError(false);
      })
      .catch(() => setCommandCenterError(true));
  }, []);

  useEffect(() => {
    if (workspaceView === "command") loadCommandCenter();
  }, [workspaceView, importedDataset, loadCommandCenter]);

  const filteredAlerts = useMemo(() => alerts.filter((alert) => {
    const bySeverity = severityFilter === "All" || alert.severity === severityFilter;
    const byService = serviceFilter === "All services" || alert.service === serviceFilter;
    const query = searchQuery.toLowerCase();
    const byQuery = !query || [alert.title, alert.entity, alert.service, alert.region].join(" ").toLowerCase().includes(query);
    return bySeverity && byService && byQuery;
  }), [alerts, severityFilter, serviceFilter, searchQuery]);
  const activeInvestigations = alerts.filter((alert) => alert.status === "in_progress").length;
  const navigateToView = (view: WorkspaceKey) => {
    setWorkspaceView(view);
    setSelected(null);
    setMobileMenu(false);
    window.history.replaceState(null, "", view === "command" ? window.location.pathname : `#${view}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const openFinding = (alert: AlertRecord) => {
    setSelected(alert);
    setAiExplanation(null);
    setAiExplanationLoading(true);
    api
      .get<AlertRecord>(`/findings/${alert.id}`)
      .then((response) => setSelected(response.data))
      .catch(() => toast.error("Could not load evidence", { description: "The backend is unreachable. Try again shortly." }));
    getFindingExplanation(alert.id)
      .then((response) => setAiExplanation(response.data.explanation))
      .catch(() => setAiExplanation(null))
      .finally(() => setAiExplanationLoading(false));
  };

  const setFindingStatus = (id: string, status: "in_progress" | "escalated") => {
    api
      .post<AlertRecord>(`/findings/${id}/status`, { status })
      .then((response) => {
        setCommandCenter((current) =>
          current
            ? {
                ...current,
                findings: current.findings.map((f) => (f.id === id ? response.data : f)),
              }
            : current,
        );
        if (status === "in_progress") {
          setSelected(null);
          toast.success("Investigation started", { description: `${id} is now marked IN PROGRESS in the queue.` });
        } else {
          toast.info("Escalation prepared", { description: "A case payload is ready to hand off to the incident-response workflow." });
        }
      })
      .catch(() => toast.error("Action failed", { description: "The backend is unreachable. Try again shortly." }));
  };

  const simulateAnomaly = () => {
    api
      .post<AlertRecord>("/findings/simulate-anomaly")
      .then((response) => {
        const created = response.data;
        setCommandCenter((current) => (current ? { ...current, findings: [created, ...current.findings] } : current));
        setSelected(created);
        toast.success("Synthetic anomaly detected", { description: "A demonstration event was added to the analyst queue." });
        loadCommandCenter();
      })
      .catch(() => toast.error("Could not simulate anomaly", { description: "The backend is unreachable. Try again shortly." }));
  };

  const exportReport = () => {
    const header = "Alert ID,Severity,Entity,Service,Risk Score,Time,Explanation\n";
    const rows = filteredAlerts.map((item) => [item.id, item.severity, item.entity, item.service, item.score, item.time, `\"${item.description}\"`].join(",")).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8" });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = "sentinel-access-demo-report.csv";
    anchor.click();
    URL.revokeObjectURL(href);
    toast.success("Investigation report exported", { description: `${filteredAlerts.length} visible findings saved as CSV.` });
  };

  const exportActivityCsv = () => {
    api
      .get("/reports/export.csv", { responseType: "blob" })
      .then((response) => {
        const href = URL.createObjectURL(response.data as Blob);
        const anchor = document.createElement("a");
        anchor.href = href;
        anchor.download = "activity-export.csv";
        anchor.click();
        URL.revokeObjectURL(href);
        toast.success("Activity export ready", { description: "The current activity log was exported from the backend as CSV." });
      })
      .catch(() => toast.error("Could not export activity", { description: "The backend is unreachable. Try again shortly." }));
  };

  return (
    <div className="app-shell relative overflow-hidden">
      <div className="signal-grid pointer-events-none absolute inset-0 opacity-50" />
      <div className="relative z-10 flex min-h-screen">
      <aside className="desktop-rail sticky top-0 z-30 flex h-screen w-[238px] shrink-0 flex-col border-r border-white/10 bg-[#0b121b]/95 px-4 py-5 backdrop-blur-xl">
        <div className="pointer-events-none absolute right-0 top-[74px] bottom-[82px] w-px bg-gradient-to-b from-transparent via-[#39e0c5]/45 to-transparent"><span className="status-pulse absolute -left-[3px] top-[14%] size-[7px] rounded-full bg-[#39e0c5]" /></div>
        <BrandBlock />
        <div className="no-scrollbar min-h-0 flex-1 overflow-y-auto">
          <div className="mt-10 px-2"><p className="mono text-[10px] uppercase tracking-[0.16em] text-slate-600">Workspace</p></div>
          <nav className="mt-3 space-y-1" aria-label="Primary navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              return <button key={item.label} onClick={() => navigateToView(item.key)} className={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${workspaceView === item.key ? "bg-[#173039] text-[#b7fff2]" : "text-slate-500 hover:bg-white/[0.045] hover:text-slate-200"}`}><Icon className="size-[17px]" />{item.label}{workspaceView === item.key && <span className="ml-auto size-1.5 rounded-full bg-[#39e0c5] shadow-[0_0_13px_#39e0c5]" />}</button>;
            })}
          </nav>
          <div className="mt-7 border-t border-white/10 pt-6">
            <p className="mono px-2 text-[10px] uppercase tracking-[0.16em] text-slate-600">Operations</p>
            <div className="mt-3 space-y-1">
              <button onClick={() => navigateToView("reports")} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${workspaceView === "reports" ? "bg-[#173039] text-[#b7fff2]" : "text-slate-500 hover:bg-white/[0.045] hover:text-slate-200"}`}><ArrowDownToLine className="size-[17px]" />Reports</button>
              <button onClick={() => navigateToView("settings")} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${workspaceView === "settings" ? "bg-[#173039] text-[#b7fff2]" : "text-slate-500 hover:bg-white/[0.045] hover:text-slate-200"}`}><Settings className="size-[17px]" />Configuration</button>
            </div>
          </div>
        </div>
        <div className="mt-4 shrink-0 rounded-2xl border border-[#39e0c5]/15 bg-[#10252a]/60 p-3.5">
          <div className="flex items-center gap-2"><span className="status-pulse size-2 rounded-full bg-[#39e0c5]" /><span className="mono text-[10px] uppercase tracking-[0.12em] text-[#75f5e0]">Detection live</span></div>
          <p className="mt-2 text-xs leading-5 text-slate-400">8 cloud sources normalized · demo telemetry</p>
        </div>
      </aside>

      <main className="relative min-w-0 flex-1">
        <header className="flex min-h-[78px] items-center justify-between border-b border-white/10 bg-[#0b121b]/65 px-5 backdrop-blur-md sm:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button className="rounded-lg p-2 text-slate-300 md:hidden" onClick={() => setMobileMenu((open) => !open)} aria-label="Open navigation"><Menu className="size-5" /></button>
            <div className="min-w-0"><div className="flex items-center gap-2"><p className="mono text-[10px] uppercase tracking-[0.15em] text-[#76eddb]">{workspaceLabels[workspaceView].eyebrow}</p><span className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[9px] font-medium text-slate-500">DEMO</span></div><h1 className="truncate text-sm font-medium text-slate-100 sm:text-base">{workspaceLabels[workspaceView].title}</h1></div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="hidden items-center gap-2 rounded-xl border border-white/10 bg-white/[0.025] px-3 py-2 text-xs text-slate-500 lg:flex"><Radio className="size-3.5 text-[#39e0c5]" />Last 24 hours <ChevronDown className="size-3.5" /></div>
            <button onClick={() => setCopilotOpen(true)} className="inline-flex items-center gap-2 rounded-xl border border-[#39e0c5]/25 bg-[#39e0c5]/10 px-3 py-2 text-xs font-semibold text-[#8df6e7] transition-transform active:scale-[0.97] hover:bg-[#39e0c5]/15 sm:px-4"><Sparkles className="size-3.5" /><span className="hidden sm:inline">Ask Sentinel</span><span className="sm:hidden">Ask</span></button>
            <button onClick={simulateAnomaly} className="inline-flex items-center gap-2 rounded-xl bg-[#39e0c5] px-3 py-2 text-xs font-semibold text-[#071312] shadow-[0_0_26px_rgba(57,224,197,0.13)] transition-transform active:scale-[0.97] sm:px-4"><Sparkles className="size-3.5" /><span className="hidden sm:inline">Simulate anomaly</span><span className="sm:hidden">Simulate</span></button>
            <button onClick={() => { setNotificationUnread(false); toast.success("Notifications cleared", { description: "You have read the current demo alert summary." }); }} className="relative rounded-xl border border-white/10 bg-white/[0.025] p-2 text-slate-400 transition-colors hover:text-white"><Bell className="size-4" />{notificationUnread && <span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-[#f5ae45]" />}</button>
            <button onClick={() => toast.info("Signed-in demo analyst", { description: "Aisha Rahman · Cloud Security Analyst · Connect this menu to your identity provider in production." })} className="flex size-8 items-center justify-center rounded-full bg-gradient-to-br from-[#2f6471] to-[#1d3049] text-xs font-semibold text-[#b9fff4]">AR</button>
          </div>
        </header>

        {mobileMenu && <div className="border-b border-white/10 bg-[#0b121b] px-4 py-3 md:hidden"><nav className="grid grid-cols-2 gap-2">{navItems.map((item) => { const Icon = item.icon; return <button key={item.label} onClick={() => navigateToView(item.key)} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${workspaceView === item.key ? "bg-[#173039] text-[#b7fff2]" : "bg-white/[0.03] text-slate-400"}`}><Icon className="size-3.5" />{item.label}</button>; })}</nav></div>}

        <div className={workspaceView === "command" ? "mx-auto max-w-[1600px] px-5 py-6 sm:px-8 sm:py-8" : "hidden"}>
          <section className="overflow-hidden rounded-2xl border border-white/10 bg-[#0d1722]">
            <div className="relative grid gap-7 p-5 sm:p-7 xl:grid-cols-[1.2fr_0.8fr] xl:p-8">
              <img src="/manus-storage/sentinel-hero_0c409c4e.jpg" alt="Abstract cloud access signal topology" className="absolute inset-0 size-full object-cover object-right opacity-45 mix-blend-screen" />
              <div className="absolute inset-0 bg-gradient-to-r from-[#0d1722] via-[#0d1722]/92 to-[#0d1722]/40" />
              <div className="relative"><div className="mb-4 flex items-center gap-2"><span className="status-pulse size-2 rounded-full bg-[#39e0c5]" /><span className="mono text-[10px] uppercase tracking-[0.16em] text-[#7bf1e0]">Simple security summary</span></div><h2 className="max-w-2xl text-2xl font-semibold tracking-[-0.04em] text-white sm:text-3xl">Three unusual activities need a quick check.</h2><p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">We checked <strong className="font-medium text-slate-200">{(commandCenter?.summaryMetrics.activitiesChecked ?? 0).toLocaleString()} cloud activities</strong> and highlighted the ones that look different from a person’s usual sign-in, location, device, or permission use.</p><div className="mt-6 flex flex-wrap items-center gap-3"><button onClick={() => document.getElementById("alert-queue")?.scrollIntoView({ behavior: "smooth" })} className="inline-flex items-center gap-2 rounded-lg bg-white px-3.5 py-2 text-xs font-semibold text-[#101720] transition-transform active:scale-[0.97]">See what needs attention <ArrowUpRight className="size-3.5" /></button><button onClick={() => toast.info("What the score means", { description: "A higher score means the activity is more different from normal and should be reviewed sooner. It is a prompt to check, not proof that someone did something wrong." })} className="rounded-lg border border-white/15 bg-black/10 px-3.5 py-2 text-xs font-medium text-slate-300 transition-colors hover:bg-white/5">What do these scores mean?</button></div></div>
              <div className="relative grid grid-cols-2 gap-3 self-end xl:grid-cols-2"><div className="rounded-xl border border-white/10 bg-[#0a1119]/70 p-4 backdrop-blur"><p className="mono text-[9px] uppercase tracking-[0.14em] text-slate-500">Signal confidence</p><p className="mt-2 text-2xl font-semibold tracking-tight text-[#76eddb]">{commandCenter?.summaryMetrics.signalConfidencePct ?? "–"}%</p><p className="mt-1 text-[11px] text-slate-500">explainability coverage</p></div><div className="rounded-xl border border-white/10 bg-[#0a1119]/70 p-4 backdrop-blur"><p className="mono text-[9px] uppercase tracking-[0.14em] text-slate-500">Identity coverage</p><p className="mt-2 text-2xl font-semibold tracking-tight text-slate-100">{commandCenter?.summaryMetrics.identityCoveragePct ?? "–"}%</p><p className="mt-1 text-[11px] text-slate-500">of active principals</p></div></div>
            </div>
            <div className="relative grid divide-y divide-white/10 border-t border-white/10 bg-[#0a1119]/70 sm:grid-cols-4 sm:divide-x sm:divide-y-0"><Metric label="Activities checked" value={(commandCenter?.summaryMetrics.activitiesChecked ?? 0).toLocaleString()} subtext="Everything reviewed today" /><Metric label="Needs attention" value={String(commandCenter?.summaryMetrics.needsAttention ?? 0)} subtext={activeInvestigations ? `${activeInvestigations} being checked now` : "Awaiting a decision"} accent="amber" /><Metric label="Most urgent case" value={commandCenter?.summaryMetrics.mostUrgentCase.rank ?? "–"} subtext={commandCenter?.summaryMetrics.mostUrgentCase.label ?? "No data yet"} accent="red" /><Metric label="Average review time" value={commandCenter?.summaryMetrics.averageReviewTime ?? "–"} subtext="Time to understand a case" /></div>
          </section>

          {commandCenterError && <div className="mt-4 rounded-xl border border-[#f5ae45]/30 bg-[#251c10]/45 px-4 py-3 text-sm text-[#ffcf89]">Could not reach the Sentinel Access backend. Data shown may be stale or missing — check that the API is running.</div>}
          {!commandCenter && !commandCenterError && <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3 text-sm text-slate-400">Loading live data from the backend…</div>}

          <DatasetImporter dataset={importedDataset} onDataset={setImportedDataset} onClear={() => setImportedDataset(null)} onOpenExplorer={() => navigateToView("activity")} />

          <section className="mt-4 overflow-hidden rounded-2xl border border-[#39e0c5]/15 bg-[#0e2025]/50">
            <div className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6"><div><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">New here? Read this first</p><p className="mt-1 text-sm text-slate-300">Think of this dashboard as a short priority list. It tells you what looks unusual, explains why, and helps you record that someone is checking it.</p></div><button onClick={() => document.getElementById("alert-queue")?.scrollIntoView({ behavior: "smooth" })} className="shrink-0 rounded-lg border border-[#39e0c5]/25 bg-[#39e0c5]/10 px-3 py-2 text-xs font-semibold text-[#8df6e7] hover:bg-[#39e0c5]/15">Start with the list below</button></div>
            <div className="grid border-t border-[#39e0c5]/10 sm:grid-cols-3"><div className="px-5 py-3.5 sm:px-6"><span className="mono text-[10px] text-[#76eddb]">01</span><p className="mt-1 text-xs font-medium text-slate-200">Choose a red or amber item</p><p className="mt-1 text-[11px] leading-4 text-slate-500">Red means review first. Amber means important, but less urgent.</p></div><div className="border-t border-[#39e0c5]/10 px-5 py-3.5 sm:border-l sm:border-t-0 sm:px-6"><span className="mono text-[10px] text-[#76eddb]">02</span><p className="mt-1 text-xs font-medium text-slate-200">Read the simple explanation</p><p className="mt-1 text-[11px] leading-4 text-slate-500">Open a row to see what changed from normal and why it was noticed.</p></div><div className="border-t border-[#39e0c5]/10 px-5 py-3.5 sm:border-l sm:border-t-0 sm:px-6"><span className="mono text-[10px] text-[#76eddb]">03</span><p className="mt-1 text-xs font-medium text-slate-200">Mark it as being checked</p><p className="mt-1 text-[11px] leading-4 text-slate-500">This closes the pop-up and visibly changes the item’s status in the list.</p></div></div>
          </section>

          <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.75fr)]">
            <div className="glass-panel rounded-2xl p-5 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="mono text-[10px] uppercase tracking-[0.15em] text-[#77eddb]">01 / access rhythm</p><h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-100">Behavioral variance across the day</h3></div><div className="flex items-center gap-3 text-[10px] text-slate-500"><span className="flex items-center gap-1.5"><i className="block size-2 rounded-full bg-[#39e0c5]" />Access volume</span><span className="flex items-center gap-1.5"><i className="block size-2 rounded-full bg-[#f5ae45]" />Anomalies</span></div></div>
              <div className="mt-4 h-[240px] w-full"><ResponsiveContainer width="100%" height="100%"><AreaChart data={commandCenter?.accessTrend ?? []} margin={{ top: 8, right: 6, left: -26, bottom: 0 }}><defs><linearGradient id="eventFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#39e0c5" stopOpacity={0.36} /><stop offset="100%" stopColor="#39e0c5" stopOpacity={0} /></linearGradient></defs><CartesianGrid vertical={false} stroke="rgba(184,210,225,0.08)" strokeDasharray="3 4" /><XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: "#667889", fontSize: 10, fontFamily: "IBM Plex Mono" }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: "#667889", fontSize: 10, fontFamily: "IBM Plex Mono" }} /><Tooltip cursor={{ stroke: "rgba(255,255,255,.18)", strokeWidth: 1 }} contentStyle={{ background: "#101a25", border: "1px solid rgba(255,255,255,.12)", borderRadius: 10, color: "#e7edf2", fontSize: 12 }} labelStyle={{ color: "#8292a1" }} /><Area type="monotone" dataKey="events" name="Events" stroke="#39e0c5" strokeWidth={2} fill="url(#eventFill)" /><Line type="monotone" dataKey="anomalies" name="Anomalies" stroke="#f5ae45" strokeWidth={2} dot={{ r: 3, fill: "#f5ae45", stroke: "#0e1720", strokeWidth: 2 }} /></AreaChart></ResponsiveContainer></div>
              <div className="mt-2 flex items-center justify-between border-t border-white/[0.08] pt-4 text-xs"><span className="text-slate-500">Peak variance surfaced at <strong className="font-medium text-slate-200">{commandCenter?.accessTrendPeakLabel ?? "–"}</strong></span><button onClick={() => navigateToView("activity")} className="font-medium text-[#69ead5] hover:text-[#b6fff4]">Open activity explorer →</button></div>
            </div>

            <div className="glass-panel rounded-2xl p-5 sm:p-6"><div className="flex items-start justify-between"><div><p className="mono text-[10px] uppercase tracking-[0.15em] text-[#77eddb]">02 / exposure map</p><h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-100">Service risk concentration</h3></div><button onClick={() => toast.info("Risk distribution", { description: "Risk is weighted by the sensitivity of accessed assets and the confidence of behavioral deviation." })} className="rounded-lg p-1 text-slate-500 hover:bg-white/5 hover:text-white"><MoreHorizontal className="size-5" /></button></div><div className="mt-4 h-[188px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={commandCenter?.serviceRisk ?? []} layout="vertical" margin={{ top: 4, right: 8, left: 0, bottom: 0 }}><XAxis type="number" hide domain={[0, 100]} /><YAxis type="category" dataKey="name" axisLine={false} tickLine={false} width={58} tick={{ fill: "#a7b3be", fontSize: 11, fontFamily: "IBM Plex Mono" }} /><Tooltip cursor={{ fill: "rgba(255,255,255,.035)" }} contentStyle={{ background: "#101a25", border: "1px solid rgba(255,255,255,.12)", borderRadius: 10, color: "#e7edf2", fontSize: 12 }} /><Bar dataKey="risk" name="Risk index" radius={[0, 6, 6, 0]} barSize={12}>{(commandCenter?.serviceRisk ?? []).map((entry) => <Cell key={entry.name} fill={entry.risk > 80 ? "#ff5962" : entry.risk > 65 ? "#f5ae45" : entry.risk > 45 ? "#94a4b5" : "#39e0c5"} />)}</Bar></BarChart></ResponsiveContainer></div><div className="mt-5 grid grid-cols-3 divide-x divide-white/[0.09]"><div><p className="mono text-[9px] uppercase tracking-wider text-slate-600">Highest</p><p className="mt-1 text-sm font-medium text-slate-200">{commandCenter?.serviceRiskSummary.highestRiskService ?? "–"}</p></div><div className="pl-4"><p className="mono text-[9px] uppercase tracking-wider text-slate-600">Sensitive assets</p><p className="mt-1 text-sm font-medium text-slate-200">{commandCenter?.serviceRiskSummary.sensitiveAssets ?? "–"}</p></div><div className="pl-4"><p className="mono text-[9px] uppercase tracking-wider text-slate-600">Coverage</p><p className="mt-1 text-sm font-medium text-[#73ecd9]">{commandCenter?.serviceRiskSummary.coverage ?? "–"}</p></div></div></div>
          </section>

          <section id="alert-queue" className="mt-6 grid gap-6 2xl:grid-cols-[minmax(0,1.55fr)_minmax(340px,0.65fr)]">
            <div className="glass-panel overflow-hidden rounded-2xl">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.1] px-5 py-5 sm:px-6"><div><p className="mono text-[10px] uppercase tracking-[0.15em] text-[#77eddb]">03 / investigation queue</p><h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-100">Prioritized findings</h3></div><div className="flex items-center gap-2"><button onClick={exportReport} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs font-medium text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-100"><ArrowDownToLine className="size-3.5" />Export</button><button onClick={() => toast.info("Filters applied", { description: "Use severity, service, or free-text search to focus the queue." })} className="rounded-lg border border-white/10 p-2 text-slate-400 hover:bg-white/5 hover:text-white"><Search className="size-3.5" /></button></div></div>
              <div className="flex flex-col gap-3 border-b border-white/[0.08] bg-black/[0.08] px-5 py-3.5 sm:flex-row sm:items-center sm:px-6"><div className="relative flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-slate-600" /><input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search identity, service, or geography" className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.025] pl-9 pr-3 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-[#39e0c5]/60" /></div><select aria-label="Filter by severity" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value as "All" | Severity)} className="h-9 rounded-lg border border-white/10 bg-[#111b26] px-3 text-xs text-slate-300 outline-none"><option>All</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select><select aria-label="Filter by service" value={serviceFilter} onChange={(event) => setServiceFilter(event.target.value)} className="h-9 rounded-lg border border-white/10 bg-[#111b26] px-3 text-xs text-slate-300 outline-none"><option>All services</option><option>AWS IAM</option><option>AWS Secrets Manager</option><option>Azure AD</option><option>GitHub Enterprise</option></select></div>
              <div className="overflow-x-auto"><table className="w-full min-w-[730px] text-left"><thead><tr className="mono border-b border-white/[0.07] text-[9px] uppercase tracking-[0.12em] text-slate-600"><th className="px-5 py-3 font-medium sm:px-6">Activity to check</th><th className="px-3 py-3 font-medium">Who or what</th><th className="px-3 py-3 font-medium">What we noticed</th><th className="px-3 py-3 font-medium">Priority score</th><th className="px-5 py-3 text-right font-medium sm:px-6">When</th></tr></thead><tbody>{filteredAlerts.map((alert) => <tr onClick={() => openFinding(alert)} key={alert.id} className={`queue-row cursor-pointer border-b border-white/[0.06] border-l-[3px] ${severityTone[alert.severity].border} bg-transparent hover:bg-white/[0.035]`}><td className="px-5 py-4 sm:px-6"><div className="flex items-center gap-3"><SeverityPill severity={alert.severity} /><div><p className="text-sm font-medium text-slate-100">{alert.title}</p><p className="mono mt-1 text-[10px] text-slate-600">{alert.id} · {alert.service}{alert.status === "in_progress" && <span className="font-semibold text-[#73ecd9]"> · IN PROGRESS</span>}{alert.status === "escalated" && <span className="font-semibold text-[#ffbe62]"> · ESCALATED</span>}</p></div></div></td><td className="px-3 py-4"><p className="text-xs font-medium text-slate-300">{alert.entity}</p><p className="mt-1 text-[10px] text-slate-600">{alert.role}</p></td><td className="px-3 py-4"><div className="flex max-w-[180px] flex-wrap gap-1">{alert.signals.slice(0, 2).map((signal) => <span key={signal} className="rounded bg-white/[0.055] px-1.5 py-1 text-[9px] text-slate-400">{signal}</span>)}</div></td><td className="px-3 py-4"><RiskTrace value={alert.score} severity={alert.severity} /></td><td className="px-5 py-4 text-right sm:px-6"><p className="mono text-[10px] text-slate-400">{alert.time}</p><ArrowUpRight className="ml-auto mt-1 size-3 text-slate-600" /></td></tr>)}</tbody></table></div>
              {filteredAlerts.length === 0 && <div className="px-6 py-14 text-center"><Search className="mx-auto size-5 text-slate-600" /><p className="mt-3 text-sm font-medium text-slate-300">No findings match these filters.</p><button onClick={() => { setSeverityFilter("All"); setServiceFilter("All services"); setSearchQuery(""); }} className="mt-2 text-xs text-[#71ead5]">Clear filters</button></div>}
              <div className="flex items-center justify-between px-5 py-3.5 text-xs text-slate-500 sm:px-6"><span>Showing <strong className="font-medium text-slate-300">{filteredAlerts.length}</strong> prioritized findings</span><span className="mono text-[10px]">LAST SYNC 08:45:18 UTC</span></div>
            </div>

            <div className="space-y-6"><div className="glass-panel rounded-2xl p-5 sm:p-6"><div className="flex items-start justify-between"><div><p className="mono text-[10px] uppercase tracking-[0.15em] text-[#77eddb]">04 / model rationale</p><h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-100">Why this was elevated</h3></div><FileWarning className="size-5 text-[#f5ae45]" /></div><p className="mt-4 text-sm leading-6 text-slate-400">{commandCenter?.modelRationale.explanation ?? "Loading rationale…"}</p><div className="mt-5 space-y-3">{(commandCenter?.modelRationale.signals ?? []).map((signal) => <div key={signal.label}><div className="mb-1.5 flex justify-between text-xs"><span className="text-slate-400">{signal.label}</span><span className="mono text-slate-300">{signal.score}</span></div><SegmentedTrace value={signal.score} color={signal.tone} segments={14} /></div>)}</div><button onClick={() => { const top = alerts.find((a) => a.id === commandCenter?.modelRationale.topFindingId); if (top) openFinding(top); }} className="mt-6 inline-flex items-center gap-2 text-xs font-semibold text-[#78eedc] hover:text-[#c0fff4]">Open top evidence <ArrowUpRight className="size-3.5" /></button></div>
              <div className="overflow-hidden rounded-2xl border border-[#39e0c5]/15 bg-[#102329]/45"><div className="flex items-center justify-between border-b border-[#39e0c5]/10 px-5 py-3"><div className="flex items-center gap-2"><span className="size-2 rounded-full bg-[#39e0c5]" /><span className="mono text-[10px] uppercase tracking-[0.13em] text-[#83f3e1]">Demo data contract</span></div><ShieldCheck className="size-4 text-[#39e0c5]" /></div><div className="p-5"><p className="text-sm font-medium text-slate-200">Designed for privacy-safe prototyping.</p><p className="mt-2 text-xs leading-5 text-slate-500">All identities, addresses, event volumes, and locations in this environment are synthetic. Connect normalized cloud audit logs when moving beyond the hackathon demo.</p></div></div>
            </div>
          </section>
        </div>
        {workspaceView !== "command" && <WorkspaceViews view={workspaceView} onNavigate={navigateToView} onExport={exportActivityCsv} dataset={importedDataset} />}
      </main>
      </div>

      <CopilotPanel open={copilotOpen} onClose={() => setCopilotOpen(false)} />

      {selected && <div className="fixed inset-0 z-50 flex justify-end bg-[#02070b]/55 backdrop-blur-[2px]" role="dialog" aria-modal="true" aria-label="Finding evidence"><aside className="h-full w-full max-w-[560px] overflow-y-auto border-l border-white/10 bg-[#0d1620] shadow-[-24px_0_70px_rgba(0,0,0,0.35)]"><div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#0d1620]/95 px-5 py-4 backdrop-blur"><div className="flex items-center gap-3"><div className={`flex size-9 items-center justify-center rounded-xl ${severityTone[selected.severity].pill}`}><ShieldAlert className="size-4" /></div><div><p className="mono text-[10px] uppercase tracking-[0.13em] text-slate-500">Evidence dossier</p><p className="text-sm font-medium text-slate-100">{selected.id}</p></div></div><button onClick={() => { setSelected(null); setAiExplanation(null); }} className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="Close evidence dossier"><X className="size-5" /></button></div><div className="p-5 sm:p-7"><div className="flex flex-wrap items-center gap-3"><SeverityPill severity={selected.severity} /><span className="mono text-[10px] text-slate-500">OBSERVED {selected.time}</span></div><h2 className="mt-4 text-2xl font-semibold tracking-[-0.04em] text-white">{selected.title}</h2><p className="mt-3 text-sm leading-6 text-slate-400">{selected.description}</p><div className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-white/10 bg-white/10"><div className="bg-[#101a25] p-4"><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Identity</p><p className="mt-2 text-sm font-medium text-slate-200">{selected.entity}</p><p className="mt-1 text-xs text-slate-500">{selected.role}</p></div><div className="bg-[#101a25] p-4"><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Risk score</p><p className="mt-1 text-2xl font-semibold text-[#ffbe62]">{selected.score}<span className="text-xs text-slate-500"> / 100</span></p><p className="text-xs text-slate-500">high-confidence deviation</p></div><div className="bg-[#101a25] p-4"><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Source</p><p className="mono mt-2 text-xs text-slate-300">{selected.source}</p><p className="mt-1 text-xs text-slate-500">{selected.region}</p></div><div className="bg-[#101a25] p-4"><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Service</p><p className="mt-2 text-sm font-medium text-slate-200">{selected.service}</p><p className="mt-1 text-xs text-slate-500">normalized audit signal</p></div></div><section className="mt-7"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">AI explanation</p><div className="mt-3 rounded-xl border border-[#39e0c5]/15 bg-[#10242a]/35 p-4"><p className="text-sm leading-6 text-slate-300">{aiExplanationLoading ? "Generating explanation…" : (aiExplanation ?? selected.baseline)}</p></div></section><section className="mt-7"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Evidence signals</p><div className="mt-3 space-y-2">{selected.signals.map((signal, index) => <div key={signal} className="flex items-center justify-between rounded-xl border border-white/[0.08] bg-white/[0.025] px-3.5 py-3"><div className="flex items-center gap-3"><span className="mono flex size-5 items-center justify-center rounded bg-white/[0.05] text-[9px] text-slate-500">0{index + 1}</span><span className="text-xs text-slate-300">{signal}</span></div><Check className="size-3.5 text-[#39e0c5]" /></div>)}</div></section><section className="mt-7 overflow-hidden rounded-xl border border-[#f5ae45]/20 bg-[#251c10]/45"><div className="flex gap-3 p-4"><CircleAlert className="mt-0.5 size-4 shrink-0 text-[#f5ae45]" /><div><p className="text-sm font-medium text-[#ffcf89]">Recommended response</p><p className="mt-1 text-xs leading-5 text-slate-400">{selected.recommended}</p></div></div></section><div className="mt-7 flex gap-3"><button onClick={() => { if (selected.status === "in_progress") { setSelected(null); return; } setFindingStatus(selected.id, "in_progress"); }} className="flex-1 rounded-xl bg-[#39e0c5] px-4 py-3 text-xs font-semibold text-[#071312] transition-transform active:scale-[0.97]">{selected.status === "in_progress" ? "Back to queue" : "Start investigation"}</button><button onClick={() => setFindingStatus(selected.id, "escalated")} className="rounded-xl border border-white/10 px-4 py-3 text-xs font-semibold text-slate-300 hover:bg-white/5">Escalate</button></div></div></aside></div>}
    </div>
  );
}

function BrandBlock() {
  return <div className="flex items-center gap-3 px-2"><div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#39e0c5]/25 to-[#39e0c5]/5 ring-1 ring-inset ring-[#39e0c5]/30"><ShieldCheck className="size-5 text-[#39e0c5]" /></div><div><p className="text-sm font-semibold tracking-[-0.03em] text-slate-100">Sentinel<span className="text-[#59e9d2]">Access</span></p><p className="mono mt-0.5 text-[9px] uppercase tracking-[0.12em] text-slate-600">security intelligence</p></div></div>;
}
