import { useEffect, useMemo, useState } from "react";
import { type MonthlyPrintPrefill, type MonthlyTemplateDefinition, type PrintTemplateCode } from "../../../print/print-registry";
import { fetchMonthlyPrintTemplates, recordPrintTemplateAction } from "./api";
import { PrintPacketBuilder } from "./PrintPacketBuilder";
import { PrintTemplateCard } from "./PrintTemplateCard";
import { PrintTemplatePreview } from "./PrintTemplatePreview";

interface MonthlyPaperworkTabProps { onPrint?: () => void; }
function currentMonth() { return new Date().toLocaleDateString("en-CA", { year: "numeric", month: "2-digit" }); }

export function MonthlyPaperworkTab({ onPrint = () => window.print() }: MonthlyPaperworkTabProps) {
  const [month, setMonth] = useState(currentMonth); const [shift, setShift] = useState("D"); const [definitions, setDefinitions] = useState<MonthlyTemplateDefinition[]>([]); const [selected, setSelected] = useState<PrintTemplateCode[]>([]); const [preview, setPreview] = useState<PrintTemplateCode | "packet" | null>(null); const [error, setError] = useState<string | null>(null);
  useEffect(() => { let active = true; void fetchMonthlyPrintTemplates().then((items) => { if (active) { setDefinitions(items); setPreview(items[0]?.code ?? null); } }).catch(() => { if (active) setError("Monthly templates could not be loaded. Try again shortly."); }); return () => { active = false; }; }, []);
  const prefill: MonthlyPrintPrefill = { month, shift };
  const selectedDefinitions = useMemo(() => selected.map((code) => definitions.find((definition) => definition.code === code)).filter((definition): definition is MonthlyTemplateDefinition => Boolean(definition)), [definitions, selected]);
  const previewDefinition = definitions.find((definition) => definition.code === preview) ?? null;
  function toggle(code: PrintTemplateCode) { setSelected((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code]); }
  function move(code: PrintTemplateCode, direction: -1 | 1) { setSelected((current) => { const index = current.indexOf(code); const target = index + direction; if (index < 0 || target < 0 || target >= current.length) return current; const next = [...current]; [next[index], next[target]] = [next[target], next[index]]; return next; }); }
  async function print(codes: PrintTemplateCode[]) { await recordPrintTemplateAction(codes, "print"); onPrint(); }
  function previewTemplate(code: PrintTemplateCode) { setPreview(code); void recordPrintTemplateAction([code], "preview"); }
  return <section id="paperwork-panel-monthly" role="tabpanel" aria-labelledby="paperwork-tab-monthly" className="monthly-paperwork"><div className="paperwork-filters"><label>Month<input aria-label="Month" type="month" value={month} onChange={(event) => setMonth(event.target.value)} /></label><label>Shift<input aria-label="Shift" value={shift} maxLength={32} onChange={(event) => setShift(event.target.value)} /></label></div>{error ? <div className="admin-alert error" role="alert">{error}</div> : null}<div className="monthly-template-grid">{definitions.map((definition) => <PrintTemplateCard key={definition.code} definition={definition} selected={selected.includes(definition.code)} onSelect={toggle} onPreview={previewTemplate} onPrint={(code) => void print([code])} />)}</div><div className="monthly-selection-actions"><button type="button" className="admin-secondary-button" disabled={!selected.length} onClick={() => setPreview("packet")}>Preview Monthly Packet ({selected.length})</button><button type="button" className="admin-primary-button" disabled={!selected.length} onClick={() => void print(selected)}>Print Monthly Packet</button><button type="button" disabled={!selected.length} onClick={() => setSelected([])}>Clear selection</button></div>{preview === "packet" && selectedDefinitions.length ? <PrintPacketBuilder definitions={selectedDefinitions} prefill={prefill} onMove={move} /> : previewDefinition ? <PrintTemplatePreview definition={previewDefinition} prefill={prefill} /> : <div className="admin-loading-panel" aria-busy="true">Loading approved monthly templates…</div>}</section>;
}
