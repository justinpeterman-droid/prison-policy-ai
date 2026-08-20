import { PrintDocument } from "../../../../print/PrintDocument";
import type { PrintComponentProps } from "../../../../print/print-registry";

export function ChemicalAgentsPrint({ definition, prefill }: PrintComponentProps) {
  return <PrintDocument title={definition.title}>
    <header className="print-document__header"><h1>{definition.title}</h1><dl><div><dt>Month</dt><dd>{prefill.month}</dd></div><div><dt>Shift supervisor</dt><dd>{prefill.shiftSupervisor || ""}</dd></div></dl></header>
    <table className="paper-log-table"><thead><tr>{definition.definition.columns.map((column) => <th key={column} scope="col">{column}</th>)}</tr></thead><tbody>{Array.from({ length: 12 }, (_, index) => <tr key={index}>{definition.definition.columns.map((column) => <td key={column} />)}</tr>)}</tbody></table>
    <section className="paper-review-grid" aria-label="Required reviews"><p>COS Review / Date</p><p>Warden Review / Date</p></section>
  </PrintDocument>;
}
