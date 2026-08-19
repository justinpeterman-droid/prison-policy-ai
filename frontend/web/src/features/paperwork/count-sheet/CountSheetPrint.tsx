import type {
  CountSheetPayload,
  CountSheetStructure,
  CountSheetTotals,
} from "./types";

interface CountSheetPrintProps {
  structure: CountSheetStructure;
  payload: CountSheetPayload;
  totals: CountSheetTotals;
  workDate: string;
  shift: string | null;
}

function display(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

function label(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function CountSheetPrint({
  structure,
  payload,
  totals,
  workDate,
  shift,
}: CountSheetPrintProps) {
  return (
    <section className="count-print" aria-label="Count Sheet print preview">
      <header className="count-print__header">
        <div>
          <p>Official operational count worksheet</p>
          <h1>{structure.title}</h1>
        </div>
        <dl>
          <div><dt>Date</dt><dd>{workDate}</dd></div>
          <div><dt>Shift</dt><dd>{shift || ""}</dd></div>
          <div><dt>Started</dt><dd>{payload.count_started || ""}</dd></div>
          <div><dt>Ended</dt><dd>{payload.count_ended || ""}</dd></div>
        </dl>
      </header>

      <table className="count-print__table">
        <thead>
          <tr>
            <th>Area</th>
            {structure.columns.map((column) => <th key={column}>{column}</th>)}
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {structure.areas.map((area) => (
            <tr key={area}>
              <th>{area}</th>
              {structure.columns.map((column) => (
                <td key={column}>{display(payload.cells[area][column])}</td>
              ))}
              <td>{totals.row_totals[area]}</td>
            </tr>
          ))}
          <tr className="count-print__subtotal">
            <th>Out of Housing</th>
            {structure.columns.map((column) => (
              <td key={column}>{totals.out_of_housing[column]}</td>
            ))}
            <td>{Object.values(totals.out_of_housing).reduce((a, b) => a + b, 0)}</td>
          </tr>
          <tr>
            <th>In Housing</th>
            {structure.columns.map((column) => (
              <td key={column}>{display(payload.in_housing[column])}</td>
            ))}
            <td>{Object.values(payload.in_housing).reduce((total, value) => total + (value ?? 0), 0)}</td>
          </tr>
          <tr className="count-print__total">
            <th>Unit Total</th>
            {structure.columns.map((column) => (
              <td key={column}>{totals.unit_totals[column]}</td>
            ))}
            <td>{totals.housing_total}</td>
          </tr>
        </tbody>
      </table>

      <div className="count-print__summary">
        <table>
          <thead><tr><th colSpan={2}>Operational Reconciliation</th></tr></thead>
          <tbody>
            {structure.operational_fields.map((field) => (
              <tr key={field}>
                <th>{label(field)}</th>
                <td>{display(payload.operational[field])}</td>
              </tr>
            ))}
            <tr><th>Operational Total</th><td>{totals.operational_total}</td></tr>
            <tr><th>Housing Total</th><td>{totals.housing_total}</td></tr>
            <tr><th>Difference</th><td>{totals.difference}</td></tr>
          </tbody>
        </table>
        <aside>
          <strong>{totals.reconciled ? "COUNT RECONCILED" : "COUNT DOES NOT RECONCILE"}</strong>
          <p>Difference: {totals.difference}</p>
          <p>
            Attach supporting forms when entries are recorded for {structure.attachment_reminders.map(label).join(", ")}.
          </p>
        </aside>
      </div>
    </section>
  );
}
