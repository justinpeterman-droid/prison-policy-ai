import { useMemo } from "react";
import type { KeyboardEvent } from "react";
import {
  calculateCountSheet,
  type CountSheetDefinition,
  type CountValues,
} from "./counts";
import "./count-sheet.css";

export type CountSaveState = "saved" | "saving" | "unsaved" | "reconnecting" | "failed";

interface CountSheetGridProps {
  definition: CountSheetDefinition;
  values: CountValues;
  expectedOperationalTotal: number;
  onValuesChange: (values: CountValues) => void;
  onExpectedOperationalTotalChange: (value: number) => void;
  onSave: () => void;
  onPrint?: () => void;
  saveState: CountSaveState;
}

const SAVE_LABELS: Record<CountSaveState, string> = {
  saved: "Saved",
  saving: "Saving…",
  unsaved: "Unsaved changes",
  reconnecting: "Reconnecting…",
  failed: "Save failed — your visible work is still here",
};

function moveFocus(
  event: KeyboardEvent<HTMLInputElement>,
  rowIndex: number,
  columnIndex: number,
  rowCount: number,
  columnCount: number,
): void {
  const offsets: Record<string, readonly [number, number]> = {
    ArrowLeft: [0, -1],
    ArrowRight: [0, 1],
    ArrowUp: [-1, 0],
    ArrowDown: [1, 0],
  };
  const offset = offsets[event.key];
  if (!offset) return;
  const nextRow = rowIndex + offset[0];
  const nextColumn = columnIndex + offset[1];
  if (
    nextRow < 0 ||
    nextRow >= rowCount ||
    nextColumn < 0 ||
    nextColumn >= columnCount
  ) {
    return;
  }
  const target = document.querySelector<HTMLInputElement>(
    `[data-count-position="${nextRow}:${nextColumn}"]`,
  );
  if (target) {
    event.preventDefault();
    target.focus();
    target.select();
  }
}

function nextValues(
  current: CountValues,
  rowId: string,
  columnId: string,
  raw: string,
): CountValues | null {
  if (!/^\d{0,5}$/.test(raw)) return null;
  const row = { ...(current[rowId] ?? {}) };
  if (raw === "") {
    delete row[columnId];
  } else {
    row[columnId] = Number(raw);
  }
  return { ...current, [rowId]: row };
}

export function CountSheetGrid({
  definition,
  values,
  expectedOperationalTotal,
  onValuesChange,
  onExpectedOperationalTotalChange,
  onSave,
  onPrint,
  saveState,
}: CountSheetGridProps) {
  const calculation = useMemo(
    () => calculateCountSheet(definition, values, expectedOperationalTotal),
    [definition, expectedOperationalTotal, values],
  );

  return (
    <section className="count-sheet" aria-labelledby="count-sheet-heading">
      <header className="count-sheet-heading">
        <div>
          <p className="count-sheet-overline">Operational Paperwork</p>
          <h1 id="count-sheet-heading">{definition.title}</h1>
          <p>Enter the observed count. The application calculates totals but never changes a value to make it balance.</p>
        </div>
        <div className="count-sheet-toolbar">
          <span className={`count-save-state ${saveState}`} role="status" aria-live="polite">
            {SAVE_LABELS[saveState]}
          </span>
          <button type="button" className="count-secondary-button" onClick={onPrint} disabled={!onPrint}>
            Print preview
          </button>
          <button type="button" className="count-primary-button" onClick={onSave} disabled={saveState === "saving"}>
            Save count
          </button>
        </div>
      </header>

      <div className="count-sheet-table-wrap">
        <table className="count-sheet-table">
          <caption className="sr-only">Count entries and calculated totals</caption>
          <thead>
            <tr>
              <th scope="col">Location</th>
              {definition.columns.map((column) => (
                <th scope="col" key={column.id}>{column.label}</th>
              ))}
              <th scope="col">Row total</th>
            </tr>
          </thead>
          <tbody>
            {definition.rows.map((row, rowIndex) => (
              <tr key={row.id} data-section={row.section}>
                <th scope="row">
                  <span>{row.label}</span>
                  <small>{row.section.replaceAll("_", " ")}</small>
                </th>
                {definition.columns.map((column, columnIndex) => {
                  const cell = values[row.id]?.[column.id];
                  return (
                    <td key={column.id}>
                      <input
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength={5}
                        value={cell ?? ""}
                        aria-label={`${row.label} ${column.label}`}
                        data-count-position={`${rowIndex}:${columnIndex}`}
                        onKeyDown={(event) => moveFocus(
                          event,
                          rowIndex,
                          columnIndex,
                          definition.rows.length,
                          definition.columns.length,
                        )}
                        onChange={(event) => {
                          const updated = nextValues(
                            values,
                            row.id,
                            column.id,
                            event.currentTarget.value,
                          );
                          if (updated) onValuesChange(updated);
                        }}
                      />
                    </td>
                  );
                })}
                <td className="count-total-cell">{calculation.rowTotals[row.id]}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">Column totals</th>
              {definition.columns.map((column) => (
                <td className="count-total-cell" key={column.id}>
                  {calculation.columnTotals[column.id]}
                </td>
              ))}
              <td className="count-total-cell">
                {Object.values(calculation.rowTotals).reduce((total, value) => total + value, 0)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <section className="count-reconciliation" aria-labelledby="count-reconciliation-heading">
        <div>
          <h2 id="count-reconciliation-heading">Reconciliation</h2>
          <p>Operational total: {calculation.operationalTotal}</p>
        </div>
        <label>
          <span>Expected operational total</span>
          <input
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={5}
            aria-label="Expected operational total"
            value={expectedOperationalTotal}
            onChange={(event) => {
              if (/^\d{1,5}$/.test(event.currentTarget.value)) {
                onExpectedOperationalTotalChange(Number(event.currentTarget.value));
              }
            }}
          />
        </label>
        <div className={`count-difference ${calculation.isReconciled ? "balanced" : "mismatch"}`}>
          <strong>Difference: {calculation.reconciliationDifference}</strong>
          {calculation.isReconciled ? (
            <span role="status">Count reconciles.</span>
          ) : (
            <span role="alert">The observed count does not reconcile. Review the entries; no value was changed automatically.</span>
          )}
        </div>
      </section>
    </section>
  );
}
