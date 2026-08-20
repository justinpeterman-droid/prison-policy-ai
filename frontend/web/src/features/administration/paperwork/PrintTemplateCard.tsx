import type { MonthlyTemplateDefinition, PrintTemplateCode } from "../../../print/print-registry";

interface PrintTemplateCardProps { definition: MonthlyTemplateDefinition; selected: boolean; onSelect(code: PrintTemplateCode): void; onPreview(code: PrintTemplateCode): void; onPrint(code: PrintTemplateCode): void; }

export function PrintTemplateCard({ definition, selected, onSelect, onPreview, onPrint }: PrintTemplateCardProps) {
  return <article className="print-template-card" data-testid="monthly-template-card"><label><input type="checkbox" checked={selected} onChange={() => onSelect(definition.code)} aria-label={`Select ${definition.title}`} /> Include in monthly packet</label><h2>{definition.title}</h2><p>{definition.description}</p><div><button type="button" className="admin-secondary-button" onClick={() => onPreview(definition.code)}>Preview {definition.title.replace("Use of ", "").replace(" Log", "")}</button><button type="button" className="admin-primary-button" onClick={() => onPrint(definition.code)}>Print</button></div></article>;
}
