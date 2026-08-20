import { PrintPacket } from "../../../print/PrintPacket";
import { printRegistry, type MonthlyPrintPrefill, type MonthlyTemplateDefinition, type PrintTemplateCode } from "../../../print/print-registry";

interface PrintPacketBuilderProps { definitions: readonly MonthlyTemplateDefinition[]; prefill: MonthlyPrintPrefill; onMove(code: PrintTemplateCode, direction: -1 | 1): void; }
export function PrintPacketBuilder({ definitions, prefill, onMove }: PrintPacketBuilderProps) {
  return <section className="print-packet-builder" aria-label="Monthly packet preview"><h2>Monthly packet</h2><p>Includes {definitions.map((definition) => definition.title).join("; ")}. Month {prefill.month}, shift {prefill.shift}.</p><ol>{definitions.map((definition, index) => <li key={definition.code}><span>{definition.title}</span><button type="button" disabled={index === 0} onClick={() => onMove(definition.code, -1)} aria-label={`Move ${definition.title} up`}><InterfaceIcon name="arrow-up" /></button><button type="button" disabled={index === definitions.length - 1} onClick={() => onMove(definition.code, 1)} aria-label={`Move ${definition.title} down`}><InterfaceIcon name="arrow-down" /></button></li>)}</ol><PrintPacket>{definitions.map((definition) => { const Component = printRegistry[definition.code]; return <Component key={definition.code} definition={definition} prefill={prefill} />; })}</PrintPacket></section>;
}
import { InterfaceIcon } from "../../../components/InterfaceIcon";
