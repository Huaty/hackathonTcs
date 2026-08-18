/** Signal Room reminder: each workspace view is an evidence-led analyst page with plain-language guidance and restrained graphite panels. */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { api, getIdentityProfile, runRiskAssessment, simulateIdentityEvent, type IdentityProfileResponse } from "@/lib/api";
import type { ImportedDataset } from "@/components/DatasetImporter";
import {
  Activity,
  ArrowDownToLine,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Cloud,
  FileText,
  Filter,
  Globe2,
  KeyRound,
  LockKeyhole,
  Mail,
  MapPin,
  MoreHorizontal,
  PanelTop,
  Search,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  UserRound,
  Users,
} from "lucide-react";

export type WorkspaceKey = "command" | "activity" | "identities" | "estate" | "policies" | "reports" | "settings";

type WorkspaceProps = {
  view: Exclude<WorkspaceKey, "command">;
  onNavigate: (view: WorkspaceKey) => void;
  onExport: () => void;
  dataset: ImportedDataset | null;
};

type ActivityRow = { time: string; actor: string; action: string; source: string; system: string; status: string; tone: string };
type IdentityCard = { identityId: string; name: string; initials: string; role: string; activity: string; score: number; color: string; description: string };
type CloudSourceCard = { name: string; type: string; status: string; eventsToday: number; health: string; icon: string; color: string; dataFreshnessMin: number };

const cloudSourceIcons: Record<string, typeof KeyRound> = {
  KeyRound,
  LockKeyhole,
  Users,
  PanelTop,
  Cloud,
};

type PolicyRule = { title: string; description: string; enabled: boolean; category: string };
type ReportTemplate = { title: string; detail: string; period: string; type: string };

const toneClasses: Record<string, string> = {
  critical: "border-[#ff5962]/30 bg-[#ff5962]/10 text-[#ff9ba1]",
  high: "border-[#f5ae45]/30 bg-[#f5ae45]/10 text-[#ffd18d]",
  medium: "border-[#94a4b5]/30 bg-[#94a4b5]/10 text-[#d2d9e0]",
  normal: "border-[#39e0c5]/25 bg-[#39e0c5]/10 text-[#86f2e1]",
};

function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="flex flex-col gap-4 border-b border-white/10 pb-6 sm:flex-row sm:items-end sm:justify-between"><div><p className="mono text-[10px] uppercase tracking-[0.15em] text-[#76eddb]">{eyebrow}</p><h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em] text-slate-100 sm:text-3xl">{title}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">{description}</p></div>{action}</div>;
}

function InfoStrip({ children }: { children: ReactNode }) {
  return <div className="mt-5 flex gap-3 rounded-xl border border-[#39e0c5]/15 bg-[#10242a]/45 px-4 py-3 text-xs leading-5 text-slate-300"><Sparkles className="mt-0.5 size-4 shrink-0 text-[#39e0c5]" /><p>{children}</p></div>;
}

export default function WorkspaceViews({ view, onNavigate, onExport, dataset }: WorkspaceProps) {
  return <div className="mx-auto max-w-[1600px] px-5 py-7 sm:px-8 sm:py-9">
    {view === "activity" && <ActivityExplorer onNavigate={onNavigate} dataset={dataset} />}
    {view === "identities" && <IdentityProfiles />}
    {view === "estate" && <CloudEstate />}
    {view === "policies" && <Policies />}
    {view === "reports" && <Reports onExport={onExport} />}
    {view === "settings" && <Configuration onNavigate={onNavigate} />}
  </div>;
}

function ActivityExplorer({ onNavigate, dataset }: { onNavigate: (view: WorkspaceKey) => void; dataset: ImportedDataset | null }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All activity");
  const [backendRows, setBackendRows] = useState<ActivityRow[]>([]);
  const [selected, setSelected] = useState<ActivityRow | null>(null);
  const [reviewed, setReviewed] = useState<string[]>([]);

  const [source, setSource] = useState<"seed" | "imported">("seed");

  useEffect(() => {
    api
      .get<{ events: ActivityRow[]; source: "seed" | "imported" }>("/activity")
      .then((response) => {
        setBackendRows(response.data.events);
        setSource(response.data.source);
      })
      .catch(() => toast.error("Could not load activity", { description: "The backend is unreachable. Try again shortly." }));
  }, [dataset]);

  const displayedRows = backendRows;
  useEffect(() => {
    if (displayedRows.length) setSelected(displayedRows[0]);
  }, [displayedRows]);
  const selectedKey = selected ? `${selected.time}-${selected.actor}` : "";
  const results = useMemo(() => displayedRows.filter((row) => {
    const haystack = `${row.actor} ${row.action} ${row.source} ${row.system}`.toLowerCase();
    const matchesSearch = !query || haystack.includes(query.toLowerCase());
    const matchesFilter = filter === "All activity" || (filter === "Needs attention" ? row.status === "Needs attention" : (row.status === "Normal" || row.status === "Imported"));
    return matchesSearch && matchesFilter;
  }), [query, filter, displayedRows]);
  return <>
    <PageHeading eyebrow="Activity explorer" title="See every important cloud activity" description="Search the day’s activity, then choose a row to see a plain-language explanation of what happened and whether it needs attention." action={<span className="mono rounded-full border border-[#39e0c5]/20 bg-[#39e0c5]/10 px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-[#79efdd]">{source === "imported" ? `${backendRows.length.toLocaleString()} imported records` : `${backendRows.length.toLocaleString()} synthetic activities`}</span>} />
    <InfoStrip>{source === "imported" && dataset ? <>You are viewing <strong className="font-semibold text-slate-100">{dataset.fileName}</strong>, imported and stored by the backend for this session.</> : <>Start with <strong className="font-semibold text-slate-100">Needs attention</strong>. These are not confirmed incidents; they are the activities most worth a human check.</>}</InfoStrip>
    <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(330px,0.75fr)]">
      <div className="glass-panel overflow-hidden rounded-2xl"><div className="flex flex-col gap-3 border-b border-white/10 p-4 sm:flex-row"><div className="relative flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-600" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a person, system, location, or activity" className="h-10 w-full rounded-lg border border-white/10 bg-white/[0.03] pl-9 pr-3 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-[#39e0c5]/50" /></div><select value={filter} onChange={(event) => setFilter(event.target.value)} className="h-10 rounded-lg border border-white/10 bg-[#111b26] px-3 text-xs text-slate-300 outline-none"><option>All activity</option><option>Needs attention</option><option>Normal</option></select></div><div className="divide-y divide-white/[0.07]">{results.map((row) => <button onClick={() => setSelected(row)} key={`${row.time}-${row.actor}`} className={`flex w-full items-center gap-4 px-4 py-4 text-left transition-colors hover:bg-white/[0.035] ${selected === row ? "bg-[#173039]/50" : ""}`}><span className="mono w-10 text-[10px] text-slate-500">{row.time}</span><span className={`size-2 shrink-0 rounded-full ${row.tone === "critical" ? "bg-[#ff5962]" : row.tone === "high" ? "bg-[#f5ae45]" : row.tone === "normal" ? "bg-[#39e0c5]" : "bg-[#94a4b5]"}`} /><span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium text-slate-200">{row.actor}</span><span className="mt-1 block truncate text-xs text-slate-500">{row.action}</span></span><span className={`hidden rounded-full border px-2 py-1 text-[9px] font-semibold uppercase tracking-wider sm:inline ${toneClasses[row.tone]}`}>{row.status}</span><ChevronRight className="size-4 text-slate-600" /></button>)}</div>{results.length === 0 && <div className="p-10 text-center text-sm text-slate-500">No activity matches those filters.</div>}</div>
      {selected && <div className="glass-panel rounded-2xl p-5"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Selected activity</p><h3 className="mt-2 text-lg font-semibold tracking-tight text-slate-100">{selected.actor}</h3><p className="mt-2 text-sm leading-6 text-slate-400">{selected.action}. This happened from <strong className="font-medium text-slate-200">{selected.source}</strong> using <strong className="font-medium text-slate-200">{selected.system}</strong>.</p><div className="mt-5 rounded-xl border border-white/10 bg-black/[0.12] p-4"><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Why it is shown here</p><p className="mt-2 text-sm leading-6 text-slate-300">{selected.status === "Normal" ? "This fits the account’s usual pattern. It is included for context, but does not need action." : "It is different enough from usual activity to deserve a quick human check. Open the person’s profile or record an investigation if you need to follow up."}</p></div>{reviewed.includes(selectedKey) && <div className="mt-4 flex items-center gap-2 rounded-xl border border-[#39e0c5]/20 bg-[#39e0c5]/10 p-3 text-xs text-[#8af4e4]"><CheckCircle2 className="size-4" />This activity is marked as checked in this review session.</div>}<div className="mt-5 grid grid-cols-2 gap-3"><button onClick={() => { setReviewed((current) => current.includes(selectedKey) ? current : [...current, selectedKey]); toast.success("Activity marked as checked", { description: "The selected activity now shows a completed review state." }); }} className="rounded-xl bg-[#39e0c5] px-3 py-3 text-xs font-semibold text-[#071312] active:scale-[0.97]">{reviewed.includes(selectedKey) ? "Checked" : "Record a check"}</button><button onClick={() => onNavigate("identities")} className="rounded-xl border border-white/10 px-3 py-3 text-xs font-medium text-slate-300 hover:bg-white/5">Open profile</button></div></div>}
    </div>
  </>;
}

function IdentityProfiles() {
  const [identities, setIdentities] = useState<IdentityCard[]>([]);
  const [selected, setSelected] = useState<IdentityCard | null>(null);
  const [timeline, setTimeline] = useState<ActivityRow[]>([]);
  const [profile, setProfile] = useState<IdentityProfileResponse | null>(null);
  const [reviewed, setReviewed] = useState<string[]>([]);
  const [assessing, setAssessing] = useState(false);
  const [simulating, setSimulating] = useState(false);

  const refreshProfile = (identityId: string) =>
    getIdentityProfile(identityId)
      .then((response) => setProfile(response.data))
      .catch(() => setProfile(null));

  const refreshIdentities = () =>
    api.get<{ identities: IdentityCard[] }>("/identities").then((response) => {
      setIdentities(response.data.identities);
      // The identity-card score/activity change server-side after an
      // assessment; re-point `selected` at the refreshed object so the
      // grid highlight and "Selected profile" panel pick up the new values.
      // On first load (current is null) this also picks a default identity.
      setSelected((current) => {
        if (!current) return response.data.identities[0] ?? null;
        return response.data.identities.find((identity) => identity.identityId === current.identityId) ?? current;
      });
    });

  const handleRunAssessment = () => {
    if (!selected) return;
    const latestEvent = profile?.events[0];
    if (!latestEvent) {
      toast.error("No stored events for this identity yet", {
        description: "Create an event for this identity before running an assessment.",
      });
      return;
    }
    setAssessing(true);
    runRiskAssessment(latestEvent.eventId)
      .then((response) => {
        const { finalRiskScore } = response.data.calculation;
        toast.success("Assessment complete", {
          description: `${selected.name}: risk score ${finalRiskScore} (${response.data.severity}).`,
        });
        return Promise.all([refreshProfile(selected.identityId), refreshIdentities()]);
      })
      .catch(() => toast.error("Assessment failed", { description: "The backend is unreachable. Try again shortly." }))
      .finally(() => setAssessing(false));
  };

  const handleCreateEvent = () => {
    if (!selected) return;
    setSimulating(true);
    simulateIdentityEvent(selected.identityId)
      .then((response) => {
        toast.success("New event created", {
          description: `${response.data.cloudService} · ${response.data.action} from ${response.data.location ?? "an unfamiliar location"}. Click Run assessment to score it.`,
        });
        return refreshProfile(selected.identityId);
      })
      .catch(() => toast.error("Could not create event", { description: "The backend is unreachable. Try again shortly." }))
      .finally(() => setSimulating(false));
  };

  useEffect(() => {
    refreshIdentities().catch(() =>
      toast.error("Could not load identities", { description: "The backend is unreachable. Try again shortly." })
    );
  }, []);

  useEffect(() => {
    if (!selected) return;
    api
      .get<{ events: ActivityRow[] }>(`/identities/${encodeURIComponent(selected.identityId)}/timeline`)
      .then((response) => setTimeline(response.data.events))
      .catch(() => setTimeline([]));
    refreshProfile(selected.identityId);
  }, [selected]);

  if (!selected) {
    return <>
      <PageHeading eyebrow="Identity profiles" title="Understand the people and accounts behind the activity" description="Each profile shows what is usual for an account, what changed, and which activity needs a conversation or check." />
      <p className="mt-6 text-sm text-slate-500">Loading identities…</p>
    </>;
  }

  return <>
    <PageHeading eyebrow="Identity profiles" title="Understand the people and accounts behind the activity" description="Each profile shows what is usual for an account, what changed, and which activity needs a conversation or check." />
    <InfoStrip>The score helps you set review order. A high score does <strong className="font-semibold text-slate-100">not</strong> say someone did something wrong; it means their activity is less like their normal pattern.</InfoStrip>
    <div className="mt-6 grid gap-4 lg:grid-cols-2 2xl:grid-cols-4">{identities.map((identity) => <button onClick={() => setSelected(identity)} key={identity.identityId} className={`glass-panel cursor-pointer rounded-2xl p-5 text-left transition-all duration-150 hover:-translate-y-0.5 hover:border-orange-400/60! hover:bg-white/[0.07]! hover:shadow-lg hover:shadow-white/10! ${selected === identity ? "ring-1 ring-[#39e0c5]/60" : "hover:ring-1! hover:ring-orange-400/30!"}`}><div className="flex items-start justify-between"><div className="flex size-10 items-center justify-center rounded-xl bg-white/[0.06] text-sm font-semibold" style={{ color: identity.color }}>{identity.initials}</div><span className="mono text-lg font-semibold" style={{ color: identity.color }}>{identity.score}</span></div><h3 className="mt-4 text-sm font-semibold text-slate-100">{identity.name}</h3><p className="mt-1 text-xs text-slate-500">{identity.role}</p><p className="mt-4 text-xs leading-5 text-slate-300">{identity.activity}</p><p className="mt-3 text-[11px] text-slate-500">Click for a simple profile summary →</p></button>)}</div>
    <div className="glass-panel mt-6 grid overflow-hidden rounded-2xl lg:grid-cols-[0.9fr_1.1fr]"><div className="border-b border-white/10 p-6 lg:border-b-0 lg:border-r"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Selected profile</p><div className="mt-4 flex items-center gap-3"><div className="flex size-12 items-center justify-center rounded-xl bg-white/[0.06] text-sm font-semibold" style={{ color: selected.color }}>{selected.initials}</div><div><h3 className="font-semibold text-slate-100">{selected.name}</h3><p className="text-xs text-slate-500">{selected.role}</p></div></div><div className="mt-5 space-y-3"><div><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">What looks unusual</p><p className="mt-1 text-sm text-slate-300">{selected.activity}</p></div><div><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">What is normally expected</p><p className="mt-1 text-sm leading-6 text-slate-400">{selected.description}</p></div></div></div><div className="p-6"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Recent activity at a glance</p><div className="mt-4 space-y-3">{(timeline.length ? timeline.map((event) => event.action) : ["No recorded activity for this identity yet."]).map((item, index) => <div key={item} className="flex items-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.025] p-3"><span className={`flex size-6 items-center justify-center rounded-full ${timeline[index]?.tone === "critical" || timeline[index]?.tone === "high" ? "bg-[#f5ae45]/15 text-[#f5ae45]" : "bg-[#39e0c5]/10 text-[#39e0c5]"}`}>{timeline[index]?.tone === "critical" || timeline[index]?.tone === "high" ? <CircleAlert className="size-3.5" /> : <Check className="size-3.5" />}</span><p className="text-xs text-slate-300">{item}</p></div>)}</div>{reviewed.includes(selected.identityId) && <div className="mt-4 flex items-center gap-2 rounded-xl border border-[#39e0c5]/20 bg-[#39e0c5]/10 p-3 text-xs text-[#8af4e4]"><CheckCircle2 className="size-4" />Profile review is active for this session. Risk score: {profile?.riskSummary.latestFinalRiskScore ?? selected.score}{profile?.riskSummary.latestSeverityFloor ? ` (floor: ${profile.riskSummary.latestSeverityFloor})` : ""}.</div>}<button onClick={() => { setReviewed((current) => current.includes(selected.identityId) ? current : [...current, selected.identityId]); const score = profile?.riskSummary.latestFinalRiskScore ?? selected.score; const source = profile?.riskSummary.latestFinalRiskScore != null ? "policy + AI assessment" : "legacy card score"; toast.success("Profile review started", { description: `${selected.name} now has an active review state. Risk score: ${score} (${source}).` }); }} className="mt-5 rounded-xl bg-[#39e0c5] px-4 py-3 text-xs font-semibold text-[#071312] active:scale-[0.97]">{reviewed.includes(selected.identityId) ? "Review active" : "Start a profile review"}</button></div></div>
    {profile && <div className="glass-panel mt-6 rounded-2xl p-6"><div className="flex flex-wrap items-center justify-between gap-3"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Policy + AI risk (database-backed)</p><div className="flex gap-2"><button onClick={handleCreateEvent} disabled={simulating} className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-[11px] font-semibold text-slate-300 transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40">{simulating ? "Creating…" : "Create event"}</button><button onClick={handleRunAssessment} disabled={assessing || !profile.events[0]} className="rounded-lg border border-[#39e0c5]/30 bg-[#39e0c5]/10 px-3 py-2 text-[11px] font-semibold text-[#8af4e4] transition-colors hover:bg-[#39e0c5]/20 disabled:cursor-not-allowed disabled:opacity-40">{assessing ? "Running…" : "Run assessment"}</button></div></div>{!profile.events[0] && <p className="mt-2 text-[11px] text-slate-500">No stored security events for this identity yet — click Create event to generate one, then Run assessment to score it.</p>}<div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><div><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Baseline confidence</p><p className="mt-1 text-sm font-semibold text-slate-100">{profile.baseline ? profile.baseline.confidence : "unknown"}</p><p className="mt-1 text-[11px] text-slate-500">{profile.baseline ? `${profile.baseline.sampleCount} events across ${profile.baseline.activeDayCount} active days` : "Not enough history yet"}</p></div><div><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Policy score</p><p className="mt-1 text-sm font-semibold text-slate-100">{profile.riskSummary.latestPolicyScore ?? "—"}</p></div><div><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">AI adjustment</p><p className="mt-1 text-sm font-semibold text-slate-100">{profile.riskSummary.latestAiAdjustment ?? "—"} <span className="text-[11px] font-normal text-slate-500">({profile.riskSummary.latestAiStatus ?? "no assessment yet"})</span></p></div><div><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Final risk score</p><p className="mt-1 text-sm font-semibold text-slate-100">{profile.riskSummary.latestFinalRiskScore ?? "—"} {profile.riskSummary.latestSeverityFloor && <span className="text-[11px] font-normal text-slate-500">(floor: {profile.riskSummary.latestSeverityFloor})</span>}</p></div></div>{profile.riskSummary.matchedPolicyIds.length > 0 && <div className="mt-5"><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Matched policies (latest assessment)</p><div className="mt-2 flex flex-wrap gap-2">{profile.riskSummary.matchedPolicyIds.map((ruleId) => <span key={ruleId} className="rounded-full bg-white/[0.06] px-2.5 py-1 text-[10px] text-slate-300">{ruleId}</span>)}</div></div>}</div>}
  </>;
}

function CloudEstate() {
  const [sources, setSources] = useState<CloudSourceCard[]>([]);
  const [sourcesOnline, setSourcesOnline] = useState(0);
  const [selected, setSelected] = useState<CloudSourceCard | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    api
      .get<{ sources: CloudSourceCard[]; sourcesOnline: number }>("/estate")
      .then((response) => {
        setSources(response.data.sources);
        setSourcesOnline(response.data.sourcesOnline);
        setSelected((current) => current ?? response.data.sources[0] ?? null);
      })
      .catch(() => toast.error("Could not load cloud estate", { description: "The backend is unreachable. Try again shortly." }));
  }, []);

  if (!selected) {
    return <>
      <PageHeading eyebrow="Cloud estate" title="Check which cloud systems are connected" description="This view shows whether Sentinel is receiving activity from each important cloud system, and where the most unusual activity is happening." />
      <p className="mt-6 text-sm text-slate-500">Loading cloud sources…</p>
    </>;
  }

  return <>
    <PageHeading eyebrow="Cloud estate" title="Check which cloud systems are connected" description="This view shows whether Sentinel is receiving activity from each important cloud system, and where the most unusual activity is happening." action={<span className="mono rounded-full border border-[#39e0c5]/20 bg-[#39e0c5]/10 px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-[#79efdd]">{sourcesOnline} sources online</span>} />
    <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]"><div className="glass-panel overflow-hidden rounded-2xl"><div className="grid divide-y divide-white/[0.08]">{sources.map((source) => { const Icon = cloudSourceIcons[source.icon] ?? Cloud; return <button onClick={() => { setSelected(source); setShowDetails(false); }} key={source.name} className={`flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-white/[0.035] ${selected === source ? "bg-[#173039]/50" : ""}`}><div className="flex size-10 items-center justify-center rounded-xl bg-white/[0.05]" style={{ color: source.color }}><Icon className="size-5" /></div><div className="min-w-0 flex-1"><p className="text-sm font-medium text-slate-200">{source.name}</p><p className="mt-1 text-xs text-slate-500">{source.type} · {source.eventsToday} events today</p></div><div className="text-right"><p className="mono text-[10px] text-[#76eddb]">{source.status}</p><p className={`mt-1 text-[10px] ${source.health === "Healthy" ? "text-slate-500" : "text-[#f5ae45]"}`}>{source.health}</p></div></button>; })}</div></div><div className="glass-panel rounded-2xl p-6"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Source detail</p><h3 className="mt-2 text-lg font-semibold text-slate-100">{selected.name}</h3><p className="mt-2 text-sm leading-6 text-slate-400">Sentinel is receiving <strong className="font-medium text-slate-200">{selected.eventsToday} events</strong> from this source. Its status is <strong className="font-medium text-slate-200">{selected.health.toLowerCase()}</strong>.</p><div className="mt-6 grid grid-cols-2 gap-3"><div className="rounded-xl border border-white/10 bg-black/[0.12] p-4"><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Connected</p><p className="mt-2 text-xl font-semibold text-[#79efdd]">{selected.status === "Connected" ? "Yes" : "No"}</p></div><div className="rounded-xl border border-white/10 bg-black/[0.12] p-4"><p className="mono text-[9px] uppercase tracking-[0.12em] text-slate-600">Data freshness</p><p className="mt-2 text-xl font-semibold text-slate-100">{selected.dataFreshnessMin} min</p></div></div>{showDetails && <div className="mt-4 rounded-xl border border-[#39e0c5]/20 bg-[#39e0c5]/10 p-3 text-xs leading-5 text-slate-300"><p className="font-semibold text-[#8af4e4]">Connection detail</p><p className="mt-1">This demo source is connected through normalized synthetic audit telemetry. In production, this area would show source owner, token status, and the most recent successful fetch.</p></div>}<button onClick={() => setShowDetails((current) => !current)} className="mt-5 inline-flex items-center gap-2 text-xs font-semibold text-[#7cf0de]">{showDetails ? "Hide connection details" : "View connection details"} <ArrowUpRight className="size-3.5" /></button></div></div>
  </>;
}

function Policies() {
  const [rules, setRules] = useState<PolicyRule[]>([]);

  useEffect(() => {
    api
      .get<{ policies: PolicyRule[] }>("/policies")
      .then((response) => setRules(response.data.policies))
      .catch(() => toast.error("Could not load policies", { description: "The backend is unreachable. Try again shortly." }));
  }, []);

  const toggle = (title: string) => {
    api
      .post<PolicyRule>(`/policies/${encodeURIComponent(title)}/toggle`)
      .then((response) => {
        setRules((current) => current.map((rule) => (rule.title === title ? response.data : rule)));
      })
      .catch(() => toast.error("Could not update policy", { description: "The backend is unreachable. Try again shortly." }));
  };

  return <>
    <PageHeading eyebrow="Policies" title="Choose what Sentinel should point out" description="Policies are simple rules that help the dashboard decide what activity deserves attention. Turn a rule on to include it in the daily review." />
    <InfoStrip>Keep policies understandable: describe the behavior, explain why it matters, and decide who should review it. The aim is useful reminders, not noisy alerts.</InfoStrip>
    <div className="mt-6 grid gap-4">{rules.map((rule) => <div key={rule.title} className="glass-panel flex flex-col gap-4 rounded-2xl p-5 sm:flex-row sm:items-center"><div className="flex min-w-0 flex-1 gap-4"><div className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${rule.enabled ? "bg-[#39e0c5]/12 text-[#39e0c5]" : "bg-white/[0.05] text-slate-500"}`}><ShieldCheck className="size-5" /></div><div><div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold text-slate-100">{rule.title}</h3><span className="rounded-full bg-white/[0.05] px-2 py-0.5 text-[9px] text-slate-500">{rule.category}</span></div><p className="mt-1.5 max-w-2xl text-xs leading-5 text-slate-400">{rule.description}</p></div></div><button aria-label={`Toggle ${rule.title}`} onClick={() => toggle(rule.title)} className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${rule.enabled ? "bg-[#39e0c5]" : "bg-white/[0.12]"}`}><span className={`absolute top-1 size-5 rounded-full bg-white shadow transition-transform ${rule.enabled ? "translate-x-6" : "translate-x-1"}`} /></button></div>)}</div>
  </>;
}

function Reports({ onExport }: { onExport: () => void }) {
  const [reports, setReports] = useState<ReportTemplate[]>([]);
  const [prepared, setPrepared] = useState<string[]>([]);
  const [preparing, setPreparing] = useState<string | null>(null);
  const [narratives, setNarratives] = useState<Record<string, string | null>>({});

  useEffect(() => {
    api
      .get<{ reports: ReportTemplate[] }>("/reports")
      .then((response) => setReports(response.data.reports))
      .catch(() => toast.error("Could not load reports", { description: "The backend is unreachable. Try again shortly." }));
  }, []);

  const prepare = (title: string) => {
    setPreparing(title);
    api
      .post<{ narrative: string | null }>(`/reports/${encodeURIComponent(title)}/prepare`)
      .then((response) => {
        setPrepared((current) => current.includes(title) ? current : [...current, title]);
        setNarratives((current) => ({ ...current, [title]: response.data.narrative }));
        toast.success("Report prepared", { description: `${title} is now marked ready to share in this session.` });
      })
      .catch(() => toast.error("Could not prepare report", { description: "The backend is unreachable. Try again shortly." }))
      .finally(() => setPreparing(null));
  };

  return <>
    <PageHeading eyebrow="Reports" title="Share a clear security update" description="Create simple summaries for teammates, judges, or managers. Every report in this demo uses synthetic telemetry and plain-language explanations." action={<button onClick={onExport} className="inline-flex items-center gap-2 rounded-xl bg-[#39e0c5] px-4 py-3 text-xs font-semibold text-[#071312] active:scale-[0.97]"><ArrowDownToLine className="size-4" />Export activity CSV</button>} />
    <div className="mt-6 grid gap-4 lg:grid-cols-3">{reports.map((report) => <div key={report.title} className="glass-panel rounded-2xl p-5"><div className="flex items-start justify-between"><div className="flex size-10 items-center justify-center rounded-xl bg-[#39e0c5]/10 text-[#39e0c5]"><FileText className="size-5" /></div><span className="mono text-[9px] uppercase tracking-[0.1em] text-slate-600">{report.period}</span></div><h3 className="mt-5 text-base font-semibold tracking-tight text-slate-100">{report.title}</h3><p className="mt-2 text-sm leading-6 text-slate-400">{report.detail}</p><p className="mt-5 mono text-[10px] uppercase tracking-[0.12em] text-[#76eddb]">{report.type}</p>{prepared.includes(report.title) && <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-[#8af4e4]"><CheckCircle2 className="size-3.5" />Ready to share</p>}{narratives[report.title] && <div className="mt-3 rounded-xl border border-[#39e0c5]/15 bg-[#10242a]/35 p-3"><p className="text-xs leading-5 text-slate-300">{narratives[report.title]}</p></div>}<button onClick={() => prepare(report.title)} disabled={preparing === report.title} className="mt-5 text-xs font-semibold text-[#79efdd] disabled:opacity-50">{preparing === report.title ? "Preparing…" : prepared.includes(report.title) ? "Prepared for sharing" : "Prepare report →"}</button></div>)}</div>
    <div className="glass-panel mt-6 rounded-2xl p-6"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">A useful update has three parts</p><div className="mt-4 grid gap-4 sm:grid-cols-3"><div><p className="text-sm font-semibold text-slate-200">What changed?</p><p className="mt-1 text-xs leading-5 text-slate-500">Summarize the unusual activity in one plain sentence.</p></div><div><p className="text-sm font-semibold text-slate-200">Why should we care?</p><p className="mt-1 text-xs leading-5 text-slate-500">Show the reason it differs from usual behavior.</p></div><div><p className="text-sm font-semibold text-slate-200">What happens next?</p><p className="mt-1 text-xs leading-5 text-slate-500">Record the person responsible for checking the item.</p></div></div></div>
  </>;
}

function Configuration({ onNavigate }: { onNavigate: (view: WorkspaceKey) => void }) {
  const [notifications, setNotifications] = useState(true);
  const [plainLanguage, setPlainLanguage] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .get<{ notificationsEnabled: boolean; plainLanguageExplanations: boolean }>("/configuration")
      .then((response) => {
        setNotifications(response.data.notificationsEnabled);
        setPlainLanguage(response.data.plainLanguageExplanations);
      })
      .catch(() => toast.error("Could not load settings", { description: "The backend is unreachable. Try again shortly." }));
  }, []);

  const save = () => {
    api
      .put("/configuration", { notificationsEnabled: notifications, plainLanguageExplanations: plainLanguage })
      .then(() => {
        setSaved(true);
        toast.success("Settings saved", { description: "Your preferences have been stored by the backend." });
      })
      .catch(() => toast.error("Could not save settings", { description: "The backend is unreachable. Try again shortly." }));
  };

  return <>
    <PageHeading eyebrow="Configuration" title="Set up a calm, useful review experience" description="These preferences control how the demo presents information. They do not change the synthetic source data." />
    <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(340px,0.65fr)]"><div className="glass-panel rounded-2xl p-6"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Review preferences</p><div className="mt-5 divide-y divide-white/[0.08]">{[{ label: "Notify me about urgent activity", description: "Show a notification when a red, high-priority item appears.", state: notifications, set: setNotifications }, { label: "Use plain-language explanations", description: "Explain security activity in everyday language wherever possible.", state: plainLanguage, set: setPlainLanguage }].map((preference) => <div key={preference.label} className="flex items-center gap-4 py-5 first:pt-0"><div className="flex-1"><p className="text-sm font-medium text-slate-200">{preference.label}</p><p className="mt-1 text-xs leading-5 text-slate-500">{preference.description}</p></div><button aria-label={`Toggle ${preference.label}`} onClick={() => { preference.set(!preference.state); setSaved(false); }} className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${preference.state ? "bg-[#39e0c5]" : "bg-white/[0.12]"}`}><span className={`absolute top-1 size-5 rounded-full bg-white shadow transition-transform ${preference.state ? "translate-x-6" : "translate-x-1"}`} /></button></div>)}</div><button onClick={save} className="mt-6 rounded-xl bg-[#39e0c5] px-4 py-3 text-xs font-semibold text-[#071312] active:scale-[0.97]">{saved ? "Saved" : "Save preferences"}</button></div><div className="glass-panel rounded-2xl p-6"><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Demo environment</p><div className="mt-5 space-y-4"><div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-[#39e0c5]" /><p className="text-sm font-medium text-slate-200">Synthetic telemetry enabled</p></div><p className="mt-2 text-xs leading-5 text-slate-500">This protects privacy during your hackathon presentation while still showing a realistic workflow.</p></div><div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex items-center gap-2"><Cloud className="size-4 text-[#39e0c5]" /><p className="text-sm font-medium text-slate-200">8 data sources normalized</p></div><p className="mt-2 text-xs leading-5 text-slate-500">Connect live cloud logs here when you are ready to move past the demo.</p></div></div><button onClick={() => onNavigate("estate")} className="mt-5 text-xs font-semibold text-[#79efdd]">View connected cloud sources →</button></div></div>
  </>;
}
