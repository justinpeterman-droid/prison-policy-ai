import { PrintDocument } from "../../../../print/PrintDocument";
import type { PrintComponentProps } from "../../../../print/print-registry";

export function ContrabandSearchPrint({ definition, prefill }: PrintComponentProps) {
  const schedule = definition.definition.schedule ?? [];
  return <PrintDocument title={definition.title}>
    <header className="print-document__header"><h1>{definition.title}</h1><dl><div><dt>Month</dt><dd>{prefill.month}</dd></div><div><dt>Shift</dt><dd>{prefill.shift}</dd></div></dl></header>
    <table className="paper-log-table"><thead><tr>{definition.definition.columns.map((column) => <th key={column} scope="col">{column}</th>)}</tr></thead><tbody>{schedule.map((area) => <tr key={area}><td /><th scope="row">{area}</th>{definition.definition.columns.slice(2).map((column) => <td key={column} />)}</tr>)}</tbody></table>
    <section className="paper-comments"><h2>Additional Comments</h2><div aria-label="Additional Comments area" /></section>
  </PrintDocument>;
}
