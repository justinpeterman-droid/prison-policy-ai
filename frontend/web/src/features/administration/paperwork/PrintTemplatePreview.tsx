import { useState } from "react";
import { printRegistry, type MonthlyPrintPrefill, type MonthlyTemplateDefinition } from "../../../print/print-registry";

interface PrintTemplatePreviewProps { definition: MonthlyTemplateDefinition; prefill: MonthlyPrintPrefill; }
export function PrintTemplatePreview({ definition, prefill }: PrintTemplatePreviewProps) {
  const [zoom, setZoom] = useState(100); const Component = printRegistry[definition.code];
  return <section className="print-preview" aria-label="Print preview"><div className="print-preview__tools"><span>Page 1 of 1</span><label>Zoom<select value={zoom} onChange={(event) => setZoom(Number(event.target.value))}><option value={80}>80%</option><option value={100}>100%</option><option value={125}>125%</option></select></label></div><div className="print-preview__canvas" style={{ "--print-zoom": zoom / 100 } as React.CSSProperties}><Component definition={definition} prefill={prefill} /></div></section>;
}
