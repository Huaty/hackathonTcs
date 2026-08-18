/** Signal Room reminder: reveal data provenance plainly; imported hackathon data stays local to the browser and never pretends to be a live integration. */
import { useRef, useState } from "react";
import { toast } from "sonner";
import { ArrowRight, CheckCircle2, Database, FileJson2, FileSpreadsheet, ShieldCheck, Trash2, Upload } from "lucide-react";

export type ImportedDataset = {
  fileName: string;
  format: "CSV" | "JSON";
  records: Record<string, unknown>[];
  fields: string[];
  importedAt: string;
};

type DatasetImporterProps = {
  dataset: ImportedDataset | null;
  onDataset: (dataset: ImportedDataset) => void;
  onClear: () => void;
  onOpenExplorer: () => void;
};

function parseCsvLine(line: string) {
  const result: string[] = [];
  let cell = "";
  let inQuotes = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (character === '"' && line[index + 1] === '"') { cell += '"'; index += 1; }
    else if (character === '"') inQuotes = !inQuotes;
    else if (character === "," && !inQuotes) { result.push(cell.trim()); cell = ""; }
    else cell += character;
  }
  result.push(cell.trim());
  return result;
}

function parseCsv(text: string) {
  const rows = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter((line) => line.trim());
  if (rows.length < 2) throw new Error("A CSV file needs a header row and at least one data row.");
  const fields = parseCsvLine(rows[0]).filter(Boolean);
  if (!fields.length) throw new Error("The CSV header row is empty.");
  const records = rows.slice(1).map((line) => {
    const values = parseCsvLine(line);
    return fields.reduce<Record<string, unknown>>((record, field, index) => ({ ...record, [field]: values[index] ?? "" }), {});
  });
  return { records, fields };
}

function parseJson(text: string) {
  const parsed = JSON.parse(text) as unknown;
  const possibleRecords = Array.isArray(parsed) ? parsed : (typeof parsed === "object" && parsed !== null ? ((parsed as Record<string, unknown>).records ?? (parsed as Record<string, unknown>).events ?? (parsed as Record<string, unknown>).data) : null);
  if (!Array.isArray(possibleRecords) || !possibleRecords.length) throw new Error("The JSON file must contain an array, or an events, records, or data array.");
  const records = possibleRecords.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null && !Array.isArray(item));
  if (!records.length) throw new Error("No object records were found in the JSON array.");
  const fields = Array.from(new Set(records.flatMap((record) => Object.keys(record))));
  return { records, fields };
}

export default function DatasetImporter({ dataset, onDataset, onClear, onOpenExplorer }: DatasetImporterProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  const handleFile = async (file: File) => {
    setBusy(true);
    try {
      const text = await file.text();
      const format = file.name.toLowerCase().endsWith(".json") ? "JSON" : "CSV";
      const parsed = format === "JSON" ? parseJson(text) : parseCsv(text);
      if (parsed.records.length > 10000) throw new Error("Please use a dataset with 10,000 records or fewer for this browser-only demo.");
      onDataset({ fileName: file.name, format, records: parsed.records, fields: parsed.fields, importedAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) });
      toast.success("Dataset loaded in this browser", { description: `${parsed.records.length.toLocaleString()} records are available in Activity Explorer.` });
    } catch (error) {
      toast.error("We could not read that dataset", { description: error instanceof Error ? error.message : "Choose a valid CSV or JSON file." });
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return <section className="glass-panel mt-6 overflow-hidden rounded-2xl">
    <div className="flex flex-col gap-4 border-b border-white/10 p-5 sm:flex-row sm:items-start sm:justify-between sm:p-6"><div><p className="mono text-[10px] uppercase tracking-[0.14em] text-[#76eddb]">Dataset workspace</p><h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-100">Bring your own sample access logs</h3><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Use a CSV or JSON export to populate the Activity Explorer for this browser session. The file is read locally and is not uploaded, saved, or sent to a server.</p></div>{dataset ? <span className="inline-flex items-center gap-2 rounded-full border border-[#39e0c5]/20 bg-[#39e0c5]/10 px-3 py-1.5 text-xs font-semibold text-[#8cf5e5]"><CheckCircle2 className="size-3.5" />Dataset loaded</span> : <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400">Optional demo input</span>}</div>
    <div className="grid divide-y divide-white/[0.08] lg:grid-cols-3 lg:divide-x lg:divide-y-0"><div className="p-5 sm:p-6"><span className="flex size-9 items-center justify-center rounded-xl bg-[#39e0c5]/10 text-[#39e0c5]"><FileSpreadsheet className="size-4" /></span><p className="mt-4 text-sm font-semibold text-slate-200">1. Choose a file</p><p className="mt-1 text-xs leading-5 text-slate-500">CSV files need a header row. JSON files should be an array of records or have an <span className="mono text-slate-400">events</span>, <span className="mono text-slate-400">records</span>, or <span className="mono text-slate-400">data</span> array.</p></div><div className="p-5 sm:p-6"><span className="flex size-9 items-center justify-center rounded-xl bg-[#39e0c5]/10 text-[#39e0c5]"><Database className="size-4" /></span><p className="mt-4 text-sm font-semibold text-slate-200">2. Inspect in the explorer</p><p className="mt-1 text-xs leading-5 text-slate-500">Imported records replace the built-in list in Activity Explorer. The current dashboard cards continue to use synthetic demo baselines.</p></div><div className="p-5 sm:p-6"><span className="flex size-9 items-center justify-center rounded-xl bg-[#39e0c5]/10 text-[#39e0c5]"><ShieldCheck className="size-4" /></span><p className="mt-4 text-sm font-semibold text-slate-200">3. Understand the boundary</p><p className="mt-1 text-xs leading-5 text-slate-500">Refresh the page and the imported file disappears. A real deployment needs protected cloud storage and a backend ingestion service.</p></div></div>
    <div className="flex flex-col gap-3 border-t border-white/[0.08] bg-black/[0.08] p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">{dataset ? <div className="min-w-0"><p className="truncate text-sm font-medium text-slate-200">{dataset.fileName}</p><p className="mt-1 text-xs text-slate-500">{dataset.records.length.toLocaleString()} records · {dataset.fields.length} fields · {dataset.format} · loaded at {dataset.importedAt}</p></div> : <p className="text-xs leading-5 text-slate-500">No file is loaded. Sentinel is currently displaying built-in synthetic demo telemetry.</p>}<div className="flex flex-wrap gap-2"><input ref={inputRef} onChange={(event) => event.target.files?.[0] && handleFile(event.target.files[0])} accept=".csv,.json,application/json,text/csv" type="file" className="hidden" /><button onClick={() => inputRef.current?.click()} disabled={busy} className="inline-flex items-center gap-2 rounded-xl bg-[#39e0c5] px-4 py-2.5 text-xs font-semibold text-[#071312] disabled:opacity-60"><Upload className="size-3.5" />{busy ? "Reading file…" : dataset ? "Replace dataset" : "Choose CSV or JSON"}</button>{dataset && <><button onClick={onOpenExplorer} className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-white/5">Open Activity Explorer <ArrowRight className="size-3.5" /></button><button onClick={() => { onClear(); toast.info("Dataset removed", { description: "The Activity Explorer has returned to built-in synthetic demo telemetry." }); }} className="rounded-xl border border-white/10 p-2.5 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="Remove current dataset"><Trash2 className="size-3.5" /></button></>}</div></div>
  </section>;
}
