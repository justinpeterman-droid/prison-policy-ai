import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { KeyboardEvent } from "react";
import { WebApiError } from "../../../api/client";
import type { SessionProfile } from "../../auth/api";
import {
  getCountSheet,
  getCountSheetStructure,
  listCountSheets,
  recordCountSheetAction,
  saveCountSheet,
} from "./api";
import {
  calculateCountTotals,
  createBlankCountPayload,
  parseCountValue,
} from "./calculations";
import { CountSheetPrint } from "./CountSheetPrint";
import type {
  CountSheetPayload,
  CountSheetRecord,
  CountSheetStructure,
  CountValue,
} from "./types";
import "./count-sheet.css";

interface CountSheetPageProps {
  profile: SessionProfile;
}

type SaveState =
  | "loading"
  | "saved"
  | "dirty"
  | "saving"
  | "offline"
  | "conflict"
  | "error";

function localDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function display(value: CountValue): string {
  return value === null ? "" : String(value);
}

function title(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window.matchMedia === "function" ? window.matchMedia(query).matches : false,
  );

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, [query]);

  return matches;
}

function statusLabel(state: SaveState): string {
  if (state === "loading") return "Loading";
  if (state === "saving") return "Saving…";
  if (state === "dirty") return "Unsaved changes";
  if (state === "offline") return "Reconnecting — values preserved";
  if (state === "conflict") return "Save conflict — values preserved";
  if (state === "error") return "Save failed — values preserved";
  return "Saved";
}

function CountInput({
  value,
  label,
  className,
  inputRef,
  onChange,
  onFocus,
  onKeyDown,
}: {
  value: CountValue;
  label: string;
  className?: string;
  inputRef?: (element: HTMLInputElement | null) => void;
  onChange: (value: CountValue) => void;
  onFocus?: (element: HTMLInputElement) => void;
  onKeyDown?: (event: KeyboardEvent<HTMLInputElement>) => void;
}) {
  return (
    <input
      ref={inputRef}
      className={className}
      aria-label={label}
      inputMode="numeric"
      pattern="[0-9]*"
      autoComplete="off"
      value={display(value)}
      onFocus={(event) => {
        event.currentTarget.select();
        onFocus?.(event.currentTarget);
      }}
      onChange={(event) => {
        try {
          onChange(parseCountValue(event.currentTarget.value));
        } catch {
          // Controlled state keeps the last valid value visible.
        }
      }}
      onKeyDown={onKeyDown}
    />
  );
}

export function CountSheetPage({ profile }: CountSheetPageProps) {
  const [structure, setStructure] = useState<CountSheetStructure | null>(null);
  const [record, setRecord] = useState<CountSheetRecord | null>(null);
  const [payload, setPayload] = useState<CountSheetPayload | null>(null);
  const [workDate, setWorkDate] = useState(localDate);
  const [shift, setShift] = useState<string | null>(profile.shift);
  const [saveState, setSaveState] = useState<SaveState>("loading");
  const [message, setMessage] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [focused, setFocused] = useState<{ area: string; column: string } | null>(null);
  const [showPrintPreview, setShowPrintPreview] = useState(false);
  const gridRefs = useRef(new Map<string, HTMLInputElement>());
  const isMobile = useMediaQuery("(max-width: 760px)");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [approvedStructure, page] = await Promise.all([
          getCountSheetStructure(),
          listCountSheets(),
        ]);
        if (!active) return;
        setStructure(approvedStructure);
        if (page.items[0]) {
          const latest = await getCountSheet(page.items[0].record_id);
          if (!active) return;
          setRecord(latest);
          setPayload(latest.payload);
          setWorkDate(latest.work_date);
          setShift(latest.shift);
        } else {
          setPayload(createBlankCountPayload(approvedStructure));
        }
        setSaveState("saved");
      } catch (error) {
        if (!active) return;
        setSaveState(error instanceof WebApiError && error.status === 0 ? "offline" : "error");
        setMessage(error instanceof Error ? error.message : "The Count Sheet could not be opened.");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const totals = useMemo(() => {
    if (!structure || !payload) return null;
    return calculateCountTotals(structure, payload);
  }, [payload, structure]);

  const markDirty = useCallback(() => {
    setSaveState("dirty");
    setMessage(null);
  }, []);

  const updateCell = useCallback((area: string, column: string, value: CountValue) => {
    setPayload((current) => current ? {
      ...current,
      cells: {
        ...current.cells,
        [area]: { ...current.cells[area], [column]: value },
      },
    } : current);
    markDirty();
    setAnnouncement(`${area}, column ${column}, ${value ?? "blank"}`);
  }, [markDirty]);

  const updateInHousing = useCallback((column: string, value: CountValue) => {
    setPayload((current) => current ? {
      ...current,
      in_housing: { ...current.in_housing, [column]: value },
    } : current);
    markDirty();
    setAnnouncement(`In housing, column ${column}, ${value ?? "blank"}`);
  }, [markDirty]);

  const updateOperational = useCallback((field: string, value: CountValue) => {
    setPayload((current) => current ? {
      ...current,
      operational: { ...current.operational, [field]: value },
    } : current);
    markDirty();
    setAnnouncement(`${title(field)}, ${value ?? "blank"}`);
  }, [markDirty]);

  const updateTime = useCallback((field: "count_started" | "count_ended", value: string) => {
    setPayload((current) => current ? { ...current, [field]: value || null } : current);
    markDirty();
  }, [markDirty]);

  const performSave = useCallback(async (
    reason: "autosave" | "manual_save" | "recovery",
  ): Promise<CountSheetRecord | null> => {
    if (!structure || !payload) return null;
    setSaveState("saving");
    setMessage(null);
    try {
      const saved = await saveCountSheet({
        record,
        workDate,
        shift,
        payload,
        reason,
      });
      setRecord(saved);
      setPayload(saved.payload);
      setWorkDate(saved.work_date);
      setShift(saved.shift);
      setSaveState("saved");
      setAnnouncement(`Count Sheet revision ${saved.current_revision_number} saved.`);
      return saved;
    } catch (error) {
      if (error instanceof WebApiError && error.code === "revision_conflict") {
        setSaveState("conflict");
      } else if (error instanceof WebApiError && error.status === 0) {
        setSaveState("offline");
      } else {
        setSaveState("error");
      }
      setMessage(error instanceof Error ? error.message : "The Count Sheet could not be saved.");
      return null;
    }
  }, [payload, record, shift, structure, workDate]);

  useEffect(() => {
    if (saveState !== "dirty") return undefined;
    const timer = window.setTimeout(() => {
      void performSave("autosave");
    }, 60_000);
    return () => window.clearTimeout(timer);
  }, [performSave, saveState]);

  const focusGridCell = useCallback((row: number, column: number) => {
    if (!structure) return;
    const area = structure.areas[row];
    const columnName = structure.columns[column];
    if (!area || !columnName) return;
    gridRefs.current.get(`${area}|${columnName}`)?.focus();
  }, [structure]);

  const handleGridKey = useCallback((
    event: KeyboardEvent<HTMLInputElement>,
    row: number,
    column: number,
  ) => {
    if (!structure) return;
    let nextRow = row;
    let nextColumn = column;
    if (event.key === "ArrowRight") nextColumn += 1;
    else if (event.key === "ArrowLeft") nextColumn -= 1;
    else if (event.key === "ArrowDown" || (event.key === "Enter" && !event.shiftKey)) nextRow += 1;
    else if (event.key === "ArrowUp" || (event.key === "Enter" && event.shiftKey)) nextRow -= 1;
    else return;
    if (
      nextRow >= 0
      && nextRow < structure.areas.length
      && nextColumn >= 0
      && nextColumn < structure.columns.length
    ) {
      event.preventDefault();
      focusGridCell(nextRow, nextColumn);
    }
  }, [focusGridCell, structure]);

  const printSheet = useCallback(async () => {
    let target = record;
    if (saveState === "dirty" || !target) {
      target = await performSave("manual_save");
    }
    if (!target) return;
    try {
      await recordCountSheetAction(target.record_id, "print");
      window.print();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Print could not be opened.");
    }
  }, [performSave, record, saveState]);

  const previewSheet = useCallback(async () => {
    let target = record;
    if (saveState === "dirty" || !target) {
      target = await performSave("manual_save");
    }
    if (!target) return;
    try {
      await recordCountSheetAction(target.record_id, "preview");
      setShowPrintPreview(true);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Preview could not be opened.");
    }
  }, [performSave, record, saveState]);

  if (!structure || !payload || !totals) {
    return (
      <section className="iw-page count-page" aria-labelledby="count-heading" aria-busy="true">
        <header className="iw-page-header">
          <div><p className="iw-eyebrow">Officer Utilities</p><h1 id="count-heading">NCU Days Count</h1></div>
        </header>
        <div className="iw-empty-state">
          <div className="iw-empty-icon" aria-hidden="true">#</div>
          <h2>{saveState === "loading" ? "Opening the official count sheet…" : "The Count Sheet is unavailable"}</h2>
          <p>{message ?? "Connecting securely. No count values have been changed."}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="iw-page count-page" aria-labelledby="count-heading">
      <header className="count-page__header">
        <div>
          <p className="iw-eyebrow">Officer Utilities · Operational Paperwork</p>
          <h1 id="count-heading">NCU Days Count</h1>
          <p>Enter the count exactly as received. Totals calculate automatically; mismatches are never balanced for you.</p>
        </div>
        <div className={`count-save-state count-save-state--${saveState}`} role="status">
          <span aria-hidden="true">{saveState === "saved" ? "✓" : saveState === "saving" ? "↻" : "•"}</span>
          <span>{statusLabel(saveState)}</span>
          {record ? <small>Revision {record.current_revision_number}</small> : <small>New sheet</small>}
        </div>
      </header>

      <div className="count-toolbar">
        <div className="count-toolbar__identity">
          <strong>{structure.title}</strong>
          <span>{profile.displayName} · {shift || "Shift not assigned"}</span>
        </div>
        <label>Date<input type="date" value={workDate} onChange={(event) => { setWorkDate(event.target.value); markDirty(); }} /></label>
        <label>Shift<input value={shift ?? ""} maxLength={32} onChange={(event) => { setShift(event.target.value || null); markDirty(); }} /></label>
        <label>Count started<input type="time" value={payload.count_started?.slice(0, 5) ?? ""} onChange={(event) => updateTime("count_started", event.target.value)} /></label>
        <label>Count ended<input type="time" value={payload.count_ended?.slice(0, 5) ?? ""} onChange={(event) => updateTime("count_ended", event.target.value)} /></label>
      </div>

      <div className="count-actions" aria-label="Count Sheet actions">
        <button className="iw-button iw-button--primary" type="button" onClick={() => void performSave("manual_save")} disabled={saveState === "saving"}>Save Count Sheet</button>
        <button className="iw-button" type="button" onClick={() => void previewSheet()}>Preview Print Layout</button>
        <button className="iw-button" type="button" onClick={() => void printSheet()}>Print Count Sheet</button>
      </div>

      {message ? <div className="iw-alert iw-alert--warning" role="alert">{message}</div> : null}

      <div className={`count-reconciliation ${totals.reconciled ? "is-reconciled" : "is-mismatch"}`} role="status">
        <div>
          <span>{totals.reconciled ? "Count reconciles" : "The count does not reconcile"}</span>
          <strong>{totals.reconciled ? "Housing and operational totals agree." : `The totals differ by ${Math.abs(totals.difference)}.`}</strong>
        </div>
        <div className="count-reconciliation__totals">
          <span>Housing total {totals.housing_total}</span>
          <span>Operational total {totals.operational_total}</span>
          <span>Signed difference {totals.difference}</span>
        </div>
      </div>

      {isMobile ? (
        <div className="count-mobile" aria-label="Mobile Count Sheet entry">
          {structure.columns.map((column) => (
            <section className="count-mobile__column" key={column}>
              <header><h2>Housing {column}</h2><strong>Unit total {totals.unit_totals[column]}</strong></header>
              <div className="count-mobile__fields">
                {structure.areas.map((area, rowIndex) => (
                  <label key={area}>
                    <span>{area}</span>
                    <CountInput
                      value={payload.cells[area][column]}
                      label={`${area}, column ${column}`}
                      onChange={(value) => updateCell(area, column, value)}
                      onFocus={() => setFocused({ area, column })}
                      onKeyDown={(event) => handleGridKey(event, rowIndex, structure.columns.indexOf(column))}
                    />
                  </label>
                ))}
                <label className="count-mobile__in-housing">
                  <span>In Housing</span>
                  <CountInput
                    value={payload.in_housing[column]}
                    label={`In housing, column ${column}`}
                    onChange={(value) => updateInHousing(column, value)}
                  />
                </label>
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="count-grid-wrap">
          <table className="count-grid">
            <thead>
              <tr>
                <th className="count-grid__area">Area</th>
                {structure.columns.map((column) => (
                  <th key={column} className={focused?.column === column ? "is-focused" : ""}>{column}</th>
                ))}
                <th className="count-grid__total">Total</th>
              </tr>
            </thead>
            <tbody>
              {structure.areas.map((area, rowIndex) => (
                <tr key={area} className={focused?.area === area ? "is-focused" : ""}>
                  <th className="count-grid__area" scope="row">{area}</th>
                  {structure.columns.map((column, columnIndex) => (
                    <td key={column}>
                      <CountInput
                        value={payload.cells[area][column]}
                        label={`${area}, column ${column}`}
                        inputRef={(element) => {
                          const key = `${area}|${column}`;
                          if (element) gridRefs.current.set(key, element);
                          else gridRefs.current.delete(key);
                        }}
                        onChange={(value) => updateCell(area, column, value)}
                        onFocus={() => setFocused({ area, column })}
                        onKeyDown={(event) => handleGridKey(event, rowIndex, columnIndex)}
                      />
                    </td>
                  ))}
                  <td className="count-grid__total">{totals.row_totals[area]}</td>
                </tr>
              ))}
              <tr className="count-grid__summary-row">
                <th className="count-grid__area" scope="row">Out of Housing</th>
                {structure.columns.map((column) => <td key={column}>{totals.out_of_housing[column]}</td>)}
                <td className="count-grid__total">{Object.values(totals.out_of_housing).reduce((a, b) => a + b, 0)}</td>
              </tr>
              <tr className="count-grid__entry-row">
                <th className="count-grid__area" scope="row">In Housing</th>
                {structure.columns.map((column) => (
                  <td key={column}>
                    <CountInput
                      value={payload.in_housing[column]}
                      label={`In housing, column ${column}`}
                      onChange={(value) => updateInHousing(column, value)}
                    />
                  </td>
                ))}
                <td className="count-grid__total">{Object.values(payload.in_housing).reduce((total, value) => total + (value ?? 0), 0)}</td>
              </tr>
              <tr className="count-grid__unit-row">
                <th className="count-grid__area" scope="row">Unit Total</th>
                {structure.columns.map((column) => <td key={column}>{totals.unit_totals[column]}</td>)}
                <td className="count-grid__total">{totals.housing_total}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      <section className="count-operational" aria-labelledby="operational-heading">
        <header>
          <div><p className="iw-eyebrow">Reconciliation</p><h2 id="operational-heading">Operational totals</h2></div>
          <p>Use the source totals supplied for this count. Court, hospital, and furlough entries retain their supporting-form reminders.</p>
        </header>
        <div className="count-operational__grid">
          {structure.operational_fields.map((field) => (
            <label key={field}>
              <span>{title(field)}</span>
              <CountInput
                value={payload.operational[field]}
                label={`Operational total: ${field.replaceAll("_", " ")}`}
                onChange={(value) => updateOperational(field, value)}
              />
              {structure.attachment_reminders.includes(field) ? <small>Supporting form reminder</small> : null}
            </label>
          ))}
        </div>
      </section>

      <aside className="count-mobile-totals" aria-label="Persistent count totals">
        <span>Housing <strong>{totals.housing_total}</strong></span>
        <span>Operational <strong>{totals.operational_total}</strong></span>
        <span>Difference <strong>{totals.difference}</strong></span>
      </aside>

      <div className="sr-only" aria-live="polite">{announcement}</div>

      {showPrintPreview ? (
        <div className="count-preview" role="dialog" aria-modal="true" aria-labelledby="count-preview-heading">
          <div className="count-preview__bar">
            <div><p className="iw-eyebrow">Print Preview</p><h2 id="count-preview-heading">Official landscape layout</h2></div>
            <button className="iw-button" type="button" onClick={() => setShowPrintPreview(false)}>Close Preview</button>
          </div>
          <div className="count-preview__paper">
            <CountSheetPrint structure={structure} payload={payload} totals={totals} workDate={workDate} shift={shift} />
          </div>
        </div>
      ) : null}

      <CountSheetPrint structure={structure} payload={payload} totals={totals} workDate={workDate} shift={shift} />
    </section>
  );
}
