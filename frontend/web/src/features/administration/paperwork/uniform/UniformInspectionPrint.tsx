import { UNIFORM_COLUMNS, UNIFORM_COLUMN_LABELS, type UniformPayload } from "./model";


export function UniformInspectionPrint({ payload }: { payload: UniformPayload }) {
  return (
    <article className="uniform-inspection-print" data-testid="uniform-inspection-print" aria-label="Uniform Inspection print document">
      <header><div><strong>North Central Unit</strong><span>Daily operational paperwork</span></div><h1>Uniform Inspection Log</h1><dl><div><dt>Date</dt><dd>{payload.work_date}</dd></div><div><dt>Shift</dt><dd>{payload.shift}</dd></div></dl></header>
      <table>
        <thead><tr><th>Name</th>{UNIFORM_COLUMNS.map((column) => <th key={column}>{UNIFORM_COLUMN_LABELS[column]}</th>)}<th>Comments</th></tr></thead>
        <tbody>{payload.rows.map((row) => <tr key={row.staff.staff_id}><th>{row.staff.display_name_snapshot}</th>{UNIFORM_COLUMNS.map((column) => <td key={column}>{row[column] ?? "—"}</td>)}<td>{row.comments || "—"}</td></tr>)}</tbody>
      </table>
      <section className="uniform-print-legend"><strong>Legend</strong><span>S = Satisfactory</span><span>N/I = Needs Improvement</span><span>U = Unsatisfactory</span><span>NONE = Not used / not applicable</span></section>
      <div className="uniform-print-signoff"><span>Staff Conducting Inspection: {payload.inspector?.display_name_snapshot ?? "____________________"}</span><span>Date: {payload.work_date}</span><span>Shift: {payload.shift}</span></div>
      <footer><strong>Distribution:</strong> Shift Supervisor · Building Captain · File</footer>
    </article>
  );
}
