import { PrintDocument } from "../../../../print/PrintDocument";
import type { PrintComponentProps } from "../../../../print/print-registry";

function monthLabel(month: string) { return /^\d{4}-\d{2}$/.test(month) ? new Date(`${month}-01T12:00:00`).toLocaleDateString(undefined, { month: "long", year: "numeric" }) : month; }

export function WindowsBarsDoorsPrint({ definition, prefill }: PrintComponentProps) {
  return <PrintDocument title={definition.title}>
    <header className="print-document__header"><h1>{definition.title}</h1><dl><div><dt>Month</dt><dd>{monthLabel(prefill.month)}</dd></div><div><dt>Shift</dt><dd>{prefill.shift}</dd></div></dl></header>
    <table className="paper-log-table"><thead><tr>{definition.definition.columns.map((column) => <th key={column} scope="col">{column}</th>)}</tr></thead><tbody>{Array.from({ length: 31 }, (_, index) => <tr key={index}><th scope="row">{index + 1}</th>{definition.definition.columns.slice(1).map((column) => <td key={column} />)}</tr>)}</tbody></table>
    <p className="paper-log-note">{definition.definition.footerNote}</p><section className="paper-comments"><h2>Comments</h2><div aria-label="Comments area" /></section>
  </PrintDocument>;
}
