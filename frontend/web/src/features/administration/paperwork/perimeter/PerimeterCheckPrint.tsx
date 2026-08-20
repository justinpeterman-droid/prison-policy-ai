import type { PerimeterDefinition, PerimeterPayload } from "./model";


export function PerimeterCheckPrint({ payload, definition }: { payload: PerimeterPayload; definition: PerimeterDefinition }) {
  const result = new Map(payload.checks.map((check) => [check.check_code, check.result]));
  return <article className="perimeter-check-print" data-testid="perimeter-check-print" aria-label="Perimeter Check print document">
    <header><div><strong>North Central Unit</strong><span>Daily operational paperwork</span></div><h1>Perimeter Check List</h1><dl><dt>Date</dt><dd>{payload.work_date}</dd><dt>Shift</dt><dd>{payload.shift}</dd></dl></header>
    <div className="perimeter-print-groups">{definition.groups.map((group) => <section key={group.code}><h2>{group.label}</h2><table><thead><tr><th>Check location</th><th>S</th><th>U</th></tr></thead><tbody>{group.items.map((item) => <tr key={item.code}><th>{item.label}</th><td>{result.get(item.code) === "S" ? "✓" : ""}</td><td>{result.get(item.code) === "U" ? "✓" : ""}</td></tr>)}</tbody></table></section>)}</div>
    <p className="perimeter-print-legend"><strong>S = Satisfactory</strong><strong>U = Unsatisfactory</strong></p>
    <div className="perimeter-print-signoff"><span>Perimeter Inspected by: {payload.perimeter_inspector?.display_name_snapshot ?? "________________"}</span><span>Signature: {payload.perimeter_signature_name ?? "________________"}</span><span>Date / Time: {payload.perimeter_inspected_at ?? "________________"}</span><span>Senstar Inspected by: {payload.senstar_inspector?.display_name_snapshot ?? "________________"}</span><span>Shift Supervisor's Signature: {payload.supervisor_signature_name ?? "________________"}</span><span>Date / Time: {payload.supervisor_signed_at ?? "________________"}</span></div>
  </article>;
}
