import { useMemo, useState } from "react";
import { MONTHLY_PRINT_TEMPLATES, type MonthlyPrintPrefill, type PrintTemplateCode } from "../../../print/print-registry";
import { PrintPacketBuilder } from "./PrintPacketBuilder";
import { PrintTemplateCard } from "./PrintTemplateCard";
import { PrintTemplatePreview } from "./PrintTemplatePreview";

interface MonthlyPaperworkTabProps { onPrint?: () => void; }
function currentMonth() { return new Date().toLocaleDateString("en-CA", { year: "numeric", month: "2-digit" }); }

export function MonthlyPaperworkTab({ onPrint = () => window.print() }: MonthlyPaperworkTabProps) {
  const [month, setMonth] = useState(currentMonth); const [shift, setShift] = useState("D"); const [selected, setSelected] = useState<PrintTemplateCode[]>([]); const [preview, setPreview] = useState<PrintTemplateCode | "packet">("monthly_windows_bars_doors");
  const prefill: MonthlyPrintPrefill = { month, shift };
  const selectedDefinitions = useMemo(() => selected.map((code) => MONTHLY_PRINT_TEMPLATES.find((definition) => definition.code === code)).filter((definition): definition is typeof MONTHLY_PRINT_TEMPLATES[number] => Boolean(definition)), [selected]);
  const previewDefinition = MONTHLY_PRINT_TEMPLATES.find((definition) => definition.code === preview) ?? MONTHLY_PRINT_TEMPLATES[0];
  function toggle(code: PrintTemplateCode) { setSelected((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code]); }
  function move(code: PrintTemplateCode, direction: -1 | 1) { setSelected((current) => { const index = current.indexOf(code); const target = index + direction; if (index < 0 || target < 0 || target >= current.length) return current; const next = [...current]; [next[index], next[target]] = [next[target], next[index]]; return next; }); }
  return <section id="paperwork-panel-monthly" role="tabpanel" aria-labelledby="paperwork-tab-monthly" className="monthly-paperwork"><div className="paperwork-filters"><label>Month<input aria-label="Month" type="month" value={month} onChange={(event) => setMonth(event.target.value)} /></label><label>Shift<input aria-label="Shift" value={shift} maxLength={32} onChange={(event) => setShift(event.target.value)} /></label></div><div className="monthly-template-grid">{MONTHLY_PRINT_TEMPLATES.map((definition) => <PrintTemplateCard key={definition.code} definition={definition} selected={selected.includes(definition.code)} onSelect={toggle} onPreview={setPreview} onPrint={onPrint} />)}</div><div className="monthly-selection-actions"><button type="button" className="admin-secondary-button" disabled={!selected.length} onClick={() => setPreview("packet")}>Preview Monthly Packet ({selected.length})</button><button type="button" className="admin-primary-button" disabled={!selected.length} onClick={onPrint}>Print Monthly Packet</button><button type="button" disabled={!selected.length} onClick={() => setSelected([])}>Clear selection</button></div>{preview === "packet" && selectedDefinitions.length ? <PrintPacketBuilder definitions={selectedDefinitions} prefill={prefill} onMove={move} /> : <PrintTemplatePreview definition={previewDefinition} prefill={prefill} />}</section>;
}
