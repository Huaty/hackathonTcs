import { useState, type FormEvent } from "react";
import { Sparkles, X } from "lucide-react";
import { queryCopilot } from "@/lib/api";

type CopilotPanelProps = {
  open: boolean;
  onClose: () => void;
};

type CopilotState = {
  answer: string;
  findings: Record<string, unknown>[];
  activity: Record<string, unknown>[];
  identities: Record<string, unknown>[];
} | null;

function summarizeRecord(record: Record<string, unknown>): string {
  if (typeof record.title === "string" && typeof record.id === "string") return `${record.id} · ${record.title}`;
  if (typeof record.actor === "string" && typeof record.action === "string") return `${record.actor} · ${record.action}`;
  if (typeof record.name === "string") return record.name;
  return JSON.stringify(record);
}

export default function CopilotPanel({ open, onClose }: CopilotPanelProps) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CopilotState>(null);
  const [error, setError] = useState(false);

  if (!open) return null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(false);
    queryCopilot(question.trim())
      .then((response) => setResult(response.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  const recordGroups: { label: string; records: Record<string, unknown>[] }[] = result
    ? [
        { label: "Findings", records: result.findings },
        { label: "Activity", records: result.activity },
        { label: "Identities", records: result.identities },
      ].filter((group) => group.records.length > 0)
    : [];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-[#02070b]/55 backdrop-blur-[2px]" role="dialog" aria-modal="true" aria-label="Ask Sentinel copilot">
      <aside className="h-full w-full max-w-[480px] overflow-y-auto border-l border-white/10 bg-[#0d1620] shadow-[-24px_0_70px_rgba(0,0,0,0.35)]">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#0d1620]/95 px-5 py-4 backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-xl bg-[#39e0c5]/12 text-[#39e0c5]">
              <Sparkles className="size-4" />
            </div>
            <div>
              <p className="mono text-[10px] uppercase tracking-[0.13em] text-slate-500">AI copilot</p>
              <p className="text-sm font-medium text-slate-100">Ask Sentinel</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="Close Ask Sentinel">
            <X className="size-5" />
          </button>
        </div>

        <div className="p-5 sm:p-6">
          <form onSubmit={submit} className="flex gap-2">
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="e.g. show me high-risk findings on AWS IAM"
              className="h-10 flex-1 rounded-lg border border-white/10 bg-white/[0.03] px-3 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-[#39e0c5]/50"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-[#39e0c5] px-4 py-2 text-xs font-semibold text-[#071312] transition-transform active:scale-[0.97] disabled:opacity-50"
            >
              Ask
            </button>
          </form>

          <div className="mt-6">
            {loading && <p className="text-sm text-slate-400">Thinking…</p>}
            {!loading && error && (
              <p className="text-sm text-[#ff9ba1]">Could not reach the AI assistant. The backend may be unreachable — try again shortly.</p>
            )}
            {!loading && !error && result && (
              <div className="rounded-xl border border-[#39e0c5]/15 bg-[#10242a]/35 p-4">
                <p className="text-sm leading-6 text-slate-200">{result.answer}</p>
              </div>
            )}
            {!loading && !error && result &&
              recordGroups.map((group) => (
                <div key={group.label} className="mt-5">
                  <p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">{group.label}</p>
                  <div className="mt-2 space-y-2">
                    {group.records.map((record, index) => (
                      <div key={index} className="rounded-lg border border-white/[0.08] bg-white/[0.025] px-3 py-2 text-xs text-slate-300">
                        {summarizeRecord(record)}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </div>
      </aside>
    </div>
  );
}
