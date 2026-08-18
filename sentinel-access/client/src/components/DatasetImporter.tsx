/** Signal Room reminder: reveal data provenance plainly; imported datasets are now validated and stored by the backend, not parsed purely in-browser. */
import { useRef, useState } from "react";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { ArrowRight, CheckCircle2, Database, FileSpreadsheet, ShieldCheck, Trash2, Upload } from "lucide-react";

export type ImportedDataset = {
  fileName: string;
  acceptedCount: number;
  rejectedCount: number;
  errors: string[];
  importedAt: string;
};

type DatasetImporterProps = {
  dataset: ImportedDataset | null;
  onDataset: (dataset: ImportedDataset) => void;
  onClear: () => void;
  onOpenExplorer: () => void;
};

export default function DatasetImporter({ dataset, onDataset, onClear, onOpenExplorer }: DatasetImporterProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  const handleFile = async (file: File) => {
    setBusy(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.post<{ acceptedCount: number; rejectedCount: number; errors: string[] }>(
        "/datasets",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      const { acceptedCount, rejectedCount, errors } = response.data;
      onDataset({
        fileName: file.name,
        acceptedCount,
        rejectedCount,
        errors,
        importedAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      });
      toast.success("Dataset imported by the backend", {
        description: `${acceptedCount.toLocaleString()} records accepted${rejectedCount ? `, ${rejectedCount.toLocaleString()} rejected` : ""}. Open Activity Explorer to view them.`,
      });
    } catch (error) {
      const message = isAxiosError(error) && error.response?.data?.detail
        ? String(error.response.data.detail)
        : "The backend rejected or could not reach that file. Choose a valid CSV or JSON file.";
      toast.error("We could not import that dataset", { description: message });
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return <section className="glass-panel mt-6 overflow-hidden rounded-2xl">
    <div className="flex flex-col gap-4 border-b border-white/10 p-5 sm:flex-row sm:items-start sm:justify-between sm:p-6"><div><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Dataset workspace</p><h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-100">Bring your own sample access logs</h3><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Use a CSV or JSON export to populate the Activity Explorer. The file is validated and stored by the Sentinel Access backend, in memory, for this session.</p></div>{dataset ? <span className="inline-flex items-center gap-2 rounded-full border border-[#39e0c5]/20 bg-[#39e0c5]/10 px-3 py-1.5 text-xs font-semibold text-[#8cf5e5]"><CheckCircle2 className="size-3.5" />Dataset loaded</span> : <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400">Optional demo input</span>}</div>
    <div className="grid divide-y divide-white/[0.08] lg:grid-cols-3 lg:divide-x lg:divide-y-0"><div className="p-5 sm:p-6"><span className="flex size-9 items-center justify-center rounded-xl bg-[#39e0c5]/10 text-[#39e0c5]"><FileSpreadsheet className="size-4" /></span><p className="mt-4 text-sm font-semibold text-slate-200">1. Choose a file</p><p className="mt-1 text-xs leading-5 text-slate-500">CSV files need a header row. JSON files should be an array of records or have an <span className="mono text-slate-400">events</span>, <span className="mono text-slate-400">records</span>, or <span className="mono text-slate-400">data</span> array.</p></div><div className="p-5 sm:p-6"><span className="flex size-9 items-center justify-center rounded-xl bg-[#39e0c5]/10 text-[#39e0c5]"><Database className="size-4" /></span><p className="mt-4 text-sm font-semibold text-slate-200">2. Inspect in the explorer</p><p className="mt-1 text-xs leading-5 text-slate-500">Imported records replace the built-in list in Activity Explorer. The current dashboard cards continue to use synthetic demo baselines.</p></div><div className="p-5 sm:p-6"><span className="flex size-9 items-center justify-center rounded-xl bg-[#39e0c5]/10 text-[#39e0c5]"><ShieldCheck className="size-4" /></span><p className="mt-4 text-sm font-semibold text-slate-200">3. Understand the boundary</p><p className="mt-1 text-xs leading-5 text-slate-500">The backend keeps this dataset in memory only. Restarting the backend service returns to the built-in synthetic demo data.</p></div></div>
    <div className="flex flex-col gap-3 border-t border-white/[0.08] bg-black/[0.08] p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">{dataset ? <div className="min-w-0"><p className="truncate text-sm font-medium text-slate-200">{dataset.fileName}</p><p className="mt-1 text-xs text-slate-500">{dataset.acceptedCount.toLocaleString()} records accepted{dataset.rejectedCount ? ` · ${dataset.rejectedCount.toLocaleString()} rejected` : ""} · loaded at {dataset.importedAt}</p></div> : <p className="text-xs leading-5 text-slate-500">No file is loaded. Sentinel is currently displaying built-in synthetic demo telemetry.</p>}<div className="flex flex-wrap gap-2"><input ref={inputRef} onChange={(event) => event.target.files?.[0] && handleFile(event.target.files[0])} accept=".csv,.json,application/json,text/csv" type="file" className="hidden" /><button onClick={() => inputRef.current?.click()} disabled={busy} className="inline-flex items-center gap-2 rounded-xl bg-[#39e0c5] px-4 py-2.5 text-xs font-semibold text-[#071312] disabled:opacity-60"><Upload className="size-3.5" />{busy ? "Uploading…" : dataset ? "Replace dataset" : "Choose CSV or JSON"}</button>{dataset && <><button onClick={onOpenExplorer} className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-white/5">Open Activity Explorer <ArrowRight className="size-3.5" /></button><button onClick={() => { onClear(); toast.info("Dataset reference cleared", { description: "This only clears the local summary card; use the backend to reset the underlying activity log." }); }} className="rounded-xl border border-white/10 p-2.5 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="Clear dataset summary"><Trash2 className="size-3.5" /></button></>}</div></div>
  </section>;
}
